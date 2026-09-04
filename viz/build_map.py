"""Renders an interactive map of city-level concert activity."""

import argparse
import json
import logging
import webbrowser
from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.express as px

from data.aggregate import aggregate_by_city
from data.ingest_ticketmaster import fetch_events_for_cities

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("outputs") / "city_map.html"
TOP_GENRES_SHOWN = 3

DEFAULT_CITIES = [
    "New York",
    "Los Angeles",
    "Chicago",
    "Houston",
    "Phoenix",
    "Philadelphia",
    "San Antonio",
    "San Diego",
    "Dallas",
    "Austin",
    "Denver",
    "Seattle",
    "Boston",
    "Nashville",
    "Atlanta",
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
        zoom=3,
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

    html = fig.to_html(full_html=True, config={"scrollZoom": True}, div_id="city-map")
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "cities",
        nargs="*",
        help=f"Cities to pull music events for (default: {len(DEFAULT_CITIES)} major US cities)",
    )
    args = parser.parse_args()
    cities = args.cities or DEFAULT_CITIES

    events = fetch_events_for_cities(cities)
    aggregates = aggregate_by_city(events)
    build_map(aggregates, events)

    print(f"Saved to {DEFAULT_OUTPUT_PATH}")
    webbrowser.open(DEFAULT_OUTPUT_PATH.resolve().as_uri())
