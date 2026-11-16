# Quickstart: Validate the OpenAI Model Migration

This guide checks the feature against its specification. Nothing in it had been run when it
was written (2026-11-15).

## Prerequisites

1. Python 3.14 and `pipenv`, with `pipenv install --dev` done.
2. The AWS SAM CLI.
3. AWS credentials for the deployment account that can invoke the runtime, read the stack,
   read its role's policy and read CloudWatch Logs.
4. In the deployment account: access to OpenAI GPT-6 Luna in Amazon Bedrock, and Bedrock
   model invocation allowed in `us-east-1`, `us-east-2` and `us-west-2`.
5. The `main` stack deployed with this feature.

Check prerequisite 4 first. In the Bedrock console's model catalog, in `us-east-1`, open
GPT-6 Luna and confirm the account can use it.

## Automated Checks

```bash
pipenv run test-unit
sam validate --lint
```

Expected outcomes:

- All tests pass with no AWS credentials, including the new tests for the reasoning effort
  setting.
- The template validates with no errors.

## Find the Deployed Agent

```bash
export AGENT_RUNTIME_ARN=$(aws cloudformation describe-stacks \
  --stack-name engineering-agents-main \
  --query "Stacks[0].Outputs[?OutputKey=='AgentRuntimeArn'].OutputValue" --output text)
```

## Scenario A: The Agent Answers Using GPT-6 Luna (User Story 1)

```bash
pipenv run python scripts/invoke.py "What can you do?"
```

Expected:

- The reply has `"kind": "answer"`.
- The request's log record (see feature 003's quickstart for how to find it) has
  `"modelId": "us.openai.gpt-6-luna"` and token counts.

Repeat with at least 10 different prompts for SC-001.

## Scenario B: Nothing Changes for Callers (User Story 2)

Run Scenarios A and B of `specs/001-agent-invocation/quickstart.md`, and Scenarios A to C of
`specs/002-conversation-memory/quickstart.md`.

Expected:

- Every result is as those guides state.

## Scenario C: The Role Covers This Model Only (User Story 3)

```bash
ROLE=$(aws cloudformation describe-stack-resource --stack-name engineering-agents-main \
  --logical-resource-id AgentExecutionRole \
  --query StackResourceDetail.PhysicalResourceId --output text)
aws iam get-role-policy --role-name "$ROLE" --policy-name AgentRuntime \
  --query "PolicyDocument.Statement[?starts_with(Sid, 'Model')]"
```

Expected:

- One statement allows `inference-profile/us.openai.gpt-6-luna` and `project/default`.
- One statement allows `foundation-model/*` with a condition that
  `bedrock:InferenceProfileArn` is the ARN of `inference-profile/us.openai.gpt-6-luna`.
- Nothing names `anthropic`, and no foundation model is allowed without the condition.

## Scenario D: Reasoning Effort Is a Setting (FR-013)

1. With `"ReasoningEffort": "default"`, send 10 prompts and note each record's
   `outputTokens` and `durationMs`.
2. On a branch, set `"ReasoningEffort": "low"` in `cfn-parameters.json`, push, and wait for
   the branch's stack to deploy.
3. Set `AGENT_RUNTIME_ARN` from that stack and send the same 10 prompts.
4. Delete the branch's stack when finished.

Expected:

- Every request is answered. This also confirms the request field the plan chose for
  reasoning effort.
- The average `outputTokens` is lower at `low` than at `default` (SC-010).

## Scenario E: A Missing Prerequisite Is Diagnosable (User Story 4)

Only run this where a prerequisite is actually missing. Do not remove access to create the
condition.

1. Send a prompt and note the `requestId` of the error reply.
2. Find the failure detail entry for that request in the agent's log group.

Expected:

- The reply is the standard error and says nothing about the cause.
- The failure detail entry contains `is not available for this account`, or `with an
  explicit deny in a service control policy`, matching the missing prerequisite.

Both texts were seen in this deployment's logs on 2026-11-15, for the previous model.

## Scenario F: Go Back (User Story 5)

1. On a branch, set `"ModelId": "us.anthropic.claude-haiku-5-5"`, push, and wait for the
   branch's stack.
2. Run Scenario C against that stack.
3. Delete the branch's stack when finished.

Expected:

- The role's profile resource and its condition name `us.anthropic.claude-haiku-5-5` and no
  longer name `us.openai.gpt-6-luna`.
- A prompt is answered if the account has access to that model. On 2026-11-15 it did not, so
  an error with `is not available for this account` is the expected result here until that
  changes.

## Scenario G: The Template Produces the Same Settings (User Story 6)

Without Backstage, render the skeleton with its default values and compare:

1. In `backstage-aws-agentcore-template`, substitute the default form values into
   `skeleton/cfn-parameters.json`, `skeleton/template.yaml` and
   `skeleton/src/agent/main.py`.
2. Compare each with the same file in this project.

Expected:

- The model and reasoning effort settings, the `Model` statement and the agent's handling of
  both environment variables are the same. The only differences are the project's own names.

With Backstage, create a project from the template with the default choices and run
Scenario A against it (SC-011).

**Result, 2026-11-15 (without Backstage)**: the skeleton was rendered with the default form
values, memory enabled and this project's names. `cfn-parameters.json`, `template.yaml`,
`src/agent/main.py`, `tests/conftest.py`, `tests/unit/test_main.py` and
`docs/handbook/07-common-tasks.md` were identical to this project's files. The handbook's
configuration and observability pages differed only where the skeleton describes the regions
and the model in general terms. In the rendered copy, all 18 unit tests passed and
`sam validate --lint` reported a valid template. No project was created through Backstage.

## Reported, Not Pass or Fail

- SC-003: review the replies to at least 10 prompts typical of the agent's use and record
  how many are acceptable.
- SC-004: from the `durationMs` of those requests, record how many replies took 30 seconds
  or less.
