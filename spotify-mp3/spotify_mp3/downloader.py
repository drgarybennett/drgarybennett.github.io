"""
YouTube downloader that converts search results to 192 kbps MP3 files.

Public surface:
    download_track(meta, output_dir, ...) — downloads one track and returns
        the output Path, or None if the track could not be found/downloaded.

Implementation notes:
- Uses yt-dlp's Python API (no subprocess) via the injectable ydl_class
  parameter, which allows unit tests to pass a mock instead of real YoutubeDL.
- The YouTube search query is "<artist> <title> official audio" via the
  ytsearch1: prefix so yt-dlp picks exactly one result.
- noplaylist: True is always set to prevent yt-dlp from accidentally
  downloading an entire YouTube playlist when the first search result is one.
- ffmpeg converts the downloaded audio to MP3 as a post-processor step;
  download_track verifies the .mp3 file exists afterwards so a silent
  ffmpeg failure is caught and reported as None rather than corrupting state.
- Both DownloadError and ExtractorError are caught and retried; the latter
  covers removed or geo-blocked videos that yt-dlp raises differently.
"""

from pathlib import Path
from typing import Optional, Type

import yt_dlp
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

_DOWNLOAD_ERRORS = (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError)

from .spotify import TrackMeta


def download_track(
    meta: TrackMeta,
    output_dir: Path,
    ffmpeg_path: Optional[str] = None,
    ydl_class: Type = yt_dlp.YoutubeDL,
) -> Optional[Path]:
    """
    Search YouTube for a track and download it as a 192 kbps MP3.

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
        None if the track could not be found on YouTube, the download failed
        after 3 retries, or ffmpeg post-processing did not produce a .mp3 file.
        If the file already exists the existing Path is returned immediately
        (resume-friendly — no re-download).
    """
    output_path = output_dir / meta.output_filename
    if output_path.exists():
        return output_path

    output_dir.mkdir(parents=True, exist_ok=True)
    query = f"ytsearch1:{meta.artist} {meta.title} official audio"
    stem = Path(meta.output_filename).stem
    outtmpl = str(output_dir / f"{stem}.%(ext)s")

    opts = {
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
        opts["ffmpeg_location"] = ffmpeg_path

    try:
        _run_download(query, opts, ydl_class)
    except _DOWNLOAD_ERRORS:
        return None

    if not output_path.exists():
        return None
    return output_path


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(_DOWNLOAD_ERRORS),
    reraise=True,
)
def _run_download(query: str, opts: dict, ydl_class: type) -> None:
    with ydl_class(opts) as ydl:
        ydl.extract_info(query, download=True)
