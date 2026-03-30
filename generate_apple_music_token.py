#!/usr/bin/env python3
"""Generate Apple Music API developer tokens."""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from playlist_creator.auth import AppleMusicConfig

load_dotenv()


def generate_apple_music_token():
    """Generate an Apple Music developer token."""
    # Get configuration from environment variables
    team_id = os.environ.get("APPLE_TEAM_ID", "YOUR_TEAM_ID")
    key_id = os.environ.get("APPLE_KEY_ID", "YOUR_KEY_ID")
    private_key_path = os.environ.get("APPLE_PRIVATE_KEY_PATH", "./AuthKey.p8")

    # Expand ~ in path if present
    if private_key_path.startswith("~/"):
        private_key_path = os.path.expanduser(private_key_path)

    try:
        # Read the private key
        private_key = Path(private_key_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(
            f"Error: Private key file not found at {private_key_path}", file=sys.stderr
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error reading private key: {e}", file=sys.stderr)
        sys.exit(1)

    # Create config and client
    config = AppleMusicConfig(
        team_id=team_id,
        key_id=key_id,
        private_key=private_key,
    )

    # Override the token expiry to 180 days (as in the Node.js version)
    # We'll generate the token manually to match the Node.js behavior
    import jwt

    from typing import Any

    now = time.time()
    payload: dict[str, Any] = {
        "iss": config.team_id,
        "iat": int(now),
        "exp": int(now + (180 * 24 * 60 * 60)),  # 180 days
    }

    # Add origin if specified
    allowed_origins = os.environ.get("ALLOWED_ORIGINS")
    if allowed_origins:
        payload["origin"] = allowed_origins.split(",")

    token = jwt.encode(
        payload,
        config.private_key,
        algorithm="ES256",
        headers={"kid": config.key_id},
    )

    return token


def main():
    """Main entry point."""
    try:
        token = generate_apple_music_token()
        print("Developer Token:", token)
        print("\nToken expires in 180 days")
        print("\nUse this token in your Authorization header:")
        print(f"Authorization: Bearer {token}")

        # Check for --save flag
        if len(sys.argv) > 1 and sys.argv[1] == "--save":
            Path("apple-music-token.txt").write_text(token)
            print("\nToken saved to apple-music-token.txt")

    except Exception as e:
        print(f"Failed to generate token: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
