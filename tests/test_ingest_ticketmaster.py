from unittest.mock import MagicMock, patch

import pytest
import requests

from data.ingest_ticketmaster import MAX_429_RETRIES, _RateLimiter, fetch_events, fetch_events_for_cities


def _make_event(
    event_id="G5vYZ9",
    name="Fallback Event Name",
    artist="The Testers",
    venue="Test Arena",
    city="Austin",
    state="TX",
    event_date="2026-10-01",
    lat=30.280735,
    lon=-97.730837,
    genre="Hip-Hop/Rap",
    include_attractions=True,
    include_venue=True,
    include_location=True,
    include_classification=True,
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
        venue_data = {"name": venue, "city": {"name": city}, "state": {"stateCode": state}}
        if include_location:
            venue_data["location"] = {"latitude": str(lat), "longitude": str(lon)}
        event["_embedded"]["venues"] = [venue_data]
    if include_classification:
        event["classifications"] = [{"genre": {"name": genre}}]
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
    assert record["state"] == "TX"
    assert record["event_date"] == "2026-10-01"
    assert record["lat"] == 30.280735
    assert record["lon"] == -97.730837
    assert record["genre"] == "Hip-Hop/Rap"


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_missing_location_and_genre_are_included_with_none(mock_get, mock_sleep):
    mock_get.return_value = _make_response(
        [_make_event(include_location=False, include_classification=False)]
    )

    results = fetch_events("Austin", api_key="fake-key")

    assert len(results) == 1
    assert results[0]["lat"] is None
    assert results[0]["lon"] is None
    assert results[0]["genre"] is None


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_city_name_whitespace_is_stripped(mock_get, mock_sleep):
    mock_get.return_value = _make_response([_make_event(city=" Miami")])

    results = fetch_events("Miami", country_code="US", api_key="fake-key")

    assert results[0]["city"] == "Miami"


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_positive_longitude_dropped_for_us_events(mock_get, mock_sleep):
    # Real bug seen live: a Ticketmaster venue with a missing minus sign
    # (lon=80.2 instead of -80.2), which would otherwise place a Miami venue
    # in the Atlantic Ocean.
    mock_get.return_value = _make_response([_make_event(city="Miami", lat=25.8, lon=80.2)])

    results = fetch_events("Miami", country_code="US", api_key="fake-key")

    assert results[0]["lat"] is None
    assert results[0]["lon"] is None


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_positive_longitude_kept_when_country_code_not_us(mock_get, mock_sleep):
    mock_get.return_value = _make_response([_make_event(city="London", lat=51.5, lon=0.1)])

    results = fetch_events("London", country_code="GB", api_key="fake-key")

    assert results[0]["lon"] == 0.1


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


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_stops_before_exceeding_ticketmaster_paging_depth_limit(mock_get, mock_sleep):
    # PAGE_SIZE is 200, so Ticketmaster's page*size<1000 limit allows pages 0-4 (5 pages).
    mock_get.return_value = _make_response([_make_event()], total_pages=50, page_number=0)

    fetch_events("Austin", api_key="fake-key")

    assert mock_get.call_count == 5
    assert all(call.kwargs["params"]["page"] < 5 for call in mock_get.call_args_list)


@patch("data.ingest_ticketmaster.requests.get")
def test_missing_api_key_raises_before_any_request(mock_get, monkeypatch):
    monkeypatch.delenv("TICKETMASTER_API_KEY", raising=False)
    with patch("data.ingest_ticketmaster.load_dotenv"):
        with pytest.raises(ValueError):
            fetch_events("Austin", api_key=None)

    mock_get.assert_not_called()


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_fetch_events_for_cities_concatenates_results(mock_get, mock_sleep):
    responses_by_city = {
        "Austin": _make_response([_make_event(event_id="austin-event", city="Austin")]),
        "Denver": _make_response([_make_event(event_id="denver-event", city="Denver")]),
    }
    # Cities are fetched concurrently, so responses must be looked up by request
    # params rather than assumed to arrive in input order.
    mock_get.side_effect = lambda *args, **kwargs: responses_by_city[kwargs["params"]["city"]]

    results = fetch_events_for_cities(["Austin", "Denver"], api_key="fake-key")

    assert mock_get.call_count == 2
    assert {r["event_id"] for r in results} == {"austin-event", "denver-event"}
    called_cities = {call.kwargs["params"]["city"] for call in mock_get.call_args_list}
    assert called_cities == {"Austin", "Denver"}


@patch("data.ingest_ticketmaster.requests.get")
def test_fetch_events_for_cities_missing_api_key_raises_before_any_request(mock_get, monkeypatch):
    monkeypatch.delenv("TICKETMASTER_API_KEY", raising=False)
    with patch("data.ingest_ticketmaster.load_dotenv"):
        with pytest.raises(ValueError):
            fetch_events_for_cities(["Austin"], api_key=None)

    mock_get.assert_not_called()


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_fetch_events_includes_country_code_when_given(mock_get, mock_sleep):
    mock_get.return_value = _make_response([_make_event()])

    fetch_events("Sydney", country_code="AU", api_key="fake-key")

    assert mock_get.call_args.kwargs["params"]["countryCode"] == "AU"


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_fetch_events_omits_country_code_when_not_given(mock_get, mock_sleep):
    mock_get.return_value = _make_response([_make_event()])

    fetch_events("Austin", api_key="fake-key")

    assert "countryCode" not in mock_get.call_args.kwargs["params"]


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_fetch_events_for_cities_accepts_mixed_plain_and_tuple_entries(mock_get, mock_sleep):
    responses_by_city = {
        "Austin": _make_response([_make_event(event_id="austin-event", city="Austin")]),
        "Sydney": _make_response([_make_event(event_id="sydney-event", city="Sydney")]),
    }
    mock_get.side_effect = lambda *args, **kwargs: responses_by_city[kwargs["params"]["city"]]

    results = fetch_events_for_cities(["Austin", ("Sydney", "AU")], api_key="fake-key")

    assert {r["event_id"] for r in results} == {"austin-event", "sydney-event"}
    calls_by_city = {call.kwargs["params"]["city"]: call.kwargs["params"] for call in mock_get.call_args_list}
    assert "countryCode" not in calls_by_city["Austin"]
    assert calls_by_city["Sydney"]["countryCode"] == "AU"


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.time.monotonic")
def test_rate_limiter_waits_when_called_again_too_soon(mock_monotonic, mock_sleep):
    limiter = _RateLimiter(min_interval=0.25)
    mock_monotonic.side_effect = [100.0, 100.0, 100.1, 100.1]

    limiter.wait()
    limiter.wait()

    mock_sleep.assert_called_once_with(pytest.approx(0.15))


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.time.monotonic")
def test_rate_limiter_does_not_wait_once_enough_time_has_passed(mock_monotonic, mock_sleep):
    limiter = _RateLimiter(min_interval=0.25)
    mock_monotonic.side_effect = [100.0, 100.0, 100.5, 100.5]

    limiter.wait()
    limiter.wait()

    mock_sleep.assert_not_called()


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_retries_on_429_then_succeeds(mock_get, mock_sleep):
    rate_limited_response = MagicMock(status_code=429, headers={"Retry-After": "2"})
    success_response = _make_response([_make_event()])
    success_response.status_code = 200
    mock_get.side_effect = [rate_limited_response, success_response]

    results = fetch_events("Austin", api_key="fake-key")

    assert len(results) == 1
    assert mock_get.call_count == 2
    mock_sleep.assert_any_call(2.0)


@patch("data.ingest_ticketmaster.time.sleep")
@patch("data.ingest_ticketmaster.requests.get")
def test_raises_after_exhausting_429_retries(mock_get, mock_sleep):
    rate_limited_response = MagicMock(status_code=429, headers={})
    rate_limited_response.raise_for_status.side_effect = requests.exceptions.HTTPError("429")
    mock_get.return_value = rate_limited_response

    with pytest.raises(requests.exceptions.HTTPError):
        fetch_events("Austin", api_key="fake-key")

    assert mock_get.call_count == MAX_429_RETRIES + 1
