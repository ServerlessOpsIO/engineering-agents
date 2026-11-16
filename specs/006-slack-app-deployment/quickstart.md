# Quickstart: Validating the STRIDEr Slack App Deployment

**Date**: 2026-11-16 | **Spec**: `specs/006-slack-app-deployment/spec.md`

How to prove the feature works. Scenarios A and B need nothing but a checkout. The rest
need the `serverlessops` Slack workspace and this repository on GitHub, and can only be run
by the owner. Commands and states are defined in `contracts/slack-app-pipeline.md` and
`data-model.md`.

Record the result of each scenario at the end of this file when it is run.

## Prerequisites

- `pipenv install --dev`
- For C onward: admin of the `serverlessops` workspace; able to set secrets and variables
  on `ServerlessOpsIO/engineering-agents`; the `gh` command signed in.

## A. Unit tests (no Slack, no GitHub)

```bash
pipenv run test-unit
```

Expected: all tests pass, including those for the offline check, the build with and
without an address, each app state, and each failure kind.

## B. Offline check (US2, US5)

```bash
pipenv run slack-app check --output /tmp/manifest.json
```

Expected: exit 0; the built manifest has no `event_subscriptions`.

Then, without committing:

1. Remove the comment from one scope line. Expected: exit 1, `invalid_definition`, the
   line named.
2. Add a `features.slash_commands` section. Expected: exit 1.
   Add an unknown top-level field, `colour: blue`. Expected: exit 1, reported by the
   schema check with its place.
3. Set `event_request_url` to `https://example.com/slack/events` in `slack/settings.json`.
   Expected: exit 0; the built manifest has `event_subscriptions` with that address and
   the four events (FR-006, SC for US5).
4. Set it to `http://example.com`. Expected: exit 1.

Restore both files.

## C. First-time setup (US3, US4; SC-004 to SC-008)

Follow `docs/handbook/08-slack-app.md`, "First-time setup", from the top, timing it.

Expected:

- The creation run passes. Its summary shows an app ID and an install link, and no secret.
- Variable `SLACK_APP_ID` and secrets `SLACK_SIGNING_SECRET`, `SLACK_CLIENT_ID` and
  `SLACK_CLIENT_SECRET` exist.
- After installing and storing `SLACK_BOT_TOKEN`: STRIDEr is listed in the workspace's
  apps with the name and the five scopes in the app definition.
- Starting the workflow by hand with `action: apply` passes.
- The whole thing took under 30 minutes, and installing the app was the only step that
  exists only because it cannot be automated.

Then start the creation run again. Expected: fails with `app_exists`; no second app in
Slack (FR-023).

## D. A change reaches Slack by merging (US1; SC-001)

1. On a branch, change `display_information.description`. Push.
   Expected: `Slack app` runs `check` only and passes; the description in Slack is
   unchanged.
2. Merge to `main`. Expected: `apply` passes; the description in Slack has changed within
   10 minutes.

## E. A bad definition is stopped on the branch (US2; SC-002)

On a branch, add the scope `not:a:scope` with a comment. Push.

Expected: `check` fails with `invalid_definition` from Slack, naming the scope. The Slack
app is unchanged. Delete the branch.

## F. Unrelated merges do not contact Slack (SC-003)

Merge a change that touches none of the watched paths. Expected: no `Slack app` run exists
for that commit.

## G. Hand-made changes are undone (SC-009)

In the Slack console, change the app's description. Start the workflow by hand with
`action: apply` (standing in for the daily run), or wait a day.

Expected: the description matches the app definition again.

## H. Adding a permission (FR-025; SC-001)

1. Merge a change adding the scope `reactions:read` with a comment.
   Expected: `apply` updates the app, then fails with `reinstall_needed`.
2. Start `action: apply` by hand. Expected: fails the same way.
3. Install the app again as the handbook says. Start `action: apply`.
   Expected: passes.
4. Merge a change removing the scope. Expected: passes. Record for issue #7 what
   `apps.manifest.update` returned and whether the installed app still holds the scope.

## I. Scheduled failure is reported (FR-026; SC-012)

Needs a scheduled run to fail. Simplest: during H step 1, wait for the next daily run
before reinstalling.

Expected: one issue labelled `slack-app-failure` is opened, with the failure kind and what
to do. A second failed daily run adds a comment and does not open a second issue. After
reinstalling, the next passing run closes the issue.

A failure before the apply step must be reported too. This is covered by reading the
workflow (the `report` job needs all three jobs and runs with `if: always()`); it is only
tried for real if a scheduled run happens to fail that way.

## J. Independence from the agent pipeline (FR-012)

During H step 1, the same merge also starts `Main`. Expected: `Main` builds and deploys
the agent as usual while `Slack app` fails; the commit shows one failed and one passed
workflow.

## K. Nothing secret, nothing on the cloud platform (SC-008, SC-011)

```bash
git diff main...HEAD --stat -- template.yaml cfn-parameters.json
```

Expected: no output.

Search the repository and the logs and summaries of every `Slack app` run made above, and
the text of every `slack-app-failure` issue and every pull request, for the values of the
Slack secrets.
Expected: none found.

## Not validated here

- SC-010 (ten runs in a row without touching a credential): met by the daily run
  over the ten days after setup. Check the workflow's history then.
- A deleted app (`app_gone`): covered by unit tests. Deleting the real app is destructive
  and is only tried if the owner chooses to.
- A refused service token (`credential_rejected`): covered by unit tests and the handbook's
  recovery steps.

## Results

**2026-11-16, on the feature branch, before merging. Run by the author; nothing here
contacted Slack or GitHub.**

| Scenario | Result |
|---|---|
| A. Unit tests | Passed. 147 tests after the move to a service token: 18 that existed before and 129 new. |
| B. Offline check | Passed. The committed files exit 0 and the built manifest has no `event_subscriptions`. A scope with no comment, a `slash_commands` section, an unknown top-level field and an `http://` address each exit 1 with `invalid_definition` and name the place. With `https://example.com/slack/events` set, the built manifest has that address and the four events. Run in a scratch copy; the repository's files were not changed. |
| K. Nothing on the cloud platform | `template.yaml`, `cfn-parameters.json`, `main.yml` and `branch.yml` are unchanged against `main`. The search for secrets has not been done; there are no runs or issues yet. |
| C to J | Not run. They need the workflow on `main`, the Slack workspace and the repository's settings, and are the owner's tasks T028 to T030, T033 and T039 to T041. |

**2026-11-16, later.** The `Slack app` workflow ran once on the feature branch and passed;
only `check` runs on a branch. The owner then ran `pipenv run slack-app validate` locally
with a Slack CLI service token and it passed: Slack's validation accepts a service token
and accepts the built manifest. `apply`, `create` and `report` have still never run.

**2026-11-16, later still.** The validate and update calls were moved to Slack's GitHub
Action. 176 unit tests pass. The workflow file parses as YAML; it has not been linted, and
the action has not run in it. Scenario E (a bad definition stopped on the branch) and
scenario D (a change reaching Slack) are now also the tests of the action steps.
