import pytest

from spotify_mp3.helpers import sanitize_filename


@pytest.mark.parametrize("inp,expected", [
    ('AC/DC - "Highway to Hell"', 'AC_DC - _Highway to Hell_'),
    ("CON", "_CON"),
    ("NUL", "_NUL"),
    ("normal name", "normal name"),
    ("trailing....", "trailing"),
    ("  leading spaces  ", "leading spaces"),
    ("a" * 300, "a" * 200),
    ("", "unknown"),
    ("....", "unknown"),
    ("hello:world", "hello_world"),
    ("file*name?here", "file_name_here"),
])
def test_sanitize_filename(inp, expected):
    assert sanitize_filename(inp) == expected


def test_unicode_preserved():
    result = sanitize_filename("Ångström")
    assert "ngstr" in result


def test_control_chars_stripped():
    result = sanitize_filename("hello\x00world\x1f!")
    assert "\x00" not in result
    assert "\x1f" not in result
