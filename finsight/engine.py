"""One object that ties the store, retrieval, answering, extraction and risk together."""

from __future__ import annotations

from pathlib import Path

from .answer import Answer, answer_question
from .config import Config
from .extract import extract_document, extract_statements
from .ingest import Document
from .llm import Backend, make_backend
from .retrieve import Retriever
from .risk import RiskReport, analyze, explain
from .store import Store

_AUTO = object()


class Engine:
    def __init__(self, cfg: Config | None = None, backend=_AUTO):
        self.cfg = cfg or Config.load()
        self.store = Store(self.cfg)
        self.store.purge_expired()
        self.backend: Backend | None = make_backend(self.cfg) if backend is _AUTO else backend
        self._docs: list[Document] | None = None

    # documents
    def add(self, path: str | Path, name: str | None = None, max_pages: int | None = None):
        doc = self.store.add(path, name, max_pages)
        self._docs = None
        return doc

    def documents(self) -> list[Document]:
        if self._docs is None:
            self._docs = self.store.load_all()
        return self._docs

    def get(self, name: str | None) -> Document:
        docs = self.documents()
        if not docs:
            raise LookupError("no documents yet, run: finsight ingest <file or folder>")
        if name is None:
            return docs[0]
        for d in docs:
            if d.name == name or Path(d.name).stem == name:
                return d
        raise LookupError(f"no document named {name}")

    def delete(self, name: str | None = None) -> int:
        self._docs = None
        return self.store.delete(name)

    # questions
    def _pdf_paths(self, docs: list[Document]) -> dict[str, Path]:
        return {d.name: p for d in docs if (p := self.store.pdf_path(d.name))}

    def ask(self, question: str, doc: str | None = None) -> Answer:
        docs = [self.get(doc)] if doc else self.documents()
        if not docs:
            raise LookupError("no documents yet, run: finsight ingest <file or folder>")
        paths = self._pdf_paths(docs)
        visual = None
        if self.cfg.visual_retriever:
            from .visual import ColPaliRetriever

            visual = ColPaliRetriever(self.cfg, paths)
        retriever = Retriever(docs, visual)
        return answer_question(
            question, retriever, self.backend, self.cfg, {k: str(v) for k, v in paths.items()}
        )  # noqa: E501

    # extraction and risk
    def extract(self, schema: str, doc: str | None = None):
        return extract_document(schema, self.get(doc), self.backend)

    def risk(self, doc: str | None = None, use_model: bool = False) -> RiskReport:
        report = analyze(extract_statements(self.get(doc)))
        if use_model and self.backend is not None:
            explain(report, self.backend)
        return report
