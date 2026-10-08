# Contributing

Small, focused changes are easiest to review.

## Set up

```bash
git clone https://github.com/mfh-001/FinSight-AI
cd FinSight-AI
python -m venv .venv && . .venv/bin/activate
pip install -e ".[app,dev]"
pytest -q
ruff check finsight tests
```

The tests run on CPU with no network. They use a mock model, so you do not need a GPU or any model download.

## Before you open a pull request

- One logical change per commit. Short commit messages, lowercase, say what changed.
- Add or update a test for the change.
- If you change answers, extraction or the risk checks, run `finsight --backend none eval` and put the before and after numbers in the pull request.
- Do not add numbers to the README that you did not measure. Say which hardware and which date.

## Good first issues

- A new schema (for example a purchase order or a payslip) in `finsight/schemas.py`, with rules in `finsight/extract.py` and a test.
- More eval questions on other public filings. Each answer must be checked by hand against the document and carry the page.
- A test on a public document in another language.
- A scanned page path (OCR) that is optional and off by default.

## Reporting bugs

Use the bug template. Please say which backend and model you used, and attach the page if you can share it.
