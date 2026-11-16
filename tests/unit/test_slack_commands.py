"""Tests for the slack-app commands. Slack and GitHub are replaced by fakes."""

import json
import shutil
from pathlib import Path

import pytest

from slack_app import FAILURE_HELP, SlackAppError
from slack_app import __main__ as cli

REPO_ROOT = Path(__file__).resolve().parents[2]

SERVICE_TOKEN = "xoxp-service-token"
STORE_TOKEN = "github_pat_store-token"
BOT_TOKEN = "xoxb-bot-token"
SIGNING_SECRET = "signing-secret-value"
CLIENT_ID = "1234567890.0987654321"
CLIENT_SECRET = "client-secret-value"
VERIFICATION_TOKEN = "verification-token-value"
SECRETS = [
    SERVICE_TOKEN, STORE_TOKEN, BOT_TOKEN, SIGNING_SECRET, CLIENT_ID,
    CLIENT_SECRET, VERIFICATION_TOKEN,
]

DEFINED_SCOPES = {
    "app_mentions:read", "chat:write", "im:history", "channels:history", "groups:history",
}


class FakeSlack:
    """Stands in for SlackApi. Records the order of calls in the shared `log`."""

    def __init__(self, log):
        self.log = log
        self.fail = {}           # method name -> SlackAppError to raise
        self.exported = None     # None means: return what was built
        self.scopes = set(DEFINED_SCOPES)
        self.sent = {}

    def _do(self, name):
        self.log.append(name)
        if name in self.fail:
            raise self.fail[name]

    def validate(self, token, manifest_json, app_id=None):
        self._do("validate")
        self.sent["token"] = token
        self.sent["validate_app_id"] = app_id

    def export(self, token, app_id):
        self._do("export")
        self.sent["token"] = token
        return self.exported if self.exported is not None else {"_slack_default": True}

    def update(self, token, app_id, manifest_json):
        self._do("update")
        self.sent["manifest"] = json.loads(manifest_json)
        return {"ok": True}

    def create(self, token, manifest_json):
        self._do("create")
        return {
            "app_id": "A0NEW",
            "credentials": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "verification_token": VERIFICATION_TOKEN,
                "signing_secret": SIGNING_SECRET,
            },
            "oauth_authorize_url": f"https://slack.com/oauth/v2/authorize?client_id={CLIENT_ID}",
        }

    def auth_test_scopes(self, bot_token):
        self._do("auth_test")
        return self.scopes


class FakeStore:
    def __init__(self, log):
        self.log = log
        self.fail_on = set()
        self.secrets = {}
        self.variables = {}

    def set_secret(self, name, value):
        self.log.append(f"store:{name}")
        if name in self.fail_on:
            raise SlackAppError("store_failed", [f"{name} could not be written to GitHub"])
        self.secrets[name] = value

    def set_variable(self, name, value):
        self.log.append(f"store:{name}")
        if name in self.fail_on:
            raise SlackAppError("store_failed", [f"{name} could not be written to GitHub"])
        self.variables[name] = value


class Run:
    """One run of a command with fakes, and everything it wrote."""

    def __init__(self, tmp_path):
        self.log = []
        self.slack = FakeSlack(self.log)
        self.store = FakeStore(self.log)
        self.root = tmp_path / "repo"
        shutil.copytree(REPO_ROOT / "slack", self.root / "slack")
        self.summary_file = tmp_path / "summary.md"
        self.output_file = tmp_path / "output.txt"
        self.env = {
            "SLACK_SERVICE_TOKEN": SERVICE_TOKEN,
            "SLACK_STORE_TOKEN": STORE_TOKEN,
            "SLACK_APP_ID": "A0OLD",
            "SLACK_BOT_TOKEN": BOT_TOKEN,
            "GITHUB_REPOSITORY": "ServerlessOpsIO/engineering-agents",
            "GITHUB_ACTIONS": "true",
            "GITHUB_STEP_SUMMARY": str(self.summary_file),
            "GITHUB_OUTPUT": str(self.output_file),
        }
        self.printed = []
        self.code = None

    def __call__(self, *argv):
        self.code = cli.main(
            list(argv), env=self.env, api=self.slack, store=self.store, root=self.root,
            out=self.printed.append,
        )
        return self

    @property
    def summary(self):
        return self.summary_file.read_text() if self.summary_file.exists() else ""

    @property
    def outputs(self):
        if not self.output_file.exists():
            return {}
        return dict(line.split("=", 1) for line in self.output_file.read_text().splitlines())

    @property
    def kind(self):
        return self.outputs.get("failure_kind")

    @property
    def published(self):
        """Everything a reader could see, leaving out the lines that tell GitHub what to hide."""
        printed = [line for line in self.printed if not line.startswith("::add-mask::")]
        return "\n".join(printed) + self.summary + self.output_file.read_text() \
            if self.output_file.exists() else "\n".join(printed) + self.summary


@pytest.fixture
def run(tmp_path):
    return Run(tmp_path)


def break_definition(run):
    (run.root / "slack" / "settings.json").write_text('{"event_request_url": "http://x"}')


# check

def test_check_passes_and_contacts_nothing(run):
    assert run("check").code == 0
    assert run.log == []
    assert "passed the offline check" in run.summary


def test_check_writes_the_built_manifest(run, tmp_path):
    target = tmp_path / "manifest.json"
    assert run("check", "--output", str(target)).code == 0
    assert json.loads(target.read_text())["display_information"]["name"] == "STRIDEr"


def test_check_reports_each_problem_and_what_to_do(run):
    break_definition(run)
    assert run("check").code == 1
    assert run.kind == "invalid_definition"
    assert run.outputs["failure_help"] == FAILURE_HELP["invalid_definition"]
    assert "event_request_url: must start with https://" in run.summary


def test_wrong_usage_exits_with_2(run):
    with pytest.raises(SystemExit) as raised:
        run("deploy")
    assert raised.value.code == 2


# what every command that contacts Slack has in common

@pytest.mark.parametrize("command", ["validate", "apply", "create"])
def test_the_service_token_is_sent_to_slack_and_never_stored(run, command):
    run(command)
    assert run.slack.sent["token"] == SERVICE_TOKEN
    assert "SLACK_SERVICE_TOKEN" not in run.store.secrets


@pytest.mark.parametrize("command", ["validate", "apply"])
def test_validating_and_applying_write_nothing_to_github(run, command):
    assert run(command).code == 0
    assert run.store.secrets == {} and run.store.variables == {}


@pytest.mark.parametrize("command", ["validate", "apply", "create"])
def test_a_bad_definition_stops_before_slack_is_contacted(run, command):
    break_definition(run)
    assert run(command).code == 1
    assert run.kind == "invalid_definition"
    assert run.log == []


@pytest.mark.parametrize("command", ["apply", "create"])
def test_a_missing_service_token_is_a_missing_credential(run, command):
    run.env.pop("SLACK_SERVICE_TOKEN")
    assert run(command).code == 1
    assert run.kind == "credential_missing"
    assert "SLACK_SERVICE_TOKEN is not set" in run.summary
    assert run.log == []


def test_nothing_is_created_when_the_apps_values_could_not_be_stored(run):
    run.env.pop("SLACK_APP_ID")
    run.env.pop("SLACK_STORE_TOKEN")
    assert run("create").code == 1
    assert run.kind == "credential_missing"
    assert "SLACK_STORE_TOKEN is not set" in run.summary
    assert run.log == []


@pytest.mark.parametrize("command, first_call", [
    ("validate", "validate"), ("apply", "export"), ("create", "export"),
])
def test_a_refused_credential_is_reported_as_itself(run, command, first_call):
    run.slack.fail[first_call] = SlackAppError("credential_rejected", [f"{first_call}: x"])
    assert run(command).code == 1
    assert run.kind == "credential_rejected"
    assert run.log == [first_call]


# validate

def test_validate_without_the_credential_skips_slack_and_passes(run):
    run.env.pop("SLACK_SERVICE_TOKEN")
    assert run("validate").code == 0
    assert run.log == []
    assert "Slack validation was skipped" in run.summary


def test_validate_asks_slack_and_names_the_recorded_app(run):
    assert run("validate").code == 0
    assert run.log == ["validate"]
    assert run.slack.sent["validate_app_id"] == "A0OLD"


def test_validate_works_before_any_app_is_recorded(run):
    run.env.pop("SLACK_APP_ID")
    assert run("validate").code == 0
    assert run.slack.sent["validate_app_id"] is None


def test_validate_reports_what_slack_rejected_with_its_place(run):
    run.slack.fail["validate"] = SlackAppError(
        "invalid_definition", ["Slack: /oauth_config/scopes/bot/5: Unknown scope not:a:scope"]
    )
    assert run("validate").code == 1
    assert run.kind == "invalid_definition"
    assert "/oauth_config/scopes/bot/5: Unknown scope not:a:scope" in run.summary


def test_validate_never_changes_slack(run):
    run("validate")
    assert "update" not in run.log and "create" not in run.log


# apply, one test for each state of the app

def test_apply_with_no_app_recorded_fails_and_changes_nothing(run):
    run.env.pop("SLACK_APP_ID")
    assert run("apply").code == 1
    assert run.kind == "app_not_recorded"
    assert run.log == []


def test_apply_to_an_app_slack_does_not_know_fails_and_creates_nothing(run):
    run.slack.fail["export"] = SlackAppError("app_gone", ["apps.manifest.export: app_not_found"])
    assert run("apply").code == 1
    assert run.kind == "app_gone"
    assert "update" not in run.log and "create" not in run.log
    assert "action 'create'" in run.outputs["failure_help"]


@pytest.mark.parametrize("kind", ["slack_unavailable", "credential_rejected"])
def test_apply_never_reports_an_outage_or_a_refused_credential_as_a_deleted_app(run, kind):
    run.slack.fail["export"] = SlackAppError(kind, ["apps.manifest.export: x"])
    assert run("apply").code == 1
    assert run.kind == kind
    assert "update" not in run.log and "create" not in run.log


def test_apply_to_an_app_that_is_not_installed_updates_and_passes(run):
    run.env.pop("SLACK_BOT_TOKEN")
    assert run("apply").code == 0
    assert "update" in run.log and "auth_test" not in run.log
    assert "has not been installed" in run.summary


def test_apply_to_an_installed_app_in_step_updates_and_passes(run):
    assert run("apply").code == 0
    assert run.log == ["export", "update", "auth_test"]
    assert run.slack.sent["manifest"]["display_information"]["name"] == "STRIDEr"
    assert "holds every permission" in run.summary


def test_apply_fails_after_updating_when_the_installed_app_lacks_a_permission(run):
    run.slack.scopes = DEFINED_SCOPES - {"groups:history"}
    assert run("apply").code == 1
    assert run.kind == "reinstall_needed"
    assert "update" in run.log
    assert "lacks the permission groups:history" in run.summary
    assert "Install the app again" in run.outputs["failure_help"]


def test_apply_passes_when_the_installed_app_holds_a_permission_the_definition_does_not(run):
    run.slack.scopes = DEFINED_SCOPES | {"reactions:read"}
    assert run("apply").code == 0


def test_apply_reports_a_refused_bot_token_as_itself_and_not_as_a_missing_permission(run):
    run.slack.fail["auth_test"] = SlackAppError("bot_token_rejected", ["auth.test: invalid_auth"])
    assert run("apply").code == 1
    assert run.kind == "bot_token_rejected"
    assert "store it as SLACK_BOT_TOKEN" in run.outputs["failure_help"]


def test_apply_says_when_a_change_made_outside_the_pipeline_was_undone(run):
    run.slack.exported = {"display_information": {"name": "Renamed by hand"}}
    assert run("apply").code == 0
    assert "A change made outside the pipeline is being undone" in run.summary


def test_apply_does_not_call_slacks_added_defaults_a_change(run):
    built = json.loads(json.dumps(cli.definition.check(run.root)))
    built["display_information"]["background_color"] = "#000000"
    built["settings"]["is_hosted"] = False
    run.slack.exported = built
    assert run("apply").code == 0
    assert "outside the pipeline" not in run.summary


def test_apply_holds_events_back_until_there_is_an_address(run):
    run("apply")
    assert "event_subscriptions" not in run.slack.sent["manifest"]["settings"]


# the commands the workflow runs around Slack's GitHub Action

def test_check_writes_the_request_for_the_action(run, tmp_path):
    target = tmp_path / "payload.json"
    assert run("check", "--payload", str(target)).code == 0
    payload = json.loads(target.read_text())
    assert payload["app_id"] == "A0OLD"
    assert json.loads(payload["manifest"])["display_information"]["name"] == "STRIDEr"
    assert run.log == []


def test_check_leaves_the_app_id_out_of_the_request_before_an_app_is_recorded(run, tmp_path):
    run.env.pop("SLACK_APP_ID")
    target = tmp_path / "payload.json"
    assert run("check", "--payload", str(target)).code == 0
    assert set(json.loads(target.read_text())) == {"manifest"}


def test_prepare_writes_the_request_and_contacts_nothing(run, tmp_path):
    target = tmp_path / "payload.json"
    assert run("prepare", "--payload", str(target)).code == 0
    assert run.log == []
    payload = json.loads(target.read_text())
    assert payload["app_id"] == "A0OLD"
    assert "event_subscriptions" not in json.loads(payload["manifest"])["settings"]


def test_prepare_with_no_app_recorded_fails_and_writes_no_request(run, tmp_path):
    run.env.pop("SLACK_APP_ID")
    target = tmp_path / "payload.json"
    assert run("prepare", "--payload", str(target)).code == 1
    assert run.kind == "app_not_recorded"
    assert not target.exists()


def test_prepare_with_no_service_token_fails_before_the_action_would(run, tmp_path):
    run.env.pop("SLACK_SERVICE_TOKEN")
    target = tmp_path / "payload.json"
    assert run("prepare", "--payload", str(target)).code == 1
    assert run.kind == "credential_missing"
    assert not target.exists()


def action_answer(
    run, ok, error="", errors=None, status="", code="", retry_after="", manifest=None
):
    """Set what the workflow passes on from the outputs of Slack's GitHub Action."""
    run.env.update({
        "SLACK_ACTION_MANIFEST": "null" if manifest is None else json.dumps(manifest),
        "SLACK_ACTION_OK": ok,
        "SLACK_ACTION_ERROR": error,
        "SLACK_ACTION_ERRORS": "null" if errors is None else json.dumps(errors),
        "SLACK_ACTION_STATUS": status,
        "SLACK_ACTION_CODE": code,
        "SLACK_ACTION_RETRY_AFTER": retry_after,
    })


def test_result_passes_when_slack_accepted_the_call(run):
    action_answer(run, "true")
    assert run("result", "--method", "apps.manifest.update").code == 0
    assert "Slack accepted apps.manifest.update" in run.summary
    assert run.log == []


def test_result_reports_what_slack_rejected_with_its_place(run):
    action_answer(run, "false", "invalid_manifest", [
        {"message": "Unknown scope not:a:scope", "pointer": "/oauth_config/scopes/bot/5"},
    ])
    assert run("result", "--method", "apps.manifest.validate").code == 1
    assert run.kind == "invalid_definition"
    assert "/oauth_config/scopes/bot/5: Unknown scope not:a:scope" in run.summary


@pytest.mark.parametrize("answer, kind", [
    ({"error": "invalid_auth"}, "credential_rejected"),
    ({"error": "not_allowed_token_type"}, "credential_rejected"),
    ({"error": "app_not_found"}, "app_gone"),
    ({"error": "ratelimited"}, "slack_unavailable"),
    ({"error": "something_new"}, "unexpected"),
    ({"error": "invalid_manifest", "errors": "not a list"}, "invalid_definition"),
    ({"code": "slack_webapi_http_error", "status": "503"}, "slack_unavailable"),
    ({"code": "slack_webapi_rate_limited_error", "retry_after": "30"}, "slack_unavailable"),
    ({"code": "ENOTFOUND"}, "slack_unavailable"),
    ({"status": "404"}, "unexpected"),
    ({}, "unexpected"),
])
def test_result_turns_each_kind_of_failed_answer_into_a_failure_kind(run, answer, kind):
    action_answer(run, "false", **answer)
    assert run("result", "--method", "apps.manifest.update").code == 1
    assert run.kind == kind
    assert run.outputs["failure_help"] == FAILURE_HELP[kind]


def test_result_fails_when_the_action_did_not_run(run):
    assert run("result", "--method", "apps.manifest.update").code == 1
    assert run.kind == "unexpected"


def test_result_does_not_trust_ok_when_slack_also_named_an_error(run):
    action_answer(run, "true", "invalid_auth")
    assert run("result", "--method", "apps.manifest.update").code == 1
    assert run.kind == "credential_rejected"


# reading the answer to "does the recorded app exist?"

def test_result_passes_when_the_recorded_app_exists(run):
    action_answer(run, "true", manifest={"_slack_default": True})
    assert run("result", "--method", "apps.manifest.export").code == 0
    assert run.log == []


def test_result_reports_a_deleted_app_and_how_to_replace_it(run):
    action_answer(run, "false", "app_not_found")
    assert run("result", "--method", "apps.manifest.export").code == 1
    assert run.kind == "app_gone"
    assert "action 'create'" in run.outputs["failure_help"]


@pytest.mark.parametrize("answer, kind", [
    ({"error": "service_unavailable"}, "slack_unavailable"),
    ({"status": "503"}, "slack_unavailable"),
    ({"error": "invalid_auth"}, "credential_rejected"),
    ({}, "unexpected"),
])
def test_result_never_reports_an_outage_or_a_refused_credential_as_a_deleted_app(
    run, answer, kind
):
    action_answer(run, "false", **answer)
    assert run("result", "--method", "apps.manifest.export").code == 1
    assert run.kind == kind


def test_result_says_when_a_change_made_outside_the_pipeline_is_being_undone(run):
    action_answer(run, "true", manifest={"display_information": {"name": "Renamed by hand"}})
    assert run("result", "--method", "apps.manifest.export").code == 0
    assert "A change made outside the pipeline is being undone" in run.summary


def test_result_does_not_call_slacks_added_defaults_a_change(run):
    exported = json.loads(json.dumps(cli.definition.check(run.root)))
    exported["display_information"]["background_color"] = "#000000"
    action_answer(run, "true", manifest=exported)
    assert run("result", "--method", "apps.manifest.export").code == 0
    assert "outside the pipeline" not in run.summary


def test_result_passes_without_a_manifest_to_compare(run):
    action_answer(run, "true")
    assert run("result", "--method", "apps.manifest.export").code == 0


# create, when Slack's GitHub Action has asked whether the recorded app exists

def test_create_refuses_when_the_action_found_the_recorded_app(run):
    action_answer(run, "true", manifest={"_slack_default": True})
    assert run("create", "--existence-from-action").code == 1
    assert run.kind == "app_exists"
    assert run.log == []


def test_create_replaces_the_app_when_the_action_found_it_gone(run):
    action_answer(run, "false", "app_not_found")
    assert run("create", "--existence-from-action").code == 0
    assert "export" not in run.log and "create" in run.log
    assert run.store.variables == {"SLACK_APP_ID": "A0NEW"}


@pytest.mark.parametrize("answer, kind", [
    ({"error": "service_unavailable"}, "slack_unavailable"),
    ({"error": "invalid_auth"}, "credential_rejected"),
    ({"status": "503"}, "slack_unavailable"),
    ({}, "unexpected"),
])
def test_create_does_not_create_when_the_action_could_not_tell(run, answer, kind):
    action_answer(run, "false", **answer)
    assert run("create", "--existence-from-action").code == 1
    assert run.kind == kind
    assert run.log == []


def test_create_with_no_app_recorded_does_not_need_the_actions_answer(run):
    run.env.pop("SLACK_APP_ID")
    assert run("create", "--existence-from-action").code == 0
    assert run.log[0] == "create"


def test_verify_passes_when_the_installed_app_holds_every_permission(run):
    assert run("verify").code == 0
    assert run.log == ["auth_test"]


def test_verify_fails_when_the_installed_app_lacks_a_permission(run):
    run.slack.scopes = DEFINED_SCOPES - {"im:history"}
    assert run("verify").code == 1
    assert run.kind == "reinstall_needed"
    assert "lacks the permission im:history" in run.summary


def test_verify_passes_with_a_note_when_the_app_is_not_installed(run):
    run.env.pop("SLACK_BOT_TOKEN")
    assert run("verify").code == 0
    assert run.log == []
    assert "has not been installed" in run.summary


def test_verify_reports_a_refused_bot_token_as_itself(run):
    run.slack.fail["auth_test"] = SlackAppError("bot_token_rejected", ["auth.test: invalid_auth"])
    assert run("verify").code == 1
    assert run.kind == "bot_token_rejected"


# create

def test_create_with_no_app_recorded_creates_and_stores_the_apps_values(run):
    run.env.pop("SLACK_APP_ID")
    assert run("create").code == 0
    assert run.log == [
        "create", "store:SLACK_APP_ID",
        "store:SLACK_SIGNING_SECRET", "store:SLACK_CLIENT_ID", "store:SLACK_CLIENT_SECRET",
    ]
    assert run.store.variables == {"SLACK_APP_ID": "A0NEW"}
    assert run.store.secrets["SLACK_SIGNING_SECRET"] == SIGNING_SECRET
    assert run.store.secrets["SLACK_CLIENT_ID"] == CLIENT_ID
    assert run.store.secrets["SLACK_CLIENT_SECRET"] == CLIENT_SECRET
    assert "A0NEW" in run.summary
    assert "https://api.slack.com/apps/A0NEW/install-on-team" in run.summary


def test_create_masks_every_value_slack_returned_before_printing_anything_else(run):
    run.env.pop("SLACK_APP_ID")
    run("create")
    masks = [line for line in run.printed if line.startswith("::add-mask::")]
    for value in (SIGNING_SECRET, CLIENT_ID, CLIENT_SECRET, VERIFICATION_TOKEN):
        assert f"::add-mask::{value}" in masks
    last_mask = max(index for index, line in enumerate(run.printed) if line in masks)
    first_other = min(
        index for index, line in enumerate(run.printed) if line not in masks
    )
    assert last_mask < first_other


def test_create_refuses_while_the_recorded_app_exists(run):
    assert run("create").code == 1
    assert run.kind == "app_exists"
    assert "create" not in run.log


def test_create_replaces_an_app_slack_does_not_know(run):
    run.slack.fail["export"] = SlackAppError("app_gone", ["apps.manifest.export: app_not_found"])
    assert run("create").code == 0
    assert run.store.variables == {"SLACK_APP_ID": "A0NEW"}
    assert run.store.secrets["SLACK_SIGNING_SECRET"] == SIGNING_SECRET


@pytest.mark.parametrize("kind", ["slack_unavailable", "credential_rejected", "unexpected"])
def test_create_does_not_create_when_it_cannot_tell_whether_the_app_exists(run, kind):
    run.slack.fail["export"] = SlackAppError(kind, ["apps.manifest.export: x"])
    assert run("create").code == 1
    assert run.kind == kind
    assert "create" not in run.log


@pytest.mark.parametrize("name", [
    "SLACK_APP_ID", "SLACK_SIGNING_SECRET", "SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET",
])
def test_create_says_which_app_was_made_when_a_value_cannot_be_stored(run, name):
    run.env.pop("SLACK_APP_ID")
    run.store.fail_on.add(name)
    assert run("create").code == 1
    assert run.kind == "store_failed"
    assert f"{name} could not be written to GitHub" in run.summary
    assert "The app A0NEW was created in Slack" in run.summary


# nothing secret is published (FR-018)

@pytest.mark.parametrize("command, change", [
    ("validate", lambda run: None),
    ("prepare", lambda run: None),
    ("verify", lambda run: setattr(run.slack, "scopes", set())),
    ("apply", lambda run: None),
    ("apply", lambda run: setattr(run.slack, "scopes", set())),
    ("create", lambda run: run.env.pop("SLACK_APP_ID")),
    ("create", lambda run: None),
    ("create", lambda run: (run.env.pop("SLACK_APP_ID"),
                            run.store.fail_on.add("SLACK_CLIENT_SECRET"))),
])
def test_no_secret_is_published(run, command, change):
    change(run)
    run(*([command, "--payload", str(run.root / "payload.json")] if command == "prepare"
          else [command]))
    for value in SECRETS:
        assert value not in run.published


def test_an_unexpected_error_reports_only_its_type(run):
    def explode(token, app_id):
        raise RuntimeError(f"failed with {token}")

    run.slack.export = explode
    assert run("apply").code == 1
    assert run.kind == "unexpected"
    assert "RuntimeError was raised" in run.summary
    assert SERVICE_TOKEN not in run.published
