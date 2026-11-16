# Feature Specification: OpenAI Model Migration

**Feature Branch**: `feature/005-model-migration`

**Created**: 2026-11-15

**Status**: Draft

**Input**: User description: "update the current spec to us migrating to `us.openai.gpt-6-luna`"

**History**: This specification was first written the same day as "Direct Anthropic Access",
from the description "as a developer my agent interfaces directly with Anthropic instead of
via Bedrock". The project owner dropped that direction during clarification and redirected
the specification to the migration described here. See Clarifications.

**Background**: The agent reaches its model through Amazon Bedrock, the cloud platform's
model service, and uses Anthropic's Claude Haiku 5.5. On 2026-11-15 every request to the
deployed agent failed: first because the organization's region restrictions denied the
call, and then because the deployment account has no access to that model. The project
owner reports that the region restriction has since been lifted, and decided to stay on
Amazon Bedrock and move the agent to OpenAI's GPT-6 Luna, reached through its United States
inference profile, `us.openai.gpt-6-luna`. It is OpenAI's lowest-cost model on the service
and is listed at the same price as the model it replaces.

## Clarifications

### Session 2026-11-15

- Q: How should the agent reach its model: directly from Anthropic, or through Amazon Bedrock? → A: Through Amazon Bedrock, moving to OpenAI GPT-6 Luna on the United States inference profile `us.openai.gpt-6-luna`. Direct access to Anthropic was dropped: the credential the owner holds is a Claude Code subscription token, which this agent cannot use, and a separate pay-per-use Anthropic account was not wanted.
- Q: If your organization's region restriction still blocks US West (Oregon) when this is built, should the agent wait for that to be lifted, or be built to reach GPT-6 Luna from US East (N. Virginia) alone? → A: Wait, and use `us.openai.gpt-6-luna` as specified, with all three regions being allowed as a prerequisite. The project owner reports that the region restriction has since been lifted.
- Q: How much should GPT-6 Luna think before it answers: the model's default amount, less than that to save cost and time, or more for better answers? → A: The model's default (medium), and the amount must be a deployment setting that can be changed from `cfn-parameters.json`.
- Q: If GPT-6 Luna's answers turn out not to be good enough when you review them, what should happen to this feature? → A: The migration is still done. Answer quality is tracked separately and does not block this feature.
- Q: Should this change also be made in the Backstage template that `engineering-agents` was generated from, so that new agents start on GPT-6 Luna with the reasoning effort setting? → A: Yes, in this feature. The template is updated together with `engineering-agents`, and the feature is not done until both are.
- Q: The model setting only accepted names with exactly three dot-separated parts, which rejects models such as GPT-6.1 Terra. Should the spec be narrowed to that form, or should other names be supported? → A: Accept any United States inference profile, meaning an ID that starts with `us.`, including one whose model name contains a dot. Reject everything else. The limit exists to keep the agent off global profiles, which the organization's region restriction denies.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The agent answers using GPT-6 Luna (Priority: P1)

A developer sends the deployed agent a prompt and receives an answer produced by GPT-6 Luna.

**Why this priority**: The deployed agent has not answered a single request. This story is
what makes it work, and everything else in this feature depends on it.

**Independent Test**: With the prerequisites in place, send the deployed agent a prompt
using the documented steps and confirm an answer arrives, and that the request's record
names the new model.

**Acceptance Scenarios**:

1. **Given** a deployment configured for GPT-6 Luna, with the account able to use it,
   **When** an authorized caller sends a prompt, **Then** the caller receives an answer.
2. **Given** an answered request, **When** an operator reads its record, **Then** the record
   names `us.openai.gpt-6-luna` as the model and includes the model usage for the request.
3. **Given** the agent's instructions, **When** a prompt is answered by the new model,
   **Then** the reply follows those instructions.
4. **Given** a deployment of any branch, **When** it is deployed after this feature,
   **Then** it uses GPT-6 Luna unless its settings say otherwise.
5. **Given** no reasoning effort is set, **When** a prompt is answered, **Then** the model
   reasons at its default level.
6. **Given** the owner sets a different reasoning effort and deploys, **When** a prompt is
   answered, **Then** the model reasons at that level, with no other change.

---

### User Story 2 - Nothing changes for callers (Priority: P1)

A caller who used the agent before the migration uses it the same way afterwards. Requests
and replies have the same form, unusable prompts are refused the same way, failures look the
same, and conversations continue.

**Why this priority**: The model is an internal choice. If changing it changes how the agent
is called or what it returns, every caller and every other specification is affected.

**Independent Test**: Run the validation steps of features 001 and 002 against a deployment
on the new model and confirm they give the same results as they are specified to.

**Acceptance Scenarios**:

1. **Given** a valid prompt, an empty prompt, an over-length prompt and a forced failure,
   **When** each is sent, **Then** each reply has the kind and the form defined in feature
   001.
2. **Given** a caller sends a prompt and then a follow-up in the same conversation, **When**
   the follow-up is answered, **Then** the reply reflects the earlier exchange, as in
   feature 002.
3. **Given** a conversation that began while the agent used the previous model, **When** the
   caller sends a follow-up after the migration, **Then** the request does not fail because
   of the earlier messages.
4. **Given** any request, **When** its record is read, **Then** it has the fields defined in
   feature 003 and contains no prompt or reply text.

---

### User Story 3 - The agent may use the chosen model and no other (Priority: P2)

The deployed agent holds the permissions GPT-6 Luna needs, and no permission for the model
it used before or for any other model.

**Why this priority**: The agent's permissions follow its configured model today. A model
from a different provider may need different permissions, and leaving the old ones in place
would let the agent use a model nobody chose.

**Independent Test**: Inspect the deployed agent's permissions and confirm they cover the
configured model and nothing else, then confirm the agent still answers.

**Acceptance Scenarios**:

1. **Given** a deployment after this feature, **When** its permissions are inspected,
   **Then** they allow it to use GPT-6 Luna through the United States inference profile.
2. **Given** the same deployment, **When** its permissions are inspected, **Then** they do
   not allow it to use Claude Haiku 5.5 or any other model.
3. **Given** the model needs a permission the previous model did not, **When** the agent is
   deployed, **Then** that permission is granted by the project's own infrastructure
   definition, and not by hand.

---

### User Story 4 - A missing prerequisite is easy to diagnose (Priority: P2)

The account cannot use the model, or the organization's region restrictions block one of the
places the request can be sent. The caller gets the same safe error as for any failure, and
an operator can tell from the records which prerequisite is missing.

**Why this priority**: These two conditions are exactly what stopped the agent before. Both
are fixed outside this project, by different people or settings, and they look identical to
the caller.

**Independent Test**: Send a prompt to a deployment in an account without access to the
model, and to one where a destination region is blocked. Confirm the caller receives the
standard error each time and that the records show which condition applied.

**Acceptance Scenarios**:

1. **Given** an account that has no access to GPT-6 Luna, **When** a prompt is sent,
   **Then** the caller receives the standard error reply, and the records show that the
   model is not available to the account.
2. **Given** region restrictions that block a region the inference profile can route to,
   **When** a prompt is sent and denied, **Then** the caller receives the standard error
   reply, and the records show that an organization policy denied the request.
3. **Given** either failure, **When** the caller reads the reply, **Then** it says nothing
   about the cause.
4. **Given** the project's documentation, **When** a reader looks for what must be true
   before the agent can answer, **Then** it lists access to the model and the three regions
   the inference profile uses.

---

### User Story 5 - The owner can go back (Priority: P3)

If GPT-6 Luna turns out not to be good enough, or stops being available, the project owner
returns the agent to its previous model, or moves it to another, by changing one setting.

**Why this priority**: The owner has not yet seen this model answer in this agent. The
migration should be cheap to undo.

**Independent Test**: Change the model setting to a different model the account can use,
deploy, and confirm the agent answers with that model and its permissions follow.

**Acceptance Scenarios**:

1. **Given** the agent on GPT-6 Luna, **When** the owner changes the model setting to
   another United States inference profile the account can use and deploys, **Then** the
   agent answers with that model.
2. **Given** such a change, **When** the deployment's permissions are inspected, **Then**
   they cover the newly configured model and no longer cover GPT-6 Luna.

---

### User Story 6 - New agents start on the same model (Priority: P2)

A developer creates a new agent from the organization's project template. It is configured
for GPT-6 Luna, with the reasoning effort setting and with permissions that follow its
model, exactly as this agent is after the migration.

**Why this priority**: The template still produces agents configured the way this one was
when it failed. Without this story every new agent starts broken in the same way.

**Independent Test**: Create a new agent from the template, without changing its model
settings, and compare its model setting, reasoning effort setting, permissions and
documentation with this agent's.

**Acceptance Scenarios**:

1. **Given** the updated template, **When** a developer creates a new agent with the
   default choices, **Then** the new project's model setting is `us.openai.gpt-6-luna`.
2. **Given** such a project, **When** its settings are read, **Then** it has the reasoning
   effort setting, unset by default.
3. **Given** such a project, **When** it is deployed in an account that meets the
   prerequisites, **Then** it answers a prompt with no further change.
4. **Given** the template's creation form, **When** a developer chooses a different model,
   **Then** the new project uses that model and its permissions follow it.

---

### Edge Cases

- The inference profile sends requests to any of three regions: US East (N. Virginia), US
  East (Ohio) and US West (Oregon). All three must be allowed by the organization's region
  restrictions. If one is blocked again later, requests routed to it are denied, and the
  agent is not changed to work around it (see Clarifications).
- The model works out its answer before replying, and bills that work as output. The agent
  uses the model's default level of effort (medium) unless the reasoning effort setting says
  otherwise, so replies may take longer and use more output than the previous model's. The
  request record shows the usage.
- The reasoning effort setting holds a value the configured model does not accept: the
  deployment is refused, or requests fail with the standard error reply and the record
  shows the cause. The agent does not silently fall back to another level.
- The owner later moves to a model that does not reason, or that uses different levels: the
  reasoning effort setting can be left unset, and an unset setting never causes a failure.
- The service counts each token of output as ten against the account's usage limit for this
  model. A long reply reaches the limit sooner than its size suggests, and a request refused
  for that reason returns the standard error reply.
- A conversation that began on the previous model and continues after the migration: the
  earlier messages are sent to the new model as they were stored. If the new model cannot
  accept them, the request must not fail; it is answered without them.
- The agent's instructions were written with the previous model in mind. They are one
  sentence today, so nothing in them is specific to a model, but replies may differ in tone
  and length.
- The agent sends and receives text only. The new model does not accept some other kinds of
  input the previous model did; this feature does not use them.
- A deployment made from a branch created before this feature: it keeps the model in its own
  settings until those are updated.
- An agent created from the template before it was updated: it is not changed by this
  feature. Its owner changes its model setting as this feature does here.
- The model setting holds an ID that does not start with `us.`, such as a global profile:
  the deployment is refused. Global profiles can route to regions the organization does not
  allow.
- The model setting starts with `us.` but is not a profile the account can use (a
  misspelling, or a model the account has no access to): the deployment succeeds, requests
  fail with the standard error reply, and the failure detail shows the cause.
- OpenAI releases a newer model, or this one is retired: moving is a setting change, as in
  User Story 5.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST obtain its model's replies from OpenAI GPT-6 Luna on Amazon
  Bedrock, through the United States inference profile `us.openai.gpt-6-luna`.
- **FR-002**: The model MUST remain a deployment setting with no fallback value in the
  agent. Changing to another model, including back to the previous one, MUST require only a
  change to that setting and a deployment.
- **FR-013**: How much the model reasons before answering MUST be a deployment setting.
  When the setting is not given, the agent MUST use the model's own default, which is
  medium for GPT-6 Luna. Changing the level MUST require only a change to that setting and
  a deployment.
- **FR-016**: The model setting MUST accept any United States inference profile ID, meaning
  one that starts with `us.`, including one whose model name contains a dot. A value that
  does not start with `us.` MUST be refused at deployment.
- **FR-003**: The form of a request and of a reply (feature 001), conversation memory
  (feature 002) and the fields of a request record (feature 003) MUST NOT change. The model
  named in a record MUST be the configured one.
- **FR-004**: Request records MUST continue to include the model usage for each answered
  request, as the new model reports it.
- **FR-005**: The agent's deployment MUST hold every permission the configured model needs,
  granted by the project's own infrastructure definition.
- **FR-006**: The agent's deployment MUST NOT hold permission to use any model other than
  the configured one.
- **FR-007**: The agent's permissions MUST follow the model setting, so that changing the
  setting changes what the agent may use without a separate edit.
- **FR-008**: When the account has no access to the model, or an organization policy denies
  the request, the caller MUST receive the standard error reply of feature 001, and the
  records MUST show which of the two it was.
- **FR-009**: A conversation remembered from before the migration MUST NOT cause a request
  to fail after it.
- **FR-010**: The automated tests MUST continue to run without cloud credentials and
  without calling any model.
- **FR-011**: The documentation MUST name the model and its inference profile, list the
  prerequisites (the account's access to the model, and the three regions the profile
  routes to), describe how to tell the two prerequisite failures apart, and describe how to
  change the model.
- **FR-012**: The specifications and documentation that name the previous model MUST be
  updated to name the new one when this feature is implemented.

- **FR-015**: The organization's project template for new agents MUST be updated in this
  feature so that a project created with the default choices has the same model setting,
  reasoning effort setting, permissions behaviour and documentation as this agent has after
  the migration. This feature is not complete until both this agent and the template are
  updated.

### Key Entities

- **Model setting**: The deployment setting that names the model the agent uses. Its value
  becomes `us.openai.gpt-6-luna`.
- **Reasoning effort setting**: The deployment setting for how much the model reasons
  before answering. Optional. Unset means the model's default.
- **Inference profile**: The service's named route to a model that may send a request to any
  of a fixed set of regions. For this model in the United States: N. Virginia, Ohio and
  Oregon.
- **Model access**: Whether the deployment account is entitled to use a given model. Granted
  outside this project.
- **Region restriction**: The organization's policy on which regions an account may use.
  Managed outside this project.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the prerequisites in place, 100% of at least 10 valid prompts sent to the
  deployed agent receive an answer, and each record names the new model.
- **SC-002**: The validation steps of features 001 and 002 that can be run against a
  deployed agent give the specified results on the new model, with 0 differences in the form
  of requests and replies.
- **SC-003**: Reported, not pass or fail: the project owner reviews the replies to at least
  10 prompts typical of the agent's intended use and records how many are acceptable. The
  result does not decide whether this feature is done.
- **SC-004**: 95% of those prompts receive their reply within 30 seconds.
- **SC-005**: An inspection of the deployed agent's permissions finds the configured model
  covered and no other model permitted.
- **SC-006**: For each of the two prerequisite failures, an operator can name the cause from
  the records alone in under 5 minutes, and 0 replies reveal it to the caller.
- **SC-007**: After the model setting is changed to another model the account can use, the
  agent answers with that model with no change other than the setting.
- **SC-010**: With the reasoning effort setting changed to a lower level and nothing else
  changed, the average output usage across the same 10 prompts is lower than at the
  default.
- **SC-008**: The automated tests pass on a machine with no cloud credentials.
- **SC-009**: The model usage in the request records for a known set of prompts is within 5%
  of what the service reports for them.

- **SC-011**: A project newly created from the template with the default choices has the
  model setting `us.openai.gpt-6-luna` and the reasoning effort setting, and a comparison
  of its model-related settings, permissions and documentation with this agent's finds no
  difference other than the project's own names.

## Assumptions

- The agent stays on Amazon Bedrock and keeps its current hosting, memory and observability
  (project owner's decision, 2026-11-15).
- GPT-6 Luna through the United States inference profile is the chosen model (project
  owner's decision, 2026-11-15), picked for cost first, then speed and accuracy. AWS lists
  it at $0.11 per million input tokens and $0.55 per million output tokens on that profile,
  which matches the list price of the model it replaces. Prices were read on 2026-11-15 and
  can change.
- Two prerequisites are outside this project: the deployment account's access to the model,
  and the organization's region restrictions allowing all three regions the profile routes
  to. The project owner reports that the region restriction was lifted on 2026-11-15; this
  has not been confirmed by a successful request. Whether the account can use GPT-6 Luna
  has not been checked. This feature cannot be shown to work until both are in place.
- The agent is not built to reach the model from a single region. Reaching it from US East
  (N. Virginia) alone was considered and rejected (project owner's decision, 2026-11-15).
- The current agent code can use the new model with a change to the model setting alone.
  This has not been tried. If the model needs a different way of being called, that is for
  the plan to establish.
- GPT-6 Luna is positioned by its provider for focused, high-volume work. Whether it is good
  enough for leading a code review has not been tested. That is recorded under SC-003 and
  does not block this feature (project owner's decision, 2026-11-15). If the answers are
  not good enough, raising the reasoning effort or moving to a larger model is a separate
  decision, made with the settings this feature provides.
- The 30-second limit in SC-004 is a starting value chosen by the spec author.
- How the service and the model's provider handle prompts and replies for this model,
  including any retention for abuse monitoring, was not reviewed. It is acceptable to the
  project owner for a personal project.
- The template is updated in the same feature although GPT-6 Luna has not yet been seen to
  answer a request in this organization (project owner's decision, 2026-11-15). If the
  model does not work here, the template will need changing again.
- The agent has no tools. Whether the new model works with tools the agent may be given
  later is out of scope.
- The project constitution is still the unfilled Spec Kit template, so this specification
  was not checked against project principles.
