from pathlib import Path
from unittest.mock import patch

import pytest
from mutagen.easyid3 import EasyID3

from spotify_mp3.spotify import TrackMeta
from spotify_mp3.tagger import tag_file


def test_standard_tags_written(silence_mp3, sample_meta):
    tag_file(silence_mp3, sample_meta)
    audio = EasyID3(silence_mp3)
    assert audio["title"] == ["Bohemian Rhapsody"]
    assert audio["artist"] == ["Queen"]
    assert audio["album"] == ["A Night at the Opera"]
    assert audio["tracknumber"] == ["11/12"]


def test_missing_track_number_skipped(silence_mp3):
    meta = TrackMeta(
        title="Song",
        artist="Artist",
        album="Album",
        track_number="",
        album_art_url=None,
        spotify_uri="",
        output_filename="Artist - Song.mp3",
    )
    tag_file(silence_mp3, meta)
    audio = EasyID3(silence_mp3)
    assert audio.get("tracknumber") is None


def test_all_empty_fields_dont_crash(silence_mp3):
    meta = TrackMeta(
        title="",
        artist="",
        album="",
        track_number="",
        album_art_url=None,
        spotify_uri="",
        output_filename="x.mp3",
    )
    tag_file(silence_mp3, meta)


def test_album_art_http_error_skipped(silence_mp3, sample_meta):
    meta = TrackMeta(
        title=sample_meta.title,
        artist=sample_meta.artist,
        album=sample_meta.album,
        track_number=sample_meta.track_number,
        album_art_url="https://example.com/art.jpg",
        spotify_uri=sample_meta.spotify_uri,
        output_filename=sample_meta.output_filename,
    )
    with patch("spotify_mp3.tagger.requests.get") as mock_get:
        mock_get.side_effect = Exception("Network error")
        tag_file(silence_mp3, meta)
    audio = EasyID3(silence_mp3)
    assert audio["title"] == ["Bohemian Rhapsody"]
