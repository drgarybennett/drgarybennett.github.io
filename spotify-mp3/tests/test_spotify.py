from unittest.mock import MagicMock, patch

import pytest

from spotify_mp3.spotify import (
    SpotifyClient,
    _detect_kind,
    _strip_query_params,
    _track_to_meta,
)


def _mock_track_item(title="Test Track", artist="Test Artist", track_num=1, total=10):
    return {
        "track": {
            "name": title,
            "artists": [{"name": artist}],
            "album": {
                "name": "Test Album",
                "images": [{"url": "https://example.com/art.jpg"}],
                "total_tracks": total,
            },
            "track_number": track_num,
            "uri": f"spotify:track:{title.replace(' ', '')}",
        }
    }


def test_strip_query_params():
    assert _strip_query_params("https://open.spotify.com/playlist/abc?si=123") == \
        "https://open.spotify.com/playlist/abc"


def test_strip_query_params_no_params():
    url = "spotify:track:abc123"
    assert _strip_query_params(url) == url


def test_detect_kind_track():
    assert _detect_kind("https://open.spotify.com/track/abc") == "track"


def test_detect_kind_playlist():
    assert _detect_kind("https://open.spotify.com/playlist/abc") == "playlist"


def test_detect_kind_album():
    assert _detect_kind("https://open.spotify.com/album/abc") == "album"


def test_detect_kind_unknown():
    with pytest.raises(ValueError):
        _detect_kind("https://open.spotify.com/unknown/abc")


def test_track_to_meta_basic():
    raw = _mock_track_item("Bohemian Rhapsody", "Queen", 11, 12)["track"]
    meta = _track_to_meta(raw)
    assert meta.title == "Bohemian Rhapsody"
    assert meta.artist == "Queen"
    assert meta.track_number == "11/12"
    assert meta.output_filename == "Queen - Bohemian Rhapsody.mp3"


def test_track_to_meta_missing_fields():
    raw = {}
    meta = _track_to_meta(raw)
    assert meta.title == "Unknown Title"
    assert meta.artist == "Unknown Artist"
    assert meta.album == "Unknown Album"
    assert meta.album_art_url is None


def test_track_to_meta_none_artists():
    raw = {"name": "Song", "artists": None, "album": None}
    meta = _track_to_meta(raw)
    assert meta.artist == "Unknown Artist"


def test_playlist_pagination_exhausted():
    page1 = {"items": [_mock_track_item("T1")], "next": "page2_url"}
    page2 = {"items": [_mock_track_item("T2")], "next": None}

    sp = MagicMock()
    sp.playlist.return_value = {"name": "My Playlist"}
    sp.playlist_items.return_value = page1
    sp.next.return_value = page2

    client = SpotifyClient.__new__(SpotifyClient)
    client._sp = sp

    name, tracks = client._fetch_all_playlist_tracks("spotify:playlist:xxx")
    assert name == "My Playlist"
    assert len(tracks) == 2
    sp.next.assert_called_once()


def test_deleted_track_in_playlist_skipped():
    page = {
        "items": [
            None,
            _mock_track_item("Real Track"),
        ],
        "next": None,
    }
    sp = MagicMock()
    sp.playlist.return_value = {"name": "Playlist"}
    sp.playlist_items.return_value = page

    client = SpotifyClient.__new__(SpotifyClient)
    client._sp = sp

    _, tracks = client._fetch_all_playlist_tracks("spotify:playlist:xxx")
    assert len(tracks) == 1
    assert tracks[0].title == "Real Track"
