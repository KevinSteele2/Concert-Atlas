"""Pulls music events for a city (or cities) from the Ticketmaster Discovery API."""

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

DISCOVERY_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
PAGE_SIZE = 200
REQUEST_DELAY_SECONDS = 0.25  # keeps us under the 5 req/sec rate limit
MAX_PAGING_DEPTH = 1000  # Ticketmaster hard limit: page * size must stay under this
DEFAULT_MAX_WORKERS = 8  # cities fetched concurrently; the shared rate limiter caps actual req/sec
MAX_429_RETRIES = 5
DEFAULT_RETRY_AFTER_SECONDS = 1.0


class _RateLimiter:
    """Enforces a minimum interval between calls, shared safely across threads."""

    def __init__(self, min_interval: float):
        self._min_interval = min_interval
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()


def fetch_events_for_cities(
    cities: list[str | tuple[str, str | None]],
    api_key: str | None = None,
    max_pages: int | None = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> list[dict]:
    """Fetch music events across multiple cities concurrently, concatenated into one list.

    Each entry in `cities` is either a plain city name, or a `(city, country_code)`
    tuple to disambiguate cities whose names collide across countries (e.g. Sydney,
    Australia vs. Sydney, Nova Scotia). Cities are fetched in parallel threads, all
    sharing one rate limiter, so the combined request rate still stays under
    Ticketmaster's 5 req/sec cap regardless of how many cities are in flight.
    """
    if api_key is None:
        load_dotenv()
        api_key = os.environ.get("TICKETMASTER_API_KEY")
    if not api_key:
        raise ValueError(
            "No Ticketmaster API key provided and TICKETMASTER_API_KEY is not set in .env"
        )

    rate_limiter = _RateLimiter(REQUEST_DELAY_SECONDS)

    def _fetch_entry(entry: str | tuple[str, str | None]) -> list[dict]:
        city, country_code = entry if isinstance(entry, tuple) else (entry, None)
        return fetch_events(
            city,
            country_code=country_code,
            api_key=api_key,
            max_pages=max_pages,
            rate_limiter=rate_limiter,
        )

    events = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for city_events in executor.map(_fetch_entry, cities):
            events.extend(city_events)
    return events


def fetch_events(
    city: str,
    country_code: str | None = None,
    api_key: str | None = None,
    max_pages: int | None = None,
    rate_limiter: _RateLimiter | None = None,
) -> list[dict]:
    """Fetch music events for a city and return them as raw event dicts.

    Each dict matches the raw event data model from CLAUDE.md: event_id, artist,
    venue, city, state, lat, lon, event_date, genre. Pass `country_code` (e.g. "AU")
    to disambiguate cities whose names collide across countries.
    """
    if api_key is None:
        load_dotenv()
        api_key = os.environ.get("TICKETMASTER_API_KEY")
    if not api_key:
        raise ValueError(
            "No Ticketmaster API key provided and TICKETMASTER_API_KEY is not set in .env"
        )

    if rate_limiter is None:
        rate_limiter = _RateLimiter(REQUEST_DELAY_SECONDS)

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
        if country_code:
            params["countryCode"] = country_code

        for attempt in range(MAX_429_RETRIES + 1):
            rate_limiter.wait()
            response = requests.get(DISCOVERY_URL, params=params, timeout=10)
            if response.status_code != 429:
                break
            retry_after = float(response.headers.get("Retry-After", DEFAULT_RETRY_AFTER_SECONDS))
            logger.warning(
                "Rate limited (429) for city=%s page=%d; retrying in %.1fs (attempt %d/%d)",
                city,
                page,
                retry_after,
                attempt + 1,
                MAX_429_RETRIES,
            )
            time.sleep(retry_after)

        response.raise_for_status()
        call_count += 1
        logger.info("Ticketmaster API call #%d (page %d) for city=%s", call_count, page, city)

        data = response.json()
        total_pages = data.get("page", {}).get("totalPages", 1)
        raw_events = data.get("_embedded", {}).get("events", [])

        for raw_event in raw_events:
            try:
                events.append(_parse_event(raw_event, city, country_code))
            except (KeyError, IndexError, TypeError) as exc:
                logger.warning(
                    "Skipping malformed event %s: %s", raw_event.get("id", "<unknown>"), exc
                )

        page += 1

    return events


def _parse_event(event: dict, queried_city: str, country_code: str | None = None) -> dict:
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
        event_city = venue_data.get("city", {}).get("name", queried_city).strip()
        state = venue_data.get("state", {}).get("stateCode")

        location = venue_data.get("location") or {}
        lat = float(location["latitude"]) if "latitude" in location else None
        lon = float(location["longitude"]) if "longitude" in location else None
        if lat is None or lon is None:
            logger.warning("Event %s has no venue coordinates", event.get("id"))
        elif country_code == "US" and lon > 0:
            # The US is entirely in the western hemisphere (negative longitude).
            # A positive value here is source-data corruption (e.g. a missing
            # minus sign), not a real location - drop it rather than trust it.
            logger.warning(
                "Event %s has an implausible longitude %.4f for country_code=US "
                "(likely a sign error in source data); dropping coordinates",
                event.get("id"),
                lon,
            )
            lat, lon = None, None
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
