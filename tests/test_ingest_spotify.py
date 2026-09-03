from unittest.mock import MagicMock, patch

import pytest

from data.ingest_spotify import fetch_artist_metrics


def _make_token_response():
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "fake-token"}
    mock_response.raise_for_status.return_value = None
    return mock_response


def _make_search_response(items):
    mock_response = MagicMock()
    mock_response.json.return_value = {"artists": {"items": items}}
    mock_response.raise_for_status.return_value = None
    return mock_response


def _make_artist_item(artist_id="abc123", popularity=80, followers=1_000_000, genres=None):
    return {
        "id": artist_id,
        "popularity": popularity,
        "followers": {"total": followers},
        "genres": genres if genres is not None else ["pop", "r&b"],
    }


@patch("data.ingest_spotify.time.sleep")
@patch("data.ingest_spotify.requests.get")
@patch("data.ingest_spotify.requests.post")
def test_happy_path_maps_all_fields(mock_post, mock_get, mock_sleep):
    mock_post.return_value = _make_token_response()
    mock_get.return_value = _make_search_response([_make_artist_item()])

    results = fetch_artist_metrics(
        ["Rod Wave"], client_id="fake-id", client_secret="fake-secret"
    )

    assert len(results) == 1
    record = results[0]
    assert record["artist"] == "Rod Wave"
    assert record["spotify_artist_id"] == "abc123"
    assert record["popularity"] == 80
    assert record["followers"] == 1_000_000
    assert record["genres"] == "pop,r&b"
    assert record["fetched_date"]


@patch("data.ingest_spotify.time.sleep")
@patch("data.ingest_spotify.requests.get")
@patch("data.ingest_spotify.requests.post")
def test_no_match_included_with_none_fields(mock_post, mock_get, mock_sleep):
    mock_post.return_value = _make_token_response()
    mock_get.return_value = _make_search_response([])

    results = fetch_artist_metrics(
        ["Totally Unknown Artist"], client_id="fake-id", client_secret="fake-secret"
    )

    assert len(results) == 1
    record = results[0]
    assert record["artist"] == "Totally Unknown Artist"
    assert record["spotify_artist_id"] is None
    assert record["popularity"] is None
    assert record["followers"] is None
    assert record["genres"] is None


@patch("data.ingest_spotify.time.sleep")
@patch("data.ingest_spotify.requests.get")
@patch("data.ingest_spotify.requests.post")
def test_duplicate_names_deduped_to_one_call_and_one_record(mock_post, mock_get, mock_sleep):
    mock_post.return_value = _make_token_response()
    mock_get.return_value = _make_search_response([_make_artist_item()])

    results = fetch_artist_metrics(
        ["Rod Wave", "Rod Wave"], client_id="fake-id", client_secret="fake-secret"
    )

    assert mock_get.call_count == 1
    assert len(results) == 1


@patch("data.ingest_spotify.requests.get")
@patch("data.ingest_spotify.requests.post")
def test_missing_credentials_raises_before_any_request(mock_post, mock_get, monkeypatch):
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    with patch("data.ingest_spotify.load_dotenv"):
        with pytest.raises(ValueError):
            fetch_artist_metrics(["Rod Wave"], client_id=None, client_secret=None)

    mock_post.assert_not_called()
    mock_get.assert_not_called()


@patch("data.ingest_spotify.time.sleep")
@patch("data.ingest_spotify.requests.get")
@patch("data.ingest_spotify.requests.post")
def test_malformed_artist_is_skipped_others_still_returned(mock_post, mock_get, mock_sleep):
    mock_post.return_value = _make_token_response()

    malformed_response = MagicMock()
    malformed_response.json.return_value = {"artists": {"items": [{"id": "no-popularity-field"}]}}
    malformed_response.raise_for_status.return_value = None

    good_response = _make_search_response([_make_artist_item()])
    mock_get.side_effect = [malformed_response, good_response]

    results = fetch_artist_metrics(
        ["Broken Artist", "Rod Wave"], client_id="fake-id", client_secret="fake-secret"
    )

    assert len(results) == 1
    assert results[0]["artist"] == "Rod Wave"
