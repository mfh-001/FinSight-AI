"""Page retrieval: BM25 over page text, optional visual retriever, fused with RRF."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from .ingest import Document, Page

_STOP = set(
    "a an and are as at be by did do does for from has have how in is it its of on or "
    "that the this to was were what when which who whose why with".split()
)


def tokenize(text: str) -> list[str]:
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text.lower())  # 383,285 -> 383285
    return [t for t in re.findall(r"[a-z0-9][a-z0-9.]*", text) if t not in _STOP]


@dataclass(frozen=True)
class Hit:
    doc: str
    page: int
    score: float

    @property
    def key(self) -> tuple[str, int]:
        return (self.doc, self.page)


class VisualRetriever(Protocol):
    def search(self, query: str, pages: list[Page], k: int) -> list[Hit]: ...


class BM25:
    def __init__(self, pages: list[Page], k1: float = 1.5, b: float = 0.75):
        self.pages = pages
        self.k1, self.b = k1, b
        self.tf = [Counter(tokenize(p.content)) for p in pages]
        self.len = [sum(c.values()) for c in self.tf]
        self.avg = (sum(self.len) / len(pages)) if pages else 0.0
        df: Counter = Counter()
        for c in self.tf:
            df.update(c.keys())
        n = len(pages)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query: str, k: int = 5) -> list[Hit]:
        q = tokenize(query)
        scored = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for t in q:
                f = tf.get(t, 0)
                if f:
                    norm = f + self.k1 * (1 - self.b + self.b * self.len[i] / (self.avg or 1))
                    s += self.idf[t] * f * (self.k1 + 1) / norm
            if s > 0:
                p = self.pages[i]
                scored.append(Hit(p.doc, p.number, s))
        scored.sort(key=lambda h: -h.score)
        return scored[:k]


def rrf(rankings: list[list[Hit]], k: int = 60) -> list[Hit]:
    """Reciprocal rank fusion. Each ranking is a best-first list of hits."""
    fused: dict[tuple[str, int], float] = {}
    for ranking in rankings:
        for rank, h in enumerate(ranking, start=1):
            fused[h.key] = fused.get(h.key, 0.0) + 1.0 / (k + rank)
    out = [Hit(d, p, s) for (d, p), s in fused.items()]
    out.sort(key=lambda h: (-h.score, h.doc, h.page))
    return out


class Retriever:
    def __init__(self, docs: list[Document], visual: VisualRetriever | None = None):
        self.pages = [p for d in docs for p in d.pages]
        self.bm25 = BM25(self.pages)
        self.visual = visual

    def search(self, query: str, k: int = 4) -> list[Hit]:
        wide = max(k * 3, 10)
        rankings = [self.bm25.search(query, wide)]
        if self.visual is not None:
            rankings.append(self.visual.search(query, self.pages, wide))
        return rrf(rankings)[:k]

    def page(self, doc: str, number: int) -> Page:
        for p in self.pages:
            if p.doc == doc and p.number == number:
                return p
        raise KeyError((doc, number))
