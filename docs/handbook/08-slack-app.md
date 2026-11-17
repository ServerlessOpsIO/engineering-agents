# The STRIDEr Slack app

STRIDEr is a Slack agent that will lead threat modeling exercises using the STRIDE
framework. This page covers the Slack app that represents STRIDEr in the `serverlessops`
workspace: how it is created, changed and repaired.

The app gives STRIDEr a name, a bot user and permissions. The service that receives
messages from Slack and replies is described in
[STRIDEr Slack messaging](09-slack-messaging.md).

Nothing on this page has been run against Slack yet. The first-time setup below is also the
first real test of the pipeline; record what happens in
`specs/006-slack-app-deployment/quickstart.md`.

## How it works

| File | Purpose |
| --- | --- |
| `slack/manifest.yaml` | The app definition: name, bot user, permissions and events. The single source of truth. |
| `slack/settings.json` | The event delivery address, `event_request_url`. |
| `slack/icon.jpg` | The app's icon. Optional; `slack/icon.png` works too. |
| `slack/manifest.schema.json` | A copy of Slack's published schema for app definitions, used by the check. |
| `scripts/slack_app/` | The program the pipeline runs around Slack's GitHub Action: `pipenv run slack-app <command>`. |
| `.github/workflows/slack-app.yml` | The `Slack app` workflow. See [CI/CD pipeline](05-ci-cd.md#the-slack-app-workflow). |

The pipeline makes the app in Slack match `slack/manifest.yaml`. **Do not change the app in
the Slack console.** A change made there is undone by the next run, at most a day later.

If `event_request_url` is emptied, the events listed in `slack/manifest.yaml` are not sent
to Slack, because Slack does not accept events without an address, and STRIDEr stops
answering. The permissions are still sent.

## First-time setup

Do this once, on `main`. It takes the workspace from having no STRIDEr app to an installed
app managed by the pipeline. Four steps are done by hand; the reason is given for each.

1. **Get the credential for changing Slack apps. By hand:** Slack only issues it to a
   signed-in person.
   1. Install the Slack CLI if you do not have it. See
      <https://docs.slack.dev/tools/slack-cli/>.
   2. Run `slack auth token`. It prints a `/slackauthticket ...` command.
   3. Paste that command into any message box in the `serverlessops` workspace and send
      it. Slack shows a challenge code; type it into the terminal.
   4. The CLI prints a **service token**. It is shown once and saved nowhere. Store it as
      the repository secret `SLACK_SERVICE_TOKEN`:

      ```bash
      gh secret set SLACK_SERVICE_TOKEN --repo ServerlessOpsIO/engineering-agents
      ```

   The token belongs to you, does not expire, and can do anything the Slack CLI can do as
   you, including changing every Slack app you own in the workspace. Treat it like a
   password. The pipeline only reads it; nothing replaces or rewrites it.

2. **Create the credential for storing values. By hand:** GitHub's built-in workflow token
   cannot write secrets, and a token that can has to be issued by a person. Only the
   `create` action uses it, to store the new app's ID and secrets.
   1. In GitHub, open **Settings**, **Developer settings**, **Personal access tokens**,
      **Fine-grained tokens**, and generate a token.
   2. Resource owner: `ServerlessOpsIO`. Repository access: only `engineering-agents`.
   3. Repository permissions: **Secrets: Read and write** and **Variables: Read and write**.
      Nothing else.
   4. Choose an expiry date and put a reminder in your calendar for a week before it.
   5. Store it as the repository secret `SLACK_GHA_STORE_TOKEN`.

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

## Running it by hand

The pipeline is the normal route. The same program can do the whole job from a checkout,
without Slack's GitHub Action, which is useful for trying a change or for the first setup:

```bash
read -s SLACK_SERVICE_TOKEN && export SLACK_SERVICE_TOKEN
export SLACK_APP_ID=<the app's ID>      # leave unset before the app exists

pipenv run slack-app check       # offline; needs no credential
pipenv run slack-app validate    # asks Slack; changes nothing
pipenv run slack-app apply       # updates the app; add SLACK_BOT_TOKEN to check permissions
```

`create` also runs by hand. It needs `SLACK_GHA_STORE_TOKEN` and `GITHUB_REPOSITORY` as well,
and writes the new app's values to GitHub, not to your machine.

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

## Changing the icon

The icon is `slack/icon.jpg` or `slack/icon.png`; keep only one. It must be a square PNG or
JPEG between 512 and 2,000 pixels on each side. `pipenv run slack-app check` checks this.

Replace the file and merge to `main`. The `apply` job uploads it every time it runs, so an
icon changed in the Slack console is also put back within a day. With no icon file, the
app's icon is left alone.

Setting the icon uses a Slack method, `apps.icon.set`, that Slack does not document; it is
the one the Slack CLI uses. If Slack changes it, the "Set the app's icon" step fails with
`unexpected` and names Slack's error. The rest of the run is not affected, except that the
permissions check after it does not run; set the icon by hand under **Basic Information**,
**Display Information**, and remove the icon file until the step is fixed.

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

The address is set: it is the receiving service's,
`https://engineering-agents.sandbox.serverlessops.io/slack/events`. These steps apply if it
is ever emptied and put back, or changed.

1. Set `event_request_url` in `slack/settings.json` to the service's `https://` address.
2. Merge to `main`. The run sends the address and the events in `slack/manifest.yaml`.
3. Verify the address once by hand: in the app's settings open **App Manifest** and follow
   Slack's prompt to verify the URL. The service must be answering Slack's verification
   request at that moment. Until this is done Slack delivers no events.

The pipeline does not check that the address answers.

## Credentials and when they expire

| Credential | Access | Expires |
| --- | --- | --- |
| `SLACK_SERVICE_TOKEN` | Anything the Slack CLI can do as you, including creating and changing your Slack apps | Never. Revoke it with `slack auth revoke --token <token>`. |
| `SLACK_GHA_STORE_TOKEN` | Write this repository's secrets and variables | On the date you chose. |

Branch runs can read `SLACK_SERVICE_TOKEN`, because asking Slack to validate needs it. Only
the `create` job is given `SLACK_GHA_STORE_TOKEN`, though any workflow run in this repository
could ask for it. That is acceptable
while you are the only person who can push to this repository. If that changes, move the
Slack validation step behind a GitHub environment limited to `main`.

An expired `SLACK_GHA_STORE_TOKEN` does not affect everyday runs. It only matters the next time
the `create` action is needed, which fails with `store_failed` until a new token is stored
as in step 2 of the first-time setup.

If the service token may have leaked, revoke it, get a new one as in step 1, and store it.
Nothing else changes: the app and its values are untouched.

## Recovery

Every failed run names one failure kind in its summary and says what to do. This is the
longer version.

| Failure | Starting state | What to do | End state |
| --- | --- | --- | --- |
| `invalid_definition` | The definition breaks Slack's schema, this project's rules, or Slack's validation. Nothing in Slack changed. | Fix the problems listed in the summary. | The check passes. |
| `credential_missing` | A secret or variable is not set. Slack was not contacted. | Set the one named in the summary; see the first-time setup. | The run gets further. |
| `credential_rejected` | Slack refused the service token. It was revoked, or is not the right kind of token. | Get a new service token as in step 1 of the first-time setup and store it. | Runs pass again. Nothing else changes. |
| `store_failed` | A value could not be written to GitHub. Any change already made in Slack stays. | Check `SLACK_GHA_STORE_TOKEN` and its expiry, then see "A stored value was lost" below. | All values are stored. |
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
