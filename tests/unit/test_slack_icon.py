"""Tests for finding and checking the app's icon."""

import struct
import zlib
from pathlib import Path

import pytest

from slack_app import SlackAppError, icon

REPO_ROOT = Path(__file__).resolve().parents[2]


def png(width, height):
    """A PNG file header for an image of the given size. Enough for the check."""
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    chunk = b"IHDR" + header
    return (
        icon.PNG_SIGNATURE + struct.pack(">I", len(header)) + chunk
        + struct.pack(">I", zlib.crc32(chunk))
    )


def jpeg(width, height):
    """A JPEG start, an application segment, and a frame header of the given size."""
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 9
    frame = b"\xff\xc0" + struct.pack(">HBHHB", 17, 8, height, width, 3) + b"\x00" * 9
    return b"\xff\xd8" + app0 + frame + b"\xff\xd9"


@pytest.fixture
def root(tmp_path):
    (tmp_path / "slack").mkdir()
    return tmp_path


def problems(root):
    with pytest.raises(SlackAppError) as raised:
        icon.check(root)
    assert raised.value.kind == "invalid_definition"
    return "\n".join(raised.value.details)


def test_the_committed_icon_passes():
    path, content_type, data = icon.check(REPO_ROOT)
    assert path.name == "icon.jpg"
    assert content_type == "image/jpeg"
    assert icon.inspect(data) == ("image/jpeg", 554, 554)


def test_a_project_with_no_icon_is_fine(root):
    assert icon.check(root) is None


@pytest.mark.parametrize("name, data, content_type", [
    ("icon.png", png(512, 512), "image/png"),
    ("icon.png", png(2000, 2000), "image/png"),
    ("icon.jpg", jpeg(1024, 1024), "image/jpeg"),
])
def test_a_square_image_of_an_accepted_size_passes(root, name, data, content_type):
    (root / "slack" / name).write_bytes(data)
    path, found_type, found = icon.check(root)
    assert (path.name, found_type, found) == (name, content_type, data)


def test_an_image_that_is_not_square_is_reported(root):
    (root / "slack" / "icon.png").write_bytes(png(800, 600))
    assert "slack/icon.png: is 800 by 600 pixels; it must be square" in problems(root)


@pytest.mark.parametrize("side", [511, 2001])
def test_an_image_outside_the_accepted_sizes_is_reported(root, side):
    (root / "slack" / "icon.jpg").write_bytes(jpeg(side, side))
    assert "each side must be between 512 and 2000" in problems(root)


def test_a_file_that_is_not_an_image_is_reported(root):
    (root / "slack" / "icon.png").write_bytes(b"<svg></svg>")
    assert "slack/icon.png: is not a PNG or JPEG image" in problems(root)


def test_a_file_named_for_the_wrong_format_is_reported(root):
    (root / "slack" / "icon.png").write_bytes(jpeg(512, 512))
    assert "is named .png but is a JPEG image" in problems(root)


def test_two_icons_are_reported(root):
    (root / "slack" / "icon.png").write_bytes(png(512, 512))
    (root / "slack" / "icon.jpg").write_bytes(jpeg(512, 512))
    assert "Keep only one of slack/icon.png and slack/icon.jpg" in problems(root)
