# Configuration

## Deployment prerequisites

Do these once before the first deployment.

1. **Model access.** The deployment account must have access to the configured model, OpenAI
   GPT-6 Luna, in Amazon Bedrock. Some models are not open to every account, and the first
   use of a provider's models in an account may need a one-time step. Check in the Bedrock
   console's model catalog.
2. **Allowed regions.** The inference profile `us.openai.gpt-6-luna` sends each request to
   `us-east-1`, `us-east-2` or `us-west-2`. The organization's region restrictions must allow
   Bedrock model invocation in all three.
3. **Transaction Search.** Enable CloudWatch Transaction Search in the deployment account and
   region. Without it the agent's traces are not delivered. This is an account-level setting,
   so it is not in the template.
4. **Image registry secret.** The `AWS_ECR_REPO` secret must be available to this repository.
   It holds the CI/CD account's registry host, for example
   `123456789012.dkr.ecr.us-east-1.amazonaws.com`.

The `AWS_CICD_ACCOUNT_ID` secret is expected from the organization, and `DEPLOYMENT_ACCOUNT_ID`
was set on this repository when it was created.

## Deployment parameters

`cfn-parameters.json` supplies the template's parameters. The deploy action resolves the
`$env.` and `$secrets.` references when it runs.

| Parameter | Value | Purpose |
| --- | --- | --- |
| `Domain`, `System` | Fixed at creation | Organization identity |
| `Component` | Repository name slug | Start of the runtime name |
| `CodeBranch` | Branch slug | Rest of the runtime name |
| `ContainerRepo` | `AWS_ECR_REPO` secret | Registry host of the agent image |
| `ContainerOrg` | Repository owner slug | First part of the image repository name |
| `ContainerImage` | Repository name slug | Second part of the image repository name |
| `ContainerTag` | Commit SHA | Image tag to run |
| `ModelId` | `us.openai.gpt-6-luna` | Bedrock inference profile the agent uses |
| `ReasoningEffort` | `default` | How much the model reasons before answering |

These parameters have defaults in `template.yaml`. Add them to `cfn-parameters.json` to
override one:

| Parameter | Default | Purpose |
| --- | --- | --- |
| `MaxPromptChars` | `4000` | Longest prompt accepted |
| `LogLevel` | `INFO` | Agent log level |
| `MemoryEventExpiryDays` | `7` | Days a conversation's messages are kept |

`ModelId` has no default in `template.yaml`, so it must be set in `cfn-parameters.json`. It
must be a United States inference profile ID, which starts with `us.`, such as
`us.openai.gpt-6-luna`. Anything else is refused at deployment: global profiles can route to
regions the organization does not allow. The rest of the ID is not checked, so a mistyped
value deploys and then fails at the first request.

The execution role's model permission follows `ModelId`. The role may call that inference
profile, and may reach a foundation model only through it.

`ReasoningEffort` is one of `default`, `none`, `low`, `medium`, `high`, `xhigh` and `max`.
`default` sends nothing and leaves the choice to the model, which is medium for GPT-6 Luna.
Reasoning is billed as output, so a lower level costs less and answers sooner. A level the
configured model does not accept makes requests fail until it is corrected.

## Environment variables

The runtime passes these to the agent: `MODEL_ID`, `REASONING_EFFORT`, `MAX_PROMPT_CHARS`,
`LOG_LEVEL` and `MEMORY_ID`. Add more under `EnvironmentVariables` in `template.yaml`.

`MODEL_ID` is required. The agent has no fallback model and does not start without it.
`REASONING_EFFORT` is optional; without it the model uses its own default.

Do not put secrets in environment variables or parameters. Store them in AWS Secrets Manager
and grant the execution role permission to read them.

## Slack app values

The `Slack app` workflow uses these repository-level GitHub values. None of them is in
`cfn-parameters.json`, and nothing in the template reads them yet. How each is created is in
[The STRIDEr Slack app](08-slack-app.md#first-time-setup).

| Name | Kind | Written by | Read by |
| --- | --- | --- | --- |
| `SLACK_SERVICE_TOKEN` | Secret | You | The `Slack app` workflow |
| `SLACK_GHA_STORE_TOKEN` | Secret | You | The `create` job of the `Slack app` workflow |
| `SLACK_APP_ID` | Variable | The creation run | The `Slack app` workflow; the later feature |
| `SLACK_SIGNING_SECRET` | Secret | The creation run | The later feature |
| `SLACK_CLIENT_ID` | Secret | The creation run | The later feature |
| `SLACK_CLIENT_SECRET` | Secret | The creation run | The later feature |
| `SLACK_BOT_TOKEN` | Secret | You, after installing the app | The `Slack app` workflow; the later feature |

The later feature, which deploys the service that receives Slack events, reads
`SLACK_APP_ID`, `SLACK_SIGNING_SECRET`, `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET` and
`SLACK_BOT_TOKEN`. It must not write them and must not call Slack's app definition service;
only the `Slack app` workflow does.

## Tags

`cfn-tags.json` sets `org:domain`, `org:system` and `org:component` on the stack's resources.
The deploy action adds `org:repo`, `org:branch` and `org:stackName`.
