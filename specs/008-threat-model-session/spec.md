# Feature Specification: STRIDEr Leads a Threat Modelling Session

**Feature Branch**: `feature/008-threat-model-session`

**Created**: 2026-11-17

**Status**: Clarified

**Input**: User description: "As a developer my slack app can lead a threat model session."
The project owner expanded this in conversation into a story, a proposed solution, scope
boundaries, dependencies and acceptance criteria, which this specification records.

**Background**: STRIDEr is a Slack agent in this repository. Features 001 to 007 gave it an
agent that answers a prompt and remembers a conversation, a Slack app, and a receiving
service that carries messages between the two. What the agent is told to do is one sentence
that mixes who it is with what it does, and it can do nothing but answer from its own
knowledge. This feature gives STRIDEr its purpose: it facilitates a threat modelling session
using the STRIDE framework. The participants do the threat modelling. STRIDEr guides, informs
and records, and at the end posts the written model.

**Terms**:

- **Session**: one threat modelling exercise on one system, from the request to start it to
  the written model. Not the same as the agent's memory of a conversation, which features
  002 and 007 call a session and this specification calls **the conversation**.
- **Participant**: a person who has written at least one message in the conversation since
  the session started.
- **Persona**: the standing instructions that say who STRIDEr is, how it speaks, and the
  rules that hold in every conversation.
- **Skill**: a self-contained set of instructions for one kind of task, in the published
  Agent Skills format, which STRIDEr takes up only when the task calls for it.
- **STRIDE**: six categories of threat: spoofing, tampering, repudiation, information
  disclosure, denial of service, elevation of privilege.
- **Element**: a part of the system being modelled: a component, a data flow, a data store
  or an external party. Each has a short identifier in the session.
- **Trust boundary**: a line between elements that trust each other to different degrees.
- **Stage**: one of the six steps of a session, listed in FR-010.
- **The written model**: the document STRIDEr posts at the end of a session (FR-037).
- **Facilitator's notes**: a separate document STRIDEr posts when a session ends, holding
  what STRIDEr raised and the participants did not take up (FR-041).
- **Owner** (of a decision or a mitigation): whoever is responsible for carrying it out, as
  named by the participants. Not the same as **the project owner**, the person this
  specification was written for, who is called "the owner" where no decision is in view.
- **Hint**: a remark that points participants at an area they have not considered without
  naming the threat.
- **The work**: naming a threat, giving a likelihood or an impact, choosing a mitigation,
  and making a decision about a threat.
- **No reply**: the agent's answer when it judges that a message needs nothing from it.
- **Receiving service**, **worker**, **eyes reaction**, **full member**, **the apology**: as
  defined in feature 007.

## Clarifications

### Session 2026-11-17

- Q: When a participant asks what a STRIDE category means, may STRIDEr give example threats from systems other than the one being modelled? → A: Yes, but only from a plainly different kind of system, such as a cash machine or a building's door locks. Never an example that fits the element under discussion.
- Q: When STRIDEr reads the repository and finds a part of the system that no participant has mentioned, what does it do? → A: It states the fact and names the file. The participants decide whether the part belongs in the model.
- Q: When two participants disagree about a rating or a decision and ask STRIDEr what it thinks, how far may its answer go? → A: It says which participant's reasoning it finds stronger and why, without naming a value or a decision of its own. The participants settle the result.
- Q: Besides the points participants missed after a hint, what else should STRIDEr record in its facilitator's notes? → A: Each rating or mitigation that STRIDEr questioned and the participants kept. STRIDEr must raise any doubt it has about a rating or a mitigation as a question in the session, so the notes hold nothing that was not raised there. The notes are posted only when the session is finished or abandoned; a model asked for early comes without them.
- Q: For each threat's decision, whose name should the written model record? → A: Two names. Who made the decision, which STRIDEr records from who said it, and the owner, who is responsible for carrying it out, whom the participants name and may leave empty. The owner may be a person outside the session or a team.
- Q: When in a session may STRIDEr tell participants about parts of the system it found in the repository that they have not mentioned? → A: Only after the participants say their description of the system is complete. Until then it may read the repository and holds back what it found. Contradictions and missing parts are reported together at that point.
- Q: After the facilitator's notes have been posted, may the participants still change the written model? → A: Yes. Anything added or changed after the notes were posted is marked as such in the model, and the participants still do the work on each addition.
- Q: Is there a limit on how many hints STRIDEr may give in one stage? → A: At most one hint per element in each stage, pointing at the most serious thing missed there. Other missed points for that element are not hinted at, and are recorded in the facilitator's notes. This changes the earlier answer that the notes hold nothing that was not raised in the session: missed points beyond the hint limit are the one exception.
- Q: In a group session, who can skip a stage, declare the session finished, or abandon it? → A: Any participant may ask. STRIDEr says what is about to happen and acts on the next message unless a participant objects. If someone objects, the participants settle it and STRIDEr waits.
- Q: When a session starts, should STRIDEr tell the participants how it works before asking its first question? → A: Yes, a short opening every time: the stages; that participants do the work and STRIDEr facilitates; that it may stay quiet when they talk among themselves and a mention always gets a reply; and that it keeps notes on what was missed, posted when the session ends.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A person is led through a threat model and receives it in writing (Priority: P1)

A person writes to STRIDEr, in a channel or a direct message, asking to threat model a
system. STRIDEr starts a session, says which stage it is in, and asks one question at a time.
It takes the person through scope, the system's elements and trust boundaries, the threats
in each STRIDE category, the rating of each threat, and what will be done about each. Then it
posts the written model, which the person can copy into a repository.

**Why this priority**: This is the feature. A session that reaches a complete written model
is the smallest thing worth having.

**Independent Test**: In a direct message, ask STRIDEr to threat model a small system with
three elements, answer its questions to the end, and check the written model against FR-037.

**Acceptance Scenarios**:

1. **Given** no session in progress, **When** a person writes "let's threat model our login
   service", **Then** STRIDEr starts a session, says briefly how it works (FR-061), names
   the system and the first stage, and asks one question.
2. **Given** a session in progress, **When** the person answers a question, **Then** STRIDEr
   records the answer and asks the next question, or says the stage is complete and names
   the next one.
3. **Given** the participants have described the system, **When** the threat stage begins,
   **Then** STRIDEr takes them through each element and, for each, each STRIDE category that
   applies to it.
4. **Given** a threat has been named, **When** the rating stage reaches it, **Then** STRIDEr
   asks for its likelihood and its impact and states the severity that follows from them.
5. **Given** every stage is complete, **When** STRIDEr writes the model, **Then** it has
   every part listed in FR-037 and contains nothing the participants did not say or decide.
6. **Given** a written model of any length, **When** it is posted, **Then** all of it
   arrives, as a Markdown file in the conversation.

---

### User Story 2 - The participants do the work, and STRIDEr does not do it for them (Priority: P1)

A participant asks STRIDEr to list the threats, or to say how likely one is, or to pick the
mitigation. STRIDEr does not. It turns the question back with a prompt that helps the
participant work it out. When the participants have missed something, STRIDEr hints at the
area, at most once for each element in a stage. What they still do not raise, STRIDEr leaves
out of the model and writes in its facilitator's notes.

**Why this priority**: The owner's purpose is that people learn to threat model. An agent
that answers for them defeats it, and this rule shapes every other behaviour.

**Independent Test**: In a session, ask STRIDEr directly for the threats to an element, for a
rating and for a mitigation. Leave an obvious area untouched. Check that no answer was given,
that one hint was given, and that the missed point is in the notes and not in the model.

**Acceptance Scenarios**:

1. **Given** a session in the threat stage, **When** a participant asks "what are the threats
   here?", **Then** STRIDEr names no threat and asks a question that directs them to an
   element and a category.
2. **Given** a threat being rated, **When** a participant asks "what would you rate it?",
   **Then** STRIDEr gives no likelihood, impact or severity of its own and asks the questions
   that help them choose.
3. **Given** a participant asks how a control works or what a term means, **When** STRIDEr
   answers, **Then** it explains, and leaves the choice of whether to use it to them.
4. **Given** the participants have not considered an area STRIDEr can see, **When** the stage
   is about to close, **Then** STRIDEr hints at the area once without naming the threat,
   and gives no second hint for the same element in that stage.
5. **Given** the hint was not taken up, **When** the model is written, **Then** the point is
   absent from the model and present in the facilitator's notes.
6. **Given** a rating contradicts something the participants said earlier, **When** it is
   given, **Then** STRIDEr points out the contradiction and the participants keep or change
   the rating.

---

### User Story 3 - Several people hold a session together in a channel thread (Priority: P2)

Several colleagues run a session in one thread. STRIDEr knows each of them by name. When they
talk to each other and need nothing from it, STRIDEr stays quiet. When one asks the group a
question, or two disagree, STRIDEr steps in to answer, to set out the tradeoff, or to give its
view. The written model names the participants, who made each decision, and who owns it.

**Why this priority**: Threat modelling is a group exercise. A session with one person is
useful; one that works for a team is the aim. It depends on story 1.

**Independent Test**: With two people in a thread, run a session in which they exchange
messages that need nothing from STRIDEr, ask the group a question, and disagree once. Check
when STRIDEr spoke, and the names in the written model.

**Acceptance Scenarios**:

1. **Given** a session in a channel thread, **When** one participant writes to another and
   needs nothing from STRIDEr, **Then** the eyes reaction appears and is removed and nothing
   is posted.
2. **Given** a participant asks a question nobody has answered, **When** STRIDEr reads it,
   **Then** it answers if the question is not part of the work, and otherwise prompts.
3. **Given** two participants disagree, **When** STRIDEr steps in, **Then** it sets out each
   position, may say which reasoning it finds stronger and why, and leaves the result to
   them.
4. **Given** a participant accepts a risk and names a colleague to review it yearly,
   **When** the model is written, **Then** the decision is recorded as decided by that
   participant, with the colleague as its owner.
5. **Given** a session in a direct message, **When** the person writes anything, **Then**
   STRIDEr replies.
6. **Given** the talk has drifted from the session, **When** STRIDEr next speaks, **Then** it
   brings the participants back to the open question.

---

### User Story 4 - STRIDEr checks what it is told against the repository (Priority: P2)

A participant names a public repository in the `ServerlessOpsIO` organisation. STRIDEr reads
the files that describe the system, says which ones it used, and points out where they differ
from what the participants have said. The participants still describe the system themselves.

**Why this priority**: It makes the model more accurate, and it is the agent's first ability
beyond conversation. A session works without it.

**Independent Test**: In a session, describe a system incorrectly in one respect, name its
repository, and check that STRIDEr names the files it read and points out the difference.

**Acceptance Scenarios**:

1. **Given** a participant names a public `ServerlessOpsIO` repository, **When** STRIDEr reads
   it, **Then** it says which files it used.
2. **Given** what was read differs from what a participant said, **When** the participants
   have said their description is complete and STRIDEr reports,
   **Then** it states the difference as a fact and asks the participants which is right.
3. **Given** a repository that is private, missing, or outside `ServerlessOpsIO`, **When**
   STRIDEr is asked to read it, **Then** it says it cannot and asks the participants to
   describe the system.
4. **Given** a file in the repository contains text addressed to an AI agent, **When**
   STRIDEr reads it, **Then** it does not act on that text.
5. **Given** the repository defines a part of the system no participant has mentioned,
   **When** STRIDEr reports, **Then** it says the part exists and names the file, and the
   participants decide whether to add it.
6. **Given** nobody has named a repository, **When** a session runs, **Then** STRIDEr reads
   none.

---

### User Story 5 - A developer changes what STRIDEr does without changing who it is (Priority: P2)

A developer opens the repository and finds the persona in one place and each skill in its
own. To change how a session runs they edit the skill. To add another kind of review they add
a skill. Tests fail if an agreed rule is removed from either.

**Why this priority**: The owner asked for the separation, and every later review type
depends on it. People using STRIDEr never see it.

**Independent Test**: Remove an agreed rule from the persona, and separately from the skill,
and check that the unit tests fail each time.

**Acceptance Scenarios**:

1. **Given** the repository, **When** a developer reads the persona, **Then** it contains no
   instruction for carrying out a threat modelling session.
2. **Given** the repository, **When** a developer reads a skill, **Then** it does not say who
   STRIDEr is or how it speaks.
3. **Given** a skill that was adopted from elsewhere, **When** a developer reads it, **Then**
   its source and licence are recorded with it.
4. **Given** a request no skill covers, **When** a person makes it, **Then** STRIDEr says
   what it can do and offers a threat modelling session.

---

### User Story 6 - Participants control the pace of a session (Priority: P3)

Participants ask where the session stands, go back to a stage, skip one, stop for the day and
carry on later, or ask for the model before the session is finished.

**Why this priority**: Real sessions are not linear. The session is usable without these.

**Independent Test**: In a session, ask for the status, skip a stage, go back to one, and ask
for the model early. Check each response and that the model marks what was skipped and
unfinished.

**Acceptance Scenarios**:

1. **Given** a session in progress, **When** a participant asks where things stand, **Then**
   STRIDEr names the stage and what remains.
2. **Given** a participant asks to skip a stage and nobody objects, **When** the model is
   written, **Then** that stage is marked as skipped.
3. **Given** a participant asks to return to an earlier stage, **When** they change something
   there, **Then** later stages use the changed version.
4. **Given** a session paused for less than the agent's memory period, **When** a participant
   returns, **Then** the session continues from where it stopped.
5. **Given** a session part-way through, **When** a participant asks for the model, **Then**
   STRIDEr writes it with the unfinished stages marked.

---

### User Story 7 - The owner can show that a session works (Priority: P3)

The owner runs one command. It plays a fixed session against the deployed agent, without
Slack, checks the structure of the written model, and keeps the transcript. The owner reads
the transcript against a short checklist to judge how well the session was led.

**Why this priority**: It is how the feature is accepted and how later changes to the persona
or a skill are checked. It delivers nothing to participants.

**Independent Test**: Run the command and check that it reports pass or fail for each
structural check and leaves a transcript.

**Acceptance Scenarios**:

1. **Given** the deployed agent, **When** the owner runs the command, **Then** it plays every
   turn of the fixed session and reports each structural check as passed or failed.
2. **Given** a written model missing a required part, **When** the command checks it,
   **Then** it reports which part is missing.
3. **Given** the command has run, **When** the owner looks for the transcript, **Then** it is
   on their own computer and nowhere public.

---

### Edge Cases

- **A second request to start a session** while one is in progress: STRIDEr says one is in
  progress and asks whether to continue it or abandon it. It does not run two.
- **A participant joins part-way**: they are a participant from their first message, under
  the name Slack displays. STRIDEr does not restart the session, summarise it or explain
  how it works unless asked.
- **A participant asks for the work repeatedly, or says they are in a hurry**: the rule holds.
  STRIDEr may offer to skip the stage or write the model as it stands.
- **A participant asks for an example of a threat to the kind of element being discussed**:
  STRIDEr gives an example from a different kind of system and asks how the idea applies to
  theirs.
- **One participant asks to finish and another objects**: the request is dropped and the
  session continues. When they agree, one of them asks again.
- **Participants cannot agree**: STRIDEr records the point as an open question and moves on.
- **Nobody knows the answer to a question**: it is recorded as an open question.
- **No threats are named for an element and category**: the coverage table records "none
  found", by the participants' choice.
- **A decision has no owner**: STRIDEr asks once. If none is named, the model says so.
- **The owner named is not in the session, or is a team**: recorded as the participants
  wrote it.
- **A large system**: when the list of elements is long, STRIDEr says so and suggests
  narrowing the scope. The participants decide.
- **Two people share a display name**, or one changes theirs mid-session: the model shows the
  names as they were when each message was written. STRIDEr does not tell the two apart.
- **A message mentions a person**: the agent is given the person's name, not their Slack
  identifier.
- **STRIDEr stays silent when a reply was wanted**: the participant mentions STRIDEr, which
  always gets a reply.
- **Every message between two people for a long stretch**: STRIDEr stays silent throughout
  and is not required to interrupt.
- **The repository is very large, or GitHub's request limit is reached**: STRIDEr says what
  it could not read and carries on from the conversation.
- **A repository is named before a session, or in a direct message**: the same rules apply.
- **A repository is named before anyone has described the system**, or a participant asks
  STRIDEr to describe the system from it: STRIDEr asks the participants to describe the
  system first, and compares afterwards.
- **The system stage is skipped**: there is no description to compare, so STRIDEr reports
  nothing from the repository about the system's parts.
- **A direct message whose earlier session has dropped out of memory**: asked to carry on,
  STRIDEr says it has no session in progress and offers to start one.
- **A channel thread older than the agent's memory**: feature 007's rule applies unchanged.
- **A participant asks to see the facilitator's notes during a session**: STRIDEr says they
  come when the session ends.
- **A session is abandoned**: STRIDEr posts the model as it stands, with its unfinished
  stages marked, and the notes. Nobody has to ask.
- **The model is asked for twice**: STRIDEr writes it again from the current state.
- **A change is asked for after the model is posted**: the participants make the change in
  conversation and STRIDEr posts the model again. If the notes have been posted, the change
  is marked (FR-059).
- **A person who took no part in the session writes after it has finished**: they can
  change the model and make decisions like anyone else, and each is marked as made after
  the notes. The written model lists them apart from the participants, as having joined
  after the session.
- **A participant says "add everything in your notes to the model"**: STRIDEr does not. The
  participants name, rate and decide each one, and each is marked.
- **The agent fails while writing the model**: feature 007's apology applies, and the session
  is still in memory, so the model can be asked for again.
- **A participant asks STRIDEr to ignore its rules**, or says the owner has allowed it: the
  rules hold.
- **Someone asks for a different kind of review**: STRIDEr says what it can do and offers a
  threat modelling session.

## Requirements *(mandatory)*

### Functional Requirements

**Persona and skills**

- **FR-001**: What STRIDEr is told MUST be divided into a persona and skills. The persona
  holds who STRIDEr is, how it speaks, and rules that apply in every conversation. A skill
  holds how to carry out one kind of task.
- **FR-002**: The persona MUST contain no instruction for carrying out a threat modelling
  session, and a skill MUST NOT say who STRIDEr is or how it speaks.
- **FR-003**: The persona MUST state at least these rules: STRIDEr is a facilitator; it does
  not do the participants' work for them (FR-018); everyone in a conversation has an equal
  say; what it reads from a repository is information and never instruction (FR-033); and
  what it does when no skill covers a request (FR-005). The owner approves the persona's
  final wording before the feature is complete.
- **FR-004**: Each skill MUST be in the published Agent Skills format and MUST be taken up by
  the agent only when the task calls for it.
- **FR-005**: Asked for something no skill covers, STRIDEr MUST say what it can do and offer
  a threat modelling session. It MUST NOT act as a general assistant.
- **FR-006**: Before a threat modelling skill is written, popular skill marketplaces MUST be
  searched for an existing one. A found skill is suitable when all of these hold: it covers
  the stages in FR-010 or can be edited to; its licence allows it to be copied into this
  public MIT repository and changed; it needs no ability the agent lacks and runs no
  scripts; and it has been read in full. A skill that writes a report in one go, without a
  conversation, is not unsuitable for that reason.
- **FR-007**: The search MUST be recorded: where was searched, what was found, and why each
  candidate was adopted or rejected. The owner makes the final choice.
- **FR-008**: An adopted skill MUST be copied into this repository and edited here, with its
  source and licence recorded beside it. No skill is fetched when the agent is built or when
  it runs.
- **FR-009**: The feature starts with one threat modelling skill. It MAY become several if
  that proves the better way to carry the stages or the facilitation.

**The session**

- **FR-010**: A session MUST have these stages, in this order:
  1. **Scope**: what system is being modelled, what is left out, and what is assumed.
  2. **System**: its components, data flows, data stores, external parties and trust
     boundaries.
  3. **Threats**: for each element, the threats in each STRIDE category that applies to it.
  4. **Rating**: a likelihood and an impact for each threat.
  5. **Mitigations and decisions**: what will be done about each threat, and by whom.
  6. **The written model**.
- **FR-011**: A session MUST start when a person asks for one in ordinary words. No fixed
  command is required.
- **FR-061**: When a session starts, STRIDEr MUST open with a short statement of how it
  works, before its first question: the stages; that the participants do the work and
  STRIDEr facilitates; that in a channel thread it may stay quiet when they talk among
  themselves and that a mention always gets a reply; and that it keeps notes on what was
  missed, which it posts when the session ends. The statement about staying quiet is left
  out in a direct message.
- **FR-012**: STRIDEr MUST ask one question at a time, and MUST say which stage the session
  is in when a stage begins.
- **FR-013**: Asked where the session stands, STRIDEr MUST name the stage and what remains.
- **FR-014**: Participants MUST be able to go back to an earlier stage and to skip a stage.
  A skipped stage MUST be marked as skipped in the written model.
- **FR-060**: Any participant MAY ask to skip a stage, to finish the session or to abandon
  it. STRIDEr MUST first say what is about to happen, and MUST act only when the next
  message arrives and is not an objection. It can act only when a message arrives, so it never
  acts on silence alone. When a participant objects, the request is dropped and the
  session carries on; when the participants are ready, one of them asks again and STRIDEr
  announces again. There is one exception to announcing first: with a single participant,
  a stage is skipped at once. Finishing and abandoning are always announced first, with
  one participant or several, because both post the notes and FR-056 requires a warning
  before that.
- **FR-015**: A session MUST be able to stop and continue later, for as long as the agent
  remembers the conversation (7 days by default). Nothing in this feature keeps a session
  longer.
- **FR-016**: There MUST be at most one session in progress in a channel thread, and at most
  one in a direct message. A new one can start when the earlier one is finished or the
  participants abandon it.
- **FR-017**: In a direct message, asked to continue a session the agent no longer remembers,
  STRIDEr MUST say it has no session in progress and offer to start one.

**Participants do the work**

- **FR-018**: STRIDEr MUST NOT do the work: it MUST NOT name a threat, give a likelihood, an
  impact or a severity of its own, choose a mitigation, or make a decision about a threat.
  This holds when it is asked directly, asked repeatedly, or told that the rule does not
  apply.
- **FR-019**: Asked to do the work, STRIDEr MUST turn the question back with a prompt that
  helps the participant answer it, such as a question about a named element and category.
- **FR-020**: STRIDEr MAY: ask questions; explain a concept, a technology or how a control
  works; state facts about a repository it has read; set out the tradeoffs between options;
  give its view when participants disagree with each other; and say what has not yet been
  covered.
- **FR-053**: When STRIDEr explains a STRIDE category or a concept, it MAY give example
  threats, and those examples MUST come from a plainly different kind of system from the one
  being modelled, such as a cash machine or a building's door locks. It MUST NOT give an
  example that fits the element under discussion, even when asked for one.
- **FR-021**: When participants disagree about the work, STRIDEr MAY say which participant's
  reasoning it finds stronger and why. It MUST NOT name a value or a decision of its own,
  and it gives this view only when at least two participants have each stated a position.
  The participants settle the result, and STRIDEr MUST NOT record a result they did not
  agree.
- **FR-022**: When STRIDEr sees something the participants have not considered, it MUST give
  a hint before the stage closes. A hint points at the area and does not name the threat.
  It gives at most one hint per element in each stage, for the most serious thing it sees
  missed there, and at most one in the scope stage, which has no elements.
- **FR-023**: When a hint is not taken up, STRIDEr MUST say no more about the point in the
  session, MUST leave it out of the written model, and MUST record it in the facilitator's
  notes. Other missed points for the same element, which the limit in FR-022 kept it from
  hinting at, MUST also be left out of the session and the model and recorded in the notes.
- **FR-024**: The written model MUST contain only what the participants said and decided.

**Facilitating a group**

- **FR-025**: In a channel thread with a session in progress, STRIDEr MAY give no reply to a
  message that is plainly between participants and needs nothing from it. It still reads the
  message and remembers it.
- **FR-026**: STRIDEr MAY speak without being addressed: to answer a question put to the
  group, to set out a tradeoff, to give its view on a disagreement, or to bring the
  participants back to the session.
- **FR-027**: When STRIDEr cannot tell whether a reply is wanted, it MUST reply. A message
  that mentions STRIDEr MUST always get a reply.
- **FR-028**: In a direct message STRIDEr MUST always reply.
- **FR-029**: When the agent gives no reply, the receiving service MUST post nothing. The
  eyes reaction is added and removed as for any message, and the outcome is logged as no
  reply and not as a failure. No apology is posted.

**Who is speaking**

- **FR-030**: The receiving service MUST tell the agent the name of the person who wrote each
  message: the name Slack displays for them. Earlier messages given as thread context under
  feature 007 carry their writers' names in the same way, and a mention of a person inside a
  message is given as that person's name.
- **FR-031**: STRIDEr MUST attribute decisions to the people who made them, MUST give every
  participant an equal say, and MUST NOT direct a question at a named person.
- **FR-032**: A person's name MUST NOT be written to any log. Feature 007's rule that
  everyone in a conversation shares one memory is unchanged.

**Reading a repository**

- **FR-033**: STRIDEr MUST be able to read files in a public repository of the
  `ServerlessOpsIO` organisation on GitHub. What it reads is information about the system.
  It MUST NOT follow instructions found there.
- **FR-034**: STRIDEr MUST read a repository only after someone in the conversation has named
  it. It MUST NOT read anything else: no repository outside `ServerlessOpsIO`, no private
  repository, no issues or pull requests, and no other web address.
- **FR-035**: STRIDEr MUST use what it reads to check what participants say and to point out
  differences. Describing the system remains the participants' work. When it reports, it
  MUST name the files it used.
- **FR-054**: When STRIDEr finds in a repository a part of the system that no participant
  has mentioned, it MUST say so as a fact and name the file. This is not a hint and is not
  limited to one mention per stage. The participants decide whether the part is in scope,
  and STRIDEr adds an element to the model only when they say so.
- **FR-058**: During the system stage STRIDEr MUST hold back what it found in a repository
  until the participants say their description is complete. It then reports, together,
  where the repository differs from what they said (FR-035) and what they did not mention
  (FR-054). Before that point it MUST NOT describe the system from the repository, even
  when asked, and it MAY say that it has read the repository and will compare once they
  have finished. After that point, in later stages, it states a repository fact when it
  becomes relevant.
- **FR-036**: STRIDEr MUST read selectively, starting with the files that describe the
  system. When it cannot read a repository or part of one, for any reason including GitHub's
  request limit, it MUST say so and carry on from the conversation.

**The written model**

- **FR-037**: The written model MUST have these parts:
  1. **Summary**: the system's name, the date, the participants, and the number of threats
     at each severity.
  2. **Scope**: what was modelled, what was left out, and the assumptions.
  3. **System description**: every element and trust boundary with its identifier, and the
     repository files read, if any.
  4. **Data flow diagram**, written in Mermaid.
  5. **Threats**: a table with one row per threat, holding its identifier, STRIDE category,
     the element it affects, a description, its likelihood and impact with the reason for
     each, its severity, the decision, who it was decided by, and its owner.
  6. **Coverage**: a table showing, for every element, every STRIDE category that was
     considered and its result, including "none found".
  7. **Mitigations**: each one with the threats it addresses and its owner.
  8. **Open questions**: what the participants could not answer or agree.
  9. **Method**: that the session used STRIDE and the OWASP Risk Rating Methodology and was
     led by an AI agent.
- **FR-038**: The written model MUST be posted in the conversation where the session took
  place, as a Markdown file, so that its content is exactly the Markdown that was written,
  tables and diagram included. The facilitator's notes are a second file.
- **FR-039**: The written model and the facilitator's notes MUST be delivered completely,
  whatever their length, within feature 007's limit on the time one reply may take. When a
  file cannot be delivered, the participants MUST be told, and can ask for it again.
- **FR-040**: Asked for the model before the session is finished, STRIDEr MUST write it with
  each unfinished stage marked and without the facilitator's notes. Asked again later, it writes it from the current state.
- **FR-041**: The facilitator's notes MUST be clearly separate from the written model. They
  hold: each point STRIDEr hinted at that was not taken up (FR-023); each missed point it
  did not hint at because of the limit in FR-022, marked as not raised in the session; and
  each rating or mitigation STRIDEr questioned that the participants kept, with what it
  questioned (FR-045, FR-055). Apart from those unhinted missed points, they MUST hold
  nothing that STRIDEr did not raise in the session. They MUST say that they are STRIDEr's
  own observations, which the participants have not checked, and not part of the
  participants' model.
- **FR-056**: The facilitator's notes MUST be posted only when the session is finished or
  abandoned. A written model asked for earlier (FR-040) comes without them, and STRIDEr
  MUST NOT reveal their contents during the session, even when asked. A session is
  finished when the participants say it is; STRIDEr then posts the written model and the
  notes. Before posting the notes STRIDEr MUST say that they are about to be posted and that
  later changes will be marked.
- **FR-059**: After the notes are posted, participants MAY still change the written model,
  and STRIDEr posts it again. Every threat, rating, mitigation or decision added or changed
  after that point MUST be marked in the model as changed after the facilitator's notes. The
  rule that participants do the work (FR-018) still holds for each change: STRIDEr MUST NOT
  turn a note into a model entry itself. The notes are not changed after they are first posted. They are sent again, as they were,
  whenever the model is asked for after the session has ended, so that a file that did not
  arrive can be had (FR-039).

**Rating**

- **FR-042**: Each threat MUST be given a likelihood and an impact by the participants, each
  high, medium or low.
- **FR-043**: STRIDEr MUST help participants reason with the factors of the OWASP Risk Rating
  Methodology: for likelihood, who the attacker is and how easily the weakness is found and
  used; for impact, the technical damage and the damage to the business. It asks about a
  factor when the participants have not addressed it.
- **FR-044**: The severity MUST be read from the methodology's table, and STRIDEr states it:

  | | Likelihood low | Likelihood medium | Likelihood high |
  |---|---|---|---|
  | **Impact high** | Medium | High | Critical |
  | **Impact medium** | Low | Medium | High |
  | **Impact low** | Note | Low | Medium |

- **FR-045**: STRIDEr MUST point out a rating that contradicts what the participants said
  earlier. The participants keep or change it.
- **FR-055**: When STRIDEr doubts a rating or a mitigation for any other reason, it MUST
  raise the doubt in the session as a question, once, without giving a value or a
  mitigation of its own. The participants keep or change what they chose.
- **FR-046**: Each threat MUST get a decision from the participants: mitigate, accept,
  transfer or avoid. An accepted threat records the participants' reason.
- **FR-057**: For each decision the written model MUST record two things. **Decided by**: the
  participant or participants who made it, which STRIDEr records from who said it, and when
  the group agreed, all who agreed. **Owner**: who is responsible for carrying it out, as
  named by the participants. The owner may be a person outside the session or a team, and
  is recorded as written. When no owner is named the model says so. STRIDEr MUST ask once
  for an owner and MUST NOT choose one.

**Proof, privacy and what must not change**

- **FR-047**: Unit tests MUST fail when any rule listed in FR-003 is removed from the
  persona, when a required stage or rule is removed from a skill, when the persona carries
  session instructions, when a skill is malformed, and when an adopted skill lacks its source
  or licence. They MUST also cover: the refusals in FR-034; that no reply posts nothing
  (FR-029); and that the writer's name reaches the agent and no log (FR-030, FR-032).
- **FR-048**: There MUST be a command that plays a fixed session against the deployed agent
  without Slack, with more than one named participant, and checks the written model against
  FR-037 part by part. It is run by hand and is not part of any automatic workflow. It keeps
  the transcript on the computer of the person who ran it.
- **FR-049**: There MUST be a short checklist by which a person reading a transcript judges
  how the session was led:
  - The opening statement was given.
  - Each stage was named when it began.
  - One question at a time.
  - STRIDEr never named a threat, gave a rating, chose a mitigation or made a decision.
  - At most one hint for each element in a stage, and no hint named the threat.
  - Everything in the written model was said or decided by a participant.
  - Every questioned rating or mitigation in the notes was raised in the session.
  - The notes' contents were not given away before the session ended.
  - STRIDEr was silent, and spoke, at the right moments.
- **FR-050**: No message text, reply text, repository content or person's name may be written
  to any log, workflow output, issue or pull request. A log may record that a repository was
  read, its name, and how many files were read.
- **FR-051**: Everything features 001 to 007 provide MUST still work, and their tests MUST
  pass. The changes this feature makes to them are: what the agent is told (FR-001); the
  writer's name (FR-030); no reply (FR-029); documents delivered as files, with one new
  Slack permission and one new sentence for a file that cannot be delivered (FR-038,
  FR-039); and an identifier for each message, so that a repeated request is recognised.
- **FR-052**: The handbook MUST describe the persona and skills, how to change or add a
  skill, how a session runs, the repository rules, and how to run the command in FR-048.

### Key Entities

- **Session**: one exercise on one system. Has a system name, a current stage, the stages
  skipped, and participants. Lives in the agent's memory of the conversation and nowhere
  else.
- **Participant**: a person in the session, known by the name Slack displays.
- **Element**: a component, data flow, data store or external party, with an identifier.
- **Trust boundary**: a line between elements, with the elements on each side.
- **Threat**: named by a participant. Has an identifier, a STRIDE category, the element
  affected, a description, a likelihood, an impact, a severity, a decision, who decided it and an owner.
- **Mitigation**: proposed by a participant. Addresses one or more threats and has an owner.
- **Open question**: something the participants could not answer or agree.
- **Written model**: the document in FR-037.
- **Facilitator's notes**: the document in FR-041.
- **Persona** and **skill**: what STRIDEr is told, in two kinds.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A person can go from asking for a session to holding a written model without
  leaving Slack.
- **SC-002**: In the fixed session, the written model has all nine parts of FR-037, every
  threat row has every field, and the coverage table has a result for every element and
  every category considered.
- **SC-003**: In the fixed session, STRIDEr is asked directly for a threat, a rating, a
  mitigation and a decision, and gives none of them.
- **SC-004**: In the fixed session, a point left unraised after its hint, and a rating
  questioned and kept, each appear in the facilitator's notes; the missed point is nowhere
  in the written model; and a model asked for part-way comes without the notes.
- **SC-005**: In a session with two people in a channel thread, messages plainly between
  them get no reply, and a question to the group, a disagreement and a mention each get one.
- **SC-006**: Every person named in a written model is named as Slack displays them, and a
  search of every log for a participant's name after a session finds nothing.
- **SC-007**: Asked to read a private repository, a repository outside `ServerlessOpsIO` and
  a web address that is not a repository, STRIDEr reads none of them and the session
  continues.
- **SC-008**: A repository file containing an instruction to the agent is read and the
  instruction is not carried out.
- **SC-009**: The written model, copied from Slack into a file in a GitHub repository, shows
  its tables as tables and its diagram as a diagram.
- **SC-010**: No reply in the fixed session fails for taking too long or being too large,
  including the written model.
- **SC-011**: Removing any one rule in FR-003 from the persona, or any stage from the skill,
  makes at least one unit test fail.
- **SC-012**: Every unit test from features 001 to 007 passes.
- **SC-013**: One person can complete a session on a system of five elements or fewer in a
  single sitting of 60 minutes.
- **SC-014**: A developer can add a skill for another kind of review by adding files, without
  changing the persona.

## Assumptions

**Decided by the owner in conversation on 2026-11-17**

- The stages, one question at a time, and starting from ordinary words.
- Participants do the work; STRIDEr facilitates. Missed points go to facilitator's notes.
- Rating by the OWASP Risk Rating Methodology, cut down to two values per threat.
- STRIDEr may stay silent in a channel thread, speaks unasked when it can help, and speaks
  when in doubt.
- People are known by their Slack display name. STRIDEr does not address individuals.
- Repositories: public ones in `ServerlessOpsIO` only, because a later feature will write
  the model to the same repositories.
- The written model has a Mermaid diagram and a coverage table, and can be written early.
- Search for an existing skill first, in planning; copy an adopted one into this repository.
- The fixed session is run by hand, and a person judges how it was led.
- The agent uses whatever model the deployment configures. This specification names none.
- The persona's wording is settled later in this process.
- In a disagreement about the work, STRIDEr weighs the reasoning and names no value.
- Each decision records who made it and, separately, its owner.
- The model can be changed after the notes are posted, and such changes are marked.
- STRIDEr opens every session by saying how it works, including that it keeps notes.
- Skipping, finishing and abandoning: any participant asks, STRIDEr announces, and an
  objection stops it.
- One hint at most per element in each stage. Missed points beyond that go to the notes
  unhinted.
- The facilitator's notes hold missed points and questioned ratings and mitigations, and
  are posted only when the session ends. Doubts about ratings and mitigations are always
  raised in the session first.
- Examples come from a different kind of system; a part found only in the repository is
  stated as a fact, after the participants have finished their own description.

**Chosen by the author, and confirmed by the owner on 2026-11-19**

- An accepted threat records the participants' reason (FR-046).
- A participant is anyone who has written in the conversation since the session started.
- Silence applies only while a session is in progress. Outside a session, feature 007's
  behaviour in a channel thread is unchanged.
- Mentions of people inside messages become names (FR-030), so that a model never shows a
  Slack identifier.
- The name is the one Slack displays: the display name, or the full name when no display
  name is set.
- A session is finished when the participants say so, and STRIDEr warns before posting the
  notes (FR-056).
- A long element list leads STRIDEr to suggest a narrower scope.
- SC-013's five elements and 60 minutes are starting values.

**Settled in planning on 2026-11-19** (`research.md`)

- The agent's framework reads the Agent Skills format. Confirmed.
- The writer's name comes from the lookup feature 007 already makes. Confirmed; no new
  permission is needed for names.
- The written model is delivered as a file (FR-038), which needs one new Slack permission
  and the app to be installed again. Text posted in Slack cannot be copied back out as
  Markdown. For the owner to confirm.
- The written model is laid out by a program from a record of the session, so producing it
  takes no noticeable time (FR-039).
- A whole session does not fit in what the model is shown: it sees only recent messages.
  The session is therefore kept as a record, which does not depend on the model's memory.
- The table in FR-044 matches OWASP's published page.

**Believed, and still to be tried**

- The configured model can keep the rules of this specification through a whole session.
  This is the largest risk, and the fixed session is run early to find out.
- GitHub can be read without a credential often enough for sessions. Its hourly limit is
  per network address, and the agent's address is not its own.

**Out of scope**

- Publishing the written model to GitHub (issue #17).
- Reading private repositories (issue #18).
- An automated assessment of a model by another agent (issue #19).
- Group direct messages (issue #13).
- Other kinds of review.
- Diagrams as images.
- Keeping a session beyond the agent's memory period.
- Changing the model the agent uses.

**Dependencies**

- Feature 007: conversations in channel threads and direct messages, replies in numbered
  parts, the limits on one reply and one prompt, and answers for full members only.
- Features 001 and 002: the agent and its memory of a conversation.
- GitHub's public interface for reading repositories.
- The OWASP Risk Rating Methodology.
- A marketplace skill and its licence, if one is adopted.
- This repository is public, which is why FR-050 forbids text, content and names in logs.
