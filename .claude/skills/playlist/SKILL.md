---
name: playlist
description: Create Apple Music playlists using MCP tools — search catalog, curate tracks by mood/genre/duration, and manage playlists
argument-hint: <description of playlist to create>
user-invocable: true
disable-model-invocation: false
---

# Apple Music Playlist Creator

You have access to an Apple Music MCP server with these tools:

- `search_catalog(query, limit, types)` — Search Apple Music for songs, albums, or artists
- `get_artist_top_songs(artist, limit, lead_artist_only)` — Get an artist's top songs sorted by popularity
- `create_playlist(name, description)` — Create a new library playlist
- `add_to_playlist(playlist_id, song_ids)` — Add songs by catalog ID
- `list_playlists()` — List the user's library playlists
- `search_playlist(playlist_id, query)` — Search within a playlist by title/artist/album
- `create_playlist_from_markdown(markdown, name, description, dry_run)` — Parse markdown and create a playlist in one step

## Your task

Create an Apple Music playlist based on the user's request: **$ARGUMENTS**

## Workflow

### 1. Understand the request

Determine what the user wants:
- **From a markdown file**: Use `create_playlist_from_markdown` with the file contents
- **From a description** (mood, genre, activity, era, etc.): Curate tracks yourself using `search_catalog`, then create and populate the playlist
- **Manage existing**: Use `list_playlists`, `add_to_playlist` as needed

### 2. Curate tracks (when building from description)

Use your music knowledge to pick specific tracks. Search for each one individually to get accurate catalog IDs.

**Search strategy:**
- Search `"artist name song title"` for best precision
- If a search misses, try variations: shorter query, just the song title, or alternate spelling
- Request `limit=3` and pick the best match — don't blindly take the first result
- Verify the result matches intent (correct artist, not a cover/remix unless requested)

**Curation guidelines:**
- Aim for variety within the theme — mix well-known tracks with deeper cuts
- Consider flow: opening energy, progression, closing track
- When a duration target is given, use `duration_ms` from results to track total runtime
- Default to 15-20 tracks if no count specified
- Mix eras and subgenres unless the user specifies constraints

### 3. Create the playlist

- Pick a descriptive, concise playlist name if the user didn't provide one
- Write a short description capturing the vibe
- Use `create_playlist` to create it, then `add_to_playlist` with all collected song IDs
- Or use `create_playlist_from_markdown` if working from markdown input

### 4. Report results

Present a clean summary:
- Playlist name and track count
- Numbered track listing with artist, title, and album
- Total duration if available
- Note any tracks that couldn't be found, with suggestions for alternatives

## Example interactions

**"90 minutes of ambient electronic for deep work"**
→ Search for specific ambient tracks (Brian Eno, Stars of the Lid, Tim Hecker, etc.), accumulate ~90 min using duration_ms, create playlist

**"Create a playlist from examples/road_trip.md"**
→ Read the file, pass contents to `create_playlist_from_markdown`

**"Add some Radiohead to my existing playlist"**
→ `list_playlists` to find it, `search_catalog` for Radiohead tracks, `add_to_playlist`

**"80s new wave workout mix, 20 songs"**
→ Curate 20 upbeat new wave tracks, search each, create and populate

## Tips

- When searching, `types: "songs"` is default and usually what you want
- Catalog IDs are strings like `"1440345678"` — always pass as strings to `add_to_playlist`
- If the user pastes a track list inline (not a file), wrap it in markdown format and use `create_playlist_from_markdown`
- The markdown parser expects `- Artist - Title` format (dash-separated)
