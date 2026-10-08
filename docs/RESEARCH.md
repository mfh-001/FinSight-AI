# Research: what sells and what gets stars

Written 2026-10-08. Star counts and README contents were read live from the GitHub API that day.
Buyer needs come from vendor blogs and procurement guides found by web search. Those are marketing
pages, not surveys, so treat them as directional.

## 1. Comparable repos

| Repo | Stars | First screen of README | Quick start | Demo format | Benchmarks | Install |
|---|---|---|---|---|---|---|
| docling | 68.5k | Banner image, 15 badges, one-line "what is", feature list | 1 line, then a 3-line Python snippet or a CLI call | Docs site, no GIF | Not on first screen | `pip install docling` |
| MinerU | 81.3k | Logo, badges, "what's new" | pip or docker, WebUI | Hosted web app, HF demo, Colab | Technical reports | `pip install mineru` |
| marker | 40.3k | Logo, license badges, one-sentence promise | 2 lines (`pip install marker-pdf`, `marker_single file.pdf`) | Playground link, example table with outputs | Bar chart image on first screen (olmocr-bench), per-category tables further down | pip |
| olmOCR | 19.7k | Logo, badges, demo link, 1-line description | pip plus GPU extras, longer | Hosted demo at olmocr.allenai.org | Own benchmark table (olmOCR-Bench, 7k tests, 1.4k docs), cost per million pages | pip, docker |
| kotaemon | 25.8k | One-line pitch, product screenshot, links to 2 live HF Spaces and a Colab | `docker run` one block, or scripts | Live Spaces plus screenshot | None | docker image, pip |
| Unstract | 7.3k | Big title, "turn unstructured documents into structured data", before/after table, GIFs | `./run-platform.sh` | Several GIFs of the UI | None | docker |
| ColPali (illuin) | 2.8k | Paper links, leaderboard badge | pip, short code | HF Space | ViDoRe leaderboard | pip |
| byaldi | 0.9k | Cute logo, "pre-release" warning, needs poppler and flash-attn | 5 or more steps | None | None | pip, system packages |
| RAGFlow | 91.8k | Engine pitch, many topics | not read | not read | not read | not read |
| paperless-ngx | 46.4k | Description is "scan, index and archive" | not read | not read | not read | not read |

What I take from this:

- The biggest repos say what they do in one plain sentence and show an install line within the first screen.
- Self-hosted tools (kotaemon, Unstract) lead with `docker`. Libraries (docling, marker) lead with `pip install`.
- Repos that make a quality claim show a chart or table against named baselines (marker, olmOCR, ColPali). The others make no numeric claim at all.
- Small ColPali wrappers (byaldi) stall at under 1k stars. The setup steps, a "pre-release" warning and a last commit in 2025 all hurt.
- Of the READMEs I read, only Unstract uses GIFs, right under the pitch. Live demos on HF Spaces are common for the mid-size repos.
- Topics are specific (`document-ai`, `rag`, `pdf-converter`, `table-extraction`, `idp`), not brand names.
- Nearly all of them have a license that is easy to see (MIT, Apache-2.0). FinSight has none in the repo today.

Closest competitors for "financial PDF Q&A with extraction":
`Zipstack/unstract` (AGPL, prompt-based extraction, big platform), `katanaml/sparrow` (GPL, vision LLM extraction),
`docling` (parsing only, has XBRL support for financial reports). New small repos in this niche
(for example `parsehawk`, `open-document-intelligence`, `py-idp`) sit at 3 to 160 stars.
So there is room for a small, focused, honest tool, but no repo in the niche has broken out.

## 2. What buyers ask for

From the search results, the same items come up for accounting, legal and lending:

1. **Private or on-prem deployment.** For finance, legal and health, sending client documents to a third-party API is often a non-starter. Legal buyers also ask about data residency and deletion on request.
2. **Every number traced to its source page.** Firms want a path from the extracted figure back to the document, exportable for audit.
3. **Structured output in a fixed schema**, with confidence or a review flag, so a person checks the doubtful cases. Spreadsheet export (XLSX/CSV) is the usual target.
4. **Audit trail.** Timestamped record of what was uploaded, extracted, changed and approved.
5. **Human in the loop.** No silent auto-posting. Low-confidence items go to review.
6. **Scanned and messy documents**, and non-English text (Arabic, French and others show up in the competitor repos).
7. **Batch processing** of folders of invoices and statements.

Not yet verified by me: exact accuracy that buyers expect. Vendor claims of 96 to 99% on standard formats and
80 to 92% on bespoke ones are marketing numbers. This repo will publish only what it measures.

## 3. Patterns that drive stars (from the table above)

- One plain sentence on what it does, in the repo description and the first README line.
- A visual in the first screen: GIF or screenshot of the real thing working.
- A 1 to 3 line quick start (`pip install` or `docker run`).
- A live demo that takes your own file (kotaemon, olmOCR).
- A benchmark with named baselines and honest hardware notes (marker, olmOCR).
- "Runs offline / on your own server" stated early (docling, kotaemon, paperless-ngx).
- Small scope, finished. Active commits. A visible license.
- Contributing guide, issue templates, specific topics.

## 4. Plan (prioritised)

Effort: S under 2 hours, M half a day, L a day or more. Impact is 1 to 3 for each goal.
(a) is my outreach to firms, (b) is GitHub traction.

| # | Item | Effort | (a) | (b) |
|---|---|---|---|---|
| 1 | Fix trust issues: remove fake ticker, relabel replay as "recorded run", fix repo description typo | S | 3 | 2 |
| 2 | Package `finsight/` with config, no Kaggle paths, pinned deps, `pip install -e .` | M | 2 | 3 |
| 3 | Text-layer ingestion with PyMuPDF (page text, tables), render images only when needed, resolution configurable | M | 3 | 2 |
| 4 | Retrieval: BM25 on page text, optional ColPali, fused with reciprocal rank | M | 2 | 2 |
| 5 | Answering with citations `[file p.N]` and "not found in the documents", pluggable backend (mock, transformers, any OpenAI-compatible local server) | M | 3 | 3 |
| 6 | Pydantic schemas (income statement, balance sheet, invoice, bank statement), clean number normalisation, CSV/XLSX export | M | 3 | 2 |
| 7 | Risk checklist with ratios computed in Python and cited pages (fixes the revenue error) | M | 3 | 2 |
| 8 | Tests (CPU, no network, mock model) and CI | M | 1 | 2 |
| 9 | Eval set: 30 or more hand-checked questions on 2 to 3 public filings, script with accuracy, citation hit rate and latency, real results table | L | 3 | 3 |
| 10 | Gradio app: upload, ask, citations with page thumbnails, extraction tab with XLSX, risk tab, bundled samples | L | 3 | 3 |
| 11 | Docker and compose with a CPU profile and an optional vLLM service | M | 3 | 3 |
| 12 | README rewrite: one sentence, GIF, 3 real badges, 3-line quick start, results table, data handling section. Old write-up kept under "Design notes" | M | 3 | 3 |
| 13 | Housekeeping: LICENSE (needs owner's choice), CONTRIBUTING, issue templates, CHANGELOG, topics | S | 1 | 2 |
| 14 | Examples (invoice, bank statement, contract Q&A) and `DEPLOY_FOR_A_TEAM.md` | M | 3 | 1 |
| 15 | Optional later: audit log file (who asked what, which pages), Arabic test, review queue | L | 3 | 1 |

Build order follows section 3 of the task: 2 to 8 first, then 9, then 10 to 12, then 13 to 15. Item 1 goes in
right after the packaging so that the old Space is never described as live inference.

Limits I already know about:

- This machine is an Apple M1 with 8 GB and no CUDA GPU, and Docker is not installed. So: GPU models
  and the Docker build cannot be run here. Their scripts and configs will be written and marked "not measured yet".
- The CPU text path and the eval on it can be measured here.
- A GIF of the real app can be recorded here for the CPU text path only.
