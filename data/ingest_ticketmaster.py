"""Pulls music events + prices for a city from the Ticketmaster Discovery API."""

import logging
import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

DISCOVERY_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
PAGE_SIZE = 200
REQUEST_DELAY_SECONDS = 0.25  # keeps us under the 5 req/sec rate limit


def fetch_events(city: str, api_key: str | None = None, max_pages: int | None = None) -> list[dict]:
    """Fetch music events for a city and return them as snapshot dicts.

    Each dict matches the snapshot data model from CLAUDE.md: event_id, artist,
    venue, city, event_date, price_min, price_max, snapshot_date, first_seen_date.
    first_seen_date is set equal to snapshot_date since this is the first pull.
    """
    if api_key is None:
        load_dotenv()
        api_key = os.environ.get("TICKETMASTER_API_KEY")
    if not api_key:
        raise ValueError(
            "No Ticketmaster API key provided and TICKETMASTER_API_KEY is not set in .env"
        )

    pulled_at = datetime.now(timezone.utc).isoformat()

    events = []
    page = 0
    total_pages = 1
    call_count = 0

    while page < total_pages:
        if max_pages is not None and page >= max_pages:
            break

        params = {
            "apikey": api_key,
            "city": city,
            "classificationName": "Music",
            "size": PAGE_SIZE,
            "page": page,
        }
        response = requests.get(DISCOVERY_URL, params=params, timeout=10)
        response.raise_for_status()
        call_count += 1
        logger.info("Ticketmaster API call #%d (page %d) for city=%s", call_count, page, city)

        data = response.json()
        total_pages = data.get("page", {}).get("totalPages", 1)
        raw_events = data.get("_embedded", {}).get("events", [])

        for raw_event in raw_events:
            try:
                events.append(_parse_event(raw_event, city, pulled_at))
            except (KeyError, IndexError, TypeError) as exc:
                logger.warning(
                    "Skipping malformed event %s: %s", raw_event.get("id", "<unknown>"), exc
                )

        page += 1
        if page < total_pages and (max_pages is None or page < max_pages):
            time.sleep(REQUEST_DELAY_SECONDS)

    return events


def _parse_event(event: dict, queried_city: str, pulled_at: str) -> dict:
    attractions = event.get("_embedded", {}).get("attractions") or []
    if attractions:
        artist = attractions[0]["name"]
    else:
        artist = event["name"]
        logger.debug("Event %s has no attractions, falling back to event name", event.get("id"))

    venues = event.get("_embedded", {}).get("venues") or []
    if venues:
        venue = venues[0].get("name")
        event_city = venues[0].get("city", {}).get("name", queried_city)
    else:
        venue = None
        event_city = queried_city
        logger.warning("Event %s has no venue data", event.get("id"))

    event_date = event.get("dates", {}).get("start", {}).get("localDate")
    if event_date is None:
        logger.warning("Event %s has no event_date (likely date-TBD)", event.get("id"))

    price_ranges = event.get("priceRanges") or []
    if price_ranges:
        price_min = price_ranges[0].get("min")
        price_max = price_ranges[0].get("max")
    else:
        price_min = None
        price_max = None
        logger.info("Event %s has no price data yet", event.get("id"))

    return {
        "event_id": event["id"],
        "artist": artist,
        "venue": venue,
        "city": event_city,
        "event_date": event_date,
        "price_min": price_min,
        "price_max": price_max,
        "snapshot_date": pulled_at,
        "first_seen_date": pulled_at,
    }
