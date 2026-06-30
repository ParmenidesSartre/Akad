"""Compare two contract versions and classify each change as breaking or
non-breaking for a consumer relying on the OLD contract's guarantees.

`akad diff` (see akad.cli) wraps this module for command-line use.

The rule applied throughout: loosening a producer guarantee is breaking
(a consumer that relied on the old, stricter guarantee may now fail);
tightening one is non-breaking (anything that satisfied the new, stricter
guarantee also satisfied the old, looser one).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from akad.models.contract import ColumnSpec, DataContract


class DiffSeverity(StrEnum):
    BREAKING     = "BREAKING"
    NON_BREAKING = "NON_BREAKING"


@dataclass
class DiffEntry:
    severity:           DiffSeverity
    path:               str
    message:            str
    affected_consumers: list[str] = field(default_factory=list)


def _path_matches(diff_path: str, dependency: str) -> bool:
    """True if a consumer's declared *dependency* overlaps with *diff_path*.

    Handles both directions: a consumer depending on a whole column
    ("schema.columns.ccy") is affected by a change to one of its
    sub-attributes ("schema.columns.ccy.allowed_values"), and a consumer
    depending on one specific rule is still affected if the broader thing
    it lives under is removed entirely.
    """
    return (
        diff_path == dependency
        or diff_path.startswith(dependency + ".")
        or dependency.startswith(diff_path + ".")
    )


def _bound_diff(
    path: str,
    old: float | None,
    new: float | None,
    *,
    higher_is_looser: bool,
) -> DiffEntry | None:
    """Compare an optional numeric bound.

    *higher_is_looser* is True for an upper-bound-style field (max_rows,
    max_value, max_age_hours — a bigger number permits more), and False for
    a lower-bound-style field (min_rows, min_value — a bigger number
    permits less).
    """
    if old == new:
        return None
    if old is None:
        bound = f"<= {new}" if higher_is_looser else f">= {new}"
        return DiffEntry(DiffSeverity.NON_BREAKING, path, f"added constraint ({bound})")
    if new is None:
        return DiffEntry(DiffSeverity.BREAKING, path, f"removed constraint (was {old})")

    loosened = (new > old) if higher_is_looser else (new < old)
    severity = DiffSeverity.BREAKING if loosened else DiffSeverity.NON_BREAKING
    return DiffEntry(severity, path, f"changed from {old} to {new}")


def _diff_column(path: str, old: ColumnSpec, new: ColumnSpec) -> list[DiffEntry]:
    entries: list[DiffEntry] = []

    if old.type != new.type:
        entries.append(DiffEntry(
            DiffSeverity.BREAKING, f"{path}.type",
            f"type changed from {old.type.value} to {new.type.value}",
        ))

    if old.nullable != new.nullable:
        if new.nullable:
            entries.append(DiffEntry(
                DiffSeverity.BREAKING, f"{path}.nullable", "became nullable (was guaranteed non-null)",
            ))
        else:
            entries.append(DiffEntry(
                DiffSeverity.NON_BREAKING, f"{path}.nullable", "became non-nullable (was nullable)",
            ))

    if old.allowed_values != new.allowed_values:
        old_set = set(old.allowed_values or [])
        new_set = set(new.allowed_values or [])
        added   = sorted(new_set - old_set)
        removed = sorted(old_set - new_set)
        if old.allowed_values is None:
            entries.append(DiffEntry(
                DiffSeverity.NON_BREAKING, f"{path}.allowed_values", f"added constraint: {sorted(new_set)}",
            ))
        elif new.allowed_values is None:
            entries.append(DiffEntry(
                DiffSeverity.BREAKING, f"{path}.allowed_values", "removed constraint (no longer limited to a fixed set)",
            ))
        elif added:
            entries.append(DiffEntry(
                DiffSeverity.BREAKING, f"{path}.allowed_values", f"now allows additional values: {added}",
            ))
        else:
            entries.append(DiffEntry(
                DiffSeverity.NON_BREAKING, f"{path}.allowed_values", f"no longer allows: {removed}",
            ))

    return entries


def _diff_schema(old: DataContract, new: DataContract) -> list[DiffEntry]:
    old_cols = {c.name: c for c in (old.schema_.columns if old.schema_ else [])}
    new_cols = {c.name: c for c in (new.schema_.columns if new.schema_ else [])}

    removed = [
        DiffEntry(DiffSeverity.BREAKING, f"schema.columns.{name}", "column removed")
        for name in sorted(old_cols.keys() - new_cols.keys())
    ]
    added = [
        DiffEntry(DiffSeverity.NON_BREAKING, f"schema.columns.{name}", "column added")
        for name in sorted(new_cols.keys() - old_cols.keys())
    ]
    changed = [
        entry
        for name in sorted(old_cols.keys() & new_cols.keys())
        for entry in _diff_column(f"schema.columns.{name}", old_cols[name], new_cols[name])
    ]
    return [*removed, *added, *changed]


def _diff_volume(old: DataContract, new: DataContract) -> list[DiffEntry]:
    old_v, new_v = old.volume, new.volume
    old_min = old_v.min_rows if old_v else None
    new_min = new_v.min_rows if new_v else None
    old_max = old_v.max_rows if old_v else None
    new_max = new_v.max_rows if new_v else None

    entries = [
        _bound_diff("volume.min_rows", old_min, new_min, higher_is_looser=False),
        _bound_diff("volume.max_rows", old_max, new_max, higher_is_looser=True),
    ]
    return [e for e in entries if e is not None]


def _diff_freshness(old: DataContract, new: DataContract) -> list[DiffEntry]:
    old_age = old.freshness.max_age_hours if old.freshness else None
    new_age = new.freshness.max_age_hours if new.freshness else None
    e = _bound_diff("freshness.max_age_hours", old_age, new_age, higher_is_looser=True)
    return [e] if e else []


_QUALITY_BOUND_FIELDS = (
    ("max_null_percentage", True),
    ("max_duplicate_percentage", True),
    ("min_value", False),
    ("max_value", True),
)


def _diff_quality(old: DataContract, new: DataContract) -> list[DiffEntry]:
    old_rules = {r.column: r for r in old.quality}
    new_rules = {r.column: r for r in new.quality}

    removed = [
        DiffEntry(DiffSeverity.BREAKING, f"quality.{col}", "quality rule removed")
        for col in sorted(old_rules.keys() - new_rules.keys())
    ]
    added = [
        DiffEntry(DiffSeverity.NON_BREAKING, f"quality.{col}", "quality rule added")
        for col in sorted(new_rules.keys() - old_rules.keys())
    ]
    changed = [
        e
        for col in sorted(old_rules.keys() & new_rules.keys())
        for field, higher_is_looser in _QUALITY_BOUND_FIELDS
        if (e := _bound_diff(
            f"quality.{col}.{field}",
            getattr(old_rules[col], field), getattr(new_rules[col], field),
            higher_is_looser=higher_is_looser,
        )) is not None
    ]
    return [*removed, *added, *changed]


def _diff_business_rules(old: DataContract, new: DataContract) -> list[DiffEntry]:
    old_rules = {r.name: r for r in old.business_rules}
    new_rules = {r.name: r for r in new.business_rules}

    removed = [
        DiffEntry(DiffSeverity.BREAKING, f"business_rules.{name}", "business rule removed")
        for name in sorted(old_rules.keys() - new_rules.keys())
    ]
    added = [
        DiffEntry(DiffSeverity.NON_BREAKING, f"business_rules.{name}", "business rule added")
        for name in sorted(new_rules.keys() - old_rules.keys())
    ]
    # An expression's strictness can't be inferred statically, so any change
    # to an existing rule's logic is conservatively flagged as breaking —
    # better a false alarm a human dismisses than a silent gap in coverage.
    changed = [
        DiffEntry(
            DiffSeverity.BREAKING, f"business_rules.{name}",
            f"expression changed from {old_rules[name].expression!r} to {new_rules[name].expression!r}",
        )
        for name in sorted(old_rules.keys() & new_rules.keys())
        if old_rules[name].expression != new_rules[name].expression
    ]
    return [*removed, *added, *changed]


def diff_contracts(old: DataContract, new: DataContract) -> list[DiffEntry]:
    """Compare *old* and *new* contract versions.

    Returns every detected change, classified as BREAKING or NON_BREAKING
    for a consumer relying on *old*'s guarantees. Pure function — no I/O,
    no registry access. Metadata, notifications, and the consumer list
    itself are not diffed as changes — they don't affect what the data
    looks like. The OLD contract's consumers ARE used, though, to annotate
    each entry with which teams declared a dependency (via
    ConsumerSpec.depends_on) that overlaps with that specific change.
    """
    entries = [
        *_diff_schema(old, new),
        *_diff_volume(old, new),
        *_diff_freshness(old, new),
        *_diff_quality(old, new),
        *_diff_business_rules(old, new),
    ]
    for entry in entries:
        entry.affected_consumers = [
            consumer.team for consumer in old.consumers
            if any(_path_matches(entry.path, dep) for dep in consumer.depends_on)
        ]
    return entries
