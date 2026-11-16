# CI/CD pipeline

## Workflow triggers

| Workflow | Automatic trigger | Manual trigger |
| --- | --- | --- |
| `.github/workflows/main.yml` (`Main`) | Push to `main` | `workflow_dispatch` |
| `.github/workflows/branch.yml` (`Branches`) | Push to any branch except `main` | `workflow_dispatch` |
| `.github/workflows/slack-app.yml` (`Slack app`) | Push to any branch that changes a Slack file; once a day | `workflow_dispatch` with an action |

Pushes that change only `specs/**` or `docs/**` do not run `Main` or `Branches`. There is no
`pull_request` trigger.

## Jobs

`Main` and `Branches` run the same three jobs. **Both deploy**: every branch that runs the workflow
gets its own stack.

### `build_infra`

Runs `sam validate --lint` and `sam build`, then stores the template artifact for the deploy
job.

### `build_container`

Runs on an arm64 runner (`ubuntu-24.04-arm`), because AgentCore Runtime runs arm64 images and
this builds one without emulation.

1. `ServerlessOpsIO/gha-setup-python@v1` installs Python 3.14, `pipenv` and the packages in
   the `Pipfile`. `pipenv run test-unit` then runs the unit tests. A failing test stops the
   image build and the deployment.
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

## The Slack app workflow

`Slack app` keeps the STRIDEr Slack app in step with `slack/manifest.yaml`. It is a separate
workflow from `Main` and `Branches`: neither waits for, blocks or cancels the other, and a
commit shows a failed check if either fails. What it manages and how to repair it is in
[The STRIDEr Slack app](08-slack-app.md).

### When it runs

The Slack files are `slack/**`, `scripts/slack_app/**` and the workflow file itself.

| Trigger | Jobs |
| --- | --- |
| Push to a branch other than `main` that changes a Slack file | `check` |
| Push to `main` that changes a Slack file | `check`, `apply`, `report` |
| Once a day | `check`, `apply`, `report` |
| Started by hand on `main` with the action `apply` | `check`, `apply`, `report` |
| Started by hand on `main` with the action `create` | `check`, `create`, `report` |

A push that changes no Slack file does not start it, so it does not contact Slack. A merge
that changes only Slack files still starts `Main`, which builds and deploys the agent as for
any other change.

### Jobs

| Job | What it does | Changes Slack |
| --- | --- | --- |
| `check` | Checks the app definition offline, then asks Slack to validate it. The Slack step skips itself when the credential is not available. | Never |
| `apply` | Makes the recorded app match the definition, then fails if the installed app lacks a permission in it. | Updates the app |
| `create` | Creates the app and stores its values. Refuses while the recorded app exists. | Creates an app |
| `report` | After a failed scheduled run, opens an issue labelled `slack-app-failure` or comments on the open one. After `apply` or `create` passes, closes it. | Never |

`apply` and `create` run only on `main`. `report` is a job of its own so that it still runs
when `check` fails and `apply` is skipped.

### One run at a time

Each job that contacts Slack renews the Slack credential, and the old one stops working. The
workflow is therefore in one concurrency group, `slack-app`, that queues runs and cancels
none in progress. GitHub keeps at most one run waiting in a group: if a third starts while
one runs and one waits, the waiting one is cancelled in favour of the newest.

### Secrets in logs

GitHub masks stored secrets in logs. Values obtained during a run, such as the renewed
credential and a new app's signing secret, are masked by the program before anything else is
printed. Run summaries and issues are built from a fixed list of messages and never from a
response, because this repository's logs and issues are public.
