"""Tests for the offline check of the Slack app definition and the build."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from slack_app import SlackAppError, definition

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def root(tmp_path):
    """A copy of the committed slack/ directory that a test can change."""
    shutil.copytree(REPO_ROOT / "slack", tmp_path / "slack")
    return tmp_path


def manifest_path(root):
    return root / "slack" / "manifest.yaml"


def change_manifest(root, change):
    """Load the definition, apply change(dict), and write it back keeping comments off."""
    path = manifest_path(root)
    text = path.read_text()
    data = yaml.safe_load(text)
    change(data)
    # Writing YAML back drops the comments, so re-add a reason to each list item.
    dumped = yaml.safe_dump(data, sort_keys=False)
    lines = [f"{line}  # reason" if line.lstrip().startswith("- ") else line
             for line in dumped.splitlines()]
    path.write_text("\n".join(lines) + "\n")


def set_address(root, address):
    (root / "slack" / "settings.json").write_text(json.dumps({"event_request_url": address}))


def problems(root):
    with pytest.raises(SlackAppError) as raised:
        definition.check(root)
    assert raised.value.kind == "invalid_definition"
    return "\n".join(raised.value.details)


def test_the_committed_definition_passes():
    built = definition.check(REPO_ROOT)
    assert built["display_information"]["name"] == "STRIDEr"


def test_the_committed_definition_asks_for_the_planned_scopes_and_events():
    manifest = yaml.safe_load((REPO_ROOT / "slack" / "manifest.yaml").read_text())
    assert manifest["oauth_config"]["scopes"]["bot"] == [
        "app_mentions:read", "chat:write", "im:history", "channels:history", "groups:history",
        "reactions:write", "users:read", "files:write",
    ]
    assert manifest["settings"]["event_subscriptions"]["bot_events"] == [
        "app_mention", "message.im", "message.channels", "message.groups",
    ]


def test_the_committed_definition_sends_the_events_to_the_committed_address():
    subscriptions = definition.check(REPO_ROOT)["settings"]["event_subscriptions"]
    assert subscriptions["request_url"] == (
        "https://engineering-agents.sandbox.serverlessops.io/slack/events"
    )
    assert subscriptions["bot_events"] == [
        "app_mention", "message.im", "message.channels", "message.groups",
    ]


def test_events_are_left_out_while_there_is_no_address(root):
    set_address(root, "")
    built = definition.check(root)
    assert "event_subscriptions" not in built["settings"]
    assert built["oauth_config"]["scopes"]["bot"]


def test_events_and_the_address_are_sent_once_an_address_is_set(root):
    set_address(root, "https://example.com/slack/events")
    subscriptions = definition.check(root)["settings"]["event_subscriptions"]
    assert subscriptions["request_url"] == "https://example.com/slack/events"
    assert subscriptions["bot_events"] == [
        "app_mention", "message.im", "message.channels", "message.groups",
    ]


def test_the_same_inputs_give_identical_text(root):
    first = definition.to_json(definition.check(root))
    second = definition.to_json(definition.check(root))
    assert first == second
    assert first == json.dumps(json.loads(first), sort_keys=True, indent=2) + "\n"


def test_a_missing_name_is_reported(root):
    change_manifest(root, lambda d: d["display_information"].pop("name"))
    assert "display_information.name: is required" in problems(root)


def test_a_missing_description_is_reported(root):
    change_manifest(root, lambda d: d["display_information"].pop("description"))
    assert "display_information.description: is required" in problems(root)


@pytest.mark.parametrize("path, limit", [
    (("display_information", "name"), 35),
    (("display_information", "description"), 140),
    (("features", "bot_user", "display_name"), 80),
])
def test_a_field_over_its_length_limit_is_reported(root, path, limit):
    def change(data):
        for key in path[:-1]:
            data = data[key]
        data[path[-1]] = "x" * (limit + 1)

    change_manifest(root, change)
    assert f"{'.'.join(path)}: is {limit + 1} characters; the limit is {limit}" in problems(root)


def test_a_scope_without_a_reason_is_reported_with_its_line(root):
    path = manifest_path(root)
    text = path.read_text()
    line = next(line for line in text.splitlines() if "- chat:write" in line)
    path.write_text(text.replace(line, "      - chat:write"))
    found = problems(root)
    assert "scope chat:write has no comment giving its reason" in found
    assert "line " in found


def test_an_event_without_a_reason_is_reported(root):
    path = manifest_path(root)
    text = path.read_text()
    line = next(line for line in text.splitlines() if "- message.im" in line)
    path.write_text(text.replace(line, "      - message.im  #"))
    assert "event message.im has no comment giving its reason" in problems(root)


def test_scopes_written_on_one_line_are_reported(root):
    path = manifest_path(root)
    data = yaml.safe_load(path.read_text())
    data["oauth_config"]["scopes"]["bot"] = ["chat:write"]
    path.write_text(yaml.safe_dump(data, default_flow_style=True))
    assert "scope chat:write: must be on a line of its own" in problems(root)


@pytest.mark.parametrize("path, value", [
    (("features", "slash_commands"), [{"command": "/stride", "description": "x"}]),
    (("features", "shortcuts"), []),
    (("features", "workflow_steps"), []),
    (("features", "unfurl_domains"), ["example.com"]),
    (("settings", "interactivity"), {"is_enabled": True}),
    (("oauth_config", "redirect_urls"), ["https://example.com"]),
    (("oauth_config", "scopes", "user"), ["chat:write"]),
    (("functions",), {}),
    (("workflows",), {}),
])
def test_a_forbidden_section_is_reported(root, path, value):
    def change(data):
        for key in path[:-1]:
            data = data.setdefault(key, {})
        data[path[-1]] = value

    change_manifest(root, change)
    assert f"{'.'.join(path)}: is not allowed in this project" in problems(root)


def test_the_home_tab_is_not_allowed(root):
    change_manifest(root, lambda d: d["features"]["app_home"].update(home_tab_enabled=True))
    assert "the home tab is not allowed" in problems(root)


def test_socket_mode_is_not_allowed(root):
    change_manifest(root, lambda d: d["settings"].update(socket_mode_enabled=True))
    assert "settings.socket_mode_enabled: must not be true" in problems(root)


def test_the_address_must_not_be_in_the_definition(root):
    change_manifest(
        root,
        lambda d: d["settings"]["event_subscriptions"].update(request_url="https://example.com"),
    )
    assert "settings.event_subscriptions.request_url: must not be set here" in problems(root)


def test_an_address_that_is_not_https_is_reported(root):
    set_address(root, "http://example.com/slack/events")
    assert "event_request_url: must start with https://" in problems(root)


def test_an_address_over_the_length_limit_is_reported(root):
    set_address(root, "https://example.com/" + "x" * 3500)
    assert "the limit is 3500" in problems(root)


def test_a_missing_address_setting_is_reported(root):
    (root / "slack" / "settings.json").write_text("{}")
    assert "event_request_url: is required" in problems(root)


def test_an_unknown_field_is_reported_by_slacks_schema_with_its_place(root):
    change_manifest(root, lambda d: d.update(colour="blue"))
    found = problems(root)
    assert "Slack's manifest schema: /:" in found
    assert "colour" in found


def test_a_wrongly_typed_field_is_reported_by_slacks_schema_with_its_place(root):
    change_manifest(root, lambda d: d["features"]["bot_user"].update(always_online="yes"))
    assert "Slack's manifest schema: /features/bot_user/always_online:" in problems(root)


def test_a_file_that_is_not_yaml_is_reported(root):
    manifest_path(root).write_text("display_information: [unclosed")
    assert "manifest.yaml: is not valid YAML" in problems(root)


def test_a_settings_file_that_is_not_json_is_reported(root):
    (root / "slack" / "settings.json").write_text("{not json")
    assert "settings.json: is not valid JSON" in problems(root)


def test_every_problem_is_reported_at_once(root):
    change_manifest(root, lambda d: d["settings"].update(socket_mode_enabled=True))
    set_address(root, "http://example.com")
    found = problems(root)
    assert "socket_mode_enabled" in found
    assert "must start with https://" in found
