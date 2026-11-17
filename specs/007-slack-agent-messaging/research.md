# Research: STRIDEr Slack Messaging

**Date**: 2026-11-16 | **Spec**: `specs/007-slack-agent-messaging/spec.md`

Each fact below is marked with how it is known:

- **Documented**: read on the named vendor page on 2026-11-16.
- **Inferred**: follows from the documentation or from source code, and is not stated
  outright.
- **Believed**: from memory or common practice. Not found in the documentation.

Nothing in this document has been tried against Slack or AWS. The "Open items" section at
the end lists what must be tried, and what happens if it turns out wrong.

## Facts checked: Slack

| # | Fact | Status | Source (docs.slack.dev unless noted) |
|---|------|--------|--------------------------------------|
| S1 | The signature is `v0=` plus the hex HMAC-SHA256, keyed with the signing secret, of `v0:{timestamp}:{raw body}`. Headers are `X-Slack-Signature` and `X-Slack-Request-Timestamp`; their case must not be assumed. The timestamp may differ from local time by at most five minutes. The raw body must be used, before it is parsed. | Documented | authentication/verifying-requests-from-slack |
| S2 | The address check is a POST with `{"token", "challenge", "type": "url_verification"}`. A 200 with the bare challenge as `text/plain`, or `{"challenge": "..."}` as JSON, is accepted. | Documented | reference/events/url_verification |
| S3 | The address check carries a signature like any other request. | Inferred | The page says to verify the request and links to S1. |
| S4 | An event must be answered with a 2xx within three seconds. Slack retries up to three times: almost at once, after 1 minute, after 5 minutes. Retries carry `x-slack-retry-num` and `x-slack-retry-reason`. | Documented | apis/events-api |
| S5 | `event_id` is the same on a retry. | Inferred | Not stated; universally relied on. |
| S6 | Slack turns event delivery off when more than 95% of deliveries fail within 60 minutes, **but not for apps receiving fewer than 1,000 events an hour**. | Documented | apis/events-api |
| S7 | A message that mentions the app in a channel, when the app subscribes to both `app_mention` and `message.channels` (or `message.groups`), arrives as two events with different `event_id`s and the same `channel` and `ts`. | Inferred | Not stated. "One request, one event"; `app_mention` "is not a `message`". |
| S8 | `app_mention` is never sent for direct messages. A mention in a channel the app is not in sends nothing. | Documented | reference/events/app_mention |
| S9 | A `message` event has `channel_type` (`channel`, `group`, `im`). `app_mention` has no `channel_type`. | Documented | reference/events/message.channels, app_mention |
| S10 | A reply has `thread_ts` different from `ts`. A parent with replies has `thread_ts` equal to `ts`. A message never threaded has no `thread_ts`. | Documented | messaging/retrieving-messages |
| S11 | Edits and deletions arrive as `message` events with subtype `message_changed` and `message_deleted`. `message_changed` is also sent for link previews and language detection. A person's message with a file may carry subtype `file_share`; a reply also sent to the channel carries `thread_broadcast`. | Documented, except that `file_share` is described inconsistently | reference/events/message |
| S12 | A message from a current app, including this one, has no subtype. It is recognised by `bot_id`. | Documented | reference/events/message |
| S13 | No field of an event says the writer is a guest. `users.info` (permission `users:read`, 100+ calls a minute) returns `team_id`, `is_restricted`, `is_ultra_restricted`, `is_bot` and `deleted`. A guest has `is_restricted` true. A person from another organisation has a `team_id` that is not the installing workspace's. | Documented | reference/methods/users.info, reference/objects/user-object, apis/slack-connect |
| S14 | The event envelope's `team_id` is the workspace the event happened in. | Documented | apis/events-api |
| S15 | `conversations.replies` takes `channel` and `ts`, where `ts` is a parent or any message in the thread. With a message that has no replies it returns that message. It needs `channels:history`, `groups:history` or `im:history`, which the app already holds. 50+ calls a minute. | Documented | reference/methods/conversations.replies |
| S16 | The 2025 limit of one `conversations.replies` call a minute does not apply to an app built for its own workspace. | Documented | changelog/2025/05/29/rate-limit-changes-for-non-marketplace-apps |
| S17 | `reactions.add` and `reactions.remove` need `reactions:write` and take `channel`, `timestamp` and `name`. `add` gives `already_reacted` when the reaction is there; `remove` gives `no_reaction` when it is not. `remove` allows 20+ calls a minute, `add` 50+. | Documented | reference/methods/reactions.add, reactions.remove |
| S18 | The name of the eyes emoji is `eyes`. | Believed | Standard emoji short name. |
| S19 | Adding a reaction lists it in the writer's Activity view. Removing one tells nobody. | Believed | Not in the API pages or the help centre. |
| S20 | `chat.postMessage` with `thread_ts` set to the parent's `ts` posts in the thread. It accepts `markdown_text`, standard Markdown up to 12,000 characters, which cannot be combined with `text` or `blocks`. About one message a second per channel. | Documented | reference/methods/chat.postMessage |
| S21 | `markdown_text` works with a bot token. | Inferred | No restriction is stated. |
| S22 | A mention in message text is `<@U…>` or, in older form, `<@U…\|name>`. IDs may start with `U` or `W`. `auth.test` returns the bot's own `user_id`. | Documented | messaging/formatting-message-text, reference/methods/auth.test |
| S23 | A new bot permission in the manifest reaches the installed app only after the app is installed again. | Documented | app-management/distribution |
| S24 | Installing again keeps the same bot token. | Believed | Not stated. Feature 006's handbook already tells the owner to compare. |
| S25 | An address set through the manifest must be verified by hand in the app's settings. Whether events flow before that is not clear: one page says events go to a new address immediately. | Documented, with the conflict noted | reference/app-manifest, app-management/distribution |

## Facts checked: AWS

| # | Fact | Status | Source (docs.aws.amazon.com unless noted) |
|---|------|--------|-------------------------------------------|
| A1 | An AgentCore runtime accepts IAM-signed calls or a JWT bearer token, not both. IAM is the default when `AuthorizerConfiguration` is left out, as it is in this repository. | Documented | bedrock-agentcore devguide, runtime-oauth |
| A2 | `boto3.client("bedrock-agentcore").invoke_agent_runtime(agentRuntimeArn, runtimeSessionId, payload, …)` returns `statusCode`, `contentType` and `response`, a stream to read. | Documented | boto3 reference; devguide, runtime-invoke-agent |
| A3 | The caller needs `bedrock-agentcore:InvokeAgentRuntime` on the runtime and on its endpoint: `…:runtime/{id}` and `…:runtime/{id}/runtime-endpoint/*`. | Documented | devguide, resource-based-policies; service reference |
| A4 | Passing `runtimeUserId` needs a second permission, `InvokeAgentRuntimeForUser`. | Documented | same |
| A5 | `runtimeSessionId` is 33 to 256 characters. Only letters, digits, `-` and `_` are safe; `.` is advised against. | Documented (length); Inferred (characters) | API reference; devguide, runtime-fuse-mounts |
| A6 | One synchronous call may take up to 15 minutes. | Documented | devguide, limits |
| A7 | Lambda offers `python3.14`. | Documented | lambda, lambda-runtimes |
| A8 | `python3.14` is offered on arm64. | Inferred | No per-runtime table found. |
| A9 | AWS recommends packaging boto3 with a function and not relying on the copy in the runtime. | Documented | lambda, python-package |
| A10 | With a Lambda proxy integration and no binary media types, the body reaches the function as the text that was sent. No mapping template runs. | Inferred | apigateway, payload-encodings-workflow |
| A11 | Header names in the event keep the sender's case. | Documented | apigateway, known-issues |
| A12 | A Lambda authorizer is not given the body. | Inferred by omission | apigateway, lambda-authorizer-input |
| A13 | `MethodSettings` sets `ThrottlingRateLimit` and `ThrottlingBurstLimit`. A throttled request gets 429. The limits are targets, not hard ceilings. | Documented | apigateway, request-throttling |
| A14 | SAM's `Domain` property creates the custom domain and its base path mapping; with `Route53.HostedZoneId` it creates the DNS record. The stage name is not part of the custom-domain address. A regional domain needs a certificate in the same region. | Documented; the DNS record is Inferred | SAM, sam-property-api-domainconfiguration |
| A15 | A certificate with DNS validation is validated automatically only when the hosted zone is in the same account as the stack. | Documented | CloudFormation, certificatemanager-certificate |
| A16 | SAM adds no Lambda permission for API Gateway when the API is defined by `DefinitionBody`. | Inferred | The convention template adds one by hand. |
| A17 | Execution logging with `DataTraceEnabled: false` keeps bodies out of the log. | **Not established.** The page says execution logs may include "payloads" and does not say when. | apigateway, rest-api-execution-logging |
| A18 | A request validator publishes validation results to the log. | Documented | apigateway, method-request-validation |
| A19 | A FIFO queue delivers the messages of one message group in order, and holds back later messages of a group while an earlier one is being processed or retried. Groups are processed in parallel. | Documented | SQS, FIFO-queues-understanding-logic; lambda, services-sqs-scaling |
| A20 | A FIFO queue drops a message whose deduplication ID it has seen in the last 5 minutes. | Documented | SQS, FIFO-queues-exactly-once-processing |
| A21 | A FIFO queue's dead-letter queue must be FIFO. AWS recommends `maxReceiveCount` of at least 5 with Lambda, because a throttled function can use up receives without running. Messages are kept for at most 14 days. | Documented | SQS; lambda, services-sqs-errorhandling |
| A22 | The queue's visibility timeout must be at least the function's timeout. AWS recommends six times it. | Documented | lambda, services-sqs-configure |
| A23 | A function can send a message straight to a dead-letter queue, which is an ordinary queue. | Inferred | Nothing forbids it. |
| A27 | A queue keeps a message for its retention period, from 60 seconds to 14 days, and then deletes it. When a FIFO queue moves a message to its dead-letter queue the clock starts again. | Documented (range); Believed (the clock) | SQS |
| A28 | SQS encrypts messages at rest by default. | Believed | SQS |
| A24 | A SecureString parameter in Parameter Store's standard tier costs nothing. Reading it needs `ssm:GetParameter` and `kms:Decrypt`. It cannot be a CloudFormation template parameter. | Documented | systems-manager; kms, services-parameter-store; CloudFormation |
| A25 | Powertools `get_parameter(name, decrypt=True)` keeps a value for 5 minutes by default. | Documented | powertools/python, utilities/parameters |
| A26 | Powertools: `APIGatewayProxyEvent` has `body`, `decoded_body` and case-insensitive `headers`. FIFO batches use `SqsFifoPartialProcessor`; there is no `EventType.SqsFifo`. | From source | github.com/aws-powertools/powertools-lambda-python |

## Facts about this repository

| # | Fact |
|---|------|
| R1 | The agent's request is `{"prompt": "...", "actorId": "..."}`. The reply is `{"kind": "answer" \| "input_rejection" \| "error", "text", "requestId"}`. `error` comes with HTTP 500. It reads no other field. |
| R2 | **The agent keeps memory by session and by `actorId`.** Two people in one session with different `actorId`s do not share memory. |
| R3 | The agent rejects an empty prompt and one over `MaxPromptChars` (4,000) with `input_rejection`. |
| R4 | The agent's log record has `requestId` and `sessionId`. The `requestId` is returned in the reply. |
| R5 | `main.yml` runs `sam build`, then deploys `template.yaml` with `cfn-parameters.json` into the deployment account. It runs on every push to `main` except changes under `specs/` and `docs/`. |
| R6 | `Pipfile` `[packages]` are installed in the agent's image. `[dev-packages]` are not. |
| R7 | Feature 006's pipeline sends the manifest's events to Slack once `event_request_url` is set, and fails with "install again" while the installed app lacks a permission the manifest has. |
| R8 | The convention template takes the hosted zone ID from a Parameter Store parameter, `/org/dns/ZoneId`, as a template parameter of type `AWS::SSM::Parameter::Value<String>`. |
| R9 | The convention template's handlers log the whole event at debug level. |

## Corrections to the spec's assumptions

- **Slack will not turn events off at this volume** (S6). The spec's edge case said it
  might. The spec has been corrected, and the handbook says what Slack does and why it is
  unlikely here.
- **The guest check needs a lookup and a permission** (S13), as the spec suspected:
  `users:read` is added to the app definition alongside `reactions:write`.
- **FR-006 and FR-036 were reworded** to match Decisions 3 and 12. See those decisions.
- **The owner changed three things after reading the first plan** (2026-11-16): no
  database table; the text of a message travels with it in the queue, taken from Slack's
  event, with no call to Slack to read it; and the held-back queue keeps a message for 60
  minutes, not 14 days. Decisions 2 to 7 below are the revised ones. Later the same day the
  owner chose a cleanup function on the held-back queue (Decision 15) and a rule for
  threads older than the agent's memory (Decision 16). The spec's FR-026,
  FR-027, FR-046 and FR-049 were changed to match.

## Decision 1: Authentication stays as it is

- **Decision**: The runtime keeps IAM. The worker's role is granted
  `bedrock-agentcore:InvokeAgentRuntime` on this runtime and its endpoints, and nothing
  else calls it from this feature.
- **Rationale**: A1 confirms the owner's reasoning: it is one or the other, and Slack can
  present neither. A role needs no secret.
- **Alternatives considered**: a JWT authorizer with a machine client. It adds an identity
  provider and a client secret and removes nothing.

## Decision 2: The shape

- **Decision**: API Gateway REST API → `ReceiveSlackEvent` function → SQS FIFO queue →
  `AnswerSlackMessage` function → the runtime and Slack. The work queue's dead-letter
  queue, also FIFO, is the held-back store, and a third function, `CleanUpSlackMessage`,
  is triggered by it (Decision 15). There is no database.
- **Rationale**: The owner's choice, confirmed after an earlier version of this plan added
  a DynamoDB table. Everything the table would have remembered can be read from Slack,
  which is where it is true (Decisions 3 and 5).
- **Alternatives considered**:
  - *A DynamoDB table* of threads and messages. Faster to ask than Slack and allowed the
    front door to drop more. Rejected by the owner: one more resource, and a copy of what
    Slack already knows that can expire or drift.
  - *Ask the agent's memory whether a session exists.* Ties the receiving service to how
    the agent stores memory.
  - *A standard queue.* Loses FR-022's ordering within a thread.

## Decision 3: Who decides a message is answerable

- **Decision**: The front door decides what can be decided from the event alone and calls
  nothing but the queue. The worker decides the two rules that need Slack to be asked:
  whether a thread is one STRIDEr has been mentioned in, and whether the writer is a full
  member. Nothing visible happens before both are settled.
- **Front door rules**, applied in order to an accepted `event_callback`:
  0. The message's `ts` is more than 4 minutes old: ignore (Decision 6).
  1. Not `app_mention` and not `message`: ignore.
  2. Has `bot_id`, or has no `user`: ignore (S12).
  3. A `message` whose subtype is anything but none, `file_share` or `thread_broadcast`:
     ignore (S11). This drops edits, deletions and Slack's own notices.
  4. `app_mention`: queue it.
  5. `message` with `channel_type` `im`: queue it.
  6. `message` in a channel that is a reply (`thread_ts` present and not equal to `ts`)
     in a thread younger than the agent's memory (Decision 16): queue it. The worker
     finds out whether the thread is STRIDEr's.
  7. Anything else, which is a top-level channel message: ignore. If it mentions STRIDEr,
     its `app_mention` twin passed rule 4.
- **Worker rules**:
  1. For a reply in a channel thread, read the thread from Slack up to the message
     (Decision 5). It is answerable if the message mentions STRIDEr or an earlier message
     in the thread does. Otherwise stop.
  2. Ask Slack about the writer (S13). Answerable only for a full member. The answer is
     remembered for an hour inside a running copy of the worker, to save calls.
- **The worker tells a mention from the text**, not from the kind of event. A mention
  inside a thread arrives as two events (S7) and the queue keeps whichever comes first
  (Decision 6), so the kind of event that survives is not reliable.
- **Rationale**: The front door makes one AWS call, so the acknowledgement is fast and
  cannot be held up by Slack.
- **Cost**: every reply a person writes in any thread, in a channel STRIDEr is in, starts
  the worker and makes one Slack call, including in threads that have nothing to do with
  STRIDEr. At this workspace's volume that is negligible. A busy workspace would press on
  Slack's limit of about 50 thread reads a minute (S15).
- **Consequence for the spec**: FR-006 now says the front door acts on what it can tell,
  and names the two rules the worker decides. FR-010 is unchanged: no reaction, no reply,
  no call to the agent.

## Decision 4: The text travels with the message

- **Decision**: The front door copies the text from Slack's event into the queued message.
  The worker does not call Slack to read the message it is answering.
- **Rationale**: The owner's choice: one Slack call fewer for every message. The text is
  the text as first sent, which is what the spec asks for; later edits are ignored.
- **What this changes**: text now waits in the work queue and, after a failure, in the
  held-back queue. The owner set the limit: the held-back queue keeps a message for 60
  minutes. The work queue is given the same 60 minutes, so a message nobody could answer
  in an hour is dropped, not answered late. Both queues are encrypted at rest (A28).
  Because moving a message to the held-back queue restarts its clock (A27), the longest
  text can exist outside Slack and the agent's memory is about two hours.
- **The log is the record of a failure.** A log record for a failed message has the
  identifiers and the reason and no text. The held-back queue is not for looking at: the
  cleanup function empties it as it goes (Decision 15), so in practice held-back text is
  gone within minutes, and 60 minutes is the most it can last if the cleanup itself is
  failing.
- **Care needed**: the queued message must never be logged. Powertools' batch processing
  is used so that a failure logs the exception and not the record.
- **Alternatives considered**: reading the text from Slack in the worker, so no text is
  queued. It was this plan's first design and the owner rejected it for the extra call.

## Decision 5: What is read from Slack, and when

- **Decision**: The worker reads a thread with `conversations.replies` only for a reply in
  a channel thread. A top-level mention and anything in a direct message need no read.
  One read, up to and including the message being answered, in pages of 200, answers
  three questions:
  1. **Is the thread STRIDEr's?** Yes if the message or an earlier one mentions STRIDEr.
  2. **Has STRIDEr answered here before?** Yes if an earlier message is STRIDEr's own and
     is not one of its fixed sentences.
  3. **What are the earlier messages?** Needed only when the answer to 2 is no.
- **Thread context is given when STRIDEr answers in a thread it has not answered in
  before** (FR-046). That is "once", without anything having to remember it: after the
  first answer, question 2 is yes. Not counting the fixed sentences means a thread whose
  first try ended in the apology still gets its context on the next try.
- **Rationale**: Slack is where these facts are true. Nothing expires and nothing can
  disagree with what people see in the thread.
- **Consequence for the spec**: FR-046 said "the first time STRIDEr is mentioned". It now
  says "the first time STRIDEr answers", which is the same in the ordinary case and also
  covers a thread where the first mention was not answered.

## Decision 6: Duplicates

- **Decision**: Three things together.
  1. The queue's deduplication ID is `{channel}:{ts}`. A second delivery of the same
     message within 5 minutes is dropped by the queue (A20). That covers the `message`
     twin of an `app_mention` (S7) and Slack's first two retries (S4).
  2. The front door ignores an event whose message is more than 4 minutes old, going by
     the `ts` in the event. Slack's third retry comes 5 minutes after the first delivery,
     outside the queue's window, and this drops it.
  3. A message is handed to the worker once. If the worker does not finish, the queue
     moves the message to the held-back queue and the cleanup function deals with it
     (Decision 15). The worker never runs twice on one message.
- **Rationale**: `event_id` cannot be the key, because the twin events have different ones.
  With no table there is nowhere to record "answered", so the guarantee has to come from
  never running twice.
- **Costs**, both accepted:
  - Slack sometimes delivers events late, after a problem on its side. A message that
    arrives more than 4 minutes late is ignored, and so is a message when the front door
    was failing for the whole 5 minutes of Slack's retries. Nobody is told.
  - AWS recommends at least five receives, because a function that is being throttled can
    use up a receive without running (A21). With one receive, such a message goes to the
    cleanup function unanswered. Throttling needs the account to be out of Lambda
    capacity, which this workspace's traffic cannot cause.
- **Alternatives considered**: marking each reply with hidden Slack metadata naming the
  message it answers, and looking for it before answering. Exact, but it needs a thread
  read for every message, which the owner asked to avoid.

## Decision 7: Two attempts, inside one run of the worker

- **Decision**: The worker calls the agent, and on failure calls it once more after a
  2-second pause. If both fail it posts the apology, removes the reaction, writes its log
  record and finishes normally. It sends nothing to the held-back queue: the person has
  been told, and the log is the record.
- **Rationale**: Letting the queue redeliver would make the second attempt wait a whole
  visibility timeout, minutes, with the person looking at the eyes, and would hold up the
  rest of the thread for as long (A19).
- **Timeouts**: each agent call is allowed 100 seconds, with the SDK's own retries off.
  The function's timeout is 240 seconds. The queue's visibility timeout is 300 seconds,
  not AWS's recommended six times (A22); with one receive (Decision 6) nothing is retried
  by the queue, so the recommendation's purpose does not apply.
- **What counts as a failed attempt**: an exception from the call, a reply that is not
  JSON, `kind` `error`, or no reply in 100 seconds. `input_rejection` is not a failure.
- **When Slack cannot say** what the worker needs to know, after a call has been tried
  three times (FR-053, confirmed by the owner on 2026-11-16):
  - a reply with no mention, thread unreadable: nothing shown. The thread may not be
    STRIDEr's.
  - writer cannot be looked up: nothing shown. STRIDEr does not respond to someone it
    does not know it may answer.
  - a mention from a full member, thread unreadable: the apology. STRIDEr was plainly
    addressed by someone it may answer, so silence would be the wrong signal. Answering
    without the thread's earlier messages was rejected: a confident answer missing its
    context is worse than an honest apology.
  All three are logged as failures.

## Decision 8: What the agent is sent

- **Decision**: `{"prompt": <text>, "slackUserId": <the writer's ID>}` with no `actorId`.
  The session is `slack-{team}-{channel}-{thread_ts}` with the dot in `thread_ts` replaced
  by a hyphen, which is at least 33 characters and uses only safe characters (A5).
- **Rationale**: **`actorId` must not be the person.** The agent keeps memory by session
  and by actor (R2), so giving each person their own would split a thread's conversation
  in two, against FR-020. Leaving it out puts everyone in a thread in one memory. The
  agent ignores fields it does not know (R1), so `slackUserId` satisfies FR-019 without
  changing the agent, and is there for a later feature to read. `runtimeUserId` was not
  used: it needs another permission and means something else (A4).
- **Thread context** (FR-046, FR-047), when there is any:

  ```text
  Earlier messages in this Slack thread, oldest first:
  <@U111>: text of the first message
  <@U222>: text of the second message

  Message to answer:
  text of the message, with the mention of STRIDEr removed
  ```

  The whole prompt must fit in `MaxPromptChars`, which the worker is given as a setting.
  Earlier messages are dropped from the oldest until it fits, and the first line becomes
  "Some earlier messages were left out. The rest, oldest first:". If the message alone is
  over the limit, the worker posts the too-long sentence and does not call the agent.
- **The limit is raised**: 4,000 characters is small for a thread. The owner chose on
  2026-11-16 to set `MaxPromptChars` to 16,000 in `cfn-parameters.json` as part of this
  feature. It is the agent's setting and the one thing about the agent this feature
  changes. It applies to every caller of the agent, not only Slack, and a longer prompt
  costs more model input.

## Decision 9: Posting the reply

- **Decision**: `chat.postMessage` with `markdown_text` and `thread_ts` (S20). A reply over
  11,000 characters is split at paragraph breaks, then line breaks, then anywhere, and the
  pieces are posted in order. When there is more than one piece, each ends with a label,
  `(part 1 of 3)`. A failed post is tried up to three times, a second apart, without
  calling the agent again. If a piece still cannot be posted, the worker posts the
  reply-incomplete sentence, or the apology when nothing was posted.
- **Why the label**: it lets the person see a piece is missing, and it lets the cleanup
  function tell from the thread alone that a reply was cut off by a crash (Decision 15).
  Confirmed by the owner on 2026-11-16.
- **Rationale**: Slack converts standard Markdown itself, so FR-018 needs no converter in
  this repository. 11,000 leaves room under the 12,000 limit.
- **Alternatives considered**: converting Markdown to Slack's own format in code. More
  code and more ways to be wrong. Kept as the fallback if S21 fails.

## Decision 10: Secrets

- **Decision** (revised 2026-11-17, at the owner's direction): the two secrets stay where
  feature 006 put them, as the GitHub secrets `SLACK_SIGNING_SECRET` and `SLACK_BOT_TOKEN`.
  `cfn-parameters.json` passes them to the template as `NoEcho` parameters, the way
  `AWS_ECR_REPO` is already passed. The template puts each in its own Secrets Manager
  secret. Each function reads its own secret when it runs, through Powertools, and keeps
  it for 5 minutes. The front door may read only the signing secret; the worker and the
  cleanup function only the bot token.
- **What the secrets are for**: both are used only by this repository's own code, at run
  time. The signing secret computes the check on every request; the bot token
  authenticates every call to Slack. Nothing in AWS consumes either directly and neither
  is rotated automatically, so nothing forced the choice of store.
- **Rationale**: the owner wants every secret kept in one place, GitHub. Secrets Manager
  was chosen over putting the values straight into the functions' environment variables
  because there they could be read by anyone able to view a function's configuration,
  and the bot token can post as STRIDEr and read channels. Two secrets cost $0.80 a month.
- **Consequences**: no step by hand in AWS. A replaced secret takes effect at the next
  deployment, within 5 minutes of it. A value changed directly in Secrets Manager is put
  back by the next deployment.
- **Alternatives considered**:
  - *Parameter Store, created by hand.* This plan's first design. It kept each secret in
    two places and needed a manual step before the first deployment.
  - *Environment variables from the same parameters.* Free and with no lookup at run
    time, but visible in each function's configuration.
  - *Parameter Store from the same parameters.* CloudFormation cannot create a
    SecureString parameter.

## Decision 11: The public address

- **Decision**: `https://engineering-agents.sandbox.serverlessops.io/slack/events`, one
  `POST` route. A regional custom domain with a certificate validated through the hosted
  zone, whose ID comes from Parameter Store as in the convention (R8). Throttled at 5
  requests a second with a burst of 10. No authorizer, no request validator, **execution
  logging off**, access logging on with the convention's format and 7 days' retention.
- **Rationale**: 5 a second is far above one workspace's traffic and caps what a flood can
  cost (FR-007). The address check and the stable address need nothing more.
- **Departures from the convention**, each for FR-033:
  - No request validator: its results are written to the log (A18), and Slack owns the
    shape of the body.
  - Execution logging off, where the convention has `INFO`: it is not established that
    bodies stay out (A17), and the access log already records every request.
  - The handlers do not log the event, where the convention logs it at debug (R9).
- **Only on `main`** (FR-040): every resource of the receiving service has the condition
  `CodeBranch` equals `main`. A branch stack, when branch deployments return, has no
  address and cannot clash over the hostname.

## Decision 12: Finding one message in three logs

- **Decision**: The front door logs API Gateway's request ID as `correlationId` and puts
  it on the queued message. The worker logs that `correlationId`, the session, and the
  `requestId` the agent returned. The agent already logs its `requestId` and session.
- **Rationale**: The agent takes its request ID from the runtime, and a caller-supplied
  one is not documented. Changing the agent's record is out of scope. The worker's record
  joins the other two.
- **Consequence for the spec**: FR-036 asked for one identifier in all three records. It
  now asks that the worker's record carry the identifiers of the other two.

## Decision 13: Code layout and libraries

- **Decision**: The convention's layout, added beside the agent: `src/handlers/` for the
  three functions, `src/common/` for a small shared package, tests under
  `tests/unit/handlers/`, sample events and schemas under `data/handlers/`.
  - `ReceiveSlackEvent` uses Powertools, the standard library, and the `boto3` that comes
    with the Lambda runtime, for the one call that sends to the queue. The signature check
    is `hmac.compare_digest`.
  - `AnswerSlackMessage` uses Powertools, `slack_sdk` for the six Slack methods, and a
    packaged `boto3` (A9).
  - `CleanUpSlackMessage` uses Powertools and `slack_sdk`.
- **Rationale**: Feature 006 avoided the Slack SDK for a pipeline script that made a few
  calls with its own error mapping. The worker makes six kinds of call that need rate
  limit handling and paging, which the SDK has. The front door stays small so it starts
  fast.
- **Dependencies for tests** go in `[dev-packages]` only, so the agent's image does not
  change (R6): `aws-lambda-powertools`, `slack-sdk`, `moto`, `pytest-mock` and the shared
  package.

## Decision 14: Getting from 006's state to working

The order, which the handbook will give:

1. The change is merged. `main.yml` deploys the receiving service. `slack-app.yml` sends
   the new permissions, the events and the address to Slack, and **fails saying the app
   must be installed again**, as feature 006 defines (R7).
2. The owner verifies the address in the app's settings (S25).
3. The owner installs the app again, compares the bot token (S24), and, if it
   changed, stores the new one as the GitHub secret and runs **Main** again.
4. The owner runs the Slack app workflow by hand with `apply`. It passes.
5. The owner adds STRIDEr to a channel and mentions it.

## Decision 15: A cleanup function on the held-back queue

- **Decision**: A third function, `CleanUpSlackMessage`, is triggered by the held-back
  queue. It deals with a message the worker did not finish: the worker crashed, ran out
  of memory or time, or never ran. For each message it reads the thread once, from the
  message onward, and then:
  1. If the message has no eyes reaction from STRIDEr, the worker never got as far as
     deciding to answer. Do nothing visible.
  2. If it has the reaction and STRIDEr has posted in the thread since the message, the
     person already has their reply or apology. Remove the reaction. One exception: if
     the last such post is a labelled part that is not the final one, post the
     reply-incomplete sentence first (Decision 9).
  3. If it has the reaction and STRIDEr has not posted, post the apology, then remove the
     reaction.
  It writes a log record and the message is deleted from the queue.
- **Rationale**: The owner's idea, proposed as a Lambda destination. Destinations do not
  fire for a function that is driven by a queue; AWS's own advice for that case is a
  dead-letter queue on the queue, which is what this is. A separate small function was
  preferred to cleaning up on a redelivery inside the worker, because whatever killed
  the worker may kill it again, and this function shares none of its dependencies on the
  agent.
- **Why step 2 is exact**: the queue gives the worker one message of a thread at a time
  (A19), so anything STRIDEr posted in the thread after the person's message is its
  response to that message.
- **Why the reaction is the signal**: the worker adds the eyes only after it has decided
  the message is answerable and the writer is a full member. No reaction means no
  apology is owed, and none is posted into a thread that was never STRIDEr's.
- **It is safe to run twice.** After step 3 has posted, a second run finds the post and
  falls into step 2.
- **Timing**: the queue moves an unfinished message after its visibility timeout, 300
  seconds, so the apology for a crashed worker arrives five to six minutes after the
  crash. If the cleanup function itself fails, the queue offers the message again until
  it is 60 minutes old and then deletes it.
- **Access**: it may read the bot token and receive from the held-back queue. It cannot
  call the agent.

## Decision 16: A thread older than the agent's memory

- **Decision**: A thread that began longer ago than the agent keeps memory
  (`MemoryEventExpiryDays`, 7 by default) is no longer STRIDEr's. The age is worked out
  from the thread's own timestamp, which every message in it carries.
  - A reply with no mention in such a channel thread is ignored by the front door.
  - A mention in such a thread, or a reply in such a direct-message thread, gets a fixed
    sentence asking the person to start a new conversation. The eyes are added first and
    removed after, as for any reply. The agent is not called.
- **Rationale**: The owner's direction: nothing STRIDEr does should last 7 days, and a
  person should be told when it has forgotten. Without this rule STRIDEr would answer in
  an old thread with no memory of it and without the thread's earlier messages, because
  it had "answered before" (Decision 5).
- **Checked first.** The worker looks at the thread's age before it reads the thread, so
  an old thread costs no call to Slack and cannot end in the apology by mistake.
- **A bluntness to accept**: the cut-off is the thread's age, not the time since its last
  message. A thread still active on its eighth day is cut off too. By then the agent has
  lost the beginning of it.

## Open items

Each is tried by an early task. None blocks writing the code.

| # | To confirm | If wrong |
|---|------------|----------|
| O1 | ~~The Parameter Store parameter that holds the hosted zone's ID.~~ **Confirmed by the owner on 2026-11-16**: it is `/org/dns/ZoneId`, and the owner created the `sandbox.serverlessops.io` zone in the hosting account (A15, R8). The first deployment shows whether the certificate validates. | If the certificate does not validate, the deployment waits and then fails; the cause would be that the parameter read in the deployment account is not this zone's ID. |
| O2 | The agent's HTTP 500 reaches the worker as an exception or as `statusCode` 500 (A2). | Either is handled as a failed attempt; the test covers both. |
| O3 | `markdown_text` is accepted with the bot token (S21). | Fall back to converting to Slack's format in code (Decision 9). |
| O4 | A mention in a channel arrives as two events with the same `channel` and `ts` (S7). | If only one arrives, nothing changes. If the `ts` differ, a mention in an active thread is answered twice and the key must change. |
| O5 | `conversations.replies` with `latest` set to a reply's `ts` and `inclusive` returns the parent and every reply up to it (S15). | Read the whole thread and ignore what comes after. |
| O10 | Moving a message to a FIFO dead-letter queue restarts its retention clock (A27). | If it does not, held-back messages last under an hour in total, which is shorter and still within what the owner asked. |
| O6 | The body reaches the function exactly as sent (A10). | Proven or disproven by the address check in step 3 above. |
| O7 | `python3.14` on arm64 (A8), and the explicit permission is needed (A16). | Use x86_64; drop or keep the permission. Seen at the first deployment. |
| O8 | Events are delivered between the manifest update and the manual verification (S25). | Nothing to change; it decides only whether step 3 can wait. |
| O9 | Removing a reaction tells nobody (S19); installing again keeps the token (S24). | Recorded in the quickstart for the owner; no code depends on either. |
| O11 | Whether Slack sends `app_mention` for a mention in a group direct message. The event has no `channel_type`, so the front door cannot tell it from a channel mention. | If it does, STRIDEr answers in a thread there. Group direct messages are out of scope and tracked in issue #13; nothing is built either way. |
| O12 | A message returned by `conversations.replies` lists its reactions, with who added each, without a further permission (Decision 15). | The cleanup function calls `reactions.remove` first and takes "there was nothing to remove" to mean the worker never started. |
