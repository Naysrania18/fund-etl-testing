# Fund ETL Testing

A small, self-contained project that demonstrates how to **test an ETL
pipeline for financial data**, using a simplified private equity fund
transactions dataset. Built as a learning/portfolio project while
preparing for an SDET interview.

## What is ETL, and why test it?

**ETL** stands for **Extract, Transform, Load**:

- **Extract** – read raw data from a source (here, a CSV file; in
  production this could be an API, a message queue, or another
  database).
- **Transform** – clean, validate, and reshape the data: fix formats,
  drop or flag bad rows, apply business rules (like currency
  conversion), and calculate summaries.
- **Load** – write the final, trustworthy data into a target system
  (here, a SQLite database) that other systems/reports will rely on.

ETL pipelines are the backbone of financial reporting: fund
administrators, investor reporting tools, and regulatory filings all
depend on numbers that have passed through pipelines like this one. If
an ETL pipeline silently drops a row, double-counts a transaction, or
mixes up currencies, the result is **wrong financial numbers** that
might not be noticed until an investor statement or audit — which is
exactly why ETL pipelines need a strong automated test suite, not just
"it ran without crashing."

## What this project tests, and why each check matters

| Test file | What it checks | Why it matters for financial data |
|---|---|---|
| `test_reconciliation.py` | Source row count = loaded + rejected + duplicates removed. Sum of EUR amounts in the target matches an independently recalculated sum from the source. | **Reconciliation** is the #1 thing finance teams check: did we lose, invent, or double-count any rows or money? A pipeline that can't prove this isn't trustworthy for financial reporting. |
| `test_data_quality.py` | No duplicate `transaction_id`s in the target. No nulls in key fields (`transaction_id`, `fund_id`, `investor_id`, `amount`). All loaded currencies are ones we know how to convert. All dates are valid `YYYY-MM-DD`. | Nulls in key fields break joins and aggregations downstream. Duplicate IDs cause double-counted money. Bad dates/currencies cause silent miscalculations in reports. |
| `test_transformation_rules.py` | Currency conversion math is correct for a real USD row and a real GBP row. The `investor_balances` summary table equals the sum of that investor's own transactions. | These are the actual **business rules** of the pipeline — a reconciliation check alone wouldn't catch "USD converted at the wrong rate" if the error happened to cancel out elsewhere. |
| `test_rejections.py` | Every category of bad data we injected (missing investor, negative amount, invalid currency, bad date) lands in `rejected_transactions` with the *correct* `rejection_reason`, and the right count of rows. | An analyst reviewing rejected rows needs to trust the reason shown — a vague or wrong reason wastes investigation time, and a row that should have been rejected but wasn't is a correctness bug hiding as "it loaded fine." |

Duplicate `transaction_id`s are handled **separately** from rejections:
a duplicate is usually the same event arriving twice (e.g. a retried
message), so the pipeline just keeps the first copy and drops the
rest, rather than flagging it as "bad data."

## Project structure

```
fund-etl-testing/
├── data/
│   ├── generate_data.py          # creates the fake (deliberately dirty) source CSV
│   └── raw/fund_transactions.csv # generated source data (not committed)
├── etl/
│   ├── extract.py                # reads the CSV into a DataFrame
│   ├── transform.py               # validates, rejects, converts currency, standardises dates
│   ├── load.py                    # writes to SQLite: transactions, rejected_transactions, investor_balances
│   └── pipeline.py                # runs extract -> transform -> load, prints a summary
├── tests/
│   ├── test_reconciliation.py
│   ├── test_data_quality.py
│   ├── test_transformation_rules.py
│   └── test_rejections.py
├── conftest.py                    # pytest fixtures: runs the pipeline once per test session
├── pytest.ini                     # pytest config + custom markers
├── requirements.txt
└── .github/workflows/etl-tests.yml  # CI: generate data, run pipeline, run tests, upload HTML report
```

## How to run it locally

```bash
# 1. Create and activate a virtual environment (optional but recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate the sample (deliberately dirty) source data
python data/generate_data.py

# 4. Run the ETL pipeline on its own, to see the summary
python -m etl.pipeline

# 5. Run the full test suite
pytest

# 6. Run only one category of tests, using the custom markers
pytest -m reconciliation
pytest -m data_quality
pytest -m transformation

# 7. Generate an HTML test report
pytest --html=report.html --self-contained-html
```

The test suite runs the pipeline **once** (see `conftest.py`, scope
`"session"`) against a temporary SQLite database created by pytest's
`tmp_path_factory`, so tests are fast and don't interfere with each
other or leave files behind.

## Continuous Integration

`.github/workflows/etl-tests.yml` runs on every push and pull request:
installs dependencies, regenerates the sample data, runs the pipeline,
runs the full pytest suite with an HTML report, and uploads that
report as a downloadable build artifact — so a reviewer can see full
test results without running anything locally.

## How I used Claude Code

I used Claude Code to scaffold this entire project — the sample data
generator, the extract/transform/load modules, the pytest suite, the
CI workflow, and this README — from a single description of what I
wanted to demonstrate for an SDET interview. I reviewed every file,
ran the pipeline and the full test suite myself, and read through the
transformation and rejection logic to make sure I actually understood
*why* each test exists (not just that it passes) before treating this
as something I could explain and defend in an interview.
