"""Tests for writing GitHub secrets and variables. The `gh` command is replaced by a fake."""

from types import SimpleNamespace

import pytest

from slack_app import SlackAppError
from slack_app.store import Store, mask

STORE_TOKEN = "github_pat_store-token-value"
SECRET_VALUE = "signing-secret-value"


class FakeGh:
    """Fails the first `failures` runs, then succeeds. Records every run."""

    def __init__(self, failures=0, raises=False):
        self.failures = failures
        self.raises = raises
        self.runs = []

    def __call__(self, command, **options):
        self.runs.append({"command": command, **options})
        if len(self.runs) <= self.failures:
            if self.raises:
                raise OSError("gh not found")
            return SimpleNamespace(returncode=1, stdout="", stderr=f"failed {SECRET_VALUE}")
        return SimpleNamespace(returncode=0, stdout="", stderr="")


def make_store(gh, token=STORE_TOKEN, repository="ServerlessOpsIO/engineering-agents"):
    return Store(repository, token, runner=gh, sleep=lambda seconds: None)


def test_a_secret_is_written_with_its_value_on_standard_input():
    gh = FakeGh()
    make_store(gh).set_secret("SLACK_SIGNING_SECRET", SECRET_VALUE)
    run = gh.runs[0]
    assert run["command"] == [
        "gh", "secret", "set", "SLACK_SIGNING_SECRET",
        "--repo", "ServerlessOpsIO/engineering-agents",
    ]
    assert run["input"] == SECRET_VALUE
    assert SECRET_VALUE not in " ".join(run["command"])


def test_a_variable_is_written_with_gh_variable_set():
    gh = FakeGh()
    make_store(gh).set_variable("SLACK_APP_ID", "A123")
    assert gh.runs[0]["command"][:4] == ["gh", "variable", "set", "SLACK_APP_ID"]
    assert gh.runs[0]["input"] == "A123"


def test_the_store_token_is_what_gh_signs_in_with():
    gh = FakeGh()
    make_store(gh).set_secret("NAME", "value")
    assert gh.runs[0]["env"]["GH_TOKEN"] == STORE_TOKEN


def test_a_failed_write_is_retried():
    gh = FakeGh(failures=2)
    make_store(gh).set_secret("NAME", "value")
    assert len(gh.runs) == 3


def test_a_write_that_keeps_failing_gives_up_after_three_attempts():
    gh = FakeGh(failures=99)
    with pytest.raises(SlackAppError) as raised:
        make_store(gh).set_secret("SLACK_SIGNING_SECRET", SECRET_VALUE)
    assert len(gh.runs) == 3
    assert raised.value.kind == "store_failed"
    assert raised.value.details == ["SLACK_SIGNING_SECRET could not be written to GitHub"]


def test_a_failed_write_does_not_repeat_what_gh_printed():
    gh = FakeGh(failures=99)
    with pytest.raises(SlackAppError) as raised:
        make_store(gh).set_secret("NAME", SECRET_VALUE)
    assert SECRET_VALUE not in " ".join([str(raised.value), *raised.value.details])


def test_gh_not_being_installed_is_a_failed_write():
    gh = FakeGh(failures=99, raises=True)
    with pytest.raises(SlackAppError) as raised:
        make_store(gh).set_secret("NAME", "value")
    assert raised.value.kind == "store_failed"


def test_a_missing_store_token_is_a_missing_credential():
    gh = FakeGh()
    with pytest.raises(SlackAppError) as raised:
        make_store(gh, token="").set_secret("NAME", "value")
    assert raised.value.kind == "credential_missing"
    assert raised.value.details == ["SLACK_GHA_STORE_TOKEN is not set"]
    assert gh.runs == []


def test_mask_prints_the_mask_command_once_in_github_actions():
    printed = []
    mask(SECRET_VALUE, env={"GITHUB_ACTIONS": "true"}, out=printed.append)
    assert printed == [f"::add-mask::{SECRET_VALUE}"]


def test_mask_prints_nothing_outside_github_actions():
    printed = []
    mask(SECRET_VALUE, env={}, out=printed.append)
    assert printed == []


def test_mask_ignores_an_empty_value():
    printed = []
    mask("", env={"GITHUB_ACTIONS": "true"}, out=printed.append)
    assert printed == []
