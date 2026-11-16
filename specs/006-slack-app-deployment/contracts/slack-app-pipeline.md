# Contract: Slack App Pipeline

**Date**: 2026-11-16 | **Spec**: `specs/006-slack-app-deployment/spec.md`

Three interfaces: what starts the pipeline, the commands it runs, and what the later
feature may rely on. Names and states are defined in `data-model.md`.

## 1. Workflow `.github/workflows/slack-app.yml` (`Slack app`)

### Triggers

| Trigger | When | Jobs that run |
|---|---|---|
| Push to any branch except `main` | The push changes a watched path | `check` |
| Push to `main` | The push changes a watched path | `check`, then `apply` |
| Schedule | Once a day | `apply` |
| Started by hand, `action: apply` (default) | Any time, on `main` | `check`, then `apply` |
| Started by hand, `action: create` | Any time, on `main` | `check`, then `create` |

Watched paths: `slack/**`, `scripts/slack_app/**`, `.github/workflows/slack-app.yml`.

A push that changes none of them does not start this workflow and so does not contact
Slack (FR-009). A run started by hand from any branch other than `main` runs `check` only.

### Jobs

| Job | Contacts Slack | Changes Slack | Permissions on the built-in token |
|---|---|---|---|
| `check` | Yes, when the credential is available (validate only) | Never | `contents: read` |
| `apply` | Yes | Updates the recorded app | `contents: read` |
| `create` | Yes | Creates an app | `contents: read` |
| `report` | No | Never | `issues: write` |

The workflow is in the concurrency group `slack-app`, which queues and never cancels.

`check`, `apply` and `create` each expose two job outputs taken from the command:
`failure_kind` and `failure_help`.

`report` is a separate job so that it runs when an earlier job failed or was skipped. It
needs `check`, `apply` and `create`, runs with `if: always()`, and only on `main`:

- any of the three failed and the trigger was the schedule: open an issue labelled
  `slack-app-failure` with the failure kind and what to do, or comment on the one already
  open (FR-026). If no failure kind was output, the kind is `unexpected`;
- `apply` or `create` succeeded, whatever the trigger: close every open issue with that
  label, with a comment naming the run;
- otherwise: do nothing.

### Guarantees

- No job in `branch.yml` or `main.yml` depends on, waits for, or is cancelled by this
  workflow, and the reverse (FR-012).
- No job on a branch other than `main` runs `apply` or `create` (FR-013).
- No step prints a secret. Every secret obtained during a job is masked before the next
  step (FR-018).

## 2. Command `pipenv run python scripts/slack_app <command>`

| Command | Reads | Does | Writes |
|---|---|---|---|
| `check` | The two files in `slack/` | Offline check; builds the manifest | Nothing. `--output FILE` writes the built manifest. |
| `validate` | Files; `SLACK_CONFIG_REFRESH_TOKEN`; `SLACK_APP_ID` if set | Renews the credential; asks Slack to validate the built manifest | `SLACK_CONFIG_REFRESH_TOKEN` |
| `apply` | Files; `SLACK_CONFIG_REFRESH_TOKEN`; `SLACK_APP_ID`; `SLACK_BOT_TOKEN` if set | Renews the credential; confirms the app exists; updates it; checks installed scopes | `SLACK_CONFIG_REFRESH_TOKEN` |
| `create` | Files; `SLACK_CONFIG_REFRESH_TOKEN`; `SLACK_APP_ID` if set | Renews the credential; refuses if the recorded app exists; creates the app | `SLACK_CONFIG_REFRESH_TOKEN`, `SLACK_APP_ID`, `SLACK_SIGNING_SECRET`, `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET` |

Inputs come from environment variables with the names above, plus `SLACK_STORE_TOKEN` and
`GITHUB_REPOSITORY` for writing.

### Order inside every command that contacts Slack

1. Run the offline check. Stop on failure; Slack is not contacted.
2. Renew the credential.
3. Store the new refresh token. Stop on failure.
4. Everything else.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Done. For `apply`: the app matches the definition and, if installed, holds every scope in it. Holding a scope the definition does not have is not a failure (FR-025; issue #7). |
| 1 | Failed. One failure kind from `data-model.md` is reported. |
| 2 | Wrong usage. |

`validate` on a run with no `SLACK_CONFIG_REFRESH_TOKEN` exits 0 after printing that Slack
validation was skipped.

### Output

- Lines `failure_kind=<kind>` and `failure_help=<the fixed "what to do" text for that
  kind>` in the file named by `GITHUB_OUTPUT`, when it is set, for the `report` job. Both
  come from the fixed list in `data-model.md` and never from a response.
- A human summary appended to the file named by `GITHUB_STEP_SUMMARY`, when it is set:
  what was done, the failure kind and what to do next. After `create`: the app ID and the
  link for installing the app. Never a secret.
- For `invalid_definition`: each problem with where it is in the app definition.

### Offline check rules

Fails with `invalid_definition` when any of these does not hold:

- both files parse; `slack/manifest.yaml` has the required fields within their length
  limits (`data-model.md`);
- the built manifest is valid against `slack/manifest.schema.json`, Slack's published
  schema. Each problem is reported with its place in the manifest;
- every bot scope line and every bot event line has a comment giving its reason (FR-003);
- none of the forbidden sections is present (FR-004);
- `settings.socket_mode_enabled` is not `true` (FR-005);
- `settings.event_subscriptions.request_url` is not in the app definition;
- `event_request_url` in `slack/settings.json` is empty or a valid `https://` address.

## 3. What the later feature may rely on

| It needs | It reads | Guarantee |
|---|---|---|
| The app's ID | Variable `SLACK_APP_ID` | Matches the app in Slack while the state is not "Recorded but gone". |
| To check that requests come from Slack | Secret `SLACK_SIGNING_SECRET` | The signing secret of the app `SLACK_APP_ID`. Changes only when a replacement app is created. |
| The app's OAuth client details | Secrets `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET` | Those of the app `SLACK_APP_ID`. Change only when a replacement app is created. |
| To post as STRIDEr | Secret `SLACK_BOT_TOKEN` | Present once the owner has installed the app. Holds the scopes in the app definition whenever the last `apply` passed. |
| To have Slack send events | Sets `event_request_url` in `slack/settings.json` and merges | The next `apply` sends the address and the events to Slack. The address must then be verified once by hand in the app's settings, with the receiver answering. |

It must not write any of these values, and must not call the Manifest API.

An app definition is **invalid** (SC-002) when any of these is true: the offline check
rules above fail, which include Slack's published schema; or Slack's `apps.manifest.validate`
rejects the built manifest.
