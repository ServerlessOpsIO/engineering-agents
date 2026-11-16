# Tasks: OpenAI Model Migration

**Input**: Design documents from `/specs/005-model-migration/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. The specification requires the automated tests to keep running without
cloud credentials (FR-010), and the plan adds unit tests for the reasoning effort setting.

**Organization**: Tasks are grouped by user story so each story can be implemented and
validated on its own. Paths without a prefix are in this repository
(`engineering-agents`). Paths that start with `../backstage-aws-agentcore-template/` are in
the template repository, checked out next to this one.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`[US1]` to `[US6]`)
- Every task names a file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the two things outside this project that the feature cannot work
without, before changing anything.

- [ ] T001 In the Bedrock model catalog of the deployment account, in `us-east-1`, confirm the account can use OpenAI GPT-6 Luna, and record the result with the date under "Open questions for the project owner" in `specs/005-model-migration/research.md`
- [X] T002 Confirm with the project owner that Bedrock model invocation is allowed in `us-east-1`, `us-east-2` and `us-west-2`, and record the answer with the date in `specs/005-model-migration/research.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The new deployment setting that User Stories 1 and 6 both build on.

**⚠️ CRITICAL**: No user story work starts until this phase is complete.

- [X] T003 Add a `ReasoningEffort` parameter to `template.yaml`: type `String`, a description saying it sets how much the model reasons and that `default` leaves the choice to the model, `AllowedValues` of `default`, `none`, `low`, `medium`, `high`, `xhigh`, `max`, and `Default: default`
- [X] T004 Pass the parameter to the agent by adding `REASONING_EFFORT: !Ref ReasoningEffort` under `EnvironmentVariables` of `AgentRuntime` in `template.yaml`
- [X] T005 Run `sam validate --lint` and confirm `template.yaml` is valid

**Checkpoint**: The setting exists and reaches the agent's environment.

---

## Phase 3: User Story 1 - The agent answers using GPT-6 Luna (Priority: P1) 🎯 MVP

**Goal**: The deployed agent answers a prompt with GPT-6 Luna, at the model's default
reasoning effort unless the setting says otherwise.

**Independent Test**: Quickstart Scenario A.

### Tests for User Story 1

- [X] T006 [US1] In `tests/unit/test_main.py`, add a test that with `main.REASONING_EFFORT` unset, empty, or `default`, `main.get_model()` constructs `BedrockModel` with `model_id=main.MODEL_ID` and no `additional_request_fields`. Replace `main.BedrockModel` with a recording fake and reset `main._model` to `None` so nothing calls AWS. Confirm the test fails before T008
- [X] T007 [US1] In `tests/unit/test_main.py`, add a test that with `main.REASONING_EFFORT` set to `low`, `main.get_model()` constructs `BedrockModel` with `additional_request_fields={"reasoning": {"effort": "low"}}`. Confirm the test fails before T008

### Implementation for User Story 1

- [X] T008 [US1] In `src/agent/main.py`, read `REASONING_EFFORT = os.environ.get("REASONING_EFFORT")` next to the other settings, and change `get_model()` so that when the value is unset, empty or `default` it builds `BedrockModel(model_id=MODEL_ID)` as today, and otherwise builds it with `additional_request_fields={"reasoning": {"effort": REASONING_EFFORT}}`
- [X] T009 [US1] In `cfn-parameters.json`, change `ModelId` to `us.openai.gpt-6-luna` and add `"ReasoningEffort": "default"`
- [X] T010 [US1] Run `pipenv run test-unit` and confirm every test passes with no AWS credentials
- [ ] T011 [US1] Deploy by pushing the branch, then run Scenario A of `specs/005-model-migration/quickstart.md` with at least 10 prompts, and record the results (SC-001) in that file

**Checkpoint**: The agent answers with the new model. This is the MVP.

---

## Phase 4: User Story 2 - Nothing changes for callers (Priority: P1)

**Goal**: Requests, replies, refusals, errors, memory and records are as features 001 to 003
define them.

**Independent Test**: Quickstart Scenario B.

- [ ] T012 [US2] Run Scenarios A and B of `specs/001-agent-invocation/quickstart.md` against the deployed agent and record the results under Scenario B of `specs/005-model-migration/quickstart.md`
- [ ] T013 [US2] Run Scenarios A to C of `specs/002-conversation-memory/quickstart.md` against the deployed agent and record the results under Scenario B of `specs/005-model-migration/quickstart.md`
- [ ] T014 [US2] For one answered request, read its log record and confirm it matches `specs/003-observability/contracts/request-record.schema.json` with `modelId` of `us.openai.gpt-6-luna`; record the result under Scenario B of `specs/005-model-migration/quickstart.md`

**Checkpoint**: User Stories 1 and 2 hold together.

---

## Phase 5: User Story 3 - The agent may use the chosen model and no other (Priority: P2)

**Goal**: The role covers GPT-6 Luna and what it needs, and nothing else.

**Independent Test**: Quickstart Scenario C.

- [X] T015 [US3] In `template.yaml`, change the `AllowedPattern` of the `ModelId` parameter to `^us\.[a-zA-Z0-9.:_-]+$` and describe it as a United States inference profile ID that must start with `us.`. Replace the `Model` statement of `AgentExecutionRole` with two statements as in Decision 3 of `specs/005-model-migration/research.md`: `Model` allowing `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on `inference-profile/${ModelId}` and `project/default` in this account and region; and `ModelThroughProfile` allowing the same actions on `arn:${AWS::Partition}:bedrock:*::foundation-model/*` with the condition `StringEquals` on `bedrock:InferenceProfileArn` equal to the profile's ARN. Remove the `!Split` expressions on `ModelId`, and comment why the condition is used
- [X] T016 [US3] Run `sam validate --lint` and confirm `template.yaml` is valid
- [ ] T017 [US3] After deployment, run Scenario C of `specs/005-model-migration/quickstart.md` and record the role's resources (SC-005) in that file
- [ ] T018 [US3] Record in `specs/005-model-migration/research.md`, under Decision 3, whether the `bedrock:InferenceProfileArn` condition worked on the first deployed request, and whether the default-project resource was needed

**Checkpoint**: The role follows the model setting.

---

## Phase 6: User Story 4 - A missing prerequisite is easy to diagnose (Priority: P2)

**Goal**: The documentation lists the prerequisites and says how to tell their failures
apart.

**Independent Test**: Quickstart Scenario E, where a prerequisite is actually missing.

- [X] T019 [P] [US4] In `docs/handbook/03-configuration.md`, rewrite the model-access prerequisite to name OpenAI GPT-6 Luna, and replace the paragraph about the `us.` profile's regions so it names `us.openai.gpt-6-luna` and the three regions `us-east-1`, `us-east-2` and `us-west-2`
- [X] T020 [P] [US4] In `docs/handbook/06-observability.md`, add a short section on telling the two prerequisite failures apart: both have `errorType` `AccessDeniedException`; the failure detail entry contains `is not available for this account` for missing model access, and `with an explicit deny in a service control policy` for a region restriction
- [ ] T021 [US4] If a prerequisite is missing when the agent is first deployed, run Scenario E of `specs/005-model-migration/quickstart.md` and record the result (SC-006) in that file; otherwise record that the scenario could not be run

**Checkpoint**: An operator can diagnose both failures from the handbook.

---

## Phase 7: User Story 6 - New agents start on the same model (Priority: P2)

**Goal**: A project created from the template with default choices matches this project's
model settings, role statement, agent code and handbook text.

**Independent Test**: Quickstart Scenario G.

### Tests for User Story 6

- [X] T022 [P] [US6] Create `../backstage-aws-agentcore-template/skeleton/tests/conftest.py`, identical to `tests/conftest.py` in this repository, so the skeleton's tests can import the agent with `MODEL_ID` required
- [X] T023 [US6] In `../backstage-aws-agentcore-template/skeleton/tests/unit/test_main.py`, add the tests this repository has for `_require_env` and the two reasoning effort tests from T006 and T007, keeping any template conditionals already in that file

### Implementation for User Story 6

- [X] T024 [US6] In `../backstage-aws-agentcore-template/template.yaml`, change the `model_id` form field's default to `us.openai.gpt-6-luna` and its `pattern` to `^us\.[a-zA-Z0-9.:_-]+$`, add a `reasoning_effort` field (title "Reasoning effort", an enum of `default`, `none`, `low`, `medium`, `high`, `xhigh`, `max`, default `default`), and pass `reasoning_effort: ${{ parameters.reasoning_effort }}` to the skeleton step's values
- [X] T025 [US6] In `../backstage-aws-agentcore-template/skeleton/template.yaml`, remove the `Default` from `ModelId` and update its example to `us.openai.gpt-6-luna`, add the `ReasoningEffort` parameter and the `REASONING_EFFORT` environment variable as in T003 and T004, and make the `AllowedPattern` and `Model` statement changes of T015
- [X] T026 [P] [US6] In `../backstage-aws-agentcore-template/skeleton/cfn-parameters.json`, add `"ModelId": "${{ values.model_id }}"` and `"ReasoningEffort": "${{ values.reasoning_effort }}"`
- [X] T027 [US6] In `../backstage-aws-agentcore-template/skeleton/src/agent/main.py`, replace the `MODEL_ID` fallback with the `_require_env` function and `MODEL_ID = _require_env("MODEL_ID")` as in this repository's `src/agent/main.py`, and add `REASONING_EFFORT` and the `get_model()` change from T008
- [X] T028 [P] [US6] In `../backstage-aws-agentcore-template/skeleton/docs/handbook/01-features.md`, `03-configuration.md`, `06-observability.md` and `07-common-tasks.md`, apply the same text changes this repository's handbook has for the model set in `cfn-parameters.json`, `MODEL_ID` being required, the reasoning effort setting, the prerequisites and the failure diagnosis, using `${{ values.model_id }}` where this repository names the model
- [X] T029 [P] [US6] In `../backstage-aws-agentcore-template/skeleton/docs/handbook/02-creating-a-component.md`, say the form's model and reasoning effort go to `ModelId` and `ReasoningEffort` in `cfn-parameters.json`
- [X] T030 [US6] Run Scenario G of `specs/005-model-migration/quickstart.md` without Backstage: substitute the default form values into the skeleton's `cfn-parameters.json`, `template.yaml` and `src/agent/main.py`, compare each with this repository's file, and record the differences (SC-011) in that quickstart file
- [X] T031 [US6] With the default form values substituted into a scratch copy of the skeleton, run its unit tests and `sam validate --lint`, and record the results under Scenario G of `specs/005-model-migration/quickstart.md`

**Checkpoint**: The template and this project agree.

---

## Phase 8: User Story 5 - The owner can go back (Priority: P3)

**Goal**: Changing the model again is one setting and a deployment.

**Independent Test**: Quickstart Scenario F.

- [X] T032 [P] [US5] In `docs/handbook/07-common-tasks.md`, update "Change the model" to say the model and the reasoning effort are both set in `cfn-parameters.json`, that `ModelId` must be a United States inference profile ID starting with `us.` (global profiles are refused because the organization's region restriction denies them), and that a mistyped value that still starts with `us.` deploys and then fails at the first request
- [ ] T033 [US5] Run Scenario F of `specs/005-model-migration/quickstart.md` on a branch deployment, record the role's resources and the reply (SC-007) in that file, and delete the branch's stack afterwards

**Checkpoint**: All six user stories are in place.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation that names the old model, the remaining measurements, and the
specification's own loose ends.

- [X] T034 [P] Update `docs/handbook/01-features.md` to name `us.openai.gpt-6-luna` and the reasoning effort setting, and add `ReasoningEffort` to the parameter tables and `REASONING_EFFORT` to the environment variables in `docs/handbook/03-configuration.md`
- [X] T035 [P] Change the local-run command in `docs/handbook/07-common-tasks.md` to `MODEL_ID=us.openai.gpt-6-luna`
- [X] T036 [P] Update `specs/001-agent-invocation/quickstart.md`, `specs/001-agent-invocation/research.md` and `specs/001-agent-invocation/data-model.md` where they name the previous model, noting the change came from feature 005 (FR-012)
- [ ] T037 Run Scenario D of `specs/005-model-migration/quickstart.md` (reasoning effort at `default` and at `low`), record the output usage for both (SC-010) in that file, and update Decision 4 in `specs/005-model-migration/research.md` with whether the request field was accepted
- [ ] T038 Record the two reported results in `specs/005-model-migration/quickstart.md`: how many of at least 10 typical replies the owner judged acceptable (SC-003), and how many arrived within 30 seconds (SC-004)
- [ ] T039 Compare the token counts in the records for a known set of prompts with the service's figures (SC-009) and record the result in `specs/005-model-migration/quickstart.md`
- [X] T040 [P] Correct the two out-of-date notes in `specs/005-model-migration/checklists/requirements.md` (clarification is complete; the 8-of-10 bar was removed)
- [X] T041 Run `pipenv run test-unit` and `sam validate --lint` one last time and confirm both pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies. If T001 shows the account cannot use the model, stop
  and resolve that first; nothing later can be validated.
- **Phase 2 (Foundational)**: Can start alongside Phase 1. Blocks User Stories 1 and 6.
- **Phase 3 (US1)**: Depends on Phase 2. T011 also depends on Phase 1.
- **Phase 4 (US2)**: Depends on US1 being deployed.
- **Phase 5 (US3)**: T015 and T016 can be done with Phase 3 so they deploy together; if the
  first request in T011 fails for lack of permission, do them before retrying.
- **Phase 6 (US4)**: Documentation tasks are independent. T021 depends on a deployment.
- **Phase 7 (US6)**: Depends on Phases 2, 3 and 5, because it copies what they changed.
- **Phase 8 (US5)**: Depends on US1 and US3.
- **Phase 9 (Polish)**: Depends on the stories whose results it records.

### User Story Dependencies

- **US1 (P1)**: Needs the foundation only.
- **US2 (P1)**: Validation of US1's deployment; no code of its own.
- **US3 (P2)**: One template change; best deployed with US1.
- **US4 (P2)**: Documentation, plus one scenario that needs a real missing prerequisite.
- **US6 (P2)**: Mirrors US1 and US3 in the template repository.
- **US5 (P3)**: Documentation, plus one scenario on a branch deployment.

### Within Each User Story

- Write the tests first and see them fail before the implementation.
- Change settings and code before deploying; deploy before running a quickstart scenario.
- Record each scenario's result in the quickstart as it is run.

---

## Parallel Execution Examples

### User Story 4

```bash
Task: "T019 [US4] Prerequisites in docs/handbook/03-configuration.md"
Task: "T020 [US4] Failure diagnosis in docs/handbook/06-observability.md"
```

### User Story 6

```bash
Task: "T022 [US6] skeleton/tests/conftest.py"
Task: "T026 [US6] skeleton/cfn-parameters.json"
Task: "T028 [US6] skeleton handbook pages"
Task: "T029 [US6] skeleton/docs/handbook/02-creating-a-component.md"
```

---

## Implementation Strategy

### MVP First (User Story 1, with User Story 3's template change)

1. Phase 1: confirm model access and regions.
2. Phase 2: the `ReasoningEffort` parameter.
3. Phase 3, plus T015 and T016 from Phase 5: tests, code, settings, role.
4. Deploy and run quickstart Scenario A. **Stop and validate**: the agent answers.

### Incremental Delivery

1. MVP: the agent answers with GPT-6 Luna.
2. US2 and US3 validation: nothing changed for callers; the role is right.
3. US4: the handbook explains the prerequisites and their failures.
4. US6: the template matches. This is a separate pull request in the template repository.
5. US5 and Polish: going back is documented and tried; measurements are recorded.

### Two Repositories

The changes in `engineering-agents` and in `backstage-aws-agentcore-template` are separate
commits and pull requests. The feature is complete only when both are merged (FR-015).
