# Tasks: STRIDEr Slack App Deployment

**Input**: Design documents from `/specs/006-slack-app-deployment/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/slack-app-pipeline.md, quickstart.md

**Tests**: Included. The plan calls for unit tests with Slack and GitHub replaced by fakes;
no test contacts either service.

**Organization**: Tasks are grouped by user story. All paths are in this repository
(`engineering-agents`). Tasks marked **(owner)** need the `serverlessops` Slack workspace
or this repository's settings on GitHub and can only be done by the project owner.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`[US1]` to `[US5]`)
- Every task names a file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Bring the spec into line with what research found, and prepare the project
for the new code.

- [X] T001 Update `specs/006-slack-app-deployment/spec.md` so it agrees with the research, changing wording only and no decision: FR-007 (pushes that change the Slack files are checked, not every push); FR-006, SC-006 and User Story 5 (events are held back until an address is set; the address must then be verified by hand in the later feature); FR-004 (the messages tab is allowed, the home tab is not); FR-012 (two runs on one commit; the commit shows a failed check); SC-005 and FR-020 (list every setup step done by hand: Slack configuration token, GitHub token, install, bot token); Edge Cases (the unlistened-address case is resolved); Assumptions (which Slack facts are now documented and which are still believed). Do not change FR-002, FR-025, FR-026 or the Clarifications; the owner decided those on 2026-11-16. Also make these changes from the checklist review of 2026-11-16 (`specs/006-slack-app-deployment/checklists/deployment.md`): FR-008 and FR-009 (define "its settings" as the files the pipeline watches: `slack/**`, `scripts/slack_app/**` and the Slack workflow file) (CHK007); FR-012 (remove "and MUST add no more time to them than is needed") (CHK013); FR-013 and FR-015 (a branch run may renew and store the pipeline credential and may read it; this is accepted while the owner is the only person who can push, and must be revisited if that changes) (CHK017, CHK036); SC-012 (replace "exactly one open issue for its cause" with "exactly one open issue while scheduled runs are failing") (CHK023); FR-014 (every credential the pipeline holds, including the one for writing repository secrets, MUST have only the access this feature needs, and the documentation MUST say when each expires and what a run does when it has) (CHK001, CHK035); FR-018 (no secret value may appear in an issue or a pull request either; the hosting service masks stored secrets in logs, and any secret obtained during a run MUST be masked before anything else is printed) (CHK005, CHK037); Edge Cases (add: the app exists but a stored app value has been lost, with the creation run refusing and the documentation saying where the owner reads the value again in Slack; and say that "fails to store an updated value" means the renewed pipeline credential, the app ID or the signing secret, that the change already made in Slack is left in place, and that the run fails) (CHK030, CHK032); Key Entities (the event delivery address is a setting kept beside the app definition, not in it; the pipeline credential is replaced each time it is renewed). Also make these changes the owner decided on 2026-11-16, and record each as an entry in the Clarifications section: the app's client ID and client secret are app values, stored as secrets by the creation run for the later feature's deployment to refer to, so update the App values term, FR-016, User Story 4, SC-007 and Key Entities from three values to five (CHK003); removing the Slack app and retiring STRIDEr are out of scope (CHK004); FR-024 MUST treat the app as gone only when Slack says it does not exist, and MUST report Slack being unreachable or the credential being refused as those failures and not as a deleted app (CHK012); SC-002 defines an invalid app definition as one that fails Slack's published manifest schema, fails this project's own rules, or is rejected by Slack's validation (CHK021); FR-025 or a new requirement beside it: when Slack refuses the stored bot token, the run MUST fail saying the stored bot token is no longer valid and must be stored again, and MUST NOT report it as a missing permission (CHK028)
- [X] T002 Add `pyyaml` and `jsonschema` to `[dev-packages]` in `Pipfile`, each with a pinned version, and regenerate `Pipfile.lock` with `pipenv lock`
- [X] T003 [P] Add `scripts` to `pythonpath` in `pytest.ini` so tests can import `slack_app`
- [X] T004 Create the package `scripts/slack_app/` with `__init__.py` defining the failure kinds exactly as listed in `specs/006-slack-app-deployment/data-model.md` ("Failure kinds": `invalid_definition`, `credential_missing`, `credential_rejected`, `store_failed`, `app_not_recorded`, `app_gone`, `app_exists`, `reinstall_needed`, `bot_token_rejected`, `slack_unavailable`, `unexpected`), a `SlackAppError` exception carrying one kind and a list of details, and for each kind the fixed "what to do" text from that table

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The app definition, the build, and the two clients every command uses.

**⚠️ CRITICAL**: No user story can be completed until this phase is done.

- [X] T005 [P] Create `slack/manifest.yaml` per `specs/006-slack-app-deployment/data-model.md` ("App definition"): `display_information.name` `STRIDEr` (at most 35 characters) and a `description` (at most 140 characters); `features.bot_user.display_name` `STRIDEr` (at most 80 characters), `always_online: true`; `features.app_home` with `home_tab_enabled: false`, `messages_tab_enabled: true`, `messages_tab_read_only_enabled: false`; `oauth_config.scopes.bot` with exactly `app_mentions:read`, `chat:write`, `im:history`, `channels:history`, `groups:history`; `settings.event_subscriptions.bot_events` with exactly `app_mention`, `message.im`, `message.channels`, `message.groups`; `settings.socket_mode_enabled: false`, `org_deploy_enabled: false`, `token_rotation_enabled: false`. Put the reason from research Decision 8 as a comment on every scope line and every event line. Do not include `request_url`
- [X] T006 [P] Create `slack/settings.json` containing `{"event_request_url": ""}`, and add `slack/manifest.schema.json` as an unmodified copy of `schemas/manifest.schema.2.0.0.json` from `https://github.com/slackapi/manifest-schema` at commit `7ec398e7edfbd2b3614c3e932c1a20c79d58177e`
- [X] T007 [P] Write tests in `tests/unit/test_slack_definition.py` for the offline check and the build: the committed files pass; each rule in `specs/006-slack-app-deployment/contracts/slack-app-pipeline.md` ("Offline check rules") fails with `invalid_definition` and names the place (a manifest that breaks `slack/manifest.schema.json`, for example an unknown top-level field or a scope list that is not a list; missing required field, name over 35 characters, description over 140, display name over 80, scope or event line without a comment, each forbidden section, `socket_mode_enabled: true`, `request_url` in the definition, address that is not `https://` or is over 3,500 characters); with an empty address the built manifest has no `settings.event_subscriptions`; with an address it has `request_url` and the four events; the same inputs give byte-identical JSON with sorted keys
- [X] T008 Implement `scripts/slack_app/definition.py`: read `slack/manifest.yaml` and `slack/settings.json`, run the offline check including validating the built manifest against `slack/manifest.schema.json` with `jsonschema` and reporting each problem with its place, and build the manifest JSON, so that the tests in T007 pass
- [X] T009 [P] Write tests in `tests/unit/test_slack_api.py` using a fake HTTP layer: `rotate` returns the new configuration token and new refresh token; `validate`, `export`, `update`, `create` send the built manifest as a JSON string and the app ID where the method takes one; `auth_test_scopes` returns the scopes from the `x-oauth-scopes` response header; Slack errors map to failure kinds (`invalid_manifest` with its `errors` list to `invalid_definition`; `invalid_refresh_token`, `token_expired`, `token_revoked`, `invalid_auth` on a configuration call to `credential_rejected`; `app_not_found` to `app_gone`; `invalid_auth` or `token_revoked` on `auth.test` to `bot_token_rejected`; `ratelimited`, `service_unavailable`, `internal_error`, `fatal_error`, `request_timeout`, HTTP 5xx and connection errors to `slack_unavailable`; anything else to `unexpected`); no token appears in any exception message
- [X] T010 Implement `scripts/slack_app/slack_api.py` with the standard library only: `rotate`, `validate`, `export`, `update`, `create`, `auth_test_scopes`, and the error mapping, so that the tests in T009 pass
- [X] T011 [P] Write tests in `tests/unit/test_slack_store.py` using a fake command runner: a secret is written with `gh secret set NAME --repo REPO` with the value passed on standard input and never as an argument; a variable is written with `gh variable set`; `GH_TOKEN` for the command is `SLACK_STORE_TOKEN`; a failed write is retried up to three times and then raises `store_failed`; a missing `SLACK_STORE_TOKEN` raises `credential_missing`; `mask` prints `::add-mask::VALUE` once per value
- [X] T012 Implement `scripts/slack_app/store.py`: `set_secret`, `set_variable` and `mask`, so that the tests in T011 pass
- [X] T013 Implement in `scripts/slack_app/__main__.py` the argument parsing for `check`, `validate`, `apply` and `create`, exit codes 0, 1 and 2, writing `failure_kind=<kind>` and `failure_help=<the fixed "what to do" text for that kind>` to the file named by `GITHUB_OUTPUT` and a summary to the file named by `GITHUB_STEP_SUMMARY` when they are set, and the shared sequence for commands that contact Slack from `specs/006-slack-app-deployment/contracts/slack-app-pipeline.md` ("Order inside every command that contacts Slack"): offline check, renew, mask both new tokens, store the new refresh token, then the command's own work
- [X] T014 Implement the `check` command in `scripts/slack_app/__main__.py`, with `--output FILE` writing the built manifest, and add `slack-app = "python scripts/slack_app"` to `[scripts]` in `Pipfile`

**Checkpoint**: `pipenv run test-unit` passes and `pipenv run slack-app check` exits 0 (quickstart A and B).

---

## Phase 3: User Story 1 - A change to the app definition reaches Slack by merging (Priority: P1) 🎯 MVP

**Goal**: A merge to `main` that changes the Slack files updates the recorded app; a daily
run undoes hand-made changes; a missing permission fails the run until the app is
installed again; failed scheduled runs are reported.

**Independent Test**: Quickstart D, G, H, I and J. They need the app to exist, so they are
run after Phase 5.

### Tests for User Story 1

- [X] T015 [US1] Write tests in `tests/unit/test_slack_commands.py` for `apply` with all three clients faked, one per row of the states table in `specs/006-slack-app-deployment/data-model.md`: no `SLACK_APP_ID` fails with `app_not_recorded` and calls neither `update` nor `create`; `export` failing with `slack_unavailable` or `credential_rejected` fails with that kind and never with `app_gone`; `export` answering `app_not_found` fails with `app_gone` and calls neither; app exists and no `SLACK_BOT_TOKEN` updates, passes and says the app is not installed; installed with every scope held updates and passes; installed with a scope missing updates and then fails with `reinstall_needed` naming the missing scope; a scope the bot token holds that the definition does not have passes (FR-025; issue #7); a rejected bot token fails with `bot_token_rejected`. Also: the new refresh token is stored before `export` or `update` is called; if storing fails nothing else is called; no secret value appears in standard output, the summary file or the output file

### Implementation for User Story 1

- [X] T016 [US1] Implement the `apply` command in `scripts/slack_app/__main__.py`: confirm the recorded app exists with `export`, send the built manifest with `update`, then compare the definition's bot scopes with `auth_test_scopes` when `SLACK_BOT_TOKEN` is set, so that the tests in T015 pass. Compare the exported manifest with the built one and write "a change made outside the pipeline was undone" in the summary when they differ; if Slack's export always differs because of added defaults, drop the comparison and record that in `specs/006-slack-app-deployment/research.md` ("Open items for implementation")
- [X] T017 [US1] Create `.github/workflows/slack-app.yml` named `Slack app` with the triggers in `specs/006-slack-app-deployment/contracts/slack-app-pipeline.md` (push with `paths` `slack/**`, `scripts/slack_app/**`, `.github/workflows/slack-app.yml`; a daily `schedule`; `workflow_dispatch` with an `action` input of `apply` (default) or `create`), a workflow-level concurrency group `slack-app` with `cancel-in-progress: false`, and a `check` job with job outputs `failure_kind` and `failure_help` that sets up the workspace and Python the same way as `build_container` in `.github/workflows/main.yml` and runs `pipenv run slack-app check`
- [X] T018 [US1] Add the `apply` job to `.github/workflows/slack-app.yml`: `needs: check`; runs only when the ref is `main` and the event is a push, the schedule, or a hand start with `action: apply`; permission `contents: read`; job outputs `failure_kind` and `failure_help`; passes `SLACK_CONFIG_REFRESH_TOKEN`, `SLACK_STORE_TOKEN`, `SLACK_BOT_TOKEN` and `SLACK_APP_ID` from repository secrets and variables as environment variables; runs `pipenv run slack-app apply`
- [X] T019 [US1] Add a separate `report` job to `.github/workflows/slack-app.yml` as `specs/006-slack-app-deployment/contracts/slack-app-pipeline.md` describes: `needs: [check, apply]`, `if: always()` and the ref is `main`, permission `issues: write` only. When the result of any needed job is `failure` and the event is the schedule, open an issue labelled `slack-app-failure` (creating the label if needed) whose text is the failure kind (`unexpected` when none was output), its `failure_help` text and a link to the run, or add a comment to the open one. When `apply` succeeded, close every open issue with that label with a comment linking the run. Otherwise do nothing. It must be a job of its own so that it still runs when `check` fails and `apply` is skipped. The text must be built only from the two job outputs and never from other command output

**Checkpoint**: The workflow exists and `apply` is covered by unit tests. It cannot pass for
real until the app exists (Phase 5).

---

## Phase 4: User Story 2 - A bad app definition is caught before it is merged (Priority: P1)

**Goal**: A branch push that changes the Slack files is checked offline and by Slack, and
changes nothing in Slack.

**Independent Test**: Quickstart B and E.

### Tests for User Story 2

- [X] T020 [US2] Add tests to `tests/unit/test_slack_commands.py` for `validate`: with no `SLACK_CONFIG_REFRESH_TOKEN` it prints that Slack validation was skipped, contacts nothing and exits 0; with one it renews, stores, then calls `validate` with `SLACK_APP_ID` when set and without it when not; Slack's `invalid_manifest` exits 1 with each `message` and `pointer` in the summary; an offline failure exits 1 without contacting Slack; `update` and `create` are never called

### Implementation for User Story 2

- [X] T021 [US2] Implement the `validate` command in `scripts/slack_app/__main__.py` so that the tests in T020 pass
- [X] T022 [US2] Add a step to the `check` job in `.github/workflows/slack-app.yml`, after the offline check, that runs `pipenv run slack-app validate` with `SLACK_CONFIG_REFRESH_TOKEN`, `SLACK_STORE_TOKEN` and `SLACK_APP_ID` passed as environment variables, and confirm by reading the file that no job other than `apply` and `create` can run `update` or `create` and that neither runs on a ref other than `main`

**Checkpoint**: A branch with a bad definition fails `check`. The Slack half of the check
is skipped until the credential is stored (Phase 5).

---

## Phase 5: User Story 3 - The app is created from nothing by following the documentation (Priority: P2)

**Goal**: A hand-started run creates the app and refuses when one exists; the handbook
takes the owner from nothing to an installed, managed app.

**Independent Test**: Quickstart C.

### Tests for User Story 3

- [X] T023 [US3] Add tests to `tests/unit/test_slack_commands.py` for `create`: with no `SLACK_APP_ID` it creates, stores `SLACK_APP_ID` as a variable and `SLACK_SIGNING_SECRET`, `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET` as secrets, masks the signing secret, client secret and verification token before anything is printed, and writes the app ID and install link to the summary; with `SLACK_APP_ID` set and `export` succeeding it fails with `app_exists` and does not call `create`; with `SLACK_APP_ID` set and `export` answering `app_not_found` it creates and overwrites all four values; with `SLACK_APP_ID` set and `export` failing with `slack_unavailable` or `credential_rejected` it fails with that kind and does not call `create`; if storing any value fails it exits 1 with `store_failed` and the summary gives the new app ID so the owner can recover; no secret appears in any output

### Implementation for User Story 3

- [X] T024 [US3] Implement the `create` command in `scripts/slack_app/__main__.py` so that the tests in T023 pass
- [X] T025 [US3] Add the `create` job to `.github/workflows/slack-app.yml`: `needs: check`; runs only on a hand start with `action: create` on `main`; same permission, job outputs and environment variables as `apply`; runs `pipenv run slack-app create`. Add `create` to the `needs` of the `report` job and treat its result the same way as `apply`'s
- [X] T026 [US3] Write `docs/handbook/08-slack-app.md`: what the Slack app is and that STRIDEr does not answer yet; "First-time setup" as numbered steps, each marked as done by hand or by the pipeline with the reason (create a Slack app configuration token and store its refresh token as `SLACK_CONFIG_REFRESH_TOKEN`; create a fine-grained GitHub token for this repository with Secrets: write and Variables: write, store it as `SLACK_STORE_TOKEN` and note its expiry date; start the `Slack app` workflow with `action: create`; install the app from the link in the run summary; store the bot token as `SLACK_BOT_TOKEN`; start the workflow with `action: apply`); which GitHub notification setting must be on to be told of failed runs; that GitHub switches the daily run off after 60 days without repository activity and how to switch it back on
- [X] T027 [US3] Add to `docs/handbook/08-slack-app.md`: "Changing the app" (edit `slack/manifest.yaml`, every scope and event needs a reason, branch check, merge); "Adding a permission" (the run fails with `reinstall_needed` until the app is installed again; how to reinstall; check the bot token); "Recovery", one entry per failure kind in `specs/006-slack-app-deployment/data-model.md` with the starting state, the steps and the end state, including a lost refresh token, an expired `SLACK_STORE_TOKEN`, a stored app value that was lost while the app still exists (where to read the signing secret, client ID, client secret and bot token again in the app's settings in Slack, and how to store them), and a deleted app (new app ID, signing secret and bot token; everything that used the old values must be updated)
- [ ] T028 [US3] **(owner)** Do steps 1 and 2 of "First-time setup" in `docs/handbook/08-slack-app.md`: store `SLACK_SERVICE_TOKEN` and `SLACK_STORE_TOKEN` on `ServerlessOpsIO/engineering-agents`. `SLACK_SERVICE_TOKEN` was stored by the owner on 2026-11-16; `SLACK_STORE_TOKEN` is still to do
- [ ] T029 [US3] **(owner)** After this branch is merged to `main`, run the rest of "First-time setup" in `docs/handbook/08-slack-app.md` as quickstart C describes, timing it, and record the result under "Results" in `specs/006-slack-app-deployment/quickstart.md`
- [ ] T030 [US3] **(owner)** During T029, check the facts research left as believed and record each with the date in `specs/006-slack-app-deployment/research.md` ("Facts checked"): F12 (run `pipenv run slack-app check --output built.json`, add `"event_subscriptions": {"bot_events": ["app_mention"]}` under `settings` in a copy of that file, and send the copy to `apps.manifest.validate` with the app's ID; Slack should reject it for having events and no request URL); F14 (the `apply` run reports the installed scopes); F3 (the previous refresh token is refused); F15 (after quickstart H, whether the bot token changed). If F14 is false, stop and return FR-025 to the owner as research Decision 9 says

**Checkpoint**: STRIDEr is in the workspace, installed, and managed by the pipeline.
Quickstart C passes; D to J can now be run.

---

## Phase 6: User Story 4 - The later feature can read the app's values (Priority: P2)

**Goal**: The app ID, signing secret and bot token are stored where the later feature can
read them, and no secret is exposed.

**Independent Test**: Quickstart C (values exist) and K (no secret found).

- [X] T031 [US4] Add a test to `tests/unit/test_slack_commands.py` that runs `validate`, `apply` and `create` end to end with fakes returning recognisable token values and asserts none of those values appears in standard output, standard error, the summary file, the output file or any raised message (FR-018)
- [X] T032 [P] [US4] Add to `docs/handbook/03-configuration.md` a section listing the seven GitHub values from `specs/006-slack-app-deployment/data-model.md` ("Values in GitHub") with kind, who writes each, who reads each, and that the later feature reads `SLACK_APP_ID`, `SLACK_SIGNING_SECRET`, `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET` and `SLACK_BOT_TOKEN` and must not write them
- [ ] T033 [US4] **(owner)** After T029, confirm variable `SLACK_APP_ID` matches the app shown in Slack and that secrets `SLACK_SIGNING_SECRET`, `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET` and `SLACK_BOT_TOKEN` exist, then run quickstart K over the repository, every `Slack app` run and every `slack-app-failure` issue, and record the result in `specs/006-slack-app-deployment/quickstart.md`

---

## Phase 7: User Story 5 - The event delivery address is added later without rework (Priority: P3)

**Goal**: Supplying the address is a one-line change to `slack/settings.json`.

**Independent Test**: Quickstart B, step 3.

- [X] T034 [US5] Add to `docs/handbook/08-slack-app.md` a section "Supplying the event delivery address": set `event_request_url` in `slack/settings.json` and merge; the next run sends the address and the four events; the address must then be verified once by hand in the app's settings with the receiver answering; this belongs to the later feature
- [X] T035 [US5] Run quickstart B step 3 locally (set an address, run `pipenv run slack-app check --output`, confirm the built manifest has the address and four events, restore the file) and record the result in `specs/006-slack-app-deployment/quickstart.md`

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T036 [P] Update `docs/handbook/05-ci-cd.md`: add the `Slack app` workflow to the triggers table, describe its three jobs, the concurrency group, that it is independent of `Main` and `Branches`, and that a merge changing only the Slack files still starts an agent build
- [X] T037 [P] Update `docs/handbook/00-index.md` with a link to `08-slack-app.md`, and `docs/handbook/01-features.md` with the STRIDEr Slack app and what it does not yet do
- [X] T038 Run `pipenv run test-unit` and `pipenv run slack-app check`, confirm both pass, and confirm `git diff main --stat -- template.yaml cfn-parameters.json .github/workflows/main.yml .github/workflows/branch.yml` prints nothing (FR-019, FR-012)
- [ ] T039 **(owner)** Run quickstart D, E, F, G and J and record the results in `specs/006-slack-app-deployment/quickstart.md`
- [ ] T040 **(owner)** Run quickstart H and I (adding a permission; a failed scheduled run opens one issue and a later pass closes it) and record the results in `specs/006-slack-app-deployment/quickstart.md`
- [ ] T041 **(owner)** Ten days after T029, check the `Slack app` workflow's history for ten passing runs in a row with no credential renewed by hand (SC-010) and record the result in `specs/006-slack-app-deployment/quickstart.md`

---

## Change after implementation: service token (2026-11-16)

After T001 to T038 were done, the owner chose a Slack CLI service token in place of the
rotating refresh token (research, Decision 12). The tasks above are left as they were
written and done. Where they mention `rotate`, renewing, storing a new refresh token or
`SLACK_CONFIG_REFRESH_TOKEN`, that code was then removed by the tasks below.

- [X] T042 Replace the refresh token with `SLACK_SERVICE_TOKEN` in `scripts/slack_app/__main__.py`: remove renewing and storing, read the token and send it unchanged, and make `create` confirm `SLACK_STORE_TOKEN` is set before creating anything
- [X] T043 Remove `rotate` from `scripts/slack_app/slack_api.py` and update the failure texts for `credential_rejected` and `store_failed` in `scripts/slack_app/__init__.py`
- [X] T044 Update `tests/unit/test_slack_commands.py`, `tests/unit/test_slack_api.py` and `tests/unit/test_slack_store.py`: the service token is sent and never stored; `validate` and `apply` write nothing to GitHub; nothing is created when `SLACK_STORE_TOKEN` is missing
- [X] T045 Update `.github/workflows/slack-app.yml`: `SLACK_SERVICE_TOKEN` in every job that contacts Slack; `SLACK_STORE_TOKEN` only in `create`
- [X] T046 Update `docs/handbook/08-slack-app.md`, `03-configuration.md` and `05-ci-cd.md`, and `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/slack-app-pipeline.md` and `quickstart.md` in `specs/006-slack-app-deployment/`
- [ ] T047 **(owner)** During T029, confirm that `create`, `apply` (which calls `export` and `update`) and the installed-permissions check all work with the service token, and record the result in `specs/006-slack-app-deployment/research.md` (Decision 12, "Checked")

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1** has no dependencies. T001 is independent of the code tasks.
- **Phase 2** depends on T002 to T004 and blocks every user story.
- **Phases 3, 4 and 5** each depend on Phase 2. Their code and tests are independent of
  each other, but they all edit `scripts/slack_app/__main__.py`,
  `tests/unit/test_slack_commands.py` and `.github/workflows/slack-app.yml`, so do them one
  after another: 3, then 4, then 5.
- **Phase 6** depends on Phases 3 to 5 for T031 and on T029 for T033.
- **Phase 7** depends on Phase 2 only.
- **Phase 8** depends on everything before it.

### What can and cannot be validated before merging

User Story 1 has the highest priority but cannot be validated for real until the app
exists, and the app is created by User Story 3's hand-started run, which only exists once
the workflow is on `main`. So:

- Before merging: T001 to T027, T031, T032, T034 to T038. Everything is covered by unit
  tests and the offline check.
- T028 (owner stores the two credentials) can be done at any time before merging.
- After merging: T029, T030, T033, T039, T040, T041, all by the owner.

### Within a phase

- A test task comes before the implementation task that makes it pass.
- T017, T018, T019, T022 and T025 edit the same workflow file and run in that order.
- T026 and T027 edit the same handbook page and run in that order; T034 follows them.

## Parallel Execution Examples

Phase 2, after T004:

```text
T005 slack/manifest.yaml
T006 slack/settings.json
T007 tests/unit/test_slack_definition.py
T009 tests/unit/test_slack_api.py
T011 tests/unit/test_slack_store.py
```

Then T008, T010 and T012 can run in parallel with each other (three different modules).

Phase 8: T036 and T037 (different handbook pages).

T015, T020, T023 and T031 share one test file and are not parallel.

## Implementation Strategy

### MVP

The smallest thing worth having is Phases 1 to 5: the definition, the check, the apply and
the creation run with its documentation. User Story 1 alone is not usable, because nothing
would exist to apply to.

### Order

1. Phases 1 and 2. Checkpoint: unit tests and the offline check pass.
2. Phases 3, 4 and 5 in order. Checkpoint: all three commands are covered by unit tests
   and the workflow file is complete.
3. Phases 6 and 7, then T036 to T038.
4. Merge. The owner then does T028 to T030, T033, T039 and T040, and T041 ten days later.

### Decided by the owner on 2026-11-16

- A thread reply need not mention STRIDEr, so `channels:history` and `groups:history` stay.
- Issues are opened for failed scheduled runs only.
- A permission the installed app holds that the definition does not have passes for now.
  Issue #7 tracks finding out what Slack does when a permission is removed.

### Still open

- `checklists/deployment.md` has 41 unreviewed items.
