"""CLI: pull music events for a city from Ticketmaster and store them as a snapshot."""

import argparse
import logging

from data.ingest_ticketmaster import fetch_events
from data.storage import append_snapshots

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("city", help="City to pull music events for, e.g. Austin")
    parser.add_argument(
        "--max-pages", type=int, default=None, help="Limit how many pages to fetch (default: all)"
    )
    args = parser.parse_args(argv)

    records = fetch_events(args.city, max_pages=args.max_pages)
    append_snapshots(records)

    priced = sum(1 for r in records if r["price_min"] is not None)
    print(f"Pulled {len(records)} events for {args.city} ({priced} with price data).")
    print("Saved to data/snapshots.csv")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
