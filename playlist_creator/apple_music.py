"""Apple Music API client for searching tracks and creating playlists."""

from __future__ import annotations

from typing import Any

import requests

from .auth import AppleMusicAuth, AppleMusicConfig  # noqa: F401 — re-exported

APPLE_MUSIC_API = "https://api.music.apple.com/v1"


class AppleMusicClient:
    """Client for Apple Music API operations."""

    def __init__(self, auth: AppleMusicAuth) -> None:
        self.auth = auth

    @property
    def storefront(self) -> str:
        return self.auth.config.storefront

    def search_track(self, query: str) -> dict | None:
        """Search for a song and return the first match, or None."""
        url = f"{APPLE_MUSIC_API}/catalog/{self.storefront}/search"
        params = {"term": query, "types": "songs", "limit": 1}
        resp = requests.get(url, headers=self.auth.headers(), params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        songs = data.get("results", {}).get("songs", {}).get("data", [])
        if songs:
            return songs[0]
        return None

    def create_playlist(
        self, name: str, description: str = ""
    ) -> str:
        """Create a new library playlist. Returns the playlist ID."""
        url = f"{APPLE_MUSIC_API}/me/library/playlists"
        body: dict = {
            "attributes": {
                "name": name,
                "description": description,
            },
        }
        resp = requests.post(
            url,
            headers=self.auth.headers(include_user_token=True),
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        playlist_data = resp.json()["data"][0]
        return playlist_data["id"]

    def search_catalog(
        self, query: str, limit: int = 10, types: str = "songs"
    ) -> list[dict[str, Any]]:
        """Search the Apple Music catalog. Returns a list of result dicts."""
        url = f"{APPLE_MUSIC_API}/catalog/{self.storefront}/search"
        params = {"term": query, "types": types, "limit": limit}
        resp = requests.get(url, headers=self.auth.headers(), params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        results = []
        for type_key in types.split(","):
            type_key = type_key.strip()
            items = data.get("results", {}).get(type_key, {}).get("data", [])
            for item in items:
                attrs = item.get("attributes", {})
                results.append({
                    "id": item["id"],
                    "title": attrs.get("name", ""),
                    "artist": attrs.get("artistName", ""),
                    "album": attrs.get("albumName", ""),
                    "duration_ms": attrs.get("durationInMillis", 0),
                    "genres": attrs.get("genreNames", []),
                    "release_date": attrs.get("releaseDate", ""),
                    "url": attrs.get("url", ""),
                })
        return results

    def get_artist_top_songs(
        self, artist_name: str, limit: int = 20, lead_artist_only: bool = True
    ) -> dict[str, Any]:
        """Search for an artist by name, then fetch their top songs.

        Returns a dict with artist info and a list of top songs.
        """
        # Step 1: Search for the artist
        url = f"{APPLE_MUSIC_API}/catalog/{self.storefront}/search"
        params = {"term": artist_name, "types": "artists", "limit": 1}
        resp = requests.get(url, headers=self.auth.headers(), params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        artists = data.get("results", {}).get("artists", {}).get("data", [])
        if not artists:
            return {"artist": None, "songs": []}

        artist = artists[0]
        artist_id = artist["id"]
        artist_attrs = artist.get("attributes", {})

        # Step 2: Fetch top songs
        top_songs_url = (
            f"{APPLE_MUSIC_API}/catalog/{self.storefront}"
            f"/artists/{artist_id}/view/top-songs"
        )
        params = {"limit": limit}
        resp = requests.get(
            top_songs_url, headers=self.auth.headers(), params=params, timeout=30
        )
        resp.raise_for_status()

        songs_data = resp.json()
        matched_name = artist_attrs.get("name", "").lower()
        songs = []
        for item in songs_data.get("data", []):
            attrs = item.get("attributes", {})
            song_artist = attrs.get("artistName", "")
            if lead_artist_only and not song_artist.lower().startswith(matched_name):
                continue
            songs.append({
                "id": item["id"],
                "title": attrs.get("name", ""),
                "artist": song_artist,
                "album": attrs.get("albumName", ""),
                "duration_ms": attrs.get("durationInMillis", 0),
                "genres": attrs.get("genreNames", []),
                "release_date": attrs.get("releaseDate", ""),
                "url": attrs.get("url", ""),
            })

        return {
            "artist": {
                "id": artist_id,
                "name": artist_attrs.get("name", ""),
                "url": artist_attrs.get("url", ""),
            },
            "songs": songs,
        }

    def list_playlists(self) -> list[dict[str, Any]]:
        """List the user's library playlists."""
        url = f"{APPLE_MUSIC_API}/me/library/playlists"
        resp = requests.get(
            url,
            headers=self.auth.headers(include_user_token=True),
            timeout=30,
        )
        resp.raise_for_status()

        data = resp.json()
        playlists = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            playlists.append({
                "id": item["id"],
                "name": attrs.get("name", ""),
                "track_count": attrs.get("playParams", {}).get("trackCount", 0),
            })
        return playlists

    def get_playlist_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        """Get all tracks in a library playlist."""
        url = f"{APPLE_MUSIC_API}/me/library/playlists/{playlist_id}/tracks"
        tracks: list[dict[str, Any]] = []
        params: dict[str, Any] = {}

        while True:
            resp = requests.get(
                url,
                headers=self.auth.headers(include_user_token=True),
                params=params,
                timeout=30,
            )
            if resp.status_code == 404:
                return tracks
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                catalog_id = attrs.get("playParams", {}).get("catalogId", "")
                tracks.append({
                    "id": item["id"],
                    "catalog_id": catalog_id,
                    "title": attrs.get("name", ""),
                    "artist": attrs.get("artistName", ""),
                    "album": attrs.get("albumName", ""),
                    "duration_ms": attrs.get("durationInMillis", 0),
                    "track_number": attrs.get("trackNumber", 0),
                })

            next_url = data.get("next")
            if not next_url:
                break
            url = f"https://api.music.apple.com{next_url}"
            params = {}

        return tracks

    def add_tracks_to_playlist(
        self, playlist_id: str, track_ids: list[dict[str, str]]
    ) -> dict[str, list[dict[str, str]]]:
        """Add tracks to a library playlist, skipping duplicates.

        track_ids: list of {"id": "<catalog-id>", "type": "songs"} dicts.

        Returns a dict with "added" and "skipped" lists.
        """
        existing = self.get_playlist_tracks(playlist_id)
        existing_catalog_ids = {t["catalog_id"] for t in existing if t.get("catalog_id")}

        to_add = [t for t in track_ids if t["id"] not in existing_catalog_ids]
        skipped = [t for t in track_ids if t["id"] in existing_catalog_ids]

        if to_add:
            url = f"{APPLE_MUSIC_API}/me/library/playlists/{playlist_id}/tracks"
            body = {"data": to_add}
            resp = requests.post(
                url,
                headers=self.auth.headers(include_user_token=True),
                json=body,
                timeout=30,
            )
            resp.raise_for_status()

        return {"added": to_add, "skipped": skipped}
