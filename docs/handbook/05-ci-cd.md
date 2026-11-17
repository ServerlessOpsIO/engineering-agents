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

`Main` and `Branches` have the same three jobs. **Only `Main` deploys at present.** The
`deploy` job in `Branches` is switched off with `if: false`, because it fails for branches
with long names (issue #10). Branch pushes still run the tests and build the image.

### `build_infra`

Installs Python 3.14, runs `sam validate --lint` and `sam build`, then stores the template
artifact for the deploy job. `sam build` also packages the three Lambda functions in `src/handlers/`, each with what
its own `requirements.txt` lists and the shared code in `src/common/`. The functions are
deployed only by `Main`: they exist in the `main` stack and no other.

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

Branch deployments are switched off at present (issue #10). When they are on, a branch
deployment creates a separate runtime and memory named after the branch.

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
| `check` | Checks the app definition offline, then asks Slack to validate it. The Slack steps are skipped when the credential is not available. | Never |
| `apply` | Asks Slack for the recorded app to confirm it exists, updates it to match the definition, sets its icon, then fails if the installed app lacks a permission in it. | Updates the app |
| `create` | Creates the app and stores its values. Refuses while the recorded app exists. | Creates an app |
| `report` | After a failed scheduled run, opens an issue labelled `slack-app-failure` or comments on the open one. After `apply` or `create` passes, closes it. | Never |

`apply` and `create` run only on `main`. `report` is a job of its own so that it still runs
when `check` fails and `apply` is skipped.

### Who calls Slack

The two everyday calls, validating and updating, are made by Slack's own GitHub Action,
`slackapi/slack-github-action`, pinned to the commit of v4.0.0. The project's program,
`pipenv run slack-app`, does what the action cannot:

| Step | Done by | Why |
| --- | --- | --- |
| Offline check; build the request | Program (`check`, `prepare`) | Slack's schema, this project's rules, and holding events back until there is an address. |
| `apps.manifest.validate`, `apps.manifest.export`, `apps.manifest.update` | Slack's action | |
| Read Slack's answer | Program (`result`; `create` for its own check) | Turns the answer into one failure kind with what to do, which also feeds the failure issue. For `export` it tells a deleted app apart from an outage, so nothing recreates an app by mistake. |
| Set the app's icon | Program (`icon`) | The action cannot upload a file. |
| Check installed permissions | Program (`verify`) | Needs a response header the action does not return. |
| `apps.manifest.create`, and storing the app's values | Program (`create`) | Slack's answer holds the app's secrets, and the action would expose the whole answer as a step output. The check before it, whether the recorded app still exists, goes through the action. |

The action's step passes even when Slack rejects the call; the "Read Slack's answer" step
that follows is the one that fails. Only the error fields of Slack's answer are passed to
it, never the whole answer, because a step's inputs are shown in its log. The one exception
is the manifest that `apps.manifest.export` returns, which holds no secrets and is passed on
so that a change made outside the pipeline can be reported.

### One run at a time

The workflow is in one concurrency group, `slack-app`, that queues runs and cancels none in
progress, so two updates to the app never overlap and the later one wins. GitHub keeps at
most one run waiting in a group: if a third starts while one runs and one waits, the waiting
one is cancelled in favour of the newest.

### Credentials

Jobs that contact Slack use `SLACK_SERVICE_TOKEN`, a Slack CLI service token that does not
expire and is never rewritten. Only the `create` job writes to GitHub, using
`SLACK_GHA_STORE_TOKEN`. See [Credentials and when they expire](08-slack-app.md#credentials-and-when-they-expire).

### Secrets in logs

GitHub masks stored secrets in logs. Values obtained during a run, such as a new
app's signing secret, are masked by the program before anything else is
printed. Run summaries and issues are built from a fixed list of messages and never from a
response, because this repository's logs and issues are public.

Do not re-run the `Slack app` workflow with **Enable debug logging**. Debug logging prints
every step output, and the action's output after an update is Slack's whole answer, which
may hold the app's secrets.
