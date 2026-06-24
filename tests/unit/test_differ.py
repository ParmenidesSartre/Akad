"""Tests for akad.differ — breaking vs non-breaking contract change detection.

The core rule under test: loosening a guarantee is breaking, tightening
one is non-breaking. Each numeric bound is tested in both directions
explicitly, since getting the direction backwards is the easiest way
for this kind of logic to be subtly wrong.
"""
from __future__ import annotations

from akad.differ import DiffSeverity, diff_contracts
from tests.conftest import make_contract


def _entry(entries, path):
    return next(e for e in entries if e.path == path)


class TestNoChanges:
    def test_identical_contracts_produce_no_entries(self):
        c = make_contract(
            schema_columns=[{"name": "id", "type": "string", "nullable": False}],
            volume={"min_rows": 10, "max_rows": 100},
            freshness={"max_age_hours": 24},
            quality=[{"column": "id", "max_null_percentage": 0.0}],
        )
        assert diff_contracts(c, c) == []


class TestColumnPresence:
    def test_column_removed_is_breaking(self):
        old = make_contract(schema_columns=[
            {"name": "id", "type": "string"}, {"name": "region", "type": "string"},
        ])
        new = make_contract(schema_columns=[{"name": "id", "type": "string"}])
        entry = _entry(diff_contracts(old, new), "schema.columns.region")
        assert entry.severity == DiffSeverity.BREAKING
        assert "removed" in entry.message

    def test_column_added_is_non_breaking(self):
        old = make_contract(schema_columns=[{"name": "id", "type": "string"}])
        new = make_contract(schema_columns=[
            {"name": "id", "type": "string"}, {"name": "notes", "type": "string"},
        ])
        entry = _entry(diff_contracts(old, new), "schema.columns.notes")
        assert entry.severity == DiffSeverity.NON_BREAKING
        assert "added" in entry.message


class TestColumnType:
    def test_type_change_is_breaking(self):
        old = make_contract(schema_columns=[{"name": "amount", "type": "integer"}])
        new = make_contract(schema_columns=[{"name": "amount", "type": "float"}])
        entry = _entry(diff_contracts(old, new), "schema.columns.amount.type")
        assert entry.severity == DiffSeverity.BREAKING
        assert "integer" in entry.message and "float" in entry.message


class TestNullable:
    def test_becoming_nullable_is_breaking(self):
        old = make_contract(schema_columns=[{"name": "id", "type": "string", "nullable": False}])
        new = make_contract(schema_columns=[{"name": "id", "type": "string", "nullable": True}])
        entry = _entry(diff_contracts(old, new), "schema.columns.id.nullable")
        assert entry.severity == DiffSeverity.BREAKING

    def test_becoming_non_nullable_is_non_breaking(self):
        old = make_contract(schema_columns=[{"name": "id", "type": "string", "nullable": True}])
        new = make_contract(schema_columns=[{"name": "id", "type": "string", "nullable": False}])
        entry = _entry(diff_contracts(old, new), "schema.columns.id.nullable")
        assert entry.severity == DiffSeverity.NON_BREAKING


class TestAllowedValues:
    def test_adding_a_value_is_breaking(self):
        old = make_contract(schema_columns=[
            {"name": "ccy", "type": "string", "allowed_values": ["MYR", "USD"]},
        ])
        new = make_contract(schema_columns=[
            {"name": "ccy", "type": "string", "allowed_values": ["MYR", "USD", "JPY"]},
        ])
        entry = _entry(diff_contracts(old, new), "schema.columns.ccy.allowed_values")
        assert entry.severity == DiffSeverity.BREAKING
        assert "JPY" in entry.message

    def test_removing_a_value_only_is_non_breaking(self):
        old = make_contract(schema_columns=[
            {"name": "ccy", "type": "string", "allowed_values": ["MYR", "USD", "SGD"]},
        ])
        new = make_contract(schema_columns=[
            {"name": "ccy", "type": "string", "allowed_values": ["MYR", "USD"]},
        ])
        entry = _entry(diff_contracts(old, new), "schema.columns.ccy.allowed_values")
        assert entry.severity == DiffSeverity.NON_BREAKING
        assert "SGD" in entry.message

    def test_adding_constraint_where_none_existed_is_non_breaking(self):
        old = make_contract(schema_columns=[{"name": "ccy", "type": "string"}])
        new = make_contract(schema_columns=[
            {"name": "ccy", "type": "string", "allowed_values": ["MYR"]},
        ])
        entry = _entry(diff_contracts(old, new), "schema.columns.ccy.allowed_values")
        assert entry.severity == DiffSeverity.NON_BREAKING

    def test_removing_constraint_entirely_is_breaking(self):
        old = make_contract(schema_columns=[
            {"name": "ccy", "type": "string", "allowed_values": ["MYR"]},
        ])
        new = make_contract(schema_columns=[{"name": "ccy", "type": "string"}])
        entry = _entry(diff_contracts(old, new), "schema.columns.ccy.allowed_values")
        assert entry.severity == DiffSeverity.BREAKING


class TestVolume:
    def test_min_rows_decreased_is_breaking(self):
        old = make_contract(volume={"min_rows": 1000})
        new = make_contract(volume={"min_rows": 500})
        entry = _entry(diff_contracts(old, new), "volume.min_rows")
        assert entry.severity == DiffSeverity.BREAKING

    def test_min_rows_increased_is_non_breaking(self):
        old = make_contract(volume={"min_rows": 500})
        new = make_contract(volume={"min_rows": 1000})
        entry = _entry(diff_contracts(old, new), "volume.min_rows")
        assert entry.severity == DiffSeverity.NON_BREAKING

    def test_max_rows_increased_is_breaking(self):
        old = make_contract(volume={"max_rows": 1000})
        new = make_contract(volume={"max_rows": 2000})
        entry = _entry(diff_contracts(old, new), "volume.max_rows")
        assert entry.severity == DiffSeverity.BREAKING

    def test_max_rows_decreased_is_non_breaking(self):
        old = make_contract(volume={"max_rows": 2000})
        new = make_contract(volume={"max_rows": 1000})
        entry = _entry(diff_contracts(old, new), "volume.max_rows")
        assert entry.severity == DiffSeverity.NON_BREAKING

    def test_removing_max_rows_constraint_is_breaking(self):
        old = make_contract(volume={"max_rows": 1000})
        new = make_contract(volume={"min_rows": 1})  # volume spec present, max_rows now unset
        entry = _entry(diff_contracts(old, new), "volume.max_rows")
        assert entry.severity == DiffSeverity.BREAKING

    def test_adding_min_rows_constraint_is_non_breaking(self):
        old = make_contract(volume={"max_rows": 1000})
        new = make_contract(volume={"max_rows": 1000, "min_rows": 1})
        entry = _entry(diff_contracts(old, new), "volume.min_rows")
        assert entry.severity == DiffSeverity.NON_BREAKING


class TestFreshness:
    def test_max_age_hours_increased_is_breaking(self):
        old = make_contract(freshness={"max_age_hours": 24})
        new = make_contract(freshness={"max_age_hours": 48})
        entry = _entry(diff_contracts(old, new), "freshness.max_age_hours")
        assert entry.severity == DiffSeverity.BREAKING

    def test_max_age_hours_decreased_is_non_breaking(self):
        old = make_contract(freshness={"max_age_hours": 48})
        new = make_contract(freshness={"max_age_hours": 24})
        entry = _entry(diff_contracts(old, new), "freshness.max_age_hours")
        assert entry.severity == DiffSeverity.NON_BREAKING

    def test_removing_freshness_entirely_is_breaking(self):
        old = make_contract(freshness={"max_age_hours": 24})
        new = make_contract()
        entry = _entry(diff_contracts(old, new), "freshness.max_age_hours")
        assert entry.severity == DiffSeverity.BREAKING

    def test_adding_freshness_where_none_existed_is_non_breaking(self):
        old = make_contract()
        new = make_contract(freshness={"max_age_hours": 24})
        entry = _entry(diff_contracts(old, new), "freshness.max_age_hours")
        assert entry.severity == DiffSeverity.NON_BREAKING


class TestQualityRulePresence:
    def test_rule_removed_is_breaking(self):
        old = make_contract(quality=[{"column": "id", "max_null_percentage": 0.0}])
        new = make_contract()
        entry = _entry(diff_contracts(old, new), "quality.id")
        assert entry.severity == DiffSeverity.BREAKING

    def test_rule_added_is_non_breaking(self):
        old = make_contract()
        new = make_contract(quality=[{"column": "id", "max_null_percentage": 0.0}])
        entry = _entry(diff_contracts(old, new), "quality.id")
        assert entry.severity == DiffSeverity.NON_BREAKING


class TestQualityBounds:
    def test_max_null_percentage_increased_is_breaking(self):
        old = make_contract(quality=[{"column": "id", "max_null_percentage": 0.0}])
        new = make_contract(quality=[{"column": "id", "max_null_percentage": 5.0}])
        entry = _entry(diff_contracts(old, new), "quality.id.max_null_percentage")
        assert entry.severity == DiffSeverity.BREAKING

    def test_max_null_percentage_decreased_is_non_breaking(self):
        old = make_contract(quality=[{"column": "id", "max_null_percentage": 5.0}])
        new = make_contract(quality=[{"column": "id", "max_null_percentage": 0.0}])
        entry = _entry(diff_contracts(old, new), "quality.id.max_null_percentage")
        assert entry.severity == DiffSeverity.NON_BREAKING

    def test_max_duplicate_percentage_increased_is_breaking(self):
        old = make_contract(quality=[{"column": "id", "max_duplicate_percentage": 0.0}])
        new = make_contract(quality=[{"column": "id", "max_duplicate_percentage": 10.0}])
        entry = _entry(diff_contracts(old, new), "quality.id.max_duplicate_percentage")
        assert entry.severity == DiffSeverity.BREAKING

    def test_min_value_decreased_is_breaking(self):
        old = make_contract(quality=[{"column": "amount", "min_value": 10.0}])
        new = make_contract(quality=[{"column": "amount", "min_value": 0.0}])
        entry = _entry(diff_contracts(old, new), "quality.amount.min_value")
        assert entry.severity == DiffSeverity.BREAKING

    def test_min_value_increased_is_non_breaking(self):
        old = make_contract(quality=[{"column": "amount", "min_value": 0.0}])
        new = make_contract(quality=[{"column": "amount", "min_value": 10.0}])
        entry = _entry(diff_contracts(old, new), "quality.amount.min_value")
        assert entry.severity == DiffSeverity.NON_BREAKING

    def test_max_value_increased_is_breaking(self):
        old = make_contract(quality=[{"column": "amount", "max_value": 100.0}])
        new = make_contract(quality=[{"column": "amount", "max_value": 200.0}])
        entry = _entry(diff_contracts(old, new), "quality.amount.max_value")
        assert entry.severity == DiffSeverity.BREAKING

    def test_max_value_decreased_is_non_breaking(self):
        old = make_contract(quality=[{"column": "amount", "max_value": 200.0}])
        new = make_contract(quality=[{"column": "amount", "max_value": 100.0}])
        entry = _entry(diff_contracts(old, new), "quality.amount.max_value")
        assert entry.severity == DiffSeverity.NON_BREAKING


class TestMultipleChanges:
    def test_mixed_breaking_and_non_breaking_changes_all_detected(self):
        old = make_contract(
            schema_columns=[
                {"name": "id", "type": "string", "nullable": False},
                {"name": "region", "type": "string"},
            ],
            volume={"min_rows": 1000},
        )
        new = make_contract(
            schema_columns=[
                {"name": "id", "type": "string", "nullable": False},
                {"name": "notes", "type": "string"},
            ],
            volume={"min_rows": 500},
        )
        entries = diff_contracts(old, new)
        by_path = {e.path: e.severity for e in entries}
        assert by_path["schema.columns.region"] == DiffSeverity.BREAKING
        assert by_path["schema.columns.notes"] == DiffSeverity.NON_BREAKING
        assert by_path["volume.min_rows"] == DiffSeverity.BREAKING
