from pathlib import Path

import pytest

from finsight.extract import extract_statements
from finsight.ingest import ingest_pdf
from finsight.llm import MockBackend
from finsight.risk import analyze, compute_ratios, explain
from finsight.schemas import BalanceSheet, CashFlow, IncomeStatement

SAMPLES = Path(__file__).parent.parent / "samples"


def stmts(**over):
    inc = dict(
        revenue=1200, revenue_prior=1000, operating_income=240, operating_income_prior=200,
        net_income=150, net_income_prior=120, unit="millions", document="d.pdf",
        source_pages={"revenue": 5, "revenue_prior": 5, "operating_income": 5, "net_income": 5},
    )  # fmt: skip
    bal = dict(
        cash=100, total_current_assets=300, total_current_liabilities=200, total_assets=900,
        total_liabilities=500, total_equity=400, total_debt=300, unit="millions", document="d.pdf",
        source_pages={"total_current_assets": 6, "total_current_liabilities": 6,
                      "total_equity": 6, "total_debt": 6},
    )  # fmt: skip
    cf = dict(
        operating_cash_flow=200, capital_expenditures=50, unit="millions", document="d.pdf",
        source_pages={"operating_cash_flow": 7, "capital_expenditures": 7},
    )  # fmt: skip
    inc.update(over.get("inc", {}))
    bal.update(over.get("bal", {}))
    cf.update(over.get("cf", {}))
    return {
        "income_statement": IncomeStatement(**inc),
        "balance_sheet": BalanceSheet(**bal),
        "cash_flow": CashFlow(**cf),
    }


def flag(report, cat):
    return next(f for f in report.flags if f.category == cat)


def test_ratio_math():
    r = compute_ratios(stmts())
    assert r["revenue_growth"] == pytest.approx(0.2)
    assert r["operating_margin"] == pytest.approx(0.2)
    assert r["current_ratio"] == pytest.approx(1.5)
    assert r["debt_to_equity"] == pytest.approx(0.75)
    assert r["free_cash_flow"] == 150
    assert r["cash_conversion"] == pytest.approx(200 / 150)


def test_healthy_company_is_low_risk():
    rep = analyze(stmts())
    assert rep.level == "LOW" and rep.score == 0
    assert flag(rep, "GROWTH").severity == "LOW" and "grew" in flag(rep, "GROWTH").message


def test_revenue_decline_is_flagged_with_numbers_and_page():
    rep = analyze(stmts(inc={"revenue": 383285, "revenue_prior": 394328}))
    g = flag(rep, "GROWTH")
    assert g.severity == "MEDIUM" and "fell 2.8%" in g.message
    assert g.numbers["revenue_prior"] == 394328
    assert ("d.pdf", 5) in g.pages


def test_negative_equity_is_high_debt_flag():
    rep = analyze(stmts(bal={"total_equity": -50}))
    assert flag(rep, "DEBT").severity == "HIGH"


def test_missing_statement_is_reported_not_guessed():
    s = stmts()
    del s["balance_sheet"]
    rep = analyze(s)
    assert flag(rep, "MISSING_DATA").severity in ("MEDIUM", "HIGH")
    assert not any(f.category in ("LIQUIDITY", "DEBT") for f in rep.flags)


def test_balance_sheet_mismatch_flagged():
    rep = analyze(stmts(bal={"total_assets": 2000}))
    assert flag(rep, "INCONSISTENCY").severity == "HIGH"


def test_model_only_writes_the_summary():
    rep = analyze(stmts())
    before = (rep.score, rep.level, [f.message for f in rep.flags])
    explain(rep, MockBackend("Looks fine."))
    assert rep.summary == "Looks fine." and rep.summary_by == "model"
    assert (rep.score, rep.level, [f.message for f in rep.flags]) == before


def test_apple_fy2023_from_the_real_filing():
    doc = ingest_pdf(SAMPLES / "apple-10k-fy2023.pdf")
    rep = analyze(extract_statements(doc))
    assert rep.ratios["revenue_growth"] == pytest.approx(383285 / 394328 - 1)
    assert rep.ratios["operating_margin"] == pytest.approx(114301 / 383285)
    g = flag(rep, "GROWTH")
    assert "fell 2.8%" in g.message and g.pages
    m = flag(rep, "MARGINS")
    assert m.severity == "LOW" and "29.8%" in m.message
