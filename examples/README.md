# Examples

Run from the repo root.

```bash
pip install -e ".[app]"
python examples/make_examples.py          # rebuilds the two synthetic pdfs
finsight ingest examples/
```

## Invoice to Excel

`invoice/invoice-synthetic.pdf` is a made-up invoice (made-up vendor and numbers).

```bash
finsight extract --schema invoice --doc invoice-synthetic --out invoice.xlsx
```

Result (also in `outputs/invoice.xlsx`): vendor Northwind Supplies Ltd, number INV-2024-0042, date 2024-03-05,
due 2024-04-04, subtotal 555.00, tax 44.40, total 599.40 USD, and 3 line items.
This runs with rules and no model. It works on invoices laid out like this one, with labelled lines and a ruled
table. Other layouts need a model: add `--backend openai --model ...` and it will use the model first and fall back to rules.

## Bank statement to Excel

`bank_statement/statement-synthetic.pdf` is a made-up statement.

```bash
finsight extract --schema bank_statement --doc statement-synthetic --out statement.xlsx
```

Result (also in `outputs/bank_statement.xlsx`): holder Jane Doe, account ending 4821, period 2024-01-01 to 2024-01-31,
opening 2,400.00, closing 2,611.75, and 5 transactions with money out as negative numbers. The opening balance
plus the amounts equals the closing balance.

## Contract clause Q&A

`contract/securities-purchase-agreement.pdf` is a public SEC exhibit (Scientific Industries, Inc. securities purchase agreement,
exhibit 10.1, filed April 2025). 27 pages.

```bash
finsight --backend openai --model qwen2.5:3b ask "What law governs this agreement?" --doc securities-purchase-agreement
finsight --backend openai --model qwen2.5:3b ask "Which securities does the Company sell?" --doc securities-purchase-agreement
```

Legal wording needs a model. Without one, `--backend none` returns the closest sentences, and for questions whose
words do not appear on the page (for example "governs" when the text says "governed by") it answers
"not found in the documents". I have not run these two commands with a model, so there are no results here.

## Arabic

Not tested. Listed under Roadmap in the main README.
