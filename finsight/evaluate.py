"""Run the question set against the engine and report accuracy, citations and speed."""

from __future__ import annotations

import json
import platform
import re
import statistics
import time
from pathlib import Path

from .answer import Answer, answer_question
from .config import Config
from .llm import make_backend
from .numbers import UNIT_FACTOR
from .retrieve import Retriever
from .store import Store

_NUM = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(thousand|million|billion|trillion|[kmbt]\b)?", re.I)
_SCALE = {"thousand": 1e3, "k": 1e3, "million": 1e6, "m": 1e6, "billion": 1e9, "b": 1e9,
          "trillion": 1e12, "t": 1e12}  # fmt: skip
_CITE = re.compile(r"\[[^\[\]]*\bp\.\s*\d+[^\[\]]*\]")


def numbers_in(text: str) -> list[tuple[float, float | None]]:
    """(value, scale) pairs. scale is None when no scale word follows the number."""
    out = []
    for m in _NUM.finditer(_CITE.sub(" ", text)):
        try:
            v = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        w = m.group(2)
        out.append((v, _SCALE.get(w.lower()) if w else None))
    return out


def number_matches(text: str, value: float, unit: str, tol: float = 0.005) -> bool:
    """True if some number in the text equals the gold value within tol. Sign is ignored."""
    gold_raw = abs(value) * UNIT_FACTOR[unit]
    for v, scale in numbers_in(text):
        candidates = [v * scale] if scale else [v * UNIT_FACTOR[unit], v]
        if any(abs(c - gold_raw) <= tol * gold_raw for c in candidates):
            return True
    return False


def exact_match(text: str, q: dict) -> bool:
    """Gold number printed the same way (digits, commas ignored), or gold string present."""
    flat = _CITE.sub(" ", text).lower().replace(",", "")
    if q["kind"] == "text":
        return q["answer"].lower() in flat
    v = q["value"]
    printed = f"{v:g}" if v != int(v) else str(int(v))
    return re.search(rf"(?<![\d.]){re.escape(printed)}(?![\d])", flat) is not None


def score(q: dict, ans: Answer) -> dict:
    kind = q["kind"]
    res = {
        "id": q["id"],
        "kind": kind,
        "found": ans.found,
        "seconds": ans.seconds,
        "mode": ans.mode,
    }
    retrieved = {h.key for h in ans.retrieved}
    if kind == "notfound":
        res["correct"] = not ans.found
        return res
    gold_pages = {(q["doc"], p) for p in q["pages"]}
    res["retrieval_hit"] = bool(gold_pages & retrieved)
    res["citation_hit"] = bool(gold_pages & set(ans.citations))
    if kind == "number":
        res["numeric"] = ans.found and number_matches(ans.text, q["value"], q["unit"])
    else:
        res["numeric"] = ans.found and exact_match(ans.text, q)
    res["exact"] = ans.found and exact_match(ans.text, q)
    return res


def summarize(rows: list[dict]) -> dict:
    ans = [r for r in rows if r["kind"] != "notfound"]
    nf = [r for r in rows if r["kind"] == "notfound"]

    def pct(xs):
        return round(100 * sum(xs) / len(xs), 1) if xs else None

    return {
        "questions": len(rows),
        "answerable": len(ans),
        "not_in_document": len(nf),
        "exact_match_pct": pct([r["exact"] for r in ans]),
        "numeric_tolerance_pct": pct([r["numeric"] for r in ans]),
        "citation_hit_pct": pct([r["citation_hit"] for r in ans]),
        "retrieval_hit_pct": pct([r["retrieval_hit"] for r in ans]),
        "not_found_correct_pct": pct([r["correct"] for r in nf]),
        "scanned_questions": sum(r.get("scanned", False) for r in ans),
        "numeric_tolerance_pct_text_pages": pct(
            [r["numeric"] for r in ans if not r.get("scanned", False)]
        ),
        "median_seconds": round(statistics.median(r["seconds"] for r in rows), 2),
    }


def load_questions(path: str | Path) -> list[dict]:
    return [json.loads(ln) for ln in Path(path).read_text().splitlines() if ln.strip()]


def hardware() -> str:
    try:
        import torch

        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        mps = torch.backends.mps.is_available()
    except ImportError:
        gpu, mps = None, False
    chip = platform.processor() or platform.machine()
    return f"{platform.system()} {platform.machine()} ({chip})" + (
        f", GPU {gpu}" if gpu else ", Apple GPU (MPS) available" if mps else ", no GPU"
    )


def run_eval(cfg: Config, questions: list[dict], docs_dir: str | Path, label: str = "") -> dict:
    import tempfile

    # a throwaway home so the eval never touches the user's own documents
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Config(**{**cfg.__dict__, "home": tmp})
        store = Store(cfg)
        names = sorted({q["doc"] for q in questions})
        for n in names:
            store.add(Path(docs_dir) / n, name=n)
        docs = store.load_all()
        retriever = Retriever(docs)
        backend = make_backend(cfg)
        rows = []
        t_start = time.perf_counter()
        for q in questions:
            ans = answer_question(q["question"], retriever, backend, cfg)
            rows.append({**score(q, ans), "answer": ans.text[:300]})
        summary = summarize(rows)
    summary.update(
        label=label or cfg.backend,
        backend=cfg.backend,
        model=cfg.llm_model if backend else "",
        hardware=hardware(),
        date=time.strftime("%Y-%m-%d"),
        total_seconds=round(time.perf_counter() - t_start, 1),
    )
    return {"summary": summary, "rows": rows}


def markdown_row(s: dict) -> str:
    return (f"| {s['label']} | {s['exact_match_pct']}% | {s['numeric_tolerance_pct']}% | "
            f"{s['citation_hit_pct']}% | {s['not_found_correct_pct']}% | {s['median_seconds']} s | "
            f"{s['hardware']} | {s['date']} |")  # fmt: skip


TABLE_HEAD = (
    "| Config | Exact match | Numeric tolerance | Citation hit | Not-in-doc correct "
    "| Median s/question | Hardware | Date |\n"
    "|---|---|---|---|---|---|---|---|"
)


def run(args) -> int:
    cfg = Config.load(args.config)
    if args.backend:
        cfg.backend = args.backend
    if args.model:
        cfg.llm_model = args.model
    out = run_eval(cfg, load_questions(args.set), args.docs)
    s = out["summary"]
    print(json.dumps(s, indent=2))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2))
        print(f"wrote {args.out}")
    print("\n" + TABLE_HEAD + "\n" + markdown_row(s))
    return 0
