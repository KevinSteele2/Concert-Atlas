from data.aggregate import aggregate_by_city


def _make_event(
    event_id="e1",
    city="Austin",
    state="TX",
    lat=30.0,
    lon=-97.0,
    event_date="2026-10-01",
    genre="Rock",
):
    return {
        "event_id": event_id,
        "artist": "The Testers",
        "venue": "Test Arena",
        "city": city,
        "state": state,
        "lat": lat,
        "lon": lon,
        "event_date": event_date,
        "genre": genre,
    }


def test_empty_input_returns_empty_list():
    assert aggregate_by_city([]) == []


def test_groups_events_by_city_with_correct_counts():
    events = [
        _make_event(event_id="a1", city="Austin"),
        _make_event(event_id="a2", city="Austin"),
        _make_event(event_id="d1", city="Denver"),
    ]

    aggregates = {a["city"]: a for a in aggregate_by_city(events)}

    assert aggregates["Austin"]["event_count"] == 2
    assert aggregates["Denver"]["event_count"] == 1


def test_genre_breakdown_counts_and_buckets_missing_as_unknown():
    events = [
        _make_event(event_id="a1", genre="Rock"),
        _make_event(event_id="a2", genre="Rock"),
        _make_event(event_id="a3", genre=None),
    ]

    aggregates = aggregate_by_city(events)

    assert aggregates[0]["genre_breakdown"] == {"Rock": 2, "Unknown": 1}
    assert sum(aggregates[0]["genre_breakdown"].values()) == aggregates[0]["event_count"]


def test_lat_lon_averaged_across_events_in_same_city():
    events = [
        _make_event(event_id="a1", lat=30.0, lon=-97.0),
        _make_event(event_id="a2", lat=32.0, lon=-99.0),
    ]

    aggregates = aggregate_by_city(events)

    assert aggregates[0]["lat"] == 31.0
    assert aggregates[0]["lon"] == -98.0


def test_lat_lon_none_when_no_events_have_coordinates():
    events = [_make_event(event_id="a1", lat=None, lon=None)]

    aggregates = aggregate_by_city(events)

    assert aggregates[0]["lat"] is None
    assert aggregates[0]["lon"] is None


def test_date_range_ignores_events_with_missing_date():
    events = [
        _make_event(event_id="a1", event_date="2026-10-05"),
        _make_event(event_id="a2", event_date="2026-09-20"),
        _make_event(event_id="a3", event_date=None),
    ]

    aggregates = aggregate_by_city(events)

    assert aggregates[0]["date_range_start"] == "2026-09-20"
    assert aggregates[0]["date_range_end"] == "2026-10-05"
    assert aggregates[0]["event_count"] == 3
