# Phase 1 Data Model: Build and Delivery

**Backfill**: Read from the workflows, `Pipfile`, `src/agent/Dockerfile`, `template.yaml`,
`cfn-parameters.json` and `docs/handbook/05-ci-cd.md` at commit `fd37671`.

Nothing here is application data. These are the things the pipeline produces and the values
that tie them together.

## Entity: DependencyDeclaration

`Pipfile` at the repository root.

| Section | Contents at backfill | Installed in the image |
|---|---|---|
| `[packages]` | `strands-agents ==1.65.0`, `bedrock-agentcore ==1.26.0`, `aws-opentelemetry-distro ==0.22.0` | Yes |
| `[dev-packages]` | `pytest ==9.2.0`, `boto3 *` | No |
| `[scripts]` | `test`, `test-unit` | Not applicable |
| `[requires]` | `python_version = "3.14"` | Not applicable |

## Entity: LockedVersions

`Pipfile.lock`. Exact versions and hashes of every package, direct and indirect, with a hash
of the `Pipfile` it was made from.

### Validation Rules

- The image build fails when the lock's `Pipfile` hash does not match the `Pipfile`
  (`pipenv install --deploy`).
- The pipeline's test stage does not fail in that case. It resolves again.

## Entity: Image

The packaged agent, in the ECR repository `<owner>/<repository>` of the CI/CD account.

| Attribute | Value |
|---|---|
| Architecture | Linux arm64 |
| Base | `public.ecr.aws/docker/library/python:3.14-slim` |
| Contents | Runtime packages at locked versions, and the files in `src/agent/` |
| User | `agent`, UID 1000 |
| Port | 8080 |
| Command | `opentelemetry-instrument python main.py` |

### Tags

| Workflow | Tags pushed |
|---|---|
| `main.yml` | `latest`, branch slug, short SHA, full SHA |
| `branch.yml` | branch slug, short SHA, full SHA |

## Entity: Deployment

One CloudFormation stack per branch.

| Attribute | Value |
|---|---|
| Stack name | `<repository>-<branch slug>` |
| Runtime and memory name | `<Component>_<CodeBranch>`, hyphens as underscores, at most 48 characters |
| Image | The image tagged with the commit's full SHA |
| Account | `DEPLOYMENT_ACCOUNT_ID` |
| GitHub environment | `production`, for every branch |
| Tags | `org:domain`, `org:system`, `org:component`, plus `org:repo`, `org:branch`, `org:stackName` from the deploy action |

## Entity: DeploymentParameters

`cfn-parameters.json`, resolved by the deploy action.

| Parameter | Source |
|---|---|
| `Domain`, `System` | Fixed: `sandbox`, `slack-ai-agent` |
| `Component` | Repository name slug |
| `CodeBranch` | Branch slug |
| `ContainerRepo` | `AWS_ECR_REPO` secret |
| `ContainerOrg` | Repository owner slug |
| `ContainerImage` | Repository name slug |
| `ContainerTag` | Full commit SHA |

`ModelId`, `MaxPromptChars`, `LogLevel` and `MemoryEventExpiryDays` use the template's
defaults unless added to this file.

## Relationships

- One commit produces one Image (with several tags) and one new version of one Deployment.
- One branch has one Deployment.
- One LockedVersions file corresponds to one DependencyDeclaration, and determines the
  packages in every Image built from that commit.

## State Transitions

A pushed commit moves through the pipeline:

1. `pushed` → `skipped`: only `specs/**` or `docs/**` changed.
2. `pushed` → `validated`: `sam validate --lint` and `sam build` succeed (`build_infra`).
3. `pushed` → `tested`: `pipenv run test-unit` succeeds (`build_container`).
4. `tested` → `packaged`: the image is built and pushed.
5. `validated` and `packaged` → `deployed`: the stack is updated (`deploy`).
6. Any step failing → `failed`: later steps in that job do not run, and `deploy` does not run.
