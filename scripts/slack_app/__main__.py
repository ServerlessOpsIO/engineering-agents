"""Command line for deploying the STRIDEr Slack app.

    pipenv run slack-app check [--output FILE]
    pipenv run slack-app validate
    pipenv run slack-app apply
    pipenv run slack-app create

Exit codes: 0 done, 1 failed with one failure kind, 2 wrong usage.
"""

import argparse
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    # Run as `python scripts/slack_app`: make the package importable by name.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slack_app import FAILURE_HELP, SlackAppError, definition  # noqa: E402
from slack_app.slack_api import SlackApi  # noqa: E402
from slack_app.store import Store, mask  # noqa: E402

SERVICE_TOKEN = "SLACK_SERVICE_TOKEN"
STORE_TOKEN = "SLACK_STORE_TOKEN"
APP_ID = "SLACK_APP_ID"
BOT_TOKEN = "SLACK_BOT_TOKEN"
SIGNING_SECRET = "SLACK_SIGNING_SECRET"
CLIENT_ID = "SLACK_CLIENT_ID"
CLIENT_SECRET = "SLACK_CLIENT_SECRET"


class Context:
    """What a command needs: its inputs, the two services, and where to write."""

    def __init__(self, env, api, store, root, out):
        self.env = env
        self.api = api
        self.store = store
        self.root = root
        self.out = out
        self.notes = []

    def note(self, text):
        self.notes.append(text)

    def mask(self, value):
        mask(value, env=self.env, out=self.out)


def _service_token(context):
    """Return the pipeline's Slack credential.

    It is a Slack CLI service token: long-lived, not replaced when used, and
    never written by this program.
    """
    token = context.env.get(SERVICE_TOKEN)
    if not token:
        raise SlackAppError("credential_missing", [f"{SERVICE_TOKEN} is not set"])
    return token


def _contains(actual, expected):
    """True when everything in `expected` is in `actual`. Extra fields in `actual` are fine.

    Slack adds default values to the manifest it returns, so the two cannot be
    compared for equality.
    """
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _contains(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            any(_contains(item, wanted) for item in actual) for wanted in expected
        )
    return actual == expected


def check(context, args):
    built = definition.check(context.root)
    if getattr(args, "output", None):
        Path(args.output).write_text(definition.to_json(built))
        context.note(f"The built manifest was written to {args.output}.")
    context.note("The app definition passed the offline check.")
    return built


def validate(context, args):
    built = definition.check(context.root)
    if not context.env.get(SERVICE_TOKEN):
        context.note(
            "The app definition passed the offline check. Slack validation was skipped: "
            f"{SERVICE_TOKEN} is not available to this run."
        )
        return
    token = _service_token(context)
    context.api.validate(token, definition.to_json(built), context.env.get(APP_ID) or None)
    context.note("The app definition passed the offline check and Slack's validation.")


def apply(context, args):
    built = definition.check(context.root)
    app_id = context.env.get(APP_ID)
    if not app_id:
        raise SlackAppError("app_not_recorded", [f"{APP_ID} is not set"])

    token = _service_token(context)
    # Raises app_gone when Slack does not know the app. An outage or a refused
    # credential raises its own kind, and never leads to creating an app.
    exported = context.api.export(token, app_id)
    if not _contains(exported, built):
        context.note(
            "The app in Slack did not match the app definition before this run. "
            "A change made outside the pipeline has been undone."
        )
    context.api.update(token, app_id, definition.to_json(built))
    context.note(f"The Slack app {app_id} now matches the app definition.")

    bot_token = context.env.get(BOT_TOKEN)
    if not bot_token:
        context.note(
            f"The app has not been installed, or {BOT_TOKEN} is not stored, so the "
            "installed permissions were not checked."
        )
        return
    held = context.api.auth_test_scopes(bot_token)
    missing = [scope for scope in definition.bot_scopes(built) if scope not in held]
    if missing:
        raise SlackAppError(
            "reinstall_needed",
            [f"The installed app lacks the permission {scope}" for scope in missing],
        )
    context.note("The installed app holds every permission in the app definition.")


def create(context, args):
    built = definition.check(context.root)
    token = _service_token(context)
    # Checked before anything is created: an app whose values cannot be stored
    # would have to be recovered by hand.
    if not context.env.get(STORE_TOKEN):
        raise SlackAppError("credential_missing", [f"{STORE_TOKEN} is not set"])

    recorded = context.env.get(APP_ID)
    if recorded:
        try:
            context.api.export(token, recorded)
        except SlackAppError as error:
            if error.kind != "app_gone":
                raise  # Slack unreachable or credential refused: do not create.
        else:
            raise SlackAppError("app_exists", [f"The recorded app {recorded} still exists"])

    answer = context.api.create(token, definition.to_json(built))
    credentials = answer.get("credentials") or {}
    for value in credentials.values():
        context.mask(value)
    app_id = answer.get("app_id")
    if not app_id:
        raise SlackAppError("unexpected", ["apps.manifest.create: no app ID in the answer"])

    context.note(f"Created the Slack app {app_id}.")
    try:
        context.store.set_variable(APP_ID, app_id)
        context.store.set_secret(SIGNING_SECRET, credentials.get("signing_secret") or "")
        context.store.set_secret(CLIENT_ID, credentials.get("client_id") or "")
        context.store.set_secret(CLIENT_SECRET, credentials.get("client_secret") or "")
    except SlackAppError as error:
        error.details.append(
            f"The app {app_id} was created in Slack. Store its values by hand: see "
            "'Recovery' in docs/handbook/08-slack-app.md"
        )
        raise
    context.note(
        f"Stored {APP_ID}, {SIGNING_SECRET}, {CLIENT_ID} and {CLIENT_SECRET}. "
        f"Install the app: https://api.slack.com/apps/{app_id}/install-on-team "
        f"then store its bot token as {BOT_TOKEN}."
    )


COMMANDS = {"check": check, "validate": validate, "apply": apply, "create": create}


def _append(path, text):
    if path:
        with open(path, "a") as file:
            file.write(text)


def _report(context, command, error):
    """Write what happened to the output, the run summary and the job outputs."""
    lines = [f"## Slack app: {command}", ""]
    lines += [f"- {note}" for note in context.notes]
    if error:
        lines += ["", f"**Failed: `{error.kind}`**", ""]
        lines += [f"- {detail}" for detail in error.details]
        lines += ["", f"What to do: {error.help}"]
        _append(
            context.env.get("GITHUB_OUTPUT"),
            f"failure_kind={error.kind}\nfailure_help={error.help}\n",
        )
    text = "\n".join(lines) + "\n"
    context.out(text)
    _append(context.env.get("GITHUB_STEP_SUMMARY"), text)


def main(argv=None, env=None, api=None, store=None, root=".", out=print):
    parser = argparse.ArgumentParser(prog="slack-app", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="check the app definition without contacting Slack") \
        .add_argument("--output", metavar="FILE", help="write the built manifest to FILE")
    commands.add_parser("validate", help="check, then ask Slack to validate")
    commands.add_parser("apply", help="make the recorded Slack app match the app definition")
    commands.add_parser("create", help="create the Slack app; refuses if it exists")
    args = parser.parse_args(argv)

    env = os.environ if env is None else env
    context = Context(
        env=env,
        api=api or SlackApi(),
        store=store or Store(env.get("GITHUB_REPOSITORY"), env.get(STORE_TOKEN)),
        root=root,
        out=out,
    )
    error = None
    try:
        COMMANDS[args.command](context, args)
    except SlackAppError as raised:
        error = raised
    except Exception as raised:  # Only the type is reported: a message could hold a secret.
        error = SlackAppError("unexpected", [f"{type(raised).__name__} was raised"])
    _report(context, args.command, error)
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
