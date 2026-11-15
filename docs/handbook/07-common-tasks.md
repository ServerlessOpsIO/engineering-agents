# Common tasks

## Validate and deploy changes

```bash
pipenv install --dev
pipenv run test-unit
sam validate --lint
```

Push the branch. The `Branches` workflow tests, builds and deploys a stack for it. Merge to
`main` to deploy the `main` stack.

## Run the agent locally

Needs AWS credentials that can invoke the model.

```bash
cd src/agent
MODEL_ID=us.anthropic.claude-haiku-5-5 pipenv run python main.py
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

Edit `src/agent/system_prompt.md`. Add a test to `tests/unit/test_prompt.py` for each rule the
prompt must keep.

## Change the model

Set `ModelId` in `cfn-parameters.json`. Use an inference profile ID of the form
`<scope>.<provider>.<model>`. The execution role's permission follows the parameter. Confirm the deployment account has access to the model first.

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
