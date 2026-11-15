# Observability Requirements Checklist: Observability

**Purpose**: Validate whether the observability requirements are complete, clear, consistent, and review-ready, given that the feature is already built.
**Created**: 2026-11-15
**Feature**: `specs/003-observability/spec.md`

**Note**: This checklist follows the format the `/speckit-checklist` command generates. It was written during the backfill of this specification.
**Review Ownership**: This checklist is a reviewer-owned requirements-quality review artifact. Mark an item `[x]` only when the reviewer determines the requirements-quality criterion is satisfied.
**Marker Semantics**: `[x]` means the criterion has been reviewed and satisfied for requirements quality. It does not mean implementation work is complete.

## Requirement Completeness

- [ ] CHK001 Are the contents of a request record fully specified for each outcome (answer, input rejection, error)? [Completeness, Spec §FR-002, Spec §FR-003, Spec §FR-004]
- [ ] CHK002 Does the ban on prompt and reply text cover every kind of data the feature produces, or only the request record? [Gap, Spec §FR-006, Spec §Differences]
- [ ] CHK003 Is there a requirement for identifying who made a request? [Gap, Spec §Differences]
- [ ] CHK004 Is there a requirement for how long records and traces are kept? [Gap, Spec §Differences]
- [ ] CHK005 Is there a requirement for what happens to a request when writing its record fails? [Gap, Edge Cases, Spec §Differences]
- [ ] CHK006 Are requirements defined for requests that never reach the agent (no permission, malformed body)? [Completeness, Edge Cases]

## Requirement Clarity

- [ ] CHK007 Is "the failure's full detail" bounded, given that it may quote text the agent does not control? [Clarity, Spec §FR-004, Edge Cases]
- [ ] CHK008 Is "the steps inside it" specific about which steps a trace must show? [Clarity, Spec §FR-008]
- [ ] CHK009 Is "duration" defined with a start point and an end point? [Clarity, Spec §FR-002]
- [ ] CHK010 Is "the organization's standard tags" defined by naming the tags? [Clarity, Spec §FR-012]

## Requirement Consistency

- [ ] CHK011 Does FR-001 (one record for every request that reaches the agent) agree with the edge cases about which requests reach it? [Consistency, Spec §FR-001, Edge Cases]
- [ ] CHK012 Does User Story 2's title ("never hold what was said") match the narrower scope of FR-006 (request records only)? [Consistency, Spec §User Story 2, Spec §FR-006]
- [ ] CHK013 Do the record fields in the requirements match the fields in the key entities and in `contracts/request-record.schema.json`? [Consistency, Spec §FR-002, Spec §Key Entities]

## Acceptance Criteria Quality

- [ ] CHK014 Is SC-001 achievable as written, given that there is no way to force a failure in a deployed agent? [Measurability, Spec §SC-001]
- [ ] CHK015 Does SC-003 say which stores a reviewer must search, so "every request record" has a boundary? [Measurability, Spec §SC-003]
- [ ] CHK016 Is SC-006's comparison practical, with a named source for the provider's usage figures? [Measurability, Spec §SC-006]
- [ ] CHK017 Is there a success criterion for traces not containing prompt or reply text? [Gap, Spec §Differences]

## Scenario Coverage

- [ ] CHK018 Are requirements stated for finding a request when the operator has no request identifier? [Gap, Spec §User Story 1]
- [ ] CHK019 Are requirements defined for telling a period with no requests from a period with no data? [Gap, Spec §Differences]
- [ ] CHK020 Are requirements defined for separating one deployment's data from another's across records, traces and measurements alike? [Coverage, Spec §FR-012, Spec §User Story 4]

## Non-Functional Requirements

- [ ] CHK021 Are privacy requirements specific about systems the records may be forwarded to? [Security, Spec §User Story 2, Spec §Differences]
- [ ] CHK022 Is the absence of a health view and alerts a recorded decision by the owner? [Gap, Spec §Differences]
- [ ] CHK023 Is there a requirement on how soon after a request its record must be findable? [Gap]

## Dependencies & Assumptions

- [ ] CHK024 Is the one-time tracing setup stated with who does it and how to tell that it has been done? [Dependency, Spec §FR-009]
- [ ] CHK025 Is the assumption that operators have access to the cloud account stated as a requirement on who can investigate? [Assumption, Spec §Assumptions]
- [ ] CHK026 Has the project owner confirmed that the record's fields, read from the code, are the intended ones? [Assumption, Spec §Assumptions]

## Notes

- Mark items `[x]` only after review confirms the requirement-quality criterion is satisfied
- Leave items unchecked when they still require clarification, correction, or reviewer evaluation
- `/speckit-implement` reads checklist checkbox state as a gate and must not modify markers
- `checklists/requirements.md` has a separate built-in lifecycle maintained by `/speckit-specify` and `/speckit-clarify`
- No item has been reviewed. All are unchecked because the reviewer, not the author, marks them
