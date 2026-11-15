# Invoke Interface Contract

**Backfill**: Read from `src/agent/main.py`, `scripts/invoke.py` and
`docs/handbook/04-architecture.md` at commit `fd37671`.

## Scope

How a caller sends the agent a prompt and what it gets back. Feature 002 adds meaning to
`runtimeSessionId` and `actorId`; this contract defines their shape.

## Operation

- **Operation**: `InvokeAgentRuntime` in the `bedrock-agentcore` service.
- **Target**: the stack's `AgentRuntimeArn` output.
- **Authorization**: IAM (SigV4). The caller needs `bedrock-agentcore:InvokeAgentRuntime` on
  that ARN.
- **Content type**: `application/json` for the request and the reply.
- **`runtimeSessionId`**: required by the service, 33 to 256 characters.

## Request body

MUST validate against `invocation-request.schema.json`.

```json
{ "prompt": "What can you do?", "actorId": "someone" }
```

## Reply body

MUST validate against `invocation-reply.schema.json`. One JSON document, not a stream.

```json
{ "kind": "answer", "text": "...", "requestId": "0f6c1a52-..." }
```

## Outcomes

| Situation | HTTP | `kind` | Produced by |
|---|---|---|---|
| The agent replied | 200 | `answer` | The agent |
| Empty, missing, non-text or over-length prompt | 200 | `input_rejection` | The agent |
| The agent could not reply | 500 | `error` | The agent |
| Body is not valid JSON | 400 | none | The runtime SDK, before the agent's handler |
| Caller lacks permission | 403 | none | The service (`AccessDeniedException`) |

## Behavioral Contract

1. The prompt is trimmed before it is checked and before it is sent to the model.
2. An `input_rejection` never causes a model call.
3. An `error` reply never contains the failure's detail.
4. `requestId` in a reply matches the `requestId` of that request's log record.
5. Callers MUST branch on `kind`, not on the wording of `text`. The fixed texts may change.

## Security Contract

- There is no unauthenticated way to reach the agent.
- Access is granted per caller, by IAM policy on the runtime ARN. Nothing in this repository
  grants access to any caller; each grant is made on the caller's own role.
- Secrets MUST NOT be put in the request body. Nothing in the agent needs one.
