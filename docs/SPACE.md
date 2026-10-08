# Updating the Hugging Face Space

The Space `MFH-001/FinSight-AI` is currently the old Streamlit replay page.
The files for the new one are in `space/`. Nothing has been pushed.

The Space installs the package from GitHub, so push this repo to GitHub first.

```bash
# 1. clone the Space next to the repo (needs your Hugging Face login or token)
git clone https://huggingface.co/spaces/MFH-001/FinSight-AI finsight-space
cd finsight-space

# 2. keep the old version reachable on a branch
git switch -c legacy-streamlit && git push origin legacy-streamlit && git switch main

# 3. replace the files with the new ones
git rm -rq . && cp ../FinSight-AI/space/{app.py,requirements.txt,README.md} .
mkdir -p samples && cp ../FinSight-AI/samples/*.pdf samples/
mkdir -p legacy/recorded_run && cp ../FinSight-AI/legacy/recorded_run/* legacy/recorded_run/

# 4. push
git add -A && git commit -m "replace replay page with upload app" && git push
```

The app looks for `samples/` and `legacy/recorded_run/` in the working directory, so keep those folders at the Space root.

For a GPU answer path (ZeroGPU or a paid GPU), set these in the Space settings, and add `FINSIGHT_BACKEND=transformers`,
`FINSIGHT_LLM_MODEL=Qwen/Qwen2.5-VL-3B-Instruct` and the `.[gpu]` extra to `requirements.txt`. I could not test ZeroGPU here.

## Notes

- The Space runs on the free CPU hardware. It reads born-digital PDFs and shows the best matching lines with page numbers. It says so on the page, and it cannot read scanned pages.
- The old Streamlit replay stays only on the `legacy-streamlit` branch of the Space. It is not the default page.
- The old `Dockerfile` and `src/streamlit_app.py` (a leftover Streamlit template) are deleted by the `git rm -rq .` step.
