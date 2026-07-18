#!/usr/bin/env python3
"""Match every track in a public Spotify playlist to a YouTube video.

Writes a text file of "<youtube_url><TAB><artist> - <title>" lines that
songloader.py can read directly and download.

Usage:
    python spotify_to_youtube.py <spotify_playlist_url> [options]

Requires a free Spotify API app (Client ID + Secret) from
https://developer.spotify.com/dashboard - read-only access to public
playlist metadata, no user login needed.
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

import yt_dlp

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"


def get_access_token(client_id: str, client_secret: str) -> str:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        SPOTIFY_TOKEN_URL,
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["access_token"]


def extract_playlist_id(url: str) -> str:
    match = re.search(r"playlist[/:]([a-zA-Z0-9]+)", url)
    if not match:
        raise ValueError(f"Could not find a playlist ID in: {url}")
    return match.group(1)


def spotify_get(path: str, token: str) -> dict:
    url = path if path.startswith("http") else f"{SPOTIFY_API_BASE}{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def fetch_playlist_tracks(playlist_id: str, token: str):
    name_info = spotify_get(f"/playlists/{playlist_id}?fields=name", token)
    playlist_name = name_info.get("name") or playlist_id

    tracks = []
    path = f"/playlists/{playlist_id}/tracks?limit=100&fields=next,items(track(name,artists(name)))"
    while path:
        page = spotify_get(path, token)
        for item in page.get("items", []):
            track = item.get("track")
            if not track or not track.get("name"):
                continue  # removed or local track, nothing to match
            artists = ", ".join(a["name"] for a in track.get("artists", []))
            tracks.append({"title": track["name"], "artists": artists})
        path = page.get("next")

    return playlist_name, tracks


def find_youtube_match(query: str):
    opts = {"quiet": True, "no_warnings": True, "default_search": "ytsearch1", "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)
    entries = info.get("entries") or []
    if not entries:
        return None
    top = entries[0]
    url = top.get("webpage_url") or f"https://www.youtube.com/watch?v={top['id']}"
    return url, top.get("title")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("playlist_url", help="Spotify playlist URL (must be public)")
    parser.add_argument("-o", "--output", default=None, help="Output .txt path (default: <playlist name>.txt)")
    parser.add_argument(
        "--client-id", default=os.environ.get("SPOTIFY_CLIENT_ID"), help="Spotify API client ID (or set SPOTIFY_CLIENT_ID)"
    )
    parser.add_argument(
        "--client-secret",
        default=os.environ.get("SPOTIFY_CLIENT_SECRET"),
        help="Spotify API client secret (or set SPOTIFY_CLIENT_SECRET)",
    )
    args = parser.parse_args()

    if not args.client_id or not args.client_secret:
        print(
            "Missing Spotify API credentials. Create a free app at "
            "https://developer.spotify.com/dashboard, then pass --client-id/--client-secret "
            "or set the SPOTIFY_CLIENT_ID/SPOTIFY_CLIENT_SECRET environment variables.",
            file=sys.stderr,
        )
        return 1

    print("Authenticating with Spotify...")
    try:
        token = get_access_token(args.client_id, args.client_secret)
    except urllib.error.HTTPError as exc:
        print(f"Spotify authentication failed: {exc}", file=sys.stderr)
        return 1

    playlist_id = extract_playlist_id(args.playlist_url)
    print("Fetching playlist tracks...")
    playlist_name, tracks = fetch_playlist_tracks(playlist_id, token)
    total = len(tracks)
    print(f'Playlist "{playlist_name}": {total} track(s)\n')

    output_path = args.output or f"{playlist_name}.txt".replace("/", "_")
    matched = 0
    misses = []

    with open(output_path, "w", encoding="utf-8") as out:
        for i, track in enumerate(tracks, start=1):
            query = f"{track['artists']} - {track['title']}"
            print(f"[{i}/{total}] {query}")
            try:
                result = find_youtube_match(f"{query} audio")
            except Exception as exc:  # noqa: BLE001 - one bad match shouldn't stop the rest
                result = None
                print(f"  search failed: {exc}", file=sys.stderr)

            if not result:
                misses.append(query)
                print("  no match found", file=sys.stderr)
                continue

            url, yt_title = result
            out.write(f"{url}\t{query}\n")
            matched += 1
            print(f"  -> {yt_title}")

    print(f"\nMatched {matched}/{total} tracks. Wrote {output_path}")
    if misses:
        print(f"\n{len(misses)} track(s) had no match:", file=sys.stderr)
        for m in misses:
            print(f"  - {m}", file=sys.stderr)

    print(f"\nNext: python songloader.py {output_path!r}")
    return 0 if not misses else 1


if __name__ == "__main__":
    sys.exit(main())
