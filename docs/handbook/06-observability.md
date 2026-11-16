# Observability

## Logs

The agent's logs are in the CloudWatch log group
`/aws/bedrock-agentcore/runtimes/<runtime-id>-DEFAULT`. The runtime ID is the stack's
`AgentRuntimeId` output.

The agent writes one JSON record per request:

| Field | Notes |
| --- | --- |
| `requestId` | Correlation identifier. Also returned to the caller. |
| `sessionId` | The caller's `runtimeSessionId`. |
| `kind` | `answer`, `input_rejection` or `error`. |
| `durationMs` | Time spent inside the agent. |
| `promptChars` | Length only. Prompt and reply text are never logged. |
| `modelId` | Absent for `input_rejection`. |
| `inputTokens`, `outputTokens` | When the model reports them. |
| `errorType` | Exception class name, for `error` only. A stack trace follows in a separate log line. |

Keep prompt and reply text out of the logs when you add fields: whatever reaches a log group
may be forwarded to other systems.

## Find a request

Take the `requestId` from a reply and search the log group for it. Expect one record with that
ID.

Calls rejected for lack of permission (403) never reach the agent, so they do not appear in
its logs. AWS CloudTrail records them if the account logs AgentCore data events.

## Tell a missing prerequisite apart

Two conditions outside this project stop the agent from answering, and both look the same in
the request record: `kind` is `error` and `errorType` is `AccessDeniedException`. The stack
trace entry that follows the record, starting `Request <requestId> failed`, tells them apart:

| Cause | Text in the entry | Fix |
| --- | --- | --- |
| The account has no access to the model | `is not available for this account` | Enable the model for the deployment account in Amazon Bedrock |
| A region the profile routes to is restricted | `with an explicit deny in a service control policy` | Allow Bedrock model invocation in `us-east-1`, `us-east-2` and `us-west-2` |

The caller sees the same generic error in both cases.

## Traces

The container runs the agent under `opentelemetry-instrument` from the AWS OpenTelemetry
distribution, and Strands emits spans for model calls and tool use. Traces are delivered to
AWS X-Ray once CloudWatch Transaction Search is enabled in the account and region (see
[deployment prerequisites](03-configuration.md#deployment-prerequisites)).

## Metrics

AgentCore Runtime publishes invocation, error, throttle and latency metrics for the runtime to
Amazon CloudWatch.

## Dashboards and alerts

None are created with this project. Build them from the log records and metrics above, and
select this agent's data with its tags: `org:component`, `org:branch` and `org:stackName`.
