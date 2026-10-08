import pymupdf
import pytest


def make_pdf(path, pages):
    """pages: dicts with 'text' lines and optional 'table' rows drawn with ruling lines."""
    doc = pymupdf.open()
    for spec in pages:
        page = doc.new_page()
        y = 60
        for line in spec.get("text", []):
            page.insert_text((50, y), line, fontsize=11)
            y += 18
        rows = spec.get("table", [])
        if rows:
            y += 20
            cw, rh = 95, 22
            ncol = len(rows[0])
            for i, row in enumerate(rows):
                for j, cell in enumerate(row):
                    r = pymupdf.Rect(50 + j * cw, y + i * rh, 50 + (j + 1) * cw, y + (i + 1) * rh)
                    page.draw_rect(r, color=(0, 0, 0), width=0.5)
                    page.insert_text((r.x0 + 4, r.y1 - 6), str(cell), fontsize=10)
            assert ncol
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def sample_pdf(tmp_path):
    return make_pdf(
        tmp_path / "acme-report.pdf",
        [
            {"text": ["Acme Corp annual report", "The company sells widgets worldwide."]},
            {
                "text": ["CONSOLIDATED STATEMENTS OF OPERATIONS", "(In millions)"],
                "table": [
                    ["", "2023", "2022"],
                    ["Total net sales", "1,200", "1,000"],
                    ["Operating income", "240", "200"],
                    ["Net income", "(30)", "150"],
                ],
            },
            {"text": ["Risk factors", "Supply chain disruption could hurt results."]},
        ],
    )
