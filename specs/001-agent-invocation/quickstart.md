# Quickstart: Validate Agent Invocation

This guide checks the feature against its specification. Scenarios A to C can be run today.
Scenarios D and E need a second AWS identity or a deployment, and had not been run when this
was written (2026-11-15).

## Prerequisites

1. Python 3.14 and `pipenv`.
2. For the deployed scenarios: AWS credentials for the deployment account with
   `bedrock-agentcore:InvokeAgentRuntime` on the runtime, and
   `cloudformation:DescribeStacks` on the stack.
3. The `main` stack deployed (`engineering-agents-main`).

## Automated Checks

```bash
pipenv install --dev
pipenv run test-unit
sam validate --lint
```

Expected outcomes:

- 11 tests pass. None of them calls AWS.
- The template validates with no errors.

## Find the Deployed Agent

```bash
export AGENT_RUNTIME_ARN=$(aws cloudformation describe-stacks \
  --stack-name engineering-agents-main \
  --query "Stacks[0].Outputs[?OutputKey=='AgentRuntimeArn'].OutputValue" --output text)
```

## Scenario A: Send a Prompt and Get a Reply (User Story 1)

```bash
pipenv run python scripts/invoke.py "What can you do?"
```

Expected:

- The command prints a JSON reply with `"kind": "answer"`, some `text` and a `requestId`.
- The exit code is 0.

## Scenario B: Unusable Prompts Are Refused (User Story 2)

```bash
pipenv run python scripts/invoke.py ""
pipenv run python scripts/invoke.py "   "
pipenv run python scripts/invoke.py "$(python3 -c 'print("x" * 4001)')"
pipenv run python scripts/invoke.py "$(python3 -c 'print("x" * 4000)')"
```

Expected:

- The first two print `"kind": "input_rejection"` with the text `Please send a prompt.`
- The third prints `"kind": "input_rejection"` with a text that states the 4,000 character
  limit.
- The fourth prints `"kind": "answer"`.
- The exit code is 1 for the three rejections.
- The log records for the three rejections have no `modelId` and no token counts (see
  feature 003's quickstart for how to read them).

## Scenario C: Failures Are Clear and Reveal Nothing (User Story 3)

This is covered by the unit test `test_a_failure_returns_a_generic_error`, which forces an
exception containing the words "secret internal detail".

```bash
pipenv run pytest -vv tests/unit/test_main.py -k failure
```

Expected:

- The test passes: the response has status 500, `kind` is `error`, the text is the fixed
  message, and the forced detail is absent from the body.

There is no documented way to force a failure in a deployed agent.

## Scenario D: A Caller Without Access Is Rejected (User Story 1, scenario 3)

1. Assume a role in the deployment account that does not have
   `bedrock-agentcore:InvokeAgentRuntime` on the runtime.
2. Run the command from Scenario A.

Expected:

- The call fails with `AccessDeniedException`. No reply body is returned.
- No log record for the request appears in the agent's log group.

## Scenario E: Changed Instructions Take Effect (User Story 4)

1. On a branch, edit `src/agent/system_prompt.md` so the change is easy to see in a reply (for
   example, add "End every reply with the word DONE.").
2. Push the branch and wait for its stack, `engineering-agents-<branch slug>`, to deploy.
3. Set `AGENT_RUNTIME_ARN` from that stack and run the command from Scenario A.
4. Delete the branch's stack when finished:
   `aws cloudformation delete-stack --stack-name engineering-agents-<branch slug>`.

Expected:

- The reply follows the edited instructions.

## Run the Agent Locally

Needs AWS credentials that can invoke the model. Memory is off locally, because `MEMORY_ID` is
not set.

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

## Acceptance Checks Not Covered Above

- SC-005 (a developer can do Scenario A in under 5 minutes from the documentation): time a
  person who has not done it before.
- SC-006 (no usage-based cost over 24 idle hours): compare the account's cost data for the
  runtime across a day with no requests.
