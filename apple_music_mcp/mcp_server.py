"""Apple Music MCP server for Claude Desktop and Claude Code."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .apple_music import AppleMusicClient
from .auth import AppleMusicAuth, AppleMusicConfig
from .parser import parse_markdown_text

load_dotenv()

logger = logging.getLogger("apple-music-mcp")

mcp = FastMCP("apple-music")

_client: AppleMusicClient | None = None


def _get_env(name: str) -> str:
    """Get a required environment variable or raise."""
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value


def _get_client() -> AppleMusicClient:
    """Return a cached AppleMusicClient, building it on first call."""
    global _client
    if _client is not None:
        return _client

    key_path = os.environ.get("APPLE_PRIVATE_KEY_PATH")
    private_key = os.environ.get("APPLE_PRIVATE_KEY")

    if key_path:
        path = key_path
        if path.startswith("~/"):
            path = os.path.expanduser(path)
        private_key = Path(path).read_text(encoding="utf-8")
    elif not private_key:
        raise ValueError(
            "Missing required env var: APPLE_PRIVATE_KEY or APPLE_PRIVATE_KEY_PATH"
        )

    config = AppleMusicConfig(
        team_id=_get_env("APPLE_TEAM_ID"),
        key_id=_get_env("APPLE_KEY_ID"),
        private_key=private_key,
        storefront=os.environ.get("APPLE_MUSIC_STOREFRONT", "us"),
    )
    auth = AppleMusicAuth(config, user_token=_get_env("APPLE_MUSIC_USER_TOKEN"))
    _client = AppleMusicClient(auth)
    return _client


def _handle_api_error(e: Exception) -> str:
    """Convert API errors to user-friendly messages."""
    import requests

    if isinstance(e, requests.HTTPError) and e.response is not None:
        status = e.response.status_code
        if status == 401:
            return "User token expired. Re-run get_user_token.html to obtain a new token."
        if status == 403:
            return "Forbidden. Check Apple Music subscription status."
        if status == 429:
            retry_after = e.response.headers.get("Retry-After", "60")
            return f"Rate limited. Retry in {retry_after} seconds."
    return str(e)


@mcp.tool()
def search_catalog(query: str, limit: int = 10, types: str = "songs") -> dict[str, object]:
    """Search the Apple Music catalog for songs, albums, or artists.

    Args:
        query: Search query string.
        limit: Maximum number of results to return (default 10).
        types: Comma-separated resource types to search (default "songs").
    """
    logger.info("search_catalog query=%r limit=%d types=%s", query, limit, types)
    try:
        client = _get_client()
        results = client.search_catalog(query, limit=limit, types=types)
        logger.info("search_catalog returned %d results", len(results))
        return {"results": results}
    except Exception as e:
        logger.error("search_catalog failed: %s", e)
        raise ValueError(_handle_api_error(e))


@mcp.tool()
def get_artist_top_songs(artist: str, limit: int = 20, lead_artist_only: bool = True) -> dict[str, object]:
    """Get an artist's top songs on Apple Music, sorted by popularity.

    Searches for the artist by name, then returns their most popular tracks
    using Apple Music's top-songs view.

    Args:
        artist: Artist name to search for.
        limit: Maximum number of top songs to return (default 20).
        lead_artist_only: If true (default), only return songs where the artist is the lead. If false, include songs where the artist is featured.
    """
    logger.info("get_artist_top_songs artist=%r limit=%d lead_artist_only=%s", artist, limit, lead_artist_only)
    try:
        client = _get_client()
        result = client.get_artist_top_songs(artist, limit=limit, lead_artist_only=lead_artist_only)
        if result["artist"] is None:
            logger.warning("get_artist_top_songs: artist not found for %r", artist)
            return {"error": f"Artist not found: {artist}"}
        logger.info(
            "get_artist_top_songs found %d songs for %s",
            len(result["songs"]),
            result["artist"]["name"],
        )
        return result
    except Exception as e:
        logger.error("get_artist_top_songs failed: %s", e)
        raise ValueError(_handle_api_error(e))


@mcp.tool()
def create_playlist(name: str, description: str = "") -> dict[str, object]:
    """Create a new playlist in the user's Apple Music library.

    Args:
        name: Name for the new playlist.
        description: Optional description for the playlist.
    """
    logger.info("create_playlist name=%r", name)
    try:
        client = _get_client()
        playlist_id = client.create_playlist(name, description)
        logger.info("create_playlist created id=%s", playlist_id)
        return {"id": playlist_id, "name": name}
    except Exception as e:
        logger.error("create_playlist failed: %s", e)
        raise ValueError(_handle_api_error(e))


@mcp.tool()
def add_to_playlist(playlist_id: str, song_ids: list[str]) -> dict[str, object]:
    """Add songs to an existing playlist by catalog IDs.

    Args:
        playlist_id: The playlist ID to add songs to.
        song_ids: List of Apple Music catalog song IDs.
    """
    logger.info("add_to_playlist playlist_id=%s songs=%d", playlist_id, len(song_ids))
    try:
        client = _get_client()
        track_data = [{"id": sid, "type": "songs"} for sid in song_ids]
        result = client.add_tracks_to_playlist(playlist_id, track_data)
        added = result["added"]
        skipped = result["skipped"]
        logger.info("add_to_playlist added=%d skipped=%d", len(added), len(skipped))
        return {
            "added": len(added),
            "skipped": len(skipped),
            "skipped_ids": [t["id"] for t in skipped],
        }
    except Exception as e:
        logger.error("add_to_playlist failed: %s", e)
        raise ValueError(_handle_api_error(e))


@mcp.tool()
def list_playlists() -> dict[str, object]:
    """List the user's Apple Music library playlists."""
    logger.info("list_playlists")
    try:
        client = _get_client()
        playlists = client.list_playlists()
        logger.info("list_playlists returned %d playlists", len(playlists))
        return {"playlists": playlists}
    except Exception as e:
        logger.error("list_playlists failed: %s", e)
        raise ValueError(_handle_api_error(e))


@mcp.tool()
def search_playlist(
    playlist_id: str,
    query: str,
) -> dict[str, object]:
    """Search for a song within an existing playlist by matching against track title, artist, or album.

    Args:
        playlist_id: The library playlist ID to search within.
        query: Search string to match against song title, artist, or album name (case-insensitive).
    """
    logger.info("search_playlist playlist_id=%s query=%r", playlist_id, query)
    try:
        client = _get_client()
        tracks = client.get_playlist_tracks(playlist_id)
        query_lower = query.lower()
        matches = [
            t for t in tracks
            if query_lower in t.get("title", "").lower()
            or query_lower in t.get("artist", "").lower()
            or query_lower in t.get("album", "").lower()
        ]
        logger.info("search_playlist found %d matches out of %d tracks", len(matches), len(tracks))
        return {"matches": matches, "total_tracks": len(tracks)}
    except Exception as e:
        logger.error("search_playlist failed: %s", e)
        raise ValueError(_handle_api_error(e))


@mcp.tool()
def get_playlist_tracks(playlist_id: str, limit: int = 100) -> dict[str, object]:
    """Get all tracks in a library playlist.

    Args:
        playlist_id: The library playlist ID.
        limit: Maximum number of tracks to return (default 100).
    """
    logger.info("get_playlist_tracks playlist_id=%s limit=%d", playlist_id, limit)
    try:
        client = _get_client()
        tracks = client.get_playlist_tracks(playlist_id)
        if limit and len(tracks) > limit:
            tracks = tracks[:limit]
        logger.info("get_playlist_tracks returned %d tracks", len(tracks))
        return {"tracks": tracks, "total": len(tracks)}
    except Exception as e:
        logger.error("get_playlist_tracks failed: %s", e)
        raise ValueError(_handle_api_error(e))


@mcp.tool()
def search_library(
    query: str,
    types: str = "library-songs,library-albums,library-artists,library-playlists",
    limit: int = 10,
) -> dict[str, object]:
    """Search the user's Apple Music library for songs, albums, artists, or playlists.

    Args:
        query: Search query string.
        types: Comma-separated library resource types (default: all).
        limit: Maximum results per type (default 10, max 25).
    """
    logger.info("search_library query=%r types=%s limit=%d", query, types, limit)
    try:
        client = _get_client()
        results = client.search_library(query, types=types, limit=limit)
        logger.info("search_library returned %d results", len(results))
        return {"results": results}
    except Exception as e:
        logger.error("search_library failed: %s", e)
        raise ValueError(_handle_api_error(e))


@mcp.tool()
def get_library_songs(limit: int = 25, offset: int = 0) -> dict[str, object]:
    """List songs in the user's Apple Music library with pagination.

    Args:
        limit: Number of songs to return (1-100, default 25).
        offset: Pagination offset (default 0).
    """
    logger.info("get_library_songs limit=%d offset=%d", limit, offset)
    try:
        client = _get_client()
        songs = client.get_library_songs(limit=limit, offset=offset)
        logger.info("get_library_songs returned %d songs", len(songs))
        return {"songs": songs}
    except Exception as e:
        logger.error("get_library_songs failed: %s", e)
        raise ValueError(_handle_api_error(e))


@mcp.tool()
def get_library_albums(limit: int = 25, offset: int = 0) -> dict[str, object]:
    """List albums in the user's Apple Music library with pagination.

    Args:
        limit: Number of albums to return (1-100, default 25).
        offset: Pagination offset (default 0).
    """
    logger.info("get_library_albums limit=%d offset=%d", limit, offset)
    try:
        client = _get_client()
        albums = client.get_library_albums(limit=limit, offset=offset)
        logger.info("get_library_albums returned %d albums", len(albums))
        return {"albums": albums}
    except Exception as e:
        logger.error("get_library_albums failed: %s", e)
        raise ValueError(_handle_api_error(e))


@mcp.tool()
def get_library_artists(limit: int = 25, offset: int = 0) -> dict[str, object]:
    """List artists in the user's Apple Music library with pagination.

    Args:
        limit: Number of artists to return (1-100, default 25).
        offset: Pagination offset (default 0).
    """
    logger.info("get_library_artists limit=%d offset=%d", limit, offset)
    try:
        client = _get_client()
        artists = client.get_library_artists(limit=limit, offset=offset)
        logger.info("get_library_artists returned %d artists", len(artists))
        return {"artists": artists}
    except Exception as e:
        logger.error("get_library_artists failed: %s", e)
        raise ValueError(_handle_api_error(e))


@mcp.tool()
def get_recently_played(limit: int = 10) -> dict[str, object]:
    """Get the user's recently played items on Apple Music.

    Returns recently played albums, playlists, and stations.

    Args:
        limit: Number of items to return (1-50, default 10).
    """
    logger.info("get_recently_played limit=%d", limit)
    try:
        client = _get_client()
        items = client.get_recently_played(limit=limit)
        logger.info("get_recently_played returned %d items", len(items))
        return {"items": items}
    except Exception as e:
        logger.error("get_recently_played failed: %s", e)
        raise ValueError(_handle_api_error(e))


@mcp.tool()
def get_recommendations(limit: int = 5) -> dict[str, object]:
    """Get personalized music recommendations from Apple Music.

    Returns recommendation groups with suggested albums, playlists, and more.

    Args:
        limit: Number of recommendation groups (1-10, default 5).
    """
    logger.info("get_recommendations limit=%d", limit)
    try:
        client = _get_client()
        recs = client.get_recommendations(limit=limit)
        logger.info("get_recommendations returned %d groups", len(recs))
        return {"recommendations": recs}
    except Exception as e:
        logger.error("get_recommendations failed: %s", e)
        raise ValueError(_handle_api_error(e))


@mcp.tool()
def create_playlist_from_markdown(
    markdown: str,
    name: str | None = None,
    description: str | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
    """Parse a markdown string and create a playlist from it.

    Parses artist/title pairs from markdown bullet lists, searches the Apple Music
    catalog for each track, creates a playlist, and adds the found tracks.

    Args:
        markdown: Markdown text containing a track listing.
        name: Override playlist name (default: parsed from # heading).
        description: Override playlist description (default: parsed from body text).
        dry_run: If true, parse and search but don't create the playlist.
    """
    logger.info("create_playlist_from_markdown name=%r dry_run=%s", name, dry_run)
    try:
        playlist = parse_markdown_text(markdown)
        playlist_name = name or playlist.name
        playlist_desc = description or playlist.description
        logger.info("parsed %d tracks from markdown, playlist=%r", len(playlist.tracks), playlist_name)

        client = _get_client()

        matched: list[dict[str, str]] = []
        not_found: list[dict[str, str]] = []

        for track in playlist.tracks:
            query = track.search_query()
            results = client.search_catalog(query, limit=1, types="songs")
            if results:
                matched.append({
                    "artist": track.artist,
                    "title": track.title,
                    "catalog_id": results[0]["id"],
                })
                logger.debug("matched: %s - %s", track.artist, track.title)
            else:
                not_found.append({"artist": track.artist, "title": track.title})
                logger.warning("not found: %s - %s (query=%r)", track.artist, track.title, query)

        logger.info("search complete: %d matched, %d not found", len(matched), len(not_found))

        if dry_run:
            logger.info("dry run — skipping playlist creation")
            return {
                "playlist_name": playlist_name,
                "matched": matched,
                "not_found": not_found,
                "dry_run": True,
            }

        if not matched:
            logger.warning("no tracks matched — playlist not created")
            return {
                "playlist_name": playlist_name,
                "matched": [],
                "not_found": not_found,
                "error": "No tracks found. Playlist not created.",
            }

        playlist_id = client.create_playlist(playlist_name, playlist_desc)
        logger.info("created playlist id=%s", playlist_id)
        track_data = [{"id": m["catalog_id"], "type": "songs"} for m in matched]
        client.add_tracks_to_playlist(playlist_id, track_data)
        logger.info("added %d tracks to playlist %s", len(matched), playlist_id)

        return {
            "playlist_id": playlist_id,
            "playlist_name": playlist_name,
            "matched": matched,
            "not_found": not_found,
        }
    except Exception as e:
        logger.error("create_playlist_from_markdown failed: %s", e)
        raise ValueError(_handle_api_error(e))


def main():
    """Run the MCP server with stdio transport."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
