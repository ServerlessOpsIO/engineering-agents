# Phase 1 Data Model: Conversation Memory

**Backfill**: Read from `src/agent/main.py` and `template.yaml` at commit `fd37671`. The agent
does not define a storage schema of its own. The stored form of a message is decided by the
`bedrock-agentcore` session manager and was not inspected.

## Entity: Memory

The store for one deployment. One `AWS::BedrockAgentCore::Memory` resource per stack.

| Attribute | Value | Notes |
|---|---|---|
| Name | `<Component>_<CodeBranch>`, hyphens as underscores | At most 48 characters. A change replaces the memory and everything in it. |
| Event expiry | `MemoryEventExpiryDays` (default 7, range 3 to 365) | Days each stored message is kept. |
| Long-term strategies | None | Nothing is extracted or summarized. |
| ID | Stack output `AgentMemoryId` | Passed to the agent as `MEMORY_ID`. |

## Entity: Conversation

Not stored as a record of its own. A conversation is every message stored under one
combination of these three values.

| Key part | Source | Notes |
|---|---|---|
| `memory_id` | `MEMORY_ID` environment variable | Fixed for a deployment. |
| `session_id` | `runtimeSessionId` of the call | 33 to 256 characters. Chosen by the caller. |
| `actor_id` | `actorId` in the request body | `default` when absent, empty or not a string. Chosen by the caller. |

## Entity: Message

One prompt or one reply, stored by the session manager as an event in the memory.

| Attribute | Notes |
|---|---|
| Conversation | The three key parts above. |
| Role and text | The prompt as sent to the model (trimmed), or the model's reply. |
| Stored at | Set by the service. The expiry counts from here. |

## Validation Rules

- A prompt refused by the input checks is never stored.
- Neither identifier is checked against the caller's identity.
- When `MEMORY_ID` is not set, or the request has no session ID, nothing is loaded or stored.

## Relationships

- One Memory holds many Conversations.
- One Conversation holds many Messages, in the order they were stored.
- A Conversation belongs to exactly one Memory, so two deployments never share one.

## State Transitions

1. No messages → `active`: the first accepted prompt in a conversation is answered and stored.
2. `active` → `active`: each further prompt loads the stored messages and adds two more.
3. `active` → `partly expired`: older messages pass the expiry and are removed, while newer
   ones remain.
4. `partly expired` or `active` → no messages: every message has expired, or the stack was
   deleted.

There is no transition for "forgotten on request". The agent cannot remove a conversation.
