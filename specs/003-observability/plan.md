# Implementation Plan: Observability

**Branch**: `plan/003-observability` | **Date**: 2026-11-15 | **Spec**: `specs/003-observability/spec.md`

**Input**: Feature specification from `specs/003-observability/spec.md`

**Backfill**: This plan was written after the feature was built. It records the design that is
in the code on `main` (commit `fd37671`), not a design made in advance.

## Summary

The agent writes one JSON log line per request to standard output, which AgentCore Runtime
delivers to a CloudWatch log group. The line holds the request ID, session ID, outcome,
duration, prompt length and, where they apply, the model ID, token counts and exception type.
It never holds prompt or reply text. The container starts the agent under
`opentelemetry-instrument` from the AWS OpenTelemetry distribution, so the spans Strands emits
for model calls are exported as traces to AWS X-Ray, once CloudWatch Transaction Search is
enabled in the account. Request counts, errors, throttles and latency come from the metrics
AgentCore Runtime publishes itself. No dashboards or alerts are created.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Python `logging` and `json` (standard library),
`aws-opentelemetry-distro` 0.22.0, `strands-agents` 1.65.0 (emits the spans),
`bedrock-agentcore` 1.26.0 (supplies the request ID)

**Storage**: CloudWatch Logs, log group `/aws/bedrock-agentcore/runtimes/<runtime-id>-DEFAULT`.
AWS X-Ray for traces. CloudWatch metrics in the `bedrock-agentcore` namespace. Retention is
not set by this project.

**Testing**: `pytest` 9.2.0. The tests attach a handler to the `agent` logger, collect the
JSON records and assert on their fields.

**Target Platform**: Amazon Bedrock AgentCore Runtime, Amazon CloudWatch, AWS X-Ray.

**Project Type**: Single service (one agent container) with its infrastructure in a SAM
template.

**Performance Goals**: None set.

**Constraints**:

- Prompt and reply text must not be written to the request record.
- Traces are delivered only when CloudWatch Transaction Search is enabled in the deployment
  account and region. This is an account setting, so it is a documented prerequisite and not
  in the template.
- The X-Ray actions, `cloudwatch:PutMetricData` and `ecr:GetAuthorizationToken` do not support
  resource-level permissions, so the role uses `*` for them. `PutMetricData` is limited to the
  `bedrock-agentcore` namespace by a condition.

**Scale/Scope**: One log record per request, tens of requests per day.

## Constitution Check

Not performed. `.specify/memory/constitution.md` is still the unfilled Spec Kit template, so
there are no principles to check this plan against. This is an open item for the project
owner.

## Project Structure

### Documentation (this feature)

```text
specs/003-observability/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── request-record.md
│   └── request-record.schema.json
├── checklists/
│   ├── requirements.md
│   └── observability.md
├── catalog-info.yaml
└── tasks.md
```

### Source Code (repository root)

```text
src/agent/main.py              # logger setup, _token_usage, _log_request, the record in invoke
src/agent/Dockerfile           # CMD runs the agent under opentelemetry-instrument
Pipfile                        # aws-opentelemetry-distro
template.yaml                  # LogLevel parameter; the role's Logs, LogGroupDiscovery,
                               # LogEvents, Tracing and Metrics statements
cfn-tags.json                  # org:domain, org:system, org:component
tests/unit/test_main.py        # the records fixture and the assertions on records
docs/handbook/06-observability.md
docs/handbook/03-configuration.md   # the Transaction Search prerequisite
```

**Structure Decision**: Observability adds no module of its own. The record is built inside
`invoke`, and tracing is turned on by how the container starts.

## Complexity Tracking

Nothing recorded. With no constitution in force there are no violations to justify.
