# Feature Specification: Build and Delivery

**Feature Branch**: `spec/004-build-and-delivery`

**Created**: 2026-11-15

**Status**: Implemented (backfilled)

**Input**: User description: "Build and delivery: every change pushed to the repository is tested, packaged and deployed automatically, with each branch getting its own deployment. A change that fails its tests or has an invalid infrastructure definition is not deployed. The agent's dependencies are declared in one file at the root of the project, split into what the agent needs to run and what is needed only to test it, with exact versions locked. The pipeline uses the organization's shared pipeline actions, the same ones its Python and container project templates use."

**Backfill**: This specification was written on 2026-11-15, after the feature was built. It
describes the code on `main` at commit `fd37671`, which includes two changes made on
2026-11-14 at the project owner's request: moving dependencies to a single file at the
project root, and aligning the pipeline with the organization's project templates. The
Bill-GN project has no specification for this; its constitution's "Everything as Code" and
"Tested" principles are the nearest source. The project owner has not reviewed or clarified
this specification.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A pushed change is tested, built and deployed (Priority: P1)

A developer pushes a change. Without doing anything else, they get the change tested,
packaged and running in a deployment of its own, where they can try it.

**Why this priority**: This is how every change reaches a running agent. Nothing is deployed
by hand.

**Independent Test**: Push a branch with a small change and confirm a separate deployment for
that branch exists afterwards, running that change, while the `main` deployment is untouched.

**Acceptance Scenarios**:

1. **Given** a change pushed to a branch other than `main`, **When** the pipeline finishes,
   **Then** a deployment named after that branch is running that change.
2. **Given** a change merged to `main`, **When** the pipeline finishes, **Then** the `main`
   deployment is running that change.
3. **Given** two branches, **When** both are deployed, **Then** each has its own agent and its
   own remembered conversations, and neither affects the other or `main`.
4. **Given** a deployed change, **When** an operator asks which change a deployment is
   running, **Then** the answer is one exact commit.

---

### User Story 2 - A broken change is not deployed (Priority: P1)

A developer pushes a change that fails a test or breaks the infrastructure definition. The
pipeline stops, and the running deployment stays as it was.

**Why this priority**: Automatic deployment is safe only if a failing change cannot get
through.

**Independent Test**: Push a branch with a failing test and confirm nothing is packaged or
deployed. Repeat with an invalid infrastructure definition.

**Acceptance Scenarios**:

1. **Given** a change with a failing test, **When** the pipeline runs, **Then** the agent is
   not packaged and nothing is deployed.
2. **Given** a change with an invalid infrastructure definition, **When** the pipeline runs,
   **Then** nothing is deployed.
3. **Given** the tests, **When** they run, **Then** they need no cloud credentials and make no
   call to the model.

---

### User Story 3 - Dependencies are declared once and locked (Priority: P2)

A developer adds or updates a dependency in one file at the root of the project. Their own
machine, the pipeline and the running agent then all use the same versions.

**Why this priority**: When versions differ between a developer's machine and the running
agent, a change that passed its tests can still fail in use.

**Independent Test**: Add a dependency to the file, update the locked versions, and confirm
the tests and the packaged agent both use the newly locked version. Then change the file
without updating the locked versions and confirm packaging fails.

**Acceptance Scenarios**:

1. **Given** the project, **When** a developer looks for its dependencies, **Then** they find
   one file at the project root, with the dependencies the agent runs on listed separately
   from those used only for testing.
2. **Given** the locked versions, **When** the agent is packaged, **Then** it contains exactly
   those versions of the dependencies it runs on, and none of the test-only dependencies.
3. **Given** the dependency file has changed and the locked versions have not been updated,
   **When** the agent is packaged, **Then** packaging fails.
4. **Given** a fresh copy of the project, **When** a developer follows the documented steps,
   **Then** they can install the dependencies and run the tests with two commands.

---

### User Story 4 - Changes to documents alone do not deploy (Priority: P3)

A developer pushes a change that touches only specifications or documentation. Nothing is
built or deployed.

**Why this priority**: Specification and planning work happens on branches of its own. It
should not create deployments or publish new versions of the agent.

**Independent Test**: Push a branch that changes only a specification and confirm the
pipeline does not run.

**Acceptance Scenarios**:

1. **Given** a change that touches only the specifications or the documentation, **When** it
   is pushed, **Then** the pipeline does not run.
2. **Given** a change that touches a specification and the agent's code, **When** it is
   pushed, **Then** the pipeline runs.

---

### Edge Cases

- The first pipeline run in a new project: it fails until the documented one-time
  prerequisites are met (access to the model, the account's tracing setup, and access to the
  image registry).
- A branch whose name makes the deployment's name too long (more than 48 characters with the
  component name): the deployment fails.
- A branch is deleted: its deployment stays. Nothing removes it, and the documentation gives
  the manual step.
- A commit that does not change the agent: it still publishes a new version of the agent,
  because each deployment is tied to its commit.
- The locked versions are out of date when the tests run in the pipeline: the pipeline
  resolves the dependencies again and the tests run against the result. Packaging then fails
  (User Story 3, scenario 3), so nothing is deployed.
- The pipeline is started by hand on a branch: it runs as it would for a push.
- Every deployment, including a branch's, goes to the same account and under the same
  approval settings as `main`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every push that changes anything other than specifications and documentation
  MUST start the pipeline. A push that changes only specifications or documentation MUST NOT.
- **FR-002**: The pipeline MUST run the project's automated tests, and MUST NOT package or
  deploy the agent when a test fails.
- **FR-003**: The pipeline MUST check the infrastructure definition, and MUST NOT deploy when
  the check fails.
- **FR-004**: The automated tests MUST run without cloud credentials and MUST NOT call the
  model.
- **FR-005**: The pipeline MUST package the agent for the processor type the hosting platform
  runs, and MUST store the package where the deployment account can retrieve it and accounts
  outside the organization cannot.
- **FR-006**: Each package MUST be labelled with the exact commit it was built from, and each
  deployment MUST run the package for its own commit.
- **FR-007**: Each branch MUST be deployed separately, under a name derived from the branch,
  with its own agent and its own remembered conversations. `main` MUST have a deployment of
  its own.
- **FR-008**: All infrastructure MUST be defined in the repository, and deployments MUST
  happen only through the pipeline.
- **FR-009**: The agent's dependencies MUST be declared in one file at the root of the
  project. The file MUST separate the dependencies the agent runs on from those needed only
  to test or operate it.
- **FR-010**: Exact versions of every dependency MUST be locked in a file kept in the
  repository, and MUST be used by developers, the pipeline and the packaged agent.
- **FR-011**: The packaged agent MUST contain only the dependencies it runs on, at the locked
  versions. Packaging MUST fail when the locked versions do not match the dependency file.
- **FR-012**: The packaged agent MUST run as an unprivileged user.
- **FR-013**: The pipeline MUST use the organization's shared pipeline actions wherever one
  exists for a step, so that this project is set up and tested the same way as the
  organization's Python and container projects.
- **FR-014**: The project MUST define named commands for running its tests, and the pipeline
  MUST run the tests through them.
- **FR-015**: Credentials the pipeline needs MUST be held as managed secrets and MUST NOT be
  in the repository.
- **FR-016**: The documentation MUST describe how to run the tests, how to add a dependency,
  what each stage of the pipeline does, the one-time prerequisites, and how to remove a
  branch's deployment.

### Key Entities

- **Pipeline**: The automated sequence that tests, packages and deploys a pushed change.
- **Deployment**: One running copy of the agent and its resources, for one branch.
- **Package**: The built agent, labelled with the commit it came from.
- **Dependency file**: The single declaration of what the agent runs on and what is needed
  only for testing.
- **Locked versions**: The exact version of every dependency, kept with the dependency file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of pushes to `main` that pass their tests result in the `main` deployment
  running that commit, with no manual step.
- **SC-002**: 100% of pushes to another branch that pass their tests result in a separate
  deployment for that branch, and 0 of them change the `main` deployment.
- **SC-003**: 100% of pushes with a failing test or an invalid infrastructure definition
  result in no new package being deployed.
- **SC-004**: A push to `main` is tested, packaged and deployed within 15 minutes.
- **SC-005**: 0 pushes that change only specifications or documentation start the pipeline.
- **SC-006**: A developer with a fresh copy of the project can install its dependencies and
  run its tests in under 5 minutes using the documented steps.
- **SC-007**: A comparison of the dependencies in the packaged agent with the locked versions
  finds no difference, and finds no test-only dependency in the package.
- **SC-008**: 100% of attempts to package the agent with locked versions that do not match
  the dependency file fail.

### Verification status at backfill

- SC-001 and SC-004 have one supporting result: the pipeline run for commit `fd37671` on
  `main` on 2026-11-15 succeeded in about 6 minutes. The run before it, for the project's
  first commit, did not deploy.
- SC-006 was done once on a developer's machine on 2026-11-14: the dependencies installed and
  all 11 tests passed.
- SC-002, SC-003, SC-005, SC-007 and SC-008 have not been tested. No branch other than `main`
  has been pushed with code changes, the pipeline has not been run with a failing test, and
  the package's contents have not been inspected. A local build of the package was attempted
  on 2026-11-14 and could not be run.

## Open Points

These were found while writing this specification. Each is a decision for the project owner.

- **The pipeline does not fail on stale locked versions at the test stage.** The shared setup
  action resolves dependencies again when the locked versions are out of date, so tests can
  run against versions nobody committed. Packaging catches it afterwards (FR-011).
- **Branch deployments are never removed automatically.** See the edge cases.
- **No check of the agent's code beyond its tests.** There is no style or static check, and no
  minimum test coverage, unlike the organization's Python project template.
- **Branch deployments share `main`'s account and approval settings.** There is no separate
  place for trying changes.
- **A build-context exclusion file inside the agent's source folder no longer has any
  effect.** The file at the project root replaced it when the dependencies moved.

## Assumptions

- Developers work on a machine with the project's language runtime and its dependency tool
  installed.
- The organization's shared pipeline actions and its secrets for the build and deployment
  accounts exist and are maintained outside this project.
- One person or a small team pushes changes, so pipeline runs rarely overlap.
- The agent's language runtime version is fixed at the version chosen when the project was
  created.
- The 15-minute figure in SC-004 is a starting value, set from the one observed run of about
  6 minutes. The owner has not confirmed it.
- Technology choices are described in the project handbook (`docs/handbook/`). The project
  constitution is still the unfilled Spec Kit template, so nothing here was checked against
  project principles.
