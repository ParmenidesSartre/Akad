"""A realistic, multi-rule scenario: BNM regulatory classification for an
Islamic financing book.

This isn't testing anything the unit tests for BusinessRuleValidator don't
already cover in isolation — it exists to demonstrate (and pin down) the
thing that actually motivated the feature: a single row can be internally
INCONSISTENT in a way no single-column check would ever catch.

The 90-days-past-due threshold for non-performing classification is the
one universally-documented number here (Basel / BNM / MFRS9 Stage 3) —
everything else (the exact column names, the Shariah profit-recognition
rule) is illustrative of the *shape* of the problem, not a literal BNM
reporting template.
"""
from __future__ import annotations

import pandas as pd

from akad.engine import validate_dataframe
from akad.models.result import OverallStatus
from tests.conftest import make_contract

_RULES = [
    {
        "name": "npf_classification_consistent_with_dpd",
        "expression": "(days_past_due < 90) or (npf_status == 'NON_PERFORMING')",
        "description": (
            "BNM Stage 3 / non-performing financing (NPF) criterion: any account "
            "90+ days past due must be classified non-performing. A mismatch here "
            "means the regulatory submission understates non-performing financing."
        ),
    },
    {
        "name": "ecl_stage_matches_npf_status",
        "expression": "(npf_status != 'NON_PERFORMING') or (ecl_stage == 3)",
        "description": (
            "MFRS9: an account classified non-performing must be credit-impaired "
            "(ECL Stage 3) for provisioning — otherwise expected credit loss is "
            "computed on the wrong basis, distorting capital adequacy figures."
        ),
    },
    {
        "name": "no_profit_recognized_on_npf_accounts",
        "expression": "(npf_status != 'NON_PERFORMING') or (profit_recognized_mtd == 0)",
        "description": (
            "Shariah and BNM guidelines require profit recognition to stop once "
            "a financing account is classified non-performing — continuing to "
            "recognize profit on an NPF account overstates income."
        ),
    },
]


def _make_contract():
    return make_contract(
        schema_columns=[
            {"name": "financing_id", "type": "string", "nullable": False},
            {"name": "days_past_due", "type": "integer", "nullable": False},
            {"name": "npf_status", "type": "string", "nullable": False,
             "allowed_values": ["PERFORMING", "NON_PERFORMING"]},
            {"name": "ecl_stage", "type": "integer", "nullable": False},
            {"name": "profit_recognized_mtd", "type": "float", "nullable": False},
        ],
        business_rules=_RULES,
    )


class TestCompliantBook:
    def test_consistently_classified_accounts_are_compliant(self):
        df = pd.DataFrame({
            "financing_id":          ["F001", "F002", "F003", "F004"],
            "days_past_due":         [0, 45, 120, 95],
            "npf_status":            ["PERFORMING", "PERFORMING", "NON_PERFORMING", "NON_PERFORMING"],
            "ecl_stage":             [1, 2, 3, 3],
            "profit_recognized_mtd": [120.50, 80.00, 0.0, 0.0],
        })
        result = validate_dataframe(df, _make_contract())
        assert result.overall_status == OverallStatus.COMPLIANT
        assert result.failed_clauses == []


class TestSilentMisclassification:
    """The exact failure mode this feature exists for: every column looks
    individually fine, the row is wrong only when you read it as a whole."""

    def test_dpd_past_threshold_but_still_flagged_performing(self):
        df = pd.DataFrame({
            "financing_id":          ["F001", "F005"],
            "days_past_due":         [0, 91],
            "npf_status":            ["PERFORMING", "PERFORMING"],  # stale — should be NON_PERFORMING
            "ecl_stage":             [1, 1],
            "profit_recognized_mtd": [120.50, 64.20],
        })
        result = validate_dataframe(df, _make_contract())
        assert result.overall_status == OverallStatus.BREACH
        failed = {c.clause_target for c in result.failed_clauses}
        assert "npf_classification_consistent_with_dpd" in failed
        # downstream consequences of the same stale flag — caught independently
        assert "ecl_stage_matches_npf_status" not in failed  # this account just never got staged
        assert "no_profit_recognized_on_npf_accounts" not in failed  # likewise

    def test_npf_flagged_correctly_but_provisioning_and_profit_not_updated(self):
        """A worse variant: the status WAS updated, but the two downstream
        consequences of that status (ECL staging, profit recognition) lag
        behind — each is its own distinct compliance breach."""
        df = pd.DataFrame({
            "financing_id":          ["F006"],
            "days_past_due":         [150],
            "npf_status":            ["NON_PERFORMING"],
            "ecl_stage":             [1],       # should be 3 — provisioning is now wrong
            "profit_recognized_mtd": [42.00],    # should be 0 — income is overstated
        })
        result = validate_dataframe(df, _make_contract())
        assert result.overall_status == OverallStatus.BREACH
        failed = {c.clause_target for c in result.failed_clauses}
        assert failed == {"ecl_stage_matches_npf_status", "no_profit_recognized_on_npf_accounts"}
        assert "npf_classification_consistent_with_dpd" not in failed  # this one IS correct
