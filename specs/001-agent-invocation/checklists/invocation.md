# Invocation Requirements Checklist: Agent Invocation

**Purpose**: Validate whether the agent invocation requirements are complete, clear, consistent, and review-ready, given that the feature is already built.
**Created**: 2026-11-15
**Feature**: `specs/001-agent-invocation/spec.md`

**Note**: This checklist follows the format the `/speckit-checklist` command generates. It was written during the backfill of this specification.
**Review Ownership**: This checklist is a reviewer-owned requirements-quality review artifact. Mark an item `[x]` only when the reviewer determines the requirements-quality criterion is satisfied.
**Marker Semantics**: `[x]` means the criterion has been reviewed and satisfied for requirements quality. It does not mean implementation work is complete.

## Requirement Completeness

- [ ] CHK001 Are requirements defined for every reply kind (answer, input rejection, error), including what each contains? [Completeness, Spec §FR-002]
- [ ] CHK002 Are requirements defined for every form of unusable prompt: missing, empty, blank, non-text and over-length? [Completeness, Spec §FR-004, Spec §FR-005]
- [ ] CHK003 Is there a requirement for how the agent treats a prompt that tells it to ignore its instructions? [Gap, Edge Cases]
- [ ] CHK004 Is there a requirement for what the agent may be asked to do, given that its instructions describe repository reviews it cannot perform? [Gap, Edge Cases, Spec §Differences]
- [ ] CHK005 Are requirements defined for requests the hosting platform rejects before the agent sees them (malformed body, no permission)? [Completeness, Edge Cases, Spec §FR-009]

## Requirement Clarity

- [ ] CHK006 Is "explicitly granted access" defined precisely enough to say who grants it, to whom, and how it is withdrawn? [Clarity, Spec §FR-009]
- [ ] CHK007 Is "any detail of the failure" bounded, so a reviewer can tell whether the request identifier or the word "error" counts as detail? [Clarity, Spec §FR-008]
- [ ] CHK008 Is "defined in one place" specific about whether settings such as the model and the length limit are part of the instructions or separate from them? [Clarity, Spec §FR-011, Spec §FR-012]
- [ ] CHK009 Is the unit of the maximum prompt length (characters after trimming) stated wherever the limit is mentioned? [Clarity, Spec §FR-005, Spec §FR-006]

## Requirement Consistency

- [ ] CHK010 Is User Story 1 consistent with feature 002, given that a second prompt in a conversation is not independent of the first? [Consistency, Edge Cases, Spec 002 §FR-001]
- [ ] CHK011 Does FR-016 (each request is recorded) agree with feature 003 about which requests have a record and which do not? [Consistency, Spec §FR-016, Spec 003 §Edge Cases]
- [ ] CHK012 Are the three reply kinds named the same way in the requirements, the key entities and the success criteria? [Consistency, Spec §FR-002, Spec §Key Entities]

## Acceptance Criteria Quality

- [ ] CHK013 Does SC-001 state a sample size, so that "100% of prompts" can be measured? [Measurability, Spec §SC-001]
- [ ] CHK014 Is "none of them causes any model use" verifiable from outside the agent, and does the spec say where to look? [Measurability, Spec §SC-002]
- [ ] CHK015 Is the absence of timing and reply-quality criteria a recorded decision, or an omission? [Gap, Spec §Differences]
- [ ] CHK016 Is "no usage-based running cost" defined with what counts as usage-based and where it is read? [Measurability, Spec §SC-006]

## Scenario Coverage

- [ ] CHK017 Are requirements stated for the primary flow and for both refusal flows, with expected outcomes? [Coverage, Spec §User Story 1, Spec §User Story 2]
- [ ] CHK018 Are requirements defined for the model being unavailable or not permitted, distinct from other failures? [Coverage, Edge Cases]
- [ ] CHK019 Are recovery expectations defined for a caller that receives an error (retry, wait, give up)? [Gap, Spec §FR-008]

## Non-Functional Requirements

- [ ] CHK020 Are access control requirements specific enough to audit against the deployed permissions? [Security, Spec §FR-009, Spec §FR-010]
- [ ] CHK021 Is there any requirement on how quickly a reply must arrive? [Gap]
- [ ] CHK022 Is there any requirement limiting how much one caller may use the agent? [Gap]

## Dependencies & Assumptions

- [ ] CHK023 Is the assumption that callers are developers and components, not end users, turned into a requirement where it matters (for example, the wording of fixed messages)? [Assumption, Spec §Assumptions]
- [ ] CHK024 Is the dependency on the account having access to the chosen model stated as a requirement or a prerequisite? [Dependency, Edge Cases]
- [ ] CHK025 Has the project owner confirmed the values read from the code (4,000 characters, the fixed messages, the default model)? [Assumption, Spec §Assumptions]

## Notes

- Mark items `[x]` only after review confirms the requirement-quality criterion is satisfied
- Leave items unchecked when they still require clarification, correction, or reviewer evaluation
- `/speckit-implement` reads checklist checkbox state as a gate and must not modify markers
- `checklists/requirements.md` has a separate built-in lifecycle maintained by `/speckit-specify` and `/speckit-clarify`
- No item has been reviewed. All are unchecked because the reviewer, not the author, marks them
