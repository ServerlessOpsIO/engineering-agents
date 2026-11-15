# Quickstart: Validate Build and Delivery

This guide checks the feature against its specification. The local checks were run on
2026-11-14, except the local image build, which could not be run. Scenarios B to E had not
been run when this was written (2026-11-15).

## Prerequisites

1. Python 3.14 and `pipenv`.
2. The AWS SAM CLI, for the template check.
3. A container engine (Docker or Podman), for the local image build.
4. Permission to push branches to the repository and to read its Actions runs (`gh` CLI).

## Local Checks

```bash
pipenv install --dev
pipenv run test-unit
pipenv verify
sam validate --lint
```

Expected outcomes:

- The dependencies install from `Pipfile.lock`.
- 11 tests pass.
- `pipenv verify` reports that `Pipfile.lock` is up to date.
- The template validates with no errors.

## Local Image Build

From the repository root:

```bash
docker build -f src/agent/Dockerfile -t engineering-agents:local .
docker run --rm engineering-agents:local pip list
docker run --rm engineering-agents:local whoami
```

Expected outcomes:

- The build succeeds.
- `pip list` shows `strands-agents 1.65.0`, `bedrock-agentcore 1.26.0` and
  `aws-opentelemetry-distro 0.22.0`, and does not show `pytest` or `pipenv`.
- `whoami` prints `agent`.

On a machine that is not arm64, add `--platform linux/arm64` to both commands.

## Scenario A: A Push to `main` Is Tested, Built and Deployed (User Story 1)

After a merge to `main`:

```bash
gh run list --workflow Main --limit 1
aws cloudformation describe-stacks --stack-name engineering-agents-main \
  --query "Stacks[0].Parameters[?ParameterKey=='ContainerTag'].ParameterValue" --output text
```

Expected:

- The run succeeded, with the `build_infra`, `build_container` and `deploy` jobs.
- The stack's `ContainerTag` is the merged commit's full SHA.

Observed once: the run for commit `fd37671` on 2026-11-15 succeeded in about 6 minutes.

## Scenario B: A Branch Gets Its Own Deployment (User Story 1)

1. Create a branch with a short name, change a comment in `src/agent/main.py`, and push.
2. Wait for the `Branches` run to finish.
3. Check both stacks:

   ```bash
   aws cloudformation describe-stacks --stack-name engineering-agents-<branch slug> \
     --query "Stacks[0].StackStatus"
   aws cloudformation describe-stacks --stack-name engineering-agents-main \
     --query "Stacks[0].LastUpdatedTime"
   ```

4. Delete the branch's stack when finished:

   ```bash
   aws cloudformation delete-stack --stack-name engineering-agents-<branch slug>
   ```

Expected:

- The branch's stack exists and is complete.
- The `main` stack's last update time has not changed.

## Scenario C: A Failing Test Stops the Deployment (User Story 2)

1. On a branch, change an assertion in `tests/unit/test_main.py` so it fails, and push.
2. Watch the run: `gh run watch`.

Expected:

- `build_container` fails at "Run tests". "Build container image" does not run.
- `deploy` does not run.
- No stack is created for the branch.

Repeat with an invalid `template.yaml` (for example, a misspelled resource type).

Expected:

- `build_infra` fails at "Validate template", and `deploy` does not run.

## Scenario D: A Stale Lock Stops Packaging (User Story 3)

1. On a branch, add a package to `[packages]` in `Pipfile` without running `pipenv lock`, and
   push.

Expected:

- "Run tests" may pass, because the setup action resolves the dependencies again.
- "Build container image" fails, because `pipenv install --deploy` refuses a lock that does
  not match the `Pipfile`.
- `deploy` does not run.

The same check locally is the image build above, after the same edit.

## Scenario E: A Documentation-Only Push Does Not Run the Pipeline (User Story 4)

1. On a branch, change only a file under `specs/` or `docs/`, and push.
2. List the runs for the branch: `gh run list --branch <branch>`.

Expected:

- No run is listed for that push.

## Acceptance Checks Not Covered Above

- SC-006 (a developer with a fresh copy can install and test in under 5 minutes): time a
  person who has not done it before, using `README.md`.
- SC-007 (the image's packages match the lock, with no test-only packages): compare the full
  `pip list` output from the local image build with the `default` section of `Pipfile.lock`.
