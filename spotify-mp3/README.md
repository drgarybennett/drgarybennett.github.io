# spotify-mp3

Download Spotify playlists, albums, and tracks as 192kbps MP3 files via YouTube.

## Prerequisites

### 1. Install ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add to your PATH,
or use the `--ffmpeg-path` flag when running the tool.

### 2. Get Spotify API credentials

1. Go to https://developer.spotify.com/dashboard and create an app
2. Copy your **Client ID** and **Client Secret**

### 3. Set environment variables

```bash
export SPOTIFY_CLIENT_ID=your_client_id_here
export SPOTIFY_CLIENT_SECRET=your_client_secret_here
```

Or copy `.env.example` to `.env` and fill in the values, then use a tool like
`direnv` or `python-dotenv` to load them.

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## Usage

**Download a playlist:**
```bash
spotify-mp3 "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
```

**Download an album:**
```bash
spotify-mp3 "https://open.spotify.com/album/4LH4d3cOWNNsVw41Gqt2kv"
```

**Download a single track:**
```bash
spotify-mp3 "https://open.spotify.com/track/7tFiyTwD0nx5a1eklYtX2J"
```

**Spotify URIs also work:**
```bash
spotify-mp3 "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"
```

### Options

| Flag | Description |
|------|-------------|
| `-o, --output PATH` | Root output directory (default: `./downloads`) |
| `--ffmpeg-path PATH` | Path to ffmpeg binary if not on PATH |
| `--dry-run` | Print track list without downloading |

## Output structure

```
downloads/
├── Playlist Name/
│   ├── Artist - Track Title.mp3
│   ├── Artist - Track Title.mp3
│   └── failed.txt          # tracks that couldn't be matched on YouTube
└── Artist - Single Track.mp3
```

## Features

- Resume-friendly: skips tracks already downloaded
- Embeds ID3 tags: title, artist, album, track number, album art
- Logs unmatched tracks to `failed.txt` with Spotify URI for reference
- Handles playlists longer than 100 tracks (full pagination)
- Retries on rate limits with exponential backoff

## Running tests

```bash
pip install pytest
pytest tests/ -v
```
