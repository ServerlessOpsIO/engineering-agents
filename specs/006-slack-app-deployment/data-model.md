# Data Model: STRIDEr Slack App Deployment

**Date**: 2026-11-16 | **Spec**: `specs/006-slack-app-deployment/spec.md`

This feature has no database. Its data is three files in the repository, seven values in
GitHub, and one app in Slack.

## Files in the repository

### App definition: `slack/manifest.yaml`

The single source of truth for the Slack app (FR-001). Follows Slack's app manifest schema.

| Field | Value or rule |
|---|---|
| `display_information.name` | `STRIDEr`. Required. At most 35 characters. |
| `display_information.description` | Required by this project. At most 140 characters. |
| `features.bot_user.display_name` | `STRIDEr`. Required. At most 80 characters. |
| `features.bot_user.always_online` | `true`. |
| `features.app_home.home_tab_enabled` | `false` (FR-004). |
| `features.app_home.messages_tab_enabled` | `true` (FR-002, direct messages). |
| `features.app_home.messages_tab_read_only_enabled` | `false`. |
| `oauth_config.scopes.bot` | Exactly the five scopes in research, Decision 8. Each line carries a comment giving its reason (FR-003). |
| `settings.event_subscriptions.bot_events` | Exactly the four events in research, Decision 8. Each line carries a comment giving its reason. |
| `settings.event_subscriptions.request_url` | MUST NOT be present. It comes from `slack/settings.json`. |
| `settings.socket_mode_enabled` | `false` (FR-005). |
| `settings.org_deploy_enabled` | `false`. |
| `settings.token_rotation_enabled` | `false`. |

Must not be present (FR-004): `features.slash_commands`, `features.shortcuts`,
`features.workflow_steps`, `features.unfurl_domains`, `settings.interactivity`,
`oauth_config.redirect_urls`, `oauth_config.scopes.user`, `functions`, `workflows`.

### Settings: `slack/settings.json`

| Field | Rule |
|---|---|
| `event_request_url` | A string. Empty, or an `https://` address of at most 3,500 characters. Empty in this feature (FR-006). |

### Schema: `slack/manifest.schema.json`

A copy of Slack's published schema for app manifests, version 2.0.0, from
`slackapi/manifest-schema` (MIT licence), file `schemas/manifest.schema.2.0.0.json` at
commit `7ec398e7edfbd2b3614c3e932c1a20c79d58177e` (2026-10-06). Kept in the repository so
that the check needs no network and does not change when Slack's copy does. It checks
structure, types, lengths and unknown fields. It does not know which scope or event names
are real; only Slack does.

### Built manifest (not stored)

Produced from the two files above each time it is needed; never committed.

- JSON, the form Slack's methods take.
- `event_request_url` empty: `settings.event_subscriptions` is left out.
- `event_request_url` set: `settings.event_subscriptions` has `request_url` and the
  `bot_events` from the app definition.
- The same inputs always give byte-identical output (keys sorted), so two builds can be
  compared.

## Values in GitHub (repository level)

| Name | Kind | Secret | Written by | Read by | Notes |
|---|---|---|---|---|---|
| `SLACK_CONFIG_REFRESH_TOKEN` | Secret | Yes | Owner, once; then every job that contacts Slack | Jobs that contact Slack | The pipeline credential. Replaced on every use (FR-015). |
| `SLACK_STORE_TOKEN` | Secret | Yes | Owner | Jobs that contact Slack | Fine-grained token for this repository with Secrets: write and Variables: write. Has an expiry date. |
| `SLACK_APP_ID` | Variable | No | Creation run | All Slack jobs; the later feature | Absent means no app is recorded. |
| `SLACK_SIGNING_SECRET` | Secret | Yes | Creation run | The later feature | Issued once, when the app is created (FR-016). |
| `SLACK_CLIENT_ID` | Secret | No, but stored as a secret at the owner's request | Creation run | The later feature | Issued once, when the app is created. |
| `SLACK_CLIENT_SECRET` | Secret | Yes | Creation run | The later feature | Issued once, when the app is created. |
| `SLACK_BOT_TOKEN` | Secret | Yes | Owner, after installing | Reinstall check; the later feature | Absent means the app has never been installed (FR-017). |

The client ID and client secret are stored because the later feature's deployment will
refer to them (owner's decision, 2026-11-16). `verification_token`, which Slack also
returns when the app is created, is not stored: it is Slack's older way of checking
requests and the signing secret replaces it. It is masked like the others and can be read
in the app's settings if ever needed.

## The Slack app

One app in the `serverlessops` workspace, identified by `SLACK_APP_ID` (FR-013).

### States

```text
                      creation run
   Not recorded  ───────────────────►  Created, not installed
        ▲                                      │
        │                                      │ owner installs, stores bot token
        │ owner clears SLACK_APP_ID            ▼
        │ (documented recovery)          Installed, in step  ◄──────────────┐
        │                                      │                            │
   Recorded but gone  ◄── deleted by hand ─────┤                            │
                                               │ a merge adds a scope       │ owner installs
                                               ▼                            │ again
                                        Installed, behind  ─────────────────┘
```

| State | How a job knows | Merge or scheduled run | Creation run |
|---|---|---|---|
| Not recorded | `SLACK_APP_ID` absent | Fails; names the creation run (FR-024) | Creates the app |
| Created, not installed | App exists; `SLACK_BOT_TOKEN` absent | Applies; passes with a notice that the app is not installed | Refuses (FR-023) |
| Installed, in step | Every scope in the definition is held by the bot token | Applies; passes | Refuses |
| Installed, behind | A scope in the definition is not held by the bot token | Applies; then fails with reinstall instructions (FR-025) | Refuses |
| Recorded but gone | Slack answers `app_not_found` for `SLACK_APP_ID` | Fails; names the recovery steps and the creation run (FR-024) | Creates a replacement and overwrites `SLACK_APP_ID`, `SLACK_SIGNING_SECRET`, `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET` |

The creation run refuses whenever the recorded app still exists. It does not need the owner
to clear `SLACK_APP_ID` first when the app is gone, because it checks with Slack.

## Failure kinds

A fixed list. Messages in run summaries and issues are built only from these (research,
Decision 10).

| Kind | Meaning | What the message tells the owner to do |
|---|---|---|
| `invalid_definition` | The offline check or Slack rejected the app definition | Fix the listed problems |
| `credential_missing` | A needed secret or variable is not set | Which one, and where it comes from |
| `credential_rejected` | Slack refused the refresh token | Issue a new configuration token and store its refresh token |
| `store_failed` | A value could not be written to GitHub | Check `SLACK_STORE_TOKEN` and its expiry; if a refresh token was lost, do as for `credential_rejected` |
| `app_not_recorded` | No `SLACK_APP_ID` | Start the creation run |
| `app_gone` | Slack does not know the recorded app | Start the creation run; reinstall; update everything that used the old values |
| `app_exists` | Creation run started while the app exists | Nothing; creation refused |
| `reinstall_needed` | The installed app lacks a scope in the definition | Install the app again; check the bot token |
| `bot_token_rejected` | Slack refused the stored bot token | Store the current bot token |
| `slack_unavailable` | Slack could not be reached or answered with a server error or rate limit | Run again later |
| `unexpected` | Anything else | Read the run's log |
