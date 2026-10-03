"""
pipeline.py
-----------
Wires Extract -> Transform -> Load together and prints a short run
summary. This is the single entry point the tests (and a human) use
to run the whole ETL job end-to-end.
"""

from pathlib import Path

from etl.extract import extract
from etl.load import load
from etl.transform import transform

DEFAULT_SOURCE_CSV = Path(__file__).parent.parent / "data" / "raw" / "fund_transactions.csv"
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "fund_data.db"


def run_pipeline(
    source_csv: str | Path = DEFAULT_SOURCE_CSV,
    db_path: str | Path = DEFAULT_DB_PATH,
):
    """
    Run the full ETL pipeline and print a summary.

    Parameters
    ----------
    source_csv:
        Path to the raw input CSV.
    db_path:
        Path to the SQLite database to write results into.

    Returns
    -------
    (valid_df, rejected_df, stats)
        The same objects produced by transform(), handed back so
        callers (e.g. pytest fixtures) can inspect them without
        re-reading the database.
    """
    raw_df = extract(source_csv)
    valid_df, rejected_df, stats = transform(raw_df)
    load(valid_df, rejected_df, db_path)

    print("=== ETL Pipeline Summary ===")
    print(f"Rows read:            {stats.rows_read}")
    print(f"Duplicates removed:   {stats.duplicates_removed}")
    print(f"Rows loaded (valid):  {stats.rows_valid}")
    print(f"Rows rejected:        {stats.rows_rejected}")
    if stats.rejection_breakdown:
        print("Rejection breakdown:")
        for reason, count in stats.rejection_breakdown.items():
            print(f"   - {reason}: {count}")
    print("============================")

    return valid_df, rejected_df, stats


if __name__ == "__main__":
    run_pipeline()
