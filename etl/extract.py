"""
extract.py
----------
The "E" in ETL: read raw source data into memory.

Kept deliberately simple: this just reads a CSV into a pandas
DataFrame. In a real-world system this might instead call an API,
read from a data lake, or query a source database - but the rest of
the pipeline wouldn't need to change, because it only depends on
getting a DataFrame back.
"""

from pathlib import Path

import pandas as pd

# All columns are read as plain strings first. We deliberately do NOT
# let pandas guess types (e.g. parse dates or infer numeric columns)
# because the raw data is "dirty" - letting pandas guess could hide
# bad values (e.g. a bad date silently becoming NaT) before our
# transform step gets a chance to classify and reject them properly.
DTYPE_MAP = {
    "transaction_id": str,
    "fund_id": str,
    "investor_id": str,
    "transaction_type": str,
    "amount": str,
    "currency": str,
    "transaction_date": str,
}


def extract(csv_path: str | Path) -> pd.DataFrame:
    """
    Read the raw transactions CSV into a DataFrame.

    Parameters
    ----------
    csv_path:
        Path to the source CSV file.

    Returns
    -------
    pd.DataFrame
        Raw data, every column as a string (see DTYPE_MAP comment above).
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Source file not found: {csv_path}")

    df = pd.read_csv(csv_path, dtype=DTYPE_MAP, keep_default_na=False)
    return df
