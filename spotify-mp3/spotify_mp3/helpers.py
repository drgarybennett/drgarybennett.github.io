"""
Filesystem utilities shared across the package.

Only sanitize_filename is public. Everything else is an implementation detail.
"""

import re
import unicodedata

_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def sanitize_filename(name: str) -> str:
    """
    Return a filesystem-safe filename stem (no extension).

    Rules applied in order:
    - Unicode NFKD normalisation (decomposes ligatures, fullwidth chars, etc.)
    - Characters illegal on Windows or POSIX (\\/:*?"<>|) replaced with _
    - ASCII control characters (0x00–0x1F, 0x7F) stripped
    - Leading/trailing dots and spaces removed (Windows rejects them)
    - Empty result replaced with "unknown"
    - Windows reserved device names (CON, NUL, COM1 …) prefixed with _
    - Result truncated to 200 characters to stay within PATH_MAX on most OSes
    """
    name = unicodedata.normalize("NFKD", name)
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    name = name.strip(". ")
    if not name:
        name = "unknown"
    stem = name.split(".")[0].upper()
    if stem in _WINDOWS_RESERVED:
        name = "_" + name
    return name[:200]
