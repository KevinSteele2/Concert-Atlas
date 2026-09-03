"""Pulls artist popularity metrics from Spotify, keyed by artist name for joining."""

import base64
import logging
import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"
REQUEST_DELAY_SECONDS = 0.1


def fetch_artist_metrics(
    artist_names: list[str],
    client_id: str | None = None,
    client_secret: str | None = None,
) -> list[dict]:
    """Fetch Spotify popularity metrics for a list of artist names.

    Returns one dict per unique artist name with keys: artist, spotify_artist_id,
    popularity, followers, genres, fetched_date. Artists with no Spotify match are
    still included, with the metric fields set to None.
    """
    if client_id is None or client_secret is None:
        load_dotenv()
        client_id = client_id or os.environ.get("SPOTIFY_CLIENT_ID")
        client_secret = client_secret or os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError(
            "No Spotify credentials provided and SPOTIFY_CLIENT_ID/SPOTIFY_CLIENT_SECRET "
            "are not set in .env"
        )

    access_token = _get_access_token(client_id, client_secret)
    fetched_at = datetime.now(timezone.utc).isoformat()

    unique_names = list(dict.fromkeys(artist_names))
    headers = {"Authorization": f"Bearer {access_token}"}

    results = []
    for i, name in enumerate(unique_names):
        try:
            response = requests.get(
                SEARCH_URL,
                params={"q": name, "type": "artist", "limit": 1},
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Spotify search call #%d for artist=%s", i + 1, name)

            items = response.json()["artists"]["items"]
            if items:
                artist = items[0]
                results.append(
                    {
                        "artist": name,
                        "spotify_artist_id": artist["id"],
                        "popularity": artist["popularity"],
                        "followers": artist["followers"]["total"],
                        "genres": ",".join(artist.get("genres", [])),
                        "fetched_date": fetched_at,
                    }
                )
            else:
                logger.info("No Spotify match for artist %s", name)
                results.append(
                    {
                        "artist": name,
                        "spotify_artist_id": None,
                        "popularity": None,
                        "followers": None,
                        "genres": None,
                        "fetched_date": fetched_at,
                    }
                )
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("Skipping malformed Spotify response for artist %s: %s", name, exc)

        if i < len(unique_names) - 1:
            time.sleep(REQUEST_DELAY_SECONDS)

    return results


def _get_access_token(client_id: str, client_secret: str) -> str:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    response = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {credentials}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]
