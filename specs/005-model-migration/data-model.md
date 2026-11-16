# Phase 1 Data Model: OpenAI Model Migration

Nothing stored changes in this feature. The entities are settings and the permissions built
from them.

## Entity: ModelSetting

The deployment parameter `ModelId`, passed to the agent as `MODEL_ID`.

| Attribute | Value |
|---|---|
| New value | `us.openai.gpt-6-luna` |
| Previous value | `us.anthropic.claude-haiku-5-5` |
| Set in | `cfn-parameters.json` (no default in `template.yaml`) |
| Form | A United States inference profile ID. Must start with `us.`; the rest may contain dots. |
| Required | Yes. The agent does not start without `MODEL_ID`. |

### Validation Rules

- Must match `^us\.[a-zA-Z0-9.:_-]+$`. A value that does not start with `us.` is refused at
  deployment.
- The value is used as given to name the inference profile.
- A value that starts with `us.` but is not a usable inference profile deploys, and fails at
  the first request.

## Entity: ReasoningEffortSetting

A new deployment parameter `ReasoningEffort`, passed to the agent as `REASONING_EFFORT`.

| Attribute | Value |
|---|---|
| Allowed values | `default`, `none`, `low`, `medium`, `high`, `xhigh`, `max` |
| Default | `default` |
| Set in | `template.yaml` default; override in `cfn-parameters.json` |
| Meaning of `default`, empty or unset | Nothing is sent. The model uses its own default (medium for GPT-6 Luna). |
| Meaning of any other value | Sent to the model as its reasoning effort. |

### Validation Rules

- A value outside the allowed list is refused at deployment by the parameter's allowed
  values.
- The agent does not check the value against the configured model. A level the model does
  not accept fails the request with the standard error reply, and the failure detail entry
  shows the service's message.

## Entity: ModelPermission

The `Model` statement of `AgentExecutionRole`. Actions `bedrock:InvokeModel` and
`bedrock:InvokeModelWithResponseStream`.

| Resource | Built from | For `us.openai.gpt-6-luna` |
|---|---|---|
| Inference profile | `ModelId` | `inference-profile/us.openai.gpt-6-luna` in this account and region |
| Default project (new) | account and region | `project/default` in this account and region |
| Any foundation model, any region, only through that profile | a condition on `bedrock:InferenceProfileArn` | `foundation-model/*`, conditioned on the profile above |

### Validation Rules

- A foundation model can be used only through the configured inference profile.
- Changing `ModelId` changes the profile resource and the condition on the next deployment,
  with no other edit.

## Entity: InferenceProfile

Owned by the service. Read-only for this project.

| Attribute | Value |
|---|---|
| ID | `us.openai.gpt-6-luna` |
| Source region | `us-east-1` |
| Destination regions | `us-east-1`, `us-east-2`, `us-west-2` |

## Entity: TemplateFormValues

The values a developer chooses when creating a project from
`backstage-aws-agentcore-template`.

| Field | Default after this feature | Goes to |
|---|---|---|
| `model_id` | `us.openai.gpt-6-luna` | `ModelId` in the new project's `cfn-parameters.json` |
| `reasoning_effort` (new) | `default` | `ReasoningEffort` in the new project's `cfn-parameters.json` |

## Relationships

- One ModelSetting determines the profile resource and the condition in ModelPermission.
- One ModelSetting names one InferenceProfile.
- ReasoningEffortSetting is independent of ModelSetting. It is not reset when the model
  changes.
- TemplateFormValues become the ModelSetting and ReasoningEffortSetting of a new project.

## State Transitions

How the reasoning effort reaches a request:

1. `ReasoningEffort` parameter → `REASONING_EFFORT` environment variable, at deployment.
2. `REASONING_EFFORT` → read once, when the agent module loads.
3. Unset, empty or `default` → the model client is created with no extra request fields.
4. Any other value → the model client is created with the reasoning effort field, and every
   request from that agent process carries it.

A changed value takes effect when a new agent process starts, which a deployment causes.
