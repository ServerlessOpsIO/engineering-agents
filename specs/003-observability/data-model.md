# Phase 1 Data Model: Observability

**Backfill**: Read from `src/agent/main.py`, `template.yaml` and
`docs/handbook/06-observability.md` at commit `fd37671`.

## Entity: RequestRecord

One JSON log line per request that reaches the agent's handler.

| Field | Type | Present | Notes |
|---|---|---|---|
| `requestId` | string | Always | Correlation identifier. Also returned to the caller. |
| `sessionId` | string or null | Always | The caller's `runtimeSessionId`. |
| `promptChars` | integer | Always | Length of the trimmed prompt. `0` for a missing or non-text prompt. |
| `kind` | enum(`answer`, `input_rejection`, `error`) | Always | The outcome. |
| `durationMs` | integer | Always | Time inside the handler, in milliseconds. |
| `modelId` | string | `answer` and `error` | Absent for `input_rejection`, because the model was not reached. |
| `inputTokens` | integer or null | `answer` | `null` when the model reports no usage. |
| `outputTokens` | integer or null | `answer` | `null` when the model reports no usage. |
| `errorType` | string | `error` | Class name of the exception. |

### Validation Rules

- Exactly one record is written per handled request.
- No field holds prompt text or reply text.
- `actorId` is not recorded.

## Entity: FailureDetail

A second log entry written only for `error`. It is not JSON: it is the line
`Request <requestId> failed` followed by the exception's stack trace. Its content is not
controlled by the agent.

## Entity: Trace

Produced by the OpenTelemetry instrumentation, not by the agent's own code. The agent sets no
span names or attributes. What a trace contains was not inspected.

## Entity: PlatformMetric

Published by AgentCore Runtime to CloudWatch for each runtime: invocations, errors, throttles
and latency. The agent publishes none.

## Entity: Tags

Set on the stack's resources, and used to select one deployment's data.

| Tag | Source |
|---|---|
| `org:domain`, `org:system`, `org:component` | `cfn-tags.json` |
| `org:repo`, `org:branch`, `org:stackName` | Added by the deploy action |

## Relationships

- One request produces exactly one RequestRecord, at most one FailureDetail, and, when tracing
  is delivered, one Trace.
- A RequestRecord and the reply for the same request share `requestId`.
- A RequestRecord and a Conversation (feature 002) share `sessionId`.
- Requests the service rejects before the handler (no permission, malformed body) produce none
  of these.

## Where Each Lives

| Data | Location |
|---|---|
| RequestRecord, FailureDetail | CloudWatch log group `/aws/bedrock-agentcore/runtimes/<AgentRuntimeId>-DEFAULT` |
| Trace | AWS X-Ray, when CloudWatch Transaction Search is enabled |
| PlatformMetric | CloudWatch metrics |
