from pathlib import Path

import requests
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3, error as ID3Error
from mutagen.mp3 import MP3

from .spotify import TrackMeta


def tag_file(path: Path, meta: TrackMeta) -> None:
    """Embeds ID3 tags. Silently skips any tag if data is unavailable."""
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
        mime = "image/jpeg" if image_data[:2] == b"\xff\xd8" else "image/png"
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
