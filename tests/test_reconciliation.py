"""
test_reconciliation.py
-----------------------
"Reconciliation" tests answer the question every finance stakeholder
asks first: *did we lose or invent any money or rows along the way?*

These tests check that the numbers on the source side and the numbers
on the target side tie out exactly - a fundamental check for any
financial ETL pipeline.
"""

import pandas as pd
import pytest


@pytest.mark.reconciliation
def test_row_counts_reconcile(pipeline_result, raw_source_df):
    """
    source rows == loaded (valid) + rejected + duplicates removed

    If this doesn't hold, rows are silently disappearing or being
    double-counted somewhere in the pipeline - which, for financial
    data, is exactly the kind of bug that must be caught before it
    reaches production.
    """
    stats = pipeline_result["stats"]

    assert len(raw_source_df) == stats.rows_read
    assert stats.rows_read == stats.rows_valid + stats.rows_rejected + stats.duplicates_removed


@pytest.mark.reconciliation
def test_eur_sum_reconciles_with_source(pipeline_result, db_connection):
    """
    The total EUR amount in the `transactions` table must equal the
    EUR-converted total of only the VALID source rows (recomputed
    independently here, rather than trusting the pipeline's own
    conversion, to catch bugs in transform.py itself).
    """
    valid_df = pipeline_result["valid_df"]

    # IMPORTANT: round each row to 2 decimals BEFORE summing, not after.
    # The ledger stores a rounded EUR amount per transaction (that's the
    # actual number on each row), so the "correct" total is the sum of
    # those per-row rounded values - summing raw unrounded amounts and
    # rounding only once at the end can drift by a cent or two due to
    # normal floating-point rounding, and would not match what's really
    # stored on each row in the table.
    fx_rates = {"USD": 0.92, "GBP": 1.17, "EUR": 1.00}
    expected_total = round(
        sum(
            round(row["amount"] * fx_rates[row["currency"]], 2)
            for _, row in valid_df.iterrows()
        ),
        2,
    )

    loaded_total = pd.read_sql("SELECT SUM(amount_eur) AS total FROM transactions", db_connection)
    actual_total = round(loaded_total["total"].iloc[0], 2)

    assert actual_total == expected_total
