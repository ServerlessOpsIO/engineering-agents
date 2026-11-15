# Pipeline Contract

**Backfill**: Read from `.github/workflows/main.yml`, `.github/workflows/branch.yml`,
`cfn-parameters.json` and `docs/handbook/05-ci-cd.md` at commit `fd37671`.

## Scope

What the pipeline needs from the repository and the organization, and what it promises in
return. A change to either workflow MUST keep `main.yml` and `branch.yml` in step, and MUST
update this contract.

## Triggers

| Workflow | Runs on | Does not run on |
|---|---|---|
| `Main` (`main.yml`) | Push to `main`; manual start | Pushes that change only `specs/**` or `docs/**` |
| `Branches` (`branch.yml`) | Push to any other branch; manual start | Pushes that change only `specs/**` or `docs/**` |

## Jobs

| Job | Runner | Steps, in order | Blocks `deploy` when |
|---|---|---|---|
| `build_infra` | `ubuntu-latest` | Set up workspace; assume AWS credentials; install SAM; `sam validate --lint`; `sam build`; store artifacts | The template is invalid or does not build |
| `build_container` | `ubuntu-24.04-arm` | Set up workspace; set up Python and install dependencies; `pipenv run test-unit`; assume AWS credentials; build and push the image | A test fails, or the image does not build |
| `deploy` | `ubuntu-latest` | Set up workspace from the artifact; assume AWS credentials; deploy with SAM | Not applicable |

`deploy` needs both build jobs and uses the GitHub environment `production`.

## Inputs the Pipeline Requires

### From the organization

| Name | Kind | Purpose |
|---|---|---|
| `AWS_CICD_ACCOUNT_ID` | Secret | Account that holds the image repository and build role |
| `AWS_ECR_REPO` | Secret | Registry host of the image repository |
| `ServerlessOpsIO/gha-*` actions | Shared actions | Workspace, Python, credentials, artifacts, deployment |

### From the repository

| Name | Kind | Purpose |
|---|---|---|
| `DEPLOYMENT_ACCOUNT_ID` | Secret | Account the stack is deployed to |
| `Pipfile`, `Pipfile.lock` | Files at the root | Dependencies for the tests and the image |
| `[scripts] test-unit` in `Pipfile` | Named command | What the pipeline runs as the tests |
| `src/agent/Dockerfile`, `.dockerignore` | Files | The image definition and its build context |
| `template.yaml`, `cfn-parameters.json`, `cfn-tags.json`, `samconfig.toml` | Files | The stack and its settings |

### One-time prerequisites

Documented in `docs/handbook/03-configuration.md`: model access in the deployment account,
CloudWatch Transaction Search, and the `AWS_ECR_REPO` secret.

## What the Pipeline Produces

1. An image in `<owner>/<repository>` tagged with the branch slug, the short SHA and the full
   SHA, and with `latest` on `main`.
2. A stack named `<repository>-<branch slug>` running the image tagged with the full SHA.
3. The stack outputs `AgentRuntimeArn`, `AgentRuntimeId` and `AgentMemoryId`.

## Behavioral Contract

1. Nothing is deployed unless both the template check and the tests pass.
2. The tests run before AWS credentials are assumed in `build_container`, so they cannot call
   AWS.
3. The deployed image is always the one built from the same commit.
4. A branch's deployment never changes another branch's deployment.
5. The image contains only `[packages]`, at the versions in `Pipfile.lock`.
6. The image build fails when `Pipfile.lock` does not match `Pipfile`.

## Security Contract

- The pipeline gets AWS credentials by assuming roles through GitHub's identity token
  (`id-token: write`). No long-lived AWS keys are stored in the repository.
- The image repository's policy allows pulls only from principals in the organization.
- Secrets MUST NOT be written to `cfn-parameters.json` as literal values. They are referenced
  as `$secrets.<NAME>`.

## Known Limits

- A branch whose name makes `<component>_<branch>` longer than 48 characters fails to deploy.
- Deleting a branch does not delete its stack.
- The test stage does not fail on a stale `Pipfile.lock`. Only the image build does.
