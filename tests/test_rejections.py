"""
test_rejections.py
--------------------
Checks that every category of "dirty" row we deliberately injected in
data/generate_data.py ends up in `rejected_transactions` with the
correct, specific rejection_reason - not just rejected for some
arbitrary reason, but the RIGHT reason. This matters in practice
because an analyst reviewing rejects needs to trust the reason shown.
"""

import pandas as pd
import pytest


@pytest.mark.data_quality
def test_missing_investor_id_rows_are_rejected(db_connection):
    df = pd.read_sql(
        "SELECT * FROM rejected_transactions WHERE rejection_reason = 'missing_investor_id'",
        db_connection,
    )
    assert len(df) == 4  # matches NUM_MISSING_INVESTOR_ROWS in generate_data.py
    assert (df["investor_id"] == "").all()


@pytest.mark.data_quality
def test_negative_amount_rows_are_rejected(db_connection):
    df = pd.read_sql(
        "SELECT * FROM rejected_transactions WHERE rejection_reason = 'negative_amount'",
        db_connection,
    )
    assert len(df) == 3  # matches NUM_NEGATIVE_AMOUNT_ROWS in generate_data.py
    assert (df["amount"].astype(float) < 0).all()


@pytest.mark.data_quality
def test_invalid_currency_rows_are_rejected(db_connection):
    df = pd.read_sql(
        "SELECT * FROM rejected_transactions WHERE rejection_reason = 'invalid_currency'",
        db_connection,
    )
    assert len(df) == 2  # matches NUM_INVALID_CURRENCY_ROWS in generate_data.py
    assert (df["currency"] == "XXX").all()


@pytest.mark.data_quality
def test_bad_date_rows_are_rejected(db_connection):
    df = pd.read_sql(
        "SELECT * FROM rejected_transactions WHERE rejection_reason = 'invalid_date_format'",
        db_connection,
    )
    assert len(df) == 2  # matches NUM_BAD_DATE_ROWS in generate_data.py
    assert (df["transaction_date"] == "31/02/2024").all()


@pytest.mark.data_quality
def test_total_rejected_count_matches_injected_dirty_rows(pipeline_result):
    """
    4 missing investor + 3 negative amount + 2 invalid currency +
    2 bad date = 11 rejected rows in total (duplicates are handled
    separately and are NOT counted as rejected - see transform.py).
    """
    stats = pipeline_result["stats"]
    assert stats.rows_rejected == 11
