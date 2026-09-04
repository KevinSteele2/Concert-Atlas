"""Rolls raw per-event data into per-city aggregates for the activity map."""

from collections import Counter, defaultdict
from datetime import datetime, timezone

UNKNOWN_GENRE = "Unknown"


def aggregate_by_city(events: list[dict]) -> list[dict]:
    """Group raw event dicts by city and compute per-city stats.

    Matches the city-aggregate data model from CLAUDE.md: city, state, lat, lon,
    event_count, genre_breakdown, date_range_start, date_range_end, pulled_at.
    """
    if not events:
        return []

    pulled_at = datetime.now(timezone.utc).isoformat()

    by_city = defaultdict(list)
    for event in events:
        by_city[event["city"]].append(event)

    aggregates = []
    for city, city_events in by_city.items():
        genre_breakdown = Counter(e.get("genre") or UNKNOWN_GENRE for e in city_events)

        state = next((e["state"] for e in city_events if e.get("state")), None)

        lats = [e["lat"] for e in city_events if e.get("lat") is not None]
        lons = [e["lon"] for e in city_events if e.get("lon") is not None]
        lat = sum(lats) / len(lats) if lats else None
        lon = sum(lons) / len(lons) if lons else None

        dates = sorted(e["event_date"] for e in city_events if e.get("event_date"))
        date_range_start = dates[0] if dates else None
        date_range_end = dates[-1] if dates else None

        aggregates.append(
            {
                "city": city,
                "state": state,
                "lat": lat,
                "lon": lon,
                "event_count": len(city_events),
                "genre_breakdown": dict(genre_breakdown),
                "date_range_start": date_range_start,
                "date_range_end": date_range_end,
                "pulled_at": pulled_at,
            }
        )

    return aggregates
