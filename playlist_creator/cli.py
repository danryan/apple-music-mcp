"""CLI entry point for playlist-creator."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .apple_music import AppleMusicClient
from .auth import AppleMusicAuth, AppleMusicConfig
from .parser import Track, parse_markdown

load_dotenv()


def _get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Error: {name} environment variable is required", file=sys.stderr)
        sys.exit(1)
    return value


def _build_client() -> AppleMusicClient:
    key_path = os.environ.get("APPLE_PRIVATE_KEY_PATH")
    private_key = os.environ.get("APPLE_PRIVATE_KEY")

    if key_path:
        private_key = Path(os.path.expanduser(key_path)).read_text(encoding="utf-8")
    elif not private_key:
        print(
            "Error: APPLE_PRIVATE_KEY or APPLE_PRIVATE_KEY_PATH required",
            file=sys.stderr,
        )
        sys.exit(1)

    config = AppleMusicConfig(
        team_id=_get_env("APPLE_TEAM_ID"),
        key_id=_get_env("APPLE_KEY_ID"),
        private_key=private_key,
        storefront=os.environ.get("APPLE_MUSIC_STOREFRONT", "us"),
    )
    auth = AppleMusicAuth(config, user_token=_get_env("APPLE_MUSIC_USER_TOKEN"))
    return AppleMusicClient(auth)


def _search_track(client: AppleMusicClient, track: Track, verbose: bool) -> dict | None:
    result = client.search_track(track.search_query())
    if result:
        attrs = result["attributes"]
        if verbose:
            print(f"  Found: {attrs['artistName']} - {attrs['name']}")
        return {"id": result["id"], "type": "songs"}
    else:
        print(f"  Not found: {track.artist} - {track.title}", file=sys.stderr)
        return None


def run(args: argparse.Namespace) -> None:
    playlist = parse_markdown(args.file)
    name = args.name or playlist.name
    description = args.description or playlist.description

    print(f"Playlist: {name}")
    print(f"Tracks to search: {len(playlist.tracks)}")

    if args.dry_run:
        print("\nDry run — parsed tracks:")
        for i, track in enumerate(playlist.tracks, 1):
            print(f"  {i}. {track.artist} - {track.title}")
        return

    client = _build_client()

    print("\nSearching Apple Music...")
    found_tracks: list[dict] = []
    for track in playlist.tracks:
        result = _search_track(client, track, verbose=args.verbose)
        if result:
            found_tracks.append(result)

    if not found_tracks:
        print("No tracks found. Playlist not created.", file=sys.stderr)
        sys.exit(1)

    print(f"\nFound {len(found_tracks)}/{len(playlist.tracks)} tracks.")
    print(f"Creating playlist '{name}'...")

    playlist_id = client.create_playlist(name, description)
    client.add_tracks_to_playlist(playlist_id, found_tracks)

    print(f"Playlist created with {len(found_tracks)} tracks. ID: {playlist_id}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="playlist-creator",
        description="Create Apple Music playlists from markdown files.",
    )
    parser.add_argument("file", type=Path, help="Path to the markdown playlist file")
    parser.add_argument("-n", "--name", help="Override the playlist name")
    parser.add_argument("-d", "--description", help="Override the playlist description")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and display tracks without creating a playlist",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed search results",
    )

    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    run(args)


if __name__ == "__main__":
    main()
