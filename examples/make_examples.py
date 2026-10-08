"""Builds the two synthetic example PDFs. The names and numbers are made up."""
from pathlib import Path

import pymupdf

HERE = Path(__file__).parent


def draw_table(page, x, y, rows, widths, row_h=22, bold_first=True):
    for i, row in enumerate(rows):
        x0 = x
        for w, cell in zip(widths, row, strict=True):
            r = pymupdf.Rect(x0, y + i * row_h, x0 + w, y + (i + 1) * row_h)
            page.draw_rect(r, color=(0.5, 0.5, 0.5), width=0.5)
            font = "helv" if not (bold_first and i == 0) else "hebo"
            page.insert_text((r.x0 + 4, r.y1 - 7), str(cell), fontsize=9.5, fontname=font)
            x0 += w
    return y + len(rows) * row_h


def invoice(path):
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 60), "Northwind Supplies Ltd", fontsize=16, fontname="hebo")
    p.insert_text((50, 80), "12 Harbour Road, Example City", fontsize=10)
    lines = [
        "Invoice No: INV-2024-0042",
        "Date: 2024-03-05",
        "Due date: 2024-04-04",
        "Bill to: Contoso Trading LLC",
    ]
    for i, ln in enumerate(lines):
        p.insert_text((50, 120 + i * 16), ln, fontsize=11)
    rows = [
        ["Description", "Qty", "Unit price", "Amount"],
        ["Steel bolts M8 (box of 100)", "40", "4.50", "180.00"],
        ["Mounting brackets", "25", "12.00", "300.00"],
        ["Freight", "1", "75.00", "75.00"],
    ]
    y = draw_table(p, 50, 200, rows, [250, 60, 90, 90])
    for i, ln in enumerate(["Subtotal: $555.00", "Tax: $44.40", "Total due: $599.40"]):
        p.insert_text((330, y + 30 + i * 16), ln, fontsize=11)
    doc.save(path)


def bank_statement(path):
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 60), "First Example Bank", fontsize=16, fontname="hebo")
    head = [
        "Account holder: Jane Doe",
        "Account number: ****4821",
        "Statement period: 2024-01-01 to 2024-01-31",
        "Opening balance: $2,400.00",
        "Closing balance: $2,611.75",
    ]
    for i, ln in enumerate(head):
        p.insert_text((50, 100 + i * 16), ln, fontsize=11)
    rows = [
        ["Date", "Description", "Debit", "Credit", "Balance"],
        ["2024-01-03", "Grocery store", "62.30", "", "2,337.70"],
        ["2024-01-09", "Electric utility", "88.45", "", "2,249.25"],
        ["2024-01-15", "Salary deposit", "", "1,500.00", "3,749.25"],
        ["2024-01-22", "Rent", "1,200.00", "", "2,549.25"],
        ["2024-01-28", "Refund", "", "62.50", "2,611.75"],
    ]
    draw_table(p, 50, 210, rows, [80, 170, 80, 80, 90])
    doc.save(path)


if __name__ == "__main__":
    invoice(HERE / "invoice" / "invoice-synthetic.pdf")
    bank_statement(HERE / "bank_statement" / "statement-synthetic.pdf")
    print("wrote example pdfs")
