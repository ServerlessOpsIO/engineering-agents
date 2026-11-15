# Implementation Plan: Agent Invocation

**Branch**: `plan/001-agent-invocation` | **Date**: 2026-11-15 | **Spec**: `specs/001-agent-invocation/spec.md`

**Input**: Feature specification from `specs/001-agent-invocation/spec.md`

**Backfill**: This plan was written after the feature was built. It records the design that is
in the code on `main` (commit `fd37671`), not a design made in advance.

## Summary

The agent is a small Python program built on the Strands Agents SDK and served by the
`BedrockAgentCoreApp` HTTP server from the `bedrock-agentcore` package. It runs as a container
on Amazon Bedrock AgentCore Runtime. One entry point, `invoke` in `src/agent/main.py`, trims
the prompt, applies the empty and length checks, builds an agent with the system prompt from
`src/agent/system_prompt.md`, calls the model on Amazon Bedrock, and returns a JSON reply with
a `kind`, the `text` and the `requestId`. Callers are authorized by IAM on the runtime.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: `strands-agents` 1.65.0, `bedrock-agentcore` 1.26.0, `starlette`
(installed by `bedrock-agentcore`; used for the HTTP 500 error response)

**Storage**: None in this feature. Conversation memory is feature 002.

**Testing**: `pytest` 9.2.0, run with `pipenv run test-unit`. The tests replace
`main.build_agent` with a fake, so they never call AWS.

**Target Platform**: Amazon Bedrock AgentCore Runtime. Linux arm64 container, HTTP protocol,
port 8080 (`POST /invocations`, `GET /ping`), `PUBLIC` network mode, IAM (SigV4) authorization
through `InvokeAgentRuntime`.

**Project Type**: Single service (one agent container) with its infrastructure in a SAM
template.

**Performance Goals**: None set. The specification has no timing criteria.

**Constraints**:

- Prompts are limited to `MaxPromptChars` characters after trimming (default 4,000).
- A runtime session ends after 300 idle seconds and lives for at most 1,800 seconds
  (`LifecycleConfiguration` in `template.yaml`).
- The reply is one JSON document, not a stream.
- The execution role may call only the model named by the `ModelId` parameter.

**Scale/Scope**: A small team and tens of prompts per day. One runtime per deployed branch.

## Constitution Check

Not performed. `.specify/memory/constitution.md` is still the unfilled Spec Kit template, so
there are no principles to check this plan against. This is an open item for the project
owner. The Bill-GN constitution, which this agent's design follows, was not applied here
because it has not been adopted for this repository.

## Project Structure

### Documentation (this feature)

```text
specs/001-agent-invocation/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── invoke-interface.md
│   ├── invocation-request.schema.json
│   └── invocation-reply.schema.json
├── checklists/
│   ├── requirements.md
│   └── invocation.md
├── catalog-info.yaml
└── tasks.md
```

### Source Code (repository root)

```text
src/agent/
├── main.py            # Entry point: input checks, agent call, reply kinds, errors
├── prompt.py          # Loads the system prompt once at start
└── system_prompt.md   # The agent's instructions
tests/unit/
├── test_main.py       # Answer, input rejection, length limit, error reply
└── test_prompt.py     # The system prompt is not empty
scripts/invoke.py      # Send one prompt to a deployed agent
template.yaml          # AgentRuntime, AgentExecutionRole, parameters, outputs
cfn-parameters.json    # Deployment parameter values
docs/handbook/         # 03-configuration, 04-architecture, 07-common-tasks
```

**Structure Decision**: One flat module directory, `src/agent/`, holds everything that ships in
the image. Tests live outside it in `tests/unit/` and reach it through `pythonpath = src/agent`
in `pytest.ini`.

## Complexity Tracking

Nothing recorded. With no constitution in force there are no violations to justify.
