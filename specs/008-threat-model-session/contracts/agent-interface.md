# Contract: the agent's interface

**Date**: 2026-11-19 | **Spec**: `specs/008-threat-model-session/spec.md`

What a caller sends the agent and gets back, after this feature. Callers are the Slack
worker (`src/common/common/agentcore.py`), `scripts/invoke.py` and the new
`scripts/play_session.py`. The call itself is unchanged: `InvokeAgentRuntime` with the
caller's IAM role and a `runtimeSessionId`.

## Request

```json
{
  "prompt": "we terminate TLS at the gateway",
  "speakerName": "Ana Souza",
  "conversationType": "channel_thread",
  "addressed": false,
  "messageId": "C0123ABCD:1795123201.951000",
  "threadEndsAt": "2026-11-26T14:00:01Z",
  "slackUserId": "U012AB3CD"
}
```

| Field | Required | Rules |
|-------|----------|-------|
| `prompt` | yes | As in feature 007. At most `MaxPromptChars`. People are named, not given as Slack identifiers. |
| `speakerName` | no | Who wrote the message. Cleaned again by the agent as in `data-model.md`. Missing or empty: `Someone`. |
| `conversationType` | no | `channel_thread` or `direct_message`. Missing or anything else: `direct_message`, so that a caller that says nothing always gets a reply. |
| `addressed` | no | True when the message mentions STRIDEr. Missing: true. |
| `messageId` | no | Identifies the message being answered. The Slack worker sends `{channel}:{ts}`. A second request with the same value in the same conversation is a retry: the agent first undoes what the earlier attempt recorded (`data-model.md`, "A request that is repeated"). Missing: every request is a new message. Never logged with anything that names a person; it is the same pair the worker already logs. |
| `threadEndsAt` | no | For a channel thread: when the thread will stop being answered, which is its first message's time plus the memory period (feature 007). UTC. Not sent for a direct message. The agent gives it in the opening of a session and, when less than 24 hours remain, tells the model once to warn the participants and offer the model as it stands (FR-015). |
| `slackUserId` | no | Still ignored. |
| `actorId` | no | As before. The Slack worker still does not send it. |

**When STRIDEr may give no reply** is decided by code from the request, not by the model:
only when `conversationType` is `channel_thread`, `addressed` is false, and a session is
`in_progress`. In every other case the model is told a reply is required, and if it still
returns the quiet marker it is asked once more. If the marker comes back a second time,
the reply is kind `error`. The caller treats that as any failed attempt: the Slack
worker tries the request again and, if that fails too, posts the apology. A person who
addresses STRIDEr therefore always sees something (FR-027, FR-028).

## What the model is given

Assembled by `src/agent/prompt.py` **before every call to the model**, not once for each
request. One request can be several calls: the model calls a tool, the tool changes the
record, and the model is called again. So the instructions and the tools offered always
match the record as it stands. In the request that starts a session, the model's second
call already has the skill, the scope stage's reference file and the scope stage's tools.
Order matters: the model follows best what comes last (`research.md`, Decision 3).

1. The session record, rendered as text, when there is one.
2. The active skill's `SKILL.md` instructions, when a session exists: in progress,
   finished or abandoned. They stay after a session ends, because the model can still be
   changed (FR-059), and go only when a new session replaces the record.
3. The current stage's reference file.
4. The list of available skills: name and description of each.
5. The persona.

**The conversation** the model is given is the messages still in view, with tool calls
and their results left out (`research.md`, Decision 2). It must start with a person's
message and alternate. Where leaving tool traffic out, or a request that failed part-way,
leaves two messages from a person running, the agent joins them into one, each still
under its own `[From: …]` line.

The message is given as:

```text
[From: Ana Souza] [You may stay quiet]
we terminate TLS at the gateway
```

The second marker is `[A reply is required]` in every other case.

## Reply

```json
{
  "kind": "answer",
  "text": "Here is the model as it stands.",
  "documents": [
    {"filename": "threat-model-login-service.md", "title": "Threat model: login service", "markdown": "# Threat model: login service\n…"}
  ],
  "requestId": "…"
}
```

| `kind` | `text` | `documents` | Caller |
|--------|--------|-------------|--------|
| `answer` | The reply. Not empty. | None, one or two. | Posts the text, then delivers each document. |
| `no_reply` | Empty. | Never. | Posts nothing. Not a failure. |
| `input_rejection` | Why. | Never. | As in feature 007. |
| `error` (HTTP 500) | A generic sentence. | Never. | A failed attempt, as in feature 007. |

`documents` is left out when there are none. The two possible documents are the written
model and the facilitator's notes, in that order:

| Document | `filename` | `title` |
|----------|------------|---------|
| Written model | `threat-model-{system}.md` | `Threat model: {system}` |
| Facilitator's notes | `facilitator-notes-{system}.md` | `Facilitator's notes: {system}` |

In a filename, `{system}` is the system's name in lower case, with every run of other
characters made one hyphen, leaving letters, digits and hyphens only, and the whole
filename cut to 60 characters before `.md`. When nothing is left of the name the files
are `threat-model.md` and `facilitator-notes.md`. In a title the name is as the
participants gave it.

The quiet marker is the reply text `[[quiet]]` and nothing else. The agent turns it into
`no_reply`. It never reaches a caller as text. A reply that contains the marker along with
other words is an `answer`, with the marker removed.

## What the Slack worker does with a reply

Changes to feature 007's contract, section 3:

1. `no_reply`: post nothing; outcome `no_reply`. The eyes are removed as always.
2. `answer`: post the text in parts as before. Then, for each document, upload it as a
   file in the same thread (or in the direct message), with its title. If an upload fails
   after three tries, still try the next document, then post the document-not-posted
   sentence once; outcome `failed`, `document_not_posted`. Asking STRIDEr for the model
   again brings every document the session has released.
3. Before calling the agent, the worker looks up the writer's name and the names of
   people mentioned, and sends `speakerName`, `conversationType`, `addressed`,
   `messageId` and, for a channel thread, `threadEndsAt`.

A document's content is never logged, by the agent or the worker.

## The scripted session

`scripts/play_session.py` (`pipenv run play-session`) sends the turns of
`data/sessions/stride-fixed-session.yaml` to a deployed agent, one after another, in one
new session, and writes the transcript and the documents to `transcripts/`, which is
ignored by git (FR-048).

A turn:

```yaml
- speaker: Ana Souza
  type: channel_thread      # default
  addressed: false          # default
  text: "Ben, did we ever move the tokens out of local storage?"
  expect: no_reply          # answer | no_reply | any (default any)
  documents: 0              # how many documents the reply must carry (optional)
```

The command reports pass or fail for each of these:

- Every turn's `expect` and `documents`.
- The final written model against `contracts/written-model.md`, section by section and
  field by field (SC-002).
- A model asked for part-way carries no notes. The turn that confirms the finish carries
  both documents, which the turn's own `documents: 2` checks.
- When the session changes something after the notes, the last written model has at least
  one entry marked `†` and the line that explains the mark.
- Each word listed under `must_not_appear_in_model` is absent from the model, and each
  under `must_appear_in_notes` is in the notes (SC-004).
- No reply took longer than 100 seconds (SC-010).

It exits 0 only when all pass. What it cannot judge is in the checklist
(`docs/handbook/10-threat-model-sessions.md`), which a person reads the transcript
against (FR-049).
