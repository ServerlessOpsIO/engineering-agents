# Request Record Contract

**Backfill**: Read from `src/agent/main.py` and `docs/handbook/06-observability.md` at commit
`fd37671`.

## Scope

The log record the agent writes for each request. Anything that reads the agent's logs (a
person, a query, a dashboard, a forwarder) can rely on this contract.

## Transport

- **Destination**: standard output of the agent container, delivered by AgentCore Runtime to
  the CloudWatch log group `/aws/bedrock-agentcore/runtimes/<AgentRuntimeId>-DEFAULT`.
- **Format**: one JSON object per line, with no prefix or suffix.
- **Other lines**: the log group also receives lines that are not request records, such as
  stack traces and output from libraries. A reader MUST skip lines that are not JSON objects
  with a `kind` field.

## Record Contract

- A record MUST validate against `request-record.schema.json`.
- One record is written per request that reaches the agent's handler, when the handler
  finishes.
- `requestId` equals the `requestId` in the reply to the same request.

## Behavioral Contract

1. A record MUST NOT contain prompt text or reply text. Lengths, counts, identifiers, outcomes
   and durations are allowed.
2. `modelId` is present only when the request passed the input checks.
3. `inputTokens` and `outputTokens` are present only for `answer`, and may be `null`.
4. `errorType` is present only for `error`.
5. New fields may be added. A reader MUST ignore fields it does not know.
6. A field's meaning MUST NOT change without a change to this contract.

## What Has No Record

- A request rejected by the service because the caller has no permission.
- A request whose body is not valid JSON.

## Adding a Field

Keep prompt and reply text out. Add the field to `request-record.schema.json`, to
`docs/handbook/06-observability.md`, and to the assertions in `tests/unit/test_main.py`.
