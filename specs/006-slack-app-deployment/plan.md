# Implementation Plan: STRIDEr Slack App Deployment

**Branch**: `feature/006-slack-app-deployment` | **Date**: 2026-11-16 | **Spec**: `specs/006-slack-app-deployment/spec.md`

**Input**: Feature specification from `specs/006-slack-app-deployment/spec.md`

## Summary

Keep the STRIDEr Slack app's definition in the repository as a Slack app manifest, and add
a pipeline that validates it on branches, applies it to Slack when it changes on `main`,
reapplies it once a day, and creates the app only when the owner starts a run by hand.

The pipeline calls Slack's Manifest API directly through a small Python program in this
repository; Terraform was compared and rejected (research, Decision 1). It lives in a new
workflow file, so it cannot block or be blocked by the agent's build and deployment. The
credential for changing Slack apps is a refresh token that is replaced on every use, so
every run stores its replacement before doing anything else. The app ID, signing secret and
bot token, with the app's client ID and client secret, are kept as GitHub repository values for the later feature to read. No cloud
resource is created and `template.yaml` is not touched.

## Technical Context

**Language/Version**: Python 3.14 for the program; GitHub Actions workflow YAML.

**Primary Dependencies**: Python standard library for HTTP. Two new development
dependencies: PyYAML, to read the app definition, and `jsonschema`, to check it against a
copy of Slack's published manifest schema. The `gh` command, already on GitHub's runners, to
write secrets and variables and to manage issues. No Slack SDK, no Terraform.

**Storage**: GitHub repository secrets and one repository variable (`data-model.md`). No
state file.

**Testing**: `pytest` 9.2.0 through `pipenv run test-unit`, with Slack and GitHub replaced
by fakes. No test contacts either service. End-to-end checks are manual and listed in
`quickstart.md`.

**Target Platform**: GitHub Actions on `ubuntu-latest`; Slack's Web API (`slack.com/api`);
the `serverlessops` Slack workspace.

**Project Type**: Pipeline tooling in an existing single-service repository.

**Performance Goals**: A merged change is in Slack within 10 minutes (SC-001). The job is
expected to take about one minute.

**Constraints**:

- The refresh token is replaced each time it is used; the replacement must be stored in the
  same run, and two runs must never renew at once (research, Decisions 2 and 4).
- Writing a GitHub secret from a workflow needs a separate token, which itself expires
  (research, Decision 3).
- Slack rejects a manifest that lists events without an address, so events are held back
  until an address is supplied (research, Decision 7).
- Installing the app, and later verifying the event address, need a person.
- The repository is public: logs, run summaries and issues are public.
- `template.yaml`, `cfn-parameters.json`, `branch.yml` and `main.yml` are not edited.

**Scale/Scope**: One Slack app. About 300 lines of Python with tests, one workflow, two
definition files, one handbook page and edits to three others.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Not performed, before or after design. `.specify/memory/constitution.md` is still the
unfilled Spec Kit template, so there are no principles or gates to evaluate. This is an open
item for the project owner and is not treated as a gate failure.

## Decisions the owner should look at

These follow from the spec but were made by the author during planning.

1. **Direct Manifest API calls, not Terraform** (research, Decision 1). Matches the owner's
   lean; the comparison is in the research.
2. **STRIDEr can read every message in channels it is added to** (research, Decision 8).
   "Replies in threads" without a mention needs `channels:history` and `groups:history`;
   Slack has nothing narrower. Accepted by the owner on 2026-11-16.
3. **A separate workflow, so two runs per commit** (research, Decision 6). "The run as a
   whole shows as failed" is read as "the commit shows a failed check".
4. **Branch runs can read the Slack credential** (research, Decision 5), because asking
   Slack to validate needs it. Acceptable while the owner is the only person who can push.
5. **One more credential to look after**: a GitHub token that can write this repository's
   secrets and variables, with an expiry date (research, Decision 3).
6. **A second manual step exists, in the later feature**: Slack requires the event address
   to be verified by hand once (research, F13). SC-005 is about this feature's setup and
   still holds.
7. **This feature's Slack app has no event subscriptions** until an address is supplied
   (research, Decision 7).
8. **The template repository is not changed.** `backstage-aws-agentcore-template` creates
   generic agents; a Slack app is specific to STRIDEr. Not asked for, so not done.

Five facts are still unverified and are checked by early tasks (research, Open items). The
one with consequences is F14: if a token's scopes cannot be read back, FR-025 returns to
the owner.

## Project Structure

### Documentation (this feature)

```text
specs/006-slack-app-deployment/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── slack-app-pipeline.md
├── checklists/
│   └── requirements.md
├── catalog-info.yaml
└── tasks.md               # Created later by /speckit-tasks
```

### Source Code (repository root)

```text
slack/
├── manifest.yaml              # New: the app definition (FR-001 to FR-005)
├── settings.json              # New: event_request_url, empty (FR-006)
└── manifest.schema.json       # New: copy of Slack's published schema, version 2.0.0

scripts/slack_app/
├── __main__.py                # New: commands check, validate, apply, create; exit codes;
│                              #      run summary and failure kind output
├── definition.py              # New: read both files, offline check, build the manifest
├── slack_api.py               # New: rotate, validate, export, update, create, auth.test;
│                              #      maps Slack errors to failure kinds
└── store.py                   # New: write GitHub secrets and variables through gh,
                               #      with retries; mask values in logs

tests/unit/
├── test_slack_definition.py   # New
├── test_slack_api.py          # New
├── test_slack_store.py        # New
└── test_slack_commands.py     # New: order of renew-store-act; every app state;
                               #      every failure kind

.github/workflows/slack-app.yml   # New: jobs check, apply, create, report

Pipfile, Pipfile.lock          # PyYAML and jsonschema added to dev-packages
pytest.ini                     # pythonpath gains scripts

docs/handbook/
├── 08-slack-app.md            # New: first-time setup, changing the app, supplying the
│                              #      address, reinstalling, recovery for each failure
│                              #      kind, notification settings, the 60-day schedule rule
├── 00-index.md                # Link to the new page
├── 01-features.md             # STRIDEr Slack app listed
├── 03-configuration.md        # The five GitHub values
└── 05-ci-cd.md                # The Slack app workflow
```

Not changed: `template.yaml`, `cfn-parameters.json`, `cfn-tags.json`, `src/`,
`.github/workflows/branch.yml`, `.github/workflows/main.yml`.

**Structure Decision**: The definition files get their own top-level directory, `slack/`,
so the workflow's path filter is simple and a reviewer sees at once that a change affects
the Slack app. The program goes under the existing `scripts/` directory, split into three
modules along the three things it talks to (files, Slack, GitHub) so each can be tested
with the other two faked. The existing workflows are left alone and a third is added.

## How the requirements are met

| Requirement | Met by |
|---|---|
| FR-001 to FR-005 | `slack/manifest.yaml`; offline check rules (contract, section 2) |
| FR-006 | `slack/settings.json`; build step (data model, Built manifest) |
| FR-007 | Job `check`: offline check, then Slack validation |
| FR-008, FR-009 | Job `apply` on pushes to `main`; workflow path filter |
| FR-010 | Daily schedule running `apply`, which always sends the full definition |
| FR-011 | Separate workflow; failure kinds with next steps (data model) |
| FR-012 | Separate workflow file; existing workflows not edited |
| FR-013 | `apply` and `create` only run on `main` |
| FR-014, FR-015 | Refresh token as a repository secret; renew-store-act order; concurrency group |
| FR-016 | `create` stores the app ID, signing secret, client ID and client secret |
| FR-017 | Owner stores the bot token; handbook step |
| FR-018 | Masking in `store.py`; fixed failure messages; unit test that no secret reaches output |
| FR-019 | Nothing under `template.yaml` or `cfn-parameters.json` is touched |
| FR-020, FR-021 | `docs/handbook/08-slack-app.md` |
| FR-022 | Research, Decision 1 |
| FR-023, FR-024 | `create` only on a hand-started run; app states (data model) |
| FR-025 | Scope check after `apply` (research, Decision 9) |
| FR-026 | Job `report` (contract, section 1) |
| FR-027 | Failure kind `bot_token_rejected` (data model); `apply` tests |

## Complexity Tracking

Nothing recorded. With no constitution in force there are no violations to justify.
