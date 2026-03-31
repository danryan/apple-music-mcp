"""Tests for Apple Music API client."""

from unittest.mock import MagicMock, patch

import pytest

from apple_music_mcp.apple_music import AppleMusicClient
from apple_music_mcp.auth import AppleMusicAuth, AppleMusicConfig


@pytest.fixture
def config() -> AppleMusicConfig:
    # Minimal EC256 test key (not a real key, just for JWT encoding tests)
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization

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
def test_add_tracks_to_playlist(mock_post: MagicMock, mock_get: MagicMock, client: AppleMusicClient) -> None:
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


@patch("apple_music_mcp.apple_music.requests.get")
def test_get_song_details(mock_get: MagicMock, client: AppleMusicClient) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": [
            {
                "id": "999",
                "type": "songs",
                "attributes": {
                    "name": "Rhubarb",
                    "artistName": "Aphex Twin",
                    "albumName": "Selected Ambient Works Volume II",
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
                },
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = client.get_song_details("999")
    assert result is not None
    assert result["id"] == "999"
    assert result["title"] == "Rhubarb"
    assert result["artist"] == "Aphex Twin"
    assert result["album"] == "Selected Ambient Works Volume II"
    assert result["duration_ms"] == 312000
    assert result["genres"] == ["Electronic"]
    assert result["has_lyrics"] is False
    assert result["preview_url"] == "https://preview.example.com/rhubarb.m4a"
    assert result["artwork_url"] == "https://artwork.example.com/rhubarb.jpg"
    assert result["isrc"] == "GBAFL9400099"
    assert result["composer"] == "Richard D. James"
    assert result["disc_number"] == 1
    assert result["track_number"] == 3


@patch("apple_music_mcp.apple_music.requests.get")
def test_get_song_details_not_found(mock_get: MagicMock, client: AppleMusicClient) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": []}
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = client.get_song_details("nonexistent")
    assert result is None


@patch("apple_music_mcp.apple_music.requests.get")
def test_get_album_details(mock_get: MagicMock, client: AppleMusicClient) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": [
            {
                "id": "888",
                "type": "albums",
                "attributes": {
                    "name": "Selected Ambient Works Volume II",
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
                    "editorialNotes": {"standard": "A masterpiece of ambient music."},
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
    assert result["name"] == "Selected Ambient Works Volume II"
    assert result["artist"] == "Aphex Twin"
    assert result["track_count"] == 24
    assert result["genres"] == ["Electronic"]
    assert result["release_date"] == "1994-11-07"
    assert result["artwork_url"] == "https://artwork.example.com/saw2.jpg"
    assert result["record_label"] == "Warp Records"
    assert result["copyright"] == "1994 Warp Records"
    assert result["editorial_notes"] == "A masterpiece of ambient music."
    assert len(result["tracks"]) == 1
    assert result["tracks"][0]["id"] == "999"
    assert result["tracks"][0]["title"] == "Rhubarb"


@patch("apple_music_mcp.apple_music.requests.get")
def test_get_album_details_not_found(mock_get: MagicMock, client: AppleMusicClient) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": []}
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = client.get_album_details("nonexistent")
    assert result is None


@patch("apple_music_mcp.apple_music.requests.get")
def test_get_artist_details(mock_get: MagicMock, client: AppleMusicClient) -> None:
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
                                    "name": "Selected Ambient Works Volume II",
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
    assert result["genres"] == ["Electronic"]
    assert result["url"] == "https://music.apple.com/us/artist/777"
    assert result["artwork_url"] == "https://artwork.example.com/aphex.jpg"
    assert result["editorial_notes"] == "Pioneering electronic artist."
    assert len(result["albums"]) == 1
    assert result["albums"][0]["id"] == "888"
    assert result["albums"][0]["name"] == "Selected Ambient Works Volume II"


@patch("apple_music_mcp.apple_music.requests.get")
def test_get_artist_details_not_found(mock_get: MagicMock, client: AppleMusicClient) -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": []}
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = client.get_artist_details("nonexistent")
    assert result is None


@patch("apple_music_mcp.apple_music.requests.delete")
def test_remove_from_playlist(mock_delete: MagicMock, client: AppleMusicClient) -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_delete.return_value = mock_resp

    client.remove_from_playlist("p.abc123", ["i.track1", "i.track2"])

    mock_delete.assert_called_once()
    call_kwargs = mock_delete.call_args
    body = call_kwargs.kwargs["json"]
    assert len(body["data"]) == 2
    assert body["data"][0] == {"id": "i.track1", "type": "songs"}


@patch("apple_music_mcp.apple_music.requests.put")
def test_update_playlist(mock_put: MagicMock, client: AppleMusicClient) -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_put.return_value = mock_resp

    client.update_playlist("p.abc123", name="New Name", description="New desc")

    mock_put.assert_called_once()
    call_kwargs = mock_put.call_args
    body = call_kwargs.kwargs["json"]
    assert body["attributes"]["name"] == "New Name"
    assert body["attributes"]["description"] == "New desc"


@patch("apple_music_mcp.apple_music.requests.put")
def test_update_playlist_name_only(mock_put: MagicMock, client: AppleMusicClient) -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_put.return_value = mock_resp

    client.update_playlist("p.abc123", name="New Name")

    call_kwargs = mock_put.call_args
    body = call_kwargs.kwargs["json"]
    assert body["attributes"]["name"] == "New Name"
    assert "description" not in body["attributes"]
