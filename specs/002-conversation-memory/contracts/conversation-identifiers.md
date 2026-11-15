# Conversation Identifiers Contract

**Backfill**: Read from `src/agent/main.py`, `scripts/invoke.py` and
`docs/handbook/07-common-tasks.md` at commit `fd37671`.

## Scope

How a caller continues, separates and starts conversations. The request and reply bodies are
defined in feature 001's `contracts/invoke-interface.md`.

## Identifiers

| Identifier | Where it is sent | Required | Rules |
|---|---|---|---|
| Conversation | `runtimeSessionId` parameter of `InvokeAgentRuntime` | Yes | 33 to 256 characters. |
| Asker | `actorId` in the request body | No | A non-empty string. Anything else is treated as `default`. |

## Behavioral Contract

1. Two requests continue one conversation only when both identifiers match and both go to the
   same deployment.
2. To start a new conversation, the caller sends a `runtimeSessionId` it has not used before.
3. To keep askers apart, the caller sends a different `actorId` for each asker.
4. A caller that never sends `actorId` shares the `default` asker with every other caller that
   does the same. Such callers MUST use session identifiers that others cannot guess or reuse.
5. A request refused with `input_rejection` is not added to the conversation.
6. Messages are removed `MemoryEventExpiryDays` days after they were stored (7 by default).
   The caller is not told when a conversation has lost messages.

## Caller Responsibilities

- The agent does not check that a caller owns a conversation. A caller acting for end users
  MUST map each end user to identifiers that another end user cannot supply.
- The caller MUST NOT put secrets in a prompt. Prompts and replies are stored for the
  retention period.

## Security Contract

- Only the stack's execution role is granted access to the stack's memory by this repository.
- Stored messages are protected at rest by the service's default settings. This repository
  sets none of its own.
- Reading a conversation's content directly from the store is possible for any principal the
  account grants the memory's read actions to. No procedure for doing so is documented.
