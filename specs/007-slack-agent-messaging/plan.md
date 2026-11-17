# Implementation Plan: STRIDEr Slack Messaging

**Branch**: `feature/007-slack-agent-messaging` | **Date**: 2026-11-16 | **Spec**: `specs/007-slack-agent-messaging/spec.md`

**Input**: Feature specification from `specs/007-slack-agent-messaging/spec.md`

## Summary

Connect the STRIDEr Slack app to the existing agent, so that a person who mentions STRIDEr
or messages it directly gets the agent's reply in a thread.

Slack sends events to a public address on API Gateway. A small function, the front door,
checks Slack's signature, answers Slack at once, and puts each message that might be worth
answering on a FIFO queue, with its text. A second function, the worker, takes messages off the
queue one thread at a time: it checks the writer is a full member of the workspace, adds
an eyes reaction, calls the agent with the thread as the session, posts the reply and
removes the reaction. For a reply in a channel thread it first reads the thread from
Slack, to see whether STRIDEr has been mentioned there and to give the agent the earlier
messages the first time. If the worker dies part-way, the message moves to a dead-letter
queue, where a third function, the cleanup function, posts the apology and removes the
reaction. There is no database.

The agent is not changed and keeps IAM authentication. The two Slack secrets are placed in
Parameter Store by the owner and read when the functions run. The receiving service exists
only in the `main` stack.

## Technical Context

**Language/Version**: Python 3.14 on AWS Lambda (arm64); AWS SAM template; OpenAPI 3.0.

**Primary Dependencies**: Powertools for AWS Lambda (logging, event classes, parameters,
batch processing) in all three functions. `slack_sdk` in the worker and the cleanup
function. A packaged `boto3` in the worker; the front door uses the runtime's `boto3` for
its one call to the queue. The signature check uses the standard library.

**Storage**: Two SQS FIFO queues (work, held back), each keeping a message for 60
minutes. Two Parameter Store SecureString parameters, created by hand. No database. See
`data-model.md`.

**Testing**: `pytest` through `pipenv run test-unit`, with `moto` for AWS and fakes for
Slack and the agent. No test contacts AWS or Slack. End-to-end checks are manual, on
`main`, and listed in `quickstart.md`.

**Target Platform**: AWS, the deployment account the agent is already in, one region.
Slack's Events API and Web API. The `serverlessops` workspace.

**Project Type**: Three serverless functions added to an existing single-service
repository.

**Performance Goals**: Acknowledge Slack within 3 seconds (SC-008). Eyes within 5 seconds
(SC-001). The apology within 5 minutes when the agent fails, and within 10 when the
worker itself dies (SC-010).

**Constraints**:

- Message text and reply text are never logged. Text waits in a queue for at most 60
  minutes (FR-033, FR-049).
- The front door makes no call to Slack, so its time depends on one AWS call only.
- The worker handles a queued message once and never runs on it again (FR-027).
- A message more than 4 minutes old is ignored, and a thread older than the agent's
  memory is no longer answered in.
- The whole prompt, thread context included, must fit in the agent's `MaxPromptChars`,
  raised from 4,000 to 16,000 by this feature.
- The agent's code and its template resources are not changed. One of its settings is.
- The repository is public, and so is the address.
- Branch deployments are off (issue #10); the first real run is on `main`.

**Scale/Scope**: One workspace, a handful of messages an hour. About 600 lines of Python
with tests, about 180 lines of template and OpenAPI, one new handbook page and edits to
six others.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Not performed, before or after design. `.specify/memory/constitution.md` is still the
unfilled Spec Kit template, so there are no principles or gates to evaluate. This is an open
item for the project owner and is not treated as a gate failure.

## Decisions the owner should look at

These follow from the spec but were made by the author during planning. Each is in
`research.md` under the number given.

1. **No database, at the owner's direction** (Decisions 2 and 5). Which threads are
   STRIDEr's, and whether it has answered in one before, are read from Slack each time.
   The cost: every reply in any thread in STRIDEr's channels starts the worker and makes
   one Slack call.
2. **The text travels in the queue, at the owner's direction** (Decision 4). Queued and
   held-back messages are kept for 60 minutes. A held-back message restarts the clock, so
   text can exist outside Slack for up to about two hours.
3. **Two rules are decided in the worker, not at the front door** (Decision 3): whether a
   thread is STRIDEr's and whether the writer is a full member. Both need Slack to be
   asked. **FR-006 was reworded to allow this.**
4. **Two new Slack permissions, not one**: `reactions:write` and `users:read`
   (`research.md`, S13). `users:read` lets STRIDEr look up any member's profile.
5. **`actorId` is not sent to the agent** (Decision 8). The agent keeps memory per actor,
   so sending the person's ID would give each person in a thread a separate conversation.
   The Slack ID goes in a field the agent ignores today.
6. **The second attempt happens at once, inside the worker** (Decision 7), not by the
   queue redelivering.
7. **The worker never runs twice on a message** (Decision 6). With no database there is
   nowhere to record "answered", so "never two replies" is kept by moving a message to
   the dead-letter queue after one receive. This goes against AWS's advice of at least
   five, and the visibility timeout is 300 seconds where AWS advises six times the
   function's timeout.
8. **A cleanup function on the dead-letter queue, at the owner's direction** (Decision
    15). The owner proposed a Lambda destination; destinations do not fire for a function
    driven by a queue, so the function is triggered by the dead-letter queue instead. It
    uses the eyes reaction to tell whether an apology is owed. The apology for a crashed
    worker arrives five to six minutes after the crash.
9. **A message more than 4 minutes old is ignored** (Decision 6). The author's
    recommendation, confirmed by the owner. It closes the one way a
    message could be answered twice. A message Slack delivers late is dropped unanswered.
10. **A thread older than the agent's memory is no longer answered in** (Decision 16),
    from the owner's suggestion. A person who addresses STRIDEr there is asked to start a
    new conversation. The cut-off is the thread's age, not its last activity.
11. **When Slack cannot say what the worker needs** (Decision 7, FR-053), confirmed by the
    owner. Calls are tried three times and membership is remembered for an hour. After
    that: silence when it is not known that STRIDEr may or should respond, and the
    apology when a full member plainly addressed it.
12. **Three departures from the convention template**, all so text cannot reach a log
   (Decision 11): no request validator, API Gateway execution logging off, and handlers
   that do not log the event.
13. **The log is the record of a failure** (Decision 4). The dead-letter queue is emptied
   by the cleanup function and is not for looking at. **FR-026, FR-027, FR-046 and FR-049 were reworded** for items 1,
   2 and 7.
14. **Parameter Store, not Secrets Manager** (Decision 10). Free, and already the
    convention.
15. **`slack_sdk` in the worker** (Decision 13), where feature 006 used none.
16. **The agent's prompt limit is raised from 4,000 to 16,000 characters** (Decision 8),
    chosen by the owner, so that thread context is not cut short in most threads. It is a
    one-line change to `cfn-parameters.json` and the only change this feature makes to
    the agent. Every caller of the agent may now send a longer prompt.
17. **The first merge makes the Slack app workflow fail** until the app is installed again
    (Decision 14). That is feature 006 working as designed.
18. **Starting values**: 5 requests a second; 100 seconds per agent call; replies split at
    11,000 characters; a member lookup remembered for an hour.
19. **FR-036 was reworded** (Decision 12). The worker's log record carries the front door's
   identifier and the agent's, instead of one identifier appearing in all three.
20. **Long replies are labelled "(part 1 of 3)", and the person is told when a reply is
    incomplete** (Decisions 9 and 15). Confirmed by the owner. The owner also confirmed
    the 4-minute rule and the rule for old threads (items 9 and 10).

The owner confirmed on 2026-11-16 that the hosted zone's ID is in the Parameter Store
parameter `/org/dns/ZoneId` (`research.md`, O1). Nine other facts are unverified and are
checked by early tasks or by the first deployment (O2 to O12).

## Project Structure

### Documentation (this feature)

```text
specs/007-slack-agent-messaging/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── slack-events.md
├── checklists/
│   └── requirements.md
└── tasks.md               # Created later by /speckit-tasks
```

### Source Code (repository root)

```text
template.yaml                    # Changed: parameters, condition, API, domain, certificate,
                                 #   three functions and permissions, two queues, outputs
openapi.yaml                     # New: POST /slack/events, proxy integration
cfn-parameters.json              # Changed: Hostname, DnsZoneId

src/handlers/
├── ReceiveSlackEvent/
│   ├── function.py              # New: signature check, address check, rules, queue
│   └── requirements.txt
├── AnswerSlackMessage/
│   ├── function.py              # New: the steps of the contract, section 3
│   └── requirements.txt
└── CleanUpSlackMessage/
    ├── function.py              # New: the three cases of the contract, section 6
    └── requirements.txt

src/common/
├── setup.py
└── common/
    ├── model/slack.py           # New: queued and held-back messages, outcomes, session ID
    ├── slack/signature.py       # New: the check of FR-002
    ├── slack/api.py             # New: the calls to Slack, with retries; member check
    ├── agentcore.py             # New: the call to the agent
    ├── slack/text.py            # New: mention removal, prompt building, reply splitting,
    │                            #   the fixed sentences
    ├── slack/thread.py          # New: what a thread read tells the worker and the
    │                            #   cleanup function; thread age
    └── util/dataclasses.py      # New: from the convention template

data/handlers/
├── ReceiveSlackEvent/           # New: sample events and schemas
├── AnswerSlackMessage/
└── CleanUpSlackMessage/

tests/unit/
├── handlers/
│   ├── ReceiveSlackEvent/test_function.py    # New
│   ├── AnswerSlackMessage/test_function.py   # New
│   └── CleanUpSlackMessage/test_function.py  # New
├── common/test_slack_model.py                # New
├── common/test_slack_signature.py            # New
├── common/test_slack_api.py                  # New
├── common/test_agentcore.py                  # New
├── common/test_slack_text.py                 # New
├── common/test_slack_thread.py               # New
└── test_slack_definition.py                  # Changed: the planned scopes

slack/manifest.yaml              # Changed: reactions:write, users:read
slack/settings.json              # Changed: event_request_url

Pipfile, Pipfile.lock            # Changed: dev packages only
pytest.ini                       # Changed: pythonpath

docs/handbook/
├── 09-slack-messaging.md        # New: what it is, first-time setup, replacing a secret,
│                                #   held-back messages, what people need to know
└── 00, 01, 03, 04, 05, 08       # Changed
```

**Structure Decision**: The convention template's layout (`src/handlers`, `src/common`,
`data/handlers`, `tests/unit/handlers`) is added beside the existing agent in `src/agent`
and the existing flat tests, which stay where they are. `main.yml` and `branch.yml` need
no change: `sam build` already runs and will build the functions, and `pipenv run
test-unit` already runs every unit test.

## Implementation notes

- **Order of work**: shared package and its tests first; then the front door, which can be
  proven alone by Slack's address check; then the worker; then the cleanup function. The
  manifest and settings change is what turns events on. It is written in Phase 5 of the
  tasks and reaches `main` only in the single merge at the end, so nothing arrives before
  the worker and the cleanup function exist.
- **Logs**: each function has its own log group, kept 30 days (FR-037). The front door's
  timeout is 3 seconds, the same as Slack's patience.
- **Relocking**: last time, relocking `Pipfile.lock` moved three of the agent's runtime
  packages. Check the diff and restore any `[packages]` entry that moved.
- **The agent's image** must not change. `.dockerignore` already limits its build context
  to `Pipfile` and `src/agent/`.
- **IAM**: the front door may read one parameter and send to the work queue. The worker
  may read the other parameter, receive from the work queue, and invoke this runtime and
  its endpoints. The cleanup function may read the bot token and receive from the
  dead-letter queue (FR-034).
- **Never log a queued message.** It has text in it. This includes exception handlers and
  the batch processor's failure path; a unit test asserts that a distinctive word in a
  test message appears in no log output.

## Complexity Tracking

No constitution, so no violations to justify. An earlier version of this plan added a
DynamoDB table; the owner removed it on 2026-11-16.
