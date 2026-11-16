# Implementation Plan: OpenAI Model Migration

**Branch**: `feature/005-model-migration` | **Date**: 2026-11-15 | **Spec**: `specs/005-model-migration/spec.md`

**Input**: Feature specification from `specs/005-model-migration/spec.md`

## Summary

Move the agent from Claude Haiku 5.5 to OpenAI GPT-6 Luna on Amazon Bedrock by changing the
`ModelId` deployment parameter to `us.openai.gpt-6-luna`. The agent keeps calling Bedrock
through Strands' `BedrockModel` (the Converse API), which GPT-6 Luna supports, so no change
to how the model is called is planned. Add one deployment parameter, `ReasoningEffort`, that
the agent passes to the model only when it is set to something other than `default`. Extend
the execution role with the one extra resource OpenAI models on this endpoint need. Make the
same changes in `backstage-aws-agentcore-template`, which also has to catch up with two
changes already made here (the model set in `cfn-parameters.json`, and `MODEL_ID` required
at start).

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: `strands-agents` 1.65.0 (`strands.models.BedrockModel`),
`bedrock-agentcore` 1.26.0. No new packages.

**Storage**: Unchanged. AgentCore Memory (feature 002).

**Testing**: `pytest` 9.2.0 through `pipenv run test-unit`. `sam validate --lint` for the
template. New unit tests for the reasoning effort setting. No test calls AWS.

**Target Platform**: Amazon Bedrock AgentCore Runtime in `us-east-1`. Model: OpenAI GPT-6
Luna through the `bedrock-runtime` endpoint, Converse and ConverseStream APIs, United States
inference profile `us.openai.gpt-6-luna` (routes to `us-east-1`, `us-east-2`, `us-west-2`).

**Project Type**: Single service (one agent container) with its infrastructure in a SAM
template, plus the Backstage template repository that generates such projects.

**Performance Goals**: 95% of replies within 30 seconds (SC-004, a starting value).

**Constraints**:

- `ModelId` must be a United States inference profile ID: it must start with `us.`
  (project owner's decision, 2026-11-15, to keep the agent off global profiles that the
  region restriction denies). The rest of the ID is not validated and may contain dots, so
  the role's permissions are tied to the profile with a condition and not derived by
  splitting the ID (see research, Decisions 3 and 7).
- GPT-6 Luna has no in-Region inference on `bedrock-runtime`, so the profile is required and
  all three destination regions must be allowed by the organization.
- The deployment account must have access to the model. Not checked.
- On this endpoint each output token counts as 10 against the account's token quota.
- The agent sends text only. The model rejects `document` content blocks on Converse.

**Scale/Scope**: Two repositories. In `engineering-agents`: `template.yaml`,
`cfn-parameters.json`, `src/agent/main.py`, `tests/unit/test_main.py`, the handbook, and the
specifications that name the old model. In `backstage-aws-agentcore-template`: the creation
form, and the same files under `skeleton/`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Not performed, before or after design. `.specify/memory/constitution.md` is still the
unfilled Spec Kit template, so there are no principles or gates to evaluate. This is an open
item for the project owner and is not treated as a gate failure.

## Project Structure

### Documentation (this feature)

```text
specs/005-model-migration/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── model-settings.md
├── checklists/
│   └── requirements.md
├── catalog-info.yaml
└── tasks.md               # Created later by /speckit-tasks
```

### Source Code (repository root)

`engineering-agents`:

```text
template.yaml                 # ReasoningEffort parameter; REASONING_EFFORT environment
                              # variable; default-project resource in the Model statement
cfn-parameters.json           # ModelId -> us.openai.gpt-6-luna; ReasoningEffort
src/agent/main.py             # Read REASONING_EFFORT; pass it to BedrockModel when set
tests/unit/test_main.py       # Tests for the reasoning effort setting
docs/handbook/                # 01-features, 03-configuration, 04-architecture,
                              # 06-observability, 07-common-tasks
specs/001-agent-invocation/   # Files that name the previous model
```

`backstage-aws-agentcore-template`:

```text
template.yaml                           # Form: model default; reasoning effort field
skeleton/template.yaml                  # Same changes as above; ModelId default removed
skeleton/cfn-parameters.json            # ModelId and ReasoningEffort from the form values
skeleton/src/agent/main.py              # MODEL_ID required; REASONING_EFFORT
skeleton/tests/conftest.py              # New: sets MODEL_ID for the tests
skeleton/tests/unit/test_main.py        # Tests for both settings
skeleton/docs/handbook/                 # Same pages as above
```

**Structure Decision**: No new modules or resources. The change is one new setting carried
through the existing path (deployment parameter, environment variable, model client), plus
values and documentation. The template repository is changed file-for-file to match.

## Complexity Tracking

Nothing recorded. With no constitution in force there are no violations to justify.
