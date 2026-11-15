# Feature Specification: Agent Invocation

**Feature Branch**: `spec/001-agent-invocation`

**Created**: 2026-11-15

**Status**: Implemented (backfilled)

**Input**: User description: "Agent invocation: an authorized caller sends the agent one text prompt and receives one text reply. The agent follows instructions that are defined in one place. Empty and over-length prompts are refused before any model work is done, and a failure produces a clear error that reveals no internal detail. The agent is invoked directly, with no chat front end. This is the foundation that later features (a front end, reference knowledge, tools, delegation) build on."

**Backfill**: This specification was written on 2026-11-15, after the feature was built. It
describes what the code on `main` (commit `fd37671`) does. It is modelled on feature 001 of
the Bill-GN project (`specs/001-gn-expert-agent`), which this agent was built from, with the
Grand National persona removed. The project owner has not reviewed or clarified it. Where the
code does less than the Bill-GN specification asks, the difference is listed under
[Differences from the Bill-GN specification](#differences-from-the-bill-gn-specification).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Send a prompt and get a reply (Priority: P1)

A caller who has been granted access sends the agent a text prompt and receives a text reply
written according to the agent's instructions.

**Why this priority**: This is the whole purpose of the agent. Every other feature depends on
a prompt going in and a reply coming out.

**Independent Test**: Send the deployed agent a prompt using the documented steps and confirm
a reply arrives that is marked as an answer and carries a request identifier.

**Acceptance Scenarios**:

1. **Given** the agent is available, **When** an authorized caller sends a prompt, **Then**
   the caller receives one complete reply containing the agent's text, a marker that it is an
   answer, and a request identifier.
2. **Given** a prompt with spaces or line breaks before or after its text, **When** it is
   sent, **Then** the agent treats it as the text alone.
3. **Given** a caller who has not been granted access, **When** that caller sends a prompt,
   **Then** the request is rejected as not authorized and the agent produces no reply.
4. **Given** the agent has not been used for some time, **When** a caller sends a prompt,
   **Then** the agent still replies, with no step needed to wake it.

---

### User Story 2 - Unusable prompts are refused before any work is done (Priority: P1)

A caller sends nothing, or sends far more text than the agent accepts. The agent says what is
wrong straight away and spends nothing on the model.

**Why this priority**: Model use is the agent's main running cost. A prompt that cannot be
answered should cost nothing, and the caller should be told why.

**Independent Test**: Send an empty prompt, a prompt of only spaces, a prompt that is not
text, a prompt exactly at the length limit and a prompt one character over it. Confirm the
refusals, the wording, and that no model use was recorded for the refused ones.

**Acceptance Scenarios**:

1. **Given** a request with no prompt, an empty prompt, a prompt of only spaces, or a prompt
   that is not text, **When** it is sent, **Then** the caller receives a reply marked as an
   input rejection that asks for a prompt, and the model is not used.
2. **Given** a prompt longer than the maximum length, **When** it is sent, **Then** the caller
   receives a reply marked as an input rejection that states the limit, and the model is not
   used.
3. **Given** a prompt exactly at the maximum length, **When** it is sent, **Then** it is
   accepted and answered.

---

### User Story 3 - Failures are clear and reveal nothing (Priority: P2)

Something goes wrong while the agent prepares a reply. The caller is told plainly that the
agent could not reply, and learns nothing about the agent's internals.

**Why this priority**: A blank or misleading reply is worse than an honest failure, and error
detail shown to a caller can expose how the agent is built.

**Independent Test**: Force a failure while the agent prepares a reply and confirm the caller
receives the fixed error message, marked as an error and as a failed request, with none of the
failure's detail.

**Acceptance Scenarios**:

1. **Given** the agent cannot produce a reply, **When** the failure occurs, **Then** the
   caller receives a reply marked as an error, with a fixed message that suggests trying
   again later and a request identifier.
2. **Given** a failure whose internal description contains sensitive detail, **When** the
   caller reads the error reply, **Then** none of that detail is in it.
3. **Given** an error reply, **When** the calling program checks whether the request
   succeeded, **Then** it can tell that it failed without reading the message text.

---

### User Story 4 - The owner sets what the agent does in one place (Priority: P2)

The project owner decides how the agent behaves by editing one set of instructions. The same
instructions govern every reply.

**Why this priority**: The instructions are what make this agent this agent. They must be easy
to find, review and change without touching anything else.

**Independent Test**: Change the instructions, deploy, and confirm the next reply follows the
new instructions.

**Acceptance Scenarios**:

1. **Given** the agent's instructions, **When** any prompt is answered, **Then** the reply is
   produced under those instructions.
2. **Given** the owner edits the instructions and deploys the change, **When** the next prompt
   is sent, **Then** the reply follows the edited instructions.
3. **Given** the instructions are missing or empty, **When** the project's automated checks
   run, **Then** they fail.

---

### Edge Cases

- The request body is not a well-formed message: it is rejected before the agent sees it, and
  no reply of any of the agent's kinds is produced.
- The request is well formed but is not the expected shape (for example, a list where a
  record is expected): it is treated as a request with no prompt.
- A second prompt in the same conversation: it continues that conversation. This is defined
  by feature 002 and differs from the Bill-GN specification, where every request stands
  alone.
- The model is unavailable, or the account has no access to it: the caller receives the error
  reply of User Story 3.
- A prompt that asks the agent to ignore its instructions: no behavior is specified. The
  current instructions contain no rule about this.
- A prompt in a language other than English: no behavior is specified.
- A caller needs the reply as it is written: not available. The reply arrives complete, in
  one piece.
- The agent's current instructions describe leading a review session against a GitHub
  repository and creating a reviewable artifact in that repository. The agent has no means of
  reading a repository or writing to one, so it can only discuss what the caller puts in the
  prompt. Giving it that ability is not part of this feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST accept a single text prompt from a caller and return a single
  text reply.
- **FR-002**: Every reply MUST state its kind and carry a request identifier. The kinds are:
  an answer, an input rejection, and an error.
- **FR-003**: The agent MUST remove leading and trailing blank space from a prompt before
  using it, and from its own reply before returning it.
- **FR-004**: The agent MUST refuse a missing, empty, blank or non-text prompt with an input
  rejection that asks the caller for a prompt.
- **FR-005**: The agent MUST enforce a maximum prompt length, measured after trimming. A
  longer prompt MUST be refused with an input rejection that states the limit. A prompt
  exactly at the limit MUST be accepted.
- **FR-006**: The maximum prompt length MUST default to 4,000 characters and MUST be
  changeable by the project owner without changing the agent's code.
- **FR-007**: A refused prompt MUST NOT cause any model use.
- **FR-008**: When the agent cannot produce a reply, the caller MUST receive an error reply
  with a fixed, generic message. The reply MUST NOT contain any detail of the failure, and
  the request MUST be reported to the caller as failed.
- **FR-009**: The agent MUST be invocable only by callers the project owner has explicitly
  granted access. A request from any other caller MUST be rejected as not authorized and MUST
  NOT reach the agent.
- **FR-010**: There MUST be no way to reach the agent without credentials.
- **FR-011**: The agent's instructions MUST be defined in one place, as prose that can be
  read and reviewed on its own, and MUST govern every reply.
- **FR-012**: The model the agent uses MUST be chosen by the project owner through the
  project's deployment settings, and the agent MUST be permitted to use only that model.
- **FR-013**: The agent MUST be invocable directly, with no chat front end, so that it can be
  verified on its own and called by other components.
- **FR-014**: The documentation MUST describe how to send the agent a prompt and read its
  reply, what a request and a reply contain, and how to grant a caller access.
- **FR-015**: The agent MUST incur no usage-based running cost while it receives no requests.
- **FR-016**: Each request MUST be recorded, as defined in feature 003.

### Key Entities

- **Prompt**: The text a caller sends. Attributes: the text, the conversation it belongs to
  (feature 002), optionally who is asking (feature 002), and a request identifier.
- **Reply**: What the agent returns. Attributes: the text, its kind (answer, input rejection
  or error), and the same request identifier.
- **Instructions**: The single definition of how the agent behaves. They govern every reply.
- **Caller**: A person or component that holds credentials the project owner has granted
  access to. In this feature callers are developers and other components, not end users.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of prompts that pass the input checks, sent by an authorized caller while
  the model is available, receive a reply marked as an answer with a request identifier.
- **SC-002**: 100% of missing, empty, blank, non-text and over-length prompts receive an input
  rejection, and none of them causes any model use.
- **SC-003**: 100% of forced failures return the fixed error message, are reported as failed,
  and contain none of the failure's detail.
- **SC-004**: 100% of requests sent by a caller without access are rejected and produce no
  reply.
- **SC-005**: A developer with access can send the agent a prompt and read its reply in under
  5 minutes using the documented steps.
- **SC-006**: Over any 24-hour period in which no prompts are sent, the agent incurs no
  usage-based running cost.
- **SC-007**: After the owner changes the instructions and deploys, 100% of subsequent replies
  are produced under the changed instructions.

### Verification status at backfill

- SC-002 and SC-003 are covered by the project's automated tests, which replace the model
  with a stand-in.
- SC-001 is covered by the automated tests only with the stand-in model. No record was found
  of a prompt being sent to the deployed agent.
- SC-004, SC-005, SC-006 and SC-007 have not been tested. They rest on how the hosting
  platform is configured and on the documentation.

## Differences from the Bill-GN specification

These are the places where Bill-GN feature 001 asks for something this agent does not do.
Each is a decision for the project owner: accept the difference, or write a feature for it.

- **No scope, honesty or safety rules.** Bill-GN's persona, on-topic scope, role-keeping,
  uncertainty and safety rules (its FR-002 to FR-008 and FR-016 to FR-023) have no
  counterpart. The instructions are one sentence, and the only automated check is that they
  are not empty.
- **No decline kind.** Bill-GN has four kinds of answer, including a decline. This agent has
  three. A reply in which the model declines is marked as an answer.
- **Requests are not independent.** Bill-GN FR-015 requires each request to stand alone. Here
  conversation memory (feature 002) is on for every request.
- **Rejected callers are not recorded by the agent.** Bill-GN FR-012 requires an unauthorized
  request to be recorded. Here it never reaches the agent, and it is recorded only if the
  account keeps the hosting platform's own access records.
- **No reply-quality or timing criteria.** Bill-GN's review sets, its 30-second reply target
  and its reply length and structure rules (FR-009, SC-001 to SC-005, SC-010) have no
  counterpart.
- **The stated purpose is not delivered.** See the last edge case: the instructions describe
  repository review sessions that the agent cannot carry out.

## Assumptions

- Callers are developers testing the agent directly and, later, other components. End users
  would reach it only through a front end that a later feature adds.
- The agent answers from the model's general knowledge. It has no reference material, no
  tools and no specialist agents.
- Replies are plain text.
- Expected usage is low: a small team and tens of prompts per day.
- The agent starts on a low-cost model chosen by the project owner. Nothing here ties the
  choice to a quality bar.
- The values in this specification (the 4,000 character limit, the reply kinds, the fixed
  messages) were read from the code and the project handbook, not confirmed with the owner.
- Technology choices are described in the project handbook (`docs/handbook/`). The project
  constitution is still the unfilled Spec Kit template, so nothing here was checked against
  project principles.
