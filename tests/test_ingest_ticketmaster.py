from unittest.mock import MagicMock, patch

import pytest

from data.ingest_ticketmaster import fetch_events


def _make_event(
    event_id="G5vYZ9",
    name="Fallback Event Name",
    artist="The Testers",
    venue="Test Arena",
    city="Austin",
    event_date="2026-10-01",
    price_min=45.0,
    price_max=250.0,
    include_attractions=True,
    include_venue=True,
    include_price=True,
):
    event = {
        "id": event_id,
        "name": name,
        "dates": {"start": {"localDate": event_date}},
        "_embedded": {},
    }
    if include_attractions:
        event["_embedded"]["attractions"] = [{"name": artist}]
    if include_venue:
        event["_embedded"]["venues"] = [{"name": venue, "city": {"name": city}}]
    if include_price:
        event["priceRanges"] = [{"type": "standard", "currency": "USD", "min": price_min, "max": price_max}]
    return event


def _make_response(events, total_pages=1, page_number=0):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "_embedded": {"events": events} if events else {},
        "page": {"size": 200, "totalPages": total_pages, "number": page_number},
    }
    mock_response.raise_for_status.return_value = None
    return mock_response


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_happy_path_maps_all_fields(mock_get, mock_sleep):
    mock_get.return_value = _make_response([_make_event()])

    results = fetch_events("Austin", api_key="fake-key")

    assert len(results) == 1
    record = results[0]
    assert record["event_id"] == "G5vYZ9"
    assert record["artist"] == "The Testers"
    assert record["venue"] == "Test Arena"
    assert record["city"] == "Austin"
    assert record["event_date"] == "2026-10-01"
    assert record["price_min"] == 45.0
    assert record["price_max"] == 250.0
    assert record["snapshot_date"] == record["first_seen_date"]


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_missing_price_data_is_included_with_none(mock_get, mock_sleep):
    mock_get.return_value = _make_response([_make_event(include_price=False)])

    results = fetch_events("Austin", api_key="fake-key")

    assert len(results) == 1
    assert results[0]["price_min"] is None
    assert results[0]["price_max"] is None


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_missing_attractions_falls_back_to_event_name(mock_get, mock_sleep):
    mock_get.return_value = _make_response(
        [_make_event(name="Fallback Event Name", include_attractions=False)]
    )

    results = fetch_events("Austin", api_key="fake-key")

    assert results[0]["artist"] == "Fallback Event Name"


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_no_events_returns_empty_list(mock_get, mock_sleep):
    mock_get.return_value = _make_response([])

    results = fetch_events("Nowhereville", api_key="fake-key")

    assert results == []


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_pagination_fetches_all_pages(mock_get, mock_sleep):
    page0 = _make_response([_make_event(event_id="page0-event")], total_pages=2, page_number=0)
    page1 = _make_response([_make_event(event_id="page1-event")], total_pages=2, page_number=1)
    mock_get.side_effect = [page0, page1]

    results = fetch_events("Austin", api_key="fake-key")

    assert mock_get.call_count == 2
    assert {r["event_id"] for r in results} == {"page0-event", "page1-event"}
    assert mock_get.call_args_list[0].kwargs["params"]["page"] == 0
    assert mock_get.call_args_list[1].kwargs["params"]["page"] == 1


@patch("data.ingest_ticketmaster.requests.get")
def test_missing_api_key_raises_before_any_request(mock_get, monkeypatch):
    monkeypatch.delenv("TICKETMASTER_API_KEY", raising=False)
    with patch("data.ingest_ticketmaster.load_dotenv"):
        with pytest.raises(ValueError):
            fetch_events("Austin", api_key=None)

    mock_get.assert_not_called()
