# Phase 0 Research: Build and Delivery

**Backfill**: These decisions were read from the code, its comments, the project handbook and
the commit history on 2026-11-15. Decisions 1 to 5 were made on 2026-11-14 at the project
owner's direction, and their rationale is what the owner asked for. For the rest, a rationale
is cited where the repository records one. Where it does not, this file says "not recorded"
and does not guess. Alternatives are listed only where one was actually replaced or
considered.

## Decision 1: Declare dependencies in a Pipfile at the repository root

- **Decision**: One `Pipfile` at the root, with runtime packages under `[packages]` and test
  and script tools under `[dev-packages]`, locked in `Pipfile.lock`.
- **Rationale**: The project owner's stated preference (2026-11-14): a Pipfile over
  requirements files, living in the root of the project. It also matches the organization's
  Python project template.
- **Alternatives considered**: Two requirements files, `src/agent/requirements.txt` and
  `requirements-dev.txt`. This is what the project was generated with, and what Decision 1
  replaced (commit `869a43f`).

## Decision 2: Build the image from the repository root

- **Decision**: The Docker build context is the repository root. A root `.dockerignore` admits
  only `Pipfile`, `Pipfile.lock` and `src/agent/`.
- **Rationale**: A consequence of Decision 1. The Dockerfile has to copy the Pipfile, which is
  outside `src/agent/`.
- **Alternatives considered**: Keeping `src/agent/` as the context and generating a
  requirements file in the pipeline before the build. Rejected because the image build would
  then depend on a file that is not in the repository, and a local build would not work.

## Decision 3: Install into the image from the lock, and fail if it is stale

- **Decision**: The Dockerfile runs `pipenv install --system --deploy`, then removes pipenv.
- **Rationale**: `--deploy` makes the build fail when `Pipfile.lock` does not match the
  `Pipfile`, so the image never contains versions nobody committed. `--system` avoids a
  virtual environment inside the image. Development packages are not installed.

## Decision 4: Use the organization's shared Python setup action

- **Decision**: `ServerlessOpsIO/gha-setup-python@v1` installs Python, pipenv and the
  project's dependencies in the `build_container` job.
- **Rationale**: The project owner asked (2026-11-14) for the workflows to be aligned with the
  actions used by the organization's Python and ECS project templates. The Python template
  uses this action.
- **Alternatives considered**: `actions/setup-python` with hand-written pipenv steps, which
  installed with `--deploy`. Replaced in commit `fd37671`. The shared action installs without
  `--deploy`, so the test stage no longer fails on a stale lock. This is listed in the
  specification's open points.

## Decision 5: Run tests through named Pipfile scripts

- **Decision**: `[scripts]` defines `test` and `test-unit`. The workflows run
  `pipenv run test-unit`.
- **Rationale**: The Python project template's workflow calls `pipenv run test-unit`. The
  template's scripts also enforce a coverage threshold; these do not, because `pytest-cov` is
  not a dependency here.

## Decision 6: Build on an arm64 runner

- **Decision**: `build_container` runs on `ubuntu-24.04-arm`.
- **Rationale**: Workflow comment: "AgentCore Runtime runs arm64 images, so the image is built
  on an arm64 runner."

## Decision 7: Take the base image from ECR Public

- **Decision**: `FROM public.ecr.aws/docker/library/python:3.14-slim`.
- **Rationale**: Dockerfile comment: "to avoid Docker Hub pull limits in CI".

## Decision 8: Deploy the image by its full commit SHA

- **Decision**: Images are tagged with the branch slug, the short SHA and the full SHA
  (`main` adds `latest`). `ContainerTag` is always the full SHA.
- **Rationale**: Handbook, `05-ci-cd.md`: "A new tag per commit is what makes CloudFormation
  see a change and publish a new runtime version."

## Decision 9: One stack per branch

- **Decision**: The deploy action deploys `<repository>-<branch slug>`, and the template names
  the runtime and memory after the component and branch.
- **Rationale**: Not recorded. It is the organization's convention in its project templates.

## Decision 10: Skip the pipeline for specification and documentation changes

- **Decision**: Both workflows have `paths-ignore` for `specs/**` and `docs/**`.
- **Rationale**: Handbook, `00-index.md`: pushes that change only those paths "do not run
  them". The reason is not written down there. It lets Spec Kit work happen on branches
  without creating deployments.

## Decision 11: Run the image as a non-root user

- **Decision**: The Dockerfile creates the user `agent` (UID 1000) and switches to it.
- **Rationale**: Not recorded.

## Decision 12: Let the organization's accounts pull the image

- **Decision**: `ecr-policy.json` allows pull actions to any principal in the organization.
- **Rationale**: Template comment: "The image repository is in the CI/CD account", while the
  runtime runs in the deployment account, so it must pull across accounts.

## Open questions found during backfill

- Nothing deletes a branch's stack when the branch is deleted.
- `src/agent/.dockerignore` is no longer read, since Decision 2.
- A local image build was attempted on 2026-11-14 and could not be run, because no container
  engine was available. The build has only been run by the pipeline.
- Why branch deployments use the `production` environment is not recorded.
