# TODO

- Replace `docs/media/demo.gif` with a real 20 to 40 second recording of the Gradio app answering three questions with page thumbnails.
  Do it once the Space is live. The current GIF is a drawn terminal made from real `finsight ask` output, not a screen recording.
- Run `notebooks/kaggle_eval.ipynb` on a Kaggle T4 and fill the model rows with `scripts/results_to_table.py --update-readme`.
- Run the Docker CI job on GitHub and fix whatever it finds. Docker was never run on the author's machine.
- Add a scanned page path (optional OCR) so the text-only path says "cannot read this page" instead of printing lines from another page.
- More held-out questions on more filings.
