"""LastfmRecommendationGateway — similar-artist candidates from Last.fm.

Spotify deprecated its related-artists endpoint, so for Spotify discovery we use
Last.fm's free `artist.getSimilar`, then map each similar artist back to a
Spotify artist (via the Spotify gateway's search) so the rest of the pipeline gets
provider-native artists. Artist top-tracks delegate to Spotify (still supported).
"""
from __future__ import annotations

import logging

import requests

from ...config import LASTFM_API_KEY
from ...domain.library.entities import Artist

log = logging.getLogger("infra.lastfm")

LASTFM_API = "http://ws.audioscrobbler.com/2.0/"
_SIMILAR_PER_SEED = 8


class LastfmRecommendationGateway:
    def __init__(self, spotify_gateway):
        self._spotify = spotify_gateway

    def similar_artists(self, artist_id: str) -> list[Artist]:
        if not LASTFM_API_KEY:
            raise RuntimeError(
                "LASTFM_API_KEY is not set. Get a free key at last.fm/api and add it to backend/.env."
            )
        name = self._spotify.get_artist_name(artist_id)
        if not name:
            return []
        try:
            resp = requests.get(
                LASTFM_API,
                params={
                    "method": "artist.getsimilar",
                    "artist": name,
                    "api_key": LASTFM_API_KEY,
                    "format": "json",
                    "limit": _SIMILAR_PER_SEED,
                },
                timeout=15,
            )
            resp.raise_for_status()
            similar = resp.json().get("similarartists", {}).get("artist", [])
        except (requests.RequestException, ValueError) as e:
            log.warning("Last.fm getSimilar failed for %s: %s", name, e)
            return []

        # Map each Last.fm name back to a Spotify artist so ids stay provider-native.
        out: list[Artist] = []
        seen: set[str] = set()
        for s in similar:
            sname = s.get("name")
            if not sname:
                continue
            try:
                results = self._spotify.search(sname, ["artists"])
            except Exception:
                continue
            match = next((a for a in results.artists if a.name.lower() == sname.lower()), None)
            match = match or (results.artists[0] if results.artists else None)
            if match and match.id not in seen:
                seen.add(match.id)
                out.append(match)
        return out

    def artist_top_tracks(self, artist_id: str, limit: int = 1) -> list[str]:
        return self._spotify.artist_top_tracks(artist_id, limit)
