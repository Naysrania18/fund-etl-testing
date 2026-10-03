"""
test_data_quality.py
---------------------
These tests check basic "is this data trustworthy" rules on the
loaded `transactions` table. For financial data especially, nulls in
key fields or duplicate IDs are not cosmetic issues - they can cause
double-counted money or broken joins downstream.
"""

import pandas as pd
import pytest

KEY_FIELDS = ["transaction_id", "fund_id", "investor_id", "amount"]


@pytest.mark.data_quality
def test_no_duplicate_transaction_ids(db_connection):
    """The transactions table must have one row per transaction_id."""
    df = pd.read_sql("SELECT transaction_id FROM transactions", db_connection)

    assert df["transaction_id"].duplicated().sum() == 0


@pytest.mark.data_quality
def test_no_nulls_in_key_fields(db_connection):
    """None of the fields we rely on for joins/aggregation may be null."""
    df = pd.read_sql("SELECT * FROM transactions", db_connection)

    for field in KEY_FIELDS:
        null_count = df[field].isna().sum()
        assert null_count == 0, f"Found {null_count} null value(s) in '{field}'"


@pytest.mark.data_quality
def test_all_amounts_converted_to_eur(db_connection):
    """
    Every loaded row must have a valid, numeric amount_eur - i.e. every
    row (regardless of its original currency) has successfully been
    expressed in a single common currency (EUR) for reporting.
    """
    df = pd.read_sql("SELECT currency, amount_eur FROM transactions", db_connection)

    assert df["amount_eur"].isna().sum() == 0
    assert pd.api.types.is_numeric_dtype(df["amount_eur"])

    # Only currencies our FX config knows about should ever reach this
    # table - anything else should have been rejected before loading.
    assert set(df["currency"].unique()).issubset({"EUR", "USD", "GBP"})


@pytest.mark.data_quality
def test_all_dates_are_valid_iso_format(db_connection):
    """Every transaction_date must parse as a real YYYY-MM-DD date."""
    df = pd.read_sql("SELECT transaction_date FROM transactions", db_connection)

    parsed = pd.to_datetime(df["transaction_date"], format="%Y-%m-%d", errors="coerce")
    assert parsed.isna().sum() == 0, "Found transaction_date values that are not valid YYYY-MM-DD"
