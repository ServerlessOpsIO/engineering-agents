# Phase 0 Research: Observability

**Backfill**: These decisions were read from the code, its comments and the project handbook on
2026-11-15. No research was recorded when the feature was built. Where a rationale is written
down in the repository it is cited. Where it is not, this file says "not recorded" and does
not guess. No alternatives were recorded for any decision, so none are listed.

## Decision 1: One JSON record per request

- **Decision**: `invoke` builds a dictionary as the request proceeds and `_log_request` writes
  it once, as one JSON line, whatever the outcome.
- **Rationale**: Docstring of `_log_request`: "Write the one log record for a request."

## Decision 2: Never log prompt or reply text

- **Decision**: The record holds the prompt's length (`promptChars`) and nothing of its
  content. The reply is not recorded at all.
- **Rationale**: Handbook, `06-observability.md`: "whatever reaches a log group may be
  forwarded to other systems." A unit test,
  `test_the_request_record_holds_no_prompt_or_reply_text`, guards it.

## Decision 3: Use the runtime's request ID as the correlation identifier

- **Decision**: `requestId` comes from `BedrockAgentCoreContext.get_request_id()` and is put in
  both the record and the reply.
- **Rationale**: Not recorded. The handbook describes the use: "Take the `requestId` from a
  reply and search the log group for it."

## Decision 4: A dedicated logger that writes bare JSON

- **Decision**: The `agent` logger has its own stream handler with the format `%(message)s`
  and does not propagate, so each record is a line of JSON with nothing around it.
- **Rationale**: Not recorded.

## Decision 5: Failure detail goes in a second log entry

- **Decision**: On an exception the record gets `kind: error` and `errorType` (the exception's
  class name). The stack trace is written by a separate `logger.exception` call that names
  the request ID.
- **Rationale**: Handbook: "Exception class name, for `error` only. A stack trace follows in a
  separate log line."

## Decision 6: Record token usage from the model's own figures

- **Decision**: `_token_usage` reads `inputTokens` and `outputTokens` from the agent result's
  accumulated usage, and records `None` when they are missing.
- **Rationale**: Not recorded.

## Decision 7: Trace with the AWS OpenTelemetry distribution

- **Decision**: The image's command is `opentelemetry-instrument python main.py`. Strands
  emits the spans; the distribution exports them.
- **Rationale**: Dockerfile comment: "opentelemetry-instrument sends the agent's traces to
  AgentCore observability."

## Decision 8: Rely on the platform's metrics

- **Decision**: The agent publishes no metrics of its own.
- **Rationale**: Handbook: "AgentCore Runtime publishes invocation, error, throttle and latency
  metrics for the runtime to Amazon CloudWatch."

## Decision 9: No dashboards or alerts

- **Decision**: None are created.
- **Rationale**: Handbook, `01-features.md`, lists "dashboards or alerts" under "Not included",
  as "left for the project to add when it needs them".

## Open questions found during backfill

- **Does prompt or reply text reach traces?** The Strands tracing code
  (`strands/telemetry/tracer.py` in version 1.65.0) adds message content to span events. Whether
  that content is exported and stored in this deployment has not been checked. If it is, the
  handbook's statement that text is kept out of the logs does not extend to traces.
- **Can the stack trace entry contain prompt text?** It is written from whatever the exception
  holds. An error passed back from the model service could quote the input.
- **Is Transaction Search enabled in the deployment account?** No record was found.
- **Do the logs, metrics and traces reach Datadog?** The Bill-GN specification says the
  environment forwards every log group and most metric namespaces. That was not checked for
  this agent.
- **The caller is not in the record.** `actorId` is read by `invoke` but not written to the
  record.
