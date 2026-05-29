import argparse
import sys
from pathlib import Path

from tqdm import tqdm

from .downloader import download_track
from .spotify import SpotifyClient
from .tagger import tag_file

DOWNLOADS_ROOT = Path("downloads")


def main():
    parser = argparse.ArgumentParser(
        description="Download Spotify tracks as 192kbps MP3 files via YouTube."
    )
    parser.add_argument("url", help="Spotify track, playlist, or album URL/URI")
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
    args = parser.parse_args()

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

    failed: list = []
    for meta in tqdm(tracks, desc=context_name, unit="track"):
        result = download_track(meta, output_dir, ffmpeg_path=args.ffmpeg_path)
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
    from .helpers import sanitize_filename
    return sanitize_filename(name)


if __name__ == "__main__":
    main()
