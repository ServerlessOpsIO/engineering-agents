# Delivery Requirements Checklist: Build and Delivery

**Purpose**: Validate whether the build and delivery requirements are complete, clear, consistent, and review-ready, given that the feature is already built.
**Created**: 2026-11-15
**Feature**: `specs/004-build-and-delivery/spec.md`

**Note**: This checklist follows the format the `/speckit-checklist` command generates. It was written during the backfill of this specification.
**Review Ownership**: This checklist is a reviewer-owned requirements-quality review artifact. Mark an item `[x]` only when the reviewer determines the requirements-quality criterion is satisfied.
**Marker Semantics**: `[x]` means the criterion has been reviewed and satisfied for requirements quality. It does not mean implementation work is complete.

## Requirement Completeness

- [ ] CHK001 Are requirements defined for every stage a pushed change passes through (check, test, package, deploy)? [Completeness, Spec §FR-001 to §FR-006]
- [ ] CHK002 Is there a requirement for removing a branch's deployment when the branch is deleted? [Gap, Edge Cases, Spec §Open Points]
- [ ] CHK003 Is there a requirement for what happens when a deployment fails part-way? [Gap]
- [ ] CHK004 Is there a requirement for returning a deployment to an earlier change? [Gap]
- [ ] CHK005 Are requirements defined for the one-time prerequisites, including who performs them? [Completeness, Edge Cases, Spec §FR-016]

## Requirement Clarity

- [ ] CHK006 Is "changes anything other than specifications and documentation" defined by naming the paths that count? [Clarity, Spec §FR-001]
- [ ] CHK007 Is "the organization's shared pipeline actions wherever one exists" specific enough to check, for example by listing the actions? [Clarity, Spec §FR-013]
- [ ] CHK008 Is "needed only to test or operate it" clear about where a tool used by a script, such as the invoke script, belongs? [Clarity, Spec §FR-009]
- [ ] CHK009 Is "accounts outside the organization cannot" stated precisely enough to audit against the repository's access policy? [Clarity, Spec §FR-005]

## Requirement Consistency

- [ ] CHK010 Does FR-010 (locked versions are used by developers, the pipeline and the package) agree with the edge case in which the pipeline's test stage resolves dependencies again? [Conflict, Spec §FR-010, Edge Cases, Spec §Open Points]
- [ ] CHK011 Does FR-007 (each branch is deployed separately) agree with the edge case that every deployment shares one account and one set of approval settings? [Consistency, Spec §FR-007, Edge Cases]
- [ ] CHK012 Does FR-001 agree with User Story 4 about a push that changes a specification and code together? [Consistency, Spec §FR-001, Spec §User Story 4]

## Acceptance Criteria Quality

- [ ] CHK013 Is the 15-minute target in SC-004 a decision by the owner, or only an observation of one run? [Measurability, Spec §SC-004, Spec §Assumptions]
- [ ] CHK014 Do SC-001 to SC-003 state a sample size, so that "100% of pushes" can be measured? [Measurability, Spec §SC-001, Spec §SC-002, Spec §SC-003]
- [ ] CHK015 Is there a success criterion for the tests needing no cloud credentials and making no model call? [Gap, Spec §FR-004]
- [ ] CHK016 Is there a success criterion for the package running as an unprivileged user? [Gap, Spec §FR-012]

## Scenario Coverage

- [ ] CHK017 Are requirements stated for both triggers (a push to `main`, a push to another branch) and for a manual start? [Coverage, Spec §User Story 1, Edge Cases]
- [ ] CHK018 Are requirements defined for two pushes to the same branch in quick succession? [Gap]
- [ ] CHK019 Are requirements defined for a branch whose name cannot be used for a deployment? [Coverage, Edge Cases]
- [ ] CHK020 Are requirements defined for updating a dependency, as distinct from adding one? [Coverage, Spec §User Story 3]

## Non-Functional Requirements

- [ ] CHK021 Are security requirements for the pipeline's credentials specific enough to audit? [Security, Spec §FR-015]
- [ ] CHK022 Is there a requirement on checking the agent's code beyond its tests (style, static checks, coverage)? [Gap, Spec §Open Points]
- [ ] CHK023 Is there a requirement on scanning the package or its dependencies for known vulnerabilities? [Gap]
- [ ] CHK024 Is there a requirement on the cost of branch deployments that are never removed? [Gap, Spec §Open Points]

## Dependencies & Assumptions

- [ ] CHK025 Is the dependency on the organization's shared actions stated with what happens when one changes its behavior? [Dependency, Spec §Assumptions]
- [ ] CHK026 Is the assumption that pipeline runs rarely overlap turned into a requirement where it matters? [Assumption, Spec §Assumptions]
- [ ] CHK027 Has the project owner decided each item under "Open Points"? [Assumption, Spec §Open Points]

## Notes

- Mark items `[x]` only after review confirms the requirement-quality criterion is satisfied
- Leave items unchecked when they still require clarification, correction, or reviewer evaluation
- `/speckit-implement` reads checklist checkbox state as a gate and must not modify markers
- `checklists/requirements.md` has a separate built-in lifecycle maintained by `/speckit-specify` and `/speckit-clarify`
- No item has been reviewed. All are unchecked because the reviewer, not the author, marks them
