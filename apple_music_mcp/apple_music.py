"""Apple Music API client for searching tracks and creating playlists."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import requests

from .auth import AppleMusicConfig as AppleMusicConfig

if TYPE_CHECKING:
    from .auth import AppleMusicAuth

APPLE_MUSIC_API = "https://api.music.apple.com/v1"


class AppleMusicClient:
    """Client for Apple Music API operations."""

    def __init__(self, auth: AppleMusicAuth) -> None:
        self.auth = auth

    @property
    def storefront(self) -> str:
        return self.auth.config.storefront

    def search_track(self, query: str) -> dict[str, Any] | None:
        """Search for a song and return the first match, or None."""
        url = f"{APPLE_MUSIC_API}/catalog/{self.storefront}/search"
        params: dict[str, Any] = {"term": query, "types": "songs", "limit": 1}
        resp = requests.get(url, headers=self.auth.headers(), params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        songs = data.get("results", {}).get("songs", {}).get("data", [])
        if songs:
            return songs[0]
        return None

    def create_playlist(self, name: str, description: str = "") -> str:
        """Create a new library playlist. Returns the playlist ID."""
        url = f"{APPLE_MUSIC_API}/me/library/playlists"
        body: dict[str, Any] = {
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
        params: dict[str, Any] = {"term": query, "types": types, "limit": limit}
        resp = requests.get(url, headers=self.auth.headers(), params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        results: list[dict[str, Any]] = []
        for raw_key in types.split(","):
            type_key = raw_key.strip()
            items = data.get("results", {}).get(type_key, {}).get("data", [])
            for item in items:
                attrs = item.get("attributes", {})
                results.append(
                    {
                        "id": item["id"],
                        "title": attrs.get("name", ""),
                        "artist": attrs.get("artistName", ""),
                        "album": attrs.get("albumName", ""),
                        "duration_ms": attrs.get("durationInMillis", 0),
                        "genres": attrs.get("genreNames", []),
                        "release_date": attrs.get("releaseDate", ""),
                        "url": attrs.get("url", ""),
                    }
                )
        return results

    def get_artist_top_songs(
        self, artist_name: str, limit: int = 20, *, lead_artist_only: bool = True
    ) -> dict[str, Any]:
        """Search for an artist by name, then fetch their top songs.

        Returns a dict with artist info and a list of top songs.
        """
        # Step 1: Search for the artist
        url = f"{APPLE_MUSIC_API}/catalog/{self.storefront}/search"
        params: dict[str, Any] = {"term": artist_name, "types": "artists", "limit": 1}
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
        params: dict[str, Any] = {"limit": limit}
        resp = requests.get(
            top_songs_url, headers=self.auth.headers(), params=params, timeout=30
        )
        resp.raise_for_status()

        songs_data = resp.json()
        matched_name = artist_attrs.get("name", "").lower()
        songs: list[dict[str, Any]] = []
        for item in songs_data.get("data", []):
            attrs = item.get("attributes", {})
            song_artist = attrs.get("artistName", "")
            if lead_artist_only and not song_artist.lower().startswith(matched_name):
                continue
            songs.append(
                {
                    "id": item["id"],
                    "title": attrs.get("name", ""),
                    "artist": song_artist,
                    "album": attrs.get("albumName", ""),
                    "duration_ms": attrs.get("durationInMillis", 0),
                    "genres": attrs.get("genreNames", []),
                    "release_date": attrs.get("releaseDate", ""),
                    "url": attrs.get("url", ""),
                }
            )

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
        playlists: list[dict[str, Any]] = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            playlists.append(
                {
                    "id": item["id"],
                    "name": attrs.get("name", ""),
                    "track_count": attrs.get("playParams", {}).get("trackCount", 0),
                }
            )
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
            if resp.status_code == HTTPStatus.NOT_FOUND:
                return tracks
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                catalog_id = attrs.get("playParams", {}).get("catalogId", "")
                tracks.append(
                    {
                        "id": item["id"],
                        "catalog_id": catalog_id,
                        "title": attrs.get("name", ""),
                        "artist": attrs.get("artistName", ""),
                        "album": attrs.get("albumName", ""),
                        "duration_ms": attrs.get("durationInMillis", 0),
                        "track_number": attrs.get("trackNumber", 0),
                    }
                )

            next_url = data.get("next")
            if not next_url:
                break
            url = f"https://api.music.apple.com{next_url}"
            params = {}

        return tracks

    def search_library(
        self,
        query: str,
        types: str = "library-songs,library-albums,library-artists,library-playlists",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search the user's library. Returns a list of result dicts."""
        url = f"{APPLE_MUSIC_API}/me/library/search"
        params: dict[str, Any] = {"term": query, "types": types, "limit": limit}
        resp = requests.get(
            url,
            headers=self.auth.headers(include_user_token=True),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()

        data = resp.json()
        results: list[dict[str, Any]] = []
        for raw_key in types.split(","):
            type_key = raw_key.strip()
            items = data.get("results", {}).get(type_key, {}).get("data", [])
            for item in items:
                attrs = item.get("attributes", {})
                results.append(
                    {
                        "id": item["id"],
                        "type": item.get("type", type_key),
                        "title": attrs.get("name", ""),
                        "artist": attrs.get("artistName", ""),
                        "album": attrs.get("albumName", ""),
                        "duration_ms": attrs.get("durationInMillis", 0),
                        "track_count": attrs.get("trackCount", 0),
                    }
                )
        return results

    def get_library_songs(
        self, limit: int = 25, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List songs in the user's library with pagination."""
        url = f"{APPLE_MUSIC_API}/me/library/songs"
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        resp = requests.get(
            url,
            headers=self.auth.headers(include_user_token=True),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()

        results: list[dict[str, Any]] = []
        for item in resp.json().get("data", []):
            attrs = item.get("attributes", {})
            results.append(
                {
                    "id": item["id"],
                    "title": attrs.get("name", ""),
                    "artist": attrs.get("artistName", ""),
                    "album": attrs.get("albumName", ""),
                    "duration_ms": attrs.get("durationInMillis", 0),
                    "track_number": attrs.get("trackNumber", 0),
                }
            )
        return results

    def get_library_albums(
        self, limit: int = 25, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List albums in the user's library with pagination."""
        url = f"{APPLE_MUSIC_API}/me/library/albums"
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        resp = requests.get(
            url,
            headers=self.auth.headers(include_user_token=True),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()

        results: list[dict[str, Any]] = []
        for item in resp.json().get("data", []):
            attrs = item.get("attributes", {})
            results.append(
                {
                    "id": item["id"],
                    "name": attrs.get("name", ""),
                    "artist": attrs.get("artistName", ""),
                    "track_count": attrs.get("trackCount", 0),
                    "release_date": attrs.get("releaseDate", ""),
                }
            )
        return results

    def get_library_artists(
        self, limit: int = 25, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List artists in the user's library with pagination."""
        url = f"{APPLE_MUSIC_API}/me/library/artists"
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        resp = requests.get(
            url,
            headers=self.auth.headers(include_user_token=True),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()

        results: list[dict[str, Any]] = []
        for item in resp.json().get("data", []):
            attrs = item.get("attributes", {})
            results.append(
                {
                    "id": item["id"],
                    "name": attrs.get("name", ""),
                }
            )
        return results

    def get_recently_played(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recently played items (albums, playlists, stations)."""
        url = f"{APPLE_MUSIC_API}/me/recent/played"
        params: dict[str, Any] = {"limit": limit}
        resp = requests.get(
            url,
            headers=self.auth.headers(include_user_token=True),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()

        results: list[dict[str, Any]] = []
        for item in resp.json().get("data", []):
            attrs = item.get("attributes", {})
            results.append(
                {
                    "id": item["id"],
                    "type": item.get("type", ""),
                    "name": attrs.get("name", ""),
                    "artist": attrs.get("artistName", ""),
                }
            )
        return results

    def get_recommendations(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get personalized recommendations from Apple Music."""
        url = f"{APPLE_MUSIC_API}/me/recommendations"
        params: dict[str, Any] = {"limit": limit}
        resp = requests.get(
            url,
            headers=self.auth.headers(include_user_token=True),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()

        results: list[dict[str, Any]] = []
        for group in resp.json().get("data", []):
            attrs = group.get("attributes", {})
            items: list[dict[str, Any]] = []
            for rel in (
                group.get("relationships", {}).get("contents", {}).get("data", [])
            ):
                rel_attrs = rel.get("attributes", {})
                items.append(
                    {
                        "id": rel["id"],
                        "type": rel.get("type", ""),
                        "name": rel_attrs.get("name", ""),
                        "artist": rel_attrs.get("artistName", ""),
                    }
                )
            results.append(
                {
                    "title": attrs.get("title", {}).get("stringForDisplay", ""),
                    "items": items,
                }
            )
        return results

    def get_song_details(self, song_id: str) -> dict[str, Any] | None:
        """Get detailed information about a song by catalog ID."""
        url = f"{APPLE_MUSIC_API}/catalog/{self.storefront}/songs/{song_id}"
        resp = requests.get(url, headers=self.auth.headers(), timeout=30)
        resp.raise_for_status()

        data = resp.json().get("data", [])
        if not data:
            return None

        item = data[0]
        attrs = item.get("attributes", {})
        previews = attrs.get("previews", [])
        artwork = attrs.get("artwork", {})
        return {
            "id": item["id"],
            "title": attrs.get("name", ""),
            "artist": attrs.get("artistName", ""),
            "album": attrs.get("albumName", ""),
            "duration_ms": attrs.get("durationInMillis", 0),
            "genres": attrs.get("genreNames", []),
            "release_date": attrs.get("releaseDate", ""),
            "url": attrs.get("url", ""),
            "has_lyrics": attrs.get("hasLyrics", False),
            "preview_url": previews[0]["url"] if previews else "",
            "artwork_url": artwork.get("url", ""),
            "isrc": attrs.get("isrc", ""),
            "composer": attrs.get("composerName", ""),
            "disc_number": attrs.get("discNumber", 0),
            "track_number": attrs.get("trackNumber", 0),
        }

    def get_album_details(self, album_id: str) -> dict[str, Any] | None:
        """Get detailed information about an album by catalog ID."""
        url = f"{APPLE_MUSIC_API}/catalog/{self.storefront}/albums/{album_id}"
        params: dict[str, Any] = {"include": "tracks"}
        resp = requests.get(url, headers=self.auth.headers(), params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json().get("data", [])
        if not data:
            return None

        item = data[0]
        attrs = item.get("attributes", {})
        artwork = attrs.get("artwork", {})
        editorial = attrs.get("editorialNotes", {})

        tracks_data = item.get("relationships", {}).get("tracks", {}).get("data", [])
        tracks: list[dict[str, Any]] = []
        for t in tracks_data:
            t_attrs = t.get("attributes", {})
            tracks.append(
                {
                    "id": t["id"],
                    "title": t_attrs.get("name", ""),
                    "artist": t_attrs.get("artistName", ""),
                    "duration_ms": t_attrs.get("durationInMillis", 0),
                    "track_number": t_attrs.get("trackNumber", 0),
                }
            )

        return {
            "id": item["id"],
            "name": attrs.get("name", ""),
            "artist": attrs.get("artistName", ""),
            "genres": attrs.get("genreNames", []),
            "release_date": attrs.get("releaseDate", ""),
            "track_count": attrs.get("trackCount", 0),
            "url": attrs.get("url", ""),
            "artwork_url": artwork.get("url", ""),
            "record_label": attrs.get("recordLabel", ""),
            "copyright": attrs.get("copyright", ""),
            "editorial_notes": editorial.get("standard", ""),
            "tracks": tracks,
        }

    def get_artist_details(self, artist_id: str) -> dict[str, Any] | None:
        """Get detailed information about an artist by catalog ID."""
        url = f"{APPLE_MUSIC_API}/catalog/{self.storefront}/artists/{artist_id}"
        params: dict[str, Any] = {"include": "albums"}
        resp = requests.get(url, headers=self.auth.headers(), params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json().get("data", [])
        if not data:
            return None

        item = data[0]
        attrs = item.get("attributes", {})
        artwork = attrs.get("artwork", {})
        editorial = attrs.get("editorialNotes", {})

        albums_data = item.get("relationships", {}).get("albums", {}).get("data", [])
        albums: list[dict[str, Any]] = []
        for a in albums_data:
            a_attrs = a.get("attributes", {})
            albums.append(
                {
                    "id": a["id"],
                    "name": a_attrs.get("name", ""),
                    "artist": a_attrs.get("artistName", ""),
                    "release_date": a_attrs.get("releaseDate", ""),
                }
            )

        return {
            "id": item["id"],
            "name": attrs.get("name", ""),
            "genres": attrs.get("genreNames", []),
            "url": attrs.get("url", ""),
            "artwork_url": artwork.get("url", ""),
            "editorial_notes": editorial.get("standard", ""),
            "albums": albums,
        }

    def remove_from_playlist(self, playlist_id: str, track_ids: list[str]) -> None:
        """Remove tracks from a library playlist by library track IDs."""
        url = f"{APPLE_MUSIC_API}/me/library/playlists/{playlist_id}/tracks"
        body = {"data": [{"id": tid, "type": "songs"} for tid in track_ids]}
        resp = requests.delete(
            url,
            headers=self.auth.headers(include_user_token=True),
            json=body,
            timeout=30,
        )
        resp.raise_for_status()

    def update_playlist(
        self, playlist_id: str, name: str | None = None, description: str | None = None
    ) -> None:
        """Update a library playlist's name and/or description."""
        url = f"{APPLE_MUSIC_API}/me/library/playlists/{playlist_id}"
        attributes: dict[str, Any] = {}
        if name is not None:
            attributes["name"] = name
        if description is not None:
            attributes["description"] = description
        body = {"attributes": attributes}
        resp = requests.put(
            url,
            headers=self.auth.headers(include_user_token=True),
            json=body,
            timeout=30,
        )
        resp.raise_for_status()

    def add_to_library(self, song_ids: list[str]) -> None:
        """Add songs to the user's library by catalog IDs."""
        url = f"{APPLE_MUSIC_API}/me/library"
        body: dict[str, Any] = {"ids": {"songs": song_ids}}
        resp = requests.post(
            url,
            headers=self.auth.headers(include_user_token=True),
            json=body,
            timeout=30,
        )
        resp.raise_for_status()

    def add_tracks_to_playlist(
        self, playlist_id: str, track_ids: list[dict[str, str]]
    ) -> dict[str, list[dict[str, str]]]:
        """Add tracks to a library playlist, skipping duplicates.

        track_ids: list of {"id": "<catalog-id>", "type": "songs"} dicts.

        Returns a dict with "added" and "skipped" lists.
        """
        existing = self.get_playlist_tracks(playlist_id)
        existing_catalog_ids = {
            t["catalog_id"] for t in existing if t.get("catalog_id")
        }

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
