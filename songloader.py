#!/usr/bin/env python3
"""Download every track in a YouTube playlist as audio files.

Usage:
    python songloader.py <playlist_url> [options]
"""
import argparse
import sys

import yt_dlp

AUDIO_FORMATS = ("opus", "mp3", "m4a", "flac", "wav")


def build_ydl_opts(args: argparse.Namespace) -> dict:
    outtmpl = f"{args.output_dir}/%(playlist_title,playlist|Songloader)s/%(title)s.%(ext)s"

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
        "noplaylist": False,
        "playliststart": args.start,
        "playlistend": args.end,
        "concurrent_fragment_downloads": args.workers,
        "quiet": not args.verbose,
        "no_warnings": not args.verbose,
        "restrictfilenames": True,
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
    args = parser.parse_args()

    ydl_opts = build_ydl_opts(args)

    failures = []

    def hook(d):
        if d["status"] == "error":
            failures.append(d.get("filename", "unknown"))

    ydl_opts["progress_hooks"] = [hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([args.playlist_url])

    if failures:
        print(f"\n{len(failures)} track(s) failed to download:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
