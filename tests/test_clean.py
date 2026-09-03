import pandas as pd

from data.clean import clean_snapshots
from data.storage import append_snapshots


def _make_record(event_id, snapshot_date="2026-09-03T12:00:00+00:00", price_min=None, price_max=None):
    return {
        "event_id": event_id,
        "artist": "The Testers",
        "venue": "Test Arena",
        "city": "Austin",
        "event_date": "2026-10-01",
        "price_min": price_min,
        "price_max": price_max,
        "snapshot_date": snapshot_date,
        "first_seen_date": snapshot_date,
    }


def test_drops_no_price_rows_by_default(tmp_path):
    path = tmp_path / "snapshots.csv"
    append_snapshots(
        [
            _make_record("priced-event", price_min=45.0, price_max=250.0),
            _make_record("unpriced-event", price_min=None, price_max=None),
        ],
        path=path,
    )

    df = clean_snapshots(path=path)

    assert list(df["event_id"]) == ["priced-event"]


def test_keeps_no_price_rows_when_disabled(tmp_path):
    path = tmp_path / "snapshots.csv"
    append_snapshots(
        [
            _make_record("priced-event", price_min=45.0, price_max=250.0),
            _make_record("unpriced-event", price_min=None, price_max=None),
        ],
        path=path,
    )

    df = clean_snapshots(path=path, drop_no_price=False)

    assert set(df["event_id"]) == {"priced-event", "unpriced-event"}


def test_date_columns_are_datetime(tmp_path):
    path = tmp_path / "snapshots.csv"
    append_snapshots([_make_record("priced-event", price_min=45.0, price_max=250.0)], path=path)

    df = clean_snapshots(path=path)

    for column in ["event_date", "snapshot_date", "first_seen_date"]:
        assert pd.api.types.is_datetime64_any_dtype(df[column])


def test_sorted_by_event_id_then_snapshot_date(tmp_path):
    path = tmp_path / "snapshots.csv"
    append_snapshots(
        [
            _make_record("event-b", snapshot_date="2026-09-03T12:00:00+00:00", price_min=10.0, price_max=20.0),
            _make_record("event-a", snapshot_date="2026-09-04T12:00:00+00:00", price_min=10.0, price_max=20.0),
            _make_record("event-a", snapshot_date="2026-09-03T12:00:00+00:00", price_min=10.0, price_max=20.0),
        ],
        path=path,
    )

    df = clean_snapshots(path=path)

    assert list(df["event_id"]) == ["event-a", "event-a", "event-b"]
    assert df.iloc[0]["snapshot_date"] < df.iloc[1]["snapshot_date"]
