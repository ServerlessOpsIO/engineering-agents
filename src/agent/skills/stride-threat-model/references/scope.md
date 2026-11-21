# Stage: scope

**Aim**: agree what system is being modelled, what is left out, and what is assumed.

## What to establish

Ask one question at a time, in roughly this order. Skip a question the participants have
already answered.

1. What does the system do, in a sentence or two, and who uses it?
2. What is in scope for this session: which parts, which environments?
3. What is deliberately left out, and why?
4. What is being assumed to be safe or handled elsewhere, such as the cloud provider,
   the network, or another team's service?
5. What would hurt most if it went wrong: which data or which function matters most?

## Recording

- Use the `add_scope_item` tool with kind `included` for each thing in scope, `excluded`
  for each thing left out, and `assumption` for each assumption.
- The answer to "what would hurt most" is recorded as an `included` item, in the
  participants' words. It guides the later stages.

## Before closing the stage

- Read the scope back in a few lines.
- If something that plainly belongs to the system has not been placed in or out of scope,
  one hint is allowed in this stage (see Hints).
- Then call `complete_stage`.
