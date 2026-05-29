import shutil
from pathlib import Path

import pytest

from spotify_mp3.spotify import TrackMeta


@pytest.fixture
def sample_meta():
    return TrackMeta(
        title="Bohemian Rhapsody",
        artist="Queen",
        album="A Night at the Opera",
        track_number="11/12",
        album_art_url=None,
        spotify_uri="spotify:track:7tFiyTwD0nx5a1eklYtX2J",
        output_filename="Queen - Bohemian Rhapsody.mp3",
    )


@pytest.fixture
def silence_mp3(tmp_path):
    src = Path(__file__).parent / "fixtures" / "silence.mp3"
    dst = tmp_path / "silence.mp3"
    shutil.copy(src, dst)
    return dst
