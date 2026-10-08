"""Optional visual page retriever (ColPali family). Needs `pip install .[gpu,colpali]`.

Not run in CI. It loads the model on first use and caches page embeddings on disk.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .config import Config
from .ingest import Page, render_page
from .retrieve import Hit


class ColPaliRetriever:
    def __init__(self, cfg: Config, pdf_paths: dict[str, Path]):
        self.cfg = cfg
        self.pdf_paths = pdf_paths
        self.model_id = cfg.visual_retriever
        tag = hashlib.sha1(self.model_id.encode()).hexdigest()[:8]
        self.cache = cfg.home_path / "visual" / tag
        self.cache.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._processor = None

    def _load(self):
        if self._model is not None:
            return
        import torch
        from colpali_engine.models import ColPali, ColPaliProcessor

        device = (
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else "cpu"
        )  # noqa: E501
        # T4 cards have no fast bfloat16, float16 works on every cuda card
        dtype = torch.float16 if device == "cuda" else torch.float32
        self._model = ColPali.from_pretrained(
            self.model_id, torch_dtype=dtype, device_map=device
        ).eval()  # noqa: E501
        self._processor = ColPaliProcessor.from_pretrained(self.model_id)

    def _page_embedding(self, page: Page):
        import torch

        key = hashlib.sha1(f"{page.doc}:{page.number}".encode()).hexdigest()[:16]
        f = self.cache / f"{key}.pt"
        if f.exists():
            return torch.load(f)
        img = render_page(
            self.pdf_paths[page.doc], page.number, self.cfg.render_dpi, self.cfg.max_side
        )  # noqa: E501
        batch = self._processor.process_images([img]).to(self._model.device)
        with torch.no_grad():
            emb = self._model(**batch)[0].cpu().float()
        torch.save(emb, f)
        return emb

    def search(self, query: str, pages: list[Page], k: int) -> list[Hit]:
        import torch

        self._load()
        pages = [p for p in pages if p.doc in self.pdf_paths]
        embs = [self._page_embedding(p) for p in pages]
        q = self._processor.process_queries([query]).to(self._model.device)
        with torch.no_grad():
            qe = self._model(**q).cpu().float()
        scores = self._processor.score_multi_vector(list(qe), embs)[0]
        order = torch.argsort(scores, descending=True)[:k].tolist()
        return [Hit(pages[i].doc, pages[i].number, float(scores[i])) for i in order]
