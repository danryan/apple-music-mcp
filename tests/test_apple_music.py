"""Tests for Apple Music API client."""

from unittest.mock import MagicMock, patch

import pytest

from apple_music_mcp.apple_music import AppleMusicClient
from apple_music_mcp.auth import AppleMusicAuth, AppleMusicConfig


@pytest.fixture
def config() -> AppleMusicConfig:
    # Minimal EC256 test key (not a real key, just for JWT encoding tests)
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()

    return AppleMusicConfig(
        team_id="TEAM123",
        key_id="KEY456",
        private_key=pem,
        storefront="us",
    )


@pytest.fixture
def auth(config: AppleMusicConfig) -> AppleMusicAuth:
    return AppleMusicAuth(config, user_token="test-user-token")


@pytest.fixture
def client(auth: AppleMusicAuth) -> AppleMusicClient:
    return AppleMusicClient(auth)


def test_developer_token_generated(auth: AppleMusicAuth) -> None:
    token = auth.developer_token
    assert isinstance(token, str)
    assert len(token) > 0


def test_developer_token_cached(auth: AppleMusicAuth) -> None:
    token1 = auth.developer_token
    token2 = auth.developer_token
    assert token1 == token2


@patch("apple_music_mcp.apple_music.requests.get")
def test_search_track_found(mock_get: MagicMock, client: AppleMusicClient) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": {
            "songs": {
                "data": [
                    {
                        "id": "123",
                        "type": "songs",
                        "attributes": {
                            "name": "Hey Jude",
                            "artistName": "The Beatles",
                        },
                    }
                ]
            }
        }
    }
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = client.search_track("The Beatles Hey Jude")
    assert result is not None
    assert result["id"] == "123"


@patch("apple_music_mcp.apple_music.requests.get")
def test_search_track_not_found(mock_get: MagicMock, client: AppleMusicClient) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": {}}
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = client.search_track("nonexistent track")
    assert result is None


@patch("apple_music_mcp.apple_music.requests.post")
def test_create_playlist(mock_post: MagicMock, client: AppleMusicClient) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": [{"id": "p.abc123", "type": "library-playlists"}]
    }
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    playlist_id = client.create_playlist("Test Playlist", "A description")
    assert playlist_id == "p.abc123"

    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["json"]["attributes"]["name"] == "Test Playlist"


@patch("apple_music_mcp.apple_music.requests.get")
@patch("apple_music_mcp.apple_music.requests.post")
def test_add_tracks_to_playlist(
    mock_post: MagicMock, mock_get: MagicMock, client: AppleMusicClient
) -> None:
    # Mock GET for get_playlist_tracks (returns empty playlist)
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 404
    mock_get.return_value = mock_get_resp

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    tracks = [{"id": "123", "type": "songs"}, {"id": "456", "type": "songs"}]
    client.add_tracks_to_playlist("p.abc123", tracks)

    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["json"]["data"] == tracks


SONG_DETAIL_KEYS = {
    "id",
    "title",
    "artist",
    "album",
    "duration_ms",
    "genres",
    "release_date",
    "url",
    "has_lyrics",
    "preview_url",
    "artwork_url",
    "isrc",
    "composer",
    "disc_number",
    "track_number",
}

ALBUM_DETAIL_KEYS = {
    "id",
    "name",
    "artist",
    "genres",
    "release_date",
    "track_count",
    "url",
    "artwork_url",
    "record_label",
    "copyright",
    "editorial_notes",
    "tracks",
}

ARTIST_DETAIL_KEYS = {
    "id",
    "name",
    "genres",
    "url",
    "artwork_url",
    "editorial_notes",
    "albums",
}


def _make_song_response(**overrides: object) -> dict:
    """Build a minimal Apple Music song API response, with optional overrides."""
    attrs: dict = {
        "name": "Rhubarb",
        "artistName": "Aphex Twin",
        "albumName": "SAW II",
        "durationInMillis": 312000,
        "genreNames": ["Electronic"],
        "releaseDate": "1994-11-07",
        "url": "https://music.apple.com/us/song/999",
        "hasLyrics": False,
        "previews": [{"url": "https://preview.example.com/rhubarb.m4a"}],
        "artwork": {
            "url": "https://artwork.example.com/rhubarb.jpg",
            "width": 3000,
            "height": 3000,
        },
        "isrc": "GBAFL9400099",
        "composerName": "Richard D. James",
        "discNumber": 1,
        "trackNumber": 3,
    }
    attrs.update(overrides)
    return {"data": [{"id": "999", "type": "songs", "attributes": attrs}]}


class TestGetSongDetails:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_maps_key_fields(
        self, mock_get: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_song_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_song_details("999")
        assert result is not None
        assert result["id"] == "999"
        assert result["title"] == "Rhubarb"
        assert result["artist"] == "Aphex Twin"
        assert set(result.keys()) == SONG_DETAIL_KEYS

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_not_found(self, mock_get: MagicMock, client: AppleMusicClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        assert client.get_song_details("nonexistent") is None

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_missing_previews_and_artwork(
        self, mock_get: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_song_response(previews=[], artwork={})
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_song_details("999")
        assert result is not None
        assert result["preview_url"] == ""
        assert result["artwork_url"] == ""


class TestGetAlbumDetails:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_maps_key_fields_and_tracks(
        self, mock_get: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "888",
                    "type": "albums",
                    "attributes": {
                        "name": "SAW II",
                        "artistName": "Aphex Twin",
                        "genreNames": ["Electronic"],
                        "releaseDate": "1994-11-07",
                        "trackCount": 24,
                        "url": "https://music.apple.com/us/album/888",
                        "artwork": {
                            "url": "https://artwork.example.com/saw2.jpg",
                            "width": 3000,
                            "height": 3000,
                        },
                        "recordLabel": "Warp Records",
                        "copyright": "1994 Warp Records",
                        "editorialNotes": {"standard": "A masterpiece."},
                    },
                    "relationships": {
                        "tracks": {
                            "data": [
                                {
                                    "id": "999",
                                    "type": "songs",
                                    "attributes": {
                                        "name": "Rhubarb",
                                        "artistName": "Aphex Twin",
                                        "durationInMillis": 312000,
                                        "trackNumber": 3,
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

        result = client.get_album_details("888")
        assert result is not None
        assert result["id"] == "888"
        assert result["name"] == "SAW II"
        assert result["artist"] == "Aphex Twin"
        assert set(result.keys()) == ALBUM_DETAIL_KEYS
        assert len(result["tracks"]) == 1
        assert result["tracks"][0]["title"] == "Rhubarb"

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_not_found(self, mock_get: MagicMock, client: AppleMusicClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        assert client.get_album_details("nonexistent") is None

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_no_tracks_relationship(
        self, mock_get: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "888",
                    "type": "albums",
                    "attributes": {
                        "name": "SAW II",
                        "artistName": "Aphex Twin",
                        "genreNames": [],
                        "releaseDate": "",
                        "trackCount": 0,
                        "url": "",
                        "artwork": {},
                        "recordLabel": "",
                        "copyright": "",
                        "editorialNotes": {},
                    },
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_album_details("888")
        assert result is not None
        assert result["tracks"] == []


class TestGetArtistDetails:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_maps_key_fields_and_albums(
        self, mock_get: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "777",
                    "type": "artists",
                    "attributes": {
                        "name": "Aphex Twin",
                        "genreNames": ["Electronic"],
                        "url": "https://music.apple.com/us/artist/777",
                        "artwork": {
                            "url": "https://artwork.example.com/aphex.jpg",
                            "width": 3000,
                            "height": 3000,
                        },
                        "editorialNotes": {"standard": "Pioneering electronic artist."},
                    },
                    "relationships": {
                        "albums": {
                            "data": [
                                {
                                    "id": "888",
                                    "type": "albums",
                                    "attributes": {
                                        "name": "SAW II",
                                        "artistName": "Aphex Twin",
                                        "releaseDate": "1994-11-07",
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

        result = client.get_artist_details("777")
        assert result is not None
        assert result["id"] == "777"
        assert result["name"] == "Aphex Twin"
        assert set(result.keys()) == ARTIST_DETAIL_KEYS
        assert len(result["albums"]) == 1

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_not_found(self, mock_get: MagicMock, client: AppleMusicClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        assert client.get_artist_details("nonexistent") is None

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_no_albums_relationship(
        self, mock_get: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "777",
                    "type": "artists",
                    "attributes": {
                        "name": "Aphex Twin",
                        "genreNames": [],
                        "url": "",
                        "artwork": {},
                        "editorialNotes": {},
                    },
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_artist_details("777")
        assert result is not None
        assert result["albums"] == []


class TestRemoveFromPlaylist:
    @patch("apple_music_mcp.apple_music.requests.delete")
    def test_sends_correct_request(
        self, mock_delete: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_delete.return_value = mock_resp

        client.remove_from_playlist("p.abc123", ["i.track1", "i.track2"])

        mock_delete.assert_called_once()
        call_kwargs = mock_delete.call_args
        assert "me/library/playlists/p.abc123/tracks" in call_kwargs.args[0]
        body = call_kwargs.kwargs["json"]
        assert len(body["data"]) == 2
        assert body["data"][0] == {"id": "i.track1", "type": "songs"}

    @patch("apple_music_mcp.apple_music.requests.delete")
    def test_http_error_propagates(
        self, mock_delete: MagicMock, client: AppleMusicClient
    ) -> None:
        import requests as req

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError(response=mock_resp)
        mock_delete.return_value = mock_resp

        with pytest.raises(req.HTTPError):
            client.remove_from_playlist("p.abc123", ["i.track1"])


class TestUpdatePlaylist:
    @patch("apple_music_mcp.apple_music.requests.put")
    def test_sends_both_fields(
        self, mock_put: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_put.return_value = mock_resp

        client.update_playlist("p.abc123", name="New Name", description="New desc")

        body = mock_put.call_args.kwargs["json"]
        assert body["attributes"]["name"] == "New Name"
        assert body["attributes"]["description"] == "New desc"

    @patch("apple_music_mcp.apple_music.requests.put")
    def test_name_only_omits_description(
        self, mock_put: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_put.return_value = mock_resp

        client.update_playlist("p.abc123", name="New Name")

        body = mock_put.call_args.kwargs["json"]
        assert body["attributes"]["name"] == "New Name"
        assert "description" not in body["attributes"]

    @patch("apple_music_mcp.apple_music.requests.put")
    def test_description_only_omits_name(
        self, mock_put: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_put.return_value = mock_resp

        client.update_playlist("p.abc123", description="New desc")

        body = mock_put.call_args.kwargs["json"]
        assert body["attributes"]["description"] == "New desc"
        assert "name" not in body["attributes"]

    @patch("apple_music_mcp.apple_music.requests.put")
    def test_http_error_propagates(
        self, mock_put: MagicMock, client: AppleMusicClient
    ) -> None:
        import requests as req

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError(response=mock_resp)
        mock_put.return_value = mock_resp

        with pytest.raises(req.HTTPError):
            client.update_playlist("p.abc123", name="New Name")


class TestGetHeavyRotation:
    @patch("apple_music_mcp.apple_music.requests.get")
    def test_returns_items(self, mock_get: MagicMock, client: AppleMusicClient) -> None:
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
                },
                {
                    "id": "pl.xyz",
                    "type": "playlists",
                    "attributes": {
                        "name": "Chill Vibes",
                    },
                },
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_heavy_rotation(limit=10)
        assert len(result) == 2
        assert result[0]["id"] == "l.abc"
        assert result[0]["type"] == "albums"
        assert result[0]["name"] == "SAW II"
        assert result[0]["artist"] == "Aphex Twin"
        assert result[1]["id"] == "pl.xyz"
        assert result[1]["name"] == "Chill Vibes"

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_empty_response(
        self, mock_get: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_heavy_rotation()
        assert result == []

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_passes_limit_param(
        self, mock_get: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client.get_heavy_rotation(limit=5)
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["params"]["limit"] == 5

    @patch("apple_music_mcp.apple_music.requests.get")
    def test_uses_user_token(
        self, mock_get: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client.get_heavy_rotation()
        call_kwargs = mock_get.call_args
        headers = call_kwargs.kwargs["headers"]
        assert "Music-User-Token" in headers


class TestAddToLibrary:
    @patch("apple_music_mcp.apple_music.requests.post")
    def test_sends_correct_request(
        self, mock_post: MagicMock, client: AppleMusicClient
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client.add_to_library(["111", "222"])

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "me/library" in call_kwargs.args[0]
        body = call_kwargs.kwargs["json"]
        assert body == {"ids": {"songs": ["111", "222"]}}

    @patch("apple_music_mcp.apple_music.requests.post")
    def test_single_song(self, mock_post: MagicMock, client: AppleMusicClient) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client.add_to_library(["999"])

        body = mock_post.call_args.kwargs["json"]
        assert body == {"ids": {"songs": ["999"]}}

    @patch("apple_music_mcp.apple_music.requests.post")
    def test_http_error_propagates(
        self, mock_post: MagicMock, client: AppleMusicClient
    ) -> None:
        import requests as req

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError(response=mock_resp)
        mock_post.return_value = mock_resp

        with pytest.raises(req.HTTPError):
            client.add_to_library(["111"])
