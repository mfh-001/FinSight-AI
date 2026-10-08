import json

from finsight.extract import (
    extract_statement,
    extract_statements,
    extract_with_model,
    parse_json_object,
)
from finsight.ingest import Document, Page, ingest_pdf
from finsight.llm import MockBackend


def income_doc():
    rows = [
        ["Total net sales", "1,200", "1,000"],
        ["Operating income", "240", "200"],
        ["Net income", "(30)", "150"],
        ["Diluted", "6.13", "6.11"],
        ["Shares used in diluted", "15,744,231", "16,325,819"],
    ]
    head = (
        "Acme Corp\n(Exact name of registrant as specified in its charter)\n"
        "For the fiscal year ended September 30, 2023"
    )
    intro = Page("x.pdf", 1, head)
    stmt = Page("x.pdf", 2, "STATEMENTS OF OPERATIONS (In millions)", tables=[rows])
    return Document("x.pdf", [intro, stmt])


def test_income_statement_from_table_rows():
    s = extract_statement("income_statement", income_doc())
    assert s.revenue == 1200 and s.revenue_prior == 1000
    assert s.net_income == -30 and s.net_income_prior == 150
    assert s.eps_diluted == 6.13
    assert s.unit == "millions"
    assert s.source_pages["revenue"] == 2
    assert s.company == "Acme Corp" and s.period_end == "September 30, 2023"


def test_balance_sheet_debt_is_summed():
    rows = [
        ["Cash and cash equivalents", "100", "90"],
        ["Total current assets", "300", "280"],
        ["Total assets", "900", "800"],
        ["Commercial paper", "50", "40"],
        ["Term debt", "20", "30"],
        ["Total liabilities", "500", "450"],
        ["Total shareholders’ equity", "400", "350"],
    ]
    d = Document("b.pdf", [Page("b.pdf", 1, "BALANCE SHEETS in thousands", tables=[rows])])
    b = extract_statement("balance_sheet", d)
    assert b.cash == 100 and b.total_debt == 70 and b.total_equity == 400
    assert b.unit == "thousands"


def test_no_statement_returns_none():
    d = Document("n.pdf", [Page("n.pdf", 1, "just prose")])
    assert extract_statement("income_statement", d) is None
    assert extract_statements(d) == {}


def test_cash_flow_capex_is_positive():
    rows = [
        ["Net cash provided by operating activities", "25,240", "20,002"],
        ["Purchases of property and equipment, net", "(225", "(313"],
    ]
    d = Document("c.pdf", [Page("c.pdf", 1, "CASH FLOWS", tables=[rows])])
    c = extract_statement("cash_flow", d)
    assert c.operating_cash_flow == 25240 and c.capital_expenditures == 225


def test_real_pdf_roundtrip(sample_pdf):
    s = extract_statements(ingest_pdf(sample_pdf))["income_statement"]
    assert s.revenue == 1200 and s.operating_income == 240


def test_parse_json_object_with_fences():
    assert parse_json_object('Sure:\n```json\n{"a": 1}\n```') == {"a": 1}


def test_model_extraction_retries_once():
    replies = iter(["not json", json.dumps({"vendor": "ACME", "total": "1,250.50", "tax": "null"})])
    b = MockBackend(lambda s, u: next(replies))
    inv = extract_with_model("invoice", [Page("i.pdf", 1, "Invoice")], b)
    assert inv.vendor == "ACME" and inv.total == 1250.5 and inv.tax is None
    assert len(b.calls) == 2


def test_model_extraction_gives_up():
    b = MockBackend("nope")
    assert extract_with_model("invoice", [Page("i.pdf", 1, "x")], b) is None


def test_invoice_rules(tmp_path):
    from conftest import make_pdf

    from finsight.extract import extract_document

    pdf = make_pdf(
        tmp_path / "inv.pdf",
        [
            {
                "text": [
                    "Northwind Supplies Ltd",
                    "Invoice No: INV-2024-0042",
                    "Date: 2024-03-05",
                    "Due date: 2024-04-04",
                    "Subtotal: $1,000.00",
                    "Tax: $80.00",
                    "Total due: $1,080.00",
                ],
                "table": [
                    ["Description", "Qty", "Unit price", "Amount"],
                    ["Steel bolts", "100", "4.00", "400.00"],
                    ["Brackets", "20", "30.00", "600.00"],
                ],
            }
        ],
    )
    inv = extract_document("invoice", ingest_pdf(pdf))
    assert inv.vendor == "Northwind Supplies Ltd"
    assert inv.invoice_number == "INV-2024-0042"
    assert inv.invoice_date == "2024-03-05" and inv.due_date == "2024-04-04"
    assert (inv.subtotal, inv.tax, inv.total) == (1000.0, 80.0, 1080.0)
    assert inv.currency == "USD"
    assert [(i.description, i.amount) for i in inv.lines] == [
        ("Steel bolts", 400.0),
        ("Brackets", 600.0),
    ]


def test_bank_statement_rules(tmp_path):
    from conftest import make_pdf

    from finsight.extract import extract_document

    pdf = make_pdf(
        tmp_path / "bank.pdf",
        [
            {
                "text": [
                    "First Example Bank",
                    "Account holder: Jane Doe",
                    "Account number: ****1234",
                    "Statement period: 2024-01-01 to 2024-01-31",
                    "Opening balance: $1,000.00",
                    "Closing balance: $1,250.00",
                ],
                "table": [
                    ["Date", "Description", "Debit", "Credit", "Balance"],
                    ["2024-01-05", "Coffee shop", "5.00", "", "995.00"],
                    ["2024-01-20", "Salary", "", "255.00", "1,250.00"],
                ],
            }
        ],
    )
    b = extract_document("bank_statement", ingest_pdf(pdf))
    assert b.account_holder == "Jane Doe" and b.account_last4 == "1234"
    assert (b.period_start, b.period_end) == ("2024-01-01", "2024-01-31")
    assert (b.opening_balance, b.closing_balance) == (1000.0, 1250.0)
    assert [t.amount for t in b.transactions] == [-5.0, 255.0]
    assert b.transactions[1].balance == 1250.0
