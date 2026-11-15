# Tasks: Observability

**Input**: Design documents from `/specs/003-observability/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Backfill**: This list was written after the work was done. A task marked `[X]` describes
something that exists in the code on `main` (commit `fd37671`). The work was not actually
carried out as these separate tasks or in this order. Tasks left unmarked, in the last phase,
are things the specification asks for that had not been done or checked on 2026-11-15.

**Tests**: Included, because the request record has unit tests.

**Organization**: Tasks are grouped by user story so each story can be traced to code and
tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Could have run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`[US1]` to `[US4]`)
- Every task names a file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies and settings observability needs.

- [X] T001 Declare the runtime dependency `aws-opentelemetry-distro` in `Pipfile`
- [X] T002 [P] Add the `LogLevel` parameter and pass it to the agent as `LOG_LEVEL` in `template.yaml`
- [X] T003 [P] Set the organization's tags `org:domain`, `org:system` and `org:component` in `cfn-tags.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: A logger and the permissions to deliver what it writes.

- [X] T004 Configure the `agent` logger to write bare JSON lines to standard output, at the level in `LOG_LEVEL`, in `src/agent/main.py`
- [X] T005 Allow the execution role to create and write to the AgentCore runtime log groups (`Logs`, `LogGroupDiscovery`, `LogEvents` statements) in `template.yaml`
- [X] T006 [P] Add a `records` fixture that collects the JSON records the agent logs in `tests/unit/test_main.py`

**Checkpoint**: The agent can write a log line that reaches a log group.

---

## Phase 3: User Story 1 - Find out what happened to one request (Priority: P1) 🎯 MVP

**Goal**: One record per request, findable from the request identifier in the reply.

**Independent Test**: Quickstart Scenario A.

### Tests for User Story 1

- [X] T007 [P] [US1] Assert that an answered request writes one record with `kind`, `sessionId`, token counts and `durationMs` in `tests/unit/test_main.py`
- [X] T008 [P] [US1] Assert that a rejected prompt writes a record with `kind` `input_rejection` in `tests/unit/test_main.py`
- [X] T009 [P] [US1] Assert that a failure writes a record with `kind` `error` and the exception's class name in `tests/unit/test_main.py`

### Implementation for User Story 1

- [X] T010 [US1] Start a record with `requestId`, `sessionId` and `promptChars` at the top of `invoke` in `src/agent/main.py`
- [X] T011 [US1] Write the record once, with `durationMs`, from `_log_request` on every exit path of `invoke` in `src/agent/main.py`
- [X] T012 [US1] Add `modelId` once the prompt passes the input checks, and token counts from `_token_usage` for an answer, in `src/agent/main.py`
- [X] T013 [US1] Add `errorType` and log the stack trace with the request identifier on failure in `src/agent/main.py`
- [X] T014 [US1] Return the same `requestId` in every reply in `src/agent/main.py`
- [X] T015 [P] [US1] Document the log group, every field and how to find a request in `docs/handbook/06-observability.md`
- [X] T016 [P] [US1] Export `AgentRuntimeId`, which names the log group, in `template.yaml`

**Checkpoint**: User Story 1 is in place.

---

## Phase 4: User Story 2 - Request records never hold what was said (Priority: P1)

**Goal**: No prompt or reply text in a request record.

**Independent Test**: Quickstart Scenario B.

### Tests for User Story 2

- [X] T017 [P] [US2] Assert that a record contains neither the prompt nor the reply, and holds the prompt's length, in `tests/unit/test_main.py`

### Implementation for User Story 2

- [X] T018 [US2] Record only the prompt's length, and nothing of the reply, in `invoke` in `src/agent/main.py`
- [X] T019 [P] [US2] Document what is deliberately not recorded in `docs/handbook/06-observability.md`

**Checkpoint**: User Stories 1 and 2 are in place.

---

## Phase 5: User Story 3 - See the steps inside a request (Priority: P2)

**Goal**: A trace for each request.

**Independent Test**: Quickstart Scenario D.

### Implementation for User Story 3

- [X] T020 [US3] Start the agent under `opentelemetry-instrument` in `src/agent/Dockerfile`
- [X] T021 [US3] Allow the execution role to send trace data (`Tracing` statement) in `template.yaml`
- [X] T022 [P] [US3] Document CloudWatch Transaction Search as a deployment prerequisite in `docs/handbook/03-configuration.md`

**Checkpoint**: User Stories 1 to 3 are in place.

---

## Phase 6: User Story 4 - See how much the agent is used (Priority: P3)

**Goal**: The platform's measurements exist and are documented.

**Independent Test**: Quickstart Scenario E.

### Implementation for User Story 4

- [X] T023 [US4] Allow the execution role to publish metrics in the `bedrock-agentcore` namespace only (`Metrics` statement) in `template.yaml`
- [X] T024 [P] [US4] Document the platform's metrics and how to select a deployment by tag in `docs/handbook/06-observability.md`

**Checkpoint**: All four user stories are in place.

---

## Phase 7: Outstanding at Backfill

**Purpose**: Things the specification asks for that were not done or not checked when this
list was written. None of these is started.

- [ ] T025 [US3] Run quickstart Scenario D and record whether traces contain prompt or reply text in `specs/003-observability/research.md`
- [ ] T026 [US2] Run quickstart Scenario B against the deployed agent and record the result (SC-003) in `specs/003-observability/quickstart.md`
- [ ] T027 [US1] Run quickstart Scenarios A and C against the deployed agent and record the results (SC-001) in `specs/003-observability/quickstart.md`
- [ ] T028 [US3] Confirm CloudWatch Transaction Search is enabled in the deployment account and record it in `specs/003-observability/research.md`
- [ ] T029 [US4] Run quickstart Scenario E and record the result (SC-005) in `specs/003-observability/quickstart.md`
- [ ] T030 Compare recorded token counts with the provider's figures (SC-006) and record the result in `specs/003-observability/quickstart.md`
- [ ] T031 Check whether the agent's logs, metrics and traces reach Datadog with the organization's tags, and record it in `specs/003-observability/research.md`
- [ ] T032 Decide each item under "Differences from the Bill-GN specification" in `specs/003-observability/spec.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Depends on feature 001's runtime and feature 004's dependency file.
- **Phase 2 (Foundational)**: Depends on Phase 1.
- **Phases 3 to 6 (User Stories)**: Each depends on Phase 2. User Story 2 constrains what User
  Story 1 writes.
- **Phase 7 (Outstanding)**: All need a deployed agent. T025 comes first, because its result
  may change the specification.

### User Story Dependencies

- **US1 (P1)**: Needs only the foundation.
- **US2 (P1)**: A constraint on US1's record.
- **US3 (P2)**: Independent of US1 and US2.
- **US4 (P3)**: Independent. Mostly documentation.
