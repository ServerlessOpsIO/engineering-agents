# Phase 0 Research: OpenAI Model Migration

Sources: the AWS model card for GPT-6 Luna, read on 2026-11-15; the source of
`strands-agents` 1.65.0 as installed in this project; and this project's own template and
code. Nothing here was tested against the service. Each decision says what still has to be
confirmed during implementation.

## Decision 1: Keep `BedrockModel` and the Converse API

- **Decision**: Do not change how the agent calls its model. `main.py` keeps
  `BedrockModel(model_id=MODEL_ID)`, which uses ConverseStream on `bedrock-runtime`.
- **Rationale**: The GPT-6 Luna model card lists Converse as supported on `bedrock-runtime`,
  with response streaming. The spec assumes a settings change is enough, and this is the
  path that makes it so.
- **Alternatives considered**: Strands' OpenAI provider pointed at Bedrock's
  OpenAI-compatible endpoint. Rejected: it is a different client and credential flow, and
  its only advantage, single-region inference in `us-east-1`, was declined in clarification.
- **To confirm**: that a ConverseStream call with this profile succeeds from the deployed
  role.

## Decision 2: Use the United States inference profile

- **Decision**: `ModelId` is `us.openai.gpt-6-luna`.
- **Rationale**: The project owner specified it. The model card says the base model ID
  cannot be called in-Region on `bedrock-runtime`; a `us.` or `global.` profile is required.
  From `us-east-1` the US profile routes to `us-east-1`, `us-east-2` and `us-west-2`.
- **Alternatives considered**: `global.openai.gpt-6-luna`, which is about 10% cheaper
  ($0.10 and $0.50 per million tokens against $0.11 and $0.55). Not chosen: it can route to
  any commercial region, which is what the organization's region restriction blocked.

## Decision 3: Tie the role's model permission to the inference profile, and add the default project

- **Decision**: Rewrite the `Model` statement of `AgentExecutionRole` so that it no longer
  builds a foundation-model ARN from parts of `ModelId`. It becomes two statements:
  - Allow `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on the inference
    profile `inference-profile/${ModelId}` in this account and region, and on
    `project/default` in this account and region.
  - Allow the same actions on `foundation-model/*` in any region, only when the request
    comes through that inference profile: a condition on `bedrock:InferenceProfileArn`
    equal to the profile's ARN.
- **Rationale**: With the form of `ModelId` no longer validated (Decision 7), splitting it
  on dots gives a wrong model name for IDs such as `us.openai.gpt-6.1-terra`. The condition
  needs no knowledge of the model's name, so it works for any profile ID. The agent can
  still reach only the model behind its configured profile (FR-006), and the permission
  still follows the setting (FR-007). The default project is added because the model card
  says callers on `bedrock-runtime` need `bedrock:InvokeModel` on "your AWS account's
  default project" as well as the inference profile (FR-005).
- **Alternatives considered**: Keeping the split and accepting that dotted names get wrong
  permissions. Rejected: the deployment would succeed and every request would be denied. A
  second parameter for the foundation model ID. Rejected: two settings to keep in step. A
  wildcard on the provider's models with no condition. Rejected: it breaks FR-006.
- **To confirm**: that the `bedrock:InferenceProfileArn` condition key behaves as described
  for this model. It is from memory of AWS's inference-profile guidance and one search
  summary, not from a page read for this plan. Also whether a Converse call needs the
  default project, which the card states only next to its OpenAI-SDK examples. The first
  deployed request will show both.

## Decision 4: Pass reasoning effort through `additional_request_fields`

- **Decision**: A new deployment parameter `ReasoningEffort`, with allowed values `default`,
  `none`, `low`, `medium`, `high`, `xhigh` and `max`, and default `default`. It reaches the
  agent as `REASONING_EFFORT`. When the value is unset, empty or `default`, the agent builds
  `BedrockModel` exactly as today. Otherwise it adds
  `additional_request_fields={"reasoning": {"effort": <value>}}`.
- **Rationale**: The spec asks for the model's own default unless a setting says otherwise,
  changeable from `cfn-parameters.json` (FR-013). The model card lists those six levels,
  with `medium` as the default. `BedrockModel` sends `additional_request_fields` as
  Converse `additionalModelRequestFields`. The card shows `reasoning.summary` being set that
  way, and an AWS sample and two open-source issue threads report
  `{"reasoning": {"effort": ...}}` as the accepted shape, with a flat `reasoning_effort` key
  rejected.
- **Alternatives considered**: An empty string as "unset". Rejected: the deploy action's
  handling of an empty parameter value is unknown, and `default` is readable in
  `cfn-parameters.json`. Omitting the parameter's default in the template, as was done for
  `ModelId`. Rejected: the spec requires an unset setting to be harmless.
- **To confirm**: the exact field shape. It comes from secondary sources, not from AWS
  documentation. Confirm with one deployed request at `low`.

## Decision 5: Rely on Strands to drop reasoning blocks the model rejects

- **Decision**: Add no code for conversations that began on the previous model (FR-009).
- **Rationale**: `BedrockModel` already removes replayed reasoning blocks that the
  configured model would reject. Its list of such models includes `openai.gpt-6`, so
  reasoning text stored from a Claude turn is dropped before the request is sent. In
  practice the `main` deployment has no answered conversations: all five requests it ever
  received failed before a reply.
- **Alternatives considered**: Clearing memory at migration, or catching the failure and
  retrying without history. Rejected as unnecessary given the library behaviour.
- **To confirm**: nothing can be confirmed without a stored Claude conversation. Accepted as
  a residual risk.

## Decision 6: Tell the two prerequisite failures apart from the failure detail entry

- **Decision**: Add no new record field. Document how to distinguish the two causes.
- **Rationale**: Both failures raise `AccessDeniedException`, so the request record's
  `errorType` is the same. The failure detail entry that follows it carries the service's
  message, and the two messages are distinct and already observed in this deployment's
  logs: "is not available for this account" for missing model access, and "with an explicit
  deny in a service control policy" for a region restriction. FR-008 asks that the records
  show which it was, and they do.
- **Alternatives considered**: A classified `errorReason` field on the record. Rejected for
  this feature: it changes the feature 003 record contract for two cases that are already
  readable.

## Decision 7: Limit the model ID to United States inference profiles

- **Decision**: Replace the `AllowedPattern` of the `ModelId` parameter with
  `^us\.[a-zA-Z0-9.:_-]+$`, and use the same pattern on the template's creation form. An ID
  must start with `us.`; the rest may contain dots.
- **Rationale**: Project owner's decision, 2026-11-15. The only purpose of the limit is to
  avoid the organization's region restriction, which denies calls made through global
  profiles. The old three-part pattern did more than that: it rejected
  `us.openai.gpt-6.1-terra` and the GPT-5.6 family, and it accepted `openai.gpt-5.6-luna`
  while misreading it. Decision 3 removes the need for the ID to be safe to split.
- **Alternatives considered**: Narrowing the spec to three-part IDs. Removing validation
  altogether, which the owner chose first and then replaced with this. Both set aside.
- **Consequence**: `global.`, `eu.` and other non-US profiles, and in-Region model IDs with
  no profile such as `openai.gpt-oss-120b-1:0`, are refused at deployment. A mistyped ID
  that still starts with `us.` is not caught; it deploys, and requests fail until it is
  corrected.

## Decision 8: Bring the template level with this project in the same change

- **Decision**: In `backstage-aws-agentcore-template`, set the form's model default to
  `us.openai.gpt-6-luna`, add a reasoning effort choice to the form, and apply to `skeleton/`
  every model-related change this project has: `ModelId` without a default in the template
  and set in `cfn-parameters.json`, `MODEL_ID` required at start, the `tests/conftest.py`
  that sets it for tests, `ReasoningEffort`, the default-project resource, and the handbook
  text.
- **Rationale**: FR-015 requires a new project to match this one. The template has the
  Pipfile and workflow changes from earlier but not the later `ModelId` and `MODEL_ID`
  changes, so it has to catch up on those as well.
- **To confirm**: by rendering the skeleton with default values and comparing it with this
  project, as was done for the Pipfile change. Creating a real project from the template is
  the full check (SC-011) and needs Backstage.

## Open questions for the project owner

- Allowed regions (T002): the project owner stated on 2026-11-15 that the region restriction
  "is gone". Recorded as reported. No request has confirmed it yet.

- Whether the deployment account can use GPT-6 Luna. It is a Marketplace model, and the last
  failure here was a missing entitlement for a different Marketplace model. Check it in the
  Bedrock model catalog before implementation starts.
- Decision 3's permission design replaces how the role was scoped. It is the part of this
  plan with the least evidence behind it.
