from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yt_dlp

from spotify_mp3.downloader import download_track


def test_skips_existing_file(tmp_path, sample_meta):
    existing = tmp_path / sample_meta.output_filename
    existing.touch()
    mock_ydl = MagicMock()
    result = download_track(sample_meta, tmp_path, ydl_class=mock_ydl)
    assert result == existing
    mock_ydl.assert_not_called()


def test_returns_none_on_download_error(tmp_path, sample_meta):
    class FailingYDL:
        def __init__(self, opts):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def extract_info(self, *a, **kw):
            raise yt_dlp.utils.DownloadError("Not found")

    result = download_track(sample_meta, tmp_path, ydl_class=FailingYDL)
    assert result is None


def test_returns_none_when_mp3_not_produced(tmp_path, sample_meta):
    class SilentYDL:
        def __init__(self, opts):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def extract_info(self, *a, **kw):
            return {"entries": [{}]}

    result = download_track(sample_meta, tmp_path, ydl_class=SilentYDL)
    assert result is None


def test_noplaylist_always_set(tmp_path, sample_meta):
    captured = {}

    class CapturingYDL:
        def __init__(self, opts):
            captured.update(opts)
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def extract_info(self, *a, **kw):
            return {"entries": [{}]}

    download_track(sample_meta, tmp_path, ydl_class=CapturingYDL)
    assert captured.get("noplaylist") is True


def test_ffmpeg_path_passed_to_opts(tmp_path, sample_meta):
    captured = {}

    class CapturingYDL:
        def __init__(self, opts):
            captured.update(opts)
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def extract_info(self, *a, **kw):
            return {"entries": [{}]}

    download_track(sample_meta, tmp_path, ffmpeg_path="/usr/bin/ffmpeg", ydl_class=CapturingYDL)
    assert captured.get("ffmpeg_location") == "/usr/bin/ffmpeg"


def test_output_dir_created(tmp_path, sample_meta):
    sub = tmp_path / "new_subdir"

    class SilentYDL:
        def __init__(self, opts):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def extract_info(self, *a, **kw):
            return {"entries": [{}]}

    download_track(sample_meta, sub, ydl_class=SilentYDL)
    assert sub.exists()
