"""
Command-line entry point for spotify-mp3.

Usage:
    spotify-mp3 <spotify-url-or-uri> [options]
    spotify-mp3 --retry-failed <failed.txt> -o <output-dir> [options]

The main() function is registered as the console_scripts entry point in
pyproject.toml, so after `pip install -e .` the tool is available as the
`spotify-mp3` command.

Pipeline for each track:
    1. SpotifyClient.get_tracks()  — fetch metadata from Spotify API
    2. download_track()            — search YouTube, download, convert to MP3
    3. tag_file()                  — embed ID3 tags (best-effort)
    4. failed.txt                  — log any tracks that couldn't be downloaded
"""

import argparse
import sys
from pathlib import Path

from tqdm import tqdm

from .downloader import download_track
from .spotify import SpotifyClient, TrackMeta
from .helpers import sanitize_filename
from .tagger import tag_file

DOWNLOADS_ROOT = Path("downloads")


def main():
    parser = argparse.ArgumentParser(
        description="Download Spotify tracks as 192kbps MP3 files via YouTube."
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Spotify track, playlist, or album URL/URI",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DOWNLOADS_ROOT,
        help="Root output directory (default: ./downloads)",
    )
    parser.add_argument(
        "--ffmpeg-path",
        default=None,
        help="Path to ffmpeg binary if not on PATH",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print track list without downloading",
    )
    parser.add_argument(
        "--browser",
        default=None,
        choices=["chrome", "safari", "firefox", "edge", "brave", "chromium"],
        help="Pass cookies from this browser to bypass YouTube bot detection",
    )
    parser.add_argument(
        "--retry-failed",
        metavar="FAILED_TXT",
        type=Path,
        help="Re-attempt all tracks listed in a failed.txt file using "
             "broader search queries. Successful downloads are removed "
             "from the file.",
    )
    args = parser.parse_args()

    if args.retry_failed:
        _retry_failed(args)
        return

    if not args.url:
        parser.error("url is required unless --retry-failed is used")

    client = SpotifyClient()
    try:
        context_name, tracks = client.get_tracks(args.url)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not tracks:
        print("No tracks found.", file=sys.stderr)
        sys.exit(0)

    is_single = (
        len(tracks) == 1
        and "playlist" not in args.url
        and "album" not in args.url
    )
    output_dir = args.output if is_single else args.output / _safe_dir(context_name)

    if args.dry_run:
        print(f"[dry-run] {context_name} — {len(tracks)} track(s) → {output_dir}")
        for t in tracks:
            print(f"  {t.output_filename}")
        return

    _run_downloads(tracks, output_dir, args)


def _retry_failed(args: argparse.Namespace) -> None:
    """Re-attempt tracks from a failed.txt, updating the file in place."""
    failed_path: Path = args.retry_failed
    if not failed_path.exists():
        print(f"Error: {failed_path} not found", file=sys.stderr)
        sys.exit(1)

    lines = failed_path.read_text().splitlines()
    entries = []
    for line in lines:
        parts = line.split("\t")
        if len(parts) >= 3:
            uri, artist, title = parts[0], parts[1], parts[2]
            entries.append((uri, artist, title))

    if not entries:
        print("No entries in failed.txt")
        return

    # Output dir defaults to the directory containing failed.txt
    output_dir = args.output if args.output != DOWNLOADS_ROOT else failed_path.parent
    print(f"Retrying {len(entries)} failed track(s) → {output_dir}\n")

    still_failed = []
    for uri, artist, title in tqdm(entries, unit="track"):
        filename = sanitize_filename(f"{artist} - {title}") + ".mp3"
        meta = TrackMeta(
            title=title,
            artist=artist,
            album="",
            track_number="",
            album_art_url=None,
            spotify_uri=uri,
            output_filename=filename,
        )
        result = download_track(
            meta, output_dir,
            ffmpeg_path=args.ffmpeg_path,
            browser=args.browser,
        )
        if result is None:
            still_failed.append(f"{uri}\t{artist}\t{title}")
        else:
            tag_file(result, meta)

    # Rewrite failed.txt with only the ones that still failed
    failed_path.write_text("\n".join(still_failed) + ("\n" if still_failed else ""))
    recovered = len(entries) - len(still_failed)
    print(f"\nRecovered: {recovered}  Still failed: {len(still_failed)}")
    if still_failed:
        print(f"Remaining failures updated in {failed_path}")


def _run_downloads(tracks: list, output_dir: Path, args: argparse.Namespace) -> None:
    failed: list = []
    for meta in tqdm(tracks, desc=output_dir.name, unit="track"):
        result = download_track(
            meta, output_dir,
            ffmpeg_path=args.ffmpeg_path,
            browser=args.browser,
        )
        if result is None:
            failed.append(meta)
            continue
        tag_file(result, meta)

    if failed:
        output_dir.mkdir(parents=True, exist_ok=True)
        failed_path = output_dir / "failed.txt"
        with open(failed_path, "a") as f:
            for meta in failed:
                f.write(f"{meta.spotify_uri}\t{meta.artist}\t{meta.title}\n")
        print(f"\n{len(failed)} track(s) failed. See {failed_path}", file=sys.stderr)


def _safe_dir(name: str) -> str:
    return sanitize_filename(name)


if __name__ == "__main__":
    main()
