# spotify-mp3

Download Spotify playlists, albums, and tracks as 192 kbps MP3 files via YouTube.

Tracks are matched on YouTube using the query `<artist> <title> official audio`,
downloaded with [yt-dlp](https://github.com/yt-dlp/yt-dlp), converted to MP3
by ffmpeg, and tagged with ID3 metadata (title, artist, album, track number,
album art) sourced from the Spotify API.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Usage](#usage)
5. [Output Structure](#output-structure)
6. [How It Works](#how-it-works)
7. [Troubleshooting](#troubleshooting)
8. [Running Tests](#running-tests)
9. [Project Layout](#project-layout)

---

## Prerequisites

### 1. Install ffmpeg

ffmpeg is required to convert downloaded audio to MP3. yt-dlp will fail at
the post-processing step without it.

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu / Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
Download a build from <https://ffmpeg.org/download.html>, extract it, and
either add the `bin/` folder to your PATH or use the `--ffmpeg-path` flag
when running the tool.

Verify the installation:
```bash
ffmpeg -version
```

### 2. Get Spotify API credentials

The tool reads track metadata from the [Spotify Web API](https://developer.spotify.com/documentation/web-api).
A free Spotify developer account is all you need — no Premium subscription required.

1. Go to <https://developer.spotify.com/dashboard> and log in.
2. Click **Create app**. Fill in any name and description; set the redirect URI
   to `http://localhost` (it won't be used).
3. Open the app settings and copy the **Client ID** and **Client Secret**.

### 3. Set environment variables

```bash
export SPOTIFY_CLIENT_ID=your_client_id_here
export SPOTIFY_CLIENT_SECRET=your_client_secret_here
```

Add these to your shell profile (`~/.zshrc`, `~/.bashrc`, etc.) to avoid
setting them every session.

Alternatively, copy `.env.example` to `.env`, fill in the values, and load
them with [direnv](https://direnv.net/) or by sourcing the file:
```bash
cp .env.example .env
# edit .env, then:
set -a && source .env && set +a
```

---

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

The second command registers the `spotify-mp3` console command so you can run
it from anywhere. Omit it if you prefer to run with `python -m spotify_mp3.cli`.

---

## Quick Start

```bash
# Download a playlist
spotify-mp3 "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"

# Download an album
spotify-mp3 "https://open.spotify.com/album/4LH4d3cOWNNsVw41Gqt2kv"

# Download a single track
spotify-mp3 "https://open.spotify.com/track/7tFiyTwD0nx5a1eklYtX2J"
```

---

## Usage

```
spotify-mp3 <url> [-o OUTPUT] [--ffmpeg-path PATH] [--dry-run]
```

### Positional argument

| Argument | Description |
|----------|-------------|
| `url` | Spotify track, playlist, or album — as a URL or a `spotify:` URI |

Both URL forms are accepted:
```
https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=abc
spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
```

The `?si=` tracking parameter in URLs is stripped automatically.

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-o, --output PATH` | `./downloads` | Root directory for saved MP3s |
| `--ffmpeg-path PATH` | *(uses PATH)* | Absolute path to ffmpeg binary |
| `--dry-run` | off | Print track list and output paths without downloading |

### Examples

```bash
# Save to a custom directory
spotify-mp3 "spotify:playlist:abc123" -o ~/Music

# Preview what would be downloaded without fetching anything
spotify-mp3 "https://open.spotify.com/album/xyz" --dry-run

# Specify ffmpeg location on Windows
spotify-mp3 "spotify:track:abc" --ffmpeg-path "C:\ffmpeg\bin\ffmpeg.exe"
```

---

## Output Structure

```
downloads/
├── My Playlist Name/
│   ├── Artist A - Track One.mp3
│   ├── Artist B - Track Two.mp3
│   └── failed.txt
├── Album Name/
│   ├── Artist - Song Title.mp3
│   └── ...
└── Artist - Single Track.mp3   ← single tracks go at the root level
```

### Resume behaviour

If a file already exists at the expected output path, that track is skipped
entirely. You can safely interrupt a long download and re-run the same command
to pick up where you left off.

### failed.txt

Any track that could not be matched on YouTube — or whose download failed after
three retries — is appended to `failed.txt` inside the output directory.

Format (tab-separated):
```
spotify:track:<id>    Artist Name    Track Title
```

The Spotify URI in the first column lets you look up the exact track and try
alternative search strategies manually.

---

## How It Works

```
┌──────────────┐   1. fetch metadata    ┌───────────────┐
│  Spotify API │ ─────────────────────► │  SpotifyClient│
└──────────────┘                        └───────┬───────┘
                                                │ TrackMeta list
                                                ▼
                                        ┌───────────────┐   2. ytsearch1:   ┌─────────┐
                                        │  download_    │ ────────────────► │ YouTube │
                                        │  track()      │ ◄──────────────── └─────────┘
                                        └───────┬───────┘   audio stream
                                                │ .mp3 (via ffmpeg)
                                                ▼
                                        ┌───────────────┐   3. write tags
                                        │  tag_file()   │ ──────────────── ID3 metadata
                                        └───────────────┘                  + album art
```

**Step 1 — Spotify metadata**
`SpotifyClient.get_tracks()` calls the Spotify Web API to resolve the URL to a
list of `TrackMeta` objects. Playlist and album responses are fully paginated
(Spotify returns at most 100 items per page). Deleted tracks in playlists
(where Spotify returns a `null` item) are silently skipped.

**Step 2 — YouTube download**
`download_track()` constructs the query `ytsearch1:<artist> <title> official audio`
and passes it to yt-dlp's Python API. yt-dlp picks the top result, downloads
the best available audio stream, and invokes ffmpeg as a post-processor to
produce a 192 kbps MP3. The `noplaylist` flag ensures yt-dlp never accidentally
downloads an entire YouTube playlist when a search result happens to be one.

**Step 3 — ID3 tagging**
`tag_file()` uses mutagen's `EasyID3` to write text tags (title, artist, album,
track number) and raw `ID3.APIC` to embed album art. MIME type is taken from
the `Content-Type` response header when fetching the image URL, with
magic-byte detection as a fallback.

**Retry strategy**
All Spotify API calls are individually wrapped with tenacity: 3 attempts,
exponential back-off 2–30 seconds. yt-dlp downloads are retried the same way
on `DownloadError` or `ExtractorError` (the latter covers removed and
geo-blocked videos).

---

## Troubleshooting

### `SpotifyOauthError: No client_id`
The `SPOTIFY_CLIENT_ID` environment variable is not set.
Run `echo $SPOTIFY_CLIENT_ID` to check. See [Prerequisites](#prerequisites).

### `FileNotFoundError: ffmpeg`
ffmpeg is not on your PATH. Install it (see [Prerequisites](#prerequisites))
or pass `--ffmpeg-path /absolute/path/to/ffmpeg`.

### Track appears in `failed.txt`
The track could not be matched on YouTube or the download failed three times.
Common causes:
- The track is very obscure and has no YouTube upload.
- The video was removed or is geo-blocked in your region.
- A temporary network error exhausted retries — re-running will retry it.

### Album art is missing
The Spotify CDN URL returned a 403 or the image server was unreachable. The
rest of the tags are still written; only the art is skipped.

### Download is slow
yt-dlp selects the best available audio format, which may be a high-bitrate
stream. This is expected; 192 kbps MP3 conversion is CPU-bound for ffmpeg.

### Playlist only downloaded 100 tracks
This would be a regression — the tool handles full pagination. Check that your
Spotify credentials are valid and that no error appears in the terminal output.

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

Tests use mocks for all external services (Spotify API, yt-dlp, requests) so
no credentials or network access are required.

---

## Project Layout

```
spotify-mp3/
├── README.md
├── requirements.txt        # runtime dependencies
├── pyproject.toml          # package metadata + console_scripts entry point
├── .env.example            # template for Spotify credentials
├── spotify_mp3/
│   ├── __init__.py         # package version
│   ├── cli.py              # argument parsing and main pipeline loop
│   ├── spotify.py          # Spotify API client + TrackMeta dataclass
│   ├── downloader.py       # yt-dlp wrapper
│   ├── tagger.py           # mutagen ID3 tag writer
│   └── helpers.py          # sanitize_filename utility
└── tests/
    ├── conftest.py          # shared fixtures (sample_meta, silence_mp3)
    ├── test_cli.py          # argument parsing + pipeline integration
    ├── test_spotify.py      # metadata parsing + pagination
    ├── test_downloader.py   # download logic (mocked yt-dlp)
    ├── test_tagger.py       # ID3 tag writing (real mutagen, test MP3)
    ├── test_helpers.py      # sanitize_filename edge cases
    └── fixtures/
        ├── sample_metadata.json
        └── silence.mp3      # minimal valid MP3 for tag tests
```
