# STRIDEr Slack messaging

STRIDEr answers in Slack. A person mentions it in a channel, or sends it a direct message,
and the agent's reply appears in a thread under their message.

This page describes the receiving service: the part between Slack and the agent. The Slack
app itself, and the workflow that applies it, are in [The STRIDEr Slack app](08-slack-app.md).
The agent is in [Architecture](04-architecture.md).

The agent answers as it always has. It does not yet lead a STRIDE exercise; that is a later
feature.

## What people in the workspace need to know

- **Add STRIDEr to a channel first.** Slack does not tell STRIDEr about a mention in a
  channel it is not a member of.
- **Mention it to start.** In a channel, `@STRIDEr` and a question. In a direct message no
  mention is needed.
- **The reply comes in a thread.** An eyes reaction on your message means STRIDEr is
  working on it. The reaction goes when the reply is posted.
- **Carry on in the thread without mentioning it.** Once STRIDEr has been mentioned in a
  thread, it answers every message there. Everyone in the thread is in the same
  conversation.
- **Each thread is its own conversation.** STRIDEr remembers nothing from one thread in
  another. In a direct message, each new top-level message starts a new conversation.
- **Bring it into an existing thread by mentioning it there.** It reads the thread's
  earlier messages the first time it answers.
- **Only full members of the workspace are answered.** Guests and people from other
  organisations get no reaction and no reply.
- **A thread lasts 7 days.** After that STRIDEr no longer remembers it and asks you to send
  a new message outside the thread.
- **Group direct messages are not supported.** See issue #13.

## How it works

```text
                                   Slack
        ┌─────────────────────────────────────────────────────────────┐
        │  Events API                                     Web API     │
        └──────┬──────────────────────────────────────────────▲───────┘
               │ 1. POST /slack/events                        │
               │    signed with the signing secret            │ 5. users.info
               ▼                                              │ 6. reactions.add (eyes)
  ┌──────────────────────────┐                                │    conversations.replies
  │ API Gateway (REST)       │                                │      (channel thread
  │ engineering-agents       │                                │       replies only)
  │ .sandbox.serverlessops.io│                                │ 8. chat.postMessage
  │ throttle 5/s, access log │                                │    reactions.remove
  └────────────┬─────────────┘                                │
               │ 2. invoke                                    │
               ▼                                              │
  ┌──────────────────────────┐      ┌──────────────────┐      │
  │ Lambda                   │─────▶│ Parameter Store  │      │
  │ ReceiveSlackEvent        │ read │ signing-secret   │      │
  │ check signature, apply   │      │ bot-token        │      │
  │ rules, answer in < 3 s   │      └────────▲─────────┘      │
  └────────────┬─────────────┘               │ read           │
               │ 3. SendMessage              │                │
               ▼                             │                │
  ┌──────────────────────────┐               │                │
  │ SQS FIFO: work queue     │               │                │
  │ keeps 60 min, 1 receive  │               │                │
  └──────┬─────────────┬─────┘               │                │
         │             │ 4. one message per thread at a time  │
         │             ▼                     │                │
         │   ┌──────────────────────────┐    │                │
         │   │ Lambda                   │────┘                │
         │   │ AnswerSlackMessage       │─────────────────────┘
         │   └────────────┬─────────────┘
         │                │ 7. InvokeAgentRuntime (IAM)
         │                ▼    session = the Slack thread
         │   ┌──────────────────────────┐
         │   │ AgentCore Runtime        │
         │   │ the agent, its memory    │
         │   └──────────────────────────┘
         │
         │ only if the worker did not finish (after 300 s)
         ▼
  ┌──────────────────────────┐     ┌──────────────────────────┐
  │ SQS FIFO: held-back      │────▶│ Lambda                   │────▶ Slack Web API
  │ queue, keeps 60 min      │     │ CleanUpSlackMessage      │
  └──────────────────────────┘     └──────────────────────────┘
```

| Part | What it does |
| --- | --- |
| `ReceiveSlackEvent`, the front door | Accepts a request only when Slack's signature proves Slack sent it within the last five minutes. Answers Slack's check of the address. Queues a mention, a direct message, or a reply in a channel thread. Ignores everything else, and anything more than four minutes old. |
| The work queue | Holds a message, with its text, until the worker takes it. One group per Slack thread keeps a thread's messages in order. |
| `AnswerSlackMessage`, the worker | Checks the thread is one STRIDEr was mentioned in, and that the writer is a full member. Adds the eyes, asks the agent, posts the reply, removes the eyes. |
| The held-back queue | Receives a message the worker did not finish, because it crashed or ran out of time. |
| `CleanUpSlackMessage` | Triggered by the held-back queue. Posts the apology if the person is still waiting, and removes the eyes. |

There is no database. Whether a thread is STRIDEr's, and whether STRIDEr has answered in
it, are read from Slack each time. The agent session for a thread is worked out from the
thread: `slack-<team>-<channel>-<thread timestamp>`.

The receiving service exists only in the stack deployed from `main`. A branch stack has
the agent and none of this.

### What the agent is sent

The text of the message with the mention of STRIDEr removed. The first time STRIDEr
answers in a thread that already has messages, those messages go first, oldest first, each
with who wrote it. If they do not fit in `MaxPromptChars`, the oldest are left out and the
agent is told.

The person's Slack ID is sent as `slackUserId`, which the agent ignores today. It is not
sent as `actorId`: the agent keeps memory by session and by actor, so that would give each
person in a thread a conversation of their own.

### What STRIDEr says when it cannot answer

These five sentences are in `src/common/common/slack/text.py`. The agent does not write
them.

| When | What is posted |
| --- | --- |
| The agent failed twice, or the worker stopped part-way | Sorry, I couldn't answer that. Please try again later. |
| The message is longer than `MaxPromptChars` | That message is too long for me to read. Please shorten it and try again. |
| A mention or a direct message with no text | What would you like help with? |
| The thread is more than `MemoryEventExpiryDays` old | I no longer remember this conversation. Please send me a new message outside this thread to start again. |
| Only part of a long reply could be posted | I couldn't post my whole reply. Please ask again. |

A reply over 11,000 characters is posted in parts, each ending `(part 1 of 3)`.

## Privacy

- **What people write is never logged.** No function logs its event, a queued message, a
  prompt or a reply. API Gateway's execution logging is off; only its access log is kept.
  Do not turn on Powertools' `log_event`, and do not add `LOGGER.debug` of an event.
- **Text waits in a queue for at most an hour.** A queued message carries its text. Both
  queues are encrypted and delete a message after 60 minutes. In practice a message is
  answered in seconds.
- **Replies in threads STRIDEr is not part of are looked at and dropped.** The front door
  cannot tell whose thread a reply is in, so the worker reads the thread to find out.
- **Slack IDs are logged.** People, channels and threads are identified in the logs by
  their Slack IDs.
- **Logs are kept 30 days**, and the access log 7.

## First-time setup

Do these in order. Steps 1, 3, 4 and 5 are done by hand.

1. **Put the two secrets in Parameter Store**, in the deployment account and region. Each
   command prompts for the value, which keeps it out of your shell history. The signing
   secret is on the app's **Basic Information** page in Slack; the bot token is on **OAuth &
   Permissions**. Both are also the GitHub secrets `SLACK_SIGNING_SECRET` and
   `SLACK_BOT_TOKEN`, but GitHub will not show you those.

   ```bash
   read -rs VALUE && aws ssm put-parameter --type SecureString \
     --name /engineering-agents/slack/signing-secret --value "$VALUE"; unset VALUE
   read -rs VALUE && aws ssm put-parameter --type SecureString \
     --name /engineering-agents/slack/bot-token --value "$VALUE"; unset VALUE
   ```

2. **Merge to `main`.** The **Main** workflow deploys the receiving service; check the
   stack has the output `SlackEventsUrl`. The **Slack app** workflow sends the new
   permissions, the events and the address to Slack, and then **fails saying the app must
   be installed again**. That is expected: a new permission only takes effect when the app
   is installed again.

3. **Verify the address in Slack.** In the app's settings open **App Manifest** and follow
   the prompt to verify the request URL. This is the first real request through the front
   door, so it also proves the signature check works.

4. **Install the app again.** In the app's settings, **Install App**, then **Reinstall to
   Workspace**. Compare the bot token on **OAuth & Permissions** with the one you stored.
   If it has changed, store the new one in Parameter Store with the command above and
   `--overwrite`, and in the GitHub secret `SLACK_BOT_TOKEN`.

5. **Run the Slack app workflow by hand** with the action `apply`. It passes.

6. **Add STRIDEr to a channel and mention it.**

Until step 4 nobody is answered: the app cannot look people up without its new
permission, and STRIDEr answers only people it knows are full members.

## Replacing a secret

Store the new value under the same name:

```bash
read -rs VALUE && aws ssm put-parameter --overwrite --type SecureString \
  --name /engineering-agents/slack/bot-token --value "$VALUE"; unset VALUE
```

The functions read a secret again every five minutes, so the new value is in use within
five minutes with no deployment. The same values are GitHub secrets for the Slack app
workflow; change them there too.

## Finding a failure

Every message the worker handles gets one log record in the log group
`/aws/lambda/<stack name>-AnswerSlackMessage`, with `outcome` and `reason`. The stack name
is in the output of the **Main** workflow's `deploy` job.

| `outcome` | `reason` | What happened |
| --- | --- | --- |
| `answered` | | The reply was posted. |
| `declined` | `not_strider_thread` | A reply in a thread where STRIDEr was never mentioned. |
| `declined` | `not_member` | The writer is not a full member. |
| `declined` | `thread_expired` | The thread is older than the agent's memory. |
| `declined` | `too_long`, `nothing_asked` | A fixed sentence was posted. |
| `failed` | `agent_failed` | The agent failed twice. The apology was posted. |
| `failed` | `reply_not_posted` | Slack would not take the reply, or part of it. |
| `failed` | `thread_unreadable`, `membership_unknown`, `identity_unknown` | Slack could not be asked. |
| `unfinished` | | The worker hit an error it did not expect. The cleanup function takes over. |

To find failures in CloudWatch Logs Insights:

```text
fields @timestamp, outcome, reason, channel, ts, correlationId, agentRequestId
| filter outcome in ["failed", "unfinished"]
| sort @timestamp desc
```

To follow one message through all three logs:

- `correlationId` is the same in the front door's record and the worker's.
- `agentRequestId` in the worker's record is `requestId` in the agent's record.

To open the message in Slack, use `channel` and `ts` from the record:
`https://serverlessops.slack.com/archives/<channel>/p<ts without the dot>`.

A worker that crashed or timed out writes no record of its own for that message. The
cleanup function's record in `/aws/lambda/<stack name>-CleanUpSlackMessage` shows
what it did: `apologised`, `already_answered`, `reply_incomplete` or `not_started`. The
person's apology comes five to six minutes after the crash, because that is how long the
message takes to reach the held-back queue. Later messages in the same thread wait until
then.

The held-back queue is not somewhere to look for failed messages. The cleanup function
empties it.

## When Slack stops sending events

Slack sends an event up to three more times over five minutes when it gets no answer, and
then gives up; that message is never answered. Slack turns event delivery off for an app
whose deliveries mostly fail for an hour, but only for apps that receive more than 1,000
events an hour, which this one does not.

If it ever happens, Slack emails the app's owner. Turn delivery on again in the app's
settings under **Event Subscriptions**.

## Disconnecting STRIDEr from Slack

To stop STRIDEr answering without removing anything:

1. Set `event_request_url` to `""` in `slack/settings.json`.
2. Merge to `main`. The Slack app workflow sends the app definition without its events,
   and Slack stops sending them.

To connect it again, put the address back and merge, then verify the address in Slack
again as in step 3 of the first-time setup. The address does not change when the stack is
rebuilt: it is `https://engineering-agents.sandbox.serverlessops.io/slack/events`.

## Limits

| Limit | Value | Where |
| --- | --- | --- |
| Requests the address accepts | 5 a second, bursts of 10 | `MethodSettings` in `template.yaml` |
| Front door timeout | 3 seconds, the same as Slack's patience | `Globals` in `template.yaml` |
| One try at the agent | 100 seconds | `src/common/common/agentcore.py` |
| Tries at the agent | 2 | `src/handlers/AnswerSlackMessage/function.py` |
| Messages answered at once | 5 | `ScalingConfig` in `template.yaml` |
| A person's membership is remembered | 1 hour | `src/common/common/slack/api.py` |
| A message waits in a queue | 60 minutes | `MessageRetentionPeriod` in `template.yaml` |
| A message is ignored when older than | 4 minutes | `src/handlers/ReceiveSlackEvent/function.py` |
