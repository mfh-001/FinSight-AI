import pytest
from pydantic import ValidationError

from finsight.schemas import SCHEMAS, BankStatement, IncomeStatement, Invoice


def test_messy_values_become_floats_and_real_nulls():
    s = IncomeStatement(
        revenue="$383,285",
        net_income="96995",
        operating_income="null",
        eps_diluted="6.13",
        cost_of_revenue="(214,137)",
        unit="millions",
    )
    assert s.revenue == 383285.0
    assert s.net_income == 96995.0
    assert s.operating_income is None
    assert s.cost_of_revenue == -214137.0
    assert s.model_dump()["gross_profit"] is None


def test_dump_has_no_string_null():
    d = IncomeStatement(revenue="null").model_dump_json()
    assert '"null"' not in d


def test_bad_unit_rejected():
    with pytest.raises(ValidationError):
        IncomeStatement(unit="lots")


def test_invoice_lines_are_cleaned():
    inv = Invoice(
        total="1,250.50", lines=[{"description": "Widget", "quantity": "2", "amount": "$100"}]
    )
    assert inv.total == 1250.5
    assert inv.lines[0].quantity == 2.0 and inv.lines[0].amount == 100.0


def test_bank_statement_negative_amounts():
    b = BankStatement(
        transactions=[{"date": "2024-01-02", "amount": "(45.10)", "balance": "955.00"}]
    )
    assert b.transactions[0].amount == -45.1


def test_registry():
    assert set(SCHEMAS) == {
        "income_statement",
        "balance_sheet",
        "cash_flow",
        "invoice",
        "bank_statement",
    }
