# Tasks: Build and Delivery

**Input**: Design documents from `/specs/004-build-and-delivery/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Backfill**: This list was written after the work was done. A task marked `[X]` describes
something that exists in the code on `main` (commit `fd37671`). Most of it came with the
project when it was generated from the organization's template. Tasks T014 to T019 and T023
were done on 2026-11-14 (commits `869a43f` and `fd37671`). The rest was not carried out as
these separate tasks or in this order. Tasks left unmarked, in the last phase, are things the
specification asks for that had not been done or checked on 2026-11-15.

**Tests**: This feature has no tests of its own. It is what runs the other features' tests.

**Organization**: Tasks are grouped by user story so each story can be traced to files.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Could have run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: User story label (`[US1]` to `[US4]`)
- Every task names a file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: The files the pipeline reads.

- [X] T001 Set the stack name prefix and capabilities in `samconfig.toml`
- [X] T002 [P] Define the deployment parameter values, resolved from the environment and secrets, in `cfn-parameters.json`
- [X] T003 [P] Define the image parameters `ContainerRepo`, `ContainerOrg`, `ContainerImage` and `ContainerTag` in `template.yaml`
- [X] T004 [P] Configure template linting in `.cfnlintrc`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: An image definition the pipeline can build.

- [X] T005 Write the image definition: arm64 base image from ECR Public, port 8080, the agent's start command, in `src/agent/Dockerfile`
- [X] T006 Create an unprivileged user and run the agent as it in `src/agent/Dockerfile`
- [X] T007 [P] Allow the organization's accounts to pull the image in `.github/workflows/ecr-policy.json`
- [X] T008 [P] Allow the execution role to pull the image from the CI/CD account's repository (`EcrToken`, `EcrImage` statements) in `template.yaml`

**Checkpoint**: The agent can be packaged and the runtime can retrieve the package.

---

## Phase 3: User Story 1 - A pushed change is tested, built and deployed (Priority: P1) 🎯 MVP

**Goal**: A push produces a deployment for its branch, running that commit.

**Independent Test**: Quickstart Scenarios A and B.

### Implementation for User Story 1

- [X] T009 [US1] Add the `build_infra` job (`sam validate --lint`, `sam build`, store artifacts) in `.github/workflows/main.yml` and `.github/workflows/branch.yml`
- [X] T010 [US1] Add the `build_container` job on an arm64 runner, building and pushing the image with branch and commit tags, in `.github/workflows/main.yml` and `.github/workflows/branch.yml`
- [X] T011 [US1] Add the `deploy` job, which needs both build jobs and deploys `<repository>-<branch slug>`, in `.github/workflows/main.yml` and `.github/workflows/branch.yml`
- [X] T012 [US1] Name the runtime and memory after the component and branch so each branch has its own in `template.yaml`
- [X] T013 [P] [US1] Document each job, the image tags and branch stacks in `docs/handbook/05-ci-cd.md`

**Checkpoint**: User Story 1 is in place.

---

## Phase 4: User Story 3 - Dependencies are declared once and locked (Priority: P2)

**Goal**: One dependency file at the root, locked, used everywhere.

**Independent Test**: Quickstart "Local Checks", "Local Image Build" and Scenario D.

Listed before User Story 2 because User Story 2's test step depends on it.

### Implementation for User Story 3

- [X] T014 [US3] Declare runtime packages under `[packages]`, test tools under `[dev-packages]` and the Python version in `Pipfile`, replacing `src/agent/requirements.txt` and `requirements-dev.txt`
- [X] T015 [US3] Lock exact versions in `Pipfile.lock`
- [X] T016 [US3] Install the locked runtime packages into the image with `pipenv install --system --deploy`, and copy the agent from `src/agent/`, in `src/agent/Dockerfile`
- [X] T017 [US3] Limit the build context to `Pipfile`, `Pipfile.lock` and `src/agent/` in `.dockerignore`
- [X] T018 [US3] Build the image with the repository root as the context (`path: .`) in `.github/workflows/main.yml` and `.github/workflows/branch.yml`
- [X] T019 [P] [US3] Document installing dependencies, running tests and adding a dependency in `README.md`, `docs/handbook/07-common-tasks.md` and `docs/handbook/04-architecture.md`

**Checkpoint**: User Stories 1 and 3 are in place.

---

## Phase 5: User Story 2 - A broken change is not deployed (Priority: P1)

**Goal**: A failing test or an invalid template stops the pipeline.

**Independent Test**: Quickstart Scenario C.

### Implementation for User Story 2

- [X] T020 [US2] Run the tests before the image is built, in the same job, so a failure stops packaging, in `.github/workflows/main.yml` and `.github/workflows/branch.yml`
- [X] T021 [US2] Run the tests before AWS credentials are assumed, so they cannot call AWS, in `.github/workflows/main.yml` and `.github/workflows/branch.yml`
- [X] T022 [US2] Make `deploy` depend on both build jobs in `.github/workflows/main.yml` and `.github/workflows/branch.yml`
- [X] T023 [US2] Set up Python with `ServerlessOpsIO/gha-setup-python@v1` and run `pipenv run test-unit`, with `test` and `test-unit` defined under `[scripts]`, in `.github/workflows/main.yml`, `.github/workflows/branch.yml` and `Pipfile`

**Checkpoint**: User Stories 1 to 3 are in place.

---

## Phase 6: User Story 4 - Changes to documents alone do not deploy (Priority: P3)

**Goal**: Pushes that touch only specifications or documentation do not run the pipeline.

**Independent Test**: Quickstart Scenario E.

### Implementation for User Story 4

- [X] T024 [US4] Ignore `specs/**` and `docs/**` in the push triggers in `.github/workflows/main.yml` and `.github/workflows/branch.yml`
- [X] T025 [P] [US4] Document that such pushes do not run the workflows in `docs/handbook/00-index.md`

**Checkpoint**: All four user stories are in place.

---

## Phase 7: Outstanding at Backfill

**Purpose**: Things the specification asks for that were not done or not checked when this
list was written. None of these is started.

- [ ] T026 [US1] Run quickstart Scenario B on a branch and record the result (SC-002) in `specs/004-build-and-delivery/quickstart.md`
- [ ] T027 [US2] Run quickstart Scenario C with a failing test and with an invalid template, and record the results (SC-003), in `specs/004-build-and-delivery/quickstart.md`
- [ ] T028 [US3] Run the local image build and compare the image's packages with the lock (SC-007) in `specs/004-build-and-delivery/quickstart.md`
- [ ] T029 [US3] Run quickstart Scenario D and record the result (SC-008) in `specs/004-build-and-delivery/quickstart.md`
- [ ] T030 [US4] Run quickstart Scenario E and record the result (SC-005) in `specs/004-build-and-delivery/quickstart.md`
- [ ] T031 [US3] Remove `src/agent/.dockerignore`, which is no longer read
- [ ] T032 Decide each item under "Open Points" in `specs/004-build-and-delivery/spec.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1 and on feature 001's agent code.
- **Phase 3 (US1)**: Depends on Phase 2.
- **Phase 4 (US3)**: Changes the image definition and the build step from Phases 2 and 3.
- **Phase 5 (US2)**: T023 depends on Phase 4's `Pipfile`.
- **Phase 6 (US4)**: Depends on Phase 3's workflows.
- **Phase 7 (Outstanding)**: T026, T027, T029 and T030 each need a pushed branch.

### User Story Dependencies

- **US1 (P1)**: Needs the foundation.
- **US2 (P1)**: A set of ordering rules inside US1's jobs.
- **US3 (P2)**: Changes how US1 packages the agent and how US2 installs for tests.
- **US4 (P3)**: A trigger setting on US1's workflows.
