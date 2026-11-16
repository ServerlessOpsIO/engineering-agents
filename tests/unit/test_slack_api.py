"""Tests for the Slack client. Slack is replaced by a fake transport."""

import json
import urllib.parse

import pytest

from slack_app import SlackAppError
from slack_app.slack_api import SlackApi

CONFIG_TOKEN = "xoxp-service-token-value"
BOT_TOKEN = "xoxb-bot-token-value"
MANIFEST = '{"display_information": {"name": "STRIDEr"}}'


class FakeSlack:
    """Answers each call with the next prepared answer and records what was sent."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, url, headers, body):
        self.calls.append({
            "method": url.rsplit("/", 1)[1],
            "authorization": headers.get("Authorization"),
            "params": dict(urllib.parse.parse_qsl(body.decode())),
        })
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        status, headers, payload = answer
        return status, headers, json.dumps(payload).encode()


def ok(payload=None, headers=None):
    return 200, headers or {}, {"ok": True, **(payload or {})}


def error(code, **extra):
    return 200, {}, {"ok": False, "error": code, **extra}


def test_validate_sends_the_manifest_and_the_app_id_when_there_is_one():
    slack = FakeSlack(ok(), ok())
    api = SlackApi(slack)
    api.validate(CONFIG_TOKEN, MANIFEST, "A123")
    api.validate(CONFIG_TOKEN, MANIFEST)
    assert slack.calls[0]["method"] == "apps.manifest.validate"
    assert slack.calls[0]["authorization"] == f"Bearer {CONFIG_TOKEN}"
    assert slack.calls[0]["params"] == {"manifest": MANIFEST, "app_id": "A123"}
    assert slack.calls[1]["params"] == {"manifest": MANIFEST}


def test_export_returns_the_apps_manifest():
    slack = FakeSlack(ok({"manifest": {"display_information": {"name": "STRIDEr"}}}))
    assert SlackApi(slack).export(CONFIG_TOKEN, "A123") == {
        "display_information": {"name": "STRIDEr"}
    }
    assert slack.calls[0]["method"] == "apps.manifest.export"
    assert slack.calls[0]["params"] == {"app_id": "A123"}


def test_update_sends_the_app_id_and_the_manifest():
    slack = FakeSlack(ok({"app_id": "A123", "permissions_updated": True}))
    assert SlackApi(slack).update(CONFIG_TOKEN, "A123", MANIFEST)["permissions_updated"] is True
    assert slack.calls[0]["method"] == "apps.manifest.update"
    assert slack.calls[0]["params"] == {"app_id": "A123", "manifest": MANIFEST}


def test_create_sends_the_manifest_and_returns_slacks_answer():
    slack = FakeSlack(ok({"app_id": "A999", "credentials": {"signing_secret": "s"}}))
    answer = SlackApi(slack).create(CONFIG_TOKEN, MANIFEST)
    assert answer["app_id"] == "A999"
    assert slack.calls[0]["method"] == "apps.manifest.create"
    assert slack.calls[0]["params"] == {"manifest": MANIFEST}


def test_set_icon_uploads_the_file_and_the_app_id_as_a_form():
    sent = {}

    def transport(url, headers, body):
        sent.update(url=url, headers=headers, body=body)
        return 200, {}, b'{"ok": true}'

    SlackApi(transport).set_icon(CONFIG_TOKEN, "A123", "icon.jpg", "image/jpeg", b"\xff\xd8DATA")
    assert sent["url"].endswith("/apps.icon.set")
    assert sent["headers"]["Authorization"] == f"Bearer {CONFIG_TOKEN}"
    content_type = sent["headers"]["Content-Type"]
    assert content_type.startswith("multipart/form-data; boundary=")
    boundary = content_type.split("boundary=")[1].encode()
    parts = sent["body"].split(b"--" + boundary)
    assert parts[-1] == b"--\r\n"
    assert (
        b'Content-Disposition: form-data; name="file"; filename="icon.jpg"\r\n'
        b"Content-Type: image/jpeg\r\n\r\n\xff\xd8DATA\r\n"
    ) in parts[1]
    assert b'Content-Disposition: form-data; name="app_id"\r\n\r\nA123\r\n' in parts[2]


def test_set_icon_reports_a_refused_credential():
    assert failure(
        error("invalid_auth"),
        lambda api: api.set_icon(CONFIG_TOKEN, "A1", "icon.png", "image/png", b"x"),
    ).kind == "credential_rejected"


def test_auth_test_returns_the_scopes_the_token_holds():
    slack = FakeSlack(ok(headers={"x-oauth-scopes": "chat:write, im:history,app_mentions:read"}))
    assert SlackApi(slack).auth_test_scopes(BOT_TOKEN) == {
        "chat:write", "im:history", "app_mentions:read",
    }
    assert slack.calls[0]["method"] == "auth.test"
    assert slack.calls[0]["authorization"] == f"Bearer {BOT_TOKEN}"


def test_auth_test_without_the_scopes_header_is_unexpected():
    with pytest.raises(SlackAppError) as raised:
        SlackApi(FakeSlack(ok())).auth_test_scopes(BOT_TOKEN)
    assert raised.value.kind == "unexpected"


def failure(answer, call):
    with pytest.raises(SlackAppError) as raised:
        call(SlackApi(FakeSlack(answer)))
    return raised.value


def test_an_invalid_manifest_lists_each_problem_with_its_place():
    found = failure(
        error("invalid_manifest", errors=[
            {"message": "Unknown scope", "pointer": "/oauth_config/scopes/bot/2"},
            {"message": "Too long", "pointer": "/display_information/name"},
        ]),
        lambda api: api.validate(CONFIG_TOKEN, MANIFEST),
    )
    assert found.kind == "invalid_definition"
    assert found.details == [
        "Slack: /oauth_config/scopes/bot/2: Unknown scope",
        "Slack: /display_information/name: Too long",
    ]


@pytest.mark.parametrize(
    "code", ["token_expired", "token_revoked", "invalid_auth", "not_allowed_token_type"]
)
def test_a_refused_pipeline_credential(code):
    assert failure(error(code), lambda api: api.export(CONFIG_TOKEN, "A1")).kind == "credential_rejected"
    assert failure(
        error(code), lambda api: api.update(CONFIG_TOKEN, "A123", MANIFEST)
    ).kind == "credential_rejected"


@pytest.mark.parametrize("code", ["invalid_auth", "token_revoked", "account_inactive"])
def test_a_refused_bot_token(code):
    assert failure(
        error(code), lambda api: api.auth_test_scopes(BOT_TOKEN)
    ).kind == "bot_token_rejected"


def test_an_app_slack_does_not_know_is_gone():
    assert failure(error("app_not_found"), lambda api: api.export(CONFIG_TOKEN, "A1")).kind == "app_gone"


@pytest.mark.parametrize("code", [
    "ratelimited", "service_unavailable", "internal_error", "fatal_error", "request_timeout",
])
def test_slack_error_codes_that_mean_try_again_later(code):
    assert failure(
        error(code), lambda api: api.export(CONFIG_TOKEN, "A1")
    ).kind == "slack_unavailable"


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_http_statuses_that_mean_try_again_later(status):
    assert failure(
        (status, {}, {}), lambda api: api.export(CONFIG_TOKEN, "A1")
    ).kind == "slack_unavailable"


def test_a_connection_failure_means_try_again_later():
    assert failure(
        SlackAppError("slack_unavailable", ["Slack could not be reached"]),
        lambda api: api.export(CONFIG_TOKEN, "A1"),
    ).kind == "slack_unavailable"


def test_an_outage_is_never_reported_as_a_deleted_app():
    for answer in [error("service_unavailable"), (503, {}, {}), error("invalid_auth")]:
        assert failure(answer, lambda api: api.export(CONFIG_TOKEN, "A1")).kind != "app_gone"


def test_any_other_error_is_unexpected_and_names_slacks_code():
    found = failure(error("something_new"), lambda api: api.create(CONFIG_TOKEN, MANIFEST))
    assert found.kind == "unexpected"
    assert found.details == ["apps.manifest.create: Slack answered something_new"]


def test_an_answer_that_is_not_json_is_unexpected():
    def transport(url, headers, body):
        return 200, {}, b"<html>"

    with pytest.raises(SlackAppError) as raised:
        SlackApi(transport).export(CONFIG_TOKEN, "A1")
    assert raised.value.kind == "unexpected"


@pytest.mark.parametrize("answer", [
    error("invalid_auth"), error("something_new"), (503, {}, {}),
    error("invalid_manifest", errors=[{"message": "bad", "pointer": "/"}]),
])
def test_no_token_appears_in_any_error(answer):
    calls = [
        lambda api: api.validate(CONFIG_TOKEN, MANIFEST, "A1"),
        lambda api: api.update(CONFIG_TOKEN, "A1", MANIFEST),
        lambda api: api.auth_test_scopes(BOT_TOKEN),
    ]
    for call in calls:
        found = failure(answer, call)
        text = " ".join([str(found), found.kind, *found.details])
        for token in (CONFIG_TOKEN, BOT_TOKEN):
            assert token not in text
