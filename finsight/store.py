"""Plain-file storage. One folder per document under FINSIGHT_HOME/docs."""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

from .config import Config
from .ingest import Document, Page, ingest_pdf


class Store:
    def __init__(self, cfg: Config):
        self.root = cfg.home_path / "docs"
        self.root.mkdir(parents=True, exist_ok=True)
        self.retention_days = cfg.retention_days

    def add(self, pdf_path: str | Path, name: str | None = None, max_pages: int | None = None):
        pdf_path = Path(pdf_path)
        name = name or pdf_path.name
        data = pdf_path.read_bytes()
        folder = self.root / (hashlib.sha1(data).hexdigest()[:12])
        folder.mkdir(exist_ok=True)
        src = folder / "source.pdf"
        src.write_bytes(data)
        doc = ingest_pdf(src, name=name, max_pages=max_pages)
        (folder / "pages.json").write_text(json.dumps({
            "name": name,
            "added": time.time(),
            "pages": [
                {"number": p.number, "text": p.text, "tables": p.tables, "scanned": p.scanned}
                for p in doc.pages
            ],
        }))
        return doc

    def _folders(self):
        return [f for f in sorted(self.root.iterdir()) if (f / "pages.json").exists()]

    def load_all(self) -> list[Document]:
        docs = []
        for f in self._folders():
            raw = json.loads((f / "pages.json").read_text())
            pages = [Page(raw["name"], **p) for p in raw["pages"]]
            docs.append(Document(raw["name"], pages))
        return docs

    def pdf_path(self, name: str) -> Path | None:
        for f in self._folders():
            if json.loads((f / "pages.json").read_text())["name"] == name:
                return f / "source.pdf"
        return None

    def delete(self, name: str | None = None) -> int:
        """Delete one document by name, or everything when name is None."""
        n = 0
        for f in self._folders():
            if name is None or json.loads((f / "pages.json").read_text())["name"] == name:
                shutil.rmtree(f)
                n += 1
        return n

    def purge_expired(self) -> int:
        if self.retention_days <= 0:
            return 0
        cutoff = time.time() - self.retention_days * 86400
        n = 0
        for f in self._folders():
            if json.loads((f / "pages.json").read_text())["added"] < cutoff:
                shutil.rmtree(f)
                n += 1
        return n
