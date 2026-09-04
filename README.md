# Live Music Activity Map

An interactive map showing upcoming concert activity across US cities, built
from the Ticketmaster Discovery API. Click a city marker to see its actual
upcoming shows in a slide-out panel. See [CLAUDE.md](CLAUDE.md) for the full
data model and architecture.

(This project pivoted from an earlier ticket-price-tracking concept — most
Ticketmaster events never expose price data, which made that version
impractical. See git history if you're curious what that looked like.)

## Status: work in progress

What works today:
- Pulling real music events across a list of cities from Ticketmaster
  (`data/ingest_ticketmaster.py`)
- Rolling raw events into per-city stats — event count, genre breakdown,
  averaged coordinates, date range (`data/aggregate.py`)
- An interactive map (`viz/build_map.py`): scroll wheel to zoom, click-and-drag
  to pan, hover a city for a quick summary, click a city to slide out a panel
  listing its real upcoming events

Not built yet: genre/date-range filtering on the map, and anything using
`data/ingest_spotify.py` (artist popularity enrichment — built and tested,
but unused; see the note below).

### Known data quirks

- **Pagination cap**: Ticketmaster hard-limits paging to `page * size < 1000`,
  so very active cities (e.g. New York) are capped at ~999 events per pull,
  not their true total. `fetch_events` stops cleanly at that limit rather
  than erroring.
- **City fragmentation**: events are grouped by each *venue's own* reported
  city, not the city you searched for. Since Ticketmaster's city search
  returns a metro-area radius, searching "Los Angeles" can also surface a
  few events under "Hollywood," for example. The map will show these as
  separate nearby markers rather than one consolidated one.
- **Spotify enrichment is on hold**: `data/ingest_spotify.py` works against
  mocked data but not the real API — Spotify now restricts `popularity`,
  `followers`, and `genres` to apps with approved "Extended Quota Mode"
  access. [Last.fm](https://www.last.fm/api) is the planned replacement if
  artist-level enrichment gets revisited.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Create a `.env` file in the project root (not committed) with:
   ```
   TICKETMASTER_API_KEY=your_key_here
   ```
   (`SPOTIFY_CLIENT_ID`/`SPOTIFY_CLIENT_SECRET` are only needed if you're
   working on the dormant Spotify enrichment piece.)

## Usage

Generate the map for a default set of 15 major US cities and open it in your
browser:
```
python -m viz.build_map
```

Or specify your own cities:
```
python -m viz.build_map Austin Denver Chicago
```

This writes a self-contained file to `outputs/city_map.html` — open it
directly in any browser, no server needed.

## Running tests

```
python -m pytest tests/ -v
```
(If `pytest` isn't recognized directly in PowerShell, use `python -m pytest`
— pip installs its script outside the default PATH on some setups.)

All tests mock external APIs and use temp files — nothing hits the real
Ticketmaster/Spotify APIs or writes to `outputs/` during test runs.
