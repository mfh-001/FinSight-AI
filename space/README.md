---
title: FinSight AI
emoji: 📄
colorFrom: green
colorTo: gray
sdk: gradio
sdk_version: 5.50.0
python_version: "3.12"
app_file: app.py
pinned: true
license: mit
short_description: Ask questions about financial PDFs, get page citations
---

Ask questions about financial PDFs and get answers with page citations.
Upload a PDF (first 20 pages are read) or try a sample SEC filing.

This Space runs on CPU without a model, so answers are the best matching lines from the cited page.
For written answers, extraction quality and the risk check, see the code and run it locally:
https://github.com/mfh-001/FinSight-AI

The first version of this Space (a replay of one recorded run) is kept in the repository under `legacy/`.
