"""Read PDFs. Born-digital pages give text and tables directly, no OCR and no images."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
from PIL import Image

_DROP_CELLS = {"", "$", "%", ")", "(", "-"}


@dataclass
class Page:
    doc: str
    number: int  # 1-based
    text: str
    tables: list[list[list[str]]] = field(default_factory=list)
    scanned: bool = False

    @property
    def content(self) -> str:
        """Text for search and prompts: prose first, then tables as aligned rows."""
        rows = [" | ".join(r) for t in self.tables for r in t]
        return "\n".join([self.text] + rows).strip()


@dataclass
class Document:
    name: str
    pages: list[Page]

    def page(self, number: int) -> Page:
        return self.pages[number - 1]


def clean_row(cells: list[str | None]) -> list[str]:
    out = []
    for c in cells:
        c = (c or "").replace("\n", " ").strip()
        if c not in _DROP_CELLS:
            out.append(c)
    return out


def read_page(doc_name: str, page: pymupdf.Page, number: int) -> Page:
    tables: list[list[list[str]]] = []
    bboxes = []
    try:
        for t in page.find_tables().tables:
            rows = [r for r in (clean_row(r) for r in t.extract()) if r]
            if rows:
                tables.append(rows)
                bboxes.append(pymupdf.Rect(t.bbox))
    except Exception:
        # table finder can fail on odd pages, plain text is still useful
        tables, bboxes = [], []

    blocks = []
    for x0, y0, x1, y1, txt, _no, kind in page.get_text("blocks"):
        if kind != 0 or not txt.strip():
            continue
        r = pymupdf.Rect(x0, y0, x1, y1)
        if any(r.intersects(b) and (r & b).get_area() > 0.5 * r.get_area() for b in bboxes):
            continue
        blocks.append((round(y0), x0, " ".join(txt.split())))
    blocks.sort()
    text = "\n".join(b[2] for b in blocks)

    scanned = len(page.get_text().strip()) < 40 and bool(page.get_images())
    return Page(doc_name, number, text, tables, scanned)


def ingest_pdf(path: str | Path, name: str | None = None, max_pages: int | None = None) -> Document:
    path = Path(path)
    name = name or path.name
    with pymupdf.open(path) as pdf:
        n = len(pdf) if max_pages is None else min(len(pdf), max_pages)
        pages = [read_page(name, pdf[i], i + 1) for i in range(n)]
    return Document(name, pages)


def render_page(path: str | Path, number: int, dpi: int = 170, max_side: int = 1536) -> Image.Image:
    """Page image for the vision model or a thumbnail. Long side is capped at max_side."""
    with pymupdf.open(path) as pdf:
        pix = pdf[number - 1].get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    scale = max_side / max(img.size)
    if scale < 1:
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    return img
