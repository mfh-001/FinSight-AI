"""Writes eval/heldout/questions.jsonl from the hand-checked table below.

Third filing: Lindsay Corporation 10-K for the year ended 2025-08-31 (farm and road equipment,
a different industry from the dev set). Source:
https://www.sec.gov/Archives/edgar/data/836157/000119312525248751/lnn-20250831.htm

The PDF was printed from the SEC html with headless Chrome. Page 54 (the balance sheet) was then replaced
by a picture of itself at 150 dpi, so it is a simulated scan with no text layer. Questions marked scanned
can only be answered by a model that reads page images.

These questions were written from the filing text before the system was run on them.
Answer logic was frozen before the first run. See eval/README.md.
"""
import json
import sys
from pathlib import Path

from finsight.ingest import ingest_pdf

DOC = "lindsay-10k-fy2025-sim-scan.pdf"
HERE = Path(__file__).parent
SCAN_PAGE = 54

# id, question, kind, value, unit, printed form searched for (None for scanned or not found)
Q = [
    ("h01", "What were Lindsay's total operating revenues in fiscal 2025?", "number", 676368, "thousands", "676,368"),
    ("h02", "What were Lindsay's operating revenues in fiscal 2024?", "number", 607074, "thousands", "607,074"),
    ("h03", "What was Lindsay's gross profit in fiscal 2025?", "number", 210780, "thousands", "210,780"),
    ("h04", "What was Lindsay's operating income in fiscal 2025?", "number", 88124, "thousands", "88,124"),
    ("h05", "What was Lindsay's net earnings in fiscal 2025?", "number", 74052, "thousands", "74,052"),
    ("h06", "What was Lindsay's diluted earnings per share in fiscal 2025?", "number", 6.78, "units", "6.78"),
    ("h07", "What were Lindsay's cash dividends declared per share in fiscal 2025?", "number", 1.45, "units", "1.45"),
    ("h08", "How much interest expense did Lindsay report in fiscal 2025?", "number", 1833, "thousands", "(1,833)"),
    ("h09", "How much interest income did Lindsay report in fiscal 2025?", "number", 7718, "thousands", "7,718"),
    ("h10", "What were Lindsay's total operating expenses in fiscal 2025?", "number", 122656, "thousands", "122,656"),
    ("h11", "How much net cash did Lindsay provide from operating activities in fiscal 2025?", "number", 132910, "thousands", "132,910"),
    ("h12", "How much did Lindsay spend on purchases of property, plant and equipment in fiscal 2025?", "number", 42496, "thousands", "(42,496)"),
    ("h13", "How much did Lindsay pay in dividends in fiscal 2025?", "number", 15748, "thousands", "(15,748)"),
    ("h14", "How much did Lindsay spend repurchasing common shares in fiscal 2025?", "number", 11532, "thousands", "(11,532)"),
    ("h15", "What were the Irrigation segment operating revenues in fiscal 2025?", "number", 568000, "thousands", "568,000"),
    ("h16", "What were the Infrastructure segment operating revenues in fiscal 2025?", "number", 108368, "thousands", "108,368"),
    ("h17", "How many shares of Lindsay common stock were outstanding as of October 21, 2025?", "number", 10804220, "units", "10,804,220"),
    ("h18", "What was the aggregate market value of Lindsay stock held by non-affiliates?", "number", 1435554352, "units", "1,435,554,352"),
    ("h19", "On which stock exchange does Lindsay's common stock trade?", "text", "New York Stock Exchange", None, "New York Stock Exchange"),
    ("h20", "Who is Lindsay's President and Chief Executive Officer?", "text", "Randy A. Wood", None, "Randy A. Wood"),
    ("h21", "Where is Lindsay's global headquarters?", "text", "Omaha", None, "global headquarters in Omaha"),
    ("h22", "Approximately how many stockholders of record did Lindsay have as of October 21, 2025?", "number", 125, "units", "approximately 125 stockholders"),
    ("h23", "What is the aggregate principal amount of Lindsay's unsecured Senior Notes?", "number", 115.0, "millions", "$115.0 million"),
    ("h24", "What fixed annual interest rate do Lindsay's Senior Notes pay?", "number", 3.82, "units", "3.82 percent"),
    ("h25", "When is the principal of Lindsay's Senior Notes due?", "text", "February 19, 2030", None, "February 19, 2030"),
    ("h26", "How much cash and cash equivalents did Lindsay have at August 31, 2025?", "number", 250575, "thousands", None, True),
    ("h27", "What were Lindsay's total assets at August 31, 2025?", "number", 840836, "thousands", None, True),
    ("h28", "What were Lindsay's total liabilities at August 31, 2025?", "number", 307986, "thousands", None, True),
    ("h90", "What were Lindsay's revenues in Saudi Arabia?", "notfound", None, None, None),
    ("h91", "How many bitcoin does Lindsay hold?", "notfound", None, None, None),
    ("h92", "How many Lindsay employees work in Japan?", "notfound", None, None, None),
    ("h93", "What is the value of Lindsay's supply contract with Caterpillar?", "notfound", None, None, None),
]  # fmt: skip


def main() -> None:
    doc = ingest_pdf(HERE / "docs" / DOC)
    out = []
    for row in Q:
        qid, q, kind, value, unit, find = row[:6]
        scanned = len(row) > 6
        pages = []
        if scanned:
            pages = [SCAN_PAGE]
        elif find:
            pages = [p.number for p in doc.pages if find in p.content or find in p.raw]
            if not pages:
                sys.exit(f"{qid}: '{find}' not found in {DOC}")
        rec = {"id": qid, "doc": DOC, "question": q, "kind": kind, "pages": pages}
        if kind == "number":
            rec.update(value=abs(value), unit=unit)
        elif kind == "text":
            rec["answer"] = value
        if scanned:
            rec["scanned"] = True
        out.append(rec)
        print(qid, kind, pages)
    (HERE / "questions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in out))
    print(len(out), "questions")


if __name__ == "__main__":
    main()
