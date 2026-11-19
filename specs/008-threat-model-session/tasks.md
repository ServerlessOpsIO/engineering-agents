# Tasks: STRIDEr Leads a Threat Modelling Session

**Input**: Design documents from `/specs/008-threat-model-session/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md,
contracts/agent-interface.md, contracts/session-tools.md, contracts/written-model.md

**Tests**: Included. FR-047 requires unit tests, and none may contact AWS, Slack or
GitHub.

**Organization**: Tasks are grouped by user story. All paths are in this repository
(`engineering-agents`). Tasks marked **(owner)** need the AWS deployment account, the
`serverlessops` Slack workspace or the owner's judgement, and can only be done by the
project owner.

**These tasks assume three decisions the owner has not yet confirmed** (`plan.md`,
"Decisions the owner should look at", 1 to 3): the `files:write` permission, writing our
own skill, and the session record. T001 asks. If the first is refused, T028 to T031
change; if the third is refused, the plan is redone.

**Rules that apply to every task**:

- No message text, reply text, tool argument, tool result, repository content, document
  or person's name is logged, at any level, including in exception handlers (FR-050).
- No test contacts AWS, Slack or GitHub.
- No package is added to `Pipfile`. If `Pipfile.lock` moves, restore it.
- The 40-message window and `filter_restored_tool_context=True` mean nothing may be kept
  only in the conversation (`research.md`, Decisions 1 and 2).
- Feature 007's behaviour outside a session must not change (FR-051). Its tests are
  changed only where a task says so.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`[US1]` to `[US7]`)
- Every task names a file path

---

## Phase 1: Setup

**Purpose**: Confirm the plan's premises and prepare the layout.

- [ ] T001 **(owner)** Confirm or refuse decisions 1, 2 and 3 in `specs/008-threat-model-session/plan.md`, and record the answers under a new heading "Owner's answers" in that file. Stop here if decision 3 is refused
- [ ] T002 Run `pipenv install --dev` and `pipenv run test-unit`; record the number of passing tests in `specs/008-threat-model-session/quickstart.md` under Results, so that SC-012 can be checked later
- [ ] T003 [P] Create empty packages `src/agent/session/__init__.py` and `tests/unit/session/` (no `__init__.py` in `tests/unit/`, which the existing flat tests rely on), and the folders `src/agent/skills/stride-threat-model/references/` and `data/sessions/`
- [ ] T004 [P] Add `transcripts/` to `.gitignore`, and add `play-session = "python scripts/play_session.py"` under `[scripts]` in `Pipfile` (no lock change)
- [ ] T005 [P] Rename `src/agent/system_prompt.md` to `src/agent/persona.md` with `git mv`, keeping its one sentence for now, and change the path read in `src/agent/prompt.py`; `tests/unit/test_prompt.py` must still pass
- [ ] T006 **(owner)** Stop message text reaching the agent's traces, before anything else is deployed (FR-050; `research.md`, O2). Strands puts the content of every model call and tool call on its spans unless told not to, and nothing in this stack tells it. In `template.yaml`, add to the runtime's `EnvironmentVariables`: `OTEL_SEMCONV_STABILITY_OPT_IN: 'gen_ai_unredacted_attributes='` (an empty list, which makes Strands replace user messages, replies, the system prompt, tool arguments and tool results with `[REDACTED]`) and `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT: 'false'` (the Bedrock call instrumentor's own switch). Merge and deploy this change on its own, since it also covers feature 007's live traffic. A read-only look on 2026-11-19 found no traces being stored for this agent (`research.md`, O2), so there is nothing to compare against today; the settings matter from the moment CloudWatch Transaction Search is turned on. If traces are being stored when this task is done, send STRIDEr one message containing a distinctive word, open that request's trace, and confirm the word is nowhere in it. Describe the two settings in `docs/handbook/06-observability.md`, and add to `docs/handbook/03-configuration.md`, beside the Transaction Search prerequisite, that they must be in place before it is turned on

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The session record, the documents made from it, and the way the model is
told what to do. Every story needs these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### The session record

- [ ] T007 Write `tests/unit/session/test_record.py` first, covering every rule in `data-model.md`, "Session record" to "Pending change": identifiers `C1`, `DS1`, `EP1`, `F1`, `TB1`, `T1`, `M1`, `Q1`, `S1`, `R1`, `H1`, `N1` given by code and never reused; a data flow's `from` and `to` "must exist and not be data flows"; removing an element "removes its data flows, its `noneFound` entries and its place in any boundary" and "is refused while a threat names it"; adding a threat "removes any `noneFound` entry for the same element and category"; `severity` worked out from the table in FR-044 for all nine combinations and absent until both values are present; `likelihoodReason` and `impactReason` "required with the value"; `decisionReason` "required when the decision is `accept`"; every name in `decidedBy` "must be in `participants`"; a mitigation's `threats` "at least one, each must exist"; "at most one hint for each (`stage`, `element`)"; `changedAfterNotes` set by code once `notesPostedOnTurn` is set; a record that does not validate when read is treated as no session
- [ ] T008 Implement `src/agent/session/record.py`: the record as dataclasses with `to_dict` and `from_dict` (plain JSON types only, since it is stored in `agent.state` under the key `session`), the stage names `scope`, `system`, `threats`, `rating`, `mitigations`, `model` in order, the statuses, the STRIDE categories, the table of categories by kind of element from `data-model.md`, and one method for each change with the rules of T007. A refused change raises `Refused(reason)` with a sentence fit to show the model. No logging in this module
- [ ] T009 Add to `src/agent/session/record.py` and `tests/unit/session/test_record.py` the transitions of `data-model.md`, "Stage and status transitions": start (refused while `in_progress`), complete a stage, go to a stage, a pending change with `announcedOnTurn` that "can be confirmed only on a later turn", `skip_stage` "applied at once" with one participant, `finish` and `abandon` "always announced first", `finished` and `abandoned` set `notesPostedOnTurn`, and adding a participant by name once. Also the rule of `data-model.md`, "A request that is repeated": a new `messageId` copies the record to `sessionBefore`, sets `lastMessageId` and advances `turn`; the same `messageId` puts `sessionBefore` back and does not advance `turn`; a missing `messageId` is always new. Test that a threat added by a first attempt is not there twice after a repeat, that a `finish` requested by a message cannot be confirmed by a repeat of that message, and that a session started by a first attempt is started once

### The documents

- [ ] T010 Write `tests/unit/session/test_render.py` first, from `contracts/written-model.md`: the nine headings exactly and in order; the status line for complete, in progress, abandoned, a skipped stage and an unfinished stage; the summary's counts by severity including "Not rated"; every threat column; threats ordered by severity then identifier; the four kinds of coverage cell (`T1, T4`, `None found`, `Not considered`, `n/a`); "Threats to be mitigated with no mitigation recorded"; the `†` mark and its explanation line; `None named` for an empty owner; the escaping rules for `|`, line breaks and a leading `#` or `>`; an empty record still gives every section. For the diagram: node shapes by kind, `subgraph` per boundary, labels with `"`, `[`, `]`, `|` and backticks made safe, and "No elements recorded." For the notes: the three headings, the fixed opening lines, `(not raised in the session)`, `Nothing.` for an empty section, and hints with `takenUp` true left out
- [ ] T011 Implement `src/agent/session/render.py`: `written_model(record, today)`, `facilitator_notes(record)` and `filename(system, kind)` ("lower case, letters, digits and hyphens only, at most 60 characters, ending `.md`"), to pass T010. Pure functions of the record; no logging
- [ ] T012 [P] Implement `src/agent/session/summary.py` and `tests/unit/session/test_summary.py`: the record as compact text for the system prompt: status, stage and each stage's state, participants, scope, elements with identifiers, boundaries, threats with their values, what each element still lacks in the current stage, the pending change, and counts of held findings. For hints and notes it follows `data-model.md`, "What the model is shown of hints and notes": the full text of those made in the current stage, under a line saying they are STRIDEr's own and MUST NOT be revealed or described to participants before the session ends; for every other stage, only which elements have had their hint and how many notes there are. Test that a hint's point from an earlier stage appears nowhere in the summary. It never includes a held finding's text before `descriptionComplete`. With no record it says there is no session

### Skills and the prompt

- [ ] T013 [P] Implement `src/agent/loader.py` and `tests/unit/test_skills.py`: read every folder under `src/agent/skills/` at import with `strands.vended_plugins.skills.Skill.from_file(path, strict=True)`; expose each skill's name, description, instructions, `allowed-tools`, `metadata.stages` and a `reference(stage)` reader; fail at start-up when a skill is malformed, when a stage in `metadata.stages` has no `references/<stage>.md`, or when `metadata.adopted` is true and `SOURCE.md` is missing or names no licence (FR-004, FR-008, FR-047). Test each failure with a temporary folder
- [ ] T014 Write a first working `src/agent/skills/stride-threat-model/SKILL.md` (front matter: `name: stride-threat-model`, a `description` that says when to use it, `license: MIT`, `allowed-tools`, `metadata.stages`, `metadata.adopted: false`) and a short `references/<stage>.md` for each of the six stages. Enough for a session to run end to end; the rules are refined in later phases. It must not say who STRIDEr is or how it speaks (FR-002). Follow `research.md` M3: named sections, tools referred to by name, a "Tool usage" section
- [ ] T015 Rewrite `src/agent/prompt.py` and `tests/unit/test_prompt.py`: `build_system_prompt(record)` returns, in this order, the record's summary (T012), the active skill's instructions and the current stage's reference file when a session exists, the list of skills by name and description, and the persona last (`contracts/agent-interface.md`, "What the model is given"). `user_message(prompt, speaker_name, quiet_allowed)` returns `[From: {name}] [You may stay quiet]` or `[A reply is required]` on the first line and the prompt after. Keep the existing `SYSTEM_PROMPT` name working until T021

### The tools and the agent

- [ ] T016 Write `tests/unit/session/test_tools.py` first, from `contracts/session-tools.md`: which tools are offered with no session, in each stage, and after a finished session, that after a finished session `write_model` and `add_open_question` are among them (FR-059); every refusal in the tables returns a sentence and does not raise; `complete_stage` is never refused, and leaving the threats stage its answer lists every element and category with neither a threat nor a none-found entry; `start_session` adds the speaker of the message that started the session to `participants`, returns the opening statement's points and leaves the staying-quiet point out for a direct message (FR-061); `rate_threat` returns the severity; `description_complete` returns every held finding at once; `write_model` attaches the model and never the notes; a confirmed `finish` attaches both documents once; an unexpected exception inside a tool returns a sentence and logs only the exception's type
- [ ] T017 Implement `src/agent/session/tools.py` to pass T016: each tool a Strands `@tool` function with a description of 20 to 50 words and short parameter descriptions (`research.md`, M4), reading and writing the record through `agent.state`; `tools_for(record, conversation_type)` chooses what is offered; documents are put in a per-request holder, not in the tool's result. This task covers the session tools and the stage tools; the repository tools are T042
- [ ] T018 Change `src/agent/main.py` and `tests/unit/test_main.py` per `contracts/agent-interface.md`: read `speakerName` (cleaned as in `data-model.md`, "Person's name"; missing gives `Someone`), `conversationType` (anything else gives `direct_message`) and `addressed` (missing gives true); load the record from the agent's state, add the speaker as a participant and advance `turn` when a session is in progress (the person whose message starts a session is added by `start_session`, T016); build the agent with `build_system_prompt`, `tools_for`, and `AgentCoreMemoryConfig(filter_restored_tool_context=True)`; return `documents` when any were attached; add `skill`, `stage`, `toolCalls` and `documents` to the log record. Assert in a test that a distinctive speaker name, prompt word and document word appear in no log output. Read `messageId` and apply the repeated-request rule (T009) before anything else touches the record, keeping `sessionBefore` in `agent.state` beside `session`. Add a test for `research.md`, O5: build stored conversations holding (a) a turn whose tool calls and results sit between a person's message and the model's words, (b) a model message with both words and a tool call, and (c) a turn that failed after a tool result and before any words, followed by the next person's message; restore each with tool traffic left out; assert that what the model would be sent starts with a person's message, never has two messages running from the same side, and has no tool call without its result. If (c) leaves two person's messages running, the agent joins them into one before sending, and the test asserts that
- [ ] T019 Run `pipenv run test-unit`; every test from before this feature must still pass (count from T002) along with the new ones (`tests/unit/`)

**Checkpoint**: The agent can hold a record and produce both documents. No model has
been tried yet.

---

## Phase 3: User Story 1 - A person is led through a threat model and receives it in writing (Priority: P1) 🎯 MVP

**Goal**: A session from "let's threat model X" to the written model as a file.

**Independent Test**: `quickstart.md`, scenario C (structure checks only) and scenario
E steps 1 and 2.

### The largest risk first

- [ ] T020 [US1] Implement a first `scripts/play_session.py` and `data/sessions/stride-fixed-session.yaml`: read the YAML's turns (`speaker`, `type`, `addressed`, `text`), send each to the runtime in `AGENT_RUNTIME_ARN` in one new session with the request fields of `contracts/agent-interface.md`, and write the transcript, each reply's time and every document to `transcripts/<timestamp>/`. The session is a one-person session on a system of three components, one data store and one external party, taking every stage to the end, with each turn written to stand alone whatever was asked before it. No checks yet (T051). Each turn is sent with a `messageId` made from the turn's number
- [ ] T021 [US1] Refine `src/agent/skills/stride-threat-model/SKILL.md` and `references/*.md` for the plain path: name the stage when it begins, one question at a time (FR-012), take the participants through each element and each category that applies to it using `references/threats.md` (the table of categories by element, and for each category two or three plain questions; credit sources in T046), record with the tools as answers come, state the severity that `rate_threat` returns, ask for a decision and once for an owner, and call `request_change` then `resolve_change` to finish. Remove the `SYSTEM_PROMPT` constant left in `src/agent/prompt.py` by T015
- [ ] T022 [US1] Write a draft `src/agent/persona.md`: who STRIDEr is, how it speaks, and the five rules of FR-003 each under a fixed heading. A draft only; its wording is settled in T048
- [ ] T023 [US1] **(owner)** Merge to `main` so the agent is deployed (branch deployments are off, issue #10). This changes what STRIDEr says to anyone who writes to it; the Slack worker is unchanged and ignores `documents`
- [ ] T024 [US1] **(owner)** Run `pipenv run play-session` three times. Record in `specs/008-threat-model-session/research.md` under O1 and O8: whether each run reached a written model, how many tool calls were refused or missing, each run's slowest reply, and what the model got wrong
- [ ] T025 [US1] **Stop and report to the owner** what T024 showed. If the model cannot hold the session, shorten `SKILL.md` and re-run once. If it still cannot, stop: Nova 2 Lite is a stopgap (`plan.md`), and the owner decides whether to wait for the model that replaces it. Do not try `ReasoningEffort`: the agent sends it in a shape Nova 2 may not accept, which is untested. Record the outcome in `specs/008-threat-model-session/research.md`, O1

### Delivering the model in Slack

- [ ] T026 [P] [US1] Change `src/common/common/agentcore.py` and `tests/unit/common/test_agentcore.py`: `ask` takes and sends `speaker_name`, `conversation_type` and `addressed`; `AgentReply` gains `documents` (a list of filename, title and Markdown; empty when absent); kind `no_reply` is accepted with empty text. A document is never part of an exception's message. `ask` also takes and sends `message_id`
- [ ] T027 [P] [US1] Add `DOCUMENT_NOT_POSTED = "I couldn't post the document. Please ask me for it again."` to `src/common/common/slack/text.py` and to `FIXED_SENTENCES`, and the outcome `no_reply` and reason `document_not_posted` to `src/common/common/model/slack.py`, with tests in `tests/unit/common/test_slack_text.py` and `tests/unit/common/test_slack_model.py`
- [ ] T028 [US1] Add `upload(channel, thread_ts, filename, title, markdown) -> bool` to `src/common/common/slack/api.py` using `files_upload_v2(content=…, filename=…, title=…, channel=…, thread_ts=…)`, tried three times like `post`, returning false on failure and never raising or logging; tests in `tests/unit/common/test_slack_api.py`
- [ ] T029 [US1] Change `src/handlers/AnswerSlackMessage/function.py` and its tests: after the text is posted, upload each document in order; on a failed upload post `DOCUMENT_NOT_POSTED` and end `failed`, `document_not_posted`; log `documents` as a count. Pass `conversation_type` and `addressed` (the existing `addressed` value's mention part) to `agentcore.ask`; `speaker_name` is sent as `None` until T037. Assert that a distinctive word of a document appears in no log output. Send `message_id` as `{channel}:{ts}`, the same on both attempts
- [ ] T030 [P] [US1] Add `- files:write  # Post the written threat model and the facilitator's notes as files.` to `slack/manifest.yaml` and update the expected scopes in `tests/unit/test_slack_definition.py`
- [ ] T031 [US1] **(owner)** Merge, then install the Slack app again as `docs/handbook/08-slack-app.md` describes (the Slack app workflow fails until this is done). Run `quickstart.md` scenario E steps 1 and 2 and confirm a model arrives as a file in a direct message; record O4 in `specs/008-threat-model-session/research.md`, including how Slack shows the `.md` file. If the upload is refused in a direct message, stop: no fallback is built in advance (`research.md`, O4), and the owner decides then between a code block and another way

**Checkpoint**: One person can be led through a session and receive the model.

---

## Phase 4: User Story 2 - The participants do the work, and STRIDEr does not do it for them (Priority: P1)

**Goal**: STRIDEr names no threat, gives no value and chooses nothing; hints once; keeps
notes.

**Independent Test**: `quickstart.md`, scenario F, and the rows of scenario C's table
about asking for the work, the hint and the questioned rating.

- [ ] T032 [US2] Add to `src/agent/persona.md` the rule that STRIDEr does not do the participants' work, in strong plain words under its fixed heading, listing the four things it never gives (a threat, a likelihood or impact or severity, a mitigation, a decision), that this holds when asked directly, repeatedly, or told the rule does not apply (FR-018), and what it may do (FR-020). Add to `tests/unit/test_prompt.py` a test for each of the five FR-003 headings and a phrase under each, so that removing any rule fails a test (SC-011)
- [ ] T033 [US2] Add to `src/agent/skills/stride-threat-model/SKILL.md` and the stage references: turning a request for the work back with a question about a named element and category (FR-019); examples only "from a plainly different kind of system", with two worked examples per category from a cash machine and a building's door locks in `references/threats.md` (FR-053); when and how to hint, with worked examples of a hint that points at an area without naming the threat, calling `give_hint` before hinting and `add_note` with `not_raised` when it is refused (FR-022, FR-023); `hint_taken_up`; pointing out a rating that contradicts an earlier statement, and raising any other doubt "as a question, once, without giving a value", then `add_note` with `questioned_kept` if it is kept (FR-045, FR-055); disagreements, only "when at least two participants have each stated a position" (FR-021); never revealing the notes (FR-056); the OWASP factors as questions in `references/rating.md`, in our own words (FR-043). Add to `tests/unit/test_skills.py` a test that each of these rules' marker phrases is present
- [ ] T034 [US2] Extend `data/sessions/stride-fixed-session.yaml` with turns that: ask for the threats to an element, for a rating, for a mitigation and for a decision; ask for an example of tampering with the kind of element under discussion; leave one obvious area untouched for one element; give a rating that contradicts an earlier turn and keep it when questioned; ask to see the notes part-way; ask for the model part-way. Add `must_not_appear_in_model` and `must_appear_in_notes` word lists for the untouched area

**Checkpoint**: The rule that shapes the feature is in the persona, the skill and the
fixed session.

---

## Phase 5: User Story 3 - Several people hold a session together in a channel thread (Priority: P2)

**Goal**: Names, silence, and agreement before a session is skipped, finished or
abandoned.

**Independent Test**: `quickstart.md`, scenario D.

- [ ] T035 [P] [US3] Change `src/common/common/slack/api.py` and `tests/unit/common/test_slack_api.py`: the member lookup's remembered answer also holds the person's name, taken from "`profile.display_name`; when empty, `profile.real_name`; when empty, `real_name`", cleaned with "line breaks and control characters removed, runs of spaces made one, `<`, `>` and backticks removed, cut to 80 characters"; add `name_of(user, team_id) -> str` that returns `Someone` when Slack cannot say or nothing is left, and never raises. No name is logged
- [ ] T036 [P] [US3] Change `src/common/common/slack/text.py` and `src/common/common/slack/thread.py` with their tests: a function that replaces `<@U…>`, `<@W…>` and the `|label` form with names from a supplied lookup, "for up to 10 different people in a message; further ones become `someone`", leaving STRIDEr's own mention to `strip_mention`; `read_thread` gives each earlier message's writer as a user ID so the worker can name them, in place of the `<@U…>` text it gives now
- [ ] T037 [US3] Change `src/handlers/AnswerSlackMessage/function.py` and its tests: send `speaker_name`; replace mentions with names in the message and in thread context; on `no_reply` post nothing and end with outcome `no_reply`, eyes removed as always, no apology (FR-029); log `namesLookedUp` as a count. Assert that a distinctive display name appears in no log output (FR-032). Confirm `src/handlers/CleanUpSlackMessage/function.py` needs no change by adding a test that a message with no eyes and no reply is `not_started`
- [ ] T038 [US3] Implement the quiet marker in `src/agent/main.py` and `tests/unit/test_main.py`: quiet is allowed only when `conversationType` is `channel_thread`, `addressed` is false and a session is `in_progress`; a reply that is exactly `[[quiet]]` becomes kind `no_reply` with empty text; the marker with other words is an `answer` with the marker removed; the marker when quiet is not allowed makes one more model call with "A reply is required.", and if it comes back again the reply is the apology path's `error` (`contracts/agent-interface.md`)
- [ ] T039 [US3] Add to `src/agent/skills/stride-threat-model/SKILL.md`: when to stay quiet and when to speak unasked, with worked examples of a message "plainly between participants" and of a question put to the group, and "when in doubt, reply" (FR-025 to FR-027); bringing people back to the open question; equal say and never directing a question at a named person (FR-031, also in the persona); recording `decided_by` from who said it and all who agreed (FR-057); announcing a pending change and treating the next message as agreement unless it objects (FR-060); a person who joins part-way is not given the opening again unless they ask. Add marker-phrase tests to `tests/unit/test_skills.py`
- [ ] T040 [US3] Extend `data/sessions/stride-fixed-session.yaml` to two named participants in a `channel_thread`: two messages between them with `expect: no_reply`; a question to the group, a disagreement with two stated positions and a mention, each with `expect: answer`; one asks to finish and the other objects; later both agree; a change after the notes

**Checkpoint**: A team can run a session in a thread.

---

## Phase 6: User Story 4 - STRIDEr checks what it is told against the repository (Priority: P2)

**Goal**: Read a named public `ServerlessOpsIO` repository and report differences after
the participants have described the system.

**Independent Test**: `quickstart.md`, scenario G.

- [ ] T041 [US4] Write `tests/unit/test_github.py` first, with a fake HTTP opener, covering every rule in `contracts/session-tools.md`, "Repository tools": the name pattern `^[A-Za-z0-9._-]{1,100}$` and the refusal of `.` and `..`; the naming rule of `contracts/session-tools.md`: refused unless the repository has an entry or the name appears "as a whole word and without regard to case" in the current request or a person's message in view; an entry is made the first time it passes; a second listing still passes after the naming message has left the 40-message view; a name that appears only in the model's own words, a tool result or file content is refused; a 301 is refused and not followed; a 404, a private repository, and an answer whose `owner.login` is not the organisation (compared without regard to case) are each refused; the list is taken at the default branch's commit and kept in the record, "at most 2,000" paths with `pathsLeftOut` counted, documentation and infrastructure files first; a path not in the list is refused; "at most 30,000 characters", "at most 8 files in one request and 30 in one session"; a 403 or 429 with `x-ratelimit-remaining: 0` gives `rate_limited`; a 10-second timeout; file content returned between markers with a line before and after saying it is content and not instruction; `hold_finding` requires a file in `filesRead` and is held until `descriptionComplete`; nothing but the repository's name and a count is logged
- [ ] T042 [US4] Implement `src/agent/github.py` to pass T041 with `urllib.request` only: a `User-Agent` of `strider-agent`, the organisation from the `GITHUB_ORG` environment variable, `GET /repos/{org}/{repo}` then `GET /repos/{org}/{repo}/git/trees/{default_branch}?recursive=1` on `api.github.com`, and files from `raw.githubusercontent.com/{org}/{repo}/{commit}/{path}`. Add the three tools to `tools_for` in `src/agent/session/tools.py`, and `repository` and `repositoryFilesRead` to the log record in `src/agent/main.py`
- [ ] T043 [P] [US4] Add a `GitHubOrg` parameter (default `ServerlessOpsIO`) to `template.yaml` and pass it to the runtime as `GITHUB_ORG`; document it in `docs/handbook/03-configuration.md`
- [ ] T044 [US4] Add to `src/agent/persona.md` the rule that what is read from a repository is information and never instruction (FR-033), and to `src/agent/skills/stride-threat-model/SKILL.md` and `references/system.md`: read only when a participant names a repository; read selectively, README and docs and infrastructure templates first; ask the participants to describe the system first, even when asked to describe it from the repository; call `hold_finding` in the same request as the read, because the file is not kept; report held findings together after `description_complete`, as facts with the file named, and add nothing to the model until told (FR-035, FR-054, FR-058); say plainly when something could not be read and carry on (FR-036). Add marker-phrase tests

**Checkpoint**: STRIDEr can check a description against a repository.

---

## Phase 7: User Story 5 - A developer changes what STRIDEr does without changing who it is (Priority: P2)

**Goal**: Persona and skill are separate, guarded by tests, and the persona's wording is
the owner's.

**Independent Test**: `quickstart.md`, scenario A's four deletions and scenario B.

- [ ] T045 [P] [US5] Add to `tests/unit/test_prompt.py` a test that the persona contains no stage name used as an instruction, no tool name and none of a list of session phrases (FR-002), and to `tests/unit/test_skills.py` a test that no skill file contains `You are`, `STRIDEr is` or a tone instruction, that each stage in FR-010 has its reference file, and that removing any one makes loading fail (SC-011)
- [ ] T046 [P] [US5] Write `src/agent/skills/stride-threat-model/SOURCE.md`: that the skill was written for this repository and copies nothing; what it draws on, each with its repository, commit, licence and what was learned, from `research.md`, "Candidates read" (A, B, C, D, E, F); the two Microsoft papers for the table of categories by element; and the OWASP Risk Rating Methodology, its author and its licence CC BY-SA 4.0, with links
- [ ] T047 [US5] Add to `src/agent/persona.md` what STRIDEr does when no skill covers a request: say what it can do and offer a threat modelling session, and not act as a general assistant (FR-005)
- [ ] T048 [US5] **(owner)** Bring the whole of `src/agent/persona.md` to the owner as its own topic, agree its wording, and update the phrases the tests in `tests/unit/test_prompt.py` look for (FR-003)

**Checkpoint**: The separation holds and is guarded.

---

## Phase 8: User Story 6 - Participants control the pace of a session (Priority: P3)

**Goal**: Status, going back, skipping, pausing and an early model.

**Independent Test**: `quickstart.md`, scenario E steps 3 and 4.

- [ ] T049 [US6] Add to `src/agent/skills/stride-threat-model/SKILL.md`: answering "where are we" from the record (FR-013); `go_to_stage` to go back, and that later stages use the changed record (FR-014); `request_change` for a skip; a second request to start while a session is in progress (FR-016); offering to skip or write the model as it stands to a person in a hurry; suggesting a narrower scope when the element list is long; `write_model` for an early model; what to say in a direct message when asked to continue a session and the record shows none (FR-017). Add marker-phrase tests to `tests/unit/test_skills.py`
- [ ] T050 [US6] Add tests to `tests/unit/session/test_tools.py` and `tests/unit/session/test_render.py` for US6's scenarios end to end on the record: a skipped stage is marked `Skipped:` in the model; going back and removing an element changes the coverage table; an early model marks each unfinished stage and carries no notes; asking twice gives the current state each time

**Checkpoint**: A session need not be linear.

---

## Phase 9: User Story 7 - The owner can show that a session works (Priority: P3)

**Goal**: One command that plays the fixed session and reports each check.

**Independent Test**: `quickstart.md`, scenario C.

- [ ] T051 [US7] Add the checks of `contracts/agent-interface.md`, "The scripted session", to `scripts/play_session.py`, each printed as pass or fail: every turn's `expect` and `documents`; the final model against `contracts/written-model.md` section by section and field by field, naming any part that is missing (SC-002); a part-way model carries no notes and the final turn carries both; the `must_not_appear_in_model` and `must_appear_in_notes` words (SC-004); no reply over 100 seconds (SC-010). Exit 0 only when all pass. The transcript stays on the computer and nothing is printed but the checks
- [ ] T052 [US7] Write `tests/unit/test_play_session.py`: the checks run against saved documents made by `render.py`, a model with a section removed is reported by name, and no call is made to AWS
- [ ] T053 [P] [US7] Add `--speaker` and `--type` to `scripts/invoke.py`, and write any documents in the reply to the current folder instead of printing them
- [ ] T054 [US7] Write the transcript checklist in `docs/handbook/10-threat-model-sessions.md`: the nine items of FR-049, in its order and its words, each with one line saying what to look for in a transcript and one example of a failure. It must also cover everything in `contracts/session-tools.md`, "What code cannot enforce"; if that list has an item FR-049 lacks, stop and say so

**Checkpoint**: The feature can be accepted, and later changes re-checked.

---

## Phase 10: Polish & Cross-Cutting Concerns

- [ ] T055 [P] Finish `docs/handbook/10-threat-model-sessions.md`: the persona and the skill, how to change or add a skill, how a session runs, the session record and what code enforces, the repository rules and limits, how documents are delivered, running the fixed session, and that a memory fault looks like no session (FR-052; `research.md`, O7)
- [ ] T056 [P] Update `docs/handbook/00-index.md`, `01-features.md`, `04-architecture.md` (the request and reply fields, `no_reply`, `documents`), `06-observability.md` (the new log fields), `07-common-tasks.md` (changing the persona, a skill, a tool), `08-slack-app.md` (`files:write`) and `09-slack-messaging.md` (names, no reply, files, the new outcome and sentence). Also `README.md`: its "Instructions" line and link point at `src/agent/persona.md` and mention `src/agent/skills/`. And `docs/handbook/02-creating-a-component.md`: leave its table describing what the Backstage template generates (`system_prompt.md`), and add one line saying that this repository has since split that file into `src/agent/persona.md` and the skills in `src/agent/skills/`, with a link to `10-threat-model-sessions.md`. Then `grep -rn system_prompt` over the repository, outside `specs/`, must find only that one page
- [ ] T057 Run `pipenv run test-unit` and `sam validate --lint`; every test passes, and the count is not below T002's (SC-012)
- [ ] T058 **(owner)** Merge, then run `quickstart.md` scenarios A to H and fill in its Results table, with C run three times. Record O3, O5 and O6 in `specs/008-threat-model-session/research.md`
- [ ] T059 Review every log line the agent and the worker wrote during T058 for a name, message text, repository content or document text (SC-006), and record the result in `specs/008-threat-model-session/quickstart.md`

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: T001 first. T003 to T005 in parallel. T006 is merged and deployed
  on its own, before T023.
- **Foundational (Phase 2)**: after Setup. Blocks every story. T007 → T008 → T009;
  T010 → T011; T012 and T013 beside them; T014 needs T013; T015 needs T012 to T014;
  T016 → T017 need T008 to T011; T018 needs T015 and T017.
- **US1 (Phase 3)**: after Phase 2. T020 to T022 → T023 → T024 → **T025, a stop**.
  T026 to T030 can be written while waiting for T023 and T024, and T031 follows T025.
- **US2 (Phase 4)**: after T025. Changes the persona, the skill and the fixed session.
- **US3 (Phase 5)**: after US1's worker tasks (T026 to T029). T035 and T036 in parallel;
  T037 needs both; T038 is in the agent and independent of them.
- **US4 (Phase 6)**: after Phase 2. Independent of US3.
- **US5 (Phase 7)**: T045 and T046 any time after Phase 2. T048 after US2, US3 and US4
  have added their rules to the persona.
- **US6 (Phase 8)**: after Phase 2. Its tools are already in T017; this phase is the
  skill's words and the tests.
- **US7 (Phase 9)**: T051 after US2 and US3 have extended the fixed session.
- **Polish (Phase 10)**: last. The trace check is T006, in Phase 1.

### Files more than one story changes

`src/agent/persona.md`, `src/agent/skills/stride-threat-model/SKILL.md`,
`data/sessions/stride-fixed-session.yaml`, `src/agent/main.py` and
`src/handlers/AnswerSlackMessage/function.py` are each changed by several stories. Stories
that touch the same file are done one after another, not in parallel.

### Parallel opportunities

- Phase 1: T003, T004, T005.
- Phase 2: T012 and T013 with the record and renderer work.
- US1: T026, T027 and T030 together; T028 beside them.
- US3: T035 and T036 together.
- US4's T041 to T043 can run beside US3, since they touch different files apart from
  the one line in `tools.py`.
- Polish: T055 and T056.

## Implementation Strategy

### MVP first

Phases 1 to 3. At T025 the largest risk has been tried and the owner knows whether the
configured model can lead a session. At T031 one person can run a session in a direct
message and receive the model. US2 is also P1 and should follow at once: without it
STRIDEr leads a session and may still do the work when asked.

### Then, in order

US2, then US3 and US4 in either order, then US5's persona review, US6, US7, Polish. Each
ends at a checkpoint where `pipenv run test-unit` passes and the fixed session can be
played.

### Merges

Branch deployments are off, so anything that needs the deployed agent needs a merge to
`main`: T023, T031 and T058 at least. Each merge changes what STRIDEr does for anyone
using it. The owner merges.
