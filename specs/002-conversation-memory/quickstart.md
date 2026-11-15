# Quickstart: Validate Conversation Memory

This guide checks the feature against its specification. None of these scenarios had been run
when this was written (2026-11-15), and the unit tests do not exercise memory.

## Prerequisites

1. Python 3.14 and `pipenv`, with `pipenv install --dev` done.
2. AWS credentials for the deployment account with
   `bedrock-agentcore:InvokeAgentRuntime` on the runtime.
3. The `main` stack deployed, and `AGENT_RUNTIME_ARN` set as in feature 001's quickstart.

Session identifiers must be 33 to 256 characters. Generate one per conversation:

```bash
SESSION_A="quickstart-$(uuidgen)-a"
SESSION_B="quickstart-$(uuidgen)-b"
```

## Scenario A: A Follow-Up Uses the Earlier Exchange (User Story 1)

```bash
pipenv run python scripts/invoke.py --session-id "$SESSION_A" "My name for this test is Alder."
pipenv run python scripts/invoke.py --session-id "$SESSION_A" "What name did I give for this test?"
```

Expected:

- The second reply says Alder.

## Scenario B: Different Conversations Stay Separate (User Story 2)

```bash
pipenv run python scripts/invoke.py --session-id "$SESSION_B" "What name did I give for this test?"
```

Expected:

- The reply does not say Alder. The agent says it has not been given a name.

## Scenario C: Different Askers Stay Separate (User Story 2)

```bash
pipenv run python scripts/invoke.py --session-id "$SESSION_A" --actor-id birch "What name did I give for this test?"
```

Expected:

- The reply does not say Alder, although the session identifier is the one from Scenario A.

## Scenario D: Memory Survives an Idle Agent (User Story 1, scenario 3)

1. Run the first command of Scenario A with a new session identifier.
2. Wait at least 30 minutes. The runtime session ends after 5 idle minutes and cannot outlive
   30 minutes.
3. Run the second command of Scenario A with the same session identifier.

Expected:

- The reply says Alder.

## Scenario E: Messages Expire (User Story 3)

The shortest retention the template allows is 3 days, so this scenario takes more than 3 days.

1. On a branch, add `"MemoryEventExpiryDays": 3` to `cfn-parameters.json`, push, and wait for
   the branch's stack to deploy.
2. Set `AGENT_RUNTIME_ARN` from that stack and run the first command of Scenario A.
3. After more than 3 days, run the second command with the same session identifier.
4. Delete the branch's stack when finished.

Expected:

- The reply does not say Alder.

## Scenario F: Separate Deployments Do Not Share Memory (User Story 2, scenario 3)

1. With a branch stack deployed, run the first command of Scenario A against `main`.
2. Set `AGENT_RUNTIME_ARN` from the branch's stack and run the second command with the same
   session identifier.

Expected:

- The reply does not say Alder.

## Acceptance Checks Not Covered Above

- SC-001 and SC-002 ask for at least 10 dependent exchanges and at least 5 pairs of
  conversations and of askers. Repeat Scenarios A to C with different facts to reach those
  counts.
- SC-005 (records hold conversation identifiers and no message text): read the log records for
  the requests above, as described in feature 003's quickstart, and search them for "Alder".
- What happens when memory is unavailable has no scenario, because there is no documented way
  to make it unavailable.
