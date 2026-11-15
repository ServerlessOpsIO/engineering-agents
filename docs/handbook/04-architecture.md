# Architecture

## AWS resources

| Resource | Type | Purpose |
| --- | --- | --- |
| `AgentRuntime` | `AWS::BedrockAgentCore::Runtime` | Runs the agent's container image. HTTP protocol, public network mode, IAM authorization. |
| `AgentExecutionRole` | `AWS::IAM::Role` | What the agent may do: write its logs, traces and metrics, pull its image and invoke its model. |
| `AgentMemory` | `AWS::BedrockAgentCore::Memory` | Keeps each session's messages so the agent can continue a conversation. |

The image repository is not in the template. The workflows create it in the CI/CD account as
`<owner>/<repository>` and apply `.github/workflows/ecr-policy.json`, which lets principals in
the AWS organization pull from it.

Sessions end after 5 idle minutes and live for at most 30 (`LifecycleConfiguration`). Raise
both for agents that run long tasks.

## Repository layout

```text
src/agent/            # The code that ships in the image
├── main.py           # Entry point: input checks, logging, errors
├── prompt.py         # Loads the system prompt
├── system_prompt.md  # The agent's instructions
└── Dockerfile        # arm64 image, non-root user, port 8080
Pipfile               # Dependencies: runtime in [packages], test tools in [dev-packages]
Pipfile.lock          # Exact versions that CI and the image install
.dockerignore         # Limits the Docker build context to the Pipfile and src/agent/
tests/unit/           # Unit tests; never packaged
scripts/invoke.py     # Ask a deployed agent one question
template.yaml         # Runtime, execution role, memory
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
3. It builds an agent whose session manager loads the session's earlier messages from
   AgentCore Memory, asks the model, and saves the exchange.
4. It writes one log record and returns the reply.
5. Any failure returns HTTP 500 with a generic message. Details go to the log.

## Invoke interface

Operation: `InvokeAgentRuntime`, signed with IAM (SigV4), on the stack's `AgentRuntimeArn`
output. `runtimeSessionId` must be 33 to 256 characters.

Request body:

```json
{ "prompt": "What can you do?" }
```

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `prompt` | string | yes | Trimmed. Must not be empty. At most `MaxPromptChars` characters. |
| `actorId` | string | no | Who is asking. Separates conversations in memory; `default` when absent. |

Response body:

```json
{ "kind": "answer", "text": "...", "requestId": "0f6c1a52-..." }
```

| Situation | HTTP | `kind` |
| --- | --- | --- |
| The agent replied | 200 | `answer` |
| Empty, missing or over-length prompt | 200 | `input_rejection` |
| The agent could not reply | 500 | `error` |
| Body is not valid JSON | 400 | n/a, returned by the runtime SDK |
| Caller lacks permission | 403 | n/a, `AccessDeniedException` from the service |

The reply is one JSON document, not a stream.
