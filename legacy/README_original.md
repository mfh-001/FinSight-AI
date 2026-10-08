# FinSight AI: Financial Document Intelligence Engine

Live Demo: https://huggingface.co/spaces/MFH-001/FinSight-AI

This repository features **FinSight AI**, a multi-modal financial document intelligence system that combines ColPali visual retrieval with Qwen2-VL-7B reasoning to extract structured data and perform autonomous risk analysis from financial PDFs — without OCR, without paid APIs, and without destroying table structure.

> **Related projects:** [MediScan AI](https://github.com/mfh-001/AI-Medical-Assistant) · [PsoriScan AI](https://github.com/mfh-001/PsoriScan-AI) — medical imaging projects that share the same philosophy: open-weight models, deployed systems, no paid APIs.


## Overview

The system provides an end-to-end financial document pipeline:

- **Visual Retrieval:** ColPali v1.2 indexes each PDF page as ~1000 image patch embeddings. MaxSim scoring finds the specific page region matching a query — preserving table layout that OCR destroys.
- **Multi-modal Reasoning:** Qwen2-VL-7B-Instruct reads tables, charts, and financial statements directly from page images. No text extraction step.
- **Structured Extraction:** All financial metrics extracted to JSON — revenue, net income, EPS, margins, debt, cash, FCF.
- **Agentic Risk Analysis:** An autonomous 8-point checklist (LIQUIDITY · MARGINS · GROWTH · DEBT · CASH\_FLOW · ANOMALY · MISSING\_DATA · INCONSISTENCY) applied without being told what to look for.

**Validated on Apple Inc. FY2023 10-K** (107 pages, downloaded from SEC EDGAR):
- Revenue: $383,285 million ✓
- Net Income: $96,995 million ✓
- EPS diluted: $6.13 ✓
- Revenue decline from FY2022 ($394B → $383B) correctly flagged by risk engine ✓


## Why This Is Different From Standard RAG

Most document AI pipelines: **PDF → OCR text → chunk → embed → retrieve → LLM**

The problem: OCR breaks on financial tables. `$383,285` becomes `S383.285` or splits across chunk boundaries. Row and column relationships are destroyed.

FinSight: **PDF → page images → ColPali patch embeddings → MaxSim retrieval → Qwen2-VL reads image directly**

ColPali's late-interaction architecture maps image patches and text query tokens into the same embedding space. The model finds which region of a page is relevant to each query token — not just "which page mentions revenue" but "which page has revenue numbers in a table." Qwen2-VL then reads that page as a human analyst would, with full visual context.


## Engineering Logic

### 1. ColPali Visual Indexing

Each PDF page is converted to a 150 DPI RGB image using PyMuPDF. ColPali v1.2 (PaliGemma-3B backbone with custom projection layer) embeds each page as a set of ~1000 patch vectors (128-dim each):

```
Page image → ~1000 patch embeddings (128-dim each)
Query text → token embeddings (128-dim each)
MaxSim score = Σ max(sim(query_token, page_patches)) over all query tokens
```

This multi-vector representation allows fine-grained matching: a query for "operating margin" finds the specific table cell, not just the page that mentions operating margin in passing.

### 2. Qwen2-VL-7B Reasoning

The retrieved page image is passed directly to Qwen2-VL-7B-Instruct (4-bit NF4 quantisation via BitsAndBytes). The model:

- Reads financial tables natively without preprocessing
- Returns structured JSON with all financial fields
- Handles multi-year comparative tables (correctly attributing FY2023 vs FY2022 values)
- Runs in ~8-15 seconds per page on dual T4 GPU

### 3. Agentic Risk Engine

The risk analysis is not a prompted summary. The model autonomously applies a financial analyst's checklist and decides which flags to raise, at what severity, with specific numbers and recommendations. This is the distinction between a chatbot and an agent.


## Project Challenges & Evolution

Every major challenge encountered during development — solved in the working pipeline:

- **ColPali ↔ Transformers version lock:** `colpali-engine==0.3.1` requires `transformers==4.46.3` exactly. Newer transformers renamed PaliGemma internals (`language_model` attribute), breaking ColPali's `__init__`. Fixed by pinning both packages and using `os.kill(os.getpid(), 9)` for a hard kernel restart to force the running Python process to reload from disk rather than from cached in-memory versions.

- **Device routing on dual GPU:** With Qwen2-VL split across two T4 GPUs via `device_map='auto'`, the default greedy packer put all 14.6GB onto cuda:0, leaving 9.81MB free — enough to allocate exactly nothing. Fixed by `max_memory={0: "7GiB", 1: "7GiB"}` forcing an even split. ColPali then loaded onto cuda:1 (7-8GB free after split) as a co-resident model during retrieval.

- **Float type mismatch in ColPali forward pass:** `processor.process_images()` returns CPU tensors. Moving to GPU with `.to(device=model.device)` silently kept tensors on CPU when `device_map` returned a non-standard device object. Fixed by explicitly iterating the processed dict: `v.to(device='cuda:1', dtype=torch.float16) if torch.is_floating_point(v) else v.to(device='cuda:1')`.

- **Integer token IDs cast to float:** Early dtype fix passed `dtype=torch.float16` to all tensors including `input_ids`. `model.embedding(124.0)` fails — embeddings require integer indices. Fixed by checking `torch.is_floating_point(v)` before casting.

- **OOM during Qwen inference:** Full-resolution 10-K pages (1241×1754px) caused Qwen's vision encoder to attempt 7.33GB allocation. Fixed by resizing to 512px max dimension before passing to Qwen. At 512px, the vision encoder uses ~0.6GB — well within headroom.

- **ColPali finding index pages instead of content pages:** Queries like "risk factors" matched the table of contents (which mentions "risk factors" more times) rather than the actual risk section. Fixed by rewriting queries to match prose content rather than section titles: `'the company faces risk uncertainty may adversely affect'` instead of `'risk factors'`.

- **`del colpali_model` on meta tensor:** Moving a quantised model to CPU before deletion fails when weights are on meta device. Fixed by deleting directly without CPU move — the goal is VRAM eviction, not CPU transfer.


## Live Demo vs Full Pipeline

<img width="2568" height="1036" alt="pipeline_results" src="https://github.com/user-attachments/assets/252f9464-f5a5-4910-835d-a7501adf6df1" />

**Live demo** (Hugging Face Spaces, CPU, always available):
- Shows real outputs from the Apple FY2023 10-K pipeline run
- Correct extracted financials: $383B revenue, $97B net income, $6.13 EPS
- Full risk analysis reports with flag categories, severity ratings, and analyst summaries
- Architecture explanation with ColPali vs RAG comparison
- Raw JSON output from the model

**Full pipeline** (requires GPU, run locally or on Kaggle):
- Upload any financial PDF
- Live ColPali indexing + Qwen2-VL inference
- Requires ~14GB VRAM total (dual T4 or single A10G)
- Run `FinSight_Development.ipynb` on Kaggle (free T4 x2) with GPU enabled


## Tech Stack

- **Retrieval:** ColPali v1.2 (PaliGemma-3B backbone, late-interaction MaxSim)
- **Reasoning:** Qwen2-VL-7B-Instruct (4-bit NF4 via BitsAndBytes)
- **PDF processing:** PyMuPDF (pymupdf)
- **Deployment:** Streamlit, Hugging Face Spaces
- **Infrastructure:** Dual NVIDIA T4 GPU (Kaggle free tier), 7GiB per GPU via `max_memory`
- **Data source:** SEC EDGAR (public, no authentication required)


## 📁 Project Structure

- `app.py` — Streamlit demo application (pre-computed results mode for CPU deployment)
- `FinSight_Development.ipynb` — Full Kaggle development notebook (ColPali indexing, Qwen2-VL extraction, risk analysis, dual-GPU pipeline)
- `requirements.txt` — Dependencies for Hugging Face Spaces
- `extracted_data.json` — Structured financial data extracted from Apple FY2023 10-K
- `risk_reports.json` — Agentic risk analysis reports per page
- `pipeline_results.png` — Pipeline output visualisation
- `pipeline_config.json` — Model configuration and hyperparameters

> **Note:** Model weights (`colpali-v1.2`, `Qwen2-VL-7B-Instruct`) load from Hugging Face Hub at runtime. No weight files are stored in this repository.

## Running Locally

```bash
git clone https://github.com/mfh-001/FinSight-AI
cd FinSight-AI
pip install -r requirements.txt
streamlit run app.py
```

For full GPU inference, run `FinSight_Development.ipynb` on Kaggle:
1. Enable GPU T4 x2 accelerator
2. Enable internet
3. Add `HF_TOKEN` as a Kaggle secret
4. Run all cells in sequence — do not skip Cell 1 (kernel restart required for package pinning)

## Visual Results
The final application features a clean, professional interface. It provides a visual extraction and summary of the input financial document.

<img width="1167" height="582" alt="Screenshot 2026-03-20 at 10 52 41 PM" src="https://github.com/user-attachments/assets/fbe9e838-3ed6-4798-92af-598599c846bc" />

---

## ⚠️ Disclaimer
This repository serves as a showcase of my technical growth and learning journey. The contents are intended strictly for educational and research purposes. All outputs should be treated as conceptual references rather than production-ready solutions.
