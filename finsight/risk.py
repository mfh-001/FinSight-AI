"""The 8 point risk checklist. Ratios and flags are plain Python. A model may write the prose."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from .llm import Backend
from .numbers import UNIT_FACTOR

CATEGORIES = [
    "LIQUIDITY",
    "MARGINS",
    "GROWTH",
    "DEBT",
    "CASH_FLOW",
    "ANOMALY",
    "MISSING_DATA",
    "INCONSISTENCY",
]
_POINTS = {"LOW": 0, "MEDIUM": 10, "HIGH": 25}
_REQUIRED = {
    "income_statement": ["revenue", "revenue_prior", "operating_income", "net_income"],
    "balance_sheet": ["cash", "total_current_assets", "total_current_liabilities", "total_equity"],
    "cash_flow": ["operating_cash_flow", "capital_expenditures"],
}


@dataclass
class Flag:
    category: str
    severity: str  # LOW, MEDIUM, HIGH
    message: str
    numbers: dict[str, float] = field(default_factory=dict)
    pages: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class RiskReport:
    flags: list[Flag]
    ratios: dict[str, float | None]
    score: int
    level: str
    summary: str
    summary_by: str = "code"  # code or model


def _fmt(x: float, unit: str = "") -> str:
    s = f"{x:,.0f}" if abs(x) >= 1000 else f"{x:,.2f}".rstrip("0").rstrip(".")
    return f"{s} {unit}".strip()


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _ratio(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b


class _Ctx:
    """Holds the three statements and looks up values with their page."""

    def __init__(self, statements: dict[str, BaseModel]):
        self.s = statements

    def get(self, stmt: str, name: str):
        m = self.s.get(stmt)
        return None if m is None else getattr(m, name, None)

    def page(self, stmt: str, name: str) -> tuple[str, int] | None:
        m = self.s.get(stmt)
        if m is None or name not in m.source_pages:
            return None
        return (m.document or "", m.source_pages[name])

    def pages(self, *pairs: tuple[str, str]) -> list[tuple[str, int]]:
        out = []
        for stmt, name in pairs:
            p = self.page(stmt, name)
            if p and p not in out:
                out.append(p)
        return out

    def unit(self, stmt: str) -> str:
        m = self.s.get(stmt)
        return getattr(m, "unit", "units") if m else "units"

    def units(self, stmt: str, name: str):
        """Value in raw units (dollars), so values from different statements can be compared."""
        v = self.get(stmt, name)
        return None if v is None else v * UNIT_FACTOR[self.unit(stmt)]


def compute_ratios(statements: dict[str, BaseModel]) -> dict[str, float | None]:
    c = _Ctx(statements)
    inc, bal, cf = "income_statement", "balance_sheet", "cash_flow"
    rev, rev0 = c.get(inc, "revenue"), c.get(inc, "revenue_prior")
    op, op0 = c.get(inc, "operating_income"), c.get(inc, "operating_income_prior")
    ni, ni0 = c.get(inc, "net_income"), c.get(inc, "net_income_prior")
    gp, cost = c.get(inc, "gross_profit"), c.get(inc, "cost_of_revenue")
    if gp is None and rev is not None and cost is not None:
        gp = rev - cost
    ocf, capex = c.get(cf, "operating_cash_flow"), c.get(cf, "capital_expenditures")
    fcf = None if ocf is None or capex is None else ocf - capex
    fcf_raw = None if fcf is None else fcf * UNIT_FACTOR[c.unit(cf)]
    tca, tcl = c.get(bal, "total_current_assets"), c.get(bal, "total_current_liabilities")
    return {
        "revenue_growth": None if rev0 in (None, 0) or rev is None else rev / rev0 - 1,
        "net_income_growth": None if ni0 in (None, 0) or ni is None else ni / ni0 - 1,
        "gross_margin": _ratio(gp, rev),
        "operating_margin": _ratio(op, rev),
        "operating_margin_prior": _ratio(op0, rev0),
        "net_margin": _ratio(ni, rev),
        "current_ratio": _ratio(tca, tcl),
        "debt_to_equity": _ratio(c.get(bal, "total_debt"), c.get(bal, "total_equity")),
        "liabilities_to_assets": _ratio(
            c.get(bal, "total_liabilities"), c.get(bal, "total_assets")
        ),
        "free_cash_flow": fcf,
        "fcf_margin": _ratio(fcf_raw, c.units(inc, "revenue")),
        "cash_conversion": _ratio(c.units(cf, "operating_cash_flow"), c.units(inc, "net_income")),
    }


def analyze(statements: dict[str, BaseModel]) -> RiskReport:
    c = _Ctx(statements)
    r = compute_ratios(statements)
    flags: list[Flag] = []
    inc, bal, cf = "income_statement", "balance_sheet", "cash_flow"
    u = c.unit(inc)

    # LIQUIDITY
    cr = r["current_ratio"]
    if cr is not None:
        sev = "HIGH" if cr < 0.8 else "MEDIUM" if cr < 1.0 else "LOW"
        msg = (
            f"Current ratio is {cr:.2f}. Current assets {_fmt(c.get(bal, 'total_current_assets'))} "
            f"against current liabilities {_fmt(c.get(bal, 'total_current_liabilities'))}."
        )
        flags.append(
            Flag(
                "LIQUIDITY",
                sev,
                msg,
                {
                    "current_ratio": cr,
                    "total_current_assets": c.get(bal, "total_current_assets"),
                    "total_current_liabilities": c.get(bal, "total_current_liabilities"),
                },
                c.pages((bal, "total_current_assets"), (bal, "total_current_liabilities")),
            )
        )

    # MARGINS
    om, om0 = r["operating_margin"], r["operating_margin_prior"]
    if om is not None:
        sev = "HIGH" if om < 0 else "MEDIUM" if om < 0.10 else "LOW"
        msg = f"Operating margin is {_pct(om)}."
        nums = {"operating_margin": om}
        if om0 is not None:
            nums["operating_margin_prior"] = om0
            msg += f" It was {_pct(om0)} the year before."
            if om0 - om > 0.03 and sev == "LOW":
                sev = "MEDIUM"
        flags.append(Flag("MARGINS", sev, msg, nums,
            c.pages((inc, "operating_income"), (inc, "revenue"))))  # fmt: skip

    # GROWTH
    rg = r["revenue_growth"]
    if rg is not None:
        word = "fell" if rg < 0 else "grew"
        sev = "HIGH" if rg < -0.10 else "MEDIUM" if rg < 0 else "LOW"
        msg = (
            f"Revenue {word} {_pct(abs(rg))} from {_fmt(c.get(inc, 'revenue_prior'), u)} "
            f"to {_fmt(c.get(inc, 'revenue'), u)}."
        )
        nums = {"revenue": c.get(inc, "revenue"), "revenue_prior": c.get(inc, "revenue_prior"),
                "revenue_growth": rg}  # fmt: skip
        ng = r["net_income_growth"]
        if ng is not None:
            nums["net_income_growth"] = ng
            msg += f" Net income changed {_pct(ng)}."
            if ng < -0.10 and sev == "LOW":
                sev = "MEDIUM"
        flags.append(
            Flag("GROWTH", sev, msg, nums, c.pages((inc, "revenue"), (inc, "revenue_prior")))
        )

    # DEBT
    de, eq = r["debt_to_equity"], c.get(bal, "total_equity")
    if eq is not None and eq < 0:
        flags.append(Flag("DEBT", "HIGH",
            f"Equity is negative ({_fmt(eq, c.unit(bal))}), so debt to equity is not meaningful.",
            {"total_equity": eq, "total_debt": c.get(bal, "total_debt") or 0.0},
            c.pages((bal, "total_equity"), (bal, "total_debt"))))  # fmt: skip
    elif de is not None:
        sev = "HIGH" if de > 2 else "MEDIUM" if de > 1 else "LOW"
        flags.append(Flag("DEBT", sev,
            f"Debt to equity is {de:.2f}. Debt {_fmt(c.get(bal, 'total_debt'))}, "
            f"equity {_fmt(eq)}.",
            {"debt_to_equity": de, "total_debt": c.get(bal, "total_debt"), "total_equity": eq},
            c.pages((bal, "total_debt"), (bal, "total_equity"))))  # fmt: skip

    # CASH_FLOW
    fcf = r["free_cash_flow"]
    if fcf is not None:
        sev = "HIGH" if fcf < 0 else "LOW"
        flags.append(Flag("CASH_FLOW", sev,
            f"Free cash flow is {_fmt(fcf, c.unit(cf))}: operating cash flow "
            f"{_fmt(c.get(cf, 'operating_cash_flow'))} minus capital spending "
            f"{_fmt(c.get(cf, 'capital_expenditures'))}.",
            {"free_cash_flow": fcf, "operating_cash_flow": c.get(cf, "operating_cash_flow"),
             "capital_expenditures": c.get(cf, "capital_expenditures")},
            c.pages((cf, "operating_cash_flow"), (cf, "capital_expenditures"))))  # fmt: skip

    # ANOMALY
    cc = r["cash_conversion"]
    cc_pages = c.pages((cf, "operating_cash_flow"), (inc, "net_income"))
    if cc is not None and (cc < 0.5 or cc > 2.0):
        flags.append(
            Flag(
                "ANOMALY",
                "MEDIUM",
                f"Operating cash flow is {cc:.2f} times net income, which is unusual.",
                {"cash_conversion": cc},
                cc_pages,
            )
        )
    elif cc is not None:
        flags.append(
            Flag(
                "ANOMALY",
                "LOW",
                f"Operating cash flow is {cc:.2f} times net income, within the usual range.",
                {"cash_conversion": cc},
                cc_pages,
            )
        )

    # MISSING_DATA
    missing = [
        f"{st}.{n}" for st, names in _REQUIRED.items() if st in statements
        for n in names if c.get(st, n) is None
    ]  # fmt: skip
    absent = [st for st in _REQUIRED if st not in statements]
    if missing or absent:
        sev = "HIGH" if len(missing) + 2 * len(absent) >= 4 else "MEDIUM"
        what = ", ".join([f"no {a.replace('_', ' ')} found" for a in absent] + missing)
        flags.append(Flag("MISSING_DATA", sev, f"Could not read: {what}."))
    else:
        flags.append(Flag("MISSING_DATA", "LOW", "All fields needed for the checks were found."))

    # INCONSISTENCY
    bad = []
    ta, tl, te = (c.get(bal, n) for n in ("total_assets", "total_liabilities", "total_equity"))
    if None not in (ta, tl, te) and abs(ta - (tl + te)) > 0.005 * abs(ta):
        bad.append(f"assets {_fmt(ta)} differ from liabilities plus equity {_fmt(tl + te)}")
    rv, cg, gp = c.get(inc, "revenue"), c.get(inc, "cost_of_revenue"), c.get(inc, "gross_profit")
    if None not in (rv, cg, gp) and abs(rv - cg - gp) > 0.005 * abs(rv):
        bad.append(f"revenue minus cost {_fmt(rv - cg)} differs from gross profit {_fmt(gp)}")
    if bad:
        flags.append(
            Flag("INCONSISTENCY", "HIGH", "Numbers do not add up: " + "; ".join(bad) + ".")
        )
    else:
        flags.append(Flag("INCONSISTENCY", "LOW", "Balance sheet and gross profit totals add up."))

    score = min(100, sum(_POINTS[f.severity] for f in flags))
    level = (
        "LOW" if score < 15 else "MEDIUM" if score < 40 else "HIGH" if score < 70 else "CRITICAL"
    )
    return RiskReport(flags, r, score, level, _code_summary(flags, level))


def _code_summary(flags: list[Flag], level: str) -> str:
    worse = [f for f in flags if f.severity in ("HIGH", "MEDIUM")]
    if not worse:
        return f"Risk level {level}. No check raised a medium or high flag."
    parts = " ".join(f"{f.category.title().replace('_', ' ')}: {f.message}" for f in worse[:4])
    return f"Risk level {level}. {parts}"


def explain(report: RiskReport, backend: Backend) -> RiskReport:
    """Ask a model to write 2 or 3 sentences from the flags. It never sets a number or a level."""
    lines = "\n".join(f"- {f.category} {f.severity}: {f.message}" for f in report.flags)
    system = (
        "You are a careful financial analyst. Write 2 or 3 plain sentences summarising the flags. "
        "Use only the facts listed. Do not add numbers, causes or advice that are not listed."
    )
    text = backend.chat(system, f"Risk level: {report.level}\n{lines}", None, 200).strip()
    if text:
        report.summary, report.summary_by = text, "model"
    return report
