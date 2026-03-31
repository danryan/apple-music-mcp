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
