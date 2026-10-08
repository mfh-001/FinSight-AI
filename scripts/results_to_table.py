"""Turn result json files into the markdown table used in the README.

    python scripts/results_to_table.py                      # print the held-out table
    python scripts/results_to_table.py --update-readme      # rewrite the table inside README.md

Configs with no result file show "not measured yet".
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = [  # label shown in the table, result file name without .json
    ("Retrieval only (BM25, no model)", "cpu-retrieval-only"),
    ("Qwen2.5-VL-3B, page images", "qwen25vl-3b"),
    ("Qwen2.5-VL-7B AWQ via vLLM, page images", "qwen25vl-7b-awq"),
    ("Qwen2-VL-7B 4-bit (original baseline), BM25 pages", "qwen2vl-7b-bm25"),
    ("Qwen2-VL-7B 4-bit (original baseline), ColPali v1.2 + BM25", "qwen2vl-7b-colpali"),
]
HEAD = (
    "| Config | Exact match | Numeric tolerance | Numeric, text pages only | Citation hit "
    "| Not-in-doc correct | Median s/question | Hardware | Date |\n"
    "|---|---|---|---|---|---|---|---|---|"
)


def fmt(v):
    return "n/a" if v is None else f"{v}%"


def row(label: str, f: Path) -> str:
    if not f.exists():
        return f"| {label} | not measured yet | | | | | | | |"
    s = json.loads(f.read_text())["summary"]
    return (
        f"| {label} | {fmt(s['exact_match_pct'])} | {fmt(s['numeric_tolerance_pct'])} "
        f"| {fmt(s.get('numeric_tolerance_pct_text_pages'))} | {fmt(s['citation_hit_pct'])} "
        f"| {fmt(s['not_found_correct_pct'])} | {s['median_seconds']} | {s['hardware']} | {s['date']} |"
    )


def table(results_dir: Path) -> str:
    return HEAD + "\n" + "\n".join(row(lbl, results_dir / f"{key}.json") for lbl, key in CONFIGS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(ROOT / "eval" / "heldout" / "results"))
    ap.add_argument("--update-readme", action="store_true")
    args = ap.parse_args()
    t = table(Path(args.dir))
    if not args.update_readme:
        print(t)
        return
    readme = ROOT / "README.md"
    s = readme.read_text()
    a, b = "<!-- results:start -->", "<!-- results:end -->"
    i, j = s.index(a) + len(a), s.index(b)
    readme.write_text(s[:i] + "\n" + t + "\n" + s[j:])
    print("updated README.md")


if __name__ == "__main__":
    main()
