# Feature Specification: Conversation Memory

**Feature Branch**: `spec/002-conversation-memory`

**Created**: 2026-11-15

**Status**: Implemented (backfilled)

**Input**: User description: "Conversation memory: prompts that a caller marks as belonging to the same conversation continue that conversation, so a follow-up is understood in light of what was said earlier, including after a pause. Different conversations, and different askers, never share context. Remembered messages are kept for a set number of days and then removed. Depends on feature 001 (agent invocation)."

**Backfill**: This specification was written on 2026-11-15, after the feature was built. It
describes what the code on `main` (commit `fd37671`) does. It is modelled on feature 003 of
the Bill-GN project (`specs/003-conversation-memory`), with everything specific to Slack
removed, because this agent has no chat front end. The project owner has not reviewed or
clarified it. Where the code does less than the Bill-GN specification asks, the difference is
listed under
[Differences from the Bill-GN specification](#differences-from-the-bill-gn-specification).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask a follow-up in the same conversation (Priority: P1)

A caller sends a prompt, reads the reply, and sends a follow-up that only makes sense in light
of the first exchange. The agent answers the follow-up without the caller repeating
themselves.

**Why this priority**: Useful work with an agent is a back-and-forth. Without memory every
prompt must restate everything that came before.

**Independent Test**: Send "My name for this test is Alder." and then, in the same
conversation, "What name did I give for this test?". Confirm the second reply says Alder.

**Acceptance Scenarios**:

1. **Given** the agent has answered a prompt, **When** the caller sends a follow-up marked as
   the same conversation and the same asker, **Then** the reply reflects the earlier exchange.
2. **Given** a conversation with several exchanges, **When** the caller refers to something
   from the first exchange, **Then** the agent still takes it into account.
3. **Given** an exchange in a conversation, **When** the caller sends a follow-up after the
   agent has been idle long enough to shut down, **Then** the reply still reflects the earlier
   exchange.

---

### User Story 2 - Conversations stay separate (Priority: P1)

What is said in one conversation never shows up in another, and two askers never see each
other's exchanges.

**Why this priority**: Leaking one conversation into another is a privacy failure and makes
replies wrong.

**Independent Test**: Hold exchanges on different subjects in two conversations, and under two
asker identifiers, then send an ambiguous follow-up in each and confirm each reply draws only
on its own exchanges.

**Acceptance Scenarios**:

1. **Given** two conversations with different conversation identifiers, **When** a follow-up
   is sent in one, **Then** nothing from the other is used.
2. **Given** two requests that share a conversation identifier but name different askers,
   **When** each asker sends a follow-up, **Then** neither reply uses the other asker's
   exchanges.
3. **Given** two deployments of the agent (for example, the `main` deployment and a branch
   deployment), **When** the same conversation identifier is used with both, **Then** neither
   uses anything remembered by the other.

---

### User Story 3 - Remembered messages are removed after a set time (Priority: P2)

Messages are kept for a set number of days and then removed without anyone acting. The project
owner chooses the number of days.

**Why this priority**: Remembered messages may hold whatever callers typed. Keeping them
indefinitely is a liability, and the owner needs to control how long they are kept.

**Independent Test**: With the retention period at its shortest setting, hold an exchange,
wait for the period to pass, send a follow-up that depends on it, and confirm it is answered
as a new conversation.

**Acceptance Scenarios**:

1. **Given** a remembered message older than the retention period, **When** a follow-up is
   sent, **Then** that message is not used.
2. **Given** the default settings, **When** a message is remembered, **Then** it is kept for
   7 days.
3. **Given** the owner sets a different retention period and deploys, **When** new messages
   are remembered, **Then** they are kept for the new period.

---

### Edge Cases

- A request that names no asker: it is handled as one shared, unnamed asker. Callers who
  never name an asker and reuse a conversation identifier therefore share that conversation.
- A caller presents another caller's conversation identifier and asker: the conversation
  continues. Any caller with access to the agent can continue any conversation whose
  identifiers it knows. There is no ownership check.
- A prompt refused by the input checks (feature 001): it is not remembered, because it never
  reaches the part of the agent that remembers.
- The remembered conversation cannot be read or saved: the request fails and the caller
  receives the error reply of feature 001. The agent does not fall back to answering the
  prompt on its own.
- A conversation in which only some messages have passed the retention period: the older
  messages are gone and the newer ones remain, so the agent may recall the end of a
  conversation without its beginning.
- A very long conversation: no behavior is specified. Nothing shortens or summarizes a
  conversation, and what happens when one outgrows what the model can take in is not known.
- A caller asks the agent to forget the conversation: the agent has no ability to do so.
- A deployment is removed: everything it remembered is removed with it.
- A conversation identifier outside the length the hosting platform accepts (33 to 256
  characters): the request is rejected before it reaches the agent.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST treat all prompts that carry the same conversation identifier and
  the same asker identifier as one conversation, and MUST use the earlier exchanges of that
  conversation when answering a new prompt in it.
- **FR-002**: The conversation identifier and the asker identifier MUST be supplied by the
  caller. A request that names no asker MUST be handled under one default asker.
- **FR-003**: Conversations MUST NOT share any context. This includes two conversations with
  different conversation identifiers, and two askers under the same conversation identifier.
- **FR-004**: Each deployment of the agent MUST keep its own remembered conversations,
  separate from every other deployment's.
- **FR-005**: A remembered conversation MUST remain available across periods in which the
  agent is idle or not running.
- **FR-006**: Each remembered message MUST be removed automatically once the retention period
  has passed since it was recorded.
- **FR-007**: The retention period MUST default to 7 days and MUST be changeable by the
  project owner, between 3 and 365 days, without changing the agent's code.
- **FR-008**: A remembered conversation MUST contain only the prompts sent to the agent in
  that conversation and the agent's replies to them.
- **FR-009**: Remembered conversations MUST be usable only by the agent's own deployment.
  This feature MUST NOT grant any other component access to them.
- **FR-010**: The agent's instructions (feature 001) MUST apply to every reply regardless of
  what earlier messages in the conversation said.
- **FR-011**: Request records (feature 003) MUST identify the conversation a request belongs
  to without recording message text.
- **FR-012**: The documentation MUST state what the agent remembers, for how long, and how a
  caller continues or separates conversations.

### Key Entities

- **Conversation**: The remembered exchanges for one conversation identifier and one asker
  identifier, in one deployment.
- **Turn**: One prompt and the agent's reply to it, in order within a conversation.
- **Conversation identifier**: A value the caller chooses and repeats to continue a
  conversation.
- **Asker identifier**: An optional value the caller supplies to say who is asking. It
  separates askers who share a conversation identifier.
- **Retention period**: The number of days a remembered message is kept.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On at least 10 two-prompt exchanges where the second prompt depends on a fact
  stated in the first, at least 90% of second replies use that fact.
- **SC-002**: On at least 5 pairs of different conversations, and at least 5 pairs of askers
  sharing a conversation identifier, 0 replies contain information that appeared only in the
  other conversation or under the other asker.
- **SC-003**: A follow-up sent after the agent has been idle for at least 30 minutes is
  answered using the earlier exchange in 100% of at least 5 trials.
- **SC-004**: With the retention period at its shortest setting, 100% of follow-ups sent after
  the period has passed are answered without the earlier exchange.
- **SC-005**: A review of request records finds conversation identifiers and no message text.

### Verification status at backfill

- None of these criteria has been tested. The project's automated tests replace the part of
  the agent that remembers with a stand-in, so they do not exercise memory at all.
- SC-005 is partly covered: an automated test confirms that a request record holds no prompt
  or reply text.

## Differences from the Bill-GN specification

These are the places where Bill-GN feature 003 asks for something this agent does not do.
Each is a decision for the project owner: accept the difference, or write a feature for it.

- **Retention is shorter and counted differently.** Bill-GN keeps a conversation for 30 days
  after its last message (FR-003, FR-004). Here each message is kept for 7 days from when it
  was recorded, so an active conversation loses its oldest messages as it goes.
- **No summary of long conversations.** Bill-GN brings the last 10 exchanges in full and a
  summary of older ones (FR-006). Here nothing limits or summarizes a conversation.
- **No forgetting on request.** Bill-GN lets a person tell it to forget a conversation
  (FR-016 to FR-018). This agent cannot.
- **No operator procedure.** Bill-GN requires documented steps for an operator to list and
  remove conversations without reading them, and a recorded step for reading one (FR-007,
  FR-011). None is documented here.
- **A memory failure fails the request.** Bill-GN answers the prompt on its own and says it
  could not recall the earlier discussion (FR-009). Here the caller receives an error. This
  was read from the code and has not been tested.
- **Direct use is not independent.** Bill-GN keeps direct, non-Slack requests independent
  (FR-014). Here every request is direct and every request uses memory.
- **Message order is not specified.** Bill-GN requires messages in one conversation to be
  handled in the order sent (FR-008). Nothing here ensures it for prompts sent at the same
  time.
- **The asker's identity is whatever the caller says.** Bill-GN ties a conversation to a
  Slack direct message. Here both identifiers are supplied by the caller and are not checked.

## Assumptions

- Callers are developers and other components that hold access to the agent. Each is trusted
  to supply honest conversation and asker identifiers. A front end added by a later feature
  would supply them on behalf of end users.
- The agent remembers nothing across conversations: no profile of an asker and no learning
  from past conversations.
- Protection of remembered conversations at rest is whatever the hosting platform provides by
  default. This feature sets nothing of its own.
- Expected usage is low, with conversations of a few turns.
- The values in this specification (7 days, the 3 to 365 day range, the default asker) were
  read from the code and the project handbook, not confirmed with the owner.
- Technology choices are described in the project handbook (`docs/handbook/`). The project
  constitution is still the unfilled Spec Kit template, so nothing here was checked against
  project principles.
