"""Renders a snapshot-in-time chart of known ticket prices per event."""

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from data.clean import clean_snapshots

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("outputs") / "price_snapshot.png"


def plot_price_snapshot(df: pd.DataFrame, output_path: Path | str = DEFAULT_OUTPUT_PATH) -> None:
    """Plot each event's latest known price_min-price_max range as a horizontal bar."""
    if df.empty:
        logger.info("No priced events to plot.")
        return

    latest_idx = df.groupby("event_id")["snapshot_date"].idxmax()
    latest = df.loc[latest_idx].sort_values("price_min")
    labels = latest["artist"] + " — " + latest["venue"]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, max(3, len(latest) * 0.4)))
    y_positions = range(len(latest))
    ax.hlines(y_positions, latest["price_min"], latest["price_max"], linewidth=6)
    ax.set_yticks(list(y_positions))
    ax.set_yticklabels(labels)
    ax.set_xlabel("Price ($)")
    ax.set_title("Known ticket price range per event (latest snapshot)")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    plot_price_snapshot(clean_snapshots())
