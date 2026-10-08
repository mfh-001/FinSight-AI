from finsight.ingest import clean_row, ingest_pdf, render_page


def test_text_pages(sample_pdf):
    doc = ingest_pdf(sample_pdf)
    assert doc.name == "acme-report.pdf"
    assert len(doc.pages) == 3
    assert "widgets" in doc.page(1).text
    assert not doc.page(1).scanned


def test_table_rows_are_kept_aligned(sample_pdf):
    page = ingest_pdf(sample_pdf).page(2)
    assert page.tables
    assert "Total net sales | 1,200 | 1,000" in page.content


def test_clean_row_drops_currency_cells():
    assert clean_row(["Products", "$", "298,085", None, "", "$", "316,199"]) == [
        "Products",
        "298,085",
        "316,199",
    ]


def test_render_respects_max_side(sample_pdf):
    img = render_page(sample_pdf, 1, dpi=200, max_side=1100)
    assert max(img.size) == 1100
    small = render_page(sample_pdf, 1, dpi=72, max_side=2000)
    assert max(small.size) < 1000


def test_max_pages(sample_pdf):
    assert len(ingest_pdf(sample_pdf, max_pages=2).pages) == 2
