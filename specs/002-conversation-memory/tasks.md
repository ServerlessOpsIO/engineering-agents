# Tasks: Conversation Memory

**Input**: Design documents from `/specs/002-conversation-memory/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Backfill**: This list was written after the work was done. A task marked `[X]` describes
something that exists in the code on `main` (commit `fd37671`). The work was not actually
carried out as these separate tasks or in this order. Tasks left unmarked, in the last phase,
are things the specification asks for that had not been done or checked on 2026-11-15.

**Tests**: None exist for this feature. The missing tests are listed in the last phase.

**Organization**: Tasks are grouped by user story so each story can be traced to code.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Could have run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`[US1]` to `[US3]`)
- Every task names a file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: The store and the agent's access to it.

- [X] T001 Define the `AgentMemory` resource, named after the component and branch, in `template.yaml`
- [X] T002 Allow the execution role to create, read, list and delete events and list sessions on this stack's memory only (`Memory` statement) in `template.yaml`
- [X] T003 Pass the memory's ID to the agent as `MEMORY_ID` in `template.yaml`
- [X] T004 [P] Export `AgentMemoryId` as a stack output in `template.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Read the settings memory depends on.

- [X] T005 Read `MEMORY_ID` from the environment and define `DEFAULT_ACTOR_ID` in `src/agent/main.py`
- [X] T006 Read the session ID from the request context in `invoke` in `src/agent/main.py`

**Checkpoint**: The agent knows which memory and which session a request belongs to.

---

## Phase 3: User Story 1 - Ask a follow-up in the same conversation (Priority: P1) 🎯 MVP

**Goal**: A follow-up in the same conversation is answered using the earlier exchange.

**Independent Test**: Quickstart Scenario A.

### Implementation for User Story 1

- [X] T007 [US1] Give the agent an `AgentCoreMemorySessionManager` for the request's memory, session and actor in `build_agent` in `src/agent/main.py`
- [X] T008 [US1] Start the agent empty when `MEMORY_ID` or the session ID is missing in `build_agent` in `src/agent/main.py`
- [X] T009 [P] [US1] Add a `--session-id` option, with a new identifier by default, in `scripts/invoke.py`
- [X] T010 [P] [US1] Document how to continue a conversation in `docs/handbook/07-common-tasks.md`

**Checkpoint**: User Story 1 is in place.

---

## Phase 4: User Story 2 - Conversations stay separate (Priority: P1)

**Goal**: Conversations and askers never share context.

**Independent Test**: Quickstart Scenarios B, C and F.

### Implementation for User Story 2

- [X] T011 [US2] Read `actorId` from the request body, falling back to `default`, in `invoke` in `src/agent/main.py`
- [X] T012 [US2] Pass the actor to the session manager in `build_agent` in `src/agent/main.py`
- [X] T013 [P] [US2] Add an `--actor-id` option in `scripts/invoke.py`
- [X] T014 [P] [US2] Document `actorId` in the invoke interface in `docs/handbook/04-architecture.md`

**Checkpoint**: User Stories 1 and 2 are in place.

---

## Phase 5: User Story 3 - Remembered messages are removed after a set time (Priority: P2)

**Goal**: Messages expire after a period the owner sets.

**Independent Test**: Quickstart Scenario E.

### Implementation for User Story 3

- [X] T015 [US3] Add the `MemoryEventExpiryDays` parameter (default 7, range 3 to 365) and use it as the memory's event expiry in `template.yaml`
- [X] T016 [P] [US3] Document the parameter and what is remembered in `docs/handbook/03-configuration.md` and `docs/handbook/01-features.md`

**Checkpoint**: All three user stories are in place.

---

## Phase 6: Outstanding at Backfill

**Purpose**: Things the specification asks for that were not done or not checked when this
list was written. None of these is started.

- [ ] T017 [US1] Add a unit test that `build_agent` creates a session manager with the request's memory, session and actor when `MEMORY_ID` is set in `tests/unit/test_main.py`
- [ ] T018 [US1] Add a unit test that `build_agent` uses no session manager when `MEMORY_ID` or the session ID is missing in `tests/unit/test_main.py`
- [ ] T019 [US2] Add a unit test that a missing, empty or non-string `actorId` becomes `default` in `tests/unit/test_main.py`
- [ ] T020 [US1] Run quickstart Scenarios A and D against the deployed agent and record the results (SC-001, SC-003) in `specs/002-conversation-memory/quickstart.md`
- [ ] T021 [US2] Run quickstart Scenarios B, C and F and record the results (SC-002) in `specs/002-conversation-memory/quickstart.md`
- [ ] T022 [US3] Run quickstart Scenario E on a branch deployment and record the result (SC-004) in `specs/002-conversation-memory/quickstart.md`
- [ ] T023 Find out what a caller receives when memory cannot be read or saved, and record it in `specs/002-conversation-memory/research.md`
- [ ] T024 Find out how much of a long conversation the session manager loads, and record it in `specs/002-conversation-memory/research.md`
- [ ] T025 Decide each item under "Differences from the Bill-GN specification" in `specs/002-conversation-memory/spec.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Depends on feature 001's runtime and execution role.
- **Phase 2 (Foundational)**: Depends on Phase 1.
- **Phases 3 to 5 (User Stories)**: Each depends on Phase 2.
- **Phase 6 (Outstanding)**: T020 to T022 need a deployed agent. T022 needs more than 3 days.

### User Story Dependencies

- **US1 (P1)**: Needs only the foundation.
- **US2 (P1)**: Extends US1's session manager with the actor.
- **US3 (P2)**: A template setting, independent of US1 and US2.
