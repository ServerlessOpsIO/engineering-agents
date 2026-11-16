"""Reads the app definition, checks it without contacting Slack, and builds the manifest.

The app definition is slack/manifest.yaml. The event delivery address is
`event_request_url` in slack/settings.json. The built manifest is the JSON that
is sent to Slack.
"""

import copy
import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

from slack_app import SlackAppError

MANIFEST_FILE = "slack/manifest.yaml"
SETTINGS_FILE = "slack/settings.json"
SCHEMA_FILE = "slack/manifest.schema.json"

MAX_NAME = 35
MAX_DESCRIPTION = 140
MAX_DISPLAY_NAME = 80
MAX_REQUEST_URL = 3500

# Sections this project does not allow (FR-004), as paths into the app definition.
FORBIDDEN_SECTIONS = (
    ("features", "slash_commands"),
    ("features", "shortcuts"),
    ("features", "workflow_steps"),
    ("features", "unfurl_domains"),
    ("settings", "interactivity"),
    ("oauth_config", "redirect_urls"),
    ("oauth_config", "scopes", "user"),
    ("functions",),
    ("workflows",),
)


def _get(mapping, *path):
    """Return the value at a path of keys, or None when any step is missing."""
    for key in path:
        if not isinstance(mapping, dict) or key not in mapping:
            return None
        mapping = mapping[key]
    return mapping


def _read(root):
    """Return (manifest, manifest text, settings) or raise for a file that cannot be read."""
    root = Path(root)
    problems = []
    manifest, text, settings = None, "", None

    try:
        text = (root / MANIFEST_FILE).read_text()
        manifest = yaml.safe_load(text)
        if not isinstance(manifest, dict):
            problems.append(f"{MANIFEST_FILE}: must be a mapping of fields")
    except FileNotFoundError:
        problems.append(f"{MANIFEST_FILE}: file not found")
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        where = f" at line {mark.line + 1}" if mark else ""
        problems.append(f"{MANIFEST_FILE}: is not valid YAML{where}")

    try:
        settings = json.loads((root / SETTINGS_FILE).read_text())
        if not isinstance(settings, dict):
            problems.append(f"{SETTINGS_FILE}: must be a JSON object")
    except FileNotFoundError:
        problems.append(f"{SETTINGS_FILE}: file not found")
    except json.JSONDecodeError as error:
        problems.append(f"{SETTINGS_FILE}: is not valid JSON at line {error.lineno}")

    if problems:
        raise SlackAppError("invalid_definition", problems)
    return manifest, text, settings


def _check_text(problems, manifest, path, limit, required=True):
    where = f"{MANIFEST_FILE}: {'.'.join(path)}"
    value = _get(manifest, *path)
    if value is None or value == "":
        if required:
            problems.append(f"{where}: is required")
    elif not isinstance(value, str):
        problems.append(f"{where}: must be text")
    elif len(value) > limit:
        problems.append(f"{where}: is {len(value)} characters; the limit is {limit}")


def _check_reasons(problems, text, values, what):
    """Every scope and event line must end with a comment giving its reason (FR-003)."""
    lines = text.splitlines()
    for value in values:
        if not isinstance(value, str):
            continue
        pattern = re.compile(r"^\s*-\s*[\"']?" + re.escape(value) + r"[\"']?\s*(#\s*(.*))?$")
        matches = [(number, match) for number, line in enumerate(lines, 1)
                   if (match := pattern.match(line))]
        if not matches:
            problems.append(
                f"{MANIFEST_FILE}: {what} {value}: must be on a line of its own, "
                "followed by a comment giving its reason"
            )
        for number, match in matches:
            if not (match.group(2) or "").strip():
                problems.append(
                    f"{MANIFEST_FILE}: line {number}: {what} {value} has no comment "
                    "giving its reason"
                )


def build(manifest, settings):
    """Return the manifest to send to Slack.

    Slack does not accept subscribed events without an address, so the events
    are sent only when the address is set.
    """
    built = copy.deepcopy(manifest)
    address = settings.get("event_request_url") or ""
    subscriptions = _get(built, "settings", "event_subscriptions")
    if address:
        if not isinstance(subscriptions, dict):
            subscriptions = {}
            built.setdefault("settings", {})["event_subscriptions"] = subscriptions
        subscriptions["request_url"] = address
    elif subscriptions is not None:
        del built["settings"]["event_subscriptions"]
    return built


def to_json(built):
    """Return the built manifest as text. The same input always gives the same text."""
    return json.dumps(built, sort_keys=True, indent=2) + "\n"


def bot_scopes(manifest):
    scopes = _get(manifest, "oauth_config", "scopes", "bot")
    return list(scopes) if isinstance(scopes, list) else []


def _check_schema(problems, built, root):
    schema = json.loads((Path(root) / SCHEMA_FILE).read_text())
    errors = sorted(Draft7Validator(schema).iter_errors(built), key=lambda e: list(e.path))
    for error in errors:
        pointer = "/" + "/".join(str(part) for part in error.path)
        problems.append(f"Slack's manifest schema: {pointer}: {error.message}")


def check(root="."):
    """Check the app definition without contacting Slack and return the built manifest.

    Raises SlackAppError("invalid_definition") listing every problem found.
    """
    manifest, text, settings = _read(root)
    problems = []

    _check_text(problems, manifest, ("display_information", "name"), MAX_NAME)
    _check_text(problems, manifest, ("display_information", "description"), MAX_DESCRIPTION)
    _check_text(problems, manifest, ("features", "bot_user", "display_name"), MAX_DISPLAY_NAME)

    for path in FORBIDDEN_SECTIONS:
        if _get(manifest, *path) is not None:
            problems.append(f"{MANIFEST_FILE}: {'.'.join(path)}: is not allowed in this project")
    if _get(manifest, "features", "app_home", "home_tab_enabled") is True:
        problems.append(
            f"{MANIFEST_FILE}: features.app_home.home_tab_enabled: the home tab is not "
            "allowed in this project"
        )
    if _get(manifest, "settings", "socket_mode_enabled") is True:
        problems.append(
            f"{MANIFEST_FILE}: settings.socket_mode_enabled: must not be true; events are "
            "delivered over HTTPS"
        )
    if _get(manifest, "settings", "event_subscriptions", "request_url") is not None:
        problems.append(
            f"{MANIFEST_FILE}: settings.event_subscriptions.request_url: must not be set "
            f"here; set event_request_url in {SETTINGS_FILE}"
        )

    events = _get(manifest, "settings", "event_subscriptions", "bot_events")
    _check_reasons(problems, text, bot_scopes(manifest), "scope")
    _check_reasons(problems, text, events if isinstance(events, list) else [], "event")

    address = settings.get("event_request_url")
    where = f"{SETTINGS_FILE}: event_request_url"
    if not isinstance(address, str):
        problems.append(f"{where}: is required and must be text; leave it empty for no address")
    elif address:
        if not address.startswith("https://"):
            problems.append(f"{where}: must start with https://")
        if len(address) > MAX_REQUEST_URL:
            problems.append(
                f"{where}: is {len(address)} characters; the limit is {MAX_REQUEST_URL}"
            )

    built = build(manifest, settings if isinstance(address, str) else {})
    _check_schema(problems, built, root)

    if problems:
        raise SlackAppError("invalid_definition", problems)
    return built
