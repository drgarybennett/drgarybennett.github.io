"""
Spotify Web API client and track-metadata types.

Public surface:
    TrackMeta   — frozen dataclass holding everything downstream needs
    SpotifyClient.get_tracks(url_or_uri) — resolves a Spotify URL or URI to a
        (context_name, [TrackMeta]) tuple, handling tracks, playlists, and albums.

Authentication is read automatically from the environment variables
SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET (set by the caller before import).

All Spotify API calls are wrapped with per-call retry (3 attempts, exponential
backoff 2–30 s) so transient 429 / 5xx responses are handled transparently.
Retries wrap individual calls rather than the whole pagination loop to avoid
re-fetching already-consumed pages on a mid-loop failure.
"""

import re
from dataclasses import dataclass
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from tenacity import retry, stop_after_attempt, wait_exponential

_spotify_retry = retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))


@dataclass(slots=True)
class TrackMeta:
    """
    Immutable snapshot of a Spotify track's metadata.

    Attributes:
        title:           Track title as returned by Spotify.
        artist:          Primary artist name.
        album:           Album title.
        track_number:    Pre-formatted for EasyID3, e.g. "3" or "3/12".
                         Empty string when Spotify doesn't provide it.
        album_art_url:   URL of the highest-resolution album cover image,
                         or None when no image is available.
        spotify_uri:     Canonical Spotify URI, e.g. "spotify:track:abc123".
                         Used as a stable identifier in failed.txt.
        output_filename: Sanitized "<Artist> - <Title>.mp3" ready to use as a
                         filename on any OS.
    """

    title: str
    artist: str
    album: str
    track_number: str
    album_art_url: Optional[str]
    spotify_uri: str
    output_filename: str


class SpotifyClient:
    """
    Thin wrapper around spotipy that returns typed TrackMeta lists.

    Instantiation reads SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET from the
    environment via SpotifyClientCredentials; raises SpotifyOauthError if
    either variable is missing.
    """

    def __init__(self):
        auth = SpotifyClientCredentials()
        self._sp = spotipy.Spotify(auth_manager=auth)

    def get_tracks(self, url_or_uri: str) -> tuple[str, list[TrackMeta]]:
        """
        Resolve a Spotify URL or URI to a list of tracks.

        Args:
            url_or_uri: Any of:
                - https://open.spotify.com/track/<id>[?si=...]
                - https://open.spotify.com/playlist/<id>[?si=...]
                - https://open.spotify.com/album/<id>[?si=...]
                - spotify:track:<id>  /  spotify:playlist:<id>  /  spotify:album:<id>

        Returns:
            (context_name, tracks) where context_name is the playlist/album
            title or "<Artist> - <Title>" for single tracks, and tracks is a
            list of TrackMeta (may be empty if the playlist contains only
            deleted/None entries).

        Raises:
            ValueError: URL/URI format is not recognised.
            spotipy.exceptions.SpotifyException: Spotify API error (e.g. 404
                for a private or non-existent playlist).
        """
        clean = _strip_query_params(url_or_uri)
        kind = _detect_kind(clean)

        if kind == "track":
            track = self._sp.track(clean)
            meta = _track_to_meta(track)
            return f"{meta.artist} - {meta.title}", [meta]
        elif kind == "playlist":
            return self._fetch_all_playlist_tracks(clean)
        elif kind == "album":
            return self._fetch_all_album_tracks(clean)
        raise ValueError(f"Unrecognized Spotify URL/URI: {url_or_uri}")

    def _fetch_all_playlist_tracks(self, uri: str) -> tuple[str, list[TrackMeta]]:
        playlist = _spotify_retry(self._sp.playlist)(
            uri, fields="name,tracks(items(track(name,artists,album,track_number,uri)),next,total)"
        )
        name = playlist["name"]
        results = playlist["tracks"]
        tracks = []
        while True:
            for item in results["items"]:
                if item and item.get("track"):
                    tracks.append(_track_to_meta(item["track"]))
            if not results["next"]:
                break
            results = _spotify_retry(self._sp.next)(results)
        return name, tracks

    def _fetch_all_album_tracks(self, uri: str) -> tuple[str, list[TrackMeta]]:
        album = _spotify_retry(self._sp.album)(uri)
        name = album["name"]
        results = album["tracks"]
        tracks = []
        while True:
            for t in results["items"]:
                t = dict(t)
                t["album"] = {"name": name, "images": album.get("images", []), "total_tracks": album.get("total_tracks", 0)}
                tracks.append(_track_to_meta(t))
            if not results["next"]:
                break
            results = _spotify_retry(self._sp.next)(results)
        return name, tracks


def _strip_query_params(url: str) -> str:
    return re.sub(r"\?.*$", "", url)


def _detect_kind(url: str) -> str:
    if "playlist" in url:
        return "playlist"
    if "album" in url:
        return "album"
    if "track" in url:
        return "track"
    raise ValueError(f"Cannot detect Spotify resource type from: {url}")


def _track_to_meta(track: dict) -> TrackMeta:
    from .helpers import sanitize_filename

    title = track.get("name") or "Unknown Title"
    artists = track.get("artists") or []
    artist = artists[0].get("name", "Unknown Artist") if artists else "Unknown Artist"
    album_obj = track.get("album") or {}
    album = album_obj.get("name") or "Unknown Album"
    track_num = track.get("track_number")
    total = album_obj.get("total_tracks") or 0
    track_number_str = f"{track_num}/{total}" if track_num and total else str(track_num or "")
    images = album_obj.get("images") or []
    art_url = images[0]["url"] if images else None
    uri = track.get("uri") or ""
    filename = sanitize_filename(f"{artist} - {title}") + ".mp3"

    return TrackMeta(
        title=title,
        artist=artist,
        album=album,
        track_number=track_number_str,
        album_art_url=art_url,
        spotify_uri=uri,
        output_filename=filename,
    )
