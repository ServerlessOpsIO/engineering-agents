# Contract: Receiving and Answering Slack Events

**Date**: 2026-11-16 | **Spec**: `specs/007-slack-agent-messaging/spec.md`

The interfaces this feature exposes or depends on. Records are defined in
`data-model.md`; reasons are in `research.md`.

## 1. The public address

`POST https://engineering-agents.sandbox.serverlessops.io/slack/events`

The only caller that succeeds is Slack. There is no other route.

### Request

| Part | Value |
|------|-------|
| Header `X-Slack-Request-Timestamp` | Epoch seconds. Looked up without regard to case. |
| Header `X-Slack-Signature` | `v0=` and 64 hex characters. Looked up without regard to case. |
| Header `X-Slack-Retry-Num` | Present on a retry. Logged only. |
| Body | JSON, as Slack sends it. Not validated against a schema. |

### Checks, in order

1. Both headers present, the timestamp a whole number. Otherwise **401**.
2. The timestamp within 300 seconds of now, either way. Otherwise **401**.
3. `v0=` + hex HMAC-SHA256 of `v0:{timestamp}:{body}`, keyed with the signing secret,
   equals the signature, compared with `hmac.compare_digest`. The body is the exact text
   received, base64-decoded first if API Gateway encoded it. Otherwise **401**.
4. The body is JSON. Otherwise **400**.

Nothing after a failed check runs. A 401 or 400 has the body `{"message": "..."}` with no
detail of which check failed beyond "not authorised" or "bad request".

### Responses

| Situation | Status | Body |
|-----------|--------|------|
| `type` is `url_verification` | 200 | `{"challenge": "<the challenge>"}` |
| `type` is `event_callback`, answerable as far as the front door can tell | 200 | `{}` after the message is queued |
| `type` is `event_callback`, not answerable | 200 | `{}` |
| Any other `type` | 200 | `{}` |
| A check failed | 401 or 400 | `{"message": "..."}` |
| The queue could not be reached | 500 | `{"message": "..."}`. Slack sends the event again. |
| More than 5 requests a second | 429 | From API Gateway. Slack sends a genuine event again. |

The function answers within 3 seconds or API Gateway returns an error and Slack retries.
Its own timeout is 5 seconds.

### Which events are answerable here

Rules 0 to 7 of `research.md`, Decision 3. A message more than 4 minutes old is ignored,
and so is a reply with no mention in a channel thread older than the agent's memory.
Otherwise, in short: an `app_mention`; a `message` in a
direct message; a `message` that is a reply in any channel thread, which the worker then
checks. Never a message with a `bot_id`, without a `user`, or with a subtype other than
`file_share` or `thread_broadcast`. The front door calls the queue and nothing else.

## 2. The queue

FIFO, encrypted at rest. Body: the queued message of `data-model.md`, as JSON, text
included. Group `{channel}:{threadTs}`, deduplication ID `{channel}:{ts}`. Messages are
kept for 60 minutes. Visibility timeout 300 seconds. A message is received once: one the
worker did not finish moves to the held-back queue, where the cleanup function deals with
it (section 6). The worker takes one message at a
time, with at most 5 running at once.

## 3. The worker

For each queued message. "Stop" means write the log record and finish normally. Outcomes
and reasons are in `data-model.md`.

| Step | Action | If not |
|------|--------|--------|
| 1 | Only for a reply in a channel thread (`isReply` true, `channelType` not `im`): read the thread up to the message. Continue if the message or an earlier one mentions STRIDEr. | Never mentioned: stop, `declined`/`not_strider_thread`, nothing visible. Slack error after retries: if the message itself does not mention STRIDEr, stop, `failed`/`thread_unreadable`, nothing visible; if it does, do step 2 and then, for a full member, post the apology and stop, `failed`/`thread_unreadable`. |
| 2 | `users.info` for the writer. A full member has the queued `teamId`, and is not restricted, a bot or deleted. | Not a full member: stop, `declined`/`not_member`. Slack cannot say after retries: stop, `failed`/`membership_unknown`. Nothing visible. |
| 3 | `reactions.add` `eyes` on the message. | `already_reacted` is success. Anything else is logged and ignored. |
| 3a | If the thread began more than `MemoryEventExpiryDays` ago: post the start-again sentence, remove the reaction and stop, `declined`/`thread_expired`. | |
| 4 | Remove STRIDEr's mention from the text and trim it. | Nothing left: post the nothing-asked sentence, remove the reaction, stop, `declined`/`nothing_asked`. |
| 5 | Build the prompt (`research.md`, Decision 8), with the thread's earlier messages when step 1 read a thread STRIDEr has not answered in before. | The message alone is over `MaxPromptChars`: post the too-long sentence, remove the reaction, stop, `declined`/`too_long`. |
| 6 | Call the agent. On a failed attempt wait 2 seconds and call once more. | `input_rejection`: as step 5. |
| 7 | Both attempts failed: post the apology, remove the reaction, stop, `failed`/`agent_failed`. | |
| 8 | Post the reply in the thread, in parts of at most 11,000 characters. When there is more than one, each ends with `(part n of m)`. Each part is tried up to 3 times. | A part not posted: post the apology if no part was posted, or the reply-incomplete sentence if some were; remove the reaction; stop, `failed`/`reply_not_posted`. |
| 9 | Remove the reaction. Stop, `answered`. | A failure to remove the reaction is logged and ignored. |

Bounds: each agent call 100 seconds; the function 240 seconds. If the function is killed,
the queue moves the message to the held-back queue after 300 seconds. The worker does not
run on it again (`research.md`, Decision 6); the cleanup function does (section 6). The
worker itself never sends to the held-back queue.

The queued message is never logged, and neither is anything read from the thread.

## 4. Calls to Slack

All with the bot token, through `slack_sdk`, with its retry handlers set to try a failed
or rate-limited call up to three times in all. Steps are the worker's; "cleanup" is the
cleanup function of section 6.

| Method | Used for | Permission |
|--------|----------|------------|
| `auth.test` | The bot's own user ID, once per start of the function. | none |
| `users.info` | Step 2. Remembered for an hour. | `users:read` (new) |
| `reactions.add`, `reactions.remove` | Step 3, and whenever the worker stops after it. Cleanup removes. | `reactions:write` (new) |
| `conversations.replies` | Step 1, for a reply in a channel thread only. Cleanup, always. | `channels:history`, `groups:history`, `im:history` |
| `chat.postMessage` with `markdown_text` and `thread_ts` | Steps 3a, 4, 5, 7 and 8. Cleanup, for the apology. | `chat:write` |

## 5. The call to the agent

`InvokeAgentRuntime` on the stack's own runtime, signed with the worker's role. Request
and reply as in `data-model.md`. The worker's role may call this runtime and its endpoints
and no other.

## 6. The held-back queue and the cleanup function

The held-back queue is the work queue's dead-letter queue: FIFO, encrypted at rest,
**messages kept for at most 60 minutes**. Only the work queue writes to it, when the
worker did not finish a message. Its body is the queued message, text included.

`CleanUpSlackMessage` is triggered by it, one message at a time. It reads the thread from
the message onward with `conversations.replies`, and:

| The message has STRIDEr's eyes | STRIDEr has posted since | Action | Outcome |
|--------------------------------|--------------------------|--------|---------|
| No | either | Nothing visible. | `cleaned_up`/`not_started` |
| Yes | Yes, and the last post is a complete reply or a fixed sentence | Remove the eyes. | `cleaned_up`/`already_answered` |
| Yes | Yes, and the last post ends `(part n of m)` with n less than m | Post the reply-incomplete sentence, then remove the eyes. | `cleaned_up`/`reply_incomplete` |
| Yes | No | Post the apology in the thread, then remove the eyes. | `cleaned_up`/`apologised` |

It writes one log record and the message is deleted. If the function fails, the queue
offers the message again after 60 seconds, until the message is 60 minutes old. Running
twice on one message is safe: after the apology is posted, the second run finds it.

The function's timeout is 30 seconds. It may read the bot token and receive from this
queue. It cannot call the agent. It never logs the message.

## 7. Deployment parameters

Added to `template.yaml` and, where they have no default, to `cfn-parameters.json`.

| Parameter | Value | Notes |
|-----------|-------|-------|
| `Hostname` | `engineering-agents.sandbox.serverlessops.io` | |
| `DnsZoneId` | `/org/dns/ZoneId` | Type `AWS::SSM::Parameter::Value<String>`. Confirmed by the owner on 2026-11-16. |
| `SlackSigningSecretParameter` | default `/engineering-agents/slack/signing-secret` | A name, not a value. |
| `SlackBotTokenParameter` | default `/engineering-agents/slack/bot-token` | A name, not a value. |

The worker and the front door are also given the existing `MaxPromptChars` and
`MemoryEventExpiryDays` values as settings.

New outputs: `SlackEventsUrl`, `SlackMessageQueueUrl`, `SlackHeldBackQueueUrl`.

No table is created.

Every resource of the receiving service exists only when `CodeBranch` is `main`.

## 8. The Slack app definition

- `slack/manifest.yaml`: two bot scopes added, each with its reason comment:
  `reactions:write` and `users:read`.
- `slack/settings.json`: `event_request_url` set to the address in section 1.

Feature 006's pipeline applies both. Its test that lists the planned scopes is updated.
