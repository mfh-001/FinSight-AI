# Audit of FinSight AI (as found on 2026-10-08)

Findings only. No fixes in this document. Repo commit audited: `12e6317`.
The HF Space (`MFH-001/FinSight-AI`) was checked through the public Hugging Face API.

How I checked: I read every file, parsed every notebook cell and its saved output, and
compared the shipped JSON with the real Apple FY2023 10-K from SEC EDGAR. I rendered the
filing to PDF with headless Chrome (74 pages) and read the numbers with PyMuPDF.
Page numbers differ from the Kaggle run (weasyprint gave 107 pages), so I checked facts, not page ids.
I could not run the models: this machine is an Apple M1 with 8 GB RAM and no CUDA GPU.

## 1. What it does today

| Step | What | Where |
|---|---|---|
| Get filings | Downloads Apple and Microsoft 10-K HTML from SEC and converts to PDF with weasyprint (JPMorgan URL returned 404) | notebook cell 4 |
| PDF to images | PyMuPDF at 150 DPI, one RGB image per page (1241x1754 px) | cell 5 |
| Index | ColPali v1.2, fp16, about 1000 patch vectors per page, saved to `doc_index.pt` (55 MB) | cells 6, 7 |
| Retrieve | MaxSim over all pages, top-k | cell 8 |
| Read a page | Qwen2-VL-7B-Instruct, 4-bit NF4, one page image plus a prompt, greedy decoding | cells 9, 10 |
| Extract | One JSON prompt per retrieved page, fixed to Apple 10-K | cell 11 |
| Risk | One prompt per page, 8 checks, model writes level, score and flags | cell 12 |
| End to end | `finsight_pipeline(pdf, query)` | cell 13 |
| Demo | `app.py` Streamlit page that shows saved JSON | `app.py` |

Inputs: a PDF path (hardcoded to `/kaggle/working/docs/...`) and a text query.
Outputs: JSON files and a matplotlib PNG.
Hardware used for the saved run: Kaggle 2x T4 (16 GB each). Qwen takes about 6 GB at 4-bit,
ColPali about 6 GB in fp16. The notebook shuttles ColPali in and out of memory for every query.

## 2. The Hugging Face Space

Confirmed, with extra detail.

- It is a Streamlit app (`sdk: streamlit`, 1.32.0) on cpu-basic. It was sleeping when checked.
  The domain `mfh-001-finsight-ai.hf.space` returns 200.
- `app.py` has no upload widget and no model code. It reads `extracted_data.json`,
  `risk_reports.json`, `pipeline_config.json` and `pipeline_results.png` and renders them.
  The Space's `app.py` is byte-identical to the one in this repo.
- The Space README says "Upload it to FinSight. Ask a question about the document."
  That is not possible. The app cannot take a file or a question.
- The banner says "git clone, add model weights, run streamlit run app.py". `app.py` never loads weights,
  so this would do nothing new.
- `app.py` shows a scrolling stock ticker (AAPL +2.34%, NVDA +3.45%, 10Y UST 4.23% and so on).
  These values are hardcoded and fake. They look like live data. This is the worst trust problem in the repo.
- The Space also contains a `Dockerfile` and `src/streamlit_app.py` that is the default Streamlit
  spiral demo. Both are leftovers from the Space template. The SDK is `streamlit`, so they are
  probably unused, but they are confusing.
- The Space card declares `license: mit`. The GitHub repo has no LICENSE file, and GitHub shows no license.

## 3. Correctness of the shipped outputs

Ground truth from the filing (Apple FY2023 10-K, fiscal year ended 2023-09-30):
revenue 383,285 (FY2022 394,328, change -2.80%), operating income 114,301 (margin 29.8%),
net income 96,995, diluted EPS 6.13, cash and equivalents 29,965, operating cash flow 110,543,
total current assets 143,566.

| Claim from the earlier review | Verdict | Detail |
|---|---|---|
| risk_reports says revenue is growing and margin is below norms | Confirmed, but mixed | 7 reports. Page 42 correctly says revenue fell from 394,328 to 383,285. Page 51 says "operating margin is below the industry norms for tech" and "Revenue is growing" as a positive signal. Page 63 says "growing revenue trend". Page 51 is wrong on margin (29.8% is above the 20% tech line the prompt itself uses). |
| README says the decline was "correctly flagged" | Partly true | One of seven reports flags it. Two others say the opposite. The claim is overstated. |
| 6 of 7 risk scores are exactly 50 | Confirmed | Scores are 50, 50, 50, 50, 20, 50, 50. Levels are MEDIUM for six pages and LOW for one. |
| Cash and debt null because of 512px images | Not confirmed as stated | The code never sends 512px. `ask_page` defaults to `max_dim=896` and the extraction call passes 896. The README and `pipeline_config.json` say 512, which is not what ran. The nulls have a more likely cause: the retrieved pages were an equity statement, MD&A and a leases note, not the balance sheet (the model's own summaries say so). Cannot prove without the Kaggle run. 896px on a 1241x1754 page is still low for 10-pt table text. |
| Net income as 96995, "$97,000 million", "97B" | Confirmed | Revenue shows as 383285, "$383,285 million", "383B", "$383 billion". Net income shows as 96995, "$97,000 million", "97B", "$97 billion". No unit field. |
| Some nulls are the string "null" | Confirmed | Page 76 has `"total_debt": "null"` and three more. `app.py` has a special case for the string "null", so the author knew. |
| "segment data" query got the consolidated statements page | Partly confirmed | Page 42 was returned for `segment_data`. The model summary calls it consolidated financial performance, and it extracted revenue 383,285. In Apple's filing the MD&A segment table sits next to the consolidated totals, so this may be reasonable. A proper segment answer was never extracted (no segment fields in the prompt). |
| transformers 4.46.3 "exactly", notebook uses `>=` | Confirmed | Cell 1 pins `transformers>=4.46.3` and `colpali-engine>=0.3.1`. README says exact. Cell 1 also installs torch from the cu118 index after everything else. |
| 4-bit 7B needs "about 14GB" | Confirmed wrong | The notebook log shows Qwen at 5.98 GB on cuda:0 and ColPali at 5.93 GB. The 14 GB figure is the sum of both models plus overhead, and the README in other places says "Qwen2-VL-7B ... ~14GB". `app.py` says "~11GB" for the same model. Three different numbers. |
| Kaggle only, no package, CLI, API, Dockerfile | Confirmed | Uses `kaggle_secrets`, `/kaggle/working`, `os._exit(0)` restart cell, and `!pip` magics. |
| Repo description starts with "inancial" | Confirmed | Repo description: "inancial document intelligence ...". |

New findings that were not in the earlier review:

1. **The extraction prompt contains the answers.** Cell 11 tells the model:
   "Known correct values for FY2023: Total net sales approximately $383 billion, Net income
   approximately $97 billion, EPS diluted approximately $6.13". It also hardcodes "Apple Inc.".
   So the README line "Validated on Apple FY2023 10-K: Revenue Net income EPS" is not a validation.
   The model was given the values. Page 76 (a leases and tax note) still returned "383B" and "97B"
   as revenue and net income. That page does not contain those numbers, so this is the prompt leaking, not reading.
2. **The risk checks are done by the model from one page.** Revenue growth needs two years, margin needs
   two statement lines, debt to equity needs the balance sheet. A single page seldom has them.
   The "risk score" is not computed. Hence the template-looking 50s.
3. **The final end-to-end demo gave a non-answer.** Cell 13 asked "What are the key financial metrics
   and any concerning trends?" and the best page was page 13 (a risk factors page). The answer
   begins "The document does not provide specific financial metrics". Cell 11 had marked page 13
   as an index page and skipped it, so the two cells disagree.
4. **The risk factors query returned nothing.** All four hits were filtered as "TOC/index" by the
   `is_content_page` heuristic, which uses `pytesseract`. So the notebook uses OCR in one place,
   although the README says "no OCR". `pytesseract` and the tesseract binary are not installed in cell 1.
5. **The filings are born-digital.** The PDFs are conversions of SEC HTML, so they have a perfect text layer.
   Text and table extraction with PyMuPDF would be faster and exact. Page images are only needed for scans.
6. **Only Apple was run.** Microsoft was downloaded and never used. JPMorgan 404ed. There is no second
   document in any result.
7. **Retrieval was never evaluated.** There is no question set, no accuracy figure, no latency figure.
   The only numbers are Kaggle log lines: 42 s to index 107 pages, and "8-15 seconds per page" in the README
   (not found in any log).
8. **Secret name mismatch.** Notebook reads `HF_TOKEN_FS`, README says add `HF_TOKEN`.
9. **Config mismatch.** `pipeline_config.json` says ColPali on `cuda:1`, `image_max_dim` 512. The notebook
   loads ColPali on `cuda:0` at first and uses 896.
10. **A 10 GB `state.db` sat in Kaggle's working directory.** Not in the repo, so no impact here.

## 4. Code quality

- Hardcoded paths: every `/kaggle/working/...` path, `cuda:0`, `cuda:1`, `max_memory={0:"7GiB",1:"7GiB"}`.
- Secrets: no token committed. The notebook reads it from Kaggle secrets. The SEC User-Agent header has a personal email address in it (public, but should be configurable).
- Pins: `requirements.txt` has `streamlit==1.32.0` and `Pillow>=9.0.0` only. Nothing pins torch, transformers,
  colpali-engine, bitsandbytes or numpy. `.gitignore` is tiny. Python version is not stated.
- Dead or unused: `io` and `base64` imports in `app.py`, `SKIP_IF_CONTENT_WORDS_BELOW` naming, the unused
  `get_latest_10k_url` and `download_sec_filing_as_pdf`, the unused `download_direct_pdf`, the Microsoft PDF.
  `st.image(use_column_width=True)` is deprecated in newer Streamlit.
- Fragile parsing: `raw.lstrip('```json')` strips characters, not a prefix. It works by accident on
  most outputs. `json.loads` failure returns a stub, with no retry.
- No tests, no CI, no license file, no CHANGELOG, no CONTRIBUTING, no issue templates.
- `app.py` is 400 lines of inline CSS and HTML strings, so it is hard to change.

## 5. Buyer gaps (accounting firm owner, 10 seconds)

- The first line of the README says "multi-modal financial document intelligence system that combines ColPali
  visual retrieval with Qwen2-VL-7B". That means nothing to a non-technical owner.
- No sentence like "ask a question about a PDF, get the answer and the page it came from".
- No way to try their own PDF. The Space only replays one run.
- The only sample is Apple's 10-K. Buyers handle invoices, bank statements and contracts.
- The "disclaimer" at the bottom says the repo is a learning journey and "not production-ready".
  That is honest but it is also the last thing a buyer reads.
- No statement about data privacy, where files go, or how to run on a private server.
- Outputs are JSON. Accountants want a spreadsheet.

## 6. GitHub user gaps (5 minute test)

- `pip install` is not possible. There is no `pyproject.toml`.
- `docker run` is not possible. There is no Dockerfile in the repo.
- "Running locally" in the README runs only the replay page.
- The real pipeline needs Kaggle, a token, and a restart cell.
- No GIF or screenshot of live use at the top. The README opens with a long paragraph and a link.
- No badges, no license, no topics about the use (topics exist: colpali, qwen2-vl, sec-edgar and others).
- The README uses emoji headings and long em-dash prose. The technical write-up is interesting
  (the dependency and memory fixes) and worth keeping under "Design notes".

## 7. What is good and should be kept

- The idea (page-image retrieval for tables) is sound and current.
- The engineering notes about ColPali and transformers version drift are useful to others.
- Real run artifacts exist, which makes an honest "before" for the changelog.
- The related-projects section and the single-author voice.
