"""Deploys the STRIDEr Slack app from the definition in slack/.

Run it with `pipenv run slack-app <command>`. The commands, their inputs and
their exit codes are described in
specs/006-slack-app-deployment/contracts/slack-app-pipeline.md.
"""

HANDBOOK = "docs/handbook/08-slack-app.md"

# Every failure the program reports is one of these kinds. The text is what the
# owner should do next. Run summaries and issues are built only from this table,
# never from a response, so that nothing secret can reach a public page.
FAILURE_HELP = {
    "invalid_definition": (
        "Fix the problems listed in the run's summary in slack/manifest.yaml or "
        "slack/settings.json."
    ),
    "credential_missing": (
        "A secret or variable the pipeline needs is not set. The run's summary names "
        f"it. See 'First-time setup' in {HANDBOOK}."
    ),
    "credential_rejected": (
        "Slack refused the pipeline's service token. Get a new one with "
        "`slack auth token` and store it as SLACK_SERVICE_TOKEN. "
        f"See 'Recovery' in {HANDBOOK}."
    ),
    "store_failed": (
        "A value could not be written to GitHub. Check SLACK_STORE_TOKEN and its "
        f"expiry date, then store the value by hand: see 'Recovery' in {HANDBOOK}."
    ),
    "app_not_recorded": (
        "No Slack app is recorded (SLACK_APP_ID is not set). Start the 'Slack app' "
        "workflow by hand with action 'create'."
    ),
    "app_gone": (
        "Slack says the recorded app does not exist. Start the 'Slack app' workflow by "
        "hand with action 'create', install the new app, store its bot token, and "
        f"update everything that used the old values. See 'Recovery' in {HANDBOOK}."
    ),
    "app_exists": "The recorded Slack app still exists, so no app was created. Nothing to do.",
    "reinstall_needed": (
        "The installed app lacks a permission that the app definition has. Install the "
        "app again in Slack, then check that SLACK_BOT_TOKEN is still the app's bot "
        f"token. See 'Adding a permission' in {HANDBOOK}."
    ),
    "bot_token_rejected": (
        "Slack refused the stored bot token. Copy the app's current bot token from "
        "Slack and store it as SLACK_BOT_TOKEN."
    ),
    "slack_unavailable": (
        "Slack could not be reached, or answered with a server error or a rate limit. "
        "Run the workflow again later."
    ),
    "unexpected": f"Read the run's log. See 'Recovery' in {HANDBOOK}.",
}


class SlackAppError(Exception):
    """A failure of one known kind, with details that are safe to publish."""

    def __init__(self, kind, details=()):
        if kind not in FAILURE_HELP:
            raise ValueError(f"unknown failure kind: {kind}")
        self.kind = kind
        self.details = list(details)
        super().__init__(kind)

    @property
    def help(self):
        return FAILURE_HELP[self.kind]
