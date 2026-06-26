import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spotify_mp3.spotify import TrackMeta


def _make_meta(title="Song", artist="Artist"):
    return TrackMeta(
        title=title,
        artist=artist,
        album="Album",
        track_number="1/10",
        album_art_url=None,
        spotify_uri=f"spotify:track:{title}",
        output_filename=f"{artist} - {title}.mp3",
    )


def test_dry_run_prints_tracks(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    tracks = [_make_meta("Song A"), _make_meta("Song B")]

    with patch("spotify_mp3.cli.SpotifyClient") as MockClient:
        MockClient.return_value.get_tracks.return_value = ("My Playlist", tracks)
        with patch("sys.argv", ["spotify-mp3", "--dry-run", "spotify:playlist:abc"]):
            from spotify_mp3.cli import main
            main()

    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "Artist - Song A.mp3" in out
    assert "Artist - Song B.mp3" in out


def test_single_track_goes_to_root_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    meta = _make_meta("Solo Song")

    with patch("spotify_mp3.cli.SpotifyClient") as MockClient, \
         patch("spotify_mp3.cli.download_track") as mock_dl, \
         patch("spotify_mp3.cli.tag_file"), \
         patch("sys.argv", ["spotify-mp3", "spotify:track:abc"]):
        MockClient.return_value.get_tracks.return_value = ("Artist - Solo Song", [meta])
        mock_dl.return_value = tmp_path / "downloads" / meta.output_filename
        import spotify_mp3.cli as cli_module
        cli_module.main()

    call_args = mock_dl.call_args
    output_dir = call_args[0][1]
    assert output_dir == Path("downloads")


def test_failed_tracks_logged(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    meta = _make_meta("Missing Song")

    with patch("spotify_mp3.cli.SpotifyClient") as MockClient, \
         patch("spotify_mp3.cli.download_track") as mock_dl, \
         patch("spotify_mp3.cli.tag_file"):
        MockClient.return_value.get_tracks.return_value = ("My Playlist", [meta])
        mock_dl.return_value = None
        with patch("sys.argv", ["spotify-mp3", "spotify:playlist:abc"]):
            import spotify_mp3.cli as cli_module
            cli_module.main()

    failed_file = tmp_path / "downloads" / "My Playlist" / "failed.txt"
    assert failed_file.exists()
    content = failed_file.read_text()
    assert "Missing Song" in content


def test_invalid_url_exits(monkeypatch):
    with patch("spotify_mp3.cli.SpotifyClient") as MockClient:
        MockClient.return_value.get_tracks.side_effect = ValueError("bad url")
        with patch("sys.argv", ["spotify-mp3", "https://notspotify.com/foo"]):
            with pytest.raises(SystemExit) as exc:
                import spotify_mp3.cli as cli_module
                cli_module.main()
    assert exc.value.code == 1
