"""
transform.py
------------
The "T" in ETL: clean, validate, and reshape the raw data.

This module takes the raw DataFrame from extract.py and produces three
outputs (see `transform()`):
    1. valid_df      - clean rows, ready to load, amounts converted to EUR
    2. rejected_df    - invalid rows, each tagged with a rejection_reason
    3. stats          - a dict of counts (read, duplicates removed, etc.)

Design choice: duplicates are handled SEPARATELY from "rejected" rows.
A duplicate transaction_id is not necessarily "bad data" - it's usually
the same event arriving twice (e.g. a retried message). We keep the
first occurrence and simply drop the rest, the same way a lot of real
ETL "dedupe" logic works. Everything else wrong with a row (missing
investor, negative amount, bad currency, bad date) is a genuine data
quality problem, so those rows go to `rejected_transactions` with an
explanation.
"""

from dataclasses import dataclass, field

import pandas as pd

# Fixed FX rates used to convert every amount into EUR.
# In a real system these would come from a market data feed, but a
# fixed config dict keeps this project simple and the tests deterministic.
FX_RATES_TO_EUR = {
    "USD": 0.92,
    "GBP": 1.17,
    "EUR": 1.00,
}

VALID_CURRENCIES = set(FX_RATES_TO_EUR.keys())
REQUIRED_FIELDS = ["transaction_id", "fund_id", "investor_id", "amount", "transaction_date"]


@dataclass
class TransformStats:
    """Simple record of what happened during the transform step."""
    rows_read: int = 0
    duplicates_removed: int = 0
    rows_rejected: int = 0
    rows_valid: int = 0
    rejection_breakdown: dict = field(default_factory=dict)


def _parse_amount(raw_amount: str):
    """Try to parse amount as a float. Returns (value, is_valid)."""
    try:
        return float(raw_amount), True
    except (TypeError, ValueError):
        return None, False


def _parse_date(raw_date: str):
    """
    Try to parse a date string strictly as YYYY-MM-DD.

    We use `format="%Y-%m-%d"` (rather than letting pandas guess) so
    that a malformed date like "31/02/2024" is correctly rejected
    instead of pandas silently reinterpreting it.
    """
    parsed = pd.to_datetime(raw_date, format="%Y-%m-%d", errors="coerce")
    if pd.isna(parsed):
        return None, False
    return parsed.strftime("%Y-%m-%d"), True


def _classify_row(row: pd.Series) -> str | None:
    """
    Check a single row against every validation rule.

    Returns
    -------
    str | None
        A rejection_reason string if the row is invalid, otherwise None.

    Note: a row could technically fail more than one rule (e.g. missing
    investor_id AND a bad date). We check in a fixed order and report
    the first problem found - good enough for this project, and keeps
    each rejected row tagged with a single, clear reason.
    """
    if not row["investor_id"].strip():
        return "missing_investor_id"

    amount, amount_ok = _parse_amount(row["amount"])
    if not amount_ok:
        return "invalid_amount_format"
    if amount < 0:
        return "negative_amount"

    if row["currency"] not in VALID_CURRENCIES:
        return "invalid_currency"

    _, date_ok = _parse_date(row["transaction_date"])
    if not date_ok:
        return "invalid_date_format"

    return None  # row passed every check


def transform(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, TransformStats]:
    """
    Clean and validate the raw extracted data.

    Parameters
    ----------
    raw_df:
        The DataFrame produced by extract.extract().

    Returns
    -------
    (valid_df, rejected_df, stats)
    """
    stats = TransformStats(rows_read=len(raw_df))

    # --- Step 1: remove duplicate transaction_ids, keep the first ---
    is_duplicate = raw_df.duplicated(subset=["transaction_id"], keep="first")
    stats.duplicates_removed = int(is_duplicate.sum())
    deduped_df = raw_df.loc[~is_duplicate].copy()

    # --- Step 2: classify every remaining row as valid or rejected ---
    reasons = deduped_df.apply(_classify_row, axis=1)

    rejected_mask = reasons.notna()
    rejected_df = deduped_df.loc[rejected_mask].copy()
    rejected_df["rejection_reason"] = reasons.loc[rejected_mask]

    valid_df = deduped_df.loc[~rejected_mask].copy()

    # --- Step 3: for valid rows only, convert amount -> EUR and standardise date ---
    valid_df["amount"] = valid_df["amount"].astype(float)
    valid_df["amount_eur"] = valid_df.apply(
        lambda r: round(r["amount"] * FX_RATES_TO_EUR[r["currency"]], 2), axis=1
    )
    valid_df["transaction_date"] = valid_df["transaction_date"].apply(
        lambda d: _parse_date(d)[0]
    )

    # Reorder/trim columns for a tidy, predictable "load-ready" shape.
    valid_df = valid_df[
        [
            "transaction_id",
            "fund_id",
            "investor_id",
            "transaction_type",
            "amount",
            "currency",
            "amount_eur",
            "transaction_date",
        ]
    ].reset_index(drop=True)
    rejected_df = rejected_df.reset_index(drop=True)

    stats.rows_valid = len(valid_df)
    stats.rows_rejected = len(rejected_df)
    stats.rejection_breakdown = (
        rejected_df["rejection_reason"].value_counts().to_dict() if len(rejected_df) else {}
    )

    return valid_df, rejected_df, stats
