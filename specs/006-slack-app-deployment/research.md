# Research: STRIDEr Slack App Deployment

**Date**: 2026-11-16 | **Spec**: `specs/006-slack-app-deployment/spec.md`

Each fact below is marked with how it is known:

- **Documented**: read on the named page on 2026-11-16.
- **Believed**: from the author's memory or from third-party pages. Must be checked by the
  named task during implementation, and the design says what happens if it is wrong.

Nothing in this document has been tried against Slack or GitHub.

## Facts checked

| # | Fact | Status | Source |
|---|------|--------|--------|
| F1 | An app configuration token expires 12 hours after it is issued. | Documented | Slack, "Configuring apps with app manifests"; `tooling.tokens.rotate` |
| F2 | `tooling.tokens.rotate` takes the refresh token and returns a new configuration token and a **new** refresh token. | Documented | `tooling.tokens.rotate` |
| F3 | The refresh token that was used stops working once it has been rotated. | Believed | Slack's page does not say. The `ymm-oss/terraform-provider-slackapp` README says Slack voids it and later use gives `invalid_refresh_token`. |
| F4 | Whether an unused refresh token expires. | Unknown | Not stated anywhere found. The daily run (FR-010) uses it every day, which makes the question moot unless the run is disabled. |
| F5 | A configuration token belongs to one user in one workspace and can manage all of that user's apps there. | Documented | "Configuring apps with app manifests" |
| F6 | `apps.manifest.create` returns `app_id`, `credentials` (`client_id`, `client_secret`, `verification_token`, `signing_secret`) and `oauth_authorize_url`. | Documented | `apps.manifest.create` |
| F7 | `apps.manifest.update` replaces the whole configuration, needs `app_id`, and returns `permissions_updated`. An invalid manifest is rejected with `invalid_manifest` and an `errors` list of `message` and `pointer`. | Documented | `apps.manifest.update` |
| F8 | `apps.manifest.validate` needs a configuration token. There is no way to ask Slack to validate without one. | Documented | `apps.manifest.validate` |
| F9 | `apps.manifest.export` returns the current manifest of an app; a deleted app gives `app_not_found`. | Documented (method exists); the error for a deleted app is Believed | "Configuring apps with app manifests"; error list of `apps.manifest.update` |
| F10 | Adding a scope takes effect for an existing install only after the app is installed again. | Documented | "Configuring apps with app manifests" |
| F11 | Installing an app to a workspace cannot be done by the Manifest API. It needs a person to approve it in Slack. | Believed | No method for it exists in the Manifest API; `create` returns a URL for a person to open. |
| F12 | Event subscriptions need a request URL or Socket Mode. A manifest that lists bot events with neither is invalid. | Documented (as a validation error shown on the manifests page) | "Configuring apps with app manifests" |
| F13 | A request URL set through a manifest must be verified by hand in the app's settings. | Documented | App manifest reference, `settings.event_subscriptions.request_url` |
| F14 | Every Web API response carries an `x-oauth-scopes` header listing the scopes the calling token holds. | Believed | Slack's older OAuth pages; not on the current `auth.test` page. |
| F15 | Installing an app again in the same workspace returns the same bot token when token rotation is off. | Believed | Author's memory. |
| F16 | GitHub: creating or updating a repository secret or variable needs the "Secrets" or "Variables" repository permission at write level. A fine-grained personal access token can hold these. The workflow's built-in token has no such permission. | Documented (permission and PAT); the built-in token part is Believed | GitHub, "Permissions required for fine-grained personal access tokens" |
| F17 | GitHub turns off scheduled workflows in a public repository after 60 days with no repository activity. This repository is public. | Believed | Author's memory of GitHub's documentation. |

**Corrections to the spec's assumptions**: all five "unconfirmed facts about Slack" hold as
far as the documentation goes (F1, F2, F6, F10 documented; F3 and F11 still believed). Two
things were found that the spec did not know: F12 and F13.

## Decision 12: The pipeline credential is a Slack CLI service token (2026-11-16)

**This replaces Decisions 2 and 4 and narrows Decision 3. Facts F1 to F4 no longer matter
to the design.** Those sections are kept below as the record of what was first built.

**Decision**: The pipeline authenticates to Slack with a service token, obtained once by
the owner with `slack auth token` and stored as the repository secret
`SLACK_SERVICE_TOKEN`. The program sends it unchanged to the same four Manifest API methods
and never writes it.

**Why it changed**: After the first implementation the owner asked whether the rotating
refresh token was needed and chose a service token. Slack's documentation describes
service tokens as "long-lived, non-rotatable user tokens" that "won't expire". The Slack
CLI's source (`internal/api/app.go`) shows the CLI sends its own token to
`apps.manifest.create`, `export`, `update` and `validate`, which is why one was expected to
work here.

**What it removes**: renewing on every run; writing a secret on every run; the failure in
which a renewed token is lost before it is stored; the need for runs never to overlap for
the credential's sake; `SLACK_GHA_STORE_TOKEN` in every job but `create`.

**What it costs**: a permanent credential that can do anything the Slack CLI can as the
owner, where the earlier design had one that changed on every run. It is readable by
branch runs (Decision 5). If it may have leaked: `slack auth revoke --token`, then issue
and store a new one.

**Checked**: on 2026-11-16 the owner ran `pipenv run slack-app validate` with a service
token and it passed, so `apps.manifest.validate` accepts one. `export`, `update`, `create`
and `auth.test` have not been tried with it.

## Decision 13: Slack's GitHub Action makes the validate and update calls (2026-11-16)

**Decision**: `slackapi/slack-github-action` v4.0.0, pinned to its commit, calls
`apps.manifest.validate` and `apps.manifest.update` with its `method` input and the service
token. The program keeps everything else and can still do the whole job by hand.

**Why this route and not the action's Slack CLI commands**: Slack documents
`manifest validate` and `deploy` through the CLI for this action, but what `deploy` does to
an app that is not hosted by Slack was not established, and the CLI expects a project
layout this repository does not have. Calling the API methods through the action avoids
both questions.

**Read from the action's source on 2026-11-16** (`src/client.js`, `src/send.js`): the
`ok` and `response` outputs are set whether the call succeeds or fails; with `errors` left
off, a failed call is a warning and the step passes; the token is registered as a secret;
the request content is only printed in debug logging.

**What stays in the program, and why**:

- The offline check and build: the action knows nothing of this project's rules.
- Confirming the app exists before an update (`apps.manifest.export`): keeps "deleted"
  apart from "unreachable" (FR-024).
- Reading the answer: gives a failure kind and the text for the failure issue (FR-011,
  FR-026).
- The installed-permissions check: needs a response header the action does not return.
- Creating the app: Slack's answer holds the signing secret and client secret, and the
  action exposes the whole answer as a step output that cannot be masked first.

**Secrets**: the Slack CLI's source suggests an update's answer may also hold credentials
(`UpdateAppResult` has a `Credentials` field, marked for removal). A step's `env` is shown
in its log, and this repository's logs are public, so the workflow passes on only the error
fields of the answer, selected with expressions, and never the whole answer. Debug logging
would still print the output, so the handbook says not to enable it for this workflow.

**Extended on 2026-11-16**: the check that the recorded app exists
(`apps.manifest.export`) now also goes through the action, in both `apply` and `create`.
Its answer is the app's manifest, which holds no secrets, so it is the one answer passed on
whole. The program still decides what the answer means. After this the program's own calls
to Slack in the pipeline are `apps.manifest.create` and `auth.test`.

**Tried**: `apps.manifest.validate` through the action passed on the feature branch on
2026-11-16, with the service token.

**Not tried**: `export` and `update` through the action have not run; they only run on `main`. The expressions that pick fields
out of its output have not been linted or run. The first branch push tests `validate`; the
first run on `main` tests `update`.

## Decision 1: Call Slack's Manifest API directly; do not use Terraform (FR-022)

**Decision**: A small Python program in this repository calls the Manifest API. The pipeline
runs it.

**Comparison**:

| | Direct Manifest API calls | Terraform with a community provider |
|---|---|---|
| What exists | Five documented methods (`create`, `update`, `validate`, `export`, `delete`) plus `tooling.tokens.rotate`. | `ymm-oss/slackapp` (was `yumemi-inc/slackapp`; 18 stars, v0.4, GPL-3.0) and `change-engine/slack-app` (10 stars, MPL-2.0, no releases listed on GitHub). No official provider. |
| State | None. The app ID is one stored value. | Needs a remote state store. That is a new cloud resource, which FR-019 forbids in this feature, or state committed to a public repository, which is not acceptable. |
| Secrets | Signing secret goes straight to the secret store. | Anything the provider returns is written into state in plain text. |
| Token renewal | We write it: rotate, store, then act. About 30 lines. | `ymm-oss` needs a "token store" program that we would write anyway to put the refresh token in GitHub secrets; without one it works for a single run. `change-engine` does not document how it handles renewal. |
| Create only on a hand-started run (FR-023, FR-024) | Natural: `create` and `update` are different calls. | Against Terraform's model. `apply` creates whatever is missing, so a deleted app would be recreated silently unless guarded outside Terraform. |
| Fail until reinstalled (FR-025) | A further check in the same program. | Outside what either provider does; needs a separate program anyway. |
| Validation on branches (FR-007) | `apps.manifest.validate`. | `terraform plan` does not ask Slack to validate; `ymm-oss` builds the manifest locally. |
| Fit with this organization | Python is already here; no new tool. | No Terraform is used in this repository or its templates. |
| Risk | We maintain about 300 lines and their tests. | Dependence on a small project for the one credential that can change the app. |

**Rationale**: Terraform's main benefits are state and a plan. Here there is one resource,
its state is one ID, and three of the owner's clarified requirements (FR-023, FR-024,
FR-025) need custom code around Terraform in any case. Terraform would add a state store
this feature is not allowed to create, and would put the signing secret in it.

**Alternatives considered**: the Slack CLI (`slack deploy`) is aimed at apps hosted by
Slack and logs in interactively; not suited to a pipeline for this kind of app.

## Decision 2 (superseded by Decision 12): The pipeline credential is the refresh token alone, renewed on every run

**Decision**: Store only the refresh token (`SLACK_CONFIG_REFRESH_TOKEN`). Every job that
contacts Slack first calls `tooling.tokens.rotate`, immediately stores the new refresh
token, and only then does anything else. The 12-hour configuration token is used within
the job and never stored.

**Rationale**: One value to store instead of two. Storing right after rotating keeps the
window in which the only valid refresh token exists solely in the job's memory as short as
possible (FR-015). The daily run keeps the refresh token in use (F4).

**If F3 is wrong** (old refresh tokens keep working): nothing breaks; storing is harmless.

**Failure this cannot remove**: if the job dies between rotating and storing, the stored
refresh token is dead. The store step is retried three times; if it still fails the job
fails with the recovery steps (owner issues a new configuration token in Slack and stores
its refresh token). Documented under Recovery in the handbook.

**Alternatives considered**: storing the configuration token too and rotating only when it
is close to expiry. Fewer rotations, but two secrets to write and a second way to be out of
step. Rejected.

## Decision 3: Values are stored in GitHub repository secrets and variables, written with a fine-grained token

**Decision**: Repository-level secrets and variables (not environment-level), so the later
feature's deploy job can read them however it is arranged. Writing them from a workflow uses
a fine-grained personal access token limited to this repository with "Secrets: write" and
"Variables: write" (F16), stored as `SLACK_GHA_STORE_TOKEN`. Values are written with the `gh`
command, which does the encryption GitHub requires.

**Rationale**: The owner chose GitHub secrets as the starting point. A fine-grained token is
the smallest thing that works. Nothing on the cloud platform is created.

**Cost**: one more credential that can expire. Its expiry date goes in the handbook, and an
expired token produces a named failure.

**Alternatives considered**: a GitHub App (no expiry to manage, but an app to register and a
key to keep; too much for one repository). A secret in the cloud platform's secret store
(needs a resource; FR-019). An organization-level secret (wider than needed).

## Decision 4 (superseded by Decision 12): Runs that contact Slack never overlap

**Decision**: Every job that contacts Slack is in one concurrency group, `slack-app`, that
queues and does not cancel.

**Rationale**: Two rotations at once would each use the same refresh token and one would
lose (F3). Queuing also makes "the later merge wins" true for the edge case of two merges
close together.

**After Decision 12**: runs still queue in one concurrency group, now only so that two
updates to the app do not overlap and the later one wins.

## Decision 5: Branches are checked twice: without Slack, then by Slack

**Decision**: On a branch push that touches the Slack files:

1. An offline check that needs no credential: the file parses, required fields and length
   limits hold, the project's own rules hold (FR-003, FR-004, FR-005), and the built
   manifest is produced.
2. `apps.manifest.validate` against Slack, which needs the pipeline credential (F8) and
   therefore a rotation.

Neither changes the Slack app. A run without access to the credential (the fork edge case)
does step 1, reports that step 2 was skipped, and passes or fails on step 1 alone.

**Rationale**: Only Slack knows whether a scope name is real; the spec's own test for User
Story 2 is an unknown permission, so step 2 is needed. Step 1 gives an answer when the
credential is unavailable and catches the project's rules, which Slack does not know.

**Trade-off accepted**: branch runs can read the pipeline credential and the store token.
Only people who can push to this repository can run them; today that is the owner. If
others gain push access, move step 2 behind an environment limited to `main`.

**Slack's published schema** (added 2026-11-16, at the owner's question): Slack publishes
JSON schemas for app manifests at `slackapi/manifest-schema` (MIT licence, maintained by
Slack, last changed 2026-11-16). Step 1 validates the built manifest against a copy of
version 2.0.0 kept in the repository, using the `jsonschema` package as a development
dependency. Read on 2026-11-16, the schema checks structure, types, lengths and unknown
fields, but scope and event names are plain strings of at most 50 characters, and it has no
rule that events need a request URL. So it cannot catch an unknown permission, and step 2
is still needed. Its README says it is meant for editors; whether Slack's own validation
uses the same schema, and which version applies to a manifest with no `_metadata`, are not
known. If the copy and Slack disagree, Slack is right and the copy is refreshed.

## Decision 6: A separate workflow file

**Decision**: A new workflow, `.github/workflows/slack-app.yml`, triggered by pushes that
change the Slack files, by a daily schedule, and by hand. `branch.yml` and `main.yml` are
not edited.

**Rationale**: FR-012 wants independence in both directions. Two workflows cannot block
each other, cannot slow each other, and a failure names itself by workflow. Path filters
at workflow level give FR-009 (no contact with Slack on unrelated merges) for free.

**Reading of "the run as a whole shows as failed"**: the commit shows a failed check if
either workflow fails. They are two runs, not one. This is the author's reading of the
owner's answer and is flagged in the plan.

**Consequence**: the existing workflows ignore `specs/**` and `docs/**` only, so a merge
that changes only the Slack files still starts an agent build and deployment, as any other
code change does today. Not changed here, because FR-012 says not to alter their behaviour.

## Decision 7: The app definition is YAML; events are left out until there is an address

**Decision**: `slack/manifest.yaml` is the app definition. `slack/settings.json` holds the
event delivery address, empty for now. A build step produces the JSON sent to Slack:

- address empty: the `settings.event_subscriptions` block is left out;
- address set: the block is included with the address.

The events are always listed in `slack/manifest.yaml`; only the built output differs.

**Rationale**: F12 makes a manifest with events and no address invalid, so the events
cannot be sent yet. Keeping them in the source file means supplying the address later is a
one-line change to `slack/settings.json` (FR-006). YAML allows a reason beside every scope
and event (FR-003), which the offline check enforces.

**Resolves the spec's open edge case** (address set, nothing listening): by F13 Slack
accepts the address but treats it as unverified until someone verifies it in the app's
settings, which needs the receiver to be answering. The pipeline applies the manifest and
does not check that the address answers. Verifying the address is a manual step that
belongs to the later feature; the handbook records it so that feature does not rediscover
it.

**Consequence for this feature**: until the later feature, the Slack app has scopes but no
event subscriptions. STRIDEr appears in the workspace and receives nothing, which is the
expected state (spec, Assumptions).

## Decision 8: Scopes and events

**Decision**:

| Entry | Kind | Needed for |
|---|---|---|
| `app_mentions:read` | bot scope | Being told when someone mentions STRIDEr in a channel. |
| `chat:write` | bot scope | Posting replies. |
| `im:history` | bot scope | Reading direct messages sent to STRIDEr. |
| `channels:history` | bot scope | Reading replies in a thread in a public channel that do not mention STRIDEr. |
| `groups:history` | bot scope | The same in a private channel. |
| `app_mention` | bot event | Mentions. |
| `message.im` | bot event | Direct messages. |
| `message.channels` | bot event | Thread replies in public channels. |
| `message.groups` | bot event | Thread replies in private channels. |

The messages tab of the app's home is enabled, and the home tab is disabled. Slack only
lets people send a direct message to an app when the messages tab is on. FR-004 excludes an
app home page; the messages tab is the direct message conversation itself, not a page, and
is required by FR-002.

**Decided by the owner, 2026-11-16**: a thread reply need not mention STRIDEr, so both
history scopes and both message events stay. The paragraph below records the cost.

`channels:history` and `groups:history` let STRIDEr read every
message in any channel it has been added to, not only threads it is in. Slack has no
narrower permission for "replies in threads I am part of". The alternative is to require a
mention in every thread reply and drop both scopes and both events. The plan follows the
spec (FR-002) and keeps them; this is the least-privilege cost of that requirement.

Group direct messages are not included; the owner did not ask for them.

## Decision 9: How "must be installed again" is detected (FR-025)

**Decision**: After applying, the job calls `auth.test` with the stored bot token and reads
the `x-oauth-scopes` response header (F14). If any scope in the app definition is missing
from it, the job fails with the reinstall instructions. With no bot token stored, the app
has never been installed: the job says so in its summary and passes (spec, Assumptions).

**Removed scopes**: a scope the bot token holds that the definition does not have is not a
failure (owner's decision, 2026-11-16). What Slack does to an installed app when a scope is
removed is not known and is tracked in issue #7.

**If F14 is wrong**: fall back to `permissions_updated` from `apps.manifest.update` (F7).
That only tells the merge run, not later scheduled runs, so FR-025's "keep failing" would
need a stored flag. In that case the requirement goes back to the owner, as the spec says.
A task checks F14 early.

**If F15 is wrong** (reinstalling issues a new bot token): the stored token stops working,
`auth.test` fails with `invalid_auth` or `token_revoked`, and the job reports "bot token is
no longer valid; store the new one". The failure message for FR-025 already tells the owner
to check the token.

## Decision 10: Failure reporting (FR-026)

**Decision**: A separate `report` job runs after the others whatever their result. When
any job of a scheduled run failed, it opens an issue labelled `slack-app-failure`, or adds
a comment to the open one. When `apply` or `create` succeeded, it closes open issues with
that label. It is a job of its own because a step inside `apply` would not run when
`check` fails first and `apply` is skipped (found in analysis, 2026-11-16). The built-in workflow token with
`issues: write` is enough. GitHub's own notification goes to the owner as long as their
notification settings include failed Actions runs; the handbook says which setting.

**Constraint**: this repository is public, so issues and logs are public. Issue text is
built from a fixed list of failure kinds and never from a raw response. Every secret value
obtained during a job is masked before any further step.

**F17**: a scheduled workflow in a quiet public repository is switched off after 60 days.
GitHub emails the owner before doing so. The handbook says how to switch it back on. The
auto-closing issue cannot report this, because nothing runs.

## Decision 11: Language, layout and tests

**Decision**: Python 3.14, the standard library for HTTP, and PyYAML as a new development
dependency for reading the app definition. Code in `slack/` beside the definition. Unit
tests in `tests/unit/` with Slack and GitHub replaced by fakes; no test contacts either.

**Rationale**: Matches the repository. PyYAML is a development dependency, so it is not
installed in the agent's image.

## Open items for implementation

| Item | Checked by |
|---|---|
| F3, F9 (error for a deleted app), F12, F14, F15 | Tasks that make one real call each during first-time setup and record the result in this file. |
| If F9 is wrong (a deleted app gives some other error) | `apply` reports `unexpected` instead of `app_gone`, and the creation run cannot tell that the app is gone, so it refuses. Fix: map the real error code to `app_gone`. Until then the owner clears `SLACK_APP_ID` by hand before starting the creation run. |
| If F12 is wrong (Slack accepts events with no address) | Nothing breaks. Holding events back is then unnecessary but harmless, and Decision 7 can be simplified. |
| F16 (built-in token cannot write secrets) | Not checked; the design does not depend on it being false. |
| F17 | Not checked; documented as a risk. |
| What Slack does to an installed app when a scope is removed from its manifest | Issue #7, during quickstart H step 4. |
| Whether `apps.manifest.export` output can be compared with the built manifest to report drift | Tried during implementation. If Slack adds defaults that make them always differ, drift is undone but not reported. FR-010 only requires undoing. |

## Sources

- Slack: Configuring apps with app manifests — https://docs.slack.dev/app-manifests/configuring-apps-with-app-manifests
- Slack: App manifest reference — https://docs.slack.dev/reference/app-manifest
- Slack: `apps.manifest.create` — https://docs.slack.dev/reference/methods/apps.manifest.create
- Slack: `apps.manifest.update` — https://docs.slack.dev/reference/methods/apps.manifest.update
- Slack: `apps.manifest.validate` — https://docs.slack.dev/reference/methods/apps.manifest.validate
- Slack: `tooling.tokens.rotate` — https://docs.slack.dev/reference/methods/tooling.tokens.rotate
- Slack: `auth.test` — https://docs.slack.dev/reference/methods/auth.test
- GitHub: Permissions required for fine-grained personal access tokens — https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens
- GitHub: REST API endpoints for GitHub Actions secrets — https://docs.github.com/en/rest/actions/secrets
- Slack: manifest schema — https://github.com/slackapi/manifest-schema
- Slack CLI: authorizing the CLI (service tokens) — https://docs.slack.dev/tools/slack-cli/guides/authorizing-the-slack-cli
- Slack CLI source — https://github.com/slackapi/slack-cli
- Slack's GitHub Action — https://github.com/slackapi/slack-github-action
- Terraform provider `ymm-oss/slackapp` — https://github.com/yumemi-inc/terraform-provider-slackapp
- Terraform provider `change-engine/slack-app` — https://github.com/change-engine/terraform-provider-slack-app
