"""
YouTube downloader that converts search results to 192 kbps MP3 files.

Public surface:
    download_track(meta, output_dir, ...) — downloads one track and returns
        the output Path, or None if the track could not be found/downloaded.

Implementation notes:
- Searches YouTube for up to 3 candidates using extract_flat (fast, no
  download), then tries each in order until one succeeds. This handles
  blocked, region-restricted, or removed videos automatically.
- Uses yt-dlp's Python API (no subprocess) via the injectable ydl_class
  parameter, which allows unit tests to pass a mock instead of real YoutubeDL.
- noplaylist: True is always set to prevent yt-dlp from accidentally
  downloading an entire YouTube playlist when a search result is one.
- ffmpeg converts the downloaded audio to MP3 as a post-processor step;
  download_track verifies the .mp3 file exists afterwards so a silent
  ffmpeg failure is caught and reported as None rather than corrupting state.
- Both DownloadError and ExtractorError are caught; the latter covers
  removed or geo-blocked videos that yt-dlp raises differently.
"""

from pathlib import Path
from typing import Optional, Type

import yt_dlp
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

_DOWNLOAD_ERRORS = (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError)

from .spotify import TrackMeta

_SEARCH_COUNT = 3


def download_track(
    meta: TrackMeta,
    output_dir: Path,
    ffmpeg_path: Optional[str] = None,
    browser: Optional[str] = None,
    ydl_class: Type = yt_dlp.YoutubeDL,
) -> Optional[Path]:
    """
    Search YouTube for a track and download it as a 192 kbps MP3.

    Tries up to 3 YouTube search results in order. If the first result is
    blocked or region-restricted, the next candidate is attempted automatically.

    Args:
        meta:        Track metadata used to build the search query and output
                     filename.
        output_dir:  Directory to save the MP3 in. Created if it doesn't exist.
        ffmpeg_path: Absolute path to the ffmpeg binary. Pass this when ffmpeg
                     is not on PATH (common on Windows). None uses PATH lookup.
        ydl_class:   yt-dlp class to instantiate. Override in tests to inject
                     a mock without making real network calls.

    Returns:
        Path to the downloaded .mp3 file on success.
        None if all candidates failed or no results were found.
        If the file already exists the existing Path is returned immediately
        (resume-friendly — no re-download).
    """
    output_path = output_dir / meta.output_filename
    if output_path.exists():
        return output_path

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(meta.output_filename).stem
    outtmpl = str(output_dir / f"{stem}.%(ext)s")

    download_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    if ffmpeg_path:
        download_opts["ffmpeg_location"] = ffmpeg_path
    if browser:
        download_opts["cookiesfrombrowser"] = (browser,)

    candidates = _gather_candidates(meta.artist, meta.title, ydl_class, browser=browser)
    if not candidates:
        return None

    for video_url in candidates:
        try:
            _run_download(video_url, download_opts, ydl_class)
            if output_path.exists():
                return output_path
        except _DOWNLOAD_ERRORS:
            continue

    return None


def _query_variations(artist: str, title: str) -> list[str]:
    """Return search queries from most specific to broadest."""
    return [
        f"ytsearch{_SEARCH_COUNT}:{artist} {title} official audio",
        f"ytsearch{_SEARCH_COUNT}:{artist} {title} official video",
        f"ytsearch{_SEARCH_COUNT}:{artist} {title} lyrics",
        f"ytsearch{_SEARCH_COUNT}:{artist} {title}",
        f"ytsearch{_SEARCH_COUNT}:{title} {artist}",
    ]


def _gather_candidates(
    artist: str,
    title: str,
    ydl_class: type,
    browser: Optional[str] = None,
) -> list[str]:
    """
    Collect unique YouTube video URLs across multiple query variations.
    Tries each query in order and stops once enough candidates are gathered.
    """
    seen: set[str] = set()
    candidates: list[str] = []

    for query in _query_variations(artist, title):
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "noplaylist": False,
        }
        if browser:
            opts["cookiesfrombrowser"] = (browser,)
        try:
            with ydl_class(opts) as ydl:
                info = ydl.extract_info(query, download=False)
                for e in (info.get("entries") or []):
                    vid_id = e.get("id") if e else None
                    if vid_id and vid_id not in seen:
                        seen.add(vid_id)
                        candidates.append(f"https://www.youtube.com/watch?v={vid_id}")
        except Exception:
            continue

        if len(candidates) >= _SEARCH_COUNT * 2:
            break

    return candidates


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(_DOWNLOAD_ERRORS),
    reraise=True,
)
def _run_download(url: str, opts: dict, ydl_class: type) -> None:
    with ydl_class(opts) as ydl:
        ydl.extract_info(url, download=True)
