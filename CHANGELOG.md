# Changelog

## 0.2.0 (unreleased)

First version that runs outside Kaggle.

- New `finsight` package and command line: `ingest`, `ask`, `extract`, `risk`, `eval`, `serve`.
- Born-digital PDFs are read with PyMuPDF (text and tables). Page images are only made for scanned
  pages or the vision model, at a long side of 1536 px by default. They are never shrunk to 512 px.
- Retrieval: BM25 over page text, optionally ColPali, joined with reciprocal rank fusion.
- Answers cite `[file.pdf p.N]` and say "not found in the documents" instead of guessing.
- Backends: none (retrieval only), any OpenAI-compatible server (vLLM, llama.cpp, Ollama), or a
  local transformers model. The Qwen2-VL-7B baseline is still supported.
- Extraction schemas: income statement, balance sheet, cash flow, invoice, bank statement.
  Numbers are plain floats with a unit and currency. Missing values are real nulls. Export to CSV and XLSX.
- Risk checklist: the same 8 checks as before, but ratios and flags are computed in Python from the
  extracted numbers and each flag shows the numbers and the page. A model can only write the summary.
  This fixes the old output that said Apple revenue was growing. Apple FY2023 revenue fell 2.8%.
- 49 hand-checked questions on two public SEC filings, with a script that reports accuracy,
  citation hits and speed.
- Gradio app with upload, page thumbnails, Excel export and the risk tab.
- Dockerfile and docker-compose with a CPU profile and an optional vLLM GPU profile.

Moved, not deleted:

- `FinSight_Development.ipynb` is now in `notebooks/original/`.
- The Streamlit replay page and the saved Kaggle outputs are in `legacy/`. The replay page lost its
  hardcoded stock ticker because those numbers were invented.
- The original README text is in `legacy/README_original.md` and in the README under "Design notes".
