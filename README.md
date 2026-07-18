# songloader

Download every track in a YouTube playlist as audio files, automatically.
Also converts a Spotify playlist into a matched list of YouTube tracks first, if that's where your songs live.

## Requirements

- Python 3.9+
- [ffmpeg](https://ffmpeg.org/) on your `PATH` (used for audio extraction, metadata tagging, and thumbnail embedding)

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python songloader.py "<playlist_url>" [options]
```

### Options

| Flag | Default | Description |
|---|---|---|
| `-o, --output-dir` | `downloads` | Root directory for downloads |
| `-f, --format` | `opus` | Target audio format: `opus`, `mp3`, `m4a`, `flac`, `wav` |
| `-q, --quality` | `0` | ffmpeg codec quality; `0` = best available |
| `--start` | `1` | Playlist index to start at (1-based) |
| `--end` | (all) | Playlist index to stop at (inclusive) |
| `-w, --workers` | `4` | Concurrent fragment downloads per video |
| `-v, --verbose` | off | Show yt-dlp's normal logging output |
| `--cookies-from-browser` | none | Browser to read cookies from (`chrome`, `firefox`, `edge`, `brave`, `opera`, `vivaldi`, `safari`) — authenticates as a logged-in user, which often fixes intermittent 403 errors |

### Examples

Download a whole playlist as Opus (native YouTube audio quality, no re-encode):

```bash
python songloader.py "https://www.youtube.com/playlist?list=PL..."
```

Download as 320kbps MP3 instead:

```bash
python songloader.py "https://www.youtube.com/playlist?list=PL..." -f mp3 -q 0
```

Only fetch entries 10-20 of the playlist:

```bash
python songloader.py "https://www.youtube.com/playlist?list=PL..." --start 10 --end 20
```

## Output layout

Files are saved flat, one folder per playlist:

```
downloads/
  <Playlist Name>/
    <Track Title>.opus
    ...
```

Each file has title/uploader metadata and the video thumbnail embedded as cover art.

## Notes

- Re-running the tool against the same playlist re-downloads everything currently in it (no skip/archive tracking) — safe to re-run, just expect duplicates if files already exist unless you clear the output directory first.
- Each track downloads independently: if one fails (removed/private video, transient network error, HTTP 403, etc.) the tool logs it and moves on to the next track instead of aborting the whole run. Failures are summarized at the end and the tool exits non-zero if any occurred.

## Spotify playlists

`songloader.py` only understands YouTube. If your songs are collected in a **Spotify** playlist instead, use `spotify_to_youtube.py` first to match each track to a YouTube video, then feed the result into `songloader.py`.

### One-time setup

Create a free Spotify API app (read-only, no user login needed) at https://developer.spotify.com/dashboard → "Create app" → any name/redirect URI works, you just need the **Client ID** and **Client Secret** it gives you. Then either export them:

```bash
export SPOTIFY_CLIENT_ID=...
export SPOTIFY_CLIENT_SECRET=...
```

or pass `--client-id`/`--client-secret` on each run.

### Usage

```bash
python spotify_to_youtube.py "https://open.spotify.com/playlist/..." -o tracks.txt
python songloader.py tracks.txt -f flac
```

The playlist must be **public** (anyone-with-the-link, not private/collaborative-only). The first command reads the track list via Spotify's Web API, searches YouTube for each `<artist> - <title>` via yt-dlp, and writes matched `<youtube_url><TAB><artist - title>` lines to `tracks.txt`. The second command downloads them exactly like a normal playlist — `songloader.py` treats an existing local file path as a list of tracks to fetch instead of a YouTube URL.

Matching is a best-effort YouTube search per track — always worth skimming the printed `-> <matched title>` lines (or the output file) for any suspicious mismatches (wrong remix, live version, etc.) before bulk-downloading.

## Troubleshooting

**`HTTP Error 403: Forbidden` on some tracks, or a `No supported JavaScript runtime` warning**

This is YouTube's anti-bot system, not a bug in the tool — it happens sporadically and gets worse over time as YouTube tightens things. Try, roughly in order of effort:

1. **Update yt-dlp** — this fight moves fast and old versions break first: `pip install -U yt-dlp`
2. **Use `--cookies-from-browser <browser>`** — log into YouTube in that browser first, then pass its name (e.g. `--cookies-from-browser chrome`). Authenticated requests get throttled far less than anonymous ones and this fixes most persistent 403s.
3. **Install a JS runtime** (e.g. [Deno](https://deno.land)) so yt-dlp can execute YouTube's signature-deciphering JavaScript itself instead of falling back to a client that YouTube may throttle harder.
4. If only a handful of tracks fail, just re-run the tool later with `--start`/`--end` targeting those specific indices — 403s are often transient.
