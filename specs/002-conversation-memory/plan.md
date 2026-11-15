# Implementation Plan: Conversation Memory

**Branch**: `plan/002-conversation-memory` | **Date**: 2026-11-15 | **Spec**: `specs/002-conversation-memory/spec.md`

**Input**: Feature specification from `specs/002-conversation-memory/spec.md`

**Backfill**: This plan was written after the feature was built. It records the design that is
in the code on `main` (commit `fd37671`), not a design made in advance.

## Summary

Each deployment has one Amazon Bedrock AgentCore Memory resource, configured for short-term
memory only. For every request that passes the input checks, `build_agent` in
`src/agent/main.py` gives the Strands agent an `AgentCoreMemorySessionManager` keyed by the
memory's ID, the caller's `runtimeSessionId` and the `actorId` from the request body. The
session manager loads the conversation's earlier messages before the model is called and
saves the new exchange afterwards. Messages expire after `MemoryEventExpiryDays`.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: `bedrock-agentcore` 1.26.0
(`bedrock_agentcore.memory.integrations.strands`: `AgentCoreMemoryConfig`,
`AgentCoreMemorySessionManager`), `strands-agents` 1.65.0

**Storage**: One `AWS::BedrockAgentCore::Memory` per stack, with `EventExpiryDuration` set from
the `MemoryEventExpiryDays` parameter and no long-term strategies.

**Testing**: None for this feature. The unit tests replace `main.build_agent`, which is the
only place memory is used.

**Target Platform**: Amazon Bedrock AgentCore Runtime and AgentCore Memory.

**Project Type**: Single service (one agent container) with its infrastructure in a SAM
template.

**Performance Goals**: None set.

**Constraints**:

- `runtimeSessionId` is 33 to 256 characters, enforced by the service.
- Memory names allow only letters, digits and underscores, with a 48 character limit. The name
  is `<Component>_<CodeBranch>` with hyphens turned into underscores. Changing it replaces the
  memory.
- `MemoryEventExpiryDays` is limited to 3 to 365.
- Memory is used only when both `MEMORY_ID` and a session ID are present. A local run has no
  `MEMORY_ID`, so it has no memory.

**Scale/Scope**: Conversations of a few turns. One memory per deployed branch.

## Constitution Check

Not performed. `.specify/memory/constitution.md` is still the unfilled Spec Kit template, so
there are no principles to check this plan against. This is an open item for the project
owner.

## Project Structure

### Documentation (this feature)

```text
specs/002-conversation-memory/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── conversation-identifiers.md
├── checklists/
│   ├── requirements.md
│   └── memory.md
├── catalog-info.yaml
└── tasks.md
```

### Source Code (repository root)

```text
src/agent/main.py      # MEMORY_ID, DEFAULT_ACTOR_ID, build_agent, actorId handling in invoke
scripts/invoke.py      # --session-id and --actor-id options
template.yaml          # AgentMemory, MemoryEventExpiryDays, the role's Memory statement,
                       # MEMORY_ID environment variable, AgentMemoryId output
docs/handbook/         # 01-features, 03-configuration, 04-architecture, 07-common-tasks
```

**Structure Decision**: Memory adds no module of its own. It is a few lines in `build_agent`
and one resource in the template.

## Complexity Tracking

Nothing recorded. With no constitution in force there are no violations to justify.
