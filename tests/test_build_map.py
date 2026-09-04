import json

from viz.build_map import build_map


def _make_aggregate(city="Austin", state="TX", lat=30.0, lon=-97.0, event_count=5):
    return {
        "city": city,
        "state": state,
        "lat": lat,
        "lon": lon,
        "event_count": event_count,
        "genre_breakdown": {"Rock": event_count},
        "date_range_start": "2026-09-04",
        "date_range_end": "2026-12-01",
        "pulled_at": "2026-09-04T12:00:00+00:00",
    }


def _make_event(city="Austin", artist="The Testers", venue="Test Arena", event_date="2026-10-01"):
    return {
        "event_id": "e1",
        "artist": artist,
        "venue": venue,
        "city": city,
        "state": "TX",
        "lat": 30.0,
        "lon": -97.0,
        "event_date": event_date,
        "genre": "Rock",
    }


def test_build_map_creates_nonempty_html_with_city_names(tmp_path):
    output_path = tmp_path / "map.html"
    aggregates = [_make_aggregate(city="Austin"), _make_aggregate(city="Denver")]
    events = [_make_event(city="Austin"), _make_event(city="Denver")]

    build_map(aggregates, events, output_path=output_path)

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert len(content) > 0
    assert "Austin" in content
    assert "Denver" in content


def test_build_map_empty_aggregates_does_not_crash_or_create_file(tmp_path):
    output_path = tmp_path / "map.html"

    build_map([], [], output_path=output_path)

    assert not output_path.exists()


def test_build_map_includes_event_panel_markup_and_click_handler(tmp_path):
    output_path = tmp_path / "map.html"
    aggregates = [_make_aggregate(city="Austin")]
    events = [_make_event(city="Austin")]

    build_map(aggregates, events, output_path=output_path)

    content = output_path.read_text(encoding="utf-8")
    assert 'id="event-panel"' in content
    assert "plotly_click" in content


def test_build_map_embeds_correct_events_per_city(tmp_path):
    output_path = tmp_path / "map.html"
    aggregates = [_make_aggregate(city="Austin"), _make_aggregate(city="Denver")]
    events = [
        _make_event(city="Austin", artist="Austin Artist", venue="Austin Venue"),
        _make_event(city="Denver", artist="Denver Artist", venue="Denver Venue"),
    ]

    build_map(aggregates, events, output_path=output_path)

    content = output_path.read_text(encoding="utf-8")
    start = content.index("const eventsByCity = ") + len("const eventsByCity = ")
    end = content.index(";\n", start)
    embedded = json.loads(content[start:end])

    assert embedded["Austin"][0]["artist"] == "Austin Artist"
    assert embedded["Austin"][0]["venue"] == "Austin Venue"
    assert embedded["Denver"][0]["artist"] == "Denver Artist"


def test_build_map_handles_city_with_no_events(tmp_path):
    output_path = tmp_path / "map.html"
    aggregates = [_make_aggregate(city="Austin")]

    build_map(aggregates, [], output_path=output_path)

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "const eventsByCity = {}" in content
