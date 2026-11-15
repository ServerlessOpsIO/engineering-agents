# Phase 0 Research: Conversation Memory

**Backfill**: These decisions were read from the code, its comments and the project handbook on
2026-11-15. No research was recorded when the feature was built. Where a rationale is written
down in the repository it is cited. Where it is not, this file says "not recorded" and does
not guess. No alternatives were recorded for any decision, so none are listed.

## Decision 1: AgentCore Memory through the Strands session manager

- **Decision**: Store conversations in Amazon Bedrock AgentCore Memory and connect it to the
  agent with `AgentCoreMemorySessionManager` from the `bedrock-agentcore` package.
- **Rationale**: Not recorded. The project template offers conversation memory as an option on
  its creation form, and this is what the option generates.

## Decision 2: Short-term memory only

- **Decision**: The memory resource has an event expiry and no long-term strategies.
- **Rationale**: Template comment: "Short-term conversation memory: the events of each session
  are kept for MemoryEventExpiryDays. No long-term strategies are configured."

## Decision 3: The caller supplies both identifiers

- **Decision**: The conversation is the `runtimeSessionId` of the call. The asker is `actorId`
  in the request body, or `default` when it is absent, empty or not a string.
- **Rationale**: Not recorded. The handbook describes the effect: "Requests that share a
  `runtimeSessionId` and `actorId` continue one conversation."

## Decision 4: One memory per stack

- **Decision**: `AgentMemory` is defined in the same template as the runtime, so every branch
  deployment has its own memory, named after the component and branch.
- **Rationale**: Handbook, `05-ci-cd.md`: "A branch deployment creates a separate runtime and
  memory named after the branch."

## Decision 5: Retention is a deployment parameter

- **Decision**: `MemoryEventExpiryDays`, default 7, allowed range 3 to 365.
- **Rationale**: Not recorded for the default of 7. The range was not checked against the
  service's own limits during the backfill.

## Decision 6: Memory is skipped when it is not configured

- **Decision**: `build_agent` creates a session manager only when `MEMORY_ID` is set and the
  request has a session ID. Otherwise the agent starts empty.
- **Rationale**: Docstring: "With MEMORY_ID set, the session's earlier messages are loaded from
  AgentCore Memory and this exchange is saved to it. Without it, the agent starts empty." This
  is what lets the agent run locally.

## Decision 7: The role's memory permissions are limited to this memory

- **Decision**: The execution role may call `CreateEvent`, `GetEvent`, `ListEvents`,
  `DeleteEvent` and `ListSessions` on this stack's memory ARN only.
- **Rationale**: Not recorded. It follows the template's stated approach of narrowing the
  role "to this agent's log groups, model and image repository".

## Open questions found during backfill

- What happens when memory cannot be read or saved has not been tested. From the code, the
  session manager is created and used inside the `try` block of `invoke`, so a failure should
  produce the generic error reply.
- Whether the session manager limits how much of a long conversation it loads was not checked.
- Why `DeleteEvent` is granted is not recorded. Nothing in the agent's own code deletes events.
- The expiry applies to each message from when it was stored, not to the conversation from its
  last message. Whether this was intended is not recorded.
