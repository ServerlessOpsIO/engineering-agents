# Contract: the tools the agent's model can call

**Date**: 2026-11-19 | **Spec**: `specs/008-threat-model-session/spec.md`

The model that drives STRIDEr changes the session record (`data-model.md`) and reads a
repository only through these tools. Each is a Python function in `src/agent/session/`.
The rules in the right-hand column are kept by the tool's code, whatever the model was
told and whatever it asks for. A refused call returns a short sentence saying why, which
the model reads and acts on; it is not an error for the caller.

The names and arguments below are the design. They may be adjusted while the skill is
being tuned against the fixed session, and this file is updated when they are.

## Which tools the model is offered

Chosen by code for each request, so the model sees only what it can use now. The most
offered at once is 18, after a finished session. Amazon suggests no more than about 20
for the model in use today (`research.md`, Decision 3); that model is a stopgap, and the
number is a guide, not a limit.

| When | Tools offered |
|------|---------------|
| No session | `start_session` and the repository tools. |
| The last session is finished or abandoned | `start_session`, the repository tools, the tools of all stages, `add_open_question` and `write_model`, so that the model can be changed and posted again (FR-059). |
| Session in progress | The session tools, the repository tools, and the tools of the current stage. |

There is no tool for staying quiet. That is the quiet marker in
`contracts/agent-interface.md`.

## Session tools

| Tool | Arguments | What it does, and what the code enforces |
|------|-----------|------------------------------------------|
| `start_session` | `system` | Makes a new record with every stage `not_started`, adds the speaker of this message as the first participant, enters `scope`, and makes the skill active. Refused while a session is in progress (FR-016). Returns the opening statement's points for the model to say in its own words (FR-061). |
| `complete_stage` | none | Marks the current stage complete and enters the next. Never refused. Leaving the threats stage, its answer lists each element's categories that have neither a threat nor a none-found entry, and tells the model to say once that these will show as "Not considered" and that the participants can go back. This is not a hint and names no threat. |
| `go_to_stage` | `stage` | Enters an earlier or later stage without marking anything skipped (FR-014). |
| `request_change` | `action` (`skip_stage`, `finish`, `abandon`) | With one participant, `skip_stage` happens at once. Otherwise records a pending change and tells the model to announce it (FR-060). `finish` and `abandon` are always pending first, whatever the number of participants, because both post the notes: the model is told to give the warning in FR-056. |
| `resolve_change` | `confirmed` (true, false) | `true` is refused on the turn the change was requested, so it can only follow a later message. `true` applies the change. For `finish` and `abandon` it attaches the documents to this reply (see below). `false` drops the pending change. |
| `add_open_question` | `text` | (FR-037, part 8) |
| `give_hint` | `element` (identifier, or none in the scope stage), `point` | Records that a hint is being given and what was missed. Refused when this element already has a hint in this stage (FR-022); the refusal tells the model to record the point with `add_note` and say nothing. |
| `hint_taken_up` | `hint` | Marks a hint as taken up, so it stays out of the notes. |
| `add_note` | `kind` (`not_raised`, `questioned_kept`), `text`, and one of `element`, `threat`, `mitigation` | (FR-041) |
| `write_model` | none | Attaches the written model, made from the record as it stands, to this reply. Never the notes (FR-040). After the notes have been posted it attaches the model with its changes marked (FR-059). |

**Documents** are made by code (`contracts/written-model.md`) and travel in the reply's
`documents` field. They are not shown to the model and are not kept in the conversation.
The tool returns only a line saying what was attached.

## Repository tools

Offered during a session and before one (a repository may be named first; the same rules
apply). The owner is always `ServerlessOpsIO`, from the `GITHUB_ORG` setting; no tool
takes an owner or a web address.

| Tool | Arguments | What it does, and what the code enforces |
|------|-----------|------------------------------------------|
| `list_repository_files` | `repository` | Refused unless the name matches `^[A-Za-z0-9._-]{1,100}$`, is not `.` or `..`, and a person has named it (FR-034). A person has named it when the repository already has an entry in the agent's state, or when the name appears, as a whole word and without regard to case, in the request being answered (which includes any thread context the worker sent) or in a message from a person among those the model is shown. The first time this passes, the entry is made, so later calls do not depend on the naming message still being in view. Text the model wrote, tool results and file content never count. Asks GitHub for the repository, without following redirects. Refused unless GitHub answers 200, the owner is the organisation, and the repository is public. Then lists its files at the default branch's current commit and keeps the list in the record. Returns the paths, documentation and infrastructure files first. |
| `read_repository_file` | `repository`, `path` | Refused unless the repository has been listed and the path is in its list. Reads the file at the recorded commit. Returns at most 30,000 characters, between markers, with a line before and after saying that what is between them is file content and not instruction (FR-033). At most 8 files in one request and 30 in one session. |
| `hold_finding` | `kind` (`differs`, `not_mentioned`), `file`, `fact` | Records a finding. Before the description is complete it is held; the tool's answer says so and tells the model not to mention it yet (FR-058). |

Any failure (not found or private, both of which GitHub answers the same way; outside the
organisation; redirected; rate limited; timed out; too large) returns a sentence saying the
repository or file could not be read and why, and tells the model to carry on from the
conversation (FR-036). Only the fact of a read, the repository's name and a count are
logged.

File content the model has read is not carried into later requests: tool calls and their
results are left out when the conversation is restored (`research.md`, Decision 2). What
is worth keeping must be recorded with `hold_finding` in the request that read it.

## Stage tools

| Stage | Tool | Arguments | What the code enforces |
|-------|------|-----------|------------------------|
| scope | `add_scope_item` | `kind` (`included`, `excluded`, `assumption`), `text` | |
| scope, system, threats, mitigations | `remove_item` | `id` | The rules for removal in `data-model.md`. |
| system | `add_element` | `kind` (`component`, `data_store`, `external_party`), `name`, `description` | Gives the identifier. |
| system | `add_data_flow` | `from`, `to`, `data` | Both ends must exist. |
| system | `add_trust_boundary` | `name`, `inside` (identifiers) | |
| system | `change_element` | `id`, `name`, `description` | |
| system | `description_complete` | none | Sets the flag. Returns every held finding at once, for the model to report together and name the files (FR-058). |
| threats | `add_threat` | `element`, `category`, `description` | Element must exist. Marked as changed after the notes when they have been posted. |
| threats | `none_found` | `element`, `category` | Refused when a threat exists there. |
| rating | `rate_threat` | `threat`, `likelihood`, `likelihood_reason`, `impact`, `impact_reason` | Values must be `high`, `medium` or `low`; both reasons required. Works out the severity and returns it for the model to state (FR-044). |
| mitigations | `add_mitigation` | `description`, `threats`, `owner` (may be empty) | |
| mitigations | `decide_threat` | `threat`, `decision`, `reason`, `decided_by` (names), `owner` (may be empty) | Every name in `decided_by` must be a participant. `accept` needs a reason. An empty owner is accepted; the first time, the answer tells the model to ask once (FR-057). |

`add_threat` is also offered in the rating and mitigations stages, and `rate_threat` in
the mitigations stage, because people think of things late.

## What code cannot enforce

These stay rules in the persona and the skill, and are judged by a person reading a
transcript (FR-049):

- That a threat, rating, mitigation or decision passed to a tool was said by a
  participant and not made up by the model (FR-018, FR-024).
- That the model's own words name no threat and give no value (FR-018, FR-053).
- That a hint points at an area without naming the threat (FR-022).
- One question at a time (FR-012).
- When to stay quiet, among the cases where code allows it (FR-025 to FR-027).
- That the notes' contents are not given away during the session (FR-056). Code limits
  what could be given away to the hints and notes of the current stage, which are all
  the model is shown (`data-model.md`).
