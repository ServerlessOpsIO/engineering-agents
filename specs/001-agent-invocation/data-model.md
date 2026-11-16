# Phase 1 Data Model: Agent Invocation

**Backfill**: Read from `src/agent/main.py` and `template.yaml` at commit `fd37671`.

Nothing in this feature is stored. These are the shapes that pass through one request.

## Entity: InvocationRequest

What a caller sends through `InvokeAgentRuntime`.

| Field | Type | Required | Notes |
|---|---|---|---|
| `prompt` | string | Yes | Trimmed before use. Must not be empty. At most `MAX_PROMPT_CHARS` characters after trimming. |
| `actorId` | string | No | Who is asking. Used by feature 002. `default` when absent, empty or not a string. |
| `runtimeSessionId` | string | Yes | A parameter of the call, not part of the body. 33 to 256 characters, enforced by the service. Reaches the agent as `context.session_id`. Used by feature 002. |

### Validation Rules

- A body that is not a JSON object is treated as a request with no prompt.
- A `prompt` that is missing, not a string, empty, or only white space is an input rejection.
- A `prompt` longer than `MAX_PROMPT_CHARS` after trimming is an input rejection. A prompt
  exactly at the limit is accepted.
- Fields other than `prompt` and `actorId` are ignored.

## Entity: InvocationReply

What the agent returns.

| Field | Type | Required | Notes |
|---|---|---|---|
| `kind` | enum(`answer`, `input_rejection`, `error`) | Yes | Tells the caller what the text is. |
| `text` | string | Yes | The model's reply, trimmed, for `answer`. A fixed message otherwise. |
| `requestId` | string | Yes | The request identifier from the runtime. The same value is in the request record (feature 003). |

### Fixed texts

| Situation | `kind` | HTTP | `text` |
|---|---|---|---|
| Missing, empty or non-text prompt | `input_rejection` | 200 | `Please send a prompt.` |
| Prompt over the limit | `input_rejection` | 200 | `The prompt is too long. The limit is <limit> characters.` |
| Any failure while the agent runs | `error` | 500 | `The agent could not produce a reply. Try again later.` |

## Entity: AgentSettings

Values the runtime passes to the agent as environment variables.

| Variable | Template parameter | Default | Notes |
|---|---|---|---|
| `MODEL_ID` | `ModelId` | None. Set to `us.openai.gpt-6-luna` in `cfn-parameters.json`. | A United States Bedrock inference profile ID. Changed by feature 005. |
| `MAX_PROMPT_CHARS` | `MaxPromptChars` | `4000` | Longest prompt accepted. |
| `LOG_LEVEL` | `LogLevel` | `INFO` | Feature 003. |
| `MEMORY_ID` | none (from `AgentMemory`) | none | Feature 002. |

## Entity: Instructions

The text of `src/agent/system_prompt.md`, stripped of surrounding white space and held as
`prompt.SYSTEM_PROMPT`. It is read once, when the module is first imported, and passed to every
agent as its system prompt.

## State Transitions

1. `received` → `rejected` (`input_rejection`): the prompt fails a check. The model is not
   called.
2. `received` → `accepted`: the prompt passes the checks.
3. `accepted` → `answered` (`answer`): the agent returned text.
4. `accepted` → `failed` (`error`): an exception was raised while building or running the
   agent.

Requests the service rejects (no permission, malformed body, bad session identifier) never
enter this model.
