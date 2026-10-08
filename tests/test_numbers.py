import pytest

from finsight.numbers import convert, normalize_number, parse_amount


@pytest.mark.parametrize(
    "raw,expected",
    [
        (96995, 96995.0),
        ("96,995", 96995.0),
        ("$383,285", 383285.0),
        ("(565)", -565.0),
        ("(4,106", -4106.0),
        ("-12.5", -12.5),
        ("6.13", 6.13),
        ("12.5%", 12.5),
        ("$97B", 97.0),
        ("$97,000 million", 97000.0),
        ("null", None),
        ("N/A", None),
        ("", None),
        (None, None),
        ("abc", None),
        ("12 apples", None),
    ],
)
def test_normalize(raw, expected):
    assert normalize_number(raw) == expected


def test_unit_is_reported():
    assert parse_amount("$97 billion") == (97.0, "billions")
    assert parse_amount("383,285") == (383285.0, None)


def test_convert():
    assert convert(383285, "millions", "billions") == pytest.approx(383.285)
    assert convert(None, "millions", "units") is None
