# Phase 0 Research: Agent Invocation

**Backfill**: These decisions were read from the code, its comments and the project handbook on
2026-11-15. No research was recorded when the feature was built. Where a rationale is written
down in the repository it is cited. Where it is not, this file says "not recorded" and does
not guess. No alternatives were recorded for any decision, so none are listed.

## Decision 1: Strands Agents SDK on Amazon Bedrock AgentCore Runtime

- **Decision**: Build the agent with the Strands Agents SDK and host it on AgentCore Runtime as
  a container, calling an Anthropic Claude model through Amazon Bedrock.
- **Rationale**: The project was generated from the organization's AgentCore agent template,
  which fixes these choices. The handbook adds that the runtime "costs nothing while idle".
  The same stack is fixed by the Bill-GN constitution this agent was modelled on.

## Decision 2: Authorize callers with IAM, with no public endpoint

- **Decision**: Callers use `InvokeAgentRuntime`, signed with IAM. A caller needs
  `bedrock-agentcore:InvokeAgentRuntime` on the runtime's ARN. The service rejects everyone
  else before the agent runs.
- **Rationale**: Handbook, `01-features.md`: "Callers authenticate with IAM. There is no
  public, unauthenticated endpoint."

## Decision 3: Check the prompt before the model is called

- **Decision**: Trim the prompt, then refuse it when it is empty, not a string, or longer than
  `MAX_PROMPT_CHARS`. The refusal is returned without building an agent.
- **Rationale**: Handbook, `01-features.md`: such prompts "are rejected without spending
  tokens".

## Decision 4: A reply envelope with a `kind`

- **Decision**: Every reply is `{"kind", "text", "requestId"}`. `answer` and `input_rejection`
  return HTTP 200. `error` returns HTTP 500.
- **Rationale**: Not recorded. The effect is that a caller can branch on `kind` and that a
  failed request is visible as failed at the HTTP level.

## Decision 5: A fixed error message, with detail only in the log

- **Decision**: Any exception while the agent runs becomes the fixed text "The agent could not
  produce a reply. Try again later." The exception type and stack trace go to the log.
- **Rationale**: Code comment in `main.py`: "Any failure becomes a generic reply; detail goes
  to the log." Handbook: "Failure details go to the log and never to the caller."

## Decision 6: The system prompt is a Markdown file

- **Decision**: The instructions are in `src/agent/system_prompt.md`, read once at start by
  `prompt.py`.
- **Rationale**: Docstring in `prompt.py`: "so it can be edited and reviewed as prose".

## Decision 7: The model is a deployment parameter, as an inference profile ID

- **Decision**: `ModelId` in `template.yaml` (default `global.anthropic.claude-haiku-5-5`) is
  passed to the agent as `MODEL_ID`. The execution role's model permission is built from the
  same value: the inference profile, and the foundation model in any region.
- **Rationale**: Template comment: "The inference profile routes requests to the model in
  other regions, so the foundation model is allowed in any region."

## Decision 8: Create the model client on first use

- **Decision**: `get_model()` creates the `BedrockModel` the first time it is needed.
- **Rationale**: Docstring: "so importing this module calls nothing". This is what lets the
  unit tests import `main` without AWS credentials.

## Decision 9: A new agent object for every request

- **Decision**: `build_agent` returns a fresh `Agent` per request, with `callback_handler=None`.
- **Rationale**: Not recorded. The effect is that no state is shared between requests inside
  the process; anything carried between requests comes from memory (feature 002).

## Decision 10: Short runtime sessions

- **Decision**: `IdleRuntimeSessionTimeout: 300` and `MaxLifetime: 1800`.
- **Rationale**: Template comment: "which keeps idle compute low. Raise both for agents that
  run long tasks."

## Open questions found during backfill

- The instructions describe leading a review session against a GitHub repository and writing
  an artifact to it. Nothing in this design gives the agent access to a repository. See the
  specification's "Differences from the Bill-GN specification".
- No decision is recorded on how the agent should treat a prompt that asks it to ignore its
  instructions.
