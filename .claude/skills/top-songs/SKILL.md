---
name: top-songs
description: Get an artist's top songs or compare top tracks across multiple artists
argument-hint: <artist name, or "compare: Artist1 vs Artist2">
user-invocable: true
disable-model-invocation: false
---

# Top Songs

You have access to an Apple Music MCP server with these tools:

- `get_artist_top_songs(artist, limit, lead_artist_only)` — Get an artist's top songs sorted by popularity
- `search_catalog(query, limit, types)` — Search Apple Music for songs, albums, or artists

## Your task

Show the user top songs for the requested artist(s): **$ARGUMENTS**

## Workflow

### 1. Understand the request

Determine the mode:
- **Single artist**: "top songs by MF DOOM", "best Stevie Wonder tracks"
- **Compare artists**: "compare Kendrick vs J. Cole", "top songs: Drake, Future, Metro Boomin"
- **Filtered**: "top Radiohead songs that aren't from OK Computer", "solo work only"

### 2. Fetch top songs

Use `get_artist_top_songs` for each artist:
- Default `limit=20` for single artist, `limit=10` for comparisons
- Set `lead_artist_only=True` by default to exclude features — set to `False` if the user wants everything or asks for features/collaborations
- If the artist name is ambiguous, search first with `search_catalog(query, types="artists")` to confirm

### 3. Present results

**Single artist — format as a numbered list:**
```
## Top Songs by [Artist]

 #  | Title                  | Album                | Duration
----|------------------------|----------------------|---------
 1  | Song Name              | Album Name           | 3:45
 2  | ...                    | ...                  | ...
```

Include:
- Track number, title, album, duration
- Total duration at the bottom

**Comparison — format as side-by-side or sequential sections:**
```
## [Artist 1] vs [Artist 2]

### [Artist 1] — Top 10
(numbered list with title, album, duration)

### [Artist 2] — Top 10
(numbered list with title, album, duration)
```

Add a brief commentary comparing the two — most popular era, genre range, solo vs collaboration ratio, etc.

### 4. Offer next steps

After presenting results, suggest relevant follow-ups:
- "Want me to create a playlist from these?" → `/playlist`
- "Want to discover similar artists?" → `/discover`
- "Want to add any of these to an existing playlist?" → `/playlist-manage`

## Example interactions

**"top songs by MF DOOM"**
→ `get_artist_top_songs("MF DOOM", limit=20, lead_artist_only=True)`, format as numbered table

**"compare Kendrick vs J. Cole"**
→ Fetch top 10 for each, present side by side, add brief comparison commentary

**"top songs: Drake, Future, Metro Boomin"**
→ Fetch top 10 for each, present in sections, note any overlapping collaborations

**"Radiohead deep cuts — skip the obvious ones"**
→ Fetch top 20, use your music knowledge to call out which are the well-known hits vs deeper cuts, or fetch more and highlight tracks ranked lower

## Tips

- `duration_ms` from results can be converted to `m:ss` format for display
- For artists with name collisions (e.g., "The National" vs "National"), verify with `search_catalog(types="artists")` first
- `lead_artist_only=True` filters out features — useful for prolific collaborators
- If the user asks for "best" rather than "top", add your own music-knowledge commentary on which tracks are critically acclaimed vs just popular
