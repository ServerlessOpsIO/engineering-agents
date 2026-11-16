# The STRIDEr Slack app

STRIDEr is a Slack agent that will lead threat modeling exercises using the STRIDE
framework. This page covers the Slack app that represents STRIDEr in the `serverlessops`
workspace: how it is created, changed and repaired.

**STRIDEr does not answer yet.** The app gives STRIDEr a name, a bot user and permissions.
The service that receives messages from Slack and replies is a later feature. Until then
the app is present in the workspace and does nothing when spoken to.

Nothing on this page has been run against Slack yet. The first-time setup below is also the
first real test of the pipeline; record what happens in
`specs/006-slack-app-deployment/quickstart.md`.

## How it works

| File | Purpose |
| --- | --- |
| `slack/manifest.yaml` | The app definition: name, bot user, permissions and events. The single source of truth. |
| `slack/settings.json` | The event delivery address, `event_request_url`. Empty for now. |
| `slack/manifest.schema.json` | A copy of Slack's published schema for app definitions, used by the check. |
| `scripts/slack_app/` | The program the pipeline runs: `pipenv run slack-app <command>`. |
| `.github/workflows/slack-app.yml` | The `Slack app` workflow. See [CI/CD pipeline](05-ci-cd.md#the-slack-app-workflow). |

The pipeline makes the app in Slack match `slack/manifest.yaml`. **Do not change the app in
the Slack console.** A change made there is undone by the next run, at most a day later.

While `event_request_url` is empty, the events listed in `slack/manifest.yaml` are not sent
to Slack, because Slack does not accept events without an address. The permissions are sent.

## First-time setup

Do this once, on `main`. It takes the workspace from having no STRIDEr app to an installed
app managed by the pipeline. Four steps are done by hand; the reason is given for each.

1. **Create the credential for changing Slack apps. By hand:** Slack only issues it to a
   signed-in person.
   1. Open <https://api.slack.com/apps> and find **Your App Configuration Tokens**.
   2. Select **Generate Token** and choose the `serverlessops` workspace.
   3. Copy the **refresh token**, which starts with `xoxe-`. The access token is not needed.
   4. Store it as the repository secret `SLACK_CONFIG_REFRESH_TOKEN`:

      ```bash
      gh secret set SLACK_CONFIG_REFRESH_TOKEN --repo ServerlessOpsIO/engineering-agents
      ```

   This token belongs to you and can change every Slack app you own in the workspace. Slack
   offers nothing narrower. The pipeline replaces it on every run, so the value you stored
   stops working after the first run; that is expected.

2. **Create the credential for storing values. By hand:** GitHub's built-in workflow token
   cannot write secrets, and a token that can has to be issued by a person.
   1. In GitHub, open **Settings**, **Developer settings**, **Personal access tokens**,
      **Fine-grained tokens**, and generate a token.
   2. Resource owner: `ServerlessOpsIO`. Repository access: only `engineering-agents`.
   3. Repository permissions: **Secrets: Read and write** and **Variables: Read and write**.
      Nothing else.
   4. Choose an expiry date and put a reminder in your calendar for a week before it.
   5. Store it as the repository secret `SLACK_STORE_TOKEN`.

3. **Create the app. By the pipeline.** In GitHub, open **Actions**, **Slack app**, **Run
   workflow**, choose the branch `main` and the action `create`. The run:
   - checks the app definition and asks Slack to validate it;
   - creates the app;
   - stores the variable `SLACK_APP_ID` and the secrets `SLACK_SIGNING_SECRET`,
     `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET`;
   - shows the app ID and an install link in its summary.

4. **Install the app. By hand:** Slack requires a person in the workspace to approve an
   app's permissions. Open the install link from the run's summary,
   `https://api.slack.com/apps/<app ID>/install-on-team`, and select **Install to
   Workspace**.

5. **Store the bot token. By hand:** it is only shown to a signed-in person, after the
   install. In the app's settings open **OAuth & Permissions**, copy the **Bot User OAuth
   Token**, which starts with `xoxb-`, and store it as the repository secret
   `SLACK_BOT_TOKEN`.

6. **Confirm. By the pipeline.** Run the workflow again with the action `apply`. It passes
   when the app matches the definition and the installed app holds every permission in it.

STRIDEr is now listed under the workspace's apps.

### Being told about failures

The workflow runs once a day. When that run fails:

- **GitHub notifies you**, if your notification settings allow it. In GitHub open
  **Settings**, **Notifications**, **Actions**, and make sure failed workflow runs are
  notified. GitHub sends notifications for a scheduled workflow to the person who last
  changed its schedule.
- **An issue labelled `slack-app-failure` is opened** in this repository, saying what failed
  and what to do. Later failures add a comment to it. The next run that passes closes it.

A failed run that you started, by merging or by hand, does not open an issue.

### The daily run can be switched off by GitHub

GitHub disables scheduled workflows in a public repository after 60 days without activity
in the repository, and emails you first. Nothing in this repository can report that, because
nothing runs. To switch it back on, open **Actions**, **Slack app**, and select **Enable
workflow**.

## Changing the app

1. Edit `slack/manifest.yaml` on a branch.
2. Every permission and every event needs a comment on its line giving its reason. The
   check fails without one.
3. Check it locally:

   ```bash
   pipenv run slack-app check
   ```

4. Push the branch. The `Slack app` workflow checks the definition and asks Slack to
   validate it. Nothing in Slack changes.
5. Merge to `main`. The workflow updates the app.

Slash commands, shortcuts, the home tab, Socket Mode and user permissions are not allowed
by the check. Changing that is a change to the project's requirements, not only to the
file.

## Adding a permission

Slack applies a new permission only after the app is installed again. So after a merge that
adds one:

1. The run on `main` updates the app and then **fails** with `reinstall_needed`, naming the
   permission. The daily run fails the same way, and opens an issue, until step 2 is done.
2. Open `https://api.slack.com/apps/<app ID>/install-on-team` and select **Reinstall to
   Workspace**.
3. In **OAuth & Permissions**, check that the **Bot User OAuth Token** is still the value
   stored as `SLACK_BOT_TOKEN`. If it has changed, store the new one.
4. Run the workflow with the action `apply`. It passes, and closes the issue if one is open.

Removing a permission needs no action: the run passes. Whether the installed app keeps a
removed permission until it is next installed is not yet known; see issue #7.

## Supplying the event delivery address

This belongs to the later feature, which provides the service Slack sends events to.

1. Set `event_request_url` in `slack/settings.json` to the service's `https://` address.
2. Merge to `main`. The run sends the address and the events in `slack/manifest.yaml`.
3. Verify the address once by hand: in the app's settings open **App Manifest** and follow
   Slack's prompt to verify the URL. The service must be answering Slack's verification
   request at that moment. Until this is done Slack delivers no events.

The pipeline does not check that the address answers.

## Credentials and when they expire

| Credential | Access | Expires |
| --- | --- | --- |
| `SLACK_CONFIG_REFRESH_TOKEN` | Create and change your Slack apps in the workspace | Replaced on every run. Whether an unused one expires is not known; the daily run keeps it in use. |
| `SLACK_STORE_TOKEN` | Write this repository's secrets and variables | On the date you chose. |

Branch runs can read both, because asking Slack to validate needs them. That is acceptable
while you are the only person who can push to this repository. If that changes, move the
Slack validation step behind a GitHub environment limited to `main`.

When `SLACK_STORE_TOKEN` has expired, runs fail with `store_failed` and the refresh token
is lost with the first such run. Renew it before the date: generate a new token as in step
2 of the first-time setup and store it.

## Recovery

Every failed run names one failure kind in its summary and says what to do. This is the
longer version.

| Failure | Starting state | What to do | End state |
| --- | --- | --- | --- |
| `invalid_definition` | The definition breaks Slack's schema, this project's rules, or Slack's validation. Nothing in Slack changed. | Fix the problems listed in the summary. | The check passes. |
| `credential_missing` | A secret or variable is not set. Slack was not contacted. | Set the one named in the summary; see the first-time setup. | The run gets further. |
| `credential_rejected` | Slack refused the refresh token. It was lost, used twice, or revoked. | Generate a new configuration token as in step 1 of the first-time setup and store its refresh token. | Runs pass again. Nothing else changes. |
| `store_failed` | A value could not be written to GitHub. Any change already made in Slack stays. | Check `SLACK_STORE_TOKEN` and its expiry. Then, by which value the summary names: for `SLACK_CONFIG_REFRESH_TOKEN`, do as for `credential_rejected`; for an app value, see "A stored value was lost" below. | All values are stored. |
| `app_not_recorded` | `SLACK_APP_ID` is not set. | Run the workflow with the action `create`. | The app exists and is recorded. |
| `app_gone` | Slack says the recorded app does not exist. | See "The app was deleted" below. | A new app is recorded and installed. |
| `app_exists` | The action `create` was run while the recorded app exists. Nothing was created. | Nothing. | Unchanged. |
| `reinstall_needed` | The installed app lacks a permission in the definition. The app was updated. | See "Adding a permission" above. | The installed app holds every permission. |
| `bot_token_rejected` | Slack refused the stored bot token. | Copy the **Bot User OAuth Token** from **OAuth & Permissions** and store it as `SLACK_BOT_TOKEN`. | Runs pass again. |
| `slack_unavailable` | Slack could not be reached, or answered with a server error or rate limit. | Run the workflow again later. The daily run retries by itself. | Runs pass again. |
| `unexpected` | Anything else. | Read the run's log. If Slack answered with an error code the program does not know, the log names it. | Depends on the cause. |

### The app was deleted

Merges and the daily run fail with `app_gone` and never create an app. The app counts as
gone only when Slack says it does not exist; an outage or a refused credential is reported
as itself.

1. Run the workflow with the action `create`. It checks with Slack that the recorded app is
   gone, creates a new one, and overwrites `SLACK_APP_ID`, `SLACK_SIGNING_SECRET`,
   `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET`.
2. Install the new app and store its bot token, as in steps 4 and 5 of the first-time setup.
3. **Update everything that used the old values.** The new app has a new ID, signing secret,
   client ID, client secret and bot token. Anything deployed with the old ones stops
   working until it is redeployed, and the event delivery address must be verified again.

If the program cannot tell that the app is gone because Slack answers with an error code it
does not know, the run fails with `unexpected`. In that case delete the variable
`SLACK_APP_ID` by hand and run `create`.

### A stored value was lost

The app still exists, but one of its values in GitHub is missing or wrong. The action
`create` refuses, because the app exists. Read the value again in the app's settings at
`https://api.slack.com/apps/<app ID>` and store it yourself:

| Value | Where in the app's settings | Store as |
| --- | --- | --- |
| App ID | **Basic Information**, **App Credentials** | Variable `SLACK_APP_ID` |
| Signing secret | **Basic Information**, **App Credentials** | Secret `SLACK_SIGNING_SECRET` |
| Client ID | **Basic Information**, **App Credentials** | Secret `SLACK_CLIENT_ID` |
| Client secret | **Basic Information**, **App Credentials** | Secret `SLACK_CLIENT_SECRET` |
| Bot token | **OAuth & Permissions** | Secret `SLACK_BOT_TOKEN` |

The same applies when the action `create` made the app but failed with `store_failed`: the
summary gives the new app's ID.

## Refreshing Slack's schema

`slack/manifest.schema.json` is an unmodified copy of
`schemas/manifest.schema.2.0.0.json` from <https://github.com/slackapi/manifest-schema> at
commit `7ec398e7edfbd2b3614c3e932c1a20c79d58177e`. It checks structure, types and lengths.
It does not know which permission and event names are real; Slack's validation does that.

If Slack accepts something the copy rejects, or the reverse, Slack is right. Replace the
file with the current version from that repository and record the new commit here.
