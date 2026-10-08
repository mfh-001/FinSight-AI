"""Writes questions.jsonl from the hand-checked table below.

Values were read from the filings by hand. The page lists are filled by searching the
sample PDFs for the number as printed, then every list was reviewed. Re-run to rebuild.
"""
import json
import sys
from pathlib import Path

from finsight.ingest import ingest_pdf

SAMPLES = Path(__file__).parent.parent.parent / "samples"
APPLE, NATH = "apple-10k-fy2023.pdf", "nathans-10k-fy2025.pdf"

# id, doc, question, kind, value, unit, printed form searched for, text answer
Q = [
    ("a01", APPLE, "What were Apple's total net sales in fiscal 2023?", "number", 383285, "millions", "383,285"),
    ("a02", APPLE, "What were Apple's total net sales in fiscal 2022?", "number", 394328, "millions", "394,328"),
    ("a03", APPLE, "What was Apple's net income in fiscal 2023?", "number", 96995, "millions", "96,995"),
    ("a04", APPLE, "What was Apple's diluted earnings per share in fiscal 2023?", "number", 6.13, "units", "6.13"),
    ("a05", APPLE, "What was Apple's operating income in fiscal 2023?", "number", 114301, "millions", "114,301"),
    ("a06", APPLE, "What was Apple's gross margin in dollars for fiscal 2023?", "number", 169148, "millions", "169,148"),
    ("a07", APPLE, "How much did Apple spend on research and development in fiscal 2023?", "number", 29915, "millions", "29,915"),
    ("a08", APPLE, "How much cash and cash equivalents did Apple have at the end of fiscal 2023?", "number", 29965, "millions", "29,965"),
    ("a09", APPLE, "What were Apple's total assets at September 30, 2023?", "number", 352583, "millions", "352,583"),
    ("a10", APPLE, "What were Apple's total liabilities at September 30, 2023?", "number", 290437, "millions", "290,437"),
    ("a11", APPLE, "How much cash did Apple generate from operating activities in fiscal 2023?", "number", 110543, "millions", "110,543"),
    ("a12", APPLE, "How many full-time equivalent employees did Apple have as of September 30, 2023?", "number", 161000, "units", "161,000"),
    ("a13", APPLE, "What were Apple's net sales in Greater China in fiscal 2023?", "number", 72559, "millions", "72,559"),
    ("a14", APPLE, "What were Apple's net sales in the Americas segment in fiscal 2023?", "number", 162560, "millions", "162,560"),
    ("a15", APPLE, "What were Apple's net sales in Japan in fiscal 2023?", "number", 24257, "millions", "24,257"),
    ("a16", APPLE, "How many shares of Apple common stock were outstanding as of October 20, 2023?", "number", 15552752000, "units", "15,552,752,000"),
    ("a17", APPLE, "What was the aggregate market value of Apple stock held by non-affiliates?", "number", 2591165000000, "units", "2,591,165,000,000"),
    ("a18", APPLE, "What were Apple's Services net sales in fiscal 2023?", "number", 85200, "millions", "85,200"),
    ("a19", APPLE, "How many shares did Apple repurchase during 2023?", "number", 471, "millions", "471 million shares"),
    ("a20", APPLE, "How much did Apple pay in dividends and dividend equivalents in fiscal 2023?", "number", 15025, "millions", "15,025"),
    ("a21", APPLE, "On which exchange is Apple's common stock traded?", "text", "Nasdaq", None, "Nasdaq Stock Market"),
    ("a22", APPLE, "What were Apple's iPhone net sales in fiscal 2023?", "number", 200583, "millions", "200,583"),
    ("a90", APPLE, "How much did Apple invest in OpenAI?", "notfound", None, None, None),
    ("a91", APPLE, "What was Microsoft's total revenue in fiscal 2023?", "notfound", None, None, None),
    ("a92", APPLE, "How many bitcoin does Apple hold?", "notfound", None, None, None),
    ("a93", APPLE, "What is the launch price of the Apple Vision Pro?", "notfound", None, None, None),
    ("n01", NATH, "What were Nathan's Famous total revenues in fiscal 2025?", "number", 148182, "thousands", "148,182"),
    ("n02", NATH, "What was Nathan's Famous net income in fiscal 2025?", "number", 24026, "thousands", "24,026"),
    ("n03", NATH, "What was Nathan's Famous diluted net income per share in fiscal 2025?", "number", 5.87, "units", "5.87"),
    ("n04", NATH, "How much cash and cash equivalents did Nathan's Famous have at March 30, 2025?", "number", 27802, "thousands", "27,802"),
    ("n05", NATH, "What were Nathan's Famous total assets at March 30, 2025?", "number", 53476, "thousands", "53,476"),
    ("n06", NATH, "What was Nathan's Famous income from operations in fiscal 2025?", "number", 36497, "thousands", "36,497"),
    ("n07", NATH, "What were Nathan's Famous license royalties in fiscal 2025?", "number", 37418, "thousands", "37,418"),
    ("n08", NATH, "What were Nathan's Famous Branded Products revenues in fiscal 2025?", "number", 91828, "thousands", "91,828"),
    ("n09", NATH, "How much did Nathan's Famous pay in dividends to stockholders in fiscal 2025?", "number", 8172, "thousands", "8,172"),
    ("n10", NATH, "How much net cash did Nathan's Famous provide from operating activities in fiscal 2025?", "number", 25240, "thousands", "25,240"),
    ("n11", NATH, "What was Nathan's Famous long-term debt, net of issuance costs, at March 30, 2025?", "number", 48073, "thousands", "48,073"),
    ("n12", NATH, "What was Nathan's Famous total stockholders' deficit at March 30, 2025?", "number", 16513, "thousands", "16,513"),
    ("n13", NATH, "How many shares of Nathan's Famous common stock were outstanding as of June 5, 2025?", "number", 4089510, "units", "4,089,510"),
    ("n14", NATH, "What was the aggregate market value of Nathan's Famous stock held by non-affiliates?", "number", 229609000, "units", "229,609,000"),
    ("n15", NATH, "How many people did Nathan's Famous employ as of March 30, 2025?", "number", 131, "units", "employed 131 people"),
    ("n16", NATH, "In which state was Nathan's Famous incorporated?", "text", "Delaware", None, "incorporated in Delaware"),
    ("n17", NATH, "Who is named as Chief Executive Officer in the Nathan's Famous certifications?", "text", "Eric Gatoff", None, "Eric Gatoff, Chief Executive Officer"),
    ("n18", NATH, "In which city are Nathan's Famous principal executive offices?", "text", "Jericho", None, "Jericho Plaza"),
    ("n19", NATH, "How much was Nathan's Famous interest expense in fiscal 2025?", "number", 4106, "thousands", "4,106"),
    ("n20", NATH, "What is Nathan's Famous Nasdaq trading symbol?", "text", "NATH", None, 'symbol “NATH'),
    ("n90", NATH, "What is Nathan's Famous market share in Germany?", "notfound", None, None, None),
    ("n91", NATH, "How many bitcoin does Nathan's Famous hold?", "notfound", None, None, None),
    ("n92", NATH, "Did Nathan's Famous acquire Burger King in 2025?", "notfound", None, None, None),
]  # fmt: skip


def main() -> None:
    docs = {n: ingest_pdf(SAMPLES / n) for n in (APPLE, NATH)}
    out = []
    for qid, doc, q, kind, value, unit, find in Q:
        pages = []
        if find:
            pages = [p.number for p in docs[doc].pages if find in p.content]
            if not pages:
                sys.exit(f"{qid}: '{find}' not found in {doc}")
        rec = {"id": qid, "doc": doc, "question": q, "kind": kind, "pages": pages}
        if kind == "number":
            rec.update(value=value, unit=unit)
        elif kind == "text":
            rec["answer"] = value
        out.append(rec)
        print(qid, kind, pages)
    path = Path(__file__).parent / "questions.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in out))
    print(len(out), "questions ->", path)


if __name__ == "__main__":
    main()
