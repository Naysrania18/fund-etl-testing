"""
test_transformation_rules.py
------------------------------
Tests for the actual business/transformation logic, rather than
general data-quality rules:
    - is the FX conversion math correct for specific known rows?
    - does the investor_balances summary table actually equal the sum
      of that investor's own transactions?
"""

import pandas as pd
import pytest

FX_RATES = {"USD": 0.92, "GBP": 1.17, "EUR": 1.00}


@pytest.mark.transformation
def test_usd_conversion_is_correct(pipeline_result):
    """Pick a real USD row from the loaded data and verify the EUR math."""
    valid_df = pipeline_result["valid_df"]
    usd_rows = valid_df[valid_df["currency"] == "USD"]

    assert len(usd_rows) > 0, "Expected at least one USD row in the test dataset"

    row = usd_rows.iloc[0]
    expected_eur = round(row["amount"] * FX_RATES["USD"], 2)

    assert row["amount_eur"] == expected_eur


@pytest.mark.transformation
def test_gbp_conversion_is_correct(pipeline_result):
    """Pick a real GBP row from the loaded data and verify the EUR math."""
    valid_df = pipeline_result["valid_df"]
    gbp_rows = valid_df[valid_df["currency"] == "GBP"]

    assert len(gbp_rows) > 0, "Expected at least one GBP row in the test dataset"

    row = gbp_rows.iloc[0]
    expected_eur = round(row["amount"] * FX_RATES["GBP"], 2)

    assert row["amount_eur"] == expected_eur


@pytest.mark.transformation
def test_investor_balances_match_transaction_sums(db_connection):
    """
    For a sample investor, the total in investor_balances must equal
    the sum of that investor's own rows in `transactions`, per fund.
    """
    balances_df = pd.read_sql("SELECT * FROM investor_balances", db_connection)
    assert len(balances_df) > 0, "Expected at least one row in investor_balances"

    # Check every (investor_id, fund_id) pair, not just one, since this
    # is cheap to do and gives much stronger confidence in the aggregation.
    for _, balance_row in balances_df.iterrows():
        txn_sum = pd.read_sql(
            """
            SELECT SUM(amount_eur) AS total
            FROM transactions
            WHERE investor_id = ? AND fund_id = ?
            """,
            db_connection,
            params=(balance_row["investor_id"], balance_row["fund_id"]),
        )["total"].iloc[0]

        assert round(txn_sum, 2) == round(balance_row["total_amount_eur"], 2)
