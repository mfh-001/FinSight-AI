import streamlit as st
import json
import os
from PIL import Image
import io
import base64

st.set_page_config(
    page_title="FinSight AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=Syne:wght@400;500;600;700&display=swap');

:root {
  --bg:       #06080f;
  --surface:  #0b1019;
  --surface2: #101620;
  --border:   rgba(148,210,160,0.10);
  --border2:  rgba(148,210,160,0.20);
  --green:    #94d2a0;
  --green-dim:rgba(148,210,160,0.12);
  --amber:    #f0b429;
  --amber-dim:rgba(240,180,41,0.12);
  --red:      #e05c5c;
  --red-dim:  rgba(224,92,92,0.12);
  --text:     #c8d8c8;
  --text-dim: #4a6a4a;
  --text-mute:#2a3a2a;
  --serif:    'DM Serif Display', Georgia, serif;
  --sans:     'Syne', sans-serif;
  --mono:     'DM Mono', monospace;
}

.stApp { background: var(--bg); font-family: var(--sans); color: var(--text); }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.ticker-wrap {
    background: var(--surface); border-bottom: 1px solid var(--border);
    overflow: hidden; padding: 6px 0;
}
.ticker-content {
    white-space: nowrap; animation: ticker 35s linear infinite;
    font-family: var(--mono); font-size: 0.6rem; letter-spacing: 0.08em; color: var(--text-dim);
}
@keyframes ticker { 0% { transform: translateX(100vw); } 100% { transform: translateX(-100%); } }
.ticker-up   { color: #94d2a0; }
.ticker-down { color: #e05c5c; }

.hero { padding: 3.5rem 0 2rem; text-align: center; }
.hero-eyebrow {
    font-family: var(--mono); font-size: 0.65rem; letter-spacing: 0.25em;
    color: var(--green); text-transform: uppercase; margin-bottom: 0.8rem;
    display: flex; align-items: center; justify-content: center; gap: 0.8rem;
}
.hero-eyebrow::before, .hero-eyebrow::after {
    content: ''; width: 50px; height: 1px;
    background: linear-gradient(90deg, transparent, var(--green));
}
.hero-eyebrow::after { background: linear-gradient(90deg, var(--green), transparent); }
.hero h1 {
    font-family: var(--serif); font-size: clamp(3rem, 7vw, 5.5rem);
    font-weight: 400; color: #e8f0e8; letter-spacing: -0.03em; line-height: 1.0; margin: 0;
}
.hero h1 em { font-style: italic; color: var(--green); }
.hero h1 sup { font-family: var(--mono); font-size: 0.28em; color: var(--text-dim);
               letter-spacing: 0.15em; vertical-align: super; }
.hero-sub { font-size: 0.88rem; color: var(--text-dim); margin-top: 0.6rem; line-height: 1.6; }
.hero-badges { display: flex; gap: 0.5rem; justify-content: center; flex-wrap: wrap; margin-top: 1.2rem; }
.badge {
    font-family: var(--mono); font-size: 0.6rem; letter-spacing: 0.1em;
    padding: 0.2rem 0.65rem; border: 1px solid var(--border2); border-radius: 2px;
    color: var(--text-dim); background: var(--surface);
}
.badge.active { border-color: var(--green); color: var(--green); background: var(--green-dim); }

.divider { height: 1px; background: linear-gradient(90deg, transparent, var(--border2), transparent); margin: 1.5rem 0; }

.section-label {
    font-family: var(--mono); font-size: 0.8rem; letter-spacing: 0.22em;
    color: var(--green); text-transform: uppercase; margin-bottom: 0.8rem;
    padding-bottom: 0.4rem; border-bottom: 1px solid var(--border);
}

.card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.4rem; margin: 0.8rem 0; }

.metric-row {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 1px; background: var(--border); border: 1px solid var(--border);
    border-radius: 8px; overflow: hidden; margin: 0.8rem 0;
}
.metric-cell { background: var(--surface); padding: 1rem 0.8rem; text-align: center; }
.metric-val  { font-family: var(--serif); font-size: 1.5rem; color: var(--green); line-height: 1; }
.metric-lbl  { font-family: var(--mono); font-size: 0.55rem; letter-spacing: 0.12em;
               color: var(--text-dim); text-transform: uppercase; margin-top: 0.3rem; }

.risk-pill {
    display: inline-block; font-family: var(--mono); font-size: 0.65rem;
    letter-spacing: 0.12em; text-transform: uppercase; padding: 0.25rem 0.8rem;
    border-radius: 2px;
}
.risk-LOW    { background: rgba(148,210,160,0.15); color: #94d2a0; border: 1px solid rgba(148,210,160,0.3); }
.risk-MEDIUM { background: rgba(240,180,41,0.15);  color: #f0b429; border: 1px solid rgba(240,180,41,0.3); }
.risk-HIGH   { background: rgba(224,92,92,0.15);   color: #e05c5c; border: 1px solid rgba(224,92,92,0.3); }

.flag-row {
    padding: 0.6rem 0.8rem; margin: 0.3rem 0;
    border-left: 2px solid; border-radius: 0 6px 6px 0;
    background: var(--surface2);
}
.flag-HIGH   { border-color: #e05c5c; }
.flag-MEDIUM { border-color: #f0b429; }
.flag-LOW    { border-color: #94d2a0; }

.answer-box {
    background: var(--surface2); border: 1px solid var(--border);
    border-left: 3px solid var(--green); border-radius: 0 8px 8px 0;
    padding: 1.2rem 1.5rem; margin: 0.8rem 0;
    font-size: 0.88rem; line-height: 1.75; color: var(--text);
}

.gpu-banner {
    background: var(--amber-dim); border: 1px solid rgba(240,180,41,0.25);
    border-radius: 8px; padding: 1rem 1.5rem; margin: 1rem 0;
    font-size: 0.82rem; color: var(--text); line-height: 1.6;
}

.arch-box {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 1.5rem; margin: 0.8rem 0;
    font-family: var(--mono); font-size: 0.72rem; color: var(--text-dim); line-height: 1.9;
}

.stTabs [data-baseweb="tab-list"] {
    background: transparent; border-bottom: 1px solid var(--border); gap: 0;
}
.stTabs [data-baseweb="tab"] {
    font-family: var(--mono); font-size: 0.65rem; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--text-dim) !important;
    padding: 0.6rem 1.2rem; border-bottom: 2px solid transparent;
}
.stTabs [aria-selected="true"] {
    color: var(--green) !important; border-bottom-color: var(--green);
    background: transparent;
}
.stButton > button {
    background: var(--green-dim) !important; border: 1px solid var(--green) !important;
    color: var(--green) !important; border-radius: 4px !important;
    font-family: var(--mono) !important; font-size: 0.68rem !important;
    letter-spacing: 0.12em !important; text-transform: uppercase !important;
}
</style>
""", unsafe_allow_html=True)

# ── Ticker
st.markdown("""
<div class="ticker-wrap"><div class="ticker-content">
  <span style="margin-right:3rem">AAPL <span class="ticker-up">▲ 2.34%</span></span>
  <span style="margin-right:3rem">MSFT <span class="ticker-up">▲ 1.12%</span></span>
  <span style="margin-right:3rem">GOOGL <span class="ticker-down">▼ 0.45%</span></span>
  <span style="margin-right:3rem">JPM <span class="ticker-up">▲ 0.89%</span></span>
  <span style="margin-right:3rem">GS <span class="ticker-down">▼ 1.23%</span></span>
  <span style="margin-right:3rem">NVDA <span class="ticker-up">▲ 3.45%</span></span>
  <span style="margin-right:3rem">S&P 500 <span class="ticker-up">▲ 0.94%</span></span>
  <span style="margin-right:3rem">10Y UST <span class="ticker-down">▼ 4.23%</span></span>
</div></div>
""", unsafe_allow_html=True)

# ── Hero
st.markdown("""
<div class="hero">
    <div class="hero-eyebrow">Financial Document Intelligence</div>
    <h1>Fin<em>Sight</em><sup>AI</sup></h1>
    <div class="hero-sub">
        Multi-modal retrieval · Structured extraction · Agentic risk analysis<br>
        <span style="color:#2a3a2a;">ColPali visual retrieval + Qwen2-VL-7B · No OCR · No paid APIs</span>
    </div>
    <div class="hero-badges">
        <span class="badge active">ColPali v1.2</span>
        <span class="badge active">Qwen2-VL-7B</span>
        <span class="badge active">Agentic Risk Engine</span>
        <span class="badge">SEC EDGAR · Apple 10-K</span>
        <span class="badge">Dual T4 GPU · 4-bit NF4</span>
    </div>
</div>
<div class="divider"></div>
""", unsafe_allow_html=True)

# ── GPU notice
st.markdown("""
<div class="gpu-banner">
    <strong style="color:#f0b429;">⚡ Live inference requires GPU.</strong>
    This Space runs on free CPU — full pipeline inference (ColPali + Qwen2-VL-7B) requires ~14GB VRAM.
    The demo below shows <strong>real outputs</strong> from the pipeline run on Apple Inc.'s FY2023 10-K filing
    (107 pages, downloaded from SEC EDGAR). Every number shown was extracted by the model.
    <br><br>
    To run locally with GPU: <code>git clone</code> the repo, add model weights, run <code>streamlit run app.py</code>
</div>
""", unsafe_allow_html=True)

# ── Load pre-computed results
@st.cache_data
def load_results():
    extracted, risk = [], []
    if os.path.exists("extracted_data.json"):
        with open("extracted_data.json") as f:
            extracted = json.load(f)
    if os.path.exists("risk_reports.json"):
        with open("risk_reports.json") as f:
            risk = json.load(f)
    config = {}
    if os.path.exists("pipeline_config.json"):
        with open("pipeline_config.json") as f:
            config = json.load(f)
    return extracted, risk, config

extracted_data, risk_reports, config = load_results()
has_results = len(extracted_data) > 0

# ── Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊  Pipeline Results",
    "🔬  Architecture",
    "📄  Raw Outputs",
    "ℹ️  About"
])

with tab1:
    if has_results:
        st.markdown('<div class="section-label">Apple Inc. FY2023 10-K — Extracted Financial Data</div>',
                    unsafe_allow_html=True)

        # Find the best page with actual financial data
        best_page = None
        for page in extracted_data:
            fin = page.get("financials", {})
            if fin.get("revenue") and fin["revenue"] != "null" and fin["revenue"] is not None:
                best_page = page
                break
        if not best_page and extracted_data:
            best_page = extracted_data[0]

        if best_page:
            fin = best_page.get("financials", {})

            # Metric cards
            fields = [
                ("Revenue",     fin.get("revenue")),
                ("Net Income",  fin.get("net_income")),
                ("EPS (diluted)", fin.get("eps")),
                ("Op. Margin",  fin.get("operating_margin")),
                ("Total Debt",  fin.get("total_debt")),
                ("Cash",        fin.get("cash")),
                ("Gross Profit",fin.get("gross_profit")),
                ("FCF",         fin.get("free_cash_flow")),
            ]
            valid = [(k, v) for k, v in fields if v and v not in ("null", None)]

            if valid:
                cells = "".join([
                    f'<div class="metric-cell"><div class="metric-val">{str(v)[:16]}</div>'
                    f'<div class="metric-lbl">{k}</div></div>'
                    for k, v in valid
                ])
                st.markdown(f'<div class="metric-row">{cells}</div>', unsafe_allow_html=True)

            # Summary answer
            summary = best_page.get("page_summary", "")
            if summary and summary not in ("null", "no summary"):
                st.markdown(f'<div class="answer-box"><strong>Model extraction summary:</strong><br>{summary}</div>',
                            unsafe_allow_html=True)

            # Metadata
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"""
                <div style="background:#0b1019; border:1px solid rgba(148,210,160,0.1); border-radius:8px; padding:1rem;">
                    <div style="font-family:monospace; font-size:0.55rem; letter-spacing:0.2em; color:#94d2a0; text-transform:uppercase; margin-bottom:0.6rem;">Document metadata</div>
                    <div style="font-family:monospace; font-size:0.72rem; color:#4a6a4a; margin-bottom:0.3rem;">Company: <span style="color:#c8d8c8;">{best_page.get('company_name','N/A')}</span></div>
                    <div style="font-family:monospace; font-size:0.72rem; color:#4a6a4a; margin-bottom:0.3rem;">Period: <span style="color:#c8d8c8;">{best_page.get('period','N/A')}</span></div>
                    <div style="font-family:monospace; font-size:0.72rem; color:#4a6a4a;">Source page: <span style="color:#c8d8c8;">Page {best_page.get('page_number','N/A')} (score: {best_page.get('retrieval_score','N/A')})</span></div>
                </div>
                """, unsafe_allow_html=True)
            with col_b:
                st.markdown(f"""
                <div style="background:#0b1019; border:1px solid rgba(148,210,160,0.1); border-radius:8px; padding:1rem;">
                    <div style="font-family:monospace; font-size:0.55rem; letter-spacing:0.2em; color:#94d2a0; text-transform:uppercase; margin-bottom:0.6rem;">Pipeline config</div>
                    <div style="font-family:monospace; font-size:0.72rem; color:#4a6a4a; margin-bottom:0.3rem;">Retrieval: <span style="color:#c8d8c8;">ColPali v1.2 (MaxSim)</span></div>
                    <div style="font-family:monospace; font-size:0.72rem; color:#4a6a4a; margin-bottom:0.3rem;">Reasoning: <span style="color:#c8d8c8;">Qwen2-VL-7B-Instruct (4-bit NF4)</span></div>
                    <div style="font-family:monospace; font-size:0.72rem; color:#4a6a4a;">GPU: <span style="color:#c8d8c8;">Dual T4 · 7GiB each</span></div>
                </div>
                """, unsafe_allow_html=True)

        # Risk reports
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Agentic Risk Analysis</div>', unsafe_allow_html=True)

        valid_risks = [r for r in risk_reports if not r.get("parse_error") and r.get("risk_level")]
        if valid_risks:
            risk_colors = {"LOW":"#94d2a0","MEDIUM":"#f0b429","HIGH":"#e05c5c","CRITICAL":"#ff5555"}

            for rr in valid_risks[:3]:
                rl = rr.get("risk_level","MEDIUM")
                rc = risk_colors.get(rl,"#f0b429")
                with st.expander(f"Page {rr.get('page_number','?')} — Risk Level: {rl}  |  Score: {rr.get('risk_score',0)}/100"):
                    summary = rr.get("analyst_summary","")
                    if summary:
                        st.markdown(f'<div class="answer-box" style="border-left-color:{rc};">{summary}</div>',
                                    unsafe_allow_html=True)
                    for flag in rr.get("flags", [])[:4]:
                        sev = flag.get("severity","MEDIUM")
                        fc  = risk_colors.get(sev,"#f0b429")
                        st.markdown(
                            f'<div class="flag-row flag-{sev}">'
                            f'<div style="font-family:monospace; font-size:0.65rem; color:{fc}; margin-bottom:0.2rem;">'
                            f'⚑ {flag.get("category","")} — {sev}</div>'
                            f'<div style="font-size:0.78rem; color:#c8d8c8; margin-bottom:0.2rem;">{flag.get("description","")}</div>'
                            f'<div style="font-size:0.78rem; color:#4a6a4a; font-style:italic;">→ {flag.get("recommendation","")}</div>'
                            f'</div>', unsafe_allow_html=True
                        )
                    pos = rr.get("positive_signals", [])
                    if pos:
                        items = "".join([f'<li style="margin-bottom:0.2rem; color:#6a8a6a;">{p}</li>' for p in pos[:3]])
                        st.markdown(
                            f'<div style="background:rgba(148,210,160,0.05); border:1px solid rgba(148,210,160,0.15); '
                            f'border-radius:6px; padding:0.8rem 1rem; margin-top:0.6rem;">'
                            f'<div style="font-family:monospace; font-size:0.55rem; letter-spacing:0.15em; '
                            f'color:#94d2a0; text-transform:uppercase; margin-bottom:0.5rem;">Positive signals</div>'
                            f'<ul style="margin:0; padding-left:1.2rem; font-size:0.75rem;">{items}</ul></div>',
                            unsafe_allow_html=True
                        )

        # Pipeline results image
        if os.path.exists("pipeline_results.png"):
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-label">Pipeline visualisation</div>', unsafe_allow_html=True)
            st.image("pipeline_results.png", use_column_width=True)

    else:
        st.markdown("""
        <div style="text-align:center; padding:4rem 0; color:#2a3a2a;">
            <div style="font-family:monospace; font-size:0.65rem; letter-spacing:0.2em; text-transform:uppercase; margin-bottom:1rem;">
                Results not loaded
            </div>
            <div style="font-family:Georgia,serif; font-size:1.4rem; color:#1a2a1a; font-style:italic; margin-bottom:0.8rem;">
                Upload extracted_data.json and risk_reports.json to this Space
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="section-label">How it works</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="arch-box">
<span style="color:#94d2a0;">Step 1 — PDF ingestion</span>
PyMuPDF converts each PDF page to a 150 DPI RGB image.
107 pages × 1241×1754px = preserving full table layout without any text extraction.

<span style="color:#94d2a0;">Step 2 — ColPali visual indexing</span>
Each page image is embedded as ~1000 patch vectors (128-dim each) using ColPali v1.2.
PaliGemma-3B backbone maps image patches and text query tokens into the same space.
No OCR. Tables, charts, and layouts are indexed as visual features.

<span style="color:#94d2a0;">Step 3 — MaxSim retrieval</span>
For each query token, find the most similar image patch. Sum across all query tokens.
This finds the specific page region matching the query — not just "which page mentions revenue"
but "which page has revenue numbers in a table format."

<span style="color:#94d2a0;">Step 4 — Qwen2-VL-7B reasoning</span>
The retrieved page image is passed directly to Qwen2-VL-7B-Instruct (4-bit NF4, ~11GB).
The model reads tables natively — no OCR preprocessing required.
Output: natural language answer + structured JSON with all financial fields.

<span style="color:#94d2a0;">Step 5 — Agentic risk analysis</span>
The model autonomously applies an 8-point financial analyst checklist:
LIQUIDITY · MARGINS · GROWTH · DEBT · CASH_FLOW · ANOMALY · MISSING_DATA · INCONSISTENCY
It decides what flags to raise — this is not a template fill, it is autonomous reasoning.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label" style="margin-top:1.5rem;">Why this is different from standard RAG</div>',
                unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="card">
            <div style="font-family:monospace; font-size:0.8rem; letter-spacing:0.15em; color:#e05c5c; text-transform:uppercase; margin-bottom:0.8rem;">Standard RAG pipeline</div>
            <div style="font-size:0.8rem; line-height:1.8; color:#4a6a4a;">
                PDF → OCR text extraction → chunk by tokens → embed text → vector search → LLM<br><br>
                <strong style="color:#6a4a4a;">Problem:</strong> OCR breaks on financial tables.
                "$383,285" becomes "S383.285" or splits across chunks.
                Table structure is destroyed — rows and columns lose their relationships.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="card">
            <div style="font-family:monospace; font-size:0.8rem; letter-spacing:0.15em; color:#94d2a0; text-transform:uppercase; margin-bottom:0.8rem;">FinSight pipeline</div>
            <div style="font-size:0.8rem; line-height:1.8; color:#4a6a4a;">
                PDF → page images → ColPali patch embeddings → MaxSim retrieval → Qwen2-VL reads image<br><br>
                <strong style="color:#4a6a4a;">Result:</strong> Tables are read as visual objects.
                The model sees the full table layout, row/column relationships, and surrounding context
                exactly as a human analyst would.
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="section-label">Raw JSON outputs from Apple FY2023 10-K run</div>',
                unsafe_allow_html=True)

    if has_results:
        col_e, col_r = st.columns(2)
        with col_e:
            st.markdown("**Structured extraction (all pages)**")
            st.json(extracted_data[:3] if len(extracted_data) > 3 else extracted_data)
        with col_r:
            st.markdown("**Risk analysis reports**")
            valid_r = [r for r in risk_reports if not r.get("parse_error")]
            st.json(valid_r[:3] if len(valid_r) > 3 else valid_r)
    else:
        st.info("Upload extracted_data.json and risk_reports.json to view raw outputs.")

with tab4:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
**FinSight AI** is a multi-modal financial document intelligence system
built as a research project.

**Architecture:**
- Retrieval: ColPali v1.2 (PaliGemma-3B backbone, late-interaction MaxSim)
- Reasoning: Qwen2-VL-7B-Instruct (4-bit NF4 quantisation)
- Infrastructure: Dual NVIDIA T4 GPU (Kaggle free tier), 7GB per GPU
- No paid APIs anywhere in the stack

**Training / development platform:** Kaggle (free GPU T4 x2)

**Related projects:**
- [MediScan AI](https://huggingface.co/spaces/MFH-001/MediScan-AI) — Skin lesion segmentation + medical Q&A
- [PsoriScan AI](https://huggingface.co/spaces/MFH-001/PsoriScan-AI) — Psoriasis severity scoring
        """)
    with col_b:
        st.markdown("""
**What the demo shows:**
Real outputs from running the full pipeline on Apple Inc.'s FY2023 10-K annual report
(107 pages, downloaded from SEC EDGAR — the same document professional analysts use).

**GPU requirement:**
Qwen2-VL-7B-Instruct requires ~14GB VRAM total. This Space runs on free CPU.
Live inference demo available on request — contact below.

**Disclaimer:**
FinSight is a research prototype. All analysis is AI-generated and may contain errors.
Not financial advice. Not validated for production use.

---
* Fahad *
*[github.com/mfh-001](https://github.com/mfh-001)*
        """)

st.markdown("""
<div style="font-family:monospace; font-size:0.6rem; color:#2a3a2a; text-align:center;
            padding:1.2rem 0 0.4rem; border-top:1px solid rgba(148,210,160,0.08); margin-top:2rem;">
    FinSight AI · Research prototype · Not financial advice 
</div>
""", unsafe_allow_html=True)
