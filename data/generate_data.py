"""
generate_data.py
-----------------
Creates a fake "raw" dataset of private equity fund transactions and
writes it to data/raw/fund_transactions.csv.

Why fake but "dirty" data?
In real ETL pipelines, source data is never perfectly clean. To test an
ETL pipeline properly, we need to deliberately inject the kinds of
problems that show up in real financial data feeds:
    - duplicate transaction IDs (the same event sent twice)
    - missing required fields (investor_id)
    - invalid/negative amounts
    - unsupported currency codes
    - badly formatted dates

The pipeline's job is to catch all of these and route them to a
"rejected" table instead of silently loading bad data.
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)  # fixed seed -> reproducible "random" data for repeatable tests

OUTPUT_PATH = Path(__file__).parent / "raw" / "fund_transactions.csv"

FUND_IDS = [f"FUND-{i:03d}" for i in range(1, 11)]        # FUND-001 .. FUND-010
INVESTOR_IDS = [f"INV-{i:04d}" for i in range(1, 41)]      # INV-0001 .. INV-0040
TRANSACTION_TYPES = ["CAPITAL_CALL", "DISTRIBUTION", "FEE"]
VALID_CURRENCIES = ["EUR", "USD", "GBP"]

NUM_CLEAN_ROWS = 189          # clean rows we generate directly
NUM_DUPLICATE_ROWS = 5        # duplicate transaction_ids
NUM_MISSING_INVESTOR_ROWS = 4
NUM_NEGATIVE_AMOUNT_ROWS = 3
NUM_INVALID_CURRENCY_ROWS = 2
NUM_BAD_DATE_ROWS = 2
# Total rows = 189 + 5 + 4 + 3 + 2 + 2 = 205 (~200 as requested)

START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2024, 12, 31)


def random_date() -> str:
    """Return a random valid date string between START_DATE and END_DATE."""
    delta_days = (END_DATE - START_DATE).days
    random_day = START_DATE + timedelta(days=random.randint(0, delta_days))
    return random_day.strftime("%Y-%m-%d")


def random_amount() -> float:
    """Return a plausible positive transaction amount."""
    return round(random.uniform(1_000, 500_000), 2)


def make_clean_row(transaction_id: int) -> dict:
    """Build one well-formed transaction row."""
    return {
        "transaction_id": f"TXN-{transaction_id:05d}",
        "fund_id": random.choice(FUND_IDS),
        "investor_id": random.choice(INVESTOR_IDS),
        "transaction_type": random.choice(TRANSACTION_TYPES),
        "amount": random_amount(),
        "currency": random.choice(VALID_CURRENCIES),
        "transaction_date": random_date(),
    }


def main() -> None:
    rows = []
    next_id = 1

    # 1. Clean rows
    for _ in range(NUM_CLEAN_ROWS):
        rows.append(make_clean_row(next_id))
        next_id += 1

    # 2. Duplicate transaction_ids: re-use an existing row's id on a new row
    for _ in range(NUM_DUPLICATE_ROWS):
        original = random.choice(rows)
        dup = make_clean_row(next_id)
        dup["transaction_id"] = original["transaction_id"]  # force duplicate id
        rows.append(dup)
        next_id += 1

    # 3. Missing investor_id
    for _ in range(NUM_MISSING_INVESTOR_ROWS):
        row = make_clean_row(next_id)
        row["investor_id"] = ""  # missing value
        rows.append(row)
        next_id += 1

    # 4. Negative amounts
    for _ in range(NUM_NEGATIVE_AMOUNT_ROWS):
        row = make_clean_row(next_id)
        row["amount"] = -abs(row["amount"])  # force negative
        rows.append(row)
        next_id += 1

    # 5. Invalid currency codes
    for _ in range(NUM_INVALID_CURRENCY_ROWS):
        row = make_clean_row(next_id)
        row["currency"] = "XXX"  # not a supported currency
        rows.append(row)
        next_id += 1

    # 6. Badly formatted dates
    for _ in range(NUM_BAD_DATE_ROWS):
        row = make_clean_row(next_id)
        row["transaction_date"] = "31/02/2024"  # not ISO format, invalid day/month order
        rows.append(row)
        next_id += 1

    # Shuffle so dirty rows aren't all clumped at the end (more realistic)
    random.shuffle(rows)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "transaction_id",
        "fund_id",
        "investor_id",
        "transaction_type",
        "amount",
        "currency",
        "transaction_date",
    ]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
