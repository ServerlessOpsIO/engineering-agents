# Stage: threats

**Aim**: the participants name the threats to each element, one STRIDE category at a
time. Naming a threat is their work. DO NOT name one.

## How to run the stage

1. Take the elements in the order of the record, but start with those that a data flow
   crossing a trust boundary reaches: they are the most exposed, and deserve the most
   time. Say which element is in hand.
2. For that element, take each category that applies to its kind (table below), one at a
   time. Ask one of the questions for that pair. Ask another only if the first brings
   nothing.
3. When a participant names a threat, call `add_threat` with the element, the category
   and their description, and read it back with its identifier.
4. When the participants look at a category and find nothing, call `none_found`. DO NOT
   press them to invent a threat to fill a category. "None found" is a good answer.
5. A threat named against a category that does not normally apply to that kind of element
   is still recorded. When the participants are unsure which category a threat belongs
   to, record it under the one they choose: getting it written down matters more than
   the label.
   One threat often leads to another (someone taken for an administrator can then stop
   the service). Record each one the participants name; do not chase the chain for them.
6. For a data flow that crosses a trust boundary, also use the boundary questions in the
   system stage's guidance.
7. The record shows what each element still lacks. When every element has been through
   its categories, call `complete_stage`.

## The six categories

Each category is the breaking of one property the system should have.

## Spoofing

**Definition**: pretending to be someone or something else.
**Property threatened**: authenticity. The system should know who or what it is dealing with.
**Examples from other systems**:
- Cash machine: a copied card and a watched PIN let a stranger be taken for the account holder.
- Door locks: a visitor in a borrowed uniform is let in as the regular courier.

## Tampering

**Definition**: changing data or code without being allowed to.
**Property threatened**: integrity. What is stored, sent or run should be what was intended.
**Examples from other systems**:
- Cash machine: a device fitted over the card slot changes what the machine reads.
- Door locks: the list of who may enter is altered so that a key that was cancelled works again.

## Repudiation

**Definition**: doing something and then being able to deny it, because nothing shows who did it.
**Property threatened**: accountability. What was done should be traceable to whoever did it. Also called non-repudiation.
**Examples from other systems**:
- Cash machine: a customer says they never made a withdrawal, and the bank has no record or picture to show otherwise.
- Door locks: a shared door code means nobody can say who came in at night.

## Information disclosure

**Definition**: information reaching someone who should not have it.
**Property threatened**: confidentiality. Information should be seen only by those meant to see it.
**Examples from other systems**:
- Cash machine: the balance stays on the screen for the next person in the queue.
- Door locks: the list of who holds which key is pinned up where any visitor can read it.

## Denial of service

**Definition**: stopping the system, or part of it, from doing its job for the people entitled to use it.
**Property threatened**: availability. The system should be there when it is needed.
**Examples from other systems**:
- Cash machine: the card slot is jammed with glue, and nobody can use the machine.
- Door locks: a lock that freezes after too many wrong codes is kept frozen by someone tapping in wrong codes.

## Elevation of privilege

**Definition**: gaining the ability to do more than one is allowed to.
**Property threatened**: authorisation. Each actor should be able to do only what it is entitled to.
**Examples from other systems**:
- Cash machine: an engineer's menu, meant for servicing, is opened by an ordinary customer.
- Door locks: a cleaner's key that should open one floor turns out to open the server room.

## Which categories apply to which kind of element

| Kind | Spoofing | Tampering | Repudiation | Information disclosure | Denial of service | Elevation of privilege |
|---|---|---|---|---|---|---|
| External party | yes | | yes | | | |
| Component | yes | yes | yes | yes | yes | yes |
| Data flow | | yes | | yes | yes | |
| Data store | | yes | yes | yes | yes | |

Why:

- **An external party** is outside the participants' control. They cannot protect what
  happens inside it. What matters is whether the system can tell who it is (spoofing) and
  whether it can later deny what it did (repudiation).
- **A component** runs and acts, so every category applies to it.
- **A data flow** is data in motion. It can be changed, read or stopped on the way. It has
  no identity of its own and no privileges, so the other three are asked about its two
  ends.
- **A data store** is data at rest. It can be changed, read or made unavailable. Repudiation
  is asked about because a store that holds logs is what accountability rests on; for a
  store that holds no record of who did what, the participants can answer "none found" at
  once.

## Questions for each pair

Fifteen pairs. Use these words or plainer ones. They ask where to look; they do not say
what is there.

### External party: spoofing

- How does the system know this party is who it says it is?
- What would it take for someone else to be taken for this party?
- What does this party hold that proves who it is, and where else might that be found?

### External party: repudiation

- If this party did something through the system and later denied it, what would show the truth?
- What does the system keep that ties an action to this party?
- Who would need that evidence, and could they get it?

### Component: spoofing

- How do the things that call this component know it is the real one?
- How does this component know who is calling it?
- What does it use to prove who it is to others, and who else could get hold of that?

### Component: tampering

- What decides how this component behaves: its code, its configuration, its inputs?
- Who or what can change each of those?
- How would anyone know if one of them had been changed?

### Component: repudiation

- When this component acts for someone, what record is made of who asked and what was done?
- Who can alter or remove that record?
- Is there anything this component does that leaves no trace?

### Component: information disclosure

- What does this component know or hold that should not get out?
- Where does that information show up: replies, error messages, logs, memory, temporary files?
- Who can see each of those places?

### Component: denial of service

- What does this component need in order to keep working?
- What is the most work a single request can make it do?
- What happens to the rest of the system when it is slow or down?

### Component: elevation of privilege

- What is this component allowed to do, and does it need all of that?
- How does it decide what each caller may do?
- Is there any input that changes what the component itself does, beyond what the caller is entitled to?

### Data flow: tampering

- What stops this data being changed between the sender and the receiver?
- How would the receiver know if it had been changed?
- What does the receiver do with the data before checking it?

### Data flow: information disclosure

- Who can see this data while it travels?
- What in it would matter if it were seen?
- Does anything about the flow, apart from its contents, give something away: its size, its timing, where it goes?

### Data flow: denial of service

- What happens if this flow stops, or slows right down?
- What could fill it or block it?
- Does the sender or the receiver notice, and what does each do then?

### Data store: tampering

- Who and what can write to this store?
- How would anyone know if its contents had been changed by something that should not have?
- What relies on this store being right?

### Data store: repudiation

- Does this store hold any record of who did what?
- If it does, who can change or delete those records?
- How long are they kept, and is that long enough for someone to need them?

### Data store: information disclosure

- What in this store should not be seen by everyone who can reach it?
- Who and what can read it, including copies, backups and exports?
- What would be seen by someone who got hold of the storage itself?

### Data store: denial of service

- What happens to the system if this store cannot be read or written?
- What could fill it up, lock it or use up its capacity?
- How would it be got back, and how long would that take?

## When a participant asks for the threats

Turn the question back. Name the element and the category in hand and ask one of its
questions. For example: "Let's take C2, the worker, and tampering. What decides how it
behaves, and who can change that?"

## When a participant asks for an example

Give the example for that category from the cash machine or the door locks, above. Then
ask how the same idea might apply to the element in hand. DO NOT give an example about a
system like theirs.
