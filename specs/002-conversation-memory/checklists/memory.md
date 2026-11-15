# Memory Requirements Checklist: Conversation Memory

**Purpose**: Validate whether the conversation memory requirements are complete, clear, consistent, and review-ready, given that the feature is already built.
**Created**: 2026-11-15
**Feature**: `specs/002-conversation-memory/spec.md`

**Note**: This checklist follows the format the `/speckit-checklist` command generates. It was written during the backfill of this specification.
**Review Ownership**: This checklist is a reviewer-owned requirements-quality review artifact. Mark an item `[x]` only when the reviewer determines the requirements-quality criterion is satisfied.
**Marker Semantics**: `[x]` means the criterion has been reviewed and satisfied for requirements quality. It does not mean implementation work is complete.

## Requirement Completeness

- [ ] CHK001 Are requirements defined for what makes two prompts part of one conversation, covering both identifiers and the deployment? [Completeness, Spec §FR-001, Spec §FR-004]
- [ ] CHK002 Is there a requirement for what happens when the remembered conversation cannot be read or saved? [Gap, Edge Cases, Spec §Differences]
- [ ] CHK003 Is there a requirement for conversations that grow beyond what the model can take in? [Gap, Edge Cases]
- [ ] CHK004 Is there a requirement for removing a conversation before it expires, by a caller or an operator? [Gap, Spec §Differences]
- [ ] CHK005 Are requirements defined for who may read a remembered conversation directly from the store? [Completeness, Spec §FR-009]

## Requirement Clarity

- [ ] CHK006 Is the retention rule unambiguous about what the period counts from: each message, or the last message in the conversation? [Clarity, Spec §FR-006, Spec §Differences]
- [ ] CHK007 Is "usable only by the agent's own deployment" defined precisely enough to audit against account-level permissions the project does not control? [Clarity, Spec §FR-009]
- [ ] CHK008 Is "the default asker" defined, including which callers share it and whether that sharing is intended? [Clarity, Spec §FR-002, Edge Cases]
- [ ] CHK009 Is "use the earlier exchanges" bounded, so a reviewer can tell whether all of them or only recent ones must be used? [Clarity, Spec §FR-001]

## Requirement Consistency

- [ ] CHK010 Does FR-003 (conversations share no context) agree with the edge case in which any caller can continue a conversation by presenting its identifiers? [Consistency, Spec §FR-003, Edge Cases]
- [ ] CHK011 Does FR-008 (only prompts and replies are remembered) agree with feature 001 about whether a refused prompt or a failed request is remembered? [Consistency, Spec §FR-008, Edge Cases]
- [ ] CHK012 Is FR-010 (instructions apply regardless of earlier messages) consistent with feature 001 having no rule about prompts that try to change the agent's instructions? [Consistency, Spec §FR-010, Spec 001 §Edge Cases]

## Acceptance Criteria Quality

- [ ] CHK013 Can SC-001 be judged objectively, with a stated way to decide that a reply "uses that fact"? [Measurability, Spec §SC-001]
- [ ] CHK014 Is SC-004 practical to measure, given that the shortest retention period is 3 days? [Measurability, Spec §SC-004]
- [ ] CHK015 Is there a success criterion for each functional requirement, including FR-005, FR-007 and FR-009? [Coverage, Gap]

## Scenario Coverage

- [ ] CHK016 Are requirements stated for the primary flow and for both kinds of separation (by conversation and by asker)? [Coverage, Spec §User Story 1, Spec §User Story 2]
- [ ] CHK017 Are requirements defined for two prompts sent at the same moment in one conversation? [Gap, Spec §Differences]
- [ ] CHK018 Are requirements defined for a conversation in which some messages have expired and others have not? [Coverage, Edge Cases]
- [ ] CHK019 Are requirements defined for what a caller is told when earlier messages are no longer available? [Gap]

## Non-Functional Requirements

- [ ] CHK020 Are privacy requirements specific about protection of remembered messages at rest, beyond relying on platform defaults? [Security, Spec §Assumptions]
- [ ] CHK021 Is there a requirement limiting how much time memory may add to a reply? [Gap]
- [ ] CHK022 Is there a requirement on the cost of long conversations, given that every remembered message is sent to the model again? [Gap]

## Dependencies & Assumptions

- [ ] CHK023 Is the assumption that callers supply honest identifiers stated as a requirement on callers, with a named owner? [Assumption, Spec §Assumptions]
- [ ] CHK024 Has the project owner confirmed the values read from the code (7 days, the 3 to 365 day range)? [Assumption, Spec §Assumptions]
- [ ] CHK025 Is the difference from the Bill-GN retention rule (30 days after the last message) a recorded decision? [Assumption, Spec §Differences]

## Notes

- Mark items `[x]` only after review confirms the requirement-quality criterion is satisfied
- Leave items unchecked when they still require clarification, correction, or reviewer evaluation
- `/speckit-implement` reads checklist checkbox state as a gate and must not modify markers
- `checklists/requirements.md` has a separate built-in lifecycle maintained by `/speckit-specify` and `/speckit-clarify`
- No item has been reviewed. All are unchecked because the reviewer, not the author, marks them
