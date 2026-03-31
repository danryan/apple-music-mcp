# apple-music-mcp

Apple Music MCP server and CLI — search the catalog, manage playlists, and more.

## Project structure

```
apple_music_mcp/
  __init__.py
  auth.py             # AppleMusicAuth — JWT token generation and auth headers
  apple_music.py      # AppleMusicClient — catalog search, playlist CRUD
  parser.py           # Markdown parser — extracts playlist name, description, tracks
  mcp_server.py       # MCP server (FastMCP, stdio transport) wrapping AppleMusicClient
  cli.py              # CLI entry point for markdown-to-playlist
tests/
  test_parser.py      # Parser unit tests
  test_apple_music.py # API client tests (mocked)
  test_mcp_server.py  # MCP server tests
examples/
  road_trip.md             # Example markdown playlist
  iconic-mpc-producers.md  # Example large playlist (212 tracks)
.claude/
  skills/playlist/         # /playlist — curate and create playlists via MCP tools
  skills/discover/         # /discover — music recommendations and artist exploration
  skills/playlist-manage/  # /playlist-manage — inspect, search, and merge playlists
  skills/top-songs/        # /top-songs — artist top songs and comparisons
```

## Setup

```bash
poetry install
```

### Environment variables

Copy `.env.example` to `.env` and fill in values. Required:

| Variable | Description |
|---|---|
| `APPLE_TEAM_ID` | Apple Developer Team ID (10 chars) |
| `APPLE_KEY_ID` | MusicKit key identifier (10 chars) |
| `APPLE_PRIVATE_KEY_PATH` | Path to `.p8` private key file (one of this or `APPLE_PRIVATE_KEY` required) |
| `APPLE_PRIVATE_KEY` | PEM string, alternative to `APPLE_PRIVATE_KEY_PATH` |
| `APPLE_MUSIC_USER_TOKEN` | Music User Token (from `get_user_token.html`) |
| `APPLE_MUSIC_STOREFRONT` | Country code, defaults to `us` |
| `LOG_LEVEL` | MCP server log level, defaults to `INFO` |

### Token generation

```bash
poetry run generate-token        # prints developer JWT to stdout
poetry run generate-token-save   # saves to apple-music-token.txt
```

User token requires interactive browser auth — open `get_user_token.html`, paste the developer JWT, authorize with Apple ID. Token lasts ~6 months; API returns 401 when expired.

## Running

### MCP server

```bash
poetry run apple-music-mcp
```

Runs on stdio. Configure in Claude Desktop or Claude Code as an MCP server.

### CLI (markdown-to-playlist)

```bash
poetry run playlist-creator examples/road_trip.md --dry-run   # preview only
poetry run playlist-creator examples/road_trip.md -v           # create playlist
```

### MCP tools

| Tool | Purpose |
|---|---|
| `search_catalog(query, limit, types)` | Search Apple Music catalog |
| `get_artist_top_songs(artist, limit, lead_artist_only)` | Get an artist's top songs by popularity |
| `add_to_library(song_ids)` | Add catalog songs to user's library |
| `create_playlist(name, description)` | Create a library playlist |
| `add_to_playlist(playlist_id, song_ids)` | Add songs by catalog ID (skips duplicates) |
| `list_playlists()` | List user's library playlists |
| `get_playlist_tracks(playlist_id, limit)` | Get all tracks in a playlist |
| `search_playlist(playlist_id, query)` | Search within a playlist by title/artist/album |
| `get_song_details(song_id)` | Get detailed song metadata by catalog ID |
| `get_album_details(album_id)` | Get album metadata + track listing by catalog ID |
| `get_artist_details(artist_id)` | Get artist metadata + albums by catalog ID |
| `remove_from_playlist(playlist_id, track_ids)` | Remove tracks from a library playlist |
| `update_playlist(playlist_id, name, description)` | Rename or update a playlist's description |
| `search_library(query, types, limit)` | Search user's library (songs, albums, artists, playlists) |
| `get_library_songs(limit, offset)` | Browse library songs with pagination |
| `get_library_albums(limit, offset)` | Browse library albums with pagination |
| `get_library_artists(limit, offset)` | Browse library artists with pagination |
| `get_charts(types, limit, genre)` | Top songs/albums/playlists charts by storefront |
| `get_heavy_rotation(limit)` | User's most frequently played items |
| `get_recently_played(limit)` | Recently played albums/playlists/stations |
| `get_recommendations(limit)` | Personalized recommendation groups |
| `create_playlist_from_markdown(markdown, name, description, dry_run)` | Parse markdown and create playlist |

## Tooling

- Linter/formatter: `ruff check . && ruff format .` before committing
- Type checker: `mypy --strict` — all code must pass
- Tests: `pytest` — do not reduce coverage below threshold
- Never disable ruff or mypy rules without a comment explaining why

## Patterns

- EAFP over LBYL — prefer `try/except` over pre-condition checks
- Use `itertools` and `functools` before writing manual loops
- Prefer generators over building intermediate lists
- Prefer `Protocol` over `ABC` for structural typing
- Prefer `dataclasses` or `TypedDict` over plain dicts for structured data
- Prefer `Enum` over string literals for fixed sets of values
- Use keyword-only args or enums instead of boolean positional arguments
- Raise specific exceptions — never `raise Exception(...)`
- Define custom exceptions per domain; inherit from a project base exception
- No `print()` for logging — use the `logging` module

## Testing

**You MUST follow test-driven development (TDD). No exceptions.** Do not write feature code until a failing test exists for it.

### TDD workflow (red-green-refactor)

1. **Red — write the test first.** Before touching any feature code, write a test for the behavior you're about to implement. Run `poetry run pytest` and confirm the new test **fails**. If it passes, the test isn't testing anything new.
2. **Green — make it pass.** Write the minimum feature code to make the failing test pass. Run `poetry run pytest` and confirm **all tests pass**.
3. **Refactor — clean up.** Improve the code (feature or test) while keeping all tests green. Run `poetry run pytest` after every change.

### When to run tests

- **Before starting work** — run the full suite to confirm a clean baseline.
- **After writing each failing test** — confirm it actually fails.
- **After writing feature code** — confirm the test now passes and nothing else broke.
- **After refactoring** — confirm tests still pass.
- **Before committing** — final check, no exceptions.

```bash
poetry run pytest
```

## Git workflow

- **Never push directly to main.** No exceptions.
- **Every change gets its own branch and PR.** Even small fixes, doc updates, or single-file changes.
- **Create the feature branch before modifying any files.** Always `git checkout -b <branch>` first, then start making changes.
- Do not add unrelated commits to an existing PR's branch — open a separate PR instead.
- Branch naming: `claude/<short-description>` or `<username>/<short-description>`

## Keeping docs current

When making changes that affect project structure, MCP tools, CLI commands, env vars, or workflows:
- **Update this file (`CLAUDE.md`)** to reflect the new state — add/remove tools, update the project structure tree, revise conventions, etc.
- **Update skills** (`.claude/skills/`) if MCP tools are added, removed, or changed — skills reference tool names and signatures, so they must stay in sync.

## Conventions

- Env vars use `APPLE_` prefix (not `APPLE_MUSIC_` for key/team config)
- `AppleMusicClient` is the single API layer — MCP server and CLI both use it, never call the REST API directly
- Markdown format: `# Playlist Name` heading, `- Artist - Title` track lines
- Error handling: MCP tools convert API errors to user-friendly messages (401 → token expired, 429 → rate limited)
- Dependencies managed with Poetry (`pyproject.toml`)
- Environment variables: loaded via `python-dotenv`; document all vars in `.env.example`
- Tests: mirror source layout under `tests/`; one test file per source module
- Commits: conventional commits (`feat:`, `fix:`, `chore:`, etc.)
 