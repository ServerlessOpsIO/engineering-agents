"""Writes values to this repository's GitHub secrets and variables with the `gh` command.

The workflow's built-in token cannot write secrets, so a separate token,
SLACK_STORE_TOKEN, is used. Values are passed on standard input and never as
arguments, so they do not appear in a process list.
"""

import os
import subprocess
import time

from slack_app import SlackAppError

ATTEMPTS = 3
WAIT_SECONDS = 2


def mask(value, env=None, out=print):
    """Tell GitHub Actions to hide a value in everything printed after this.

    Outside GitHub Actions nothing is printed, because printing the command
    would itself show the value.
    """
    env = os.environ if env is None else env
    if value and env.get("GITHUB_ACTIONS") == "true":
        out(f"::add-mask::{value}")


class Store:
    def __init__(self, repository, token, runner=subprocess.run, sleep=time.sleep):
        self._repository = repository
        self._token = token
        self._runner = runner
        self._sleep = sleep

    def set_secret(self, name, value):
        self._set("secret", name, value)

    def set_variable(self, name, value):
        self._set("variable", name, value)

    def _set(self, kind, name, value):
        if not self._token:
            raise SlackAppError("credential_missing", ["SLACK_STORE_TOKEN is not set"])
        if not self._repository:
            raise SlackAppError("credential_missing", ["GITHUB_REPOSITORY is not set"])

        command = ["gh", kind, "set", name, "--repo", self._repository]
        env = {**os.environ, "GH_TOKEN": self._token}
        for attempt in range(1, ATTEMPTS + 1):
            try:
                result = self._runner(
                    command, input=value, text=True, capture_output=True, env=env, check=False
                )
                if result.returncode == 0:
                    return
            except OSError:
                pass
            if attempt < ATTEMPTS:
                self._sleep(WAIT_SECONDS)
        # The command's own output is left out on purpose: nothing it printed is published.
        raise SlackAppError("store_failed", [f"{name} could not be written to GitHub"])
