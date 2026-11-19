# Contract: the written model and the facilitator's notes

**Date**: 2026-11-19 | **Spec**: `specs/008-threat-model-session/spec.md`

Both documents are GitHub-flavoured Markdown, made by code in `src/agent/session/render.py`
from the session record (`data-model.md`). The same record always gives the same
document. Unit tests and `scripts/play_session.py` check a document against this file.

## Rules for both

- Text the participants gave is escaped so that it cannot break a table or the diagram:
  `|` becomes `\|`, a line break becomes a space, and a leading `#` or `>` is escaped.
- An empty value is written as an em dash in a table cell.
- Dates are UTC, `YYYY-MM-DD`.
- Nothing in either document comes from the model's own words at the time of writing.

## The written model

Headings are exactly these, in this order (FR-037). Every section is always present.

```markdown
# Threat model: {system}

> Status: **{Complete | Finished | In progress | Abandoned}**. {One line per unfinished or skipped stage.}

## Summary
## Scope
## System description
## Data flow diagram
## Threats
## Coverage
## Mitigations
## Open questions
## Method
```

### Status line

`Complete` when the session is finished and every stage is complete. `Finished` when it
is finished and a stage was skipped or left unfinished. Otherwise `In progress` or
`Abandoned`. Every status but `Complete` is followed by one line for each stage that is
not complete: `Not finished: Rating.` or
`Skipped: Rating.` (FR-014, FR-040). A section whose stage is skipped or not started
begins with the same words.

When anything is marked as changed after the notes (FR-059), the status block gains:
`Entries marked † were added or changed after the facilitator's notes were posted.`
And, when anything was removed after the notes:
`Removed after the facilitator's notes were posted: T3, M2.`

### Summary

A list: **System**, **Date** (the day the document was made), **Session started**,
**Participants** (names, in order of first message), **Joined after the session** (the
names of people who first wrote after it was finished or abandoned; left out when there
are none), and **Threats by severity**: a count
for each of Critical, High, Medium, Low, Note and Not rated.

### Scope

Three lists: **In scope**, **Out of scope**, **Assumptions**. An empty list reads
`None recorded.`

### System description

A table of elements, then a table of trust boundaries, then the files read.

| Identifier | Kind | Name | Description |
|---|---|---|---|

Data flows show `{from} → {to}` as their name and what travels as their description.

| Identifier | Trust boundary | Inside |
|---|---|---|

**Repository files read**: a list of `{repository}@{first 7 characters of the commit}: {path}`, or
`None.` When a repository could not be read in full, a line says so.

### Data flow diagram

One fenced `mermaid` block, a `flowchart LR`:

- Each component, data store and external party is a node whose identifier is its
  identifier in the record. Components are rectangles, data stores cylinders, external
  parties rounded. The label is `{id}: {name}`, in double quotes, with `"` replaced by
  `'` and brackets removed.
- Each trust boundary is a `subgraph` holding the nodes inside it. An element inside two
  boundaries is drawn in the first, and the second is named in a comment line.
- Each data flow is an arrow labelled `{id}: {data}`.
- With no elements, the block is replaced by `No elements recorded.`

The diagram must be accepted by Mermaid for any record. Unit tests cover names with
quotes, brackets, pipes and Markdown characters.

### Threats

One row per threat, ordered by severity, most severe first, then by identifier.

| ID | Category | Element | Threat | Likelihood | Impact | Severity | Decision | Decided by | Owner |
|---|---|---|---|---|---|---|---|---|---|

- **Likelihood** and **Impact** cells read `High: {reason}`.
- **Decision** reads `Accept: {reason}` when a reason was given.
- **Owner** reads `None named` when the participants named none.
- An entry changed after the notes has `†` after its identifier.
- With no threats: `No threats recorded.`

### Coverage

One row per element. One column per STRIDE category.

| Element | S | T | R | I | D | E |
|---|---|---|---|---|---|---|

Each cell is one of:

| Cell | Meaning |
|---|---|
| `T1, T4` | The threats recorded there. |
| `None found` | The participants looked and recorded none. |
| `Not considered` | The category applies to this kind of element and nothing was recorded. |
| `n/a` | The category does not normally apply to this kind of element (`data-model.md`). |

A line under the table gives the letters' meanings.

### Mitigations

| ID | Mitigation | Addresses | Owner |
|---|---|---|---|

Then, when any exist: **Threats to be mitigated with no mitigation recorded**, a list of
their identifiers.

### Open questions

A numbered list, or `None.`

### Method

Fixed text, with a link to each source:

> This model was made in a session led by STRIDEr, an AI agent. The participants named
> the threats, rated them and decided what to do. STRIDEr asked the questions and
> recorded the answers. Threats were looked for with STRIDE, element by element.
> Likelihood and impact were judged by the participants as high, medium or low, and
> severity was read from the table of the OWASP Risk Rating Methodology.

## The facilitator's notes

```markdown
# Facilitator's notes: {system}

> These are STRIDEr's own observations from the session. The participants have not
> checked them, and they are not part of the participants' threat model.

## Hinted at, and not taken up
## Not raised in the session
## Questioned, and kept
```

- **Hinted at, and not taken up**: one item per hint not taken up: the stage, the element
  and the point.
- **Not raised in the session**: one item per `not_raised` note, each ending
  `(not raised in the session)`.
- **Questioned, and kept**: one item per `questioned_kept` note: the threat or mitigation
  and what was questioned.
- An empty section reads `Nothing.`

First made by a confirmed `finish` or `abandon`, and never before (FR-056). After that
they come again, unchanged, whenever the model is asked for.
