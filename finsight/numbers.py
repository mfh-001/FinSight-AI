"""Turn the many ways a number is written into one float plus an optional unit."""

from __future__ import annotations

import re

NULLS = {"", "null", "none", "n/a", "na", "nil", "-", "--", "not available", "not provided"}

_SCALE_WORDS = {
    "thousand": "thousands", "thousands": "thousands", "k": "thousands",
    "million": "millions", "millions": "millions", "m": "millions", "mm": "millions",
    "billion": "billions", "billions": "billions", "b": "billions", "bn": "billions",
}  # fmt: skip

UNIT_FACTOR = {"units": 1.0, "thousands": 1e3, "millions": 1e6, "billions": 1e9}

_NUM = re.compile(
    r"^\(?\s*(?P<cur>[$€£]|USD|EUR|GBP|SAR|AED)?\s*(?P<neg>-)?\s*(?P<num>\d[\d,]*(?:\.\d+)?|\.\d+)"
    r"\s*(?P<pct>%)?\s*(?P<scale>[a-zA-Z]+)?\s*\)?$"
)


def parse_amount(value) -> tuple[float | None, str | None]:
    """Return (number, unit). unit is set only when the text says it, like '97B'."""
    if value is None:
        return None, None
    if isinstance(value, bool):
        return None, None
    if isinstance(value, (int, float)):
        return float(value), None
    s = str(value).strip()
    if s.lower() in NULLS:
        return None, None
    m = _NUM.match(s.replace("−", "-"))
    if not m:
        return None, None
    num = float(m.group("num").replace(",", ""))
    negative = bool(m.group("neg")) or (s.startswith("(") and s.endswith(")"))
    unit = None
    if m.group("scale"):
        unit = _SCALE_WORDS.get(m.group("scale").lower())
        if unit is None:
            return None, None  # some other word glued to the number
    return (-num if negative else num), unit


def normalize_number(value) -> float | None:
    """Plain float, or None for anything that is not a number. '(565)' gives -565."""
    return parse_amount(value)[0]


def convert(value: float | None, from_unit: str, to_unit: str) -> float | None:
    if value is None:
        return None
    return value * UNIT_FACTOR[from_unit] / UNIT_FACTOR[to_unit]
