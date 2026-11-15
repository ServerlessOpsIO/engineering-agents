# Tasks: Agent Invocation

**Input**: Design documents from `/specs/001-agent-invocation/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Backfill**: This list was written after the work was done. A task marked `[X]` describes
something that exists in the code on `main` (commit `fd37671`). The work was not actually
carried out as these separate tasks or in this order. Tasks left unmarked, in the last phase,
are things the specification asks for that had not been done or checked on 2026-11-15.

**Tests**: Included, because the feature has unit tests.

**Organization**: Tasks are grouped by user story so each story can be traced to code and
tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Could have run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`[US1]` to `[US4]`)
- Every task names a file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: The project skeleton the agent lives in.

- [X] T001 Create the agent module directory with its entry point in `src/agent/main.py`
- [X] T002 [P] Configure pytest to find tests and the agent module in `pytest.ini`
- [X] T003 [P] Declare runtime dependencies `strands-agents` and `bedrock-agentcore` in `Pipfile` (feature 004)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The runtime, its role and its settings.

- [X] T004 Define the `AgentRuntime` resource (HTTP protocol, public network mode, container image, lifecycle limits) in `template.yaml`
- [X] T005 Define `AgentExecutionRole` with a trust policy limited to this account's AgentCore runtimes in `template.yaml`
- [X] T006 Add the `ModelId` and `MaxPromptChars` parameters and pass them to the agent as `MODEL_ID` and `MAX_PROMPT_CHARS` in `template.yaml`
- [X] T007 Create the `BedrockAgentCoreApp` and register the `invoke` entry point in `src/agent/main.py`
- [X] T008 Export `AgentRuntimeArn` and `AgentRuntimeId` as stack outputs in `template.yaml`

**Checkpoint**: A runtime exists that can receive a request.

---

## Phase 3: User Story 1 - Send a prompt and get a reply (Priority: P1) 🎯 MVP

**Goal**: An authorized caller sends a prompt and receives an answer.

**Independent Test**: Quickstart Scenario A.

### Tests for User Story 1

- [X] T009 [P] [US1] Test that a prompt is trimmed, answered, and returned with `kind` `answer` and a `requestId` in `tests/unit/test_main.py`

### Implementation for User Story 1

- [X] T010 [US1] Create the Bedrock model client on first use in `get_model` in `src/agent/main.py`
- [X] T011 [US1] Build an agent per request with the system prompt in `build_agent` in `src/agent/main.py`
- [X] T012 [US1] Trim the prompt, call the agent and return the answer envelope in `invoke` in `src/agent/main.py`
- [X] T013 [US1] Allow the execution role to invoke only the configured model (`Model` statement) in `template.yaml`
- [X] T014 [P] [US1] Write a command-line script that sends one prompt to a deployed agent in `scripts/invoke.py`
- [X] T015 [P] [US1] Document the invoke interface and how to grant a caller access in `docs/handbook/04-architecture.md` and `docs/handbook/07-common-tasks.md`

**Checkpoint**: User Story 1 works with a deployed agent.

---

## Phase 4: User Story 2 - Unusable prompts are refused before any work is done (Priority: P1)

**Goal**: Empty and over-length prompts get an input rejection and never reach the model.

**Independent Test**: Quickstart Scenario B.

### Tests for User Story 2

- [X] T016 [P] [US2] Test that missing, empty, blank and non-text prompts are rejected without calling the agent in `tests/unit/test_main.py`
- [X] T017 [P] [US2] Test that a prompt over the limit is rejected and a prompt at the limit is accepted in `tests/unit/test_main.py`

### Implementation for User Story 2

- [X] T018 [US2] Return an `input_rejection` for an empty prompt before building an agent in `src/agent/main.py`
- [X] T019 [US2] Return an `input_rejection` that states the limit for a prompt over `MAX_PROMPT_CHARS` in `src/agent/main.py`

**Checkpoint**: User Stories 1 and 2 both work.

---

## Phase 5: User Story 3 - Failures are clear and reveal nothing (Priority: P2)

**Goal**: Any failure returns a fixed error message with HTTP 500.

**Independent Test**: Quickstart Scenario C.

### Tests for User Story 3

- [X] T020 [P] [US3] Test that a failure returns status 500, `kind` `error`, the fixed text, and none of the exception's message in `tests/unit/test_main.py`

### Implementation for User Story 3

- [X] T021 [US3] Catch any exception from building or running the agent and return the fixed error reply with status 500 in `src/agent/main.py`

**Checkpoint**: User Stories 1 to 3 work.

---

## Phase 6: User Story 4 - The owner sets what the agent does in one place (Priority: P2)

**Goal**: The instructions are one prose file that governs every reply.

**Independent Test**: Quickstart Scenario E.

### Tests for User Story 4

- [X] T022 [P] [US4] Test that the system prompt is not empty in `tests/unit/test_prompt.py`

### Implementation for User Story 4

- [X] T023 [US4] Write the agent's instructions in `src/agent/system_prompt.md`
- [X] T024 [US4] Load the instructions once at start in `src/agent/prompt.py`
- [X] T025 [P] [US4] Document how to change the instructions and the model in `docs/handbook/07-common-tasks.md`

**Checkpoint**: All four user stories are in place.

---

## Phase 7: Outstanding at Backfill

**Purpose**: Things the specification asks for that were not done or not checked when this
list was written. None of these is started.

- [ ] T026 [US1] Run quickstart Scenario A against the deployed `main` agent and record the result (SC-001) in `specs/001-agent-invocation/quickstart.md`
- [ ] T027 [US1] Run quickstart Scenario D with a role that lacks access and record the result (SC-004) in `specs/001-agent-invocation/quickstart.md`
- [ ] T028 [US4] Run quickstart Scenario E on a branch deployment and record the result (SC-007) in `specs/001-agent-invocation/quickstart.md`
- [ ] T029 Measure idle cost over 24 hours with no requests and record it (SC-006) in `specs/001-agent-invocation/quickstart.md`
- [ ] T030 [US4] Decide what the agent is for, given that `src/agent/system_prompt.md` describes repository reviews the agent cannot perform, and update `specs/001-agent-invocation/spec.md`
- [ ] T031 [US4] Add a test in `tests/unit/test_prompt.py` for each rule the instructions must keep, once the instructions contain rules
- [ ] T032 Fill in `.specify/memory/constitution.md` and complete the Constitution Check in `specs/001-agent-invocation/plan.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1.
- **Phases 3 to 6 (User Stories)**: Each depends on Phase 2. User Stories 2 and 3 change the
  same function as User Story 1 (`invoke`), so they follow it.
- **Phase 7 (Outstanding)**: T026 to T029 need a deployed agent. T031 depends on T030.

### User Story Dependencies

- **US1 (P1)**: Needs only the foundation.
- **US2 (P1)**: Adds checks in front of US1's agent call.
- **US3 (P2)**: Wraps US1's agent call.
- **US4 (P2)**: Independent of US2 and US3. US1 uses its output.
