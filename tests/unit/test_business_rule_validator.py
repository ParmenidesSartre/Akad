"""Tests for BusinessRuleValidator — cross-column/conditional pandas-eval rules."""
from __future__ import annotations

import pandas as pd

from akad.models.result import ClauseStatus
from akad.validators.business_rule_validator import BusinessRuleValidator
from tests.conftest import make_contract


class TestSimpleExpression:
    def test_pass_when_all_rows_satisfy(self):
        df = pd.DataFrame({"amount": [10.0, 20.0, 30.0]})
        contract = make_contract(business_rules=[
            {"name": "positive_amount", "expression": "amount > 0"},
        ])
        results = BusinessRuleValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.PASS

    def test_fail_when_some_rows_violate(self):
        df = pd.DataFrame({"amount": [10.0, -5.0, 30.0]})
        contract = make_contract(business_rules=[
            {"name": "positive_amount", "expression": "amount > 0"},
        ])
        results = BusinessRuleValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.FAIL
        assert "1 violating row" in results[0].observed


class TestCrossColumnExpression:
    def test_pass_when_relationship_holds(self):
        df = pd.DataFrame({"start": [1, 5], "end": [3, 9]})
        contract = make_contract(business_rules=[
            {"name": "end_after_start", "expression": "end >= start"},
        ])
        results = BusinessRuleValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.PASS

    def test_fail_when_relationship_violated(self):
        df = pd.DataFrame({"start": [1, 10], "end": [3, 9]})
        contract = make_contract(business_rules=[
            {"name": "end_after_start", "expression": "end >= start"},
        ])
        results = BusinessRuleValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.FAIL
        assert "1 violating row" in results[0].observed


class TestConditionalExpression:
    def test_null_check_only_applies_when_condition_met(self):
        df = pd.DataFrame({
            "status": ["COMPLETED", "PENDING", "COMPLETED"],
            "ship_date": ["2024-01-01", None, None],
        })
        contract = make_contract(business_rules=[
            {
                "name": "ship_date_required",
                "expression": 'not (status == "COMPLETED" and ship_date.isnull())',
            },
        ])
        results = BusinessRuleValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.FAIL
        assert "1 violating row" in results[0].observed

    def test_description_included_in_failure_message(self):
        df = pd.DataFrame({"amount": [-1.0]})
        contract = make_contract(business_rules=[
            {
                "name": "positive_amount", "expression": "amount > 0",
                "description": "Amounts must never be negative",
            },
        ])
        results = BusinessRuleValidator().validate(df, contract, None)
        assert "Amounts must never be negative" in results[0].message


class TestMultipleRules:
    def test_each_rule_produces_its_own_clause(self):
        df = pd.DataFrame({"amount": [10.0], "start": [1], "end": [5]})
        contract = make_contract(business_rules=[
            {"name": "positive_amount", "expression": "amount > 0"},
            {"name": "end_after_start", "expression": "end >= start"},
        ])
        results = BusinessRuleValidator().validate(df, contract, None)
        assert len(results) == 2
        assert all(r.status == ClauseStatus.PASS for r in results)
        assert {r.clause_target for r in results} == {"positive_amount", "end_after_start"}


class TestMalformedExpression:
    def test_invalid_syntax_becomes_error_not_a_crash(self):
        df = pd.DataFrame({"amount": [10.0]})
        contract = make_contract(business_rules=[
            {"name": "broken", "expression": "this is not valid python !!!"},
        ])
        results = BusinessRuleValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.ERROR
        assert results[0].clause_target == "broken"

    def test_unknown_column_becomes_error_not_a_crash(self):
        df = pd.DataFrame({"amount": [10.0]})
        contract = make_contract(business_rules=[
            {"name": "typo", "expression": "amonut > 0"},
        ])
        results = BusinessRuleValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.ERROR


class TestEdgeCases:
    def test_no_rules_returns_empty(self):
        df = pd.DataFrame({"amount": [10.0]})
        contract = make_contract()
        results = BusinessRuleValidator().validate(df, contract, None)
        assert results == []

    def test_empty_dataframe_returns_empty(self):
        df = pd.DataFrame({"amount": pd.Series([], dtype="float64")})
        contract = make_contract(business_rules=[
            {"name": "positive_amount", "expression": "amount > 0"},
        ])
        results = BusinessRuleValidator().validate(df, contract, None)
        assert results == []

    def test_blocks_unsafe_builtin_access(self):
        df = pd.DataFrame({"amount": [10.0]})
        contract = make_contract(business_rules=[
            {"name": "unsafe", "expression": "__import__('os').system('echo hi') == 0"},
        ])
        results = BusinessRuleValidator().validate(df, contract, None)
        assert results[0].status == ClauseStatus.ERROR
