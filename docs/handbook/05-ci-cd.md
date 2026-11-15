# CI/CD pipeline

## Workflow triggers

| Workflow | Automatic trigger | Manual trigger |
| --- | --- | --- |
| `.github/workflows/main.yml` (`Main`) | Push to `main` | `workflow_dispatch` |
| `.github/workflows/branch.yml` (`Branches`) | Push to any branch except `main` | `workflow_dispatch` |

Pushes that change only `specs/**` or `docs/**` do not run either workflow. There is no
`pull_request` trigger.

## Jobs

Both workflows run the same three jobs. **Both deploy**: every branch that runs the workflow
gets its own stack.

### `build_infra`

Runs `sam validate --lint` and `sam build`, then stores the template artifact for the deploy
job.

### `build_container`

Runs on an arm64 runner (`ubuntu-24.04-arm`), because AgentCore Runtime runs arm64 images and
this builds one without emulation.

1. Installs Python 3.14 and the packages in `Pipfile.lock` with `pipenv`, then runs `pytest`.
   A failing test stops the image build and the deployment.
2. `kciter/aws-ecr-action@v4` builds `src/agent/Dockerfile` with the repository root as the
   context, creates the ECR repository `<owner>/<repository>` in the CI/CD account if needed,
   pushes the tags below, and applies `.github/workflows/ecr-policy.json`.

| Workflow | Image tags pushed |
| --- | --- |
| `main.yml` | `latest`, branch slug, short SHA, full SHA |
| `branch.yml` | branch slug, short SHA, full SHA |

### `deploy`

Needs both build jobs and uses the GitHub environment `production`.
`ServerlessOpsIO/gha-deploy-aws-sam@v1` deploys the stack `<repository>-<branch slug>` to the
account in `DEPLOYMENT_ACCOUNT_ID`, resolving `cfn-parameters.json` and `cfn-tags.json`.

The deployment always uses the **full commit SHA** tag. A new tag per commit is what makes
CloudFormation see a change and publish a new runtime version, so every deploying commit
publishes one, including commits that do not change the agent.

## Branch stacks

A branch deployment creates a separate runtime and memory named after the branch.

- The runtime name `<component>_<branch>` must be 48 characters or fewer. A longer branch name
  fails the deployment.
- Nothing deletes a branch's stack when the branch is deleted. Remove it yourself:

  ```bash
  aws cloudformation delete-stack --stack-name <repository>-<branch slug>
  ```

- Images accumulate in the ECR repository; there is no lifecycle policy.
- The image is not patched automatically. A rebuild picks up the current base image.
