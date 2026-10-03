"""
conftest.py
-----------
Shared pytest fixtures for the whole test suite.

Key idea: we run the ETL pipeline ONCE per test session (scope="session")
against a temporary SQLite database and a temporary copy of the source
data. Every test file then reuses that same result instead of
re-running the pipeline, which keeps the suite fast and means every
test is checking the exact same run.
"""

import shutil
import sqlite3
from pathlib import Path

import pytest

from etl.pipeline import run_pipeline

PROJECT_ROOT = Path(__file__).parent
SOURCE_CSV = PROJECT_ROOT / "data" / "raw" / "fund_transactions.csv"


@pytest.fixture(scope="session")
def pipeline_result(tmp_path_factory):
    """
    Run the full ETL pipeline once, against a temporary SQLite database,
    and return everything a test might need:

        valid_df     - the clean DataFrame that was loaded
        rejected_df  - the rejected DataFrame
        stats        - TransformStats (counts)
        db_path      - path to the temporary SQLite database on disk
    """
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(
            f"Source data not found at {SOURCE_CSV}. "
            "Run `python data/generate_data.py` first."
        )

    tmp_dir = tmp_path_factory.mktemp("fund_etl_test_run")
    db_path = tmp_dir / "test_fund_data.db"

    valid_df, rejected_df, stats = run_pipeline(source_csv=SOURCE_CSV, db_path=db_path)

    return {
        "valid_df": valid_df,
        "rejected_df": rejected_df,
        "stats": stats,
        "db_path": db_path,
    }


@pytest.fixture(scope="session")
def db_connection(pipeline_result):
    """
    A read-only-ish sqlite3 connection to the temporary database that
    the pipeline wrote to. Shared across tests in the session, closed
    automatically when the session ends.
    """
    conn = sqlite3.connect(pipeline_result["db_path"])
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def raw_source_df():
    """The untouched raw CSV, read as plain strings, for comparison in
    reconciliation tests (source count vs loaded+rejected+duplicates)."""
    from etl.extract import extract

    return extract(SOURCE_CSV)
