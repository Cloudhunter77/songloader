#!/usr/bin/env python3
"""Download every track in a YouTube playlist as audio files.

Usage:
    python songloader.py <playlist_url> [options]
"""
import argparse
import sys

import yt_dlp
from yt_dlp.utils import sanitize_filename

AUDIO_FORMATS = ("opus", "mp3", "m4a", "flac", "wav")


def cookie_opts(args: argparse.Namespace) -> dict:
    if not args.cookies_from_browser:
        return {}
    return {"cookiesfrombrowser": (args.cookies_from_browser, None, None, None)}


def list_entries(playlist_url: str, args: argparse.Namespace):
    """Resolve the playlist (or single video) into a title + flat entry list, without downloading."""
    list_opts = {
        "extract_flat": "in_playlist",
        "quiet": not args.verbose,
        "no_warnings": not args.verbose,
        "ignoreerrors": True,
        **cookie_opts(args),
    }
    with yt_dlp.YoutubeDL(list_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    title = sanitize_filename(info.get("title") or "Songloader", restricted=True)
    entries = info.get("entries")
    if entries is None:
        entries = [info]

    resolved = []
    for entry in entries:
        if not entry:
            continue
        url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
        if entry.get("id") and "watch?v=" not in str(url) and "://" not in str(url):
            url = f"https://www.youtube.com/watch?v={entry['id']}"
        resolved.append({"url": url, "title": entry.get("title") or url})

    start = max(args.start, 1)
    end = args.end if args.end is not None else len(resolved)
    return title, resolved[start - 1:end]


def build_ydl_opts(args: argparse.Namespace, playlist_title: str) -> dict:
    outtmpl = f"{args.output_dir}/{playlist_title}/%(title)s.%(ext)s"

    postprocessors = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": args.format,
            "preferredquality": args.quality,
        },
        {"key": "FFmpegMetadata", "add_metadata": True},
        {"key": "EmbedThumbnail"},
    ]

    return {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "postprocessors": postprocessors,
        "writethumbnail": True,
        "ignoreerrors": True,
        "concurrent_fragment_downloads": args.workers,
        "quiet": not args.verbose,
        "no_warnings": not args.verbose,
        "restrictfilenames": True,
        **cookie_opts(args),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("playlist_url", help="YouTube playlist URL")
    parser.add_argument(
        "-o", "--output-dir", default="downloads", help="Root directory for downloads (default: downloads)"
    )
    parser.add_argument(
        "-f",
        "--format",
        default="opus",
        choices=AUDIO_FORMATS,
        help="Target audio format (default: opus, kept at native quality when the source is already Opus)",
    )
    parser.add_argument(
        "-q",
        "--quality",
        default="0",
        help="Preferred codec quality passed to ffmpeg; '0' means best available (default: 0)",
    )
    parser.add_argument("--start", type=int, default=1, help="Playlist index to start at (1-based, default: 1)")
    parser.add_argument("--end", type=int, default=None, help="Playlist index to stop at (inclusive, default: all)")
    parser.add_argument(
        "-w", "--workers", type=int, default=4, help="Concurrent fragment downloads per video (default: 4)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show yt-dlp's normal logging output")
    parser.add_argument(
        "--cookies-from-browser",
        dest="cookies_from_browser",
        choices=("chrome", "firefox", "edge", "brave", "opera", "vivaldi", "safari"),
        default=None,
        help="Read cookies from this browser to download as a logged-in user "
        "(often fixes intermittent 403 errors from YouTube)",
    )
    args = parser.parse_args()

    print("Resolving playlist...")
    playlist_title, entries = list_entries(args.playlist_url, args)
    total = len(entries)
    print(f'Playlist "{playlist_title}": {total} track(s) queued\n')

    ydl_opts = build_ydl_opts(args, playlist_title)
    failures = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, entry in enumerate(entries, start=1):
            print(f"[{i}/{total}] {entry['title']}")
            try:
                ydl.download([entry["url"]])
            except Exception as exc:  # noqa: BLE001 - keep the batch going no matter what fails
                print(f"  FAILED: {exc}", file=sys.stderr)
                failures.append((entry["title"], str(exc)))

    if failures:
        print(f"\n{len(failures)}/{total} track(s) failed to download:", file=sys.stderr)
        for title, reason in failures:
            print(f"  - {title}: {reason}", file=sys.stderr)
        return 1

    print(f"\nDone: {total}/{total} track(s) downloaded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
