# Model Settings Contract

## Scope

The deployment settings that choose the agent's model and how much it reasons, and what the
project promises about them. This is the interface a project owner uses to change the model.
The invoke interface (feature 001) and the request record (feature 003) are not changed by
this feature.

## Settings

Both are CloudFormation parameters of `template.yaml`, given values in
`cfn-parameters.json`.

| Parameter | Required | Default in template | Value in `cfn-parameters.json` | Environment variable |
|---|---|---|---|---|
| `ModelId` | Yes | None | `us.openai.gpt-6-luna` | `MODEL_ID` |
| `ReasoningEffort` | No | `default` | `default` | `REASONING_EFFORT` |

### `ModelId`

- A United States Bedrock inference profile ID. It must start with `us.`, for example
  `us.openai.gpt-6-luna` or `us.openai.gpt-6.1-terra`. The rest of the ID is not checked.
- Anything else is refused at deployment: `global.` and other non-US profiles, and
  in-Region model IDs with no profile such as `openai.gpt-oss-120b-1:0`. The limit keeps the
  agent off profiles that the organization's region restriction denies.

### `ReasoningEffort`

- One of `default`, `none`, `low`, `medium`, `high`, `xhigh`, `max`.
- `default` sends nothing and leaves the choice to the model.

## Behavioral Contract

1. Changing either setting needs only an edit to `cfn-parameters.json` and a deployment. No
   code change.
2. The execution role's model permission is rebuilt from `ModelId` on every deployment. It
   allows the configured inference profile, and foundation models only when reached
   through that profile.
8. A `ModelId` that starts with `us.` but is not a usable inference profile is not caught
   at deployment. Requests fail with the standard error reply until it is corrected.
3. The agent does not start without `MODEL_ID`. It starts normally without
   `REASONING_EFFORT`.
4. The agent has no fallback model and no fallback reasoning effort of its own.
5. `REASONING_EFFORT` is read once per agent process. A new value applies after the
   deployment that sets it.
6. A reasoning effort the configured model does not accept does not stop the agent from
   starting. Requests fail with the standard error reply until the setting is corrected.
7. The request record's `modelId` is the value of `ModelId`.

## Prerequisites Outside This Contract

For `us.openai.gpt-6-luna`:

- The deployment account has access to OpenAI GPT-6 Luna in Amazon Bedrock.
- The organization allows Bedrock model invocation in `us-east-1`, `us-east-2` and
  `us-west-2`.

When either is missing, requests fail with `kind: error` and `errorType:
AccessDeniedException`. The failure detail entry that follows the record tells them apart:

| Cause | Text in the failure detail entry |
|---|---|
| No access to the model | `is not available for this account` |
| A region is restricted | `with an explicit deny in a service control policy` |

## Template Form Contract

In `backstage-aws-agentcore-template`, the creation form supplies both settings to a new
project:

| Form field | Default | Becomes |
|---|---|---|
| Model | `us.openai.gpt-6-luna` | `ModelId` in the new project's `cfn-parameters.json` |
| Reasoning effort | `default` | `ReasoningEffort` in the new project's `cfn-parameters.json` |

A project created with the defaults has the same two settings, the same role statement and
the same handbook text as this project.
