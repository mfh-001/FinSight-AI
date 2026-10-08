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


def _best_lines(question: str, page_text: str, n: int = 3) -> list[str]:
    q = set(tokenize(question))
    scored = []
    for line in page_text.splitlines():
        t = set(tokenize(line))
        if t & q:
            scored.append((len(t & q), -len(line), line.strip()))
    scored.sort(reverse=True)
    return [s[2] for s in scored[:n]]


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
        lines = _best_lines(question, retriever.page(top.doc, top.page).content)
        text = "\n".join(lines) + f" [{top.doc} p.{top.page}]"
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
