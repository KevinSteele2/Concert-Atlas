# Live Music Activity Map

An interactive map showing upcoming concert activity across US cities, built
from the Ticketmaster Discovery API, opening as its own desktop window (no
browser, no terminal). Every run pulls fresh data automatically, with a
loading screen while it does. Click a city marker to see its actual upcoming
shows in a slide-out panel.

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
- A loading screen (pulsing dots, live status text) shown in the app window
  itself while data is being fetched, so there's something to look at besides
  a blank window for the ~20-40 seconds a full pull takes

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
  few events under "Hollywood," for example — the map shows these as
  separate nearby markers rather than one consolidated one. (Leading/trailing
  whitespace variants of the *same* city name, e.g. `"Miami"` vs `" Miami"`,
  are normalized and merged automatically — this quirk is only about
  genuinely different city names.)
- **Bad coordinates in Ticketmaster's own data**: occasionally a venue's
  longitude is corrupted at the source (e.g. missing its minus sign, which
  once placed a Miami venue in the Atlantic Ocean on this map). Since every
  city in `DEFAULT_CITIES` is in the US, any event with a *positive*
  longitude is treated as bad data and dropped rather than trusted.
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

**Easiest way**: double-click `Launch Map.bat` in the project folder — no
terminal involved. It opens the app window immediately with a loading screen
("Fetching events across 42 cities…" etc.), then swaps over to the finished
map once the pull completes. No console window appears at any point; if
something goes wrong, the error shows up inside the app window itself rather
than a terminal.

Or from a terminal, with dependencies installed (see Setup above):
```
python -m viz.build_map
```
This is equivalent to the `.bat` file but with live log output in the
terminal — useful if you want to see what's happening under the hood or are
debugging something. It always pulls fresh data for the default set of 42
US cities (see `DEFAULT_CITIES` in `viz/build_map.py`) — there's no manual
refresh step or flag; every run is current as of when you ran it. City
pulls run concurrently (multiple cities fetched in parallel threads, all
sharing one rate limiter so Ticketmaster's 5 req/sec cap is still respected,
with automatic retry if a request gets rate-limited anyway), so a full pull
typically finishes in well under a minute.

Or specify your own cities from the terminal:
```
python -m viz.build_map Austin Denver Chicago
```

This also writes a self-contained file to `outputs/city_map.html`, so you
can reopen the last-generated map anytime by double-clicking that file —
it'll open in your browser rather than its own window, but the map itself
(zoom, pan, click-to-drill-down) works the same either way. Note it won't
have the latest data unless you run `python -m viz.build_map` again first.

## Running tests

```
python -m pytest tests/ -v
```
(If `pytest` isn't recognized directly in PowerShell, use `python -m pytest`
— pip installs its script outside the default PATH on some setups.)

All tests mock external APIs and use temp files — nothing hits the real
Ticketmaster/Spotify APIs or writes to `outputs/` during test runs.
