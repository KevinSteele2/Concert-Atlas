"""Cleans the raw snapshot history into a modeling-ready DataFrame."""

from pathlib import Path

import pandas as pd

from data.storage import DEFAULT_SNAPSHOT_PATH, load_snapshots

DATE_COLUMNS = ["event_date", "snapshot_date", "first_seen_date"]
PRICE_COLUMNS = ["price_min", "price_max"]


def clean_snapshots(
    path: Path | str = DEFAULT_SNAPSHOT_PATH, drop_no_price: bool = True
) -> pd.DataFrame:
    """Load and clean the snapshot history: real dtypes, sorted, optionally price-only."""
    df = load_snapshots(path)

    for column in DATE_COLUMNS:
        df[column] = pd.to_datetime(df[column])
    for column in PRICE_COLUMNS:
        df[column] = df[column].astype(float)

    if drop_no_price:
        df = df[df["price_min"].notna()]

    return df.sort_values(["event_id", "snapshot_date"]).reset_index(drop=True)
