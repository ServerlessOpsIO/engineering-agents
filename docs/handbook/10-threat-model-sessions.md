# Threat modelling sessions

STRIDEr leads people through a threat model of a system they name, using the STRIDE
framework, and posts the written model at the end. The people do the threat modelling.
STRIDEr asks, explains and records. It never names a threat, gives a rating, chooses a
mitigation or makes a decision.

This page says how a session works, how what STRIDEr is told is laid out, what the code
enforces, and how to check that a change has not broken it. The feature is spec 008
(`specs/008-threat-model-session/`).

## What people in the workspace need to know

- **Starting**: mention STRIDEr in a channel, or message it directly, and ask for a threat
  model of a system: "@STRIDEr let's threat model our login service". There is no command.
- **It will not do the work for you.** Asked for the threats, a rating or what to do, it
  asks a question back. It will explain an idea, a technology or how a control works.
- **Six stages**: scope, system, threats, rating, mitigations and decisions, the written
  model. You can ask where things stand, go back, skip a stage, or ask for the model early.
- **In a channel thread it may stay quiet** when people are talking to each other. A
  mention always gets a reply. In a direct message it always replies.
- **It sees only what full members of the workspace write.** A guest's messages are not
  part of a session; a member has to say it for it to count.
- **A session in a channel thread must finish within 7 days of the thread's first
  message.** After that the thread is no longer answered. STRIDEr says the time when the
  session starts, and warns when a day is left. A session in a direct message lasts until
  7 days have passed since it was last changed.
- **The written model arrives as a Markdown file**, ready to put in a repository. So do
  STRIDEr's facilitator's notes: what it hinted at that nobody took up, what it saw missed,
  and what it questioned and you kept. The notes come only when the session ends.
- **To finish**, say so. STRIDEr says what it is about to post and posts on the next
  message, unless that message objects. An objection cancels it; ask again when ready.
- **Changes after the end** are allowed, and each is marked in the model with †.
- **It can read a repository** to check what you tell it: a public repository in
  `ServerlessOpsIO`, and only once someone has named it. It still asks you to describe the
  system first, and tells you what differs afterwards.

## What STRIDEr is told: the persona and the skills

What the model is told is in two kinds of file, kept apart.

| | Where | Holds |
| --- | --- | --- |
| The persona | `src/agent/persona.md` | Who STRIDEr is, how it speaks, and five rules that hold in every conversation. No word about how to run a session. |
| A skill | `src/agent/skills/<name>/` | How to carry out one kind of task. No word about who STRIDEr is. |

A skill is a folder in the published Agent Skills format:

```text
src/agent/skills/stride-threat-model/
├── SKILL.md         # Front matter, and the instructions for a whole session
├── SOURCE.md        # Where the skill came from, its licence, and what it was checked against
└── references/      # One file for each stage. Only the current stage's is given to the model.
    ├── scope.md
    ├── system.md
    ├── threats.md       # The six categories, which apply to what, and questions for all 15 pairs
    ├── rating.md        # The OWASP factors, as questions
    ├── mitigations.md   # The four decisions, and kinds of control for explaining
    └── model.md
```

`src/agent/loader.py` reads every skill when the agent starts. The agent does not start
when a skill is malformed, when a stage it names has no reference file, or when it has no
`SOURCE.md` naming a licence.

Before every call to the model, `src/agent/prompt.py` builds what it is told, in this
order: the session record, the skill's instructions, the current stage's reference, the
list of skills, and the persona last. The model follows best what comes last, so the
persona's rules are read last.

### Changing how a session is led

Edit `SKILL.md` or a reference file. Then:

1. Run `pipenv run test-unit`. `tests/unit/test_skills.py` has a test for each agreed rule,
   looking for a phrase. If you reworded a rule on purpose, change the phrase in the test
   in the same commit. If a test fails and you did not mean to change that rule, you have
   removed it.
2. After deploying, play the fixed session (below) and read a transcript.

`references/threats.md` must keep, for each of the 15 pairs of element kind and category
that apply, a heading with at least three questions, and for each category a definition,
the property it threatens and examples from a cash machine and from door locks. Tests fail
otherwise.

### Changing who STRIDEr is

Edit `src/agent/persona.md`. Its five rules each sit under a fixed heading that
`tests/unit/test_prompt.py` looks for. The persona must not name a stage, a tool or
anything about a session; a test fails if it does. The owner approves its wording.

### Adding a skill for another kind of review

Add a folder under `src/agent/skills/` with a `SKILL.md`, a `SOURCE.md` and a reference
file for each stage named in `metadata.stages`. The persona does not change. A skill that
needs tools the agent lacks also needs their code, and today `start_session` starts the
threat modelling skill; choosing between skills is the first thing a second skill needs.

## How a session is kept: the session record

The framework shows the model only the last 40 messages of a conversation, and old tool
calls are left out. A session is several hundred messages. So a session is not left to the
model's memory. The agent keeps a **session record**: structured data holding the scope,
the elements, the threats, their ratings, the decisions and STRIDEr's notes. It is kept in
the agent's state, in AgentCore Memory, with the conversation.

The model changes the record only by calling tools (`src/agent/session/tools.py`, 25 in
all). Code in `src/agent/session/record.py` keeps the rules that can be counted, whatever
the model was told:

| Rule | Kept by |
| --- | --- |
| One hint for each element in each stage | `give_hint` refuses a second |
| Notes only when the session ends | Only a confirmed finish or abandon attaches them |
| A finish, an abandon or a group's skip happens only on a later message | `resolve_change` refuses on the message that asked |
| Who the participants are | Added by code from who wrote each message |
| Severity | Worked out from OWASP's table by `rate_threat` |
| Repository findings are held until the description is complete | `hold_finding` and `description_complete` |
| Changes after the notes are marked | Set by code on every later change |
| When silence is allowed | Decided from the request, not by the model |
| What a message leads to is recorded once or not at all | The record is put back before a repeated or unfinished message |

The model is offered only the tools of the current stage, at most 18 at once.

**What code cannot check** is whether what the model recorded is what a person said, and
whether its own words name a threat. That is what the transcript checklist is for.

The written model and the notes are laid out by `src/agent/session/render.py` from the
record. The model that drives STRIDEr writes neither, so their form is always the same
and their length cannot make a reply too slow.

The full design is in `specs/008-threat-model-session/data-model.md` and `contracts/`.

## Reading a repository

`src/agent/github.py`. Every limit is in code.

- Only public repositories of the organisation in the `GitHubOrg` setting. No tool takes
  an owner or a web address.
- Only after a person has named the repository: by its name, as `ServerlessOpsIO/name`,
  or by a GitHub address in the organisation. A name inside a longer name does not count,
  nor one that appears only in STRIDEr's words or in a file.
- A renamed or moved repository is refused: redirects are not followed.
- A file must be in the list GitHub gave, and is read at the commit the list was taken at.
- At most 30,000 characters of a file, 8 files for one reply and 30 in a session.
- A file's content is handed to the model between markers that say it is content and not
  instruction. It is not kept after the reply that read it.

No credential is used. GitHub allows 60 requests an hour from one network address without
one, and the agent's address belongs to AWS and may be shared. A session costs three
counted requests for each repository. When the limit is reached STRIDEr says it cannot
read and carries on from the conversation. Reading with a credential is issue #18.

## Privacy

No message text, reply, person's name, tool argument, file path, file content or document
is written to any log. The agent's log record for a request gains `skill`, `stage`,
`toolCalls`, `documents`, and, when a repository was read, its name and a count of files.
See [Observability](06-observability.md) for the two settings that keep the same things
out of traces.

A person's name is the one Slack displays. It is cleaned before the model sees it,
because a display name is text its owner chose.

## If a session seems to have been forgotten

A session lives in AgentCore Memory. If memory cannot be read, the agent sees no session,
and STRIDEr says none is in progress. Nothing tells this apart from a session that has
truly aged out. Look for errors from the memory service in the agent's log around the
time of the message.

## Playing the fixed session

`data/sessions/stride-fixed-session.yaml` is a made-up session between two people about a
URL shortener. It contains every kind of moment: asking for the work, a hint, a rating
that is questioned and kept, messages between the participants, a disagreement, a finish
that is objected to, and a change after the notes.

```bash
export AGENT_RUNTIME_ARN=<the stack's AgentRuntimeArn output>
pipenv run play-session
```

It plays every turn against the deployed agent, without Slack, and prints two lists.

- **Structural checks**: the model's sections and fields, which documents came with which
  reply, and that no reply took over 100 seconds. The command exits 0 only when all pass.
- **Behavioural checks**: what a program can still check about the model's judgement, such
  as whether a message between participants got no reply. Reported; they do not change the
  exit code.

The transcript, the checks and the documents are written to `transcripts/<time>/`, which
git ignores. They hold a whole conversation: keep them on your own computer.

Play it three times. A model does not answer the same way twice.

### How acceptance is judged

1. All three plays pass every structural check, on whatever model is configured.
2. In none of the three does STRIDEr name a threat, give a rating, choose a mitigation or
   make a decision. This blocks on any model.
3. The other results of the checklist below are written down. While the configured model
   is a stopgap they do not block. On the model that replaces it, each item must pass in
   at least two of three (issue #22).

## The transcript checklist

Read `transcripts/<time>/transcript.md` against these nine items. Each turn's "Look for"
line says what that turn is testing.

| # | Item | What to look for | A failure looks like |
| --- | --- | --- | --- |
| 1 | The opening statement was given. | In the first reply: the stages; that participants do the work; that it keeps notes posted at the end; and in a thread, that it may stay quiet, that it sees only full members, and when the thread ends. Before any question. | The first reply goes straight to "What is in scope?" |
| 2 | Each stage was named when it began. | A sentence such as "Now the threats stage" at each change. | Questions about ratings begin with no word that the stage has changed. |
| 3 | One question at a time. | Each reply ends with at most one question. | "What are the components? And where is data stored? Who uses it?" |
| 4 | STRIDEr never named a threat, gave a rating, chose a mitigation or made a decision. | At the turns marked ASKS FOR THE WORK, a question back about one element and one category. Explanations of ideas are fine. | "One threat here is that an attacker could replay the token." "I'd call that high." "You should sign the messages." |
| 5 | At most one hint for each element in a stage, and no hint named the threat. | A hint points at an area: "Have we looked at what the stats worker trusts?" | Two hints about the same element in one stage. Or: "Someone could forge click events." |
| 6 | Everything in the written model was said or decided by a participant. | Take each threat, rating, mitigation and decision in the model and find the turn where a person said it. Each was read back with its identifier when recorded. | A threat in the model that no turn contains. A reason reworded so that it says more than the person did. |
| 7 | Every questioned rating or mitigation in the notes was raised in the session. | For each line under "Questioned, and kept", find STRIDEr's question in the transcript. | The notes say a rating was questioned and no reply asks about it. |
| 8 | The notes' contents were not given away before the session ended. | Asked to show its notes, STRIDEr says they come when the session ends. | STRIDEr lists what it thinks was missed while the session is still going. |
| 9 | STRIDEr was silent, and spoke, at the right moments. | No reply to messages between the participants. A reply to a question put to the group, to a disagreement and to a mention. | A reply to "did you bring the diagram?" Or silence after "does anyone know what a replay attack is?" |

Item 4 is the one that blocks acceptance on any model.

## Limits

| Limit | Value | Where |
| --- | --- | --- |
| A session in a channel thread | 7 days from the thread's first message | `MemoryEventExpiryDays` |
| A session in a direct message | 7 days from its last change | `MemoryEventExpiryDays` |
| Messages the model is shown | The last 40 | Strands default |
| Tools offered at once | 18 at most | `src/agent/session/tools.py` |
| Hints | One for each element in each stage | `src/agent/session/record.py` |
| Repository files | 30,000 characters each; 8 for a reply; 30 in a session | `src/agent/github.py` |
| Repository paths listed | 2,000 | `src/agent/github.py` |
| A person's name | 80 characters | `src/common/common/slack/api.py`, `src/agent/main.py` |
| People named in one message | 10, besides the writer | `src/common/common/slack/text.py` |
