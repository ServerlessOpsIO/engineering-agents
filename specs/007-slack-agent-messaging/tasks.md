# Tasks: STRIDEr Slack Messaging

**Input**: Design documents from `/specs/007-slack-agent-messaging/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/slack-events.md, quickstart.md

**Tests**: Included. FR-043 requires unit tests for all three programs that contact
neither AWS nor Slack.

**Organization**: Tasks are grouped by user story. All paths are in this repository
(`engineering-agents`). "The convention template" is the sibling checkout
`../backstage-aws-sam-python-template` (`skeleton/base`, `skeleton/crud`,
`functions/crud`). Tasks marked **(owner)** need the AWS deployment account or the
`serverlessops` Slack workspace and can only be done by the project owner.

**Two rules that apply to every task**:

- Message text, thread text and reply text are never logged (FR-033). No handler logs its
  event or a queue record, at any log level, including in exception handlers.
- `template.yaml`'s existing resources (`AgentExecutionRole`, `AgentRuntime`,
  `AgentMemory`), `src/agent/` and the existing tests are not changed (FR-044). The one exception is the value of
  `MaxPromptChars` in `cfn-parameters.json` (T011).

**Shared package**: requirements.txt (`-e src/common/`). Found by T013 on 2026-11-16: `sam build` copies `common` into the function's artifact from that line, so no layer is needed.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`[US1]` to `[US6]`)
- Every task names a file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the project for Lambda functions beside the existing agent.

- [X] T001 Add to `[dev-packages]` in `Pipfile`, each with a pinned version: `aws-lambda-powertools`, `slack-sdk`, `moto` with the `sqs` and `ssm` extras, `pytest-mock`, and `common = {editable = true, path = "src/common"}`. Add nothing to `[packages]`: those are installed in the agent's image (research R6). Run `pipenv lock`, then compare `Pipfile.lock` with `git diff` and restore by hand any entry under `default` that moved, as happened in feature 006; confirm with `pipenv verify`
- [X] T002 Create the shared package: `src/__init__.py`, `src/handlers/__init__.py`, `src/common/setup.py` (from the convention template's `skeleton/base/src/common/setup.py`, with name `common`, description "engineering-agents common code", no author line, `python_requires='>=3.14'`), `src/common/common/__init__.py`, and `src/common/common/util/__init__.py` with `src/common/common/util/dataclasses.py` copied from `skeleton/base/src/common/common/util/dataclasses.py`. Also create a throwaway `src/handlers/_probe/function.py` with a one-line `handler` and a `requirements.txt` that pulls in the shared package the way the convention template's handlers do (`-e src/common/`), for T013
- [X] T003 [P] Add `.` to `pythonpath` in `pytest.ini` (keeping `src/agent scripts`) so tests can import `src.handlers.<Name>.function`
- [X] T004 [P] Add the `lambda_function_context` fixture from the convention template's `skeleton/base/tests/conftest.py` to `tests/conftest.py`, keeping the existing `MODEL_ID` line, and create empty `tests/unit/handlers/__init__.py` and `tests/unit/common/__init__.py`. Do not add `tests/unit/__init__.py`; the existing flat tests rely on its absence
- [X] T005 Run `pipenv install --dev` and `pipenv run test-unit`; all 212 existing tests must still pass before any new code is written (`tests/unit/`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The records, the text handling and the queues that every story uses.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 Create `src/common/common/model/__init__.py` and `src/common/common/model/slack.py` with: a `QueuedMessage` dataclass with exactly the fields of `data-model.md` "Queued message" (`teamId`, `channel`, `channelType` one of `channel`, `group`, `im`, `unknown`, `ts`, `threadTs`, `isReply`, `user`, `text`, `eventType` one of `app_mention`, `message`, `eventId`, `correlationId`, `receivedAt` ISO 8601 UTC), with `to_json()` and `from_json()`; `message_group_id()` returning `{channel}:{threadTs}`; `deduplication_id()` returning `{channel}:{ts}`; `session_id()` returning `slack-{teamId}-{channel}-{threadTs with "." replaced by "-"}`, raising if the result is under 33 characters or has a character outside letters, digits, `-` and `_`; and string constants for every outcome and reason in `data-model.md` "Outcomes", including the cleanup function's
- [X] T007 [P] Write `tests/unit/common/test_slack_model.py`: round trip through JSON; the group and deduplication IDs; the session ID for a thread reply and for a top-level message; the same thread always giving the same session and two threads giving different ones (FR-020); the length and character checks
- [X] T008 [P] Create `src/common/common/slack/__init__.py` and `src/common/common/slack/text.py` with: the five fixed sentences as constants with exactly the text in `data-model.md` "Fixed sentences" (Apology, Too long, Nothing asked, Start again, Reply incomplete) and `FIXED_SENTENCES` as a set of them; `mentions(text, bot_user_id)` true for `<@ID>` and `<@ID|name>`; `strip_mention(text, bot_user_id)` removing both forms and trimming, changing nothing else (FR-014); `build_prompt(text, earlier, max_chars)` returning `(prompt, dropped_count)` in the format of `research.md` Decision 8, dropping the oldest earlier messages until it fits and changing the first line to "Some earlier messages were left out. The rest, oldest first:" when any are dropped (FR-047), and raising `TooLong` when the message alone exceeds `max_chars`; `split_reply(text, limit=11000)` returning a list of parts split at paragraph breaks, then line breaks, then anywhere, with no text lost, each ending with a last line `(part n of m)` when there is more than one part and no label when there is one (FR-017); and `incomplete_part(text)` true when text ends with `(part n of m)` and n is less than m
- [X] T009 Write `tests/unit/common/test_slack_text.py` covering each function in T008, including: both mention forms; a mention of another person left in place; a prompt with no earlier messages equal to the stripped text; earlier messages in order with their writers; oldest dropped first and the count returned; the message alone over the limit; a reply at exactly the limit; a reply of 25,000 characters giving three labelled parts whose text, with labels removed, joins back to the original; `incomplete_part` for the first, the last and an unlabelled part
- [X] T010 Add to `template.yaml`, changing no existing resource: parameters `Hostname` (String), `DnsZoneId` (`AWS::SSM::Parameter::Value<String>`), `SlackSigningSecretParameter` (String, default `/engineering-agents/slack/signing-secret`) and `SlackBotTokenParameter` (String, default `/engineering-agents/slack/bot-token`); a condition `ConnectSlack` true when `CodeBranch` equals `main`; a `Globals` section for `Function` with `Runtime: python3.14`, `Architectures: [arm64]`, `Timeout: 3`, `MemorySize: 512` and the environment variable `POWERTOOLS_SERVICE_NAME` set to the stack name; and, both with `Condition: ConnectSlack`, `SlackHeldBackQueue` (FIFO, `MessageRetentionPeriod: 3600`, `VisibilityTimeout: 60`, `SqsManagedSseEnabled: true`) and `SlackMessageQueue` (FIFO, `ContentBasedDeduplication: false`, `MessageRetentionPeriod: 3600`, `VisibilityTimeout: 300`, `SqsManagedSseEnabled: true`, redrive to `SlackHeldBackQueue` with `maxReceiveCount: 1`); and conditional outputs `SlackMessageQueueUrl` and `SlackHeldBackQueueUrl`
- [X] T011 [P] Add `"Hostname": "engineering-agents.sandbox.serverlessops.io"` and `"DnsZoneId": "/org/dns/ZoneId"` to `cfn-parameters.json`, and `"MaxPromptChars": 16000`, which raises the agent's prompt limit from its default of 4,000 so that thread context fits (the owner's decision of 2026-11-16; the parameter itself is not changed in `template.yaml`)
- [X] T012 Run `sam validate --lint` on `template.yaml` and fix what it reports
- [X] T013 Add a temporary `ProbeFunction` (`CodeUri: ./src/handlers/_probe`, `Condition: ConnectSlack`) to `template.yaml`, run `sam build`, and check whether `.aws-sam/build/ProbeFunction/` contains the `common` package. If it does, write "Shared package: requirements.txt (`-e src/common/`)" under the heading of this file, `specs/007-slack-agent-messaging/tasks.md`. If it does not, add a `CommonLayer` (`AWS::Serverless::LayerVersion`, `BuildMethod: makefile`) built with the convention template's `skeleton/base/src/common/Makefile` copied to `src/common/Makefile`, reference it from `Globals`, and write "Shared package: layer". Then remove `ProbeFunction` from `template.yaml` and delete `src/handlers/_probe/`

**Checkpoint**: Shared code is tested and the template validates.

---

## Phase 3: User Story 2 - Only Slack can reach the agent (Priority: P1)

**Goal**: A public address that accepts a request only when Slack's signature proves it,
and answers Slack's address check.

**Independent Test**: The unit tests reject a request with a missing, wrong or stale
signature and accept a correctly signed one. Once deployed, `quickstart.md` scenario D
returns 401 twice.

This story is done before User Story 1 because User Story 1's front door is built on it.
Both are P1.

### Tests for User Story 2

- [X] T014 [P] [US2] Write `tests/unit/common/test_slack_signature.py` for `verify(signing_secret, timestamp, signature, body, now)`: a correct signature passes; a missing timestamp, a missing signature, a timestamp that is not a whole number, a wrong signature, a signature for a different body, and a timestamp 301 seconds before or after `now` all fail; 300 seconds passes; the body is used exactly as given
- [X] T015 [P] [US2] Create sample API Gateway proxy events and their schemas, following the convention template's `functions/crud/data/handlers/` layout, in `data/handlers/ReceiveSlackEvent/`: `event-url-verification.json`, `event-app-mention.json`, `event.schema.json`, `output.json`, `output.schema.json`. Sample message text must be invented and harmless
- [X] T016 [US2] Write `tests/unit/handlers/ReceiveSlackEvent/__init__.py` and `tests/unit/handlers/ReceiveSlackEvent/test_function.py` in the convention template's style (fixtures for context, events and the function module; `moto` for SQS and SSM with a SecureString signing secret), with a helper that signs a sample event. Cases: no signature gives 401 and nothing on the queue; wrong signature the same; stale timestamp the same; header names in lower case are accepted; a body that is not JSON gives 400; a signed `url_verification` gives 200 with `{"challenge": ...}` (FR-004); a base64-encoded body is decoded before checking; and no captured log line contains the sample message text or the signing secret (FR-031, FR-033)

### Implementation for User Story 2

- [X] T017 [US2] Implement `src/common/common/slack/signature.py`: `verify()` as tested in T014, building `v0:{timestamp}:{body}`, HMAC-SHA256 with the signing secret, `v0=` prefix, compared with `hmac.compare_digest` (FR-002, contract §1)
- [X] T018 [US2] Implement `src/handlers/ReceiveSlackEvent/__init__.py`, `src/handlers/ReceiveSlackEvent/requirements.txt` (the shared package, by the mechanism recorded at the top of this file, and `aws_lambda_powertools`) and `src/handlers/ReceiveSlackEvent/function.py` in the convention template's handler style (Powertools `Logger`, `event_source(data_class=APIGatewayProxyEvent)`, a thin `handler` calling `_main`, dataclasses for output), **without** the convention's `LOGGER.debug('Event', ...)` line. It reads the signing secret with Powertools `get_parameter(name, decrypt=True, max_age=300)` from the name in `SLACK_SIGNING_SECRET_PARAMETER`; runs the checks of contract §1 in order using `decoded_body`; returns 401 or 400 with `{"message": ...}`; answers `url_verification`; returns 200 `{}` for anything else; and writes one log record with the front door fields of `data-model.md` "Log records" and no text
- [X] T019 [P] [US2] Create `openapi.yaml` at the repository root in the convention template's form (`skeleton/crud/openapi.yaml`): one path, `POST /slack/events`, with an `AWS_PROXY` integration to `ReceiveSlackEventFunction`, no `security`, no request validators, and no health route
- [X] T020 [US2] Add to `template.yaml`, all with `Condition: ConnectSlack`, following `skeleton/crud/template.yaml`: `SiteCertificate` (DNS validation in `DnsZoneId`); `RestApiLogGroup` (`/aws/api-gateway/${AWS::StackName}`, 7 days); `RestApi` (`AWS::Serverless::Api`, `StageName: !Ref CodeBranch`, regional `Domain` with `Hostname`, the certificate and `Route53.HostedZoneId`, `AccessLogSetting` with the convention's format, `MethodSettings` for `/*` and `*` with `LoggingLevel: OFF`, `DataTraceEnabled: false`, `MetricsEnabled: true`, `ThrottlingRateLimit: 5`, `ThrottlingBurstLimit: 10`, and `DefinitionBody` including `openapi.yaml`); `ReceiveSlackEventFunction` (`CodeUri: ./src/handlers/ReceiveSlackEvent`, `Handler: function.handler`, environment `SLACK_SIGNING_SECRET_PARAMETER`, `SLACK_MESSAGE_QUEUE_URL` and `MEMORY_EXPIRY_DAYS` from `MemoryEventExpiryDays`, policies for `ssm:GetParameter` on the signing secret parameter only, `kms:Decrypt` limited by `kms:ViaService` to Systems Manager, and `sqs:SendMessage` on `SlackMessageQueue` only); `ReceiveSlackEventFunctionInvokePermission` for `apigateway.amazonaws.com`; and the output `SlackEventsUrl` as `https://${Hostname}/slack/events`. Add an `AWS::Logs::LogGroup` for the function, named `/aws/lambda/` followed by the function's name, with `RetentionInDays: 30` and the same condition (FR-037)
- [X] T021 [US2] Run `sam validate --lint` and `sam build`; confirm `.aws-sam/build/ReceiveSlackEventFunction/` can import `common` by the mechanism recorded at the top of this file

**Checkpoint**: The front door rejects everything but Slack and passes Slack's address check. It queues nothing yet.

---

## Phase 4: User Story 1 - A person mentions STRIDEr and gets a reply in a thread (Priority: P1) 🎯 MVP

**Goal**: A mention in a channel gets the eyes, then the agent's reply in a thread, then
the eyes removed.

**Independent Test**: With Slack and the agent replaced by fakes, a signed `app_mention`
event put through the front door and then the worker produces `reactions.add`, one agent
call with the thread's session, one `chat.postMessage` in the thread, and
`reactions.remove`. Once deployed, `quickstart.md` scenario C.

### Tests for User Story 1

- [X] T022 [US1] Add to `tests/unit/handlers/ReceiveSlackEvent/test_function.py`: a signed `app_mention` puts exactly one message on the queue with every field of the queued message set as `data-model.md` says, the group `{channel}:{threadTs}` and the deduplication ID `{channel}:{ts}`; a top-level `message` in a channel queues nothing (FR-010); an event with `bot_id` queues nothing, mention or not (FR-009); an event with no `user` queues nothing; `message_changed`, `message_deleted` and `channel_join` queue nothing; an event of another type queues nothing; the same event sent twice leaves one message on the queue (FR-011); a queue that cannot be reached gives 500
- [X] T023 [P] [US1] Write `tests/unit/common/test_slack_api.py` for `src/common/common/slack/api.py` with a fake `WebClient`: `bot_user_id()` calls `auth.test` once and remembers it, and raises `SlackUnavailable` when Slack will not answer; `is_full_member(user, team_id)` is true only when the user's `team_id` matches and `is_restricted`, `is_ultra_restricted`, `is_bot` and `deleted` are all false, remembers its answer for an hour, and raises `SlackUnavailable` when Slack cannot say; `add_eyes` treats `already_reacted` as success and returns false on any other error without raising; `remove_eyes` treats `no_reaction` as success; `post(channel, thread_ts, markdown)` sends `markdown_text` and `thread_ts` and tries up to three times
- [X] T024 [P] [US1] Write `tests/unit/common/test_agentcore.py` for `src/common/common/agentcore.py` with a stubbed client: the request carries `agentRuntimeArn`, `runtimeSessionId` and a JSON payload with `prompt` and `slackUserId` and **no** `actorId` (research Decision 8); `kind` `answer` and `input_rejection` are returned with `text` and `requestId`; `kind` `error`, `statusCode` 500, an exception from the client, and a body that is not JSON each raise `AgentFailed` (research O2); the client is built with a 100-second read timeout and no retries of its own
- [X] T025 [P] [US1] Create sample SQS events and schemas in `data/handlers/AnswerSlackMessage/`: `event-mention.json` (one record whose body is a queued message, with `MessageGroupId` and `ApproximateReceiveCount` attributes), `event.schema.json`, `data.json`, `data.schema.json`
- [X] T026 [US1] Write `tests/unit/handlers/AnswerSlackMessage/__init__.py` and `tests/unit/handlers/AnswerSlackMessage/test_function.py` with fakes for the Slack API module and the agent module. Cases for a top-level mention: the calls happen in the order member check, add eyes, agent, post, remove eyes; the prompt has the mention removed and nothing else changed; the session is the thread's; the reply is posted with `thread_ts` equal to the message's `ts`; a writer who is not a full member gets no eyes, no agent call and no post, outcome `declined`/`not_member` (FR-010); a failure to add the eyes does not stop the answer (FR-013); the log record has the worker fields of `data-model.md` and the correlation ID and the agent's request ID (FR-036); and no captured log line contains the message text or the reply text

### Implementation for User Story 1

- [X] T027 [US1] Add the front door rules to `src/handlers/ReceiveSlackEvent/function.py` (research Decision 3, rules 1 to 4 and 7): ignore what is not `app_mention` or `message`, what has `bot_id` or no `user`, and a `message` with a subtype other than none, `file_share` or `thread_broadcast`; queue an `app_mention`; ignore the rest for now. Build the `QueuedMessage` with `text` copied from the event, `correlationId` from the API Gateway request ID and `teamId` from the envelope, and send it with the runtime's `boto3` using `MessageGroupId` and `MessageDeduplicationId` from the model. Return 500 when the send fails
- [X] T028 [P] [US1] Implement `src/common/common/slack/api.py` as tested in T023, building `slack_sdk.WebClient` from the bot token read with Powertools `get_parameter(decrypt=True, max_age=300)` from the name in `SLACK_BOT_TOKEN_PARAMETER`, with the SDK's rate-limit and connection-error retry handlers set to three tries in all (FR-053)
- [X] T029 [P] [US1] Implement `src/common/common/agentcore.py` as tested in T024, using `boto3.client("bedrock-agentcore")` and the runtime ARN from `AGENT_RUNTIME_ARN`
- [X] T030 [US1] Implement `src/handlers/AnswerSlackMessage/__init__.py`, `src/handlers/AnswerSlackMessage/requirements.txt` (the shared package, by the mechanism recorded at the top of this file, `aws_lambda_powertools`, `slack_sdk`, `boto3`) and `src/handlers/AnswerSlackMessage/function.py` in the convention template's style, using Powertools `SqsFifoPartialProcessor` and `process_partial_response` so a failure never logs the record. For a message that is not a reply in a channel thread: contract §3 step 2 (member check), step 3 (eyes), step 4 without its failure branch (remove the mention), step 5 with no earlier messages, step 6 with a single attempt, step 8 posting each part from `split_reply`, step 9. Write one log record per message
- [X] T031 [US1] Add to `template.yaml`, with `Condition: ConnectSlack`: `AnswerSlackMessageFunction` (`CodeUri: ./src/handlers/AnswerSlackMessage`, `Timeout: 240`, environment `SLACK_BOT_TOKEN_PARAMETER`, `AGENT_RUNTIME_ARN` from `AgentRuntime`, `MAX_PROMPT_CHARS` from `MaxPromptChars` and `MEMORY_EXPIRY_DAYS` from `MemoryEventExpiryDays`; an `SQS` event on `SlackMessageQueue` with `BatchSize: 1`, `FunctionResponseTypes: [ReportBatchItemFailures]` and `ScalingConfig.MaximumConcurrency: 5`; policies for `ssm:GetParameter` on the bot token parameter only, `kms:Decrypt` limited to Systems Manager, and `bedrock-agentcore:InvokeAgentRuntime` on the runtime's ARN and on `${AgentRuntimeArn}/runtime-endpoint/*` only). Add an `AWS::Logs::LogGroup` for the function, named `/aws/lambda/` followed by the function's name, with `RetentionInDays: 30` and the same condition (FR-037). Then run `sam validate --lint` and `sam build`

**Checkpoint**: A mention is answered in a thread. Thread replies and direct messages are not queued yet.

---

## Phase 5: User Story 3 - The owner connects the Slack app to the agent by following the documentation (Priority: P1)

**Goal**: The Slack app asks for what it now needs and points at the address, and the
handbook says how to finish the job by hand.

**Independent Test**: `pipenv run slack-app check` passes with the new permissions and
the address, and the built manifest has the events and the address. The owner's part is
`quickstart.md` scenario B, done in Phase 10.

- [X] T032 [US3] Add two bot scopes to `slack/manifest.yaml`, each on its own line with a reason comment as feature 006 requires: `reactions:write  # Show that STRIDEr is working on a message, and clear it when done.` and `users:read  # Check that a person is a full member of the workspace before answering them.`
- [X] T033 [P] [US3] Set `event_request_url` to `https://engineering-agents.sandbox.serverlessops.io/slack/events` in `slack/settings.json`
- [X] T034 [US3] Update the feature 006 tests that assumed an empty address, now that the committed `slack/settings.json` has one. In `tests/unit/test_slack_definition.py`: the planned-scopes test expects the seven scopes in manifest order; the test that events are left out while there is no address sets an empty address in its temporary copy first; add a test that the committed files build a manifest with `event_subscriptions.request_url` and the four events. In `tests/unit/test_slack_commands.py`: the two tests that assert `"event_subscriptions" not in ...` set an empty address in their copy of `slack/` first; add one beside each that expects the events when the address is set. Check `tests/unit/test_slack_icon.py` for the same assumption. Run `pipenv run test-unit` and `pipenv run slack-app check` and confirm both pass
- [X] T035 [US3] Write `docs/handbook/09-slack-messaging.md` (FR-045): what the receiving service is, with the path diagram from the planning conversation; the six first-time steps of `research.md` Decision 14 in order, saying which are done by hand, with the two `aws ssm put-parameter` commands of `quickstart.md` scenario B; that the first merge makes the Slack app workflow fail until the app is installed again; how to replace a secret, and that it takes effect within 5 minutes with no deployment; how to find a failed message in the log, by outcome and reason, and open it in Slack from the channel and timestamp; what Slack does when deliveries keep failing and how to turn events on again; how to disconnect STRIDEr from Slack by emptying `event_request_url` in `slack/settings.json` and merging, and how to connect it again; and what people in the workspace need to know: add STRIDEr to a channel before mentioning it, replies come in a thread, only full members are answered, a thread older than 7 days must be started again, group direct messages are not supported (issue #13)
- [X] T036 [P] [US3] Update the other handbook pages: `docs/handbook/00-index.md` (link the new page); `docs/handbook/01-features.md` (replace the "Not yet" paragraph: STRIDEr now answers; list the receiving service); `docs/handbook/03-configuration.md` (the four new parameters, the two Parameter Store secrets, and `MaxPromptChars` now 16,000); `docs/handbook/04-architecture.md` (the new resources, the repository layout, and that the receiving service exists only in the `main` stack); `docs/handbook/05-ci-cd.md` (the functions are built by `sam build` and tested by `pipenv run test-unit`; no workflow changed); `docs/handbook/08-slack-app.md` (the address is now set; the two new permissions)

**Checkpoint**: Everything needed to connect is in the repository. Nothing is merged yet.

---

## Phase 6: User Story 4 - A conversation continues in its thread (Priority: P2)

**Goal**: STRIDEr answers replies in its threads without a mention, remembers the thread,
and reads a thread's earlier messages the first time it answers in it.

**Independent Test**: With fakes, a reply with no mention in a thread where STRIDEr was
mentioned is answered with the same session; the same reply in a thread with no mention
is dropped with nothing visible; a first mention part-way down a thread sends the earlier
messages to the agent. Once deployed, `quickstart.md` scenario E.

### Tests for User Story 4

- [X] T037 [P] [US4] Write `tests/unit/common/test_slack_thread.py` for `src/common/common/slack/thread.py` with a fake `WebClient`: `read_thread(channel, thread_ts, upto_ts)` calls `conversations.replies` with `latest` and `inclusive`, follows the cursor in pages of 200 and returns a result with `mentioned` (the message or an earlier one mentions STRIDEr), `answered_before` (an earlier message is STRIDEr's own and is not in `FIXED_SENTENCES` and is not an incomplete part) and `earlier` (writer and text of each earlier message, oldest first, including bots' and guests'); it raises `SlackUnavailable` when Slack cannot be read; `thread_expired(thread_ts, days, now)` is true only when the thread began more than `days` days before `now`
- [X] T038 [US4] Add to `tests/unit/handlers/ReceiveSlackEvent/test_function.py`: a `message` in a channel with `thread_ts` different from `ts` is queued with `isReply` true and `threadTs` set to the thread's; a parent message (`thread_ts` equal to `ts`) is not; a reply in a thread older than `MEMORY_EXPIRY_DAYS` is not queued and is logged `ignored`/`thread_expired`; an `app_mention` in such a thread is still queued; an `app_mention` and its `message` twin for one reply leave one message on the queue (FR-012)
- [X] T039 [US4] Add to `tests/unit/handlers/AnswerSlackMessage/test_function.py`, for a reply in a channel thread: no mention anywhere in the thread gives no member check, no eyes and no post, outcome `declined`/`not_strider_thread`; an earlier mention makes an unmentioned reply answerable, with the thread's session; when STRIDEr has not answered before, the prompt carries the earlier messages and the log has `contextMessages`; when it has, the prompt is the message alone (FR-046); earlier messages that do not fit are dropped oldest first and counted in `contextDropped`; the worker decides "mention" from the text and not from `eventType`; a thread older than the memory period, addressed by a full member, gets the eyes, the start-again sentence and the eyes removed, with no agent call and no `conversations.replies` call, outcome `declined`/`thread_expired` (FR-050); the thread cannot be read and the message has no mention gives nothing, outcome `failed`/`thread_unreadable`; the thread cannot be read and a full member mentioned STRIDEr gives the apology and no agent call (FR-053); two threads never share a session

### Implementation for User Story 4

- [X] T040 [US4] Implement `src/common/common/slack/thread.py` as tested in T037
- [X] T041 [US4] Add rule 6 to `src/handlers/ReceiveSlackEvent/function.py`: queue a `message` in a channel that is a reply, unless its thread is older than `MEMORY_EXPIRY_DAYS` days
- [X] T042 [US4] Add to `src/handlers/AnswerSlackMessage/function.py`: contract §3 step 1 for a reply in a channel thread, with both of its failure branches; passing `earlier` to `build_prompt` only when the thread has not been answered in before; and step 0 for an expired thread, checked before the thread is read

**Checkpoint**: Conversations work in channel threads.

---

## Phase 7: User Story 5 - A person talks to STRIDEr in a direct message (Priority: P2)

**Goal**: Direct messages are answered without a mention, each top-level message in its
own thread and session.

**Independent Test**: With fakes, a signed `message` event with `channel_type` `im` is
queued and answered in a thread under it with no thread read; a reply in that thread uses
the same session. Once deployed, `quickstart.md` scenario F.

- [X] T043 [US5] Add to `tests/unit/handlers/ReceiveSlackEvent/test_function.py`: a `message` with `channel_type` `im` is queued, top-level or reply; one from a bot is not; one that is an edit is not
- [X] T044 [US5] Add to `tests/unit/handlers/AnswerSlackMessage/test_function.py`, for a direct message: no `conversations.replies` call is made; a top-level message is answered in a thread under itself with a session of its own; a reply uses its thread's session; a second top-level message gets a different session (FR-021); a guest gets nothing; a reply in a thread older than the memory period gets the start-again sentence
- [X] T045 [US5] Add rule 5 to `src/handlers/ReceiveSlackEvent/function.py` (queue a `message` with `channel_type` `im`), and make the direct-message path in `src/handlers/AnswerSlackMessage/function.py` skip step 1 and apply step 0 to replies

**Checkpoint**: Both ways of reaching STRIDEr work.

---

## Phase 8: User Story 6 - When something goes wrong, the person is told and nothing is lost (Priority: P2)

**Goal**: Two attempts and then the apology; the right fixed sentence for each case; no
second reply; and a cleanup function for a message the worker did not finish.

**Independent Test**: With fakes, an agent that fails twice produces one apology and no
reply; a worker that never finished, with the eyes on the message and nothing posted,
produces the apology from the cleanup function. Once deployed, `quickstart.md` scenario G.

### Tests for User Story 6

- [X] T046 [US6] Add to `tests/unit/handlers/ReceiveSlackEvent/test_function.py`: an event whose message `ts` is more than 240 seconds old is not queued and is logged `ignored`/`too_old` (FR-051); one 239 seconds old is queued
- [X] T047 [US6] Add to `tests/unit/handlers/AnswerSlackMessage/test_function.py`: the agent fails once and then answers gives the reply and no apology, with `attempts` 2; fails twice gives one apology, the eyes removed, outcome `failed`/`agent_failed`, and exactly two agent calls (FR-024, FR-025); the apology contains no detail of the failure; a mention with no other text gives the nothing-asked sentence and no agent call, and so does an empty direct message; a reply with no text and no mention in one of STRIDEr's threads gives no post and no agent call, with the eyes removed (FR-029); a message over `MAX_PROMPT_CHARS`, and an `input_rejection` from the agent, give the too-long sentence and are not retried (FR-028); a reply in three parts where the second cannot be posted gives the reply-incomplete sentence, and where the first cannot be posted gives the apology (FR-052); a writer Slack cannot look up gives nothing, outcome `failed`/`membership_unknown`; STRIDEr's own user ID not being available gives nothing, outcome `failed`/`identity_unknown` (FR-053); a failure to remove the eyes is logged and does not change the outcome; in every case at most one of reply and apology is posted (FR-027); and the handler never returns a batch item failure for a failure it handled itself
- [X] T048 [P] [US6] Add to `tests/unit/common/test_slack_thread.py` tests for `since_message(channel, thread_ts, ts)`: it calls `conversations.replies` from the message onward and returns whether the message has an `eyes` reaction that includes STRIDEr's user ID, whether STRIDEr has posted after `ts`, and whether its last such post is an incomplete part; an `eyes` reaction from a person only does not count
- [X] T049 [P] [US6] Create `data/handlers/CleanUpSlackMessage/event.json` (an SQS record from the held-back queue whose body is a queued message) and `event.schema.json`
- [X] T050 [US6] Write `tests/unit/handlers/CleanUpSlackMessage/__init__.py` and `tests/unit/handlers/CleanUpSlackMessage/test_function.py` for the four rows of contract §6: no eyes gives no post and no reaction call, `cleaned_up`/`not_started`; eyes and a complete reply since gives only the eyes removed, `cleaned_up`/`already_answered`; eyes and nothing posted gives the apology and then the eyes removed, `cleaned_up`/`apologised`; eyes and an incomplete part gives the reply-incomplete sentence and then the eyes removed, `cleaned_up`/`reply_incomplete`. Also: running twice on the "nothing posted" case posts one apology; a Slack failure makes the handler report the record as failed so the queue offers it again; no captured log line contains the message text

### Implementation for User Story 6

- [X] T051 [US6] Add rule 0 to `src/handlers/ReceiveSlackEvent/function.py`: ignore an event whose message `ts` is more than 240 seconds before now
- [X] T052 [US6] Complete `src/handlers/AnswerSlackMessage/function.py` to contract §3 in full: the failure branch of step 2; both nothing-left branches of step 4 and the too-long branches of steps 5 and 6; the second attempt after a 2-second pause; step 7; the failure branch of step 8; and an outer guard so that any exception after the eyes were added still tries to remove them before the handler finishes normally. Stop with `failed`/`identity_unknown` when the bot's user ID cannot be read. The handler must not raise for a failure it has handled
- [X] T053 [US6] Add `since_message()` to `src/common/common/slack/thread.py` as tested in T048 (research Decision 15, O12)
- [X] T054 [US6] Implement `src/handlers/CleanUpSlackMessage/__init__.py`, `src/handlers/CleanUpSlackMessage/requirements.txt` (the shared package, by the mechanism recorded at the top of this file, `aws_lambda_powertools`, `slack_sdk`) and `src/handlers/CleanUpSlackMessage/function.py` as tested in T050, with one log record per message carrying the cleanup fields of `data-model.md`
- [X] T055 [US6] Add to `template.yaml`, with `Condition: ConnectSlack`: `CleanUpSlackMessageFunction` (`CodeUri: ./src/handlers/CleanUpSlackMessage`, `Timeout: 30`, environment `SLACK_BOT_TOKEN_PARAMETER`; an `SQS` event on `SlackHeldBackQueue` with `BatchSize: 1` and `FunctionResponseTypes: [ReportBatchItemFailures]`; policies for `ssm:GetParameter` on the bot token parameter and `kms:Decrypt` limited to Systems Manager, and nothing for AgentCore). Add an `AWS::Logs::LogGroup` for the function, named `/aws/lambda/` followed by the function's name, with `RetentionInDays: 30` and the same condition (FR-037). Then run `sam validate --lint` and `sam build`

**Checkpoint**: Every path ends with the person told, or deliberately not told, and a log record saying which.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T056 Run `pipenv run test-unit`: every new test and all 212 earlier tests pass with no AWS credentials and no network (FR-043, FR-044, SC-014). Record the count under "A" in `specs/007-slack-agent-messaging/quickstart.md`
- [X] T057 [P] Review the three functions' policies in `template.yaml` against FR-034 and contract §3 and §6: the front door cannot read the bot token or call the agent; the worker cannot read the signing secret or send to either queue; the cleanup function cannot call the agent; no policy uses a wildcard resource except where the action allows nothing narrower, and each such case has a comment
- [X] T058 [P] Search `src/handlers/` and `src/common/` for anything that could log text: `LOGGER.*event`, `log_event`, `POWERTOOLS_LOGGER_LOG_EVENT`, f-strings or `extra=` containing `text`, `prompt`, `body` or `record`; remove any found
- [X] T059 Read `docs/handbook/09-slack-messaging.md` against the finished code and `contracts/slack-events.md`, and correct any step, name or number that no longer matches
- [X] T060 [P] Add a line to `README.md` saying STRIDEr answers in Slack, with a link to `docs/handbook/09-slack-messaging.md`, if the README lists features

---

## Phase 10: Going live (owner)

**Purpose**: The manual steps, in order, and the checks that can only be made against
real Slack and real AWS. Results go in `specs/007-slack-agent-messaging/quickstart.md`.

- [X] T061 **(owner)** ~~Create the two SecureString parameters in the deployment account~~ No longer needed: on 2026-11-17 the owner chose to keep the secrets in GitHub only, and the deployment passes `SLACK_SIGNING_SECRET` and `SLACK_BOT_TOKEN` to the stack (see "Changes during implementation")
- [ ] T062 **(owner)** Merge the branch. Confirm **Main** passes, the certificate validated (research O1, O7) and the stack has the output `SlackEventsUrl`. Expect **Slack app** to fail with "install again"
- [ ] T063 **(owner)** Verify the event address in the Slack app's settings (research O6), install the app again, compare the bot token with the stored one and store it again if it changed (O9), then run **Slack app** by hand with `apply` and confirm it passes. Record the time taken and the result under "B" in `specs/007-slack-agent-messaging/quickstart.md` (SC-007, SC-015)
- [ ] T064 **(owner)** Run scenarios C to I of `specs/007-slack-agent-messaging/quickstart.md` and record each result there, including what was seen for the open items: `markdown_text` accepted (O3), a mention in a thread arriving as two events with one reply (O4), the thread read stopping at the message (O5), events before verification (O8), reaction notifications (O9), the held-back queue's clock (O10), a mention in a group direct message (O11, issue #13), and reactions in a thread read (O12, checked in scenario C). Scenarios G.4 and G.5 are covered by unit tests and are not run against the live stack
- [ ] T065 Update `specs/007-slack-agent-messaging/research.md` from the results of T062 to T064: mark each open item confirmed or wrong, and for any that is wrong apply the fallback its row names and add a task here

---

## Changes during implementation (2026-11-16)

Where the code differs from the wording of a task above. None changes behaviour the spec
describes.

- **The functions were written whole, not rule by rule.** `ReceiveSlackEvent` and
  `AnswerSlackMessage` each appear in several phases above. Each was written once with
  all its rules, with its tests, and the tasks in later phases were marked done together.
- **No Powertools batch processor** (T030, T054). The installed version of
  `SqsFifoPartialProcessor` cannot be told to report a failed batch instead of raising.
  Each handler loops over its records itself and returns `batchItemFailures`, which keeps
  what is logged about a failure fully in this repository's hands.
- **Part of a reply counts as an answer** (T037). The task said a thread where STRIDEr's
  only post is an unfinished reply has not been answered in. It has: the agent answered
  and remembers the thread, so the earlier messages are not sent again. Only the fixed
  sentences do not count.
- **A mention that Slack marks as edited is ignored** by the front door. Added because
  edits are to be ignored (FR-009) and a mention added by an edit may arrive as an
  `app_mention`. Not tried against Slack.
- **`boto3` was taken out of the shared package's requirements** (T002). The convention
  template lists it. Leaving it there packaged boto3 with the front door, which is meant
  to stay small; the worker lists boto3 itself.
- **Log groups are named after the stack, not the function** (T020, T031, T055):
  `/aws/lambda/<stack name>-<FunctionName>`, attached with `LoggingConfig`. A group named
  after the function could be created by Lambda before CloudFormation creates it.
- **Memory is 512 MB for all three functions**, set once in `Globals` (T010).
- **The secrets come from GitHub, not Parameter Store** (T010, T018, T020, T028, T031,
  T055, T061). Decided by the owner on 2026-11-17, after the first push. The template
  takes the two secrets as `NoEcho` parameters from `cfn-parameters.json`, keeps each in
  a Secrets Manager secret, and the functions read those. The Parameter Store names, the
  KMS statements and the manual step are gone. Spec FR-030 and FR-032 changed to match.
- **Both workflows gained one step.** The plan said `main.yml` and `branch.yml` need no
  change. `sam build` now packages Python functions and needs Python 3.14 on the runner to
  do it, so the `build_infra` job of each installs it first. Not yet run in GitHub
  Actions; the first push shows whether the build passes there.

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1** has no dependencies. **Phase 2** needs Phase 1.
- **Phase 3 (US2)** needs Phase 2. **Phase 4 (US1)** needs Phase 3: its front door is the
  one US2 builds.
- **Phase 5 (US3)** needs nothing but Phase 1 to write, and Phases 3 and 4 to mean
  anything. Its settings change turns events on, so it must not reach `main` before
  Phase 4 does.
- **Phases 6, 7 and 8 (US4, US5, US6)** each need Phase 4. They edit the same two
  handler files, so they are done one after another, in this order.
- **Phase 9** needs every phase before it. **Phase 10** needs Phase 9 and the owner.

### Within a phase

- Tests are written before the code they test, and fail first.
- Tasks that add to the same file are in order and are never marked [P]:
  `tests/unit/handlers/ReceiveSlackEvent/test_function.py` (T016, T022, T038, T043, T046),
  `tests/unit/handlers/AnswerSlackMessage/test_function.py` (T026, T039, T044, T047),
  `src/handlers/ReceiveSlackEvent/function.py` (T018, T027, T041, T045, T051),
  `src/handlers/AnswerSlackMessage/function.py` (T030, T042, T045, T052),
  `src/common/common/slack/thread.py` (T040, T053) and its test file (T037, T048), and
  `template.yaml` (T010, T013, T020, T031, T055).

### What can and cannot be validated before merging

- **Before merging**: everything in Phases 1 to 9, by unit tests, `sam validate` and
  `sam build`. Branch deployments are off (issue #10), so nothing is deployed from the
  branch.
- **Only on `main`**: the certificate and hostname, Slack's address check, real events,
  the agent call, and every open item in `research.md`. That is Phase 10.

## Parallel Execution Examples

```text
# Phase 1, after T001 and T002:
T003 pytest.ini            T004 tests/conftest.py

# Phase 2, after T006:
T007 test_slack_model.py   T008 slack/text.py   T011 cfn-parameters.json

# Phase 3:
T014 test_slack_signature.py   T015 data/handlers/ReceiveSlackEvent/   T019 openapi.yaml

# Phase 4, tests:
T023 test_slack_api.py   T024 test_agentcore.py   T025 data/handlers/AnswerSlackMessage/
# Phase 4, code:
T028 slack/api.py        T029 agentcore.py

# Phase 9:
T057 policy review   T058 log search   T060 README.md
```

## Implementation Strategy

### MVP

Phases 1 to 5: the front door, a mention answered in a thread, and the Slack app pointed
at it. That is User Stories 1 to 3 and is enough to see STRIDEr answer. If it were merged
alone, replies in threads and direct messages would be ignored, and a worker that died
would leave the eyes on the message.

### Order

All ten phases on this branch, merged once. The feature is small, the first real run can
only happen on `main`, and merging the MVP alone would put a half-finished experience in
front of people. Phase 10 follows the merge.

### Decided by the owner on 2026-11-16

No database; message text travels in the queue; queues keep a message for 60 minutes; a
cleanup function on the dead-letter queue; threads older than the agent's memory are
started again; messages more than 4 minutes old are ignored; long replies are labelled and
an incomplete one is announced; what happens when Slack cannot be asked (FR-053); group
direct messages are out of scope (issue #13).

### Still open

- The constitution is still the unfilled template, so no gates were applied.
- Eleven facts are unverified (`research.md`, O2 to O12). Each has a fallback and is
  checked in Phase 10.
- Nothing in the checklists: all 78 items of `checklists/messaging.md` and all 16 of
  `checklists/requirements.md` are marked.
