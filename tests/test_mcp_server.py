# pyright: basic
"""Tests for Apple Music MCP server tool handlers."""

from unittest.mock import MagicMock, patch

import pytest

import playlist_creator.mcp_server as mcp_mod
from playlist_creator.mcp_server import (
    add_to_playlist,
    create_playlist,
    create_playlist_from_markdown,
    list_playlists,
    search_catalog,
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
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization

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
    @patch("playlist_creator.apple_music.requests.get")
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

    @patch("playlist_creator.apple_music.requests.get")
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
    @patch("playlist_creator.apple_music.requests.post")
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
    @patch("playlist_creator.apple_music.requests.get")
    @patch("playlist_creator.apple_music.requests.post")
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
    @patch("playlist_creator.apple_music.requests.get")
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


class TestCreatePlaylistFromMarkdown:
    @patch("playlist_creator.apple_music.requests.post")
    @patch("playlist_creator.apple_music.requests.get")
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

    @patch("playlist_creator.apple_music.requests.get")
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

    @patch("playlist_creator.apple_music.requests.get")
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


class TestErrorHandling:
    @patch("playlist_creator.apple_music.requests.get")
    def test_401_error(self, mock_get, mock_env):
        import requests

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = requests.HTTPError(
            response=mock_resp
        )
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="User token expired"):
            search_catalog("test")

    @patch("playlist_creator.apple_music.requests.get")
    def test_429_error(self, mock_get, mock_env):
        import requests

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"Retry-After": "30"}
        mock_resp.raise_for_status.side_effect = requests.HTTPError(
            response=mock_resp
        )
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="Rate limited.*30 seconds"):
            search_catalog("test")
