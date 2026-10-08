import pytest

from finsight.answer import Answer
from finsight.evaluate import exact_match, number_matches, numbers_in, score, summarize
from finsight.retrieve import Hit

Q = {
    "id": "x",
    "doc": "d.pdf",
    "kind": "number",
    "value": 383285,
    "unit": "millions",
    "pages": [40],
}


@pytest.mark.parametrize(
    "text,ok",
    [
        ("Total net sales were $383,285 million [d.pdf p.40].", True),
        ("About $383.3 billion.", True),
        ("383,285", True),
        ("It was 394,328 million.", False),
        ("$383 million", False),
        ("not found in the documents", False),
    ],
)
def test_number_matching(text, ok):
    assert number_matches(text, 383285, "millions") is ok


def test_citation_numbers_are_ignored():
    assert numbers_in("sales [apple.pdf p.40]") == []
    assert not number_matches("see [d.pdf p.40]", 40, "units")


def test_sign_is_ignored_for_deficits():
    assert number_matches("a deficit of $16,513 thousand", -16513, "thousands")


def test_exact_match_needs_digits_not_substring():
    assert exact_match("sales 383,285 million", Q)
    assert not exact_match("sales 3832850", Q)
    assert exact_match("The symbol is NATH.", {"kind": "text", "answer": "NATH"})


def mk(text, found=True, cites=(("d.pdf", 40),)):
    return Answer(text, found, list(cites), [Hit("d.pdf", 40, 1.0)], "model", 1.5)


def test_score_answerable():
    r = score(Q, mk("383,285 million [d.pdf p.40]"))
    assert r["exact"] and r["numeric"] and r["citation_hit"] and r["retrieval_hit"]
    wrong = score(Q, mk("1 million [d.pdf p.12]", cites=(("d.pdf", 12),)))
    assert not wrong["numeric"] and not wrong["citation_hit"]


def test_score_not_found_question():
    q = {"id": "n", "doc": "d.pdf", "kind": "notfound", "pages": []}
    assert score(q, mk("not found in the documents", found=False))["correct"]
    assert not score(q, mk("it is 5"))["correct"]


def test_summary_percentages():
    rows = [
        {**score(Q, mk("383,285")), "seconds": 1.0},
        {**score(Q, mk("5", cites=())), "seconds": 3.0},
        {
            **score({"id": "n", "doc": "d", "kind": "notfound", "pages": []}, mk("x", False)),
            "seconds": 2.0,
        },
    ]
    s = summarize(rows)
    assert s["answerable"] == 2 and s["numeric_tolerance_pct"] == 50.0
    assert s["not_found_correct_pct"] == 100.0 and s["median_seconds"] == 2.0


def test_summary_reports_text_pages_separately():
    scanned = {**score(Q, mk("nothing", False)), "scanned": True, "seconds": 1.0}
    ok = {**score(Q, mk("383,285")), "seconds": 1.0}
    s = summarize([ok, scanned])
    assert s["scanned_questions"] == 1
    assert s["numeric_tolerance_pct"] == 50.0 and s["numeric_tolerance_pct_text_pages"] == 100.0
