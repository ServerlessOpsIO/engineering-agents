# Quickstart: Validate Observability

This guide checks the feature against its specification. Scenario A's automated check runs
today. The scenarios against the deployed agent had not been run when this was written
(2026-11-15).

## Prerequisites

1. Python 3.14 and `pipenv`, with `pipenv install --dev` done.
2. AWS credentials for the deployment account that can invoke the runtime, read the stack's
   outputs, read CloudWatch Logs and metrics, and read X-Ray traces.
3. The `main` stack deployed, and `AGENT_RUNTIME_ARN` set as in feature 001's quickstart.
4. For Scenario D: CloudWatch Transaction Search enabled in the deployment account and region.

Find the log group:

```bash
RUNTIME_ID=$(aws cloudformation describe-stacks \
  --stack-name engineering-agents-main \
  --query "Stacks[0].Outputs[?OutputKey=='AgentRuntimeId'].OutputValue" --output text)
LOG_GROUP="/aws/bedrock-agentcore/runtimes/${RUNTIME_ID}-DEFAULT"
```

## Automated Checks

```bash
pipenv run test-unit
```

Expected outcomes:

- `test_answers_a_prompt` passes: one record, with `kind`, `sessionId`, token counts and an
  integer `durationMs`.
- `test_a_failure_returns_a_generic_error` passes: the record has `kind` `error` and the
  exception's class name.
- `test_the_request_record_holds_no_prompt_or_reply_text` passes.

## Scenario A: Find One Request From Its Identifier (User Story 1)

1. Send a prompt and note the `requestId` in the reply:

   ```bash
   pipenv run python scripts/invoke.py "What can you do?"
   ```

2. Search the log group for it:

   ```bash
   aws logs filter-log-events --log-group-name "$LOG_GROUP" \
     --filter-pattern '{ $.requestId = "<requestId>" }' \
     --query "events[].message" --output text
   ```

Expected:

- Exactly one record, with `kind` `answer`, a `sessionId`, `promptChars` of 16, a `modelId`,
  `inputTokens`, `outputTokens` and `durationMs`.

Repeat with an empty prompt (`pipenv run python scripts/invoke.py ""`).

Expected:

- Exactly one record, with `kind` `input_rejection`, `promptChars` of 0, and no `modelId` or
  token counts.

## Scenario B: Records Hold No Prompt or Reply Text (User Story 2)

1. Send a prompt with text that will not occur by chance:

   ```bash
   pipenv run python scripts/invoke.py "Repeat this word once: zyzzyva-quickstart"
   ```

2. Search the whole log group for it:

   ```bash
   aws logs filter-log-events --log-group-name "$LOG_GROUP" \
     --filter-pattern '"zyzzyva-quickstart"' --query "length(events)"
   ```

Expected:

- `0`. Any other number means prompt or reply text reached the log group, from the agent or
  from a library.

## Scenario C: The Record Matches the Contract

Save the record from Scenario A to `record.json` and validate it:

```bash
pipenv run python -c "
import json, jsonschema
jsonschema.validate(json.load(open('record.json')),
    json.load(open('specs/003-observability/contracts/request-record.schema.json')))
print('valid')"
```

Expected:

- `valid`.

## Scenario D: A Request Has a Trace (User Story 3)

1. Send a prompt as in Scenario A.
2. In the CloudWatch console, open the trace view for the deployment account and region, and
   find the trace for the time of the request.

Expected:

- A trace exists for the request, and it shows the model call with a duration.
- Check the trace's content for the prompt text and the reply text. The specification's most
  important open point is whether they are there. Record what is found.

## Scenario E: Platform Metrics Count Requests (User Story 4)

1. Note the time, then send a known number of prompts (for example 5).
2. In the CloudWatch console, open the `bedrock-agentcore` metrics for the runtime and read the
   invocation count for that period.

Expected:

- The count matches the number sent.

## Acceptance Checks Not Covered Above

- SC-001 asks for at least 20 requests, including a forced failure. There is no documented way
  to force a failure in a deployed agent, so the failure case is covered only by the unit
  test.
- SC-002 (an operator new to the request can do Scenario A in under 5 minutes): time a person
  using only `docs/handbook/06-observability.md`.
- SC-006 (token counts within 5% of the provider's figures): sum `inputTokens` and
  `outputTokens` over a set of requests and compare with the model's usage metrics in
  CloudWatch for the same period, on a deployment with no other traffic.
