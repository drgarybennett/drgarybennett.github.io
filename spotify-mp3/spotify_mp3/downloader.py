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
    Downloads and converts a single track to MP3.
    Returns the output Path on success, None on failure.
    Skips (returns existing path) if the file already exists.
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
