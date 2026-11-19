# Implementation Plan: STRIDEr Leads a Threat Modelling Session

**Branch**: `feature/008-threat-model-session` | **Date**: 2026-11-19 | **Spec**: `specs/008-threat-model-session/spec.md`

**Input**: Feature specification from `specs/008-threat-model-session/spec.md`

## Summary

Give STRIDEr its purpose: it leads people through a STRIDE threat model in Slack, they do
the work, and it posts the written model.

What the agent is told is split in two. A **persona** says who STRIDEr is and the rules
that always hold. A **skill**, in the Agent Skills format, says how to lead a session,
with one reference file for each stage. No existing skill was suitable, so ours is
written here (`research.md`, the search).

The session itself is not left to the model's memory. The agent keeps a **session
record**: structured data holding the scope, the system's elements, the threats, their
ratings, the decisions and STRIDEr's notes. The model changes the record by calling small
tools, and code enforces the rules that can be counted. Code, not the model, writes the
model document and the facilitator's notes from the record, so their form is always right
and their length cannot break the reply limit. The model's own job is the conversation:
asking, explaining, prompting and knowing when to stay quiet.

Three more tools let the agent read files from a public `ServerlessOpsIO` repository,
with the limits kept in code.

The Slack worker changes in three ways: it sends each writer's name, it posts nothing
when the agent gives no reply, and it uploads the documents as files, which needs one new
Slack permission.

## Technical Context

**Language/Version**: Python 3.14. The agent runs in a container on AgentCore Runtime
(arm64); the worker on AWS Lambda. AWS SAM template.

**Primary Dependencies**: `strands-agents` 1.65.0 and `bedrock-agentcore` 1.26.0, both
already pinned and unchanged. From Strands: tools, agent state, and the `Skill` reader.
`slack_sdk` 3.47.0 in the worker, for the file upload. The Python standard library for
GitHub. **No new package.**

**Storage**: AgentCore Memory, as now: the conversation and the agent's state, kept 7
days. The session record is part of that state. No database. See `data-model.md`.

**Testing**: `pytest` through `pipenv run test-unit`, with a fake model, a fake GitHub
and fakes for Slack. No test contacts AWS, Slack or GitHub. The fixed session
(`pipenv run play-session`) runs by hand against the deployed agent. The rest is manual
and listed in `quickstart.md`.

**Target Platform**: AWS, the account and region the agent is in. Slack's Web API.
GitHub's public REST interface and `raw.githubusercontent.com`.

**Project Type**: Changes to an existing agent and one existing serverless function, a
new skill, and one script.

**Performance Goals**: Every reply inside feature 007's 100 seconds, including one that
reads repository files or carries the documents (SC-010). A session on five elements
inside 60 minutes (SC-013).

**Constraints**:

- No message text, reply text, repository content, document or person's name in any log
  (FR-050). The repository is public.
- The model sees the last 40 messages of a conversation and nothing older. What matters
  must be in the session record.
- The model is whatever `cfn-parameters.json` configures. Today that is Nova 2 Lite, a
  small model used only until an OpenAI or Anthropic model is enabled in the account
  (owner, 2026-11-19). The design must work with it but is not shaped around its limits:
  the prompt and the tools offered are kept short because that is good practice, not to
  a fixed number.
- The agent's only reach outside AWS is GitHub, read-only, to one organisation.
- Feature 007's behaviour outside a session does not change (FR-051).
- Branch deployments are off (issue #10); the first real run is on `main`.

**Scale/Scope**: One workspace, a few sessions a week. About 1,400 lines of Python with
tests; a skill of about seven short Markdown files; one new handbook page and edits to
six others; small changes to the template, the Slack manifest and the worker.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Not performed, before or after design. `.specify/memory/constitution.md` is still the
unfilled Spec Kit template, so there are no principles or gates to evaluate. This remains
an open item for the project owner and is not treated as a gate failure.

## Decisions the owner should look at

Made by the author during planning. Each is in `research.md` under the number given. The
first three change the feature's shape or its cost and need a yes or no.

1. **A new Slack permission, `files:write`, and installing the app again** (Decision 7).
   The written model and the notes are delivered as Markdown files. It is the only way
   the Markdown arrives intact. The permission lets the app upload files to any
   conversation it is in. **US1 scenario 6, FR-038 and FR-039 were reworded**: the model
   is a file, not numbered parts.
2. **We write our own skill; none is adopted** (the search, in `research.md`). Eight
   candidates were read and eleven more looked at. All but one have the agent do the
   work, which is what STRIDEr must not do. The exception, the interview mode of
   Anthropic's `threat-model` skill, lacks most of our stages. The skill credits what it
   learned from. Two marketplaces refused the search and were not covered. FR-007 gives
   the owner the final choice.
3. **The session is a record kept by code, and code writes the model** (Decision 1). The
   spec says STRIDEr "writes" the model; in this design STRIDEr's model fills in a record
   and a program lays it out. It makes the form reliable and removes the reply-time risk.
   It is also most of this feature's code. The alternative, letting the model hold the
   session in its head and write the document, does not work with the framework's
   40-message view.
4. **Rules that can be counted are enforced by code, not by instruction**
   (`contracts/session-tools.md`): one hint per element per stage; notes only at the
   end; acting on a request to finish only on a later message; holding back repository
   findings; who the participants are; severity; the mark on late changes; when silence
   is allowed. What cannot be counted is listed at the end of that file and is still
   judged by a person.
5. **Old tool traffic is dropped from the model's view** (Decision 2), so repository
   files are not re-sent on every turn. STRIDEr cannot quote a file it read earlier
   unless it recorded the fact at the time.
6. **Limits on repository reading, as starting values** (Decision 8): 30,000 characters
   a file, 8 files a reply, 30 a session, 2,000 paths listed.
7. **Repudiation is asked about for every data store** (Decision 9). The original table
   leaves it out; a later paper adds it for logs.
8. **A person whose name Slack cannot give is called "Someone"**, and the message is
   still answered (`data-model.md`).
9. **Names are cleaned before the model sees them** (Decision 10), because a display
   name is text its owner chose.
10. **OWASP's factors are restated in our words, with credit** (Decision 11). The
    methodology is CC BY-SA 4.0 and this repository is MIT.
11. **The system prompt file is renamed** `persona.md` (Decision 5). Its wording comes to
    the owner separately, as agreed.
12. **The fixed session is played three times for acceptance** (Decision 12).
13. **A new stack setting, `GitHubOrg`**, default `ServerlessOpsIO`.

Three things the owner should know that are not decisions:

- **The largest risk is the model** (`research.md`, O1). Whether a small model can keep
  about 25 rules and call tools reliably for a whole session is not known until it is
  tried. The plan tries it early. The owner said on 2026-11-19 that Nova 2 Lite is a
  stopgap until an OpenAI or Anthropic model is enabled in the account, so a poor result
  on Nova is a reason to wait for that model, not to redesign.
- **The agent's traces would carry message text if they were being stored** (O2).
  Looked at on 2026-11-19: no traces are stored today, because CloudWatch Transaction
  Search is off. The moment it is turned on, message text, names and repository content
  would go to X-Ray. Task T006 sets two settings that prevent it, before anything else
  is deployed.
- **GitHub without a credential may be refused often** (O3), because the limit is per
  network address and the runtime's address is AWS's. STRIDEr then says so and carries
  on. The fix is issue #18.

## Project Structure

### Documentation (this feature)

```text
specs/008-threat-model-session/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── agent-interface.md     # Request, reply, what the worker does, the fixed session
│   ├── session-tools.md       # The tools and what each enforces
│   └── written-model.md       # The two documents
├── checklists/
│   └── requirements.md
└── tasks.md                   # Created later by /speckit-tasks
```

### Source Code (repository root)

```text
src/agent/
├── main.py                      # Changed: new request fields, no_reply, documents,
│                                #   tools, window, log fields
├── prompt.py                    # Changed: builds the system prompt for each request
├── persona.md                   # Renamed from system_prompt.md and rewritten
├── loader.py                    # New: reads and validates the skills at start-up
├── skills/
│   └── stride-threat-model/
│       ├── SKILL.md             # New: how to lead a session
│       ├── SOURCE.md            # New: credits and licences
│       └── references/          # New: scope.md, system.md, threats.md, rating.md,
│                                #   mitigations.md, model.md
├── session/
│   ├── record.py                # New: the session record and its rules
│   ├── tools.py                 # New: session and stage tools
│   ├── render.py                # New: the written model, the notes, the diagram
│   └── summary.py               # New: the record as text for the system prompt
└── github.py                    # New: the three repository tools

src/common/common/
├── agentcore.py                 # Changed: new request fields, no_reply, documents
├── model/slack.py               # Changed: new outcome and reason
├── slack/api.py                 # Changed: names from the member lookup; file upload
├── slack/text.py                # Changed: mentions to names; one fixed sentence
└── slack/thread.py              # Changed: writers' names in thread context

src/handlers/AnswerSlackMessage/function.py   # Changed: names, no_reply, documents

scripts/
├── invoke.py                    # Changed: --speaker, --type; saves documents
└── play_session.py              # New: the fixed session

data/sessions/stride-fixed-session.yaml       # New: the fixed session's turns

tests/unit/
├── test_main.py                 # Changed
├── test_prompt.py               # Changed: the persona's rules; no session instructions
├── test_skills.py               # New: format, stages, rules, source and licence
├── session/                     # New: test_record.py, test_tools.py, test_render.py,
│                                #   test_summary.py
├── test_github.py               # New: every refusal in FR-034
├── test_play_session.py         # New: the checks, against saved documents
├── common/                      # Changed: agentcore, slack_api, slack_text, slack_thread
└── handlers/AnswerSlackMessage/test_function.py   # Changed

template.yaml                    # Changed: GitHubOrg parameter and setting
cfn-parameters.json              # Unchanged unless GitHubOrg is set there
slack/manifest.yaml              # Changed: files:write, with its reason
Pipfile                          # Changed: the play-session script
.gitignore                       # Changed: transcripts/
src/agent/Dockerfile             # Unchanged: it already copies all of src/agent/

docs/handbook/
├── 10-threat-model-sessions.md  # New: how a session runs, the repository rules, the
│                                #   fixed session, the transcript checklist
└── 00, 01, 02, 03, 04, 06, 07, 08, 09   # Changed

README.md                        # Changed: the persona and skills, where the system prompt was
```

**Structure Decision**: The agent's code stays flat in `src/agent`, with two new
packages beside it: `skills/` for what the model is told and `session/` for what the code
does. The split mirrors the spec's own: a developer changes how a session is led by
editing Markdown in `skills/`, and changes a rule that code enforces in `session/`. The
worker's changes stay in the shared package where its Slack code already lives.

## Implementation notes

- **Order of work**:
  1. The session record, the renderer and their tests. No model needed; this proves
     SC-002's structure early.
  2. The tools, the prompt builder, the skill's first draft and a draft persona; the
     request and reply changes in the agent; `play_session.py`.
  3. **Deploy and play the fixed session.** This is the test of the largest risk (O1).
     Stop and tell the owner what it shows before going further.
  4. The worker's file upload and the manifest, so that one person can receive a model
     in Slack.
  5. The rules about doing the work; then names and no reply in the worker, and the
     repository tools, in either order.
  6. The persona's final wording with the owner; the handbook; the quickstart.
- **The deployment in step 3 is safe before the worker changes**: a request without the
  new fields is treated as a direct message that must be answered, and the old worker
  ignores `documents`. It does change what STRIDEr says to anyone who writes to it.
- **The manifest change makes the Slack app workflow fail** until the app is installed
  again, as in feature 007. Until then uploads fail and people see the
  document-not-posted sentence.
- **Never log a request, a reply, a tool's arguments or its result.** Unit tests assert
  that a distinctive name, a distinctive word of message text and a distinctive word of
  file content appear in no log output, for the agent and the worker.
- **Tool errors**: a tool never raises to the model's loop for a rule it enforces. It
  returns a sentence. An unexpected failure is caught, logged by type only, and returns
  a sentence too, so one bad call does not cost the reply.
- **The record is validated when read** as well as when written. A record that does not
  validate is treated as no session, and the fact is logged.
- **Relocking**: no dependency changes, so `Pipfile.lock` should not move. If it does,
  restore it.
- **IAM**: nothing new. The agent needs no permission to reach GitHub. The worker's
  upload uses the bot token it already reads.

## Complexity Tracking

No constitution, so no violations to justify. One thing is more complex than the spec
suggests and is recorded here: the session record, its tools and the renderer
(`research.md`, Decision 1). The simpler design, a prompt and nothing else, was rejected
because the framework shows the model only the last 40 messages and because a small model
cannot be trusted to lay out a long document correctly from memory.
