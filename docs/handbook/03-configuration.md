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

5. **Slack secrets, for STRIDEr.** Two SecureString parameters in Parameter Store hold the
   Slack signing secret and bot token. Create them before the stack that answers Slack is
   deployed; see [STRIDEr Slack messaging](09-slack-messaging.md#first-time-setup).
6. **The hosted zone.** The Parameter Store parameter `/org/dns/ZoneId` must hold the ID of
   the Route 53 hosted zone for `sandbox.serverlessops.io`, in the deployment account.

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
| `MaxPromptChars` | `16000` | Longest prompt the agent accepts. Raised from the default so a Slack thread's earlier messages fit. It applies to every caller of the agent. |
| `Hostname` | `engineering-agents.sandbox.serverlessops.io` | Hostname Slack sends events to |
| `DnsZoneId` | `/org/dns/ZoneId` | Name of the Parameter Store parameter holding the hosted zone's ID |

These parameters have defaults in `template.yaml`. Add them to `cfn-parameters.json` to
override one:

| Parameter | Default | Purpose |
| --- | --- | --- |
| `MaxPromptChars` | `4000` | Longest prompt accepted |
| `LogLevel` | `INFO` | Agent log level |
| `MemoryEventExpiryDays` | `7` | Days a conversation's messages are kept. Also how old a Slack thread may be before STRIDEr asks for a new one. |
| `SlackSigningSecretParameter` | `/engineering-agents/slack/signing-secret` | Name of the SecureString parameter holding the Slack signing secret |
| `SlackBotTokenParameter` | `/engineering-agents/slack/bot-token` | Name of the SecureString parameter holding the Slack bot token |

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
or as SecureString parameters in Parameter Store, and grant the role that needs them
permission to read them. The two Slack parameters above hold names, not secrets.

## Slack secrets in AWS

The Slack receiving service reads two secrets when it runs. You create them by hand; the
template never holds their values.

| Parameter Store name | Read by | Used for |
| --- | --- | --- |
| `/engineering-agents/slack/signing-secret` | `ReceiveSlackEvent` | Checking that a request came from Slack |
| `/engineering-agents/slack/bot-token` | `AnswerSlackMessage`, `CleanUpSlackMessage` | Every call to Slack |

Each is read again every five minutes, so a replaced value is in use within five minutes
with no deployment. See
[Replacing a secret](09-slack-messaging.md#replacing-a-secret).

## Slack app values

The `Slack app` workflow uses these repository-level GitHub values. None of them is in
`cfn-parameters.json`, and nothing in the template reads them: the receiving service reads
its own copies of the signing secret and bot token from Parameter Store, above. How each is created is in
[The STRIDEr Slack app](08-slack-app.md#first-time-setup).

| Name | Kind | Written by | Read by |
| --- | --- | --- | --- |
| `SLACK_SERVICE_TOKEN` | Secret | You | The `Slack app` workflow |
| `SLACK_GHA_STORE_TOKEN` | Secret | You | The `create` job of the `Slack app` workflow |
| `SLACK_APP_ID` | Variable | The creation run | The `Slack app` workflow |
| `SLACK_SIGNING_SECRET` | Secret | The creation run | Nothing yet. Its copy in Parameter Store is what the receiving service reads. |
| `SLACK_CLIENT_ID` | Secret | The creation run | Nothing yet |
| `SLACK_CLIENT_SECRET` | Secret | The creation run | Nothing yet |
| `SLACK_BOT_TOKEN` | Secret | You, after installing the app | The `Slack app` workflow |

The signing secret and the bot token are therefore in two places: here, and in Parameter
Store. When one changes, change both. Only the `Slack app` workflow calls Slack's app
definition service.

## Tags

`cfn-tags.json` sets `org:domain`, `org:system` and `org:component` on the stack's resources.
The deploy action adds `org:repo`, `org:branch` and `org:stackName`.
