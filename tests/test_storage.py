from data.storage import SNAPSHOT_COLUMNS, append_snapshots, load_snapshots


def _make_record(event_id="G5vYZ9", snapshot_date="2026-09-03T12:00:00+00:00"):
    return {
        "event_id": event_id,
        "artist": "The Testers",
        "venue": "Test Arena",
        "city": "Austin",
        "event_date": "2026-10-01",
        "price_min": 45.0,
        "price_max": 250.0,
        "snapshot_date": snapshot_date,
        "first_seen_date": snapshot_date,
    }


def test_append_creates_file_with_header_and_rows(tmp_path):
    path = tmp_path / "snapshots.csv"

    append_snapshots([_make_record()], path=path)

    assert path.exists()
    df = load_snapshots(path=path)
    assert len(df) == 1
    assert list(df.columns) == SNAPSHOT_COLUMNS
    assert df.iloc[0]["event_id"] == "G5vYZ9"


def test_append_twice_accumulates_without_duplicate_header(tmp_path):
    path = tmp_path / "snapshots.csv"

    append_snapshots([_make_record(snapshot_date="2026-09-03T12:00:00+00:00")], path=path)
    append_snapshots([_make_record(snapshot_date="2026-09-04T12:00:00+00:00")], path=path)

    lines = path.read_text().strip().splitlines()
    assert lines[0] == ",".join(SNAPSHOT_COLUMNS)
    assert len(lines) == 3  # header + 2 data rows

    df = load_snapshots(path=path)
    assert len(df) == 2


def test_append_empty_list_does_not_create_file(tmp_path):
    path = tmp_path / "snapshots.csv"

    append_snapshots([], path=path)

    assert not path.exists()


def test_load_snapshots_missing_file_returns_empty_dataframe(tmp_path):
    path = tmp_path / "does_not_exist.csv"

    df = load_snapshots(path=path)

    assert df.empty
    assert list(df.columns) == SNAPSHOT_COLUMNS


def test_round_trip_preserves_values(tmp_path):
    path = tmp_path / "snapshots.csv"
    record = _make_record()

    append_snapshots([record], path=path)
    df = load_snapshots(path=path)

    row = df.iloc[0]
    for key, value in record.items():
        assert row[key] == value
