from __future__ import annotations

import pandas as pd

from akad.models.contract import DataContract
from akad.models.result import ClauseResult, ClauseStatus
from akad.validators.base import Validator


class BusinessRuleValidator(Validator):
    """Evaluates cross-column/conditional rules expressed as pandas boolean
    expressions — e.g. "status != 'COMPLETED' or ship_date.notnull()" or
    "end_date >= start_date". A rule passes only if every row satisfies it.

    Expressions run through pandas' own restricted expression grammar
    (df.eval(..., engine="python")), not Python's builtin eval() — it has no
    access to builtins, imports, or arbitrary function calls. As with every
    other contract field, the expression text is assumed to come from a
    trusted contract author, not untrusted end-user input.
    """

    def validate(
        self,
        df: pd.DataFrame,
        contract: DataContract,
        _reader_last_modified: float | None,
    ) -> list[ClauseResult]:
        results: list[ClauseResult] = []
        if df.empty:
            return results

        for rule in contract.business_rules:
            try:
                mask = df.eval(rule.expression, engine="python")
            except Exception as exc:
                results.append(ClauseResult(
                    clause_type="business_rule.error",
                    clause_target=rule.name,
                    status=ClauseStatus.ERROR,
                    expected="expression to evaluate against every row",
                    observed=f"evaluation failed: {exc}",
                    message=f'Business rule "{rule.name}" failed to evaluate: {exc}',
                ))
                continue

            violations = int((~mask).sum())
            suffix = f" — {rule.description}" if rule.description else ""
            results.append(ClauseResult.check(
                "business_rule", rule.name, violations == 0,
                expected="0 violating rows", observed=f"{violations} violating row(s)",
                fail_message=f'Business rule "{rule.name}" violated by {violations} row(s){suffix}',
            ))

        return results
