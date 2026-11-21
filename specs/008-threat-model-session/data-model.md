# Data Model: STRIDEr Leads a Threat Modelling Session

**Date**: 2026-11-19 | **Spec**: `specs/008-threat-model-session/spec.md`

There is still no database. A session lives in two places, both in the agent's memory of
the conversation (AgentCore Memory, kept 7 days by default):

- **The session record**: structured data the agent keeps as its state. Everything the
  written model is made from is here. The agent's code writes it, through tools the model
  calls (`contracts/session-tools.md`).
- **The conversation**: the messages. Only the most recent are shown to the model
  (`research.md`, Decision 2), so nothing that matters may live only here.

Names, message text and repository content are in both. Neither is ever logged (FR-050).

## What the agent keeps in its state

Five keys, saved and restored with the conversation.

| Key | Holds | Exists |
|-----|-------|--------|
| `session` | The session record, below. | From the start of a session. A new session replaces it. |
| `repositories` | The repositories people have named, and what was listed and read ("Repository", below). | From the first repository named, which may be before any session. |
| `lastMessageId` | The `messageId` of the request being handled, or last handled. | From the first request that carries one. |
| `lastMessageDone` | Whether the handling of the last message reached its end. Set false when a message is taken up and true when its reply is ready. | From the first request. |
| `sessionBefore` | `session` and `repositories` as they were before the current message ("A request that is repeated", below). | From the first request that carries a `messageId`. |

## Session record

Kept under the key `session` in the agent's state. One per conversation, so one session
at a time per thread and per direct message (FR-016). Absent until a session starts.

| Field | Type | Rules |
|-------|------|-------|
| `skill` | string | The skill leading the session: `stride-threat-model`. |
| `status` | `in_progress` \| `finished` \| `abandoned` | A new session may start only when there is none or the last is `finished` or `abandoned`. Starting one replaces the record. |
| `system` | string | The system's name, as the participants gave it. |
| `startedOn` | date | UTC date of the first message of the session. |
| `turn` | integer | Counts messages since the session started, including after it has ended. Used to tell "the next message" from the same one (FR-060). A repeated request for the same message sees the same turn as the first attempt. |
| `stage` | stage name | The current stage. |
| `stages` | map of stage name to `not_started` \| `in_progress` \| `complete` \| `skipped` | Stage names: `scope`, `system`, `threats`, `rating`, `mitigations`, `model` (FR-010). |
| `participants` | list of names | People who wrote while the session was in progress, in order of first message. Added by code from each request's `speakerName`, never by the model. |
| `joinedAfter` | list of names | People who first wrote after the session was finished or abandoned. Added by code in the same way. They can make changes and decisions, each of which is marked as made after the notes. |
| `scope` | list of scope items | |
| `elements` | list of elements | |
| `boundaries` | list of trust boundaries | |
| `descriptionComplete` | boolean | Set when the participants say their description of the system is complete (FR-058). |
| `findings` | list of repository findings | |
| `threats` | list of threats | |
| `noneFound` | list of (element, category) | Where the participants looked and chose to record no threat. |
| `mitigations` | list of mitigations | |
| `openQuestions` | list of open questions | |
| `hints` | list of hints | |
| `notes` | list of notes | |
| `pending` | pending change, or none | |
| `notesPostedOnTurn` | integer, or none | Set when the facilitator's notes are posted. |
| `replaceWarnedOnTurn` | integer, or none | The turn on which STRIDEr was told to say that starting a new session replaces this ended one. A new session can start on a later turn (FR-016). |
| `counters` | map of prefix to integer | The last number given for each kind of identifier, so none is reused. |
| `endWarned` | boolean | Set once STRIDEr has been told to warn that a channel thread has less than a day left, so it warns once (FR-015). |
| `removedAfterNotes` | list of identifiers | Threats and mitigations removed after the notes were posted, so that the written model can say so (FR-059). |

### A request that is repeated

The Slack worker asks the agent a second time when the first attempt fails, and the first
attempt may already have changed what the agent keeps. So the agent keeps a copy of
`session` and `repositories` as they were before the current message, under the key
`sessionBefore`. `lastMessageId` is a key of its own, so the rule works when there is no
session.

| When a request arrives | The agent |
|---|---|
| Its `messageId` differs from `lastMessageId`, or it has none | Copies `session` and `repositories` to `sessionBefore`, sets `lastMessageId`, and advances `turn` when a session is in progress. |
| Any request, when `lastMessageDone` is false | First puts `sessionBefore` back as `session` and `repositories`. The message before never finished, so nothing from it stays recorded (FR-063). Then one of the two rows below applies. |
| Its `messageId` equals `lastMessageId` | Puts `sessionBefore` back as `session` and `repositories`, then advances `turn` as the first attempt did, so the repeat sees the same turn. Whatever the first attempt recorded is undone, and this attempt records it once. |

This covers a session that the first attempt started: `sessionBefore` then holds "no
session". The conversation itself still holds the message twice, as it has since feature
007.

### Identifiers

Given by code, never by the model, and never reused in a session.

| Kind | Form |
|------|------|
| Component | `C1`, `C2` … |
| Data store | `DS1` … |
| External party | `EP1` … |
| Data flow | `F1` … |
| Trust boundary | `TB1` … |
| Threat | `T1` … |
| Mitigation | `M1` … |
| Open question | `Q1` … |
| Scope item, finding, hint, note | `S1`, `R1`, `H1`, `N1` … (not shown in the written model) |

### Scope item

| Field | Type | Rules |
|-------|------|-------|
| `id` | identifier | |
| `kind` | `included` \| `excluded` \| `assumption` | |
| `text` | string | |

### Element

| Field | Type | Rules |
|-------|------|-------|
| `id` | identifier | Its letters say its kind. |
| `kind` | `component` \| `data_store` \| `external_party` \| `data_flow` | |
| `name` | string | |
| `description` | string | May be empty. |
| `from`, `to` | element identifiers | Data flows only. Both must exist and not be data flows. |
| `data` | string | Data flows only: what travels. |

Removing an element removes its data flows, its `noneFound` entries and its place in any
boundary. It is refused while a threat names it.

**Removing other things** (`remove_item`):

| Removed | What follows |
|---------|--------------|
| A threat | It is taken out of every mitigation's `threats`. A mitigation left with none is removed too, and the tool's answer says so. |
| A mitigation, a trust boundary, a scope item, an open question | Nothing else changes. |
| A threat or a mitigation, after the notes were posted | Its identifier is added to `removedAfterNotes`. |

Hints, notes and findings cannot be removed.

**STRIDE categories that apply to each kind** (`research.md`, Decision 9). The coverage
table has a cell for each:

| Kind | S | T | R | I | D | E |
|------|---|---|---|---|---|---|
| External party | yes | | yes | | | |
| Component | yes | yes | yes | yes | yes | yes |
| Data flow | | yes | | yes | yes | |
| Data store | | yes | yes | yes | yes | |

A threat may still be recorded against a category that does not normally apply, when the
participants say so. The coverage table then gains that cell.

### Trust boundary

| Field | Type | Rules |
|-------|------|-------|
| `id` | identifier | |
| `name` | string | |
| `inside` | list of element identifiers | Components, data stores and external parties. A data flow crosses a boundary when its two ends are not on the same side. |

### Threat

| Field | Type | Rules |
|-------|------|-------|
| `id` | identifier | |
| `element` | element identifier | Must exist. |
| `category` | `spoofing` \| `tampering` \| `repudiation` \| `information_disclosure` \| `denial_of_service` \| `elevation_of_privilege` | |
| `description` | string | The participants' words, or a faithful shortening. |
| `likelihood`, `impact` | `high` \| `medium` \| `low`, or none | Given by the participants (FR-042). |
| `likelihoodReason`, `impactReason` | string | Required with the value. |
| `severity` | `note` \| `low` \| `medium` \| `high` \| `critical`, or none | Worked out by code from the table in FR-044 whenever both values are present. Never supplied by the model. |
| `decision` | `mitigate` \| `accept` \| `transfer` \| `avoid`, or none | (FR-046) |
| `decisionReason` | string | Required when the decision is `accept`. |
| `decidedBy` | list of names | Each must be in `participants` or `joinedAfter` (FR-057). |
| `owner` | string, or none | As the participants wrote it. May be a person outside the session or a team. |
| `ownerAsked` | boolean | Set once STRIDEr has asked for an owner, so it asks once. |
| `changedAfterNotes` | boolean | Set by code when the threat is added or changed after the notes were posted (FR-059). |

Adding a threat removes any `noneFound` entry for the same element and category.

### Mitigation

| Field | Type | Rules |
|-------|------|-------|
| `id` | identifier | |
| `description` | string | |
| `threats` | list of threat identifiers | At least one. Each must exist. |
| `owner` | string, or none | |
| `changedAfterNotes` | boolean | As for a threat. |

### Open question

| Field | Type | Rules |
|-------|------|-------|
| `id` | identifier | |
| `text` | string | What the participants could not answer or agree. |

### Repository

An entry is made the first time a repository passes the check that a person named it
(FR-034). From then on the entry is the proof: the check does not depend on the naming
message still being among the messages the model is shown.

| Field | Type | Rules |
|-------|------|-------|
| `name` | string | The repository's name within `ServerlessOpsIO`, as the person wrote it until GitHub answers, then in GitHub's spelling. Compared without regard to case. |
| `listed` | boolean | False until its files have been listed. The fields below are empty until then. |
| `commit` | string | The commit the file list was taken at. Every file is read at this commit. |
| `paths` | list of strings | The repository's file paths, at most 2,000, so that later requests list nothing again. |
| `pathsLeftOut` | integer | How many paths did not fit. |
| `filesRead` | list of paths | In the order read. Named in the written model (FR-035). |
| `unread` | string, or none | Why something could not be read: `rate_limited`, `too_large`, `unavailable`. |

Rules for where this sits beside a session:

- **Before a session**: a repository can be named, listed and read. Nothing can be
  recorded as a finding, because findings belong to a session; `hold_finding` is not
  offered.
- **When a session starts**: the entries are kept, so a repository named just before is
  still named. Each entry's `filesRead` is emptied, so the written model lists only files
  read during the session, and the limit of 30 files counts from the start of the session.
- **A repeated request** restores the entries with the record.
- **The written model** is made from the record and the entries together.

A repository nobody named leaves no entry. One that was named and then refused by GitHub
(private, missing, outside the organisation) keeps its entry with `listed` false, and is
asked for again only when a tool is called for it again.

### Repository finding

What STRIDEr found in a repository that bears on the participants' description.

| Field | Type | Rules |
|-------|------|-------|
| `id` | identifier | |
| `kind` | `differs` \| `not_mentioned` | (FR-035, FR-054) |
| `repository` | string | The repository the file is in. Must have an entry. |
| `file` | path | Must be in that repository's `filesRead`. |
| `fact` | string | Stated as a fact about the repository. |
| `reported` | boolean | False while it is held back. Findings made before `descriptionComplete` stay unreported until then, and are handed to the model together at that moment (FR-058). |

### Hint

| Field | Type | Rules |
|-------|------|-------|
| `id` | identifier | |
| `stage` | stage name | |
| `element` | element identifier, or none in the scope stage | At most one hint for each (`stage`, `element`). Code refuses a second (FR-022). |
| `point` | string | What STRIDEr saw missed. Written for the notes, not for the session. |
| `takenUp` | boolean | Set when the participants raise the point after the hint. |

### Note

An entry for the facilitator's notes that is not a hint.

| Field | Type | Rules |
|-------|------|-------|
| `id` | identifier | |
| `kind` | `not_raised` \| `questioned_kept` | `not_raised`: a missed point the hint limit kept STRIDEr from hinting at. `questioned_kept`: a rating or mitigation STRIDEr questioned and the participants kept (FR-041). |
| `stage` | stage name | |
| `element`, `threat`, `mitigation` | identifier, or none | What it is about. |
| `text` | string | For `questioned_kept`: what was questioned. |

The facilitator's notes are every hint with `takenUp` false, then every note.

### What the model is shown of hints and notes

The record's summary, which the model is given on every request, shows:

| | Shown |
|---|---|
| Hints and notes made in the current stage | In full, so that STRIDEr can tell when a hint is taken up and does not record a point twice. Under a line saying they must not be revealed before the session ends. |
| Hints and notes made in other stages | For each element, whether its hint in that stage has been used; and a count of notes. No text. |

So what STRIDEr could give away, if asked, is limited to the stage in hand. The rule
against giving it away (FR-056) is still an instruction to the model.

### Pending change

A request to skip a stage, finish or abandon that STRIDEr has announced and not yet acted
on (FR-060).

| Field | Type | Rules |
|-------|------|-------|
| `action` | `skip_stage` \| `finish` \| `abandon` | |
| `stage` | stage name | For `skip_stage`: the stage the session was in when the skip was asked for. Only the current stage can be skipped. |
| `announcedOnTurn` | integer | The change can be confirmed only on a later turn. |

At most one change is pending. A message that objects drops it (`resolve_change` with
`confirmed` false), and a new request is needed later; asking for a change while one is
pending replaces it and must be announced afresh.

With one participant, `skip_stage` is applied at once and nothing is pending. `finish`
and `abandon` are always announced first, because both post the notes and FR-056
requires a warning before that.

## Stage and status transitions

```text
no session ──start──▶ in_progress ──finish (confirmed)──▶ finished
                           │                                  │
                           └──abandon (confirmed)──▶ abandoned │
                                                               ▼
                            finished: the record can still be changed; each change is marked
```

- Stages are normally entered in order, by completing the one before. `go_to_stage` can
  enter any stage, earlier or later. Entering a stage sets it `in_progress`. The stage
  that was left keeps the status it had, so a stage left unfinished stays `in_progress`
  and is shown as not finished. Going back leaves later stages as they were; they read
  the changed record (US6, scenario 3).
- A stage becomes `complete` only through `complete_stage`, and `skipped` only through a
  confirmed `skip_stage`. Both then enter the next stage in order.
- Completing or skipping the system stage sets `descriptionComplete` only when it is
  completed, not when it is skipped (`contracts/session-tools.md`).
- In the last stage, `model`, there is no next stage. `complete_stage` marks it complete
  and its answer tells the model to ask whether the participants want to finish.
- A confirmed `finish` marks the `model` stage complete and changes no other stage's
  status. A session can therefore be finished with stages skipped or not finished, and
  the written model says so.
- `finish` posts the written model and the facilitator's notes, sets `status` to
  `finished` and sets `notesPostedOnTurn`. The notes are first produced this way or by
  `abandon`, and no other. After that, asking for the model gives the notes again as
  well, so that a file that failed to arrive can be had. Their content cannot change:
  no hint or note can be added once the session has ended.
- `abandon` posts the written model as it stands, with its unfinished stages marked, and
  the notes, and sets `status` to `abandoned` and `notesPostedOnTurn`. Nobody has to ask.
- A new session can start once the status is `finished` or `abandoned`.

## Written model and facilitator's notes

Two Markdown documents, made by code from the session record. The model that drives
STRIDEr does not write either. Their format is `contracts/written-model.md`. Neither is
kept: each is made again from the record when asked for.

## Agent request and reply

The full interface is `contracts/agent-interface.md`. What changes from feature 007:

| Field | Direction | Change |
|-------|-----------|--------|
| `speakerName` | request | New. The writer's name as Slack displays it. |
| `conversationType` | request | New. `channel_thread` or `direct_message`. |
| `addressed` | request | New. Whether the message mentions STRIDEr. |
| `messageId` | request | New. Identifies the message, so that a repeated request is recognised. |
| `threadEndsAt` | request | New. When a channel thread will stop being answered. |
| `prompt` | request | Mentions of people are now names, not Slack identifiers, here and in thread context. |
| `kind` `no_reply` | reply | New. The worker posts nothing. |
| `documents` | reply | New. Documents for the worker to deliver as files. |

## Receiving service

### Person's name

Not stored. Looked up from Slack by the worker with the `users.info` call it already makes
for the membership rule, and remembered with the membership answer for an hour.

| Rule | |
|------|---|
| Source | `profile.display_name`; when empty, `profile.real_name`; when empty, `real_name`. |
| Cleaning | Line breaks and control characters removed, runs of spaces made one, `<`, `>`, `[`, `]` and backticks removed, cut to 80 characters. Square brackets go because the message is given to the model as `[From: name]`. The agent cleans the name again. |
| Unknown | When Slack cannot say, or nothing is left after cleaning: `Someone`. A name that cannot be found never stops a message being answered. |
| Mentions in text | `<@U…>`, `<@W…>` and either with `\|label` become the person's name, for up to 10 different people in a message; further ones become `someone`. STRIDEr's own mention is removed as before. |
| Thread context | Each earlier message is given with its writer's name in place of `<@U…>`. |

### Outcomes

Added to feature 007's table.

| Outcome | Reason | Meaning | Person sees |
|---------|--------|---------|-------------|
| `no_reply` | | The agent judged that the message needed nothing from it (FR-029). | The eyes appear and go. Nothing is posted. |
| `failed` | `document_not_posted` | The agent answered and a document could not be delivered. | The reply, and the document-not-posted sentence. |

The cleanup function needs no change. After a `no_reply` the eyes are gone, which it
already reads as nothing owed.

### Fixed sentences

| Name | Text |
|------|------|
| Document not posted | I couldn't post the document. Please ask me for it again. |

### Log records

Worker, added: `documents` (how many were delivered), `namesLookedUp` (how many people's
names were looked up). No name.

Agent, added: `skill` and `stage` when a session is in progress; `toolCalls` (how many);
`repository` (name) and `repositoryFilesRead` (how many) when a repository was read in
this request; `documents` (how many). `kind` may now be `no_reply`. No name, no path, no
text.

## Skill

A folder under `src/agent/skills/`, in the Agent Skills format.

| File | Holds |
|------|-------|
| `SKILL.md` | Front matter (`name`, `description`, `license`, `allowed-tools`, `metadata`) and the instructions for the whole session. |
| `references/<stage>.md` | One per stage. Only the current stage's file is given to the model. |
| `SOURCE.md` | Where the skill and anything it restates came from, and under what licence (FR-008). Required for every skill, adopted or written here, and it must name a licence. The agent does not start without it. |

`metadata.stages` lists the stage names in order, which is how the code knows which
reference file to give. `allowed-tools` lists the tools the skill uses.
