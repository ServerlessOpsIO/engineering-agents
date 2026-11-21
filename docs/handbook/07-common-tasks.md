# Common tasks

## Validate and deploy changes

```bash
pipenv install --dev
pipenv run test-unit
sam validate --lint
```

Push the branch. The `Branches` workflow tests and builds it; it does not deploy at present
(issue #10). Merge to `main` to deploy the `main` stack.

## Run the agent locally

Needs AWS credentials that can invoke the model.

```bash
cd src/agent
MODEL_ID=us.openai.gpt-6-luna pipenv run python main.py
```

In another terminal:

```bash
curl -s localhost:8080/ping
curl -s -X POST localhost:8080/invocations \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "What can you do?"}'
```

## Ask the deployed agent

```bash
export AGENT_RUNTIME_ARN=$(aws cloudformation describe-stacks \
  --stack-name <repository>-<branch slug> \
  --query "Stacks[0].Outputs[?OutputKey=='AgentRuntimeArn'].OutputValue" --output text)

uv run --with boto3 scripts/invoke.py "What can you do?"
```

## Change the agent's instructions

Who the agent is and the rules that always hold are in `src/agent/persona.md`; add a test to
`tests/unit/test_prompt.py` for each rule it must keep. How it carries out a task is in a
skill under `src/agent/skills/`. A rule that code enforces is in `src/agent/session/`.
[Threat modelling sessions](10-threat-model-sessions.md) says how to change each and how to
check the change.

## Play the fixed threat modelling session

```bash
export AGENT_RUNTIME_ARN=<as above>
pipenv run play-session
```

See [Threat modelling sessions](10-threat-model-sessions.md#playing-the-fixed-session).

## Change the model

Set `ModelId` in `cfn-parameters.json` and deploy. It must be a United States inference
profile ID, which starts with `us.`; global profiles are refused because the organization's
region restriction denies them. The execution role's permission follows the parameter.
Confirm the deployment account has access to the model first.

The rest of the ID is not checked. A mistyped value that still starts with `us.` deploys and
then fails at the first request.

## Change how much the model reasons

Set `ReasoningEffort` in `cfn-parameters.json` and deploy. The values are `default`, `none`,
`low`, `medium`, `high`, `xhigh` and `max`. `default` leaves the choice to the model.
Reasoning is billed as output, so lower levels cost less and answer sooner.

## Give the agent a tool

Write a function with the Strands `@tool` decorator and pass it to `Agent(tools=[...])` in
`build_agent` in `src/agent/main.py`. If the tool calls an AWS service, add a statement to
`AgentExecutionRole` in `template.yaml` scoped to the resources it uses.

## Grant a caller access

Give the caller's role `bedrock-agentcore:InvokeAgentRuntime` on the stack's `AgentRuntimeArn`
output.

## Add a dependency

Add it, pinned, to `[packages]` in the `Pipfile`. Use `[dev-packages]` for tools that are not
needed in the image. Then run `pipenv lock` and commit `Pipfile.lock` with the `Pipfile`.

## Continue or separate conversations

Requests that share a `runtimeSessionId` and `actorId` continue one conversation. Send a new
session ID to start a new one. Messages expire after `MemoryEventExpiryDays`.
