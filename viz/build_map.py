"""Renders an interactive map of city-level concert activity."""

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.express as px

from data.aggregate import aggregate_by_city
from data.ingest_ticketmaster import fetch_events_for_cities

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("outputs") / "city_map.html"
TOP_GENRES_SHOWN = 3

# (city, country_code) pairs, curated from markets confirmed to have real
# Ticketmaster coverage.
DEFAULT_CITIES = [
    ("New York", "US"),
    ("Los Angeles", "US"),
    ("Chicago", "US"),
    ("Houston", "US"),
    ("Phoenix", "US"),
    ("Philadelphia", "US"),
    ("San Antonio", "US"),
    ("San Diego", "US"),
    ("Dallas", "US"),
    ("Austin", "US"),
    ("Denver", "US"),
    ("Seattle", "US"),
    ("Boston", "US"),
    ("Nashville", "US"),
    ("Atlanta", "US"),
    ("Miami", "US"),
    ("Las Vegas", "US"),
    ("San Francisco", "US"),
    ("Washington", "US"),
    ("Charlotte", "US"),
    ("Minneapolis", "US"),
    ("Detroit", "US"),
    ("Tampa", "US"),
    ("Orlando", "US"),
    ("Pittsburgh", "US"),
    ("Cleveland", "US"),
    ("St. Louis", "US"),
    ("Sacramento", "US"),
    ("Baltimore", "US"),
    ("Cincinnati", "US"),
    ("Raleigh", "US"),
    ("Salt Lake City", "US"),
    ("New Orleans", "US"),
    ("Indianapolis", "US"),
    ("Milwaukee", "US"),
    ("Memphis", "US"),
    ("Oklahoma City", "US"),
    ("Louisville", "US"),
    ("Buffalo", "US"),
    ("Albuquerque", "US"),
    ("Tucson", "US"),
    ("Honolulu", "US"),
]

PANEL_TEMPLATE = """
<style>
  #event-panel {{
    position: fixed;
    top: 0;
    right: 0;
    width: 340px;
    height: 100%;
    background: white;
    box-shadow: -2px 0 8px rgba(0, 0, 0, 0.2);
    transform: translateX(100%);
    transition: transform 0.25s ease-out;
    overflow-y: auto;
    z-index: 1000;
    padding: 16px;
    box-sizing: border-box;
    font-family: sans-serif;
  }}
  #event-panel.open {{
    transform: translateX(0);
  }}
  #event-panel .close-btn {{
    cursor: pointer;
    float: right;
    font-size: 20px;
    line-height: 1;
  }}
  #event-panel h2 {{
    margin: 0 0 12px 0;
    padding-right: 24px;
  }}
  #event-panel .event-item {{
    padding: 8px 0;
    border-bottom: 1px solid #eee;
  }}
  #event-panel .event-item .artist {{
    font-weight: bold;
  }}
</style>
<div id="event-panel">
  <span class="close-btn" onclick="document.getElementById('event-panel').classList.remove('open')">&times;</span>
  <h2 id="event-panel-title"></h2>
  <div id="event-panel-list"></div>
</div>
<script>
  const eventsByCity = {events_json};

  function escapeHtml(value) {{
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  }}

  function showCityEvents(city) {{
    const events = eventsByCity[city] || [];
    document.getElementById("event-panel-title").textContent = city + " (" + events.length + " events)";
    document.getElementById("event-panel-list").innerHTML = events
      .map(function (e) {{
        return (
          '<div class="event-item">' +
          '<div class="artist">' + escapeHtml(e.artist) + "</div>" +
          "<div>" + escapeHtml(e.venue) + "</div>" +
          "<div>" + escapeHtml(e.event_date) + "</div>" +
          "</div>"
        );
      }})
      .join("");
    document.getElementById("event-panel").classList.add("open");
  }}

  document.getElementById("city-map").on("plotly_click", function (data) {{
    const city = data.points[0].customdata[0];
    showCityEvents(city);
  }});
</script>
"""


def build_map(
    aggregates: list[dict], events: list[dict], output_path: Path | str = DEFAULT_OUTPUT_PATH
) -> None:
    """Render city aggregates as an interactive map with a click-to-drill-down event panel."""
    if not aggregates:
        logger.info("No city aggregates to map.")
        return

    df = pd.DataFrame(aggregates)
    df["top_genres"] = df["genre_breakdown"].apply(_format_top_genres)

    fig = px.scatter_map(
        df,
        lat="lat",
        lon="lon",
        size="event_count",
        color="event_count",
        size_max=40,
        hover_name="city",
        hover_data={
            "state": True,
            "event_count": True,
            "top_genres": True,
            "lat": False,
            "lon": False,
        },
        custom_data=["city"],
        map_style="open-street-map",
        title="Live Music Activity by City",
    )

    config = {
        "scrollZoom": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["select2d", "lasso2d"],
    }
    html = fig.to_html(full_html=True, config=config, div_id="city-map")
    events_json = json.dumps(_events_by_city(events))
    panel = PANEL_TEMPLATE.format(events_json=events_json)
    html = html.replace("</body>", panel + "</body>")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def _events_by_city(events: list[dict]) -> dict[str, list[dict]]:
    by_city = defaultdict(list)
    for event in events:
        by_city[event["city"]].append(
            {
                "artist": event.get("artist") or "Unknown Artist",
                "venue": event.get("venue") or "Unknown Venue",
                "event_date": event.get("event_date") or "TBD",
            }
        )

    for city_events in by_city.values():
        city_events.sort(key=lambda e: (e["event_date"] == "TBD", e["event_date"]))

    return dict(by_city)


def _format_top_genres(genre_breakdown: dict) -> str:
    top = sorted(genre_breakdown.items(), key=lambda item: item[1], reverse=True)[:TOP_GENRES_SHOWN]
    return ", ".join(f"{genre}: {count}" for genre, count in top)


LOADING_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  body {
    font-family: sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    margin: 0;
    background: #ffffff;
    color: #333;
  }
  .dots {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
  }
  .dots span {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #4dabf7;
    opacity: 0.3;
    animation: blink 1.4s infinite both;
  }
  .dots span:nth-child(2) { animation-delay: 0.2s; }
  .dots span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes blink {
    0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
    40% { opacity: 1; transform: scale(1); }
  }
  #status {
    font-size: 16px;
  }
  #status.error {
    color: #e03131;
    max-width: 500px;
    text-align: center;
  }
</style>
</head>
<body>
  <div class="dots" id="dots"><span></span><span></span><span></span></div>
  <div id="status">Starting…</div>
  <script>
    function updateStatus(text) {
      document.getElementById("status").textContent = text;
    }
    function showError(text) {
      document.getElementById("dots").style.display = "none";
      var el = document.getElementById("status");
      el.textContent = text;
      el.classList.add("error");
    }
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "cities",
        nargs="*",
        help=f"Cities to pull music events for (default: {len(DEFAULT_CITIES)} US cities)",
    )
    args = parser.parse_args()
    cities = args.cities or DEFAULT_CITIES

    import webview

    def _load_map(window):
        try:
            window.evaluate_js(
                f"updateStatus({json.dumps(f'Fetching events across {len(cities)} cities…')})"
            )
            events = fetch_events_for_cities(cities)
            window.evaluate_js(f"updateStatus({json.dumps('Building map…')})")
            aggregates = aggregate_by_city(events)
            build_map(aggregates, events)
            window.load_url(str(DEFAULT_OUTPUT_PATH.resolve()))
        except Exception as exc:
            logger.exception("Failed to build map")
            window.evaluate_js(f"showError({json.dumps(f'Something went wrong: {exc}')})")

    window = webview.create_window(
        "Live Music Activity Map",
        html=LOADING_HTML,
        width=1280,
        height=850,
    )
    webview.start(_load_map, window)
