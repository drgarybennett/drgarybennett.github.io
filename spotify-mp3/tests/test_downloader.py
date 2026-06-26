from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yt_dlp

from spotify_mp3.downloader import download_track


def _make_ydl(search_entries=None, download_raises=None):
    """
    Build a fake YDL class.
    - search_entries: list of dicts returned by extract_flat search
    - download_raises: exception to raise during the download phase (or None)
    """
    entries = search_entries if search_entries is not None else [{"id": "abc123"}]

    class FakeYDL:
        _opts_seen = []

        def __init__(self, opts):
            FakeYDL._opts_seen.append(dict(opts))
            self._opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def extract_info(self, query, download=True):
            if not download:
                return {"entries": entries}
            if download_raises:
                raise download_raises
            return {}

    return FakeYDL


def test_skips_existing_file(tmp_path, sample_meta):
    existing = tmp_path / sample_meta.output_filename
    existing.touch()
    mock_cls = MagicMock()
    result = download_track(sample_meta, tmp_path, ydl_class=mock_cls)
    assert result == existing
    mock_cls.assert_not_called()


def test_returns_none_when_all_candidates_fail(tmp_path, sample_meta):
    YDL = _make_ydl(download_raises=yt_dlp.utils.DownloadError("blocked"))
    result = download_track(sample_meta, tmp_path, ydl_class=YDL)
    assert result is None


def test_returns_none_when_no_candidates(tmp_path, sample_meta):
    YDL = _make_ydl(search_entries=[])
    result = download_track(sample_meta, tmp_path, ydl_class=YDL)
    assert result is None


def test_returns_none_when_mp3_not_produced(tmp_path, sample_meta):
    YDL = _make_ydl()
    result = download_track(sample_meta, tmp_path, ydl_class=YDL)
    assert result is None


def test_falls_through_to_second_candidate(tmp_path, sample_meta):
    """First candidate blocked; second succeeds and produces the MP3."""
    call_count = 0

    class FallbackYDL:
        def __init__(self, opts):
            self._opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def extract_info(self, url, download=True):
            nonlocal call_count
            if not download:
                return {"entries": [{"id": "blocked1"}, {"id": "good2"}]}
            call_count += 1
            if "blocked1" in url:
                raise yt_dlp.utils.DownloadError("403 Forbidden")
            # Simulate successful download by writing the output file
            outtmpl = self._opts["outtmpl"]
            mp3_path = Path(outtmpl.replace(".%(ext)s", ".mp3"))
            mp3_path.parent.mkdir(parents=True, exist_ok=True)
            mp3_path.write_bytes(b"fake")
            return {}

    result = download_track(sample_meta, tmp_path, ydl_class=FallbackYDL)
    assert result is not None
    # _run_download retries up to 3x on DownloadError (tenacity), so blocked1
    # is attempted 3 times before good2 succeeds on its first try → 4 total.
    assert call_count == 4


def test_noplaylist_set_in_download_opts(tmp_path, sample_meta):
    captured_download_opts = {}

    class CapturingYDL:
        def __init__(self, opts):
            self._opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def extract_info(self, url, download=True):
            if not download:
                return {"entries": [{"id": "abc"}]}
            captured_download_opts.update(self._opts)
            return {}

    download_track(sample_meta, tmp_path, ydl_class=CapturingYDL)
    assert captured_download_opts.get("noplaylist") is True


def test_ffmpeg_path_passed_to_download_opts(tmp_path, sample_meta):
    captured = {}

    class CapturingYDL:
        def __init__(self, opts):
            self._opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def extract_info(self, url, download=True):
            if not download:
                return {"entries": [{"id": "abc"}]}
            captured.update(self._opts)
            return {}

    download_track(sample_meta, tmp_path, ffmpeg_path="/usr/bin/ffmpeg", ydl_class=CapturingYDL)
    assert captured.get("ffmpeg_location") == "/usr/bin/ffmpeg"


def test_output_dir_created(tmp_path, sample_meta):
    sub = tmp_path / "new_subdir"
    YDL = _make_ydl()
    download_track(sample_meta, sub, ydl_class=YDL)
    assert sub.exists()
