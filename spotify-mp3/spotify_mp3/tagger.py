"""
ID3 tag writer for downloaded MP3 files.

Public surface:
    tag_file(path, meta) — writes standard tags and embeds album art.
        All operations are best-effort: a failure on any individual tag is
        silently swallowed so a bad Spotify metadata field or a CDN error
        never prevents the rest of the tags from being written.

Implementation notes:
- Standard text tags (title, artist, album, tracknumber) use mutagen's
  EasyID3 API which handles frame encoding automatically.
- Album art requires raw ID3 access (APIC frame) because EasyID3 doesn't
  expose binary frames. The two passes (EasyID3 save, then ID3 APIC save)
  are intentional — writing both in one ID3 pass would require manually
  constructing all text frames.
- MIME type is read from the Content-Type response header; magic-byte
  detection is the fallback for servers that omit or mislabel the header.
"""

from pathlib import Path

import requests
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3, error as ID3Error
from mutagen.mp3 import MP3

from .spotify import TrackMeta


def tag_file(path: Path, meta: TrackMeta) -> None:
    """
    Write ID3 tags to an MP3 file.

    Writes title, artist, album, track number, and album art (front cover).
    Each field is skipped silently if the data is empty or an error occurs,
    so partial metadata is always preferred over no metadata.

    Args:
        path: Path to the .mp3 file to tag. Must exist and be a valid MPEG
              audio file; an unrecoverable parse error causes an early return
              with no tags written.
        meta: Track metadata source. Fields are taken as-is from Spotify;
              empty strings and None values are handled gracefully.
    """
    try:
        audio = EasyID3(path)
    except ID3Error:
        try:
            mp3 = MP3(path)
            mp3.add_tags()
            mp3.save()
            audio = EasyID3(path)
        except Exception:
            return

    _safe_set(audio, "title", [meta.title])
    _safe_set(audio, "artist", [meta.artist])
    _safe_set(audio, "album", [meta.album])
    if meta.track_number:
        _safe_set(audio, "tracknumber", [meta.track_number])
    audio.save()

    if meta.album_art_url:
        _embed_album_art(path, meta.album_art_url)


def _safe_set(audio: EasyID3, key: str, value: list) -> None:
    try:
        audio[key] = value
    except Exception:
        pass


def _embed_album_art(path: Path, url: str) -> None:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        image_data = resp.content
        mime = resp.headers.get("content-type", "").split(";")[0].strip()
        if not mime.startswith("image/"):
            if image_data[:2] == b"\xff\xd8":
                mime = "image/jpeg"
            elif image_data[:8] == b"\x89PNG\r\n\x1a\n":
                mime = "image/png"
            elif image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
                mime = "image/webp"
            else:
                mime = "image/jpeg"
    except Exception:
        return

    try:
        tags = ID3(path)
        tags.add(APIC(
            encoding=3,
            mime=mime,
            type=3,
            desc="Cover",
            data=image_data,
        ))
        tags.save()
    except Exception:
        return
