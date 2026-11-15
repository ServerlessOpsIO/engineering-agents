# slack-ai-agent / engineering-agents

AWS AgentCore agents for engineering tasks

An AI agent built with the [Strands Agents SDK](https://strandsagents.com/) and hosted on
[Amazon Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html).
Infrastructure is defined with [AWS SAM](https://aws.amazon.com/serverless/sam/) and deployed by
GitHub Actions.

The [project handbook](docs/handbook/00-index.md) covers features, configuration, architecture,
CI/CD, observability and common tasks. It is also in the component's **Docs** tab in Backstage.

## New Project Getting Started

This repository was generated from a template. Before the first deployment succeeds, complete
the [deployment prerequisites](docs/handbook/03-configuration.md#deployment-prerequisites):

1. The deployment account has access to the configured model in Amazon Bedrock.
2. CloudWatch Transaction Search is enabled in the deployment account and region (for traces).
3. The `AWS_ECR_REPO` secret is available to this repository.

Then make the agent your own:

- **Instructions**: edit [`src/agent/system_prompt.md`](src/agent/system_prompt.md).
- **Behaviour and tools**: edit [`src/agent/main.py`](src/agent/main.py).
- **Infrastructure**: edit [`template.yaml`](template.yaml).

## Run the tests

```bash
pipenv install --dev
pipenv run pytest
sam validate --lint
```

## Ask the deployed agent

```bash
export AGENT_RUNTIME_ARN=$(aws cloudformation describe-stacks \
  --stack-name engineering-agents-main \
  --query "Stacks[0].Outputs[?OutputKey=='AgentRuntimeArn'].OutputValue" --output text)

uv run --with boto3 scripts/invoke.py "What can you do?"
```

Your AWS credentials need `bedrock-agentcore:InvokeAgentRuntime` on the runtime.
