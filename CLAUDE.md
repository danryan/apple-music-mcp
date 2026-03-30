# playlist-creator

Apple Music playlist creator — CLI tool and MCP server for searching the Apple Music catalog and managing playlists.

## Project structure

```
playlist_creator/
  __init__.py
  apple_music.py      # AppleMusicClient — JWT auth, catalog search, playlist CRUD
  parser.py           # Markdown parser — extracts playlist name, description, tracks
  mcp_server.py       # MCP server (FastMCP, stdio transport) wrapping AppleMusicClient
  cli.py              # CLI entry point
tests/
  test_parser.py      # Parser unit tests
  test_apple_music.py # API client tests (mocked)
  test_mcp_server.py  # MCP server tests
examples/
  road_trip.md        # Example markdown playlist
.claude/
  skills/playlist/    # /playlist skill for curating playlists via MCP tools
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
| `APPLE_PRIVATE_KEY_PATH` | Path to `.p8` private key file |
| `APPLE_MUSIC_USER_TOKEN` | Music User Token (from `get_user_token.html`) |
| `APPLE_MUSIC_STOREFRONT` | Country code, defaults to `us` |

### Token generation

```bash
poetry run generate-token        # prints developer JWT to stdout
poetry run generate-token-save   # saves to apple-music-token.txt
```

User token requires interactive browser auth — open `get_user_token.html`, paste the developer JWT, authorize with Apple ID. Token lasts ~6 months; API returns 401 when expired.

## Running

### CLI

```bash
poetry run playlist-creator examples/road_trip.md --dry-run   # preview only
poetry run playlist-creator examples/road_trip.md -v           # create playlist
```

### MCP server

```bash
poetry run playlist-creator-mcp
```

Runs on stdio. Configure in Claude Desktop or Claude Code as an MCP server.

### MCP tools

| Tool | Purpose |
|---|---|
| `search_catalog(query, limit, types)` | Search Apple Music catalog |
| `create_playlist(name, description)` | Create a library playlist |
| `add_to_playlist(playlist_id, song_ids)` | Add songs by catalog ID |
| `list_playlists()` | List user's library playlists |
| `create_playlist_from_markdown(markdown, name, description, dry_run)` | Parse markdown and create playlist |

## Testing

```bash
poetry run pytest
```

## Git workflow

- **Never push directly to main.** No exceptions.
- **Every change gets its own branch and PR.** Even small fixes, doc updates, or single-file changes.
- Create a new branch from main, commit work there, push the branch, and open a PR.
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
