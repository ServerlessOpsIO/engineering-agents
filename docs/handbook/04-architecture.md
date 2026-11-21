# Architecture

## AWS resources

| Resource | Type | Purpose |
| --- | --- | --- |
| `AgentRuntime` | `AWS::BedrockAgentCore::Runtime` | Runs the agent's container image. HTTP protocol, public network mode, IAM authorization. |
| `AgentExecutionRole` | `AWS::IAM::Role` | What the agent may do: write its logs, traces and metrics, pull its image and invoke its model. |
| `AgentMemory` | `AWS::BedrockAgentCore::Memory` | Keeps each session's messages so the agent can continue a conversation. |

The stack deployed from `main` also has the Slack receiving service. A branch stack does not.

| Resource | Type | Purpose |
| --- | --- | --- |
| `RestApi` | `AWS::Serverless::Api` | The public address Slack sends events to, defined in `openapi.yaml`. Throttled; access log only. |
| `SiteCertificate` | `AWS::CertificateManager::Certificate` | Certificate for the hostname, validated through the hosted zone. |
| `SlackSigningSecretStore`, `SlackBotTokenStore` | `AWS::SecretsManager::Secret` | The two Slack secrets, filled at deployment from GitHub secrets. Each is readable only by the functions that use it. |
| `ReceiveSlackEventFunction` | `AWS::Serverless::Function` | Checks Slack's signature, answers Slack, queues the message. |
| `SlackMessageQueue` | `AWS::SQS::Queue` (FIFO) | Messages waiting to be answered, one group per Slack thread. |
| `AnswerSlackMessageFunction` | `AWS::Serverless::Function` | Asks the agent and posts the reply in the thread. |
| `SlackHeldBackQueue` | `AWS::SQS::Queue` (FIFO) | Messages the worker did not finish. |
| `CleanUpSlackMessageFunction` | `AWS::Serverless::Function` | Posts the apology if one is owed and removes the eyes reaction. |
| Three log groups | `AWS::Logs::LogGroup` | One per function, kept 30 days. The API's access log is kept 7. |

How a message travels through these is in [STRIDEr Slack messaging](09-slack-messaging.md).

The image repository is not in the template. The workflows create it in the CI/CD account as
`<owner>/<repository>` and apply `.github/workflows/ecr-policy.json`, which lets principals in
the AWS organization pull from it.

Sessions end after 5 idle minutes and live for at most 30 (`LifecycleConfiguration`). Raise
both for agents that run long tasks.

## Repository layout

```text
src/agent/            # The code that ships in the image
├── main.py           # Entry point: input checks, logging, errors; runs one message
├── prompt.py         # Builds what the model is told, before every call to it
├── persona.md        # Who the agent is, and the rules that always hold
├── loader.py         # Reads and checks the skills when the agent starts
├── skills/           # One folder for each skill, in the Agent Skills format
├── session/          # The session record, its tools, and the documents made from it
├── github.py         # The tools that read a repository
└── Dockerfile        # arm64 image, non-root user, port 8080
src/handlers/         # The Lambda functions of the Slack receiving service
├── ReceiveSlackEvent/    # function.py and the requirements.txt packaged with it
├── AnswerSlackMessage/
└── CleanUpSlackMessage/
src/common/           # Code the three functions share, packaged with each
data/handlers/        # Sample events and schemas for the functions' tests
openapi.yaml          # The one route of the public address
Pipfile               # Dependencies: the agent's in [packages]; test tools and what the
                      # functions import in [dev-packages]
Pipfile.lock          # Exact versions that CI and the image install
.dockerignore         # Limits the Docker build context to the Pipfile and src/agent/
tests/unit/           # Unit tests; never packaged
data/sessions/        # The fixed threat modelling session
scripts/invoke.py     # Ask a deployed agent one question
scripts/play_session.py  # Play the fixed session against a deployed agent and check it
template.yaml         # Runtime, execution role, memory; the Slack receiving service
cfn-parameters.json   # Deployment parameters
cfn-tags.json         # Resource tags
.github/workflows/    # Branch and main workflows, image repository policy
```

## Request flow

1. A caller invokes the runtime with IAM credentials. Callers without
   `bedrock-agentcore:InvokeAgentRuntime` on the runtime are rejected by the service before the
   agent runs.
2. `main.py` reads the request ID and session ID, trims the prompt and applies the empty and
   length checks. A failed check returns an `input_rejection` without calling the model.
3. It builds an agent whose session manager loads the session's earlier messages and the
   agent's state from AgentCore Memory. Tool calls and their results are left out of what
   is loaded.
4. Before every call to the model it builds what the model is told and chooses which
   tools it is offered, from the session record as it stands. The model may call tools,
   which change the record, and is then called again.
5. It saves the exchange and the state, writes one log record and returns the reply, with
   any documents the tools attached.
6. Any failure returns HTTP 500 with a generic message. Details go to the log.

## Invoke interface

Operation: `InvokeAgentRuntime`, signed with IAM (SigV4), on the stack's `AgentRuntimeArn`
output. `runtimeSessionId` must be 33 to 256 characters.

Request body:

```json
{
  "prompt": "we terminate TLS at the gateway",
  "speakerName": "Ana Souza",
  "conversationType": "channel_thread",
  "addressed": false,
  "messageId": "C0123ABCD:1795123201.951000",
  "threadEndsAt": "2026-11-26T14:00:01Z"
}
```

Only `prompt` is required.

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `prompt` | string | yes | Trimmed. Must not be empty. At most `MaxPromptChars` characters. |
| `actorId` | string | no | Who is asking. Separates conversations in memory; `default` when absent. |
| `speakerName` | string | no | The name of whoever wrote the message. Cleaned before the model sees it; `Someone` when absent. Never logged. |
| `conversationType` | string | no | `channel_thread` or `direct_message`. Anything else, or absent, is a direct message, so the agent always replies. |
| `addressed` | boolean | no | Whether the message mentions the agent. Absent means it does. |
| `messageId` | string | no | Identifies the message. A second request with the same value is a retry, and what the first led the agent to record is undone first. |
| `threadEndsAt` | string | no | For a channel thread: when the thread stops being answered, UTC. |

Response body:

```json
{
  "kind": "answer",
  "text": "...",
  "documents": [{ "filename": "threat-model-shop.md", "title": "Threat model: Shop", "markdown": "..." }],
  "requestId": "0f6c1a52-..."
}
```

`documents` is present only when the agent attached some: the written threat model, and
the facilitator's notes.

| Situation | HTTP | `kind` |
| --- | --- | --- |
| The agent replied | 200 | `answer` |
| The agent judged that the message needed nothing from it. `text` is empty. Only in a channel thread, during a session, for a message that does not mention it. | 200 | `no_reply` |
| Empty, missing or over-length prompt | 200 | `input_rejection` |
| The agent could not reply | 500 | `error` |
| Body is not valid JSON | 400 | n/a, returned by the runtime SDK |
| Caller lacks permission | 403 | n/a, `AccessDeniedException` from the service |

The reply is one JSON document, not a stream.
