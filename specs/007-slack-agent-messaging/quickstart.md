# Quickstart: Validating STRIDEr Slack Messaging

**Date**: 2026-11-16 | **Spec**: `specs/007-slack-agent-messaging/spec.md`

How to prove the feature works. Scenario A needs nothing but a checkout. The rest need
the deployed `main` stack and the `serverlessops` Slack workspace, and can only be run by
the owner. Interfaces are in `contracts/slack-events.md`; records in `data-model.md`.

Record the result of each scenario at the end of this file when it is run.

## Prerequisites

- `pipenv install --dev`
- For B onward: admin of the `serverlessops` workspace; AWS access to the deployment
  account; the `gh` and `aws` commands signed in.
- For H: a guest account in the workspace, or a channel shared with another organisation.
  Skip H and say so if neither exists.

## A. Unit tests (no AWS, no Slack)

```bash
pipenv run test-unit
```

Expected: all tests pass, including the agent's and the Slack app's existing tests
(FR-043, FR-044, SC-014).

## B. First-time setup (US3; SC-007, SC-015)

Follow `docs/handbook/09-slack-messaging.md` and nothing else. Time it. The steps, for
reference:

1. Create the two parameters. Each command prompts for the value:

   ```bash
   read -rs VALUE && aws ssm put-parameter --type SecureString \
     --name /engineering-agents/slack/signing-secret --value "$VALUE"; unset VALUE
   read -rs VALUE && aws ssm put-parameter --type SecureString \
     --name /engineering-agents/slack/bot-token --value "$VALUE"; unset VALUE
   ```

2. Merge the change. Expected: **Main** passes and the stack has the output
   `SlackEventsUrl`. **Slack app** fails with "install again" (expected; `research.md`,
   Decision 14).
3. In the app's settings in Slack, verify the event address. Expected: verified on the
   first try (SC-007). This also proves the signature check works on a real request.
4. Install the app again. Compare the bot token with the stored one; store it again if it
   changed.
5. Run **Slack app** by hand with `apply`. Expected: passes.
6. Add STRIDEr to a test channel.

Expected overall: under 30 minutes of the owner's time (SC-015).

## C. A mention gets a reply (US1; SC-001, SC-018)

In the test channel, post `@STRIDEr what is two plus two?`.

Expected: eyes on the message within 5 seconds; a reply in a thread under it; the eyes
gone within 5 seconds of the reply. Post a message with no mention: nothing happens
(SC-005).

In the front door's log, find the record for this mention and note `durationMs`.
Expected: under 3000, and under 1000 once the function is warm (SC-008).

Also note, for `research.md` O9: whether adding and removing the reaction notified you,
and for O12: read the thread while the eyes are on a message, and note whether the
reaction and who added it are in what Slack returns.

## D. Forged requests are rejected (US2; SC-006)

```bash
URL=https://engineering-agents.sandbox.serverlessops.io/slack/events
BODY='{"type":"event_callback","event":{"type":"app_mention","user":"U0","channel":"C0","ts":"1.1","text":"hi"}}'
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$URL" -H 'Content-Type: application/json' -d "$BODY"
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$URL" -H 'Content-Type: application/json' \
  -H "X-Slack-Request-Timestamp: $(date +%s)" -H 'X-Slack-Signature: v0=00' -d "$BODY"
```

Expected: `401` twice. Nothing appears in Slack and the worker's log has no new record.
A correctly signed request more than five minutes old is covered by the unit tests; it
cannot be made by hand without the signing secret.

## E. A conversation in a thread (US4; SC-003, SC-004, SC-017)

1. Post `@STRIDEr my project is called Heron. Remember that.` Wait for the reply.
2. In the thread, with no mention: `What is my project called?` Expected: eyes, then a
   reply naming Heron.
3. In a new top-level message: `@STRIDEr what is my project called?` Expected: it does
   not know.
4. Start a thread with no mention: `We deploy on Fridays.` Reply in it with no mention.
   Expected: nothing visible; the worker's log has `declined` and `not_strider_thread`. Then reply `@STRIDEr when do we deploy?` Expected: a reply saying
   Fridays, which shows it read the thread. Reply again with no mention; expected: an
   answer.
5. Post two messages in one of STRIDEr's threads a second apart. Expected: two replies,
   in order.

## F. A direct message (US5; SC-002)

Send STRIDEr a direct message with no mention. Expected: eyes, then a reply in a thread
under it. Reply in the thread referring to the first message: it remembers. Send a second
top-level message asking about the first: it does not.

## G. Failures (US6; SC-009, SC-010)

1. **Nothing asked**: post `@STRIDEr` alone. Expected: "What would you like help with?"
2. **Too long**: post a mention followed by more than 16,000 characters. Expected: the
   too-long sentence.
3. **The agent fails**: deploy with `ModelId` set to a model that does not exist, on a
   branch of the change if branch deployments are back, otherwise on `main` and reverted
   straight after. **This takes STRIDEr out of service until it is reverted.** Mention
   STRIDEr. Expected: the apology within 5 minutes; the eyes gone;
   the worker's log has a record with `failed` and `agent_failed`; and nothing on the
   held-back queue:

   ```bash
   aws sqs receive-message --visibility-timeout 0 --queue-url "$(aws cloudformation \
     describe-stacks --stack-name engineering-agents --query \
     "Stacks[0].Outputs[?OutputKey=='SlackHeldBackQueueUrl'].OutputValue" --output text)"
   ```

4. **The worker dies**: covered by the unit tests of `CleanUpSlackMessage`. Not run
   against the live stack, because it needs a code change to the worker's timeout.

5. **An old thread**: covered by the unit tests. Run for real only when a thread STRIDEr
   answered in is more than 7 days old: reply there with no mention, expected nothing;
   mention STRIDEr there, expected the start-again sentence. Do not lower
   `MemoryEventExpiryDays` to test this; it also shortens the agent's real memory.

6. **Duplicates**: covered by the unit tests. Also mention STRIDEr inside one of its
   threads and confirm from the logs that the mention arrived as two events and produced
   one reply (`research.md`, O4).

## H. Only full members (SC-019)

As a guest, or from the other organisation in a shared channel, mention STRIDEr. Expected:
no reaction and no reply. The worker's log has a record with `declined` and `not_member`.

## I. Privacy (SC-012, SC-013)

After C to H, search the three log groups (the API's access log and both functions)
for a distinctive word used in a test message, and for the first eight characters of each
secret. Expected: no matches. Confirm both queues are empty.

## Results

| Scenario | Date | Result | Notes |
|----------|------|--------|-------|
| A | | | |
| B | | | |
| C | | | |
| D | | | |
| E | | | |
| F | | | |
| G | | | |
| H | | | |
| I | | | |
