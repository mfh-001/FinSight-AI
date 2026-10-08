# Legacy

The first version of FinSight AI, kept as it was run.

- `recorded_run/`: the saved output of the Kaggle notebook on the Apple FY2023 10-K
  (`extracted_data.json`, `risk_reports.json`, `pipeline_config.json`, `pipeline_results.png`).
  These files are unchanged. They have known problems, listed in `docs/AUDIT.md`.
- `streamlit_replay/`: the old Streamlit page that replays that recording. It does no live inference.
  Two edits were made: file paths now point to `recorded_run/`, and the scrolling stock ticker
  was removed because its numbers were hardcoded and not real. A banner says it is a recording.
- `README_original.md`: the README as it was before the rewrite.

The notebook itself is in `notebooks/original/`.

Run the replay page:

```bash
pip install streamlit==1.32.0
streamlit run legacy/streamlit_replay/app.py
```
