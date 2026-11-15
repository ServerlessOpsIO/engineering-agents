# Configuration

## Deployment prerequisites

Do these once before the first deployment.

1. **Model access.** The deployment account must have access to the configured model in Amazon
   Bedrock. Some models are not open to every account, and the first use of a provider's models
   in an account may need a one-time form. Check in the Bedrock console.
2. **Transaction Search.** Enable CloudWatch Transaction Search in the deployment account and
   region. Without it the agent's traces are not delivered. This is an account-level setting,
   so it is not in the template.
3. **Image registry secret.** The `AWS_ECR_REPO` secret must be available to this repository.
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
| `ModelId` | `us.anthropic.claude-haiku-5-5` | Bedrock inference profile the agent uses |

These parameters have defaults in `template.yaml`. Add them to `cfn-parameters.json` to
override one:

| Parameter | Default | Purpose |
| --- | --- | --- |
| `MaxPromptChars` | `4000` | Longest prompt accepted |
| `LogLevel` | `INFO` | Agent log level |
| `MemoryEventExpiryDays` | `7` | Days a conversation's messages are kept |

`ModelId` has no default in `template.yaml`, so it must be set in `cfn-parameters.json`. It
must have the form `<scope>.<provider>.<model>`, such as `us.anthropic.claude-haiku-5-5`. The
execution role's model permission is built from it.

The `us.` profile routes requests to `us-east-1`, `us-east-2` and `us-west-2`. The
organization's region restrictions must allow Bedrock model invocation in all three, or
requests fail with `AccessDeniedException`.

## Environment variables

The runtime passes these to the agent: `MODEL_ID`, `MAX_PROMPT_CHARS`, `LOG_LEVEL` and
`MEMORY_ID`. Add more under `EnvironmentVariables` in `template.yaml`.

`MODEL_ID` is required. The agent has no fallback model and does not start without it.

Do not put secrets in environment variables or parameters. Store them in AWS Secrets Manager
and grant the execution role permission to read them.

## Tags

`cfn-tags.json` sets `org:domain`, `org:system` and `org:component` on the stack's resources.
The deploy action adds `org:repo`, `org:branch` and `org:stackName`.
