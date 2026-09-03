# Concert Ticket Pricing Prediction Application

Tracks concert ticket prices over time by periodically pulling events from the
Ticketmaster Discovery API, and (eventually) predicts future price movement.
See [CLAUDE.md](CLAUDE.md) for the full data model and architecture.

## Status: work in progress

What works today:
- Pulling real music events + prices for a city from Ticketmaster
- Appending them as snapshots to a local CSV store
- Cleaning that store into a modeling-ready table
- Rendering a chart of currently known ticket prices

What's not built yet: recurring/scheduled pulls, artist popularity enrichment,
and the actual price prediction model (`models/train.py`, `models/forecast.py`).

### A known data limitation

Most Ticketmaster events never expose price data through this API, even once
on sale — it's populated at the promoter's discretion, and large arena tours
with dynamic/platinum pricing frequently omit it entirely. Coverage is much
better in smaller markets (e.g. ~50%+ in a city like Boise) than in major
metros (often <5% in NYC, LA, Chicago). This means the chart and model will
be sparse until enough events with real pricing accumulate, and are more
useful for small/mid-market shows than headline arena tours.

Spotify artist-popularity enrichment (`data/ingest_spotify.py`) is built and
tested but not wired into the pipeline — Spotify now restricts the
`popularity`/`followers`/`genres` fields to apps with approved "Extended
Quota Mode" access. [Last.fm](https://www.last.fm/api) is the planned
replacement data source for this later.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Create a `.env` file in the project root (not committed) with:
   ```
   TICKETMASTER_API_KEY=your_key_here
   SPOTIFY_CLIENT_ID=your_id_here
   SPOTIFY_CLIENT_SECRET=your_secret_here
   ```

## Usage

Pull events for a city and store them as a snapshot:
```
python pull_prices.py Austin
```
(`--max-pages N` limits how many pages are fetched, useful for a quick test.)

Generate a chart of currently known prices (reads from `data/snapshots.csv`,
writes to `outputs/price_snapshot.png`):
```
python visualize_prices.py
```

Read the cleaned, modeling-ready snapshot table directly:
```python
from data.clean import clean_snapshots

df = clean_snapshots()  # drops events with no price data by default
```

## Running tests

```
python -m pytest tests/ -v
```
(If `pytest` isn't recognized directly in PowerShell, use `python -m pytest`
— pip installs its script outside the default PATH on some setups.)

All tests mock external APIs and use temp files — nothing hits the real
Ticketmaster/Spotify APIs or writes to the real `data/snapshots.csv` during
test runs.
