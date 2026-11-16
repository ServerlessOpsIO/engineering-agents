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
| `check` | Yes, when the credential is available (validate only, through Slack's action) | Never | `contents: read` |
| `apply` | Yes (update through Slack's action) | Updates the recorded app | `contents: read` |
| `create` | Yes | Creates an app | `contents: read` |
| `report` | No | Never | `issues: write` |

The workflow is in the concurrency group `slack-app`, which queues and never cancels, so
two updates never overlap and the later one wins.

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

### Slack's GitHub Action

`apps.manifest.validate` (in `check`), `apps.manifest.export` (in `apply` and `create`) and
`apps.manifest.update` (in `apply`) are called by `slackapi/slack-github-action`, pinned to the commit of v4.0.0, with `method`, `token`
(`SLACK_SERVICE_TOKEN`) and `payload-file-path` (the request file the program wrote). Its
`errors` input is left off, so its step passes whatever Slack answers. The next step runs
`slack-app result`, which is given only these fields of the action's `response` output:
`error`, `errors`, `statusCode`, `code` and `retryAfter`, plus the `ok` output. The whole
response is never passed to a step.

Steps in `check`: `check --payload`, the action, `result`. The last two are skipped when
`SLACK_SERVICE_TOKEN` is not available.

Steps in `apply`: `prepare --payload` (contacts nothing); the action calling
`apps.manifest.export`; `result --method apps.manifest.export`, which is also given the
returned manifest (`SLACK_ACTION_MANIFEST`), since it holds no secrets; the action calling
`apps.manifest.update`; `result --method apps.manifest.update`; `icon`; `verify`.

Steps in `create`: the action calling `apps.manifest.export`, only when `SLACK_APP_ID` is
set; then `create --existence-from-action`, which reads that answer, refuses when the app
exists, and otherwise calls `apps.manifest.create` itself and stores the app's values.

## 2. Command `pipenv run slack-app <command>`

| Command | Reads | Does | Writes |
|---|---|---|---|
| `check` | The two files in `slack/` | Offline check; builds the manifest | Nothing. `--output FILE` writes the built manifest. |
| `check --payload FILE` | Files; `SLACK_APP_ID` if set | Offline check; writes the request for the action: `{"manifest": "<the built manifest as text>", "app_id": "<if set>"}` | The request file |
| `prepare --payload FILE` | Files; `SLACK_SERVICE_TOKEN` (only to confirm it is set); `SLACK_APP_ID` | Offline check; fails when no app is recorded; writes the request. Contacts nothing | The request file |
| `result --method METHOD` | `SLACK_ACTION_OK`, `SLACK_ACTION_ERROR`, `SLACK_ACTION_ERRORS`, `SLACK_ACTION_STATUS`, `SLACK_ACTION_CODE`, `SLACK_ACTION_RETRY_AFTER` | Passes when Slack accepted the call; otherwise fails with one failure kind. For `apps.manifest.export`, also reads `SLACK_ACTION_MANIFEST` and notes when the app had drifted from the definition | Nothing |
| `icon` | Files; `SLACK_SERVICE_TOKEN`; `SLACK_APP_ID` | Uploads `slack/icon.jpg` or `slack/icon.png` with `apps.icon.set`; passes with a note when there is no icon | Nothing |
| `verify` | Files; `SLACK_BOT_TOKEN` if set | Checks the installed app's scopes | Nothing |
| `validate` (by hand) | Files; `SLACK_SERVICE_TOKEN`; `SLACK_APP_ID` if set | Asks Slack to validate the built manifest | Nothing |
| `apply` (by hand) | Files; `SLACK_SERVICE_TOKEN`; `SLACK_APP_ID`; `SLACK_BOT_TOKEN` if set | Confirms the app exists; updates it; checks installed scopes | Nothing |
| `create [--existence-from-action]` | Files; `SLACK_SERVICE_TOKEN`; `SLACK_GHA_STORE_TOKEN`; `SLACK_APP_ID` if set; with the option, the `SLACK_ACTION_*` fields for `apps.manifest.export` | Refuses if the recorded app exists, asking Slack itself or, with the option, reading the answer the action got; creates the app | `SLACK_APP_ID`, `SLACK_SIGNING_SECRET`, `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET` |

Inputs come from environment variables with the names above, plus `GITHUB_REPOSITORY` for
`create`.

### Order inside every command that contacts Slack

1. Run the offline check. Stop on failure; Slack is not contacted.
2. Read `SLACK_SERVICE_TOKEN`. It is sent to Slack as it is and is never written anywhere.
3. For `create` only: confirm `SLACK_GHA_STORE_TOKEN` is set before creating anything.
4. Everything else.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Done. For `apply`: the app matches the definition and, if installed, holds every scope in it. Holding a scope the definition does not have is not a failure (FR-025; issue #7). |
| 1 | Failed. One failure kind from `data-model.md` is reported. |
| 2 | Wrong usage. |

`validate` on a run with no `SLACK_SERVICE_TOKEN` exits 0 after printing that Slack
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
- `event_request_url` in `slack/settings.json` is empty or a valid `https://` address;
- the icon, when there is one, is a single PNG or JPEG file, square, between 512 and 2,000
  pixels on each side, and named for its format.

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
