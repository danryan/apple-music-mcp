"""Authentication for the Apple Music API.

Handles JWT developer token generation and header construction.
Separated from the API client so auth logic is reusable and testable independently.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import jwt


@dataclass
class AppleMusicConfig:
    team_id: str
    key_id: str
    private_key: str  # PEM-encoded private key contents
    storefront: str = "us"


class AppleMusicAuth:
    """Manages developer token generation and auth headers."""

    def __init__(self, config: AppleMusicConfig, user_token: str) -> None:
        self.config = config
        self.user_token = user_token
        self._developer_token: str | None = None
        self._token_expiry: float = 0

    @property
    def developer_token(self) -> str:
        now = time.time()
        if self._developer_token and now < self._token_expiry:
            return self._developer_token

        expiry = now + 15_777_000  # ~6 months (Apple's max)
        payload = {
            "iss": self.config.team_id,
            "iat": int(now),
            "exp": int(expiry),
        }
        token = jwt.encode(
            payload,
            self.config.private_key,
            algorithm="ES256",
            headers={"kid": self.config.key_id},
        )
        self._developer_token = token
        self._token_expiry = expiry - 300  # refresh 5 min early
        return token

    def headers(self, *, include_user_token: bool = False) -> dict[str, str]:
        """Return auth headers for Apple Music API requests."""
        h = {
            "Authorization": f"Bearer {self.developer_token}",
            "Content-Type": "application/json",
        }
        if include_user_token:
            h["Music-User-Token"] = self.user_token
        return h
