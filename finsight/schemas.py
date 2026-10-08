"""Extraction schemas. Numbers are plain floats in the stated unit. Missing means None."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .numbers import normalize_number

Unit = Literal["units", "thousands", "millions", "billions"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")

    @field_validator("*", mode="before")
    @classmethod
    def _clean(cls, v, info):
        # models like to write the string "null" for missing values
        if isinstance(v, str) and v.strip().lower() in ("null", "none", "n/a", ""):
            return None
        if info.field_name in cls._number_fields() and v is not None:
            return normalize_number(v)
        return v

    @classmethod
    def _number_fields(cls) -> set[str]:
        return {n for n, f in cls.model_fields.items() if f.annotation == (float | None)}


class _Statement(_Base):
    company: str | None = None
    period_end: str | None = None
    unit: Unit = "units"
    currency: str | None = "USD"
    # field name -> page number it was read from
    source_pages: dict[str, int] = Field(default_factory=dict)
    document: str | None = None


class IncomeStatement(_Statement):
    revenue: float | None = None
    revenue_prior: float | None = None
    cost_of_revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    operating_income_prior: float | None = None
    net_income: float | None = None
    net_income_prior: float | None = None
    eps_diluted: float | None = None


class BalanceSheet(_Statement):
    cash: float | None = None
    total_current_assets: float | None = None
    total_assets: float | None = None
    total_current_liabilities: float | None = None
    total_liabilities: float | None = None
    total_debt: float | None = None
    total_equity: float | None = None


class CashFlow(_Statement):
    operating_cash_flow: float | None = None
    capital_expenditures: float | None = None  # positive number means cash spent


class InvoiceLine(_Base):
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None


class Invoice(_Base):
    vendor: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    currency: str | None = None
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    lines: list[InvoiceLine] = Field(default_factory=list)


class Transaction(_Base):
    date: str | None = None
    description: str | None = None
    amount: float | None = None  # negative for money out
    balance: float | None = None


class BankStatement(_Base):
    bank: str | None = None
    account_holder: str | None = None
    account_last4: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    currency: str | None = None
    opening_balance: float | None = None
    closing_balance: float | None = None
    transactions: list[Transaction] = Field(default_factory=list)


SCHEMAS: dict[str, type[BaseModel]] = {
    "income_statement": IncomeStatement,
    "balance_sheet": BalanceSheet,
    "cash_flow": CashFlow,
    "invoice": Invoice,
    "bank_statement": BankStatement,
}
