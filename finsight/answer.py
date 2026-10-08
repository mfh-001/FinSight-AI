"""Question answering with page citations. Cites as [file.pdf p.12]."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from .config import Config
from .ingest import render_page
from .llm import Backend
from .retrieve import Hit, Retriever, tokenize

NOT_FOUND = "not found in the documents"

SYSTEM = (
    "You answer questions about documents using only the pages given. "
    "After every fact, cite the page like [file.pdf p.12]. "
    f"If the pages do not contain the answer, reply exactly: {NOT_FOUND}. "
    "Never guess. Keep numbers exactly as written and say the unit and year."
)

_CITE = re.compile(r"\[([^\[\]]*?\bp\.\s*\d+[^\[\]]*)\]")


@dataclass
class Answer:
    text: str
    found: bool
    citations: list[tuple[str, int]] = field(default_factory=list)
    retrieved: list[Hit] = field(default_factory=list)
    mode: str = "model"  # model, retrieval-only, empty
    seconds: float = 0.0


def parse_citations(text: str) -> list[tuple[str, int]]:
    """Pull (doc, page) pairs out of '[a.pdf p.3]' and '[a.pdf p.3, p.5]'."""
    out: list[tuple[str, int]] = []
    for m in _CITE.finditer(text):
        body = m.group(1)
        doc = re.split(r"\s*,?\s*\bp\.", body, maxsplit=1)[0].strip()
        for n in re.findall(r"\bp\.\s*(\d+)", body):
            pair = (doc, int(n))
            if doc and pair not in out:
                out.append(pair)
    return out


def is_not_found(text: str) -> bool:
    return NOT_FOUND in text.lower()


def build_context(retriever: Retriever, hits: list[Hit], char_budget: int = 9000) -> str:
    blocks, used = [], 0
    for h in hits:
        body = retriever.page(h.doc, h.page).content
        room = max(char_budget - used, 0)
        if room < 300:
            break
        body = body[:room]
        used += len(body)
        blocks.append(f"[{h.doc} p.{h.page}]\n{body}")
    return "\n\n".join(blocks)


def _coverage(question: str, page_text: str, retriever: Retriever) -> float:
    """Share of the question's rare words that the page contains."""
    q = set(tokenize(question))
    if not q:
        return 0.0
    have = set(tokenize(page_text))
    return sum(retriever.idf(t) for t in q & have) / sum(retriever.idf(t) for t in q)


def _sentences(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        out += [s.strip()[:300] for s in re.split(r"(?<=[.;])\s+(?=[A-Z])", line) if s.strip()]
    return out


def _best_lines(question: str, retriever: Retriever, hits: list[Hit], n: int = 3):
    """Best matching lines over the top pages. Returns (page hit, lines)."""
    q = set(tokenize(question))
    best: tuple[float, Hit] | None = None
    per_page: dict[tuple[str, int], list[tuple[float, str]]] = {}
    for h in hits:
        for line in _sentences(retriever.page(h.doc, h.page).content):
            toks = tokenize(line)
            overlap = q & set(toks)
            if overlap:
                # long sentences match by chance, so damp the score by length
                sc = sum(retriever.idf(t) for t in overlap) / (len(toks) ** 0.25)
                per_page.setdefault(h.key, []).append((sc, line.strip()))
                if best is None or sc > best[0]:
                    best = (sc, h)
    if best is None:
        return hits[0], []
    lines = sorted(per_page[best[1].key], key=lambda x: -x[0])[:n]
    return best[1], [ln for _, ln in lines]


def answer_question(
    question: str,
    retriever: Retriever,
    backend: Backend | None,
    cfg: Config,
    pdf_paths: dict[str, str] | None = None,
) -> Answer:
    t0 = time.perf_counter()
    hits = retriever.search(question, cfg.top_k)
    if not hits:
        return Answer(NOT_FOUND, False, [], [], "empty", time.perf_counter() - t0)

    if backend is None:
        top = hits[0]
        if (
            _coverage(question, retriever.page(top.doc, top.page).content, retriever)
            < cfg.min_coverage
        ):
            return Answer(NOT_FOUND, False, [], hits, "retrieval-only", time.perf_counter() - t0)
        top, lines = _best_lines(question, retriever, hits)
        text = "\n".join(f"- {ln}" for ln in lines) + f"\n\n[{top.doc} p.{top.page}]"
        return Answer(text, True, [top.key], hits, "retrieval-only", time.perf_counter() - t0)

    images = None
    if cfg.use_vision and pdf_paths:
        images = [
            render_page(pdf_paths[h.doc], h.page, cfg.render_dpi, cfg.max_side)
            for h in hits[:2]
            if h.doc in pdf_paths
        ]
    user = f"Pages:\n{build_context(retriever, hits)}\n\nQuestion: {question}"
    raw = backend.chat(SYSTEM, user, images, cfg.max_new_tokens)

    if is_not_found(raw):
        return Answer(NOT_FOUND, False, [], hits, "model", time.perf_counter() - t0)

    valid = {h.key for h in hits}
    cites = [c for c in parse_citations(raw) if c in valid]
    if not cites:
        # model forgot to cite, so point at the best page instead of inventing a source
        cites = [hits[0].key]
        raw += f" [{hits[0].doc} p.{hits[0].page}] (citation added from top search hit)"
    return Answer(raw, True, cites, hits, "model", time.perf_counter() - t0)
