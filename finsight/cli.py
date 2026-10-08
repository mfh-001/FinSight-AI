"""finsight command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import Config
from .engine import Engine
from .export import write_csv, write_xlsx
from .extract import extract_statements
from .schemas import SCHEMAS


def _engine(args) -> Engine:
    cfg = Config.load(args.config)
    if args.backend:
        cfg.backend = args.backend
    if args.model:
        cfg.llm_model = args.model
    return Engine(cfg)


def cmd_ingest(args) -> int:
    eng = _engine(args)
    target = Path(args.path)
    files = sorted(target.rglob("*.pdf")) if target.is_dir() else [target]
    if not files:
        print(f"no pdf files in {target}", file=sys.stderr)
        return 1
    for f in files:
        doc = eng.add(f, max_pages=args.max_pages)
        scanned = sum(p.scanned for p in doc.pages)
        note = f", {scanned} scanned pages need a vision model" if scanned else ""
        print(f"{doc.name}: {len(doc.pages)} pages{note}")
    return 0


def cmd_ask(args) -> int:
    eng = _engine(args)
    ans = eng.ask(args.question, args.doc)
    if args.json:
        print(json.dumps({"answer": ans.text, "found": ans.found, "mode": ans.mode,
                          "citations": [f"{d} p.{p}" for d, p in ans.citations],
                          "seconds": round(ans.seconds, 2)}, indent=2))  # fmt: skip
        return 0
    print(ans.text)
    if ans.citations:
        print("\nsources: " + ", ".join(f"{d} p.{p}" for d, p in ans.citations))
    if ans.mode == "retrieval-only":
        print("(no model configured, showing the best matching lines)")
    return 0


def cmd_extract(args) -> int:
    eng = _engine(args)
    if args.schema == "statements":
        results = extract_statements(eng.get(args.doc))
    else:
        got = eng.extract(args.schema, args.doc)
        results = {args.schema: got} if got is not None else {}
    if not results:
        print("nothing found for that schema", file=sys.stderr)
        return 1
    if args.out:
        out = Path(args.out)
        if out.suffix == ".xlsx":
            write_xlsx(out, results)
        elif out.suffix == ".csv":
            write_csv(out, next(iter(results.values())))
        else:
            out.write_text(json.dumps({k: v.model_dump() for k, v in results.items()}, indent=2))
        print(f"wrote {out}")
    else:
        print(json.dumps({k: v.model_dump() for k, v in results.items()}, indent=2))
    return 0


def cmd_risk(args) -> int:
    eng = _engine(args)
    rep = eng.risk(args.doc, use_model=args.explain)
    print(f"risk level {rep.level}, score {rep.score}/100\n")
    for f in rep.flags:
        pages = ", ".join(f"{d} p.{p}" for d, p in f.pages)
        print(f"[{f.severity}] {f.category}: {f.message}" + (f" [{pages}]" if pages else ""))
    print(f"\n{rep.summary}")
    return 0


def cmd_docs(args) -> int:
    for d in _engine(args).documents():
        print(f"{d.name}\t{len(d.pages)} pages")
    return 0


def cmd_delete(args) -> int:
    eng = _engine(args)
    if not args.all and not args.name:
        print("give a document name or --all", file=sys.stderr)
        return 1
    print(f"deleted {eng.delete(None if args.all else args.name)} document(s)")
    return 0


def cmd_eval(args) -> int:
    from .evaluate import run

    return run(args)


def cmd_serve(args) -> int:
    from .app import launch

    launch(args.config, args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="finsight", description="Ask questions about financial PDFs.")
    ap.add_argument("--version", action="version", version=f"finsight {__version__}")
    ap.add_argument("--config", help="yaml settings file, or set FINSIGHT_CONFIG")
    ap.add_argument("--backend", choices=["none", "mock", "openai", "transformers"])
    ap.add_argument("--model", help="model id or name for the chosen backend")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ingest", help="read a pdf or a folder of pdfs")
    p.add_argument("path")
    p.add_argument("--max-pages", type=int)
    p.set_defaults(fn=cmd_ingest)

    p = sub.add_parser("ask", help="ask a question, get an answer with page citations")
    p.add_argument("question")
    p.add_argument("--doc")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_ask)

    p = sub.add_parser("extract", help="extract fields to json, csv or xlsx")
    p.add_argument("--schema", required=True, choices=["statements", *SCHEMAS])
    p.add_argument("--doc")
    p.add_argument("--out", help="file ending in .json, .csv or .xlsx")
    p.set_defaults(fn=cmd_extract)

    p = sub.add_parser("risk", help="run the 8 point risk checklist")
    p.add_argument("--doc")
    p.add_argument("--explain", action="store_true", help="let the model write the summary")
    p.set_defaults(fn=cmd_risk)

    sub.add_parser("docs", help="list ingested documents").set_defaults(fn=cmd_docs)

    p = sub.add_parser("delete", help="delete ingested documents from disk")
    p.add_argument("name", nargs="?")
    p.add_argument("--all", action="store_true")
    p.set_defaults(fn=cmd_delete)

    p = sub.add_parser("eval", help="run the question set and print accuracy")
    p.add_argument("--set", default="eval/questions.jsonl")
    p.add_argument("--docs", default="samples")
    p.add_argument("--out", help="write the results table as markdown")
    p.set_defaults(fn=cmd_eval)

    p = sub.add_parser("serve", help="start the web app")
    p.add_argument("--port", type=int, default=7860)
    p.set_defaults(fn=cmd_serve)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except LookupError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
