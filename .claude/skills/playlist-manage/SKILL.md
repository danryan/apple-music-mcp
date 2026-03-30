---
name: playlist-manage
description: Manage existing Apple Music playlists — find duplicates, merge playlists, search across playlists, and inspect contents
argument-hint: <action: list, search, duplicates, merge, or describe what you need>
user-invocable: true
disable-model-invocation: false
---

# Playlist Manager

You have access to an Apple Music MCP server with these tools:

- `search_catalog(query, limit, types)` — Search Apple Music for songs, albums, or artists
- `list_playlists()` — List the user's Apple Music library playlists
- `search_playlist(playlist_id, query)` — Search within a playlist by title/artist/album
- `add_to_playlist(playlist_id, song_ids)` — Add songs by catalog ID (skips duplicates)
- `create_playlist(name, description)` — Create a new library playlist

## Your task

Help the user manage their Apple Music playlists: **$ARGUMENTS**

## Workflow

### 1. Understand the request

Determine what the user needs:
- **List/browse**: "show my playlists", "what playlists do I have"
- **Search**: "find Radiohead across my playlists", "is this song in any playlist"
- **Inspect**: "what's in my workout playlist", "how many tracks in X"
- **Merge**: "combine my two jazz playlists into one"
- **Find duplicates**: "are there duplicates in my playlist"
- **Add tracks**: "add these songs to my existing playlist"

### 2. Find the right playlist(s)

Start with `list_playlists()` to see all available playlists. Match the user's description to playlist names — be flexible with matching (case-insensitive, partial matches).

If the user is vague ("my workout playlist"), list playlists and pick the best match, or ask if ambiguous.

### 3. Perform the action

**Listing playlists:**
- Call `list_playlists()` and present a clean table with name and track count

**Searching within a playlist:**
- Use `search_playlist(playlist_id, query)` to find specific tracks
- Report matches with track details

**Searching across playlists:**
- Call `list_playlists()`, then `search_playlist` on each relevant playlist
- Report which playlists contain the track

**Finding duplicates within a playlist:**
- Use `search_playlist` with artist names or song titles that might appear multiple times
- Note: the API doesn't return full track lists directly, so search for specific artists/titles the user mentions, or ask what to check for

**Merging playlists:**
- Search the source playlists to identify tracks
- Create a new playlist with `create_playlist` or add to an existing one with `add_to_playlist`
- The `add_to_playlist` tool automatically skips duplicates

**Adding tracks:**
- Use `search_catalog` to find tracks by name
- Use `add_to_playlist` to add them to the target playlist

### 4. Report results

Present results clearly:
- Use tables for track listings
- Show track counts and totals
- Note any issues (tracks not found, duplicates skipped)

## Example interactions

**"show my playlists"**
→ Call `list_playlists()`, display as a formatted list with names and track counts

**"is Bohemian Rhapsody in any of my playlists?"**
→ List playlists, search each for "Bohemian Rhapsody", report which ones contain it

**"merge my 'Chill Vibes' and 'Sunday Morning' playlists"**
→ List playlists to find both, search each to understand contents, create a new merged playlist or add contents of one to the other

**"add the top 5 Tame Impala songs to my psychedelic playlist"**
→ Find the playlist via `list_playlists`, search catalog for Tame Impala tracks, add to playlist

## Tips

- Always start with `list_playlists()` to get accurate playlist IDs — never guess IDs
- `add_to_playlist` handles duplicate prevention automatically
- When merging, ask the user if they want a new playlist or to add to one of the existing ones
- Playlist IDs are opaque strings — always look them up, never hardcode
