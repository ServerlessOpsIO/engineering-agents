# Implementation Plan: Build and Delivery

**Branch**: `plan/004-build-and-delivery` | **Date**: 2026-11-15 | **Spec**: `specs/004-build-and-delivery/spec.md`

**Input**: Feature specification from `specs/004-build-and-delivery/spec.md`

**Backfill**: This plan was written after the feature was built. It records the design that is
in the code on `main` (commit `fd37671`), not a design made in advance.

## Summary

Two GitHub Actions workflows, `main.yml` for `main` and `branch.yml` for every other branch,
run three jobs: `build_infra` validates and builds the SAM template, `build_container` runs
the unit tests and then builds and pushes the agent's arm64 image to Amazon ECR, and `deploy`
deploys the stack `<repository>-<branch slug>` with the image tagged by the commit SHA.
Dependencies are declared in a `Pipfile` at the repository root and locked in `Pipfile.lock`.
The image installs only the runtime packages, at the locked versions. The workflows use the
organization's shared actions, including `ServerlessOpsIO/gha-setup-python@v1` for Python and
pipenv.

## Technical Context

**Language/Version**: Python 3.14 for the agent and its tests. YAML for the workflows and the
SAM template.

**Primary Dependencies**:

- Dependency management: `pipenv`, `Pipfile`, `Pipfile.lock`
- Shared actions: `ServerlessOpsIO/gha-setup-workspace@v2`,
  `ServerlessOpsIO/gha-setup-python@v1`, `ServerlessOpsIO/gha-assume-aws-credentials@v1`,
  `ServerlessOpsIO/gha-store-artifacts@v2`, `ServerlessOpsIO/gha-deploy-aws-sam@v1`
- Other actions: `aws-actions/setup-sam@v3`, `kciter/aws-ecr-action@v4`
- AWS SAM CLI (`sam validate --lint`, `sam build`)
- Base image: `public.ecr.aws/docker/library/python:3.14-slim`

**Storage**: Amazon ECR repository `<owner>/<repository>` in the CI/CD account for images. The
SAM build artifact is stored between jobs by `gha-store-artifacts`.

**Testing**: `pytest` 9.2.0 through the Pipfile scripts `test-unit` (`pytest -vv tests/unit`)
and `test` (`pytest -vv tests`). `sam validate --lint` for the template, with `.cfnlintrc`
ignoring `E3034`.

**Target Platform**: GitHub Actions runners: `ubuntu-latest` for `build_infra` and `deploy`,
`ubuntu-24.04-arm` for `build_container`. Deployment to the AWS account in
`DEPLOYMENT_ACCOUNT_ID`.

**Project Type**: Single service (one agent container) with its infrastructure in a SAM
template.

**Performance Goals**: A push to `main` is tested, packaged and deployed within 15 minutes
(SC-004). The one observed run took about 6 minutes.

**Constraints**:

- AgentCore Runtime runs arm64 images, so the image is built on an arm64 runner without
  emulation.
- The runtime name `<component>_<branch>` must be 48 characters or fewer.
- The Docker build context is the repository root, because the Dockerfile copies `Pipfile` and
  `Pipfile.lock`. `.dockerignore` limits the context to those files and `src/agent/`.
- Pushes that change only `specs/**` or `docs/**` do not run the workflows.
- Every deployment uses the GitHub environment `production`.

**Scale/Scope**: One repository, one image, one stack per deployed branch.

## Constitution Check

Not performed. `.specify/memory/constitution.md` is still the unfilled Spec Kit template, so
there are no principles to check this plan against. This is an open item for the project
owner.

## Project Structure

### Documentation (this feature)

```text
specs/004-build-and-delivery/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── pipeline-contract.md
├── checklists/
│   ├── requirements.md
│   └── delivery.md
├── catalog-info.yaml
└── tasks.md
```

### Source Code (repository root)

```text
Pipfile                          # [packages], [dev-packages], [scripts], python_version
Pipfile.lock                     # Exact versions
.dockerignore                    # Limits the build context
src/agent/Dockerfile             # arm64 image, locked runtime packages, non-root user
src/agent/.dockerignore          # No longer read; see the specification's open points
.github/workflows/
├── main.yml                     # Pushes to main
├── branch.yml                   # Pushes to other branches
└── ecr-policy.json              # Lets the organization's accounts pull the image
template.yaml                    # The stack; ContainerRepo/Org/Image/Tag parameters
cfn-parameters.json              # Parameter values resolved by the deploy action
cfn-tags.json                    # Resource tags
samconfig.toml                   # Stack name prefix and capabilities
.cfnlintrc                       # Lint settings
pytest.ini                       # Test paths
tests/unit/                      # The tests the pipeline runs
docs/handbook/                   # 03-configuration, 05-ci-cd, 07-common-tasks
```

**Structure Decision**: The pipeline is two near-identical workflow files, one per trigger,
following the organization's project templates. They differ only in their trigger and in
`main.yml` also pushing the `latest` image tag.

## Complexity Tracking

Nothing recorded. With no constitution in force there are no violations to justify.
