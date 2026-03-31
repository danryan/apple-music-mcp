"""Parse markdown files to extract playlist name and track listings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_MAX_ARTIST_WORDS = 6


@dataclass
class Track:
    artist: str
    title: str

    def search_query(self) -> str:
        return f"{self.artist} {self.title}"


@dataclass
class Playlist:
    name: str
    description: str
    tracks: list[Track]


def parse_markdown(path: str | Path) -> Playlist:
    """Parse a markdown file into a Playlist.

    Expected format:
        # Playlist Name

        Optional description paragraph.

        - Artist - Track Title
        - Artist - Track Title

    Also supports numbered lists (1. Artist - Track) and
    lines without list markers (Artist - Track).
    """
    text = Path(path).read_text(encoding="utf-8")
    return parse_markdown_text(text)


def parse_markdown_text(text: str) -> Playlist:
    """Parse markdown text into a Playlist."""
    lines = text.strip().splitlines()

    name = _extract_name(lines)
    description = ""
    tracks: list[Track] = []

    in_header = True
    desc_lines: list[str] = []

    for line in lines[1:]:  # skip the title line
        stripped = line.strip()

        if not stripped:
            if in_header and desc_lines:
                in_header = False
            continue

        track = _parse_track_line(stripped)
        if track:
            in_header = False
            tracks.append(track)
        elif in_header:
            # Skip sub-headings in description
            if not stripped.startswith("#"):
                desc_lines.append(stripped)

    description = " ".join(desc_lines)
    return Playlist(name=name, description=description, tracks=tracks)


def _extract_name(lines: list[str]) -> str:
    """Extract playlist name from the first heading."""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            return re.sub(r"^#+\s*", "", stripped).strip()
    return "Untitled Playlist"


# Pattern: optional list marker, then "Artist - Title" or "Artist — Title"
_TRACK_RE = re.compile(
    r"^(?:[-*]|\d+[.)]\s*)\s*"  # list marker (required)
    r"(.+?)"  # artist (non-greedy)
    r"\s+[-\u2013\u2014]\s+"  # separator dash (hyphen, en dash, em dash)
    r"(.+)$"  # title
)

_BARE_TRACK_RE = re.compile(
    r"^(.+?)"  # artist
    r"\s+[-\u2013\u2014]\s+"  # separator dash (hyphen, en dash, em dash)
    r"(.+)$"  # title
)


def _parse_track_line(line: str) -> Track | None:
    """Try to parse a single line as a track entry."""
    # Strip markdown bold/italic
    cleaned = re.sub(r"[*_]{1,3}", "", line).strip()

    match = _TRACK_RE.match(cleaned)
    if match:
        return Track(artist=match.group(1).strip(), title=match.group(2).strip())

    # Try bare "Artist - Title" lines (no list marker) only if line
    # doesn't look like a heading or description
    if not cleaned.startswith("#") and not cleaned.startswith(">"):
        match = _BARE_TRACK_RE.match(cleaned)
        if match:
            artist = match.group(1).strip()
            title = match.group(2).strip()
            # Heuristic: skip if artist portion is very long (likely prose)
            if len(artist.split()) <= _MAX_ARTIST_WORDS:
                return Track(artist=artist, title=title)

    return None
