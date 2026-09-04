"""Pulls music events for a city (or cities) from the Ticketmaster Discovery API."""

import logging
import os
import time

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

DISCOVERY_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
PAGE_SIZE = 200
REQUEST_DELAY_SECONDS = 0.25  # keeps us under the 5 req/sec rate limit
MAX_PAGING_DEPTH = 1000  # Ticketmaster hard limit: page * size must stay under this


def fetch_events_for_cities(
    cities: list[str], api_key: str | None = None, max_pages: int | None = None
) -> list[dict]:
    """Fetch music events across multiple cities, concatenated into one list."""
    if api_key is None:
        load_dotenv()
        api_key = os.environ.get("TICKETMASTER_API_KEY")
    if not api_key:
        raise ValueError(
            "No Ticketmaster API key provided and TICKETMASTER_API_KEY is not set in .env"
        )

    events = []
    for city in cities:
        events.extend(fetch_events(city, api_key=api_key, max_pages=max_pages))
    return events


def fetch_events(city: str, api_key: str | None = None, max_pages: int | None = None) -> list[dict]:
    """Fetch music events for a city and return them as raw event dicts.

    Each dict matches the raw event data model from CLAUDE.md: event_id, artist,
    venue, city, state, lat, lon, event_date, genre.
    """
    if api_key is None:
        load_dotenv()
        api_key = os.environ.get("TICKETMASTER_API_KEY")
    if not api_key:
        raise ValueError(
            "No Ticketmaster API key provided and TICKETMASTER_API_KEY is not set in .env"
        )

    events = []
    page = 0
    total_pages = 1
    call_count = 0

    while page < total_pages:
        if max_pages is not None and page >= max_pages:
            break
        if page * PAGE_SIZE >= MAX_PAGING_DEPTH:
            logger.info(
                "Reached Ticketmaster's max paging depth for city=%s; stopping at %d events",
                city,
                len(events),
            )
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
                events.append(_parse_event(raw_event, city))
            except (KeyError, IndexError, TypeError) as exc:
                logger.warning(
                    "Skipping malformed event %s: %s", raw_event.get("id", "<unknown>"), exc
                )

        page += 1
        if page < total_pages and (max_pages is None or page < max_pages):
            time.sleep(REQUEST_DELAY_SECONDS)

    return events


def _parse_event(event: dict, queried_city: str) -> dict:
    attractions = event.get("_embedded", {}).get("attractions") or []
    if attractions:
        artist = attractions[0]["name"]
    else:
        artist = event["name"]
        logger.debug("Event %s has no attractions, falling back to event name", event.get("id"))

    venues = event.get("_embedded", {}).get("venues") or []
    if venues:
        venue_data = venues[0]
        venue = venue_data.get("name")
        event_city = venue_data.get("city", {}).get("name", queried_city)
        state = venue_data.get("state", {}).get("stateCode")

        location = venue_data.get("location") or {}
        lat = float(location["latitude"]) if "latitude" in location else None
        lon = float(location["longitude"]) if "longitude" in location else None
        if lat is None or lon is None:
            logger.warning("Event %s has no venue coordinates", event.get("id"))
    else:
        venue = None
        event_city = queried_city
        state = None
        lat = None
        lon = None
        logger.warning("Event %s has no venue data", event.get("id"))

    event_date = event.get("dates", {}).get("start", {}).get("localDate")
    if event_date is None:
        logger.warning("Event %s has no event_date (likely date-TBD)", event.get("id"))

    classifications = event.get("classifications") or []
    if classifications:
        genre = classifications[0].get("genre", {}).get("name")
    else:
        genre = None
    if genre is None:
        logger.info("Event %s has no genre data", event.get("id"))

    return {
        "event_id": event["id"],
        "artist": artist,
        "venue": venue,
        "city": event_city,
        "state": state,
        "lat": lat,
        "lon": lon,
        "event_date": event_date,
        "genre": genre,
    }
