# Feature Specification: Observability

**Feature Branch**: `spec/003-observability`

**Created**: 2026-11-15

**Status**: Implemented (backfilled)

**Input**: User description: "Observability: an operator can find out what happened to one request and see how the agent is being used. Covers one structured record per request with a request identifier, outcome, duration and model usage; traces of the steps inside a request; the hosting platform's own measurements; and never putting prompt or reply text into the request records. Dashboards and alerts are not included. Applies to features 001 and 002."

**Backfill**: This specification was written on 2026-11-15, after the feature was built. It
describes what the code on `main` (commit `fd37671`) does. It is modelled on feature 007 of
the Bill-GN project (`specs/007-observability`), which is much larger: that specification
covers a monitoring system, a health view, alerts and several components, and most of it has
no counterpart here. The project owner has not reviewed or clarified this specification. The
differences are listed under
[Differences from the Bill-GN specification](#differences-from-the-bill-gn-specification).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find out what happened to one request (Priority: P1)

Someone reports that the agent did not reply, or replied badly. An operator takes the request
identifier from the reply and finds that request's record: its outcome, how long it took, and
for a failure, what kind of failure it was.

**Why this priority**: Without this, every problem report ends in guesswork.

**Independent Test**: Send the agent a set of prompts, including refused ones and one forced
to fail, then find each in the records from its request identifier alone and state its
outcome.

**Acceptance Scenarios**:

1. **Given** a request that was answered, **When** an operator searches the records for its
   request identifier, **Then** they find exactly one record, with the outcome, the duration,
   the conversation it belonged to, the prompt's length, the model used, and the model usage
   for that request.
2. **Given** a request that was refused by the input checks, **When** an operator looks it up,
   **Then** they find one record marked as an input rejection, with no model named.
3. **Given** a request that failed, **When** an operator looks it up, **Then** they find one
   record marked as an error with the kind of failure, and the failure's detail alongside it.
4. **Given** any reply, **When** a caller reads it, **Then** it carries the request identifier
   needed to find its record.

---

### User Story 2 - Request records never hold what was said (Priority: P1)

An operator, or any system the records are forwarded to, can read every request record
without seeing a prompt or a reply.

**Why this priority**: Callers may put anything in a prompt. Whatever reaches the records may
be forwarded to other systems and kept there, out of the project's control.

**Independent Test**: Send a prompt with distinctive text, then search the request records
for that text and for the reply's text and confirm neither is present.

**Acceptance Scenarios**:

1. **Given** any request record, **When** an operator reads it, **Then** it contains no prompt
   text and no reply text. The prompt appears only as a length.
2. **Given** a failure, **When** the caller reads the error reply, **Then** the failure's
   detail is in the records and not in the reply.

---

### User Story 3 - See the steps inside a request (Priority: P2)

An operator looks at one request as a timeline: when the agent called the model, how long
each call took, and where time was spent.

**Why this priority**: The request record gives one duration. When a request is slow, the
operator needs to see which step was slow.

**Independent Test**: Send a prompt, then open that request's trace and confirm it shows the
model call with its duration.

**Acceptance Scenarios**:

1. **Given** the account's one-time tracing setup has been done, **When** a request is
   answered, **Then** a trace of that request is available showing the steps inside it and
   how long each took.
2. **Given** the one-time tracing setup has not been done, **When** a request is sent,
   **Then** the agent still replies, and no trace is delivered.

---

### User Story 4 - See how much the agent is used (Priority: P3)

An operator sees how many requests the agent receives, how many fail, and how long they take,
without the agent itself counting anything.

**Why this priority**: Totals show whether the agent is healthy, but the hosting platform
already produces them, so this story asks only that they exist and are documented.

**Independent Test**: Send a known number of requests and confirm the platform's request count
for the agent matches.

**Acceptance Scenarios**:

1. **Given** the agent has been in use, **When** an operator views the hosting platform's
   measurements for it, **Then** they see requests, errors, throttled requests and response
   times.
2. **Given** several deployments of the agent, **When** an operator selects data by the
   organization's standard tags, **Then** they can separate one deployment's data from
   another's.

---

### Edge Cases

- A request rejected because the caller has no access: it never reaches the agent, so it has
  no request record. It appears only in the account's own access records, if those are kept.
- A request rejected because its body is malformed: it is turned away before the agent's
  handler runs, so it has no request record.
- A failure whose description quotes the prompt (for example, an error passed back from the
  model service): the description is written to the records as a separate entry. Nothing
  removes prompt text from it.
- Traces: the tracing built into the agent's framework can attach prompt and reply text to a
  trace. Whether it does so in this deployment has not been checked. See the differences
  below.
- The model does not report usage for a request: the record is written without usage figures.
- A request is answered from a remembered conversation (feature 002): the record's model
  usage includes the remembered messages, so the same prompt costs more later in a
  conversation.
- A branch deployment: it has its own records and traces, separate from `main`.
- The records' destination is unavailable: no behavior is specified.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST write exactly one structured record for every request that
  reaches it, whatever the outcome.
- **FR-002**: Every request record MUST contain: the request identifier, the conversation
  identifier, the outcome (answer, input rejection or error), the duration, and the length of
  the prompt.
- **FR-003**: A record of a request that reached the model MUST also name the model. A record
  of an answered request MUST also contain the model usage for that request, when the model
  reports it.
- **FR-004**: A record of a failed request MUST contain the kind of failure. The failure's
  full detail MUST be written to the same place as a separate entry that carries the request
  identifier.
- **FR-005**: The request identifier in a record MUST be the one returned to the caller in the
  reply.
- **FR-006**: Request records MUST NOT contain prompt text or reply text.
- **FR-007**: Request records MUST be machine-readable, one record per entry, so they can be
  searched and counted without parsing prose.
- **FR-008**: The agent MUST produce a trace of each request showing the steps inside it,
  including each use of the model, with durations.
- **FR-009**: Traces MUST be delivered without any per-request action. The one-time account
  setup that delivery depends on MUST be documented as a deployment prerequisite.
- **FR-010**: The amount of detail the agent writes MUST be adjustable by the project owner
  through the project's deployment settings.
- **FR-011**: The agent's permission to write records and measurements MUST be limited to the
  areas the hosting platform sets aside for agents. It MUST NOT be able to write to other
  components' records.
- **FR-012**: All of the agent's resources MUST carry the organization's standard tags, so
  that its data can be selected by component, branch and deployment.
- **FR-013**: The documentation MUST say where the records are, what each field means, how to
  find one request, what is deliberately not recorded, and which measurements the hosting
  platform provides.

### Key Entities

- **Request record**: One structured entry describing one request. Attributes: request
  identifier, conversation identifier, outcome, duration, prompt length, and, where they
  apply, the model, the model usage and the kind of failure.
- **Request identifier**: The identifier that ties a reply to its record.
- **Trace**: The ordered steps inside one request, with timings.
- **Measurement**: A number the hosting platform tracks over time, such as requests or errors.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For 100% of at least 20 test requests, including refused prompts and at least
  one forced failure, an operator can find exactly one record from the request identifier and
  state the outcome.
- **SC-002**: An operator who has not seen the request before can do this in under 5 minutes
  using only the documentation.
- **SC-003**: A review of every request record produced during testing finds no prompt text
  and no reply text.
- **SC-004**: With the one-time tracing setup done, 100% of answered test requests have a
  trace that shows the model call.
- **SC-005**: After a known number of test requests, the hosting platform's request count for
  the agent matches that number.
- **SC-006**: For answered requests, the model usage in the records, summed over a known set
  of requests, is within 5% of the usage the model provider reports for the same requests.

### Verification status at backfill

- SC-003 is covered for the request record by an automated test. SC-001 is covered by the
  automated tests only in that each outcome writes one record with the expected fields.
- SC-002, SC-004, SC-005 and SC-006 have not been tested. No record was found that traces
  from the deployed agent have been looked at, or that the one-time tracing setup has been
  done in the deployment account.

## Differences from the Bill-GN specification

These are the places where Bill-GN feature 007 asks for something this agent does not do.
Each is a decision for the project owner: accept the difference, or write a feature for it.

- **Prompt and reply text may be in traces.** Bill-GN FR-005 and FR-017 forbid question and
  answer text in any record, measurement or trace, including those a platform writes. Here
  only the request record is protected. The framework's tracing can attach message text to a
  trace, and the failure detail entry is not checked for it. Neither has been verified. This
  is the most important open point in this specification.
- **The caller is not identified.** Bill-GN FR-006 requires a direct request to be recorded
  with a non-content identifier of the caller. Here the record holds the conversation
  identifier only. The asker identifier a caller supplies is not recorded.
- **No monitoring system.** Bill-GN's records, measurements and traces must reach Datadog
  (FR-001, FR-018). Here nothing is specified beyond the cloud account. They may reach
  Datadog through the environment's existing forwarding, but that has not been checked.
- **No health view and no alerts.** Bill-GN FR-009 to FR-012, FR-019 and FR-020 have no
  counterpart. The handbook says none are created.
- **No cost estimate.** Bill-GN FR-007 asks for model usage with an estimate of its cost.
  Here usage is recorded per request and nothing adds it up or prices it.
- **Rejected callers are not counted by the agent.** Bill-GN FR-007 measures requests rejected
  as not permitted. Here they do not reach the agent.
- **No retention rule.** Bill-GN FR-016 sets how long records are kept. Nothing here does.
- **No behavior when recording fails.** Bill-GN FR-013 and FR-014 require that a recording
  failure never blocks an answer and that a period with no data can be told from a period
  with no problems. Neither is specified or tested here.

## Assumptions

- Operators are the project owner and developers, with access to the cloud account. There is
  no separate support team.
- Not recording prompt and reply text is deliberate and takes priority over ease of
  debugging. An operator diagnosing a bad reply asks the caller for the prompt.
- Expected usage is low, so the volume and cost of records is small.
- The fields in this specification were read from the code and the project handbook, not
  confirmed with the owner.
- Technology choices are described in the project handbook (`docs/handbook/`). The project
  constitution is still the unfilled Spec Kit template, so nothing here was checked against
  project principles.
