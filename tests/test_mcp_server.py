# pyright: basic
"""Tests for Apple Music MCP server tool handlers."""

from unittest.mock import MagicMock, patch

import pytest

import apple_music_mcp.mcp_server as mcp_mod
from apple_music_mcp.mcp_server import (
    add_to_library,
    add_to_playlist,
    create_playlist,
    create_playlist_from_markdown,
    get_album_details,
    get_artist_details,
    get_library_albums,
    get_library_artists,
    get_library_songs,
    get_playlist_tracks,
    get_recently_played,
    get_recommendations,
    get_song_details,
    list_playlists,
    remove_from_playlist,
    search_catalog,
    search_library,
    update_playlist,
)


@pytest.fixture(autouse=True)
def reset_client_cache():
    """Reset the cached MCP client between tests."""
    mcp_mod._client = None
    yield
    mcp_mod._client = None


@pytest.fixture
def mock_env(monkeypatch):
    """Set required environment variables for client construction."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()

    monkeypatch.setenv("APPLE_TEAM_ID", "TEAM123")
    monkeypatch.setenv("APPLE_KEY_ID", "KEY456")
    monkeypatch.setenv("APPLE_PRIVATE_KEY", pem)
    monkeypatch.setenv("APPLE_MUSIC_USER_TOKEN", "test-user-token")
    monkeypatch.setenv("APPLE_MUSIC_STOREFRONT", "us")


class TestSearchCatalog:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_returns_results(self, mock_get, mock_env):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": {
                "songs": {
                    "data": [
                        {
                            "id": "123",
                            "type": "songs",
                            "attributes": {
                                "name": "Rhubarb",
                                "artistName": "Aphex Twin",
                                "albumName": "Selected Ambient Works Volume II",
                                "durationInMillis": 312000,
                                "genreNames": ["Electronic"],
                                "releaseDate": "1994-11-07",
                                "url": "https://music.apple.com/us/album/rhubarb/123",
                            },
                        }
                    ]
                }
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = search_catalog("Aphex Twin Rhubarb", limit=5)
        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "123"
        assert result["results"][0]["artist"] == "Aphex Twin"
        assert result["results"][0]["title"] == "Rhubarb"
        assert result["results"][0]["duration_ms"] == 312000

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_empty_results(self, mock_get, mock_env):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": {}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = search_catalog("nonexistent")
        assert result["results"] == []

    def test_missing_env_var(self, monkeypatch):
        monkeypatch.delenv("APPLE_TEAM_ID", raising=False)
        monkeypatch.delenv("APPLE_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("APPLE_PRIVATE_KEY_PATH", raising=False)
        with pytest.raises(ValueError, match="Missing required env var"):
            search_catalog("test")


class TestCreatePlaylist:
    @patch("apple_music_mcp.apple_music.requests.post")
    def test_creates_playlist(self, mock_post, mock_env):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [{"id": "p.abc123", "type": "library-playlists"}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = create_playlist("Deep Focus", "Ambient tracks")
        assert result["id"] == "p.abc123"
        assert result["name"] == "Deep Focus"


class TestAddToPlaylist:
    @patch("apple_music_mcp.apple_music.requests.get")
    @patch("apple_music_mcp.apple_music.requests.post")
    def test_adds_songs(self, mock_post, mock_get, mock_env):
        # Mock GET for get_playlist_tracks (returns empty playlist)
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 404
        mock_get.return_value = mock_get_resp

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = add_to_playlist("p.abc123", ["111", "222", "333"])
        assert result["added"] == 3
        assert result["skipped"] == 0

        call_kwargs = mock_post.call_args
        sent_data = call_kwargs.kwargs["json"]["data"]
        assert len(sent_data) == 3
        assert sent_data[0] == {"id": "111", "type": "songs"}


class TestListPlaylists:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_lists_playlists(self, mock_get, mock_env):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "p.abc123",
                    "type": "library-playlists",
                    "attributes": {
                        "name": "Late Night Ambient",
                        "playParams": {"trackCount": 24},
                    },
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = list_playlists()
        assert len(result["playlists"]) == 1
        assert result["playlists"][0]["name"] == "Late Night Ambient"


class TestGetPlaylistTracks:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_returns_tracks(self, mock_get, mock_env):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "i.abc123",
                    "attributes": {
                        "name": "Rhubarb",
                        "artistName": "Aphex Twin",
                        "albumName": "SAW II",
                        "durationInMillis": 312000,
                        "trackNumber": 3,
                        "playParams": {"catalogId": "999"},
                    },
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_playlist_tracks("p.abc123")
        assert len(result["tracks"]) == 1
        assert result["tracks"][0]["title"] == "Rhubarb"
        assert result["tracks"][0]["catalog_id"] == "999"

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_respects_limit(self, mock_get, mock_env):
        tracks = [
            {
                "id": f"i.{i}",
                "attributes": {
                    "name": f"Track {i}",
                    "artistName": "Artist",
                    "albumName": "Album",
                    "durationInMillis": 180000,
                    "trackNumber": i,
                    "playParams": {"catalogId": str(i)},
                },
            }
            for i in range(5)
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": tracks}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_playlist_tracks("p.abc123", limit=3)
        assert len(result["tracks"]) == 3


class TestSearchLibrary:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_returns_results(self, mock_get, mock_env):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": {
                "library-songs": {
                    "data": [
                        {
                            "id": "i.abc",
                            "type": "library-songs",
                            "attributes": {
                                "name": "Rhubarb",
                                "artistName": "Aphex Twin",
                                "albumName": "SAW II",
                                "durationInMillis": 312000,
                            },
                        }
                    ]
                }
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = search_library("Aphex Twin", types="library-songs")
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Rhubarb"


class TestGetLibrarySongs:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_returns_songs(self, mock_get, mock_env):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "i.abc",
                    "attributes": {
                        "name": "Rhubarb",
                        "artistName": "Aphex Twin",
                        "albumName": "SAW II",
                        "durationInMillis": 312000,
                        "trackNumber": 3,
                    },
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_library_songs(limit=10)
        assert len(result["songs"]) == 1
        assert result["songs"][0]["title"] == "Rhubarb"


class TestGetLibraryAlbums:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_returns_albums(self, mock_get, mock_env):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "l.abc",
                    "attributes": {
                        "name": "Selected Ambient Works Volume II",
                        "artistName": "Aphex Twin",
                        "trackCount": 24,
                        "releaseDate": "1994-11-07",
                    },
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_library_albums(limit=10)
        assert len(result["albums"]) == 1
        assert result["albums"][0]["name"] == "Selected Ambient Works Volume II"


class TestGetLibraryArtists:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_returns_artists(self, mock_get, mock_env):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "r.abc",
                    "attributes": {"name": "Aphex Twin"},
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_library_artists(limit=10)
        assert len(result["artists"]) == 1
        assert result["artists"][0]["name"] == "Aphex Twin"


class TestGetRecentlyPlayed:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_returns_items(self, mock_get, mock_env):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "l.abc",
                    "type": "albums",
                    "attributes": {
                        "name": "SAW II",
                        "artistName": "Aphex Twin",
                    },
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_recently_played(limit=5)
        assert len(result["items"]) == 1
        assert result["items"][0]["name"] == "SAW II"
        assert result["items"][0]["type"] == "albums"


class TestGetRecommendations:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_returns_recommendations(self, mock_get, mock_env):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "attributes": {
                        "title": {"stringForDisplay": "Made for You"},
                    },
                    "relationships": {
                        "contents": {
                            "data": [
                                {
                                    "id": "pl.abc",
                                    "type": "playlists",
                                    "attributes": {
                                        "name": "New Music Mix",
                                        "artistName": "",
                                    },
                                }
                            ]
                        }
                    },
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_recommendations(limit=5)
        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["title"] == "Made for You"
        assert len(result["recommendations"][0]["items"]) == 1


class TestCreatePlaylistFromMarkdown:
    @patch("apple_music_mcp.apple_music.requests.post")
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_full_flow(self, mock_get, mock_post, mock_env):
        # Mock search returning results for each track
        search_resp = MagicMock()
        search_resp.json.return_value = {
            "results": {
                "songs": {
                    "data": [
                        {
                            "id": "999",
                            "type": "songs",
                            "attributes": {
                                "name": "Hey Jude",
                                "artistName": "The Beatles",
                                "albumName": "Past Masters",
                                "durationInMillis": 431000,
                                "genreNames": ["Rock"],
                                "releaseDate": "1968-08-26",
                                "url": "https://music.apple.com/us/song/999",
                            },
                        }
                    ]
                }
            }
        }
        search_resp.raise_for_status = MagicMock()
        mock_get.return_value = search_resp

        # Mock playlist creation
        create_resp = MagicMock()
        create_resp.json.return_value = {
            "data": [{"id": "p.new123", "type": "library-playlists"}]
        }
        create_resp.raise_for_status = MagicMock()

        # Mock add tracks
        add_resp = MagicMock()
        add_resp.raise_for_status = MagicMock()

        mock_post.side_effect = [create_resp, add_resp]

        md = """# Test Playlist

- The Beatles - Hey Jude
- Queen - Bohemian Rhapsody
"""
        result = create_playlist_from_markdown(md)
        assert result["playlist_id"] == "p.new123"
        assert result["playlist_name"] == "Test Playlist"
        assert len(result["matched"]) == 2

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_dry_run(self, mock_get, mock_env):
        search_resp = MagicMock()
        search_resp.json.return_value = {
            "results": {
                "songs": {
                    "data": [
                        {
                            "id": "999",
                            "type": "songs",
                            "attributes": {
                                "name": "Hey Jude",
                                "artistName": "The Beatles",
                                "albumName": "Past Masters",
                                "durationInMillis": 431000,
                                "genreNames": [],
                                "releaseDate": "1968-08-26",
                                "url": "",
                            },
                        }
                    ]
                }
            }
        }
        search_resp.raise_for_status = MagicMock()
        mock_get.return_value = search_resp

        md = """# Dry Run Test

- The Beatles - Hey Jude
"""
        result = create_playlist_from_markdown(md, dry_run=True)
        assert result["dry_run"] is True
        assert len(result["matched"]) == 1
        assert "playlist_id" not in result

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_no_matches(self, mock_get, mock_env):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": {}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        md = """# Empty

- Unknown Artist - Unknown Song
"""
        result = create_playlist_from_markdown(md)
        assert "error" in result
        assert len(result["not_found"]) == 1


class TestGetSongDetails:
    def test_wraps_client_result(self, mock_env):
        fake_song = {"id": "999", "title": "Rhubarb", "artist": "Aphex Twin"}
        client = mcp_mod._get_client()
        with patch.object(client, "get_song_details", return_value=fake_song):
            mcp_mod._client = client
            result = get_song_details("999")
        assert result["song"] == fake_song

    def test_not_found_returns_error(self, mock_env):
        client = mcp_mod._get_client()
        with patch.object(client, "get_song_details", return_value=None):
            mcp_mod._client = client
            result = get_song_details("nonexistent")
        assert "error" in result


class TestGetAlbumDetails:
    def test_wraps_client_result(self, mock_env):
        fake_album = {"id": "888", "name": "SAW II", "tracks": []}
        client = mcp_mod._get_client()
        with patch.object(client, "get_album_details", return_value=fake_album):
            mcp_mod._client = client
            result = get_album_details("888")
        assert result["album"] == fake_album

    def test_not_found_returns_error(self, mock_env):
        client = mcp_mod._get_client()
        with patch.object(client, "get_album_details", return_value=None):
            mcp_mod._client = client
            result = get_album_details("nonexistent")
        assert "error" in result


class TestGetArtistDetails:
    def test_wraps_client_result(self, mock_env):
        fake_artist = {"id": "777", "name": "Aphex Twin", "albums": []}
        client = mcp_mod._get_client()
        with patch.object(client, "get_artist_details", return_value=fake_artist):
            mcp_mod._client = client
            result = get_artist_details("777")
        assert result["artist"] == fake_artist

    def test_not_found_returns_error(self, mock_env):
        client = mcp_mod._get_client()
        with patch.object(client, "get_artist_details", return_value=None):
            mcp_mod._client = client
            result = get_artist_details("nonexistent")
        assert "error" in result


class TestRemoveFromPlaylist:
    def test_returns_count(self, mock_env):
        client = mcp_mod._get_client()
        with patch.object(client, "remove_from_playlist") as mock_remove:
            mcp_mod._client = client
            result = remove_from_playlist("p.abc123", ["i.track1", "i.track2"])
        assert result["removed"] == 2
        mock_remove.assert_called_once_with("p.abc123", ["i.track1", "i.track2"])

    def test_empty_list_skips_client(self, mock_env):
        result = remove_from_playlist("p.abc123", [])
        assert result["removed"] == 0

    def test_api_error_handled(self, mock_env):
        import requests

        client = mcp_mod._get_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        error = requests.HTTPError(response=mock_resp)
        with patch.object(client, "remove_from_playlist", side_effect=error):
            mcp_mod._client = client
            with pytest.raises(ValueError, match="User token expired"):
                remove_from_playlist("p.abc123", ["i.track1"])


class TestUpdatePlaylist:
    def test_returns_updated(self, mock_env):
        client = mcp_mod._get_client()
        with patch.object(client, "update_playlist") as mock_update:
            mcp_mod._client = client
            result = update_playlist(
                "p.abc123", name="New Name", description="New desc"
            )
        assert result["updated"] is True
        mock_update.assert_called_once_with(
            "p.abc123", name="New Name", description="New desc"
        )

    def test_no_changes_raises(self, mock_env):
        with pytest.raises(ValueError, match="at least one"):
            update_playlist("p.abc123")

    def test_api_error_handled(self, mock_env):
        import requests

        client = mcp_mod._get_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"Retry-After": "30"}
        error = requests.HTTPError(response=mock_resp)
        with patch.object(client, "update_playlist", side_effect=error):
            mcp_mod._client = client
            with pytest.raises(ValueError, match=r"Rate limited.*30 seconds"):
                update_playlist("p.abc123", name="X")


class TestAddToLibrary:
    def test_returns_count(self, mock_env):
        client = mcp_mod._get_client()
        with patch.object(client, "add_to_library") as mock_add:
            mcp_mod._client = client
            result = add_to_library(["111", "222"])
        assert result["added"] == 2
        mock_add.assert_called_once_with(["111", "222"])

    def test_empty_list(self, mock_env):
        result = add_to_library([])
        assert result["added"] == 0

    def test_api_error_handled(self, mock_env):
        import requests

        client = mcp_mod._get_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        error = requests.HTTPError(response=mock_resp)
        with patch.object(client, "add_to_library", side_effect=error):
            mcp_mod._client = client
            with pytest.raises(ValueError, match="User token expired"):
                add_to_library(["111"])


class TestErrorHandling:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_401_error(self, mock_get, mock_env):
        import requests

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = requests.HTTPError(response=mock_resp)
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="User token expired"):
            search_catalog("test")

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_429_error(self, mock_get, mock_env):
        import requests

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"Retry-After": "30"}
        mock_resp.raise_for_status.side_effect = requests.HTTPError(response=mock_resp)
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match=r"Rate limited.*30 seconds"):
            search_catalog("test")
