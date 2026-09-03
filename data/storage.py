"""Reads and writes ticket price snapshots. Append-only: past snapshots are never overwritten."""

from pathlib import Path

import pandas as pd

SNAPSHOT_COLUMNS = [
    "event_id",
    "artist",
    "venue",
    "city",
    "event_date",
    "price_min",
    "price_max",
    "snapshot_date",
    "first_seen_date",
]

DEFAULT_SNAPSHOT_PATH = Path(__file__).parent / "snapshots.csv"


def append_snapshots(records: list[dict], path: Path | str = DEFAULT_SNAPSHOT_PATH) -> None:
    """Append snapshot records to the store, writing a header only if the file is new."""
    if not records:
        return

    path = Path(path)
    df = pd.DataFrame(records, columns=SNAPSHOT_COLUMNS)
    file_exists = path.exists()
    df.to_csv(path, mode="a", header=not file_exists, index=False)


def load_snapshots(path: Path | str = DEFAULT_SNAPSHOT_PATH) -> pd.DataFrame:
    """Load the full snapshot history. Returns an empty frame if no pull has happened yet."""
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)
    return pd.read_csv(path)
