"""Finds and checks the app's icon, an image file in slack/.

The icon is optional. When there is one, the pipeline uploads it each time it
updates the app.
"""

import struct
from pathlib import Path

from slack_app import SlackAppError

# The icon is the one of these that exists.
ICON_FILES = ("slack/icon.png", "slack/icon.jpg")
# Slack asks for a square image between these sizes.
MIN_SIDE = 512
MAX_SIDE = 2000

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# JPEG markers that start a frame and carry the image's height and width.
JPEG_FRAME_MARKERS = set(range(0xC0, 0xD0)) - {0xC4, 0xC8, 0xCC}


def find(root="."):
    """Return the icon's path, or None when the project has no icon."""
    found = [Path(root) / name for name in ICON_FILES if (Path(root) / name).is_file()]
    if len(found) > 1:
        raise SlackAppError(
            "invalid_definition", [f"Keep only one of {' and '.join(ICON_FILES)}"]
        )
    return found[0] if found else None


def _jpeg_size(data):
    position = 2
    while position + 9 < len(data):
        if data[position] != 0xFF:
            return None
        marker = data[position + 1]
        if marker == 0xFF:  # padding before a marker
            position += 1
            continue
        if marker in JPEG_FRAME_MARKERS:
            height, width = struct.unpack(">HH", data[position + 5:position + 9])
            return width, height
        position += 2 + struct.unpack(">H", data[position + 2:position + 4])[0]
    return None


def inspect(data):
    """Return (content type, width, height) for PNG or JPEG data, or None for anything else."""
    if data.startswith(PNG_SIGNATURE) and data[12:16] == b"IHDR" and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return "image/png", width, height
    if data.startswith(b"\xff\xd8"):
        size = _jpeg_size(data)
        if size:
            return "image/jpeg", size[0], size[1]
    return None


def check(root="."):
    """Check the icon and return (path, content type, data), or None when there is no icon.

    Raises SlackAppError("invalid_definition") when the icon would not be accepted.
    """
    path = find(root)
    if path is None:
        return None
    name = path.relative_to(root).as_posix()
    data = path.read_bytes()
    details = inspect(data)
    if details is None:
        raise SlackAppError("invalid_definition", [f"{name}: is not a PNG or JPEG image"])

    content_type, width, height = details
    problems = []
    if path.suffix == ".png" and content_type != "image/png":
        problems.append(f"{name}: is named .png but is a JPEG image")
    if path.suffix == ".jpg" and content_type != "image/jpeg":
        problems.append(f"{name}: is named .jpg but is a PNG image")
    if width != height:
        problems.append(f"{name}: is {width} by {height} pixels; it must be square")
    if min(width, height) < MIN_SIDE or max(width, height) > MAX_SIDE:
        problems.append(
            f"{name}: is {width} by {height} pixels; each side must be between "
            f"{MIN_SIDE} and {MAX_SIDE}"
        )
    if problems:
        raise SlackAppError("invalid_definition", problems)
    return path, content_type, data
