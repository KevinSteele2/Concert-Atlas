from unittest.mock import patch

from pull_prices import main


@patch("pull_prices.append_snapshots")
@patch("pull_prices.fetch_events")
def test_main_fetches_and_stores_for_given_city(mock_fetch_events, mock_append_snapshots):
    mock_fetch_events.return_value = [
        {"event_id": "e1", "price_min": 45.0},
        {"event_id": "e2", "price_min": None},
    ]

    main(["Austin"])

    mock_fetch_events.assert_called_once_with("Austin", max_pages=None)
    mock_append_snapshots.assert_called_once_with(mock_fetch_events.return_value)


@patch("pull_prices.append_snapshots")
@patch("pull_prices.fetch_events")
def test_main_passes_through_max_pages(mock_fetch_events, mock_append_snapshots):
    mock_fetch_events.return_value = []

    main(["Austin", "--max-pages", "2"])

    mock_fetch_events.assert_called_once_with("Austin", max_pages=2)
