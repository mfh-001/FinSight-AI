"""Gradio app: upload PDFs, ask with page citations, extract to XLSX, run the risk check."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

import gradio as gr

from .config import Config
from .engine import Engine
from .export import write_xlsx
from .extract import extract_statements
from .ingest import render_page
from .schemas import SCHEMAS

UPLOAD_PAGE_LIMIT = 20


def _find(rel: str) -> Path:
    """Repo folders sit next to the package in a checkout, or in the working dir in Docker."""
    here = Path(__file__).resolve().parent.parent
    for base in (Path(os.environ.get("FINSIGHT_ASSETS", ".")), Path.cwd(), here):
        if (base / rel).exists():
            return base / rel
    return here / rel


SAMPLES = {
    "Apple 10-K FY2023 (public SEC filing)": _find("samples") / "apple-10k-fy2023.pdf",
    "Nathan's Famous 10-K FY2025 (public SEC filing)": _find("samples") / "nathans-10k-fy2025.pdf",
}
RECORDED = _find("legacy/recorded_run")


class Session:
    """One visitor. Files live in a temp folder that is removed when the session ends.

    With FINSIGHT_PERSIST=1 the app uses the shared FINSIGHT_HOME instead and keeps the files,
    which suits a firm server where everyone sees the same document library.
    """

    def __init__(self, cfg: Config):
        self.persist = os.environ.get("FINSIGHT_PERSIST", "") in ("1", "true", "yes")
        self.tmp = str(cfg.home_path) if self.persist else tempfile.mkdtemp(prefix="finsight-")
        self.engine = Engine(replace(cfg, home=self.tmp))

    def close(self) -> None:
        if not self.persist:
            shutil.rmtree(self.tmp, ignore_errors=True)


def _new_session(cfg: Config) -> Session:
    return Session(cfg)


def build_app(cfg: Config | None = None) -> gr.Blocks:
    cfg = cfg or Config.load()
    sample_names = [n for n, p in SAMPLES.items() if p.exists()]

    def load_docs(files, samples, state: Session | None):
        state = state or _new_session(cfg)
        notes = []
        for f in files or []:
            doc = state.engine.add(f, name=Path(f).name, max_pages=UPLOAD_PAGE_LIMIT)
            notes.append(
                f"{doc.name}: read {len(doc.pages)} pages (upload limit {UPLOAD_PAGE_LIMIT})"
            )
        for s in samples or []:
            doc = state.engine.add(SAMPLES[s], name=SAMPLES[s].name)
            notes.append(f"{doc.name}: {len(doc.pages)} pages")
        names = [d.name for d in state.engine.documents()]
        status = "\n".join(notes) or "Nothing loaded yet."
        return state, status, gr.update(choices=names, value=names[0] if names else None)

    def ask(question, doc_choice, state: Session | None):
        if state is None or not state.engine.documents():
            raise gr.Error("Load a PDF or pick a sample first.")
        if not question.strip():
            raise gr.Error("Type a question.")
        ans = state.engine.ask(question, None if doc_choice == "All" else doc_choice)
        if ans.mode == "retrieval-only":
            note = (
                "This server has no language model, so it shows the best matching lines from the "
                "cited page. Written answers and reading scanned pages or charts need a GPU or a "
                "local run, see the README."
            )
        elif ans.mode == "model":
            note = f"Answered by {state.engine.backend.name}."
        else:
            note = ""
        text = f"### {ans.text}\n\n_{note}_" if ans.mode != "model" else f"{ans.text}\n\n_{note}_"
        thumbs = []
        for d, p in ans.citations:
            path = state.engine.store.pdf_path(d)
            if path:
                thumbs.append((render_page(path, p, 110, 1024), f"{d} p.{p}"))
        cites = "  \n".join(f"- {d} p.{p}" for d, p in ans.citations) or "No source pages."
        return text, thumbs, f"**Sources**\n\n{cites}\n\n_{ans.seconds:.1f} s_"

    def run_extract(schema, doc_choice, state: Session | None):
        if state is None or not state.engine.documents():
            raise gr.Error("Load a PDF or pick a sample first.")
        name = None if doc_choice == "All" else doc_choice
        doc = state.engine.get(name)
        if schema == "financial statements":
            results = extract_statements(doc)
        else:
            got = state.engine.extract(schema, name)
            results = {schema: got} if got is not None else {}
        if not results:
            return {"result": "nothing found for this schema in this document"}, [], None
        rows = [
            [
                sheet,
                k,
                v,
                getattr(m, "unit", ""),
                m.source_pages.get(k) if hasattr(m, "source_pages") else None,
            ]
            for sheet, m in results.items()
            for k, v in m.model_dump().items()
            if not isinstance(v, (dict, list))
        ]
        out = Path(state.tmp) / f"{Path(doc.name).stem}-{schema.replace(' ', '_')}.xlsx"
        write_xlsx(out, results)
        return {k: v.model_dump() for k, v in results.items()}, rows, str(out)

    def run_risk(doc_choice, state: Session | None):
        if state is None or not state.engine.documents():
            raise gr.Error("Load a PDF or pick a sample first.")
        rep = state.engine.risk(None if doc_choice == "All" else doc_choice)
        flags = [
            [f.category, f.severity, f.message, ", ".join(f"{d} p.{p}" for d, p in f.pages)]
            for f in rep.flags
        ]
        ratios = [[k, None if v is None else round(v, 4)] for k, v in rep.ratios.items()]
        head = f"### Risk level {rep.level}, score {rep.score}/100\n\n{rep.summary}"
        return head, flags, ratios

    with gr.Blocks(title="FinSight AI") as demo:
        state = gr.State(None, time_to_live=3600, delete_callback=lambda s: s and s.close())
        gr.Markdown(
            "# FinSight AI\n"
            "Ask questions about financial PDFs and get answers with page citations. "
            "Files stay on this server and are deleted when your session ends. "
            "This free server runs the text path only: it reads born-digital PDFs and shows "
            "the best matching lines with page numbers."
        )
        with gr.Row():
            files = gr.File(
                label=f"Your PDFs (first {UPLOAD_PAGE_LIMIT} pages are read)",
                file_types=[".pdf"],
                file_count="multiple",
            )
            samples = gr.CheckboxGroup(sample_names, label="Or try a sample filing")
        load = gr.Button("Load documents", variant="primary")
        status = gr.Textbox(label="Loaded", interactive=False, lines=2)
        doc_choice = gr.Dropdown(["All"], value="All", label="Search in")

        with gr.Tab("Ask"):
            q = gr.Textbox(
                label="Question", placeholder="What were total net sales in fiscal 2023?"
            )
            ask_btn = gr.Button("Ask")
            answer = gr.Markdown()
            gallery = gr.Gallery(label="Cited pages (click to enlarge)", columns=3, height=360)
            sources = gr.Markdown()
        with gr.Tab("Extract to Excel"):
            schema = gr.Dropdown(
                ["financial statements", *SCHEMAS],
                value="financial statements",
                label="What to extract",
            )
            ex_btn = gr.Button("Extract")
            ex_json = gr.JSON(label="Result")
            ex_table = gr.Dataframe(
                headers=["sheet", "field", "value", "unit", "page"], label="Fields"
            )
            ex_file = gr.File(label="Download XLSX")
        with gr.Tab("Risk check"):
            rk_btn = gr.Button("Run the 8 point check")
            rk_head = gr.Markdown()
            rk_flags = gr.Dataframe(
                headers=["check", "severity", "finding", "pages"], label="Flags"
            )
            rk_ratios = gr.Dataframe(headers=["ratio", "value"], label="Ratios computed in code")
        with gr.Tab("Recorded run (not live)"):
            gr.Markdown(_recorded_md())
        with gr.Tab("Data handling"):
            gr.Markdown(
                "- Uploaded files are copied to a temporary folder for your session only.\n"
                "- They are deleted when the session ends or after one hour.\n"
                "- Nothing is sent to another service unless the server owner has set a remote "
                "model endpoint.\n"
                "- Running it yourself keeps everything on your machine: see the README."
            )

        load.click(load_docs, [files, samples, state], [state, status, doc_choice]).then(
            lambda s: (
                gr.update(choices=["All"] + [d.name for d in s.engine.documents()], value="All")
                if s
                else gr.update()
            ),
            [state],
            [doc_choice],
        )
        ask_btn.click(ask, [q, doc_choice, state], [answer, gallery, sources])
        q.submit(ask, [q, doc_choice, state], [answer, gallery, sources])
        ex_btn.click(run_extract, [schema, doc_choice, state], [ex_json, ex_table, ex_file])
        rk_btn.click(run_risk, [doc_choice, state], [rk_head, rk_flags, rk_ratios])
    return demo


def _recorded_md() -> str:
    head = (
        "This tab replays saved output from the original Kaggle notebook (ColPali v1.2 and "
        "Qwen2-VL-7B on two T4 GPUs). **It is a recording, not live inference.** "
        "Known problems with that run are listed in docs/AUDIT.md."
    )
    f = RECORDED / "extracted_data.json"
    if not f.exists():
        return head
    data = json.loads(f.read_text())
    lines = "\n".join(
        f"- page {d.get('page_number')}: revenue `{d.get('financials', {}).get('revenue')}`, "
        f"net income `{d.get('financials', {}).get('net_income')}`"
        for d in data
    )
    title = "**Extracted values as recorded (page numbers refer to the Kaggle PDF):**"
    return f"{head}\n\n{title}\n\n{lines}"


def launch(config_path: str | None = None, port: int = 7860) -> None:
    cfg = Config.load(config_path)
    auth = os.environ.get("FINSIGHT_AUTH")  # "user:password" turns on basic auth
    kwargs = {"auth": tuple(auth.split(":", 1))} if auth else {}
    host = os.environ.get("FINSIGHT_HOST", "127.0.0.1")
    build_app(cfg).launch(server_name=host, server_port=port, **kwargs)
