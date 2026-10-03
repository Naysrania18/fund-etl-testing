"""
load.py
-------
The "L" in ETL: write the transformed data into a SQLite database.

Three tables are produced:
    - transactions            valid, cleaned rows (amount_eur included)
    - rejected_transactions   invalid rows + rejection_reason
    - investor_balances       summary: total EUR per (investor, fund)

Using SQLite keeps this project dependency-free and easy to run/test
(no external database server needed), while still exercising the same
"load into a real table and query it back" logic tests would use
against a production warehouse.
"""

import sqlite3
from pathlib import Path

import pandas as pd


def load(
    valid_df: pd.DataFrame,
    rejected_df: pd.DataFrame,
    db_path: str | Path,
) -> None:
    """
    Write valid rows, rejected rows, and a derived summary table to SQLite.

    Parameters
    ----------
    valid_df:
        Clean rows produced by transform.transform().
    rejected_df:
        Rejected rows (with rejection_reason) produced by transform.transform().
    db_path:
        Path to the SQLite database file to write to. The file is
        created if it doesn't exist; tables are replaced if they do
        (so re-running the pipeline against the same file is safe).
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        valid_df.to_sql("transactions", conn, if_exists="replace", index=False)
        rejected_df.to_sql("rejected_transactions", conn, if_exists="replace", index=False)

        balances_df = build_investor_balances(valid_df)
        balances_df.to_sql("investor_balances", conn, if_exists="replace", index=False)

        conn.commit()
    finally:
        conn.close()


def build_investor_balances(valid_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the investor_balances summary: total amount_eur per investor,
    per fund.

    Kept as its own function (rather than inline SQL) so it is easy to
    unit test directly and reuse from pipeline.py.
    """
    if valid_df.empty:
        return pd.DataFrame(columns=["investor_id", "fund_id", "total_amount_eur"])

    balances_df = (
        valid_df.groupby(["investor_id", "fund_id"], as_index=False)["amount_eur"]
        .sum()
        .rename(columns={"amount_eur": "total_amount_eur"})
    )
    balances_df["total_amount_eur"] = balances_df["total_amount_eur"].round(2)
    return balances_df
