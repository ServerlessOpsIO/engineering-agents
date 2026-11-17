# Data Model: STRIDEr Slack Messaging

**Date**: 2026-11-16 | **Spec**: `specs/007-slack-agent-messaging/spec.md`

There is no database. What the receiving service needs to remember between events is read
from Slack (`research.md`, Decision 5).

Message text is in the queued message, and in the held-back message until the cleanup
function has dealt with it, for at most 60 minutes each. It is in no log (FR-033, FR-049).

## Queued message

What the front door puts on the work queue. One per message that might be answerable.

| Field | Type | Rules |
|-------|------|-------|
| `teamId` | string | The envelope's `team_id`. |
| `channel` | string | The event's `channel`. |
| `channelType` | `channel` \| `group` \| `im` \| `unknown` | From the event; `unknown` for an `app_mention`, which has none. |
| `ts` | string | The message's own `ts`. |
| `threadTs` | string | The event's `thread_ts` when present, otherwise `ts`. The thread the reply goes in. |
| `isReply` | boolean | True when the event had a `thread_ts` different from `ts`. |
| `user` | string | The writer's Slack ID. |
| `text` | string | The event's `text`, unchanged. **Never logged.** |
| `eventType` | `app_mention` \| `message` | For the log only. The worker does not decide anything from it. |
| `eventId` | string | Slack's `event_id`. For the log only. |
| `correlationId` | string | API Gateway's request ID. |
| `receivedAt` | string | ISO 8601, UTC. |

Queue attributes:

- **Message group**: `{channel}:{threadTs}`. Gives order within a thread (FR-022).
- **Deduplication ID**: `{channel}:{ts}`. Drops a second delivery within 5 minutes
  (FR-011, FR-012).
- **Kept for** 60 minutes, then deleted unanswered.
- **Received once.** A message the worker did not finish moves to the held-back queue
  after 300 seconds.

## Held-back message

A queued message that the worker did not finish, moved to the held-back queue by the work
queue. The same fields, text included; nothing is added. The cleanup function is triggered
by it, acts, and the message is deleted. A message the cleanup function cannot deal with
is offered again until it is 60 minutes old, and then deleted (FR-026).

The record of any failure is a log record, which has the identifiers and the reason and
no text. The message can be opened in Slack from `channel` and `ts`:
`https://serverlessops.slack.com/archives/{channel}/p{ts without the dot}`.

## What a thread read tells the worker

Not stored. Worked out from one `conversations.replies` read of a channel thread, up to
and including the message being answered.

| Name | Meaning |
|------|---------|
| `mentioned` | The message, or an earlier message in the thread, contains a mention of STRIDEr. Decides FR-008 rule 3. |
| `answeredBefore` | An earlier message is STRIDEr's own and is not one of the fixed sentences. |
| `earlier` | The earlier messages, oldest first: each one's writer and text. Used as thread context only when `answeredBefore` is false (FR-046). |

For a top-level mention and for direct messages nothing is read: `mentioned` is true or
not needed, and there are no earlier messages to give.

## Outcomes

How handling one message ends. Recorded in the worker's log record and nowhere else.

| Outcome | Reason | Meaning | Person sees |
|---------|--------|---------|-------------|
| `answered` | | The reply was posted. | The reply. |
| `declined` | `not_strider_thread` | A reply in a thread where STRIDEr was never mentioned. | Nothing. |
| `declined` | `not_member` | The writer is a guest, from another organisation, a bot or deleted (FR-008). | Nothing. |
| `declined` | `thread_expired` | The thread is older than the agent's memory and STRIDEr was addressed. | The start-again sentence. |
| `declined` | `too_long` | Over the agent's limit (FR-028). | The too-long sentence. |
| `declined` | `nothing_asked` | No text once the mention is removed (FR-029). | The nothing-asked sentence when the message mentioned STRIDEr or is a direct message. Otherwise nothing. |
| `failed` | `agent_failed` | Both attempts failed. | The apology. |
| `failed` | `thread_unreadable` | The thread could not be read from Slack, after retries. | The apology, if the message mentions STRIDEr and the writer is a full member. Otherwise nothing: the thread may not be STRIDEr's. |
| `failed` | `membership_unknown` | Slack could not say who the writer is, after retries. | Nothing. |
| `failed` | `identity_unknown` | Slack would not say what STRIDEr's own user ID is. | Nothing. |
| `failed` | `reply_not_posted` | The agent answered and Slack would not take the reply, or some part of it. | The apology if no part was posted; the reply-incomplete sentence if some were. Nothing if Slack takes neither. |

The cleanup function has outcomes of its own, for a message the worker did not finish:

| Outcome | Meaning | Person sees |
|---------|---------|-------------|
| `cleaned_up`/`not_started` | The message has no eyes from STRIDEr; the worker never decided to answer. | Nothing. |
| `cleaned_up`/`already_answered` | STRIDEr posted after the message. The eyes are removed. | What was already posted. |
| `cleaned_up`/`reply_incomplete` | STRIDEr's last post after the message is a part that is not the final one. | The reply-incomplete sentence. |
| `cleaned_up`/`apologised` | STRIDEr had not posted. The apology is posted and the eyes removed. | The apology. |

## Agent request and reply

Defined by the agent (`docs/handbook/04-architecture.md`). What this feature sends:

| Field | Value |
|-------|-------|
| `runtimeSessionId` | `slack-{teamId}-{channel}-{threadTs with "." replaced by "-"}`. One per thread (FR-020). |
| `prompt` | The message text with STRIDEr's mention removed, preceded by thread context when FR-046 applies. At most `MaxPromptChars`. |
| `slackUserId` | The writer's Slack ID. Information only (FR-019). The agent ignores it today. |
| `actorId` | Not sent, so that everyone in a thread shares one memory. |

What comes back, and what the worker does:

| Reply | Worker |
|-------|--------|
| `kind` `answer` | Posts `text` in the thread. |
| `kind` `input_rejection` | Posts the too-long sentence. Not a failure. |
| `kind` `error`, an exception, not JSON, or nothing in 100 seconds | A failed attempt. |

## Fixed sentences

Constants in the shared package. Not written by the agent. The worker recognises them
when it reads a thread, so that they do not count as an answer.

| Name | Text |
|------|------|
| Apology | Sorry, I couldn't answer that. Please try again later. |
| Too long | That message is too long for me to read. Please shorten it and try again. |
| Nothing asked | What would you like help with? |
| Start again | I no longer remember this conversation. Please send me a new message outside this thread to start again. |
| Reply incomplete | I couldn't post my whole reply. Please ask again. |

A reply in more than one part has a last line on each part: `(part 1 of 3)`.

## Secrets

Kept by hand only as GitHub secrets. The deployment passes each to the stack as a hidden
parameter, and the stack keeps it in a Secrets Manager secret. Read at run time, kept for
5 minutes.

| Secret in the stack | From the GitHub secret | Read by | Used for |
|---------------------|------------------------|---------|----------|
| `SlackSigningSecretStore` | `SLACK_SIGNING_SECRET` | Front door | Checking signatures (FR-002). |
| `SlackBotTokenStore` | `SLACK_BOT_TOKEN` | Worker, cleanup function | Every call to Slack. |

## Log records

One JSON record per request (front door) and per message (worker), through Powertools.
Never any text (FR-033, FR-035).

Front door: `correlationId`, `outcome` (`rejected_signature`, `rejected_stale`,
`url_verified`, `ignored`, `queued`, `error`), `reason` when ignored (including `too_old`
and `thread_expired`), `durationMs`,
`eventId`, `eventType`, `channel`, `threadTs`, `user`, `retryNum` when Slack sent one.

Worker: `correlationId`, `outcome` and `reason` from the table above, `durationMs`,
`eventId`, `channel`, `threadTs`, `ts`, `user`, `sessionId`, `agentRequestId`, `attempts`,
`threadRead` (boolean), `contextMessages` (how many earlier messages were sent),
`contextDropped` (how many were left out), `replyParts`, and `reactionAdded` and
`reactionRemoved` as booleans.

Cleanup function: `correlationId`, `outcome` and reason from its table above,
`durationMs`, `eventId`, `channel`, `threadTs`, `ts`, `user`, `reactionRemoved`.
