# Sample filings

Public SEC EDGAR filings. I rendered the original HTML to PDF with headless Chrome,
so page numbers in this repo refer to these PDFs and not to the printed page numbers.

| File | Filing | Source |
|---|---|---|
| apple-10k-fy2023.pdf | Apple Inc. 10-K, fiscal year ended 2023-09-30 | https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm |
| nathans-10k-fy2025.pdf | Nathan's Famous, Inc. 10-K, fiscal year ended 2025-03-30 | https://www.sec.gov/Archives/edgar/data/69733/000143774925019916/nath20250331_10k.htm |

To rebuild a PDF:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
  --no-pdf-header-footer --print-to-pdf=out.pdf file:///path/to/filing.htm
```

Another Chrome version can break pages differently, so the eval in `eval/` always runs on the files in this folder.
