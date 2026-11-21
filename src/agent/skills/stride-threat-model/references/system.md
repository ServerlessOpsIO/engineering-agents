# Stage: system

**Aim**: the participants describe the system as elements and trust boundaries. Describing
it is their work.

## The kinds of element

| Kind | What it is | Tool |
|---|---|---|
| Component | Something that runs and acts: a service, a function, an application, a job. | `add_element`, kind `component` |
| Data store | Somewhere data rests: a database, a bucket, a queue's storage, a log, a cache. | `add_element`, kind `data_store` |
| External party | A person or system outside the participants' control that the system deals with: a user, a browser, a partner's service. | `add_element`, kind `external_party` |
| Data flow | Data moving from one element to another. | `add_data_flow`, with the two identifiers and what travels |

## What to establish

Ask one question at a time. Record each answer as it comes and read it back with its
identifier.

1. What are the components?
2. Where does data rest?
3. Who or what outside the system does it deal with?
4. For each pair that talk to each other: what data moves, and in which direction? Go
   through the elements until every one has at least one data flow, or the participants
   say it has none.
5. Where are the trust boundaries?

## Trust boundaries

A trust boundary is a line between parts of the system that trust each other to different
degrees. Data that crosses one arrives somewhere that should not simply believe it.

Ways to find them. Ask about each, one at a time:

- Where does the system meet the internet, or anything the participants do not run?
- Where does one team's, one account's or one network's responsibility end and another's
  begin?
- Where does a request change from not signed in to signed in, or from an ordinary user
  to an administrator?
- Where does data pass from one process or machine to another?

Record each with the `add_trust_boundary` tool, giving the elements inside it.

Questions for a data flow that crosses a boundary, for use in the threats stage:

- What does the receiving side check before it trusts what arrives?
- What would the receiving side do with something it did not expect?
- What can be seen of this flow by someone on the less trusted side?

## Checking the description

A description with holes hides threats. Before the stage closes, ask about each of these
that the record leaves open, one at a time. They are questions about the description, not
about threats.

- For each data store: what writes to it, and what reads from it? A store nothing reads,
  or nothing writes, usually means a part of the system is missing.
- For each external party: which component does it talk to? Data does not move from a
  person to a store without a component in between.
- Is there any element with no data flow at all?
- Does every data flow say what travels on it?
- Are several parts that do the same job, inside the same trust boundary, better
  described as one element?

## If a repository has been named

- The participants still describe the system themselves. DO NOT describe it for them from
  the repository, even when asked.
- Read what describes the system and call `hold_finding` for each difference and each
  part nobody has mentioned, in the reply that read the file.
- Say nothing of what was found until the description is complete.

## Before closing the stage

- Ask whether the description is complete. When unsure whether the participants have said
  so, ask.
- When they say it is, call `description_complete`, or `complete_stage`, which does the
  same.
- Read the elements back as a short list with their identifiers.
