---
name: discover
description: Discover and recommend music — find similar artists, explore genres, and get personalized suggestions based on taste
argument-hint: <artist, genre, mood, or "music like X">
user-invocable: true
disable-model-invocation: false
---

# Music Discovery

You have access to an Apple Music MCP server with these tools:

- `search_catalog(query, limit, types)` — Search Apple Music for songs, albums, or artists
- `get_artist_top_songs(artist, limit, lead_artist_only)` — Get an artist's top songs sorted by popularity
- `get_recently_played(limit)` — Get recently played albums/playlists/stations
- `get_recommendations(limit)` — Get personalized recommendation groups from Apple Music
- `search_library(query, types, limit)` — Search the user's library

## Your task

Help the user discover music based on their request: **$ARGUMENTS**

## Workflow

### 1. Understand the request

Determine what the user is looking for:
- **Similar artists**: "artists like Radiohead", "if I like Bjork what else would I like"
- **Genre exploration**: "best 90s trip-hop", "introduce me to shoegaze"
- **Mood/vibe**: "dark ambient stuff", "upbeat funk"
- **Artist deep-dive**: "I just discovered Khruangbin, where do I start"

### 2. Use your music knowledge

Draw on your knowledge of music history, genres, scenes, and artist connections to generate recommendations. Think about:
- **Direct influences**: who influenced the artist, who they influenced
- **Scene connections**: same label, same era, same city, collaborators
- **Sonic similarity**: similar production style, instrumentation, mood
- **Genre lineage**: subgenre roots and branches

### 3. Verify and enrich with catalog searches

For each recommendation, use `search_catalog` or `get_artist_top_songs` to:
- Confirm the artist/album/song exists in Apple Music
- Pull specific track names, albums, and catalog IDs
- Get concrete "start here" tracks for each recommendation

**Search strategy:**
- Use `types: "artists"` to find artists, then `get_artist_top_songs` for their best tracks
- Use `types: "songs"` when looking for specific tracks
- Use `types: "albums"` when recommending full albums
- If a search misses, try alternate spellings or shorter queries

### 4. Present recommendations

Structure your response clearly:
- Group by relevance (closest matches first) or by theme/subgenre
- For each artist/recommendation, include:
  - Why they're relevant (the connection to the user's taste)
  - 2-3 specific tracks or an album to start with
  - A brief description of their sound
- Aim for 5-10 recommendations unless the user asks for more or fewer
- Distinguish between well-known picks and deeper cuts

## Example interactions

**"artists like Radiohead"**
→ Recommend artists across Radiohead's influences (Talking Heads, Can), peers (Portishead, Massive Attack), and descendants (Everything Everything, Alt-J). Verify each in catalog, provide starting tracks.

**"introduce me to Afrobeat"**
→ Start with Fela Kuti as the origin, branch to Tony Allen, Antibalas, Mdou Moctar, KOKOROKO. Group by classic vs modern. Provide key albums and standout tracks.

**"dark electronic music for late nights"**
→ Think Burial, Andy Stott, Actress, Demdike Stare, Oneohtrix Point Never. Verify tracks, note the different flavors (dubstep, techno, ambient).

**"I like Kendrick Lamar and Frank Ocean, what else?"**
→ Find the intersection — artists who blend hip-hop with introspection and genre-bending: Isaiah Rashad, Sampha, SZA, Anderson .Paak, Noname. Pull top songs for each.

## Tips

- Don't just list obvious names — mix well-known with genuinely surprising picks
- Explain *why* each recommendation connects, not just *what* to listen to
- When the user names multiple artists, find the intersection of their tastes
- If the user wants to turn recommendations into a playlist, suggest using `/playlist`
- Catalog IDs from search results can be used directly with `/playlist` to build a playlist from discoveries
