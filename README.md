# songloader

Download every track in a YouTube playlist as audio files, automatically.

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
- Individual video failures (removed/private videos, etc.) don't stop the rest of the playlist; failures are summarized at the end and the tool exits non-zero if any occurred.
