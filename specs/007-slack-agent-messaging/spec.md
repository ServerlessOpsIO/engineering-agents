# Feature Specification: STRIDEr Slack Messaging

**Feature Branch**: `feature/007-slack-agent-messaging`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "As a developer my slack app can communicate with it's AI
backend." The project owner expanded this in conversation into a story, a proposed solution,
scope boundaries, dependencies and acceptance criteria, which this specification records.

**Background**: STRIDEr is a Slack agent in this repository that will lead threat modeling
exercises using the STRIDE framework. Feature 006 created its Slack app, which is present in
the workspace and does nothing when spoken to. Features 001 and 002 created an agent that
answers a prompt and remembers a conversation, and that only accepts calls from inside the
cloud account. This feature joins the two: a person writes to STRIDEr in Slack and the
agent's answer appears in the same thread. The agent answers as it does today. Making it
lead a STRIDE exercise is a later feature.

**Terms**:

- **Slack app**: the thing registered with Slack that gives STRIDEr its name, its bot user
  and its permissions in the workspace. Created by feature 006.
- **Agent**: the existing program in `src/agent` that takes a prompt and returns a reply.
- **Session**: one conversation the agent remembers. Requests with the same session
  continue the same conversation.
- **Event**: a notice Slack sends when something happens that the Slack app has asked to
  hear about, such as a message that mentions STRIDEr.
- **Event delivery address**: the public web address Slack sends events to. Feature 006
  left a place for it, `event_request_url` in `slack/settings.json`, and left it empty.
- **Receiving service**: everything this feature adds between Slack and the agent. It has
  three parts. The **front door** accepts or rejects what arrives at the event delivery
  address and answers Slack at once. The **worker** takes accepted messages, asks the
  agent, and posts the reply. The **cleanup step** is defined below.
- **Signing secret** and **bot token**: two of the app values from feature 006. The signing
  secret proves a request came from Slack for this app. The bot token lets the receiving
  service post and react as STRIDEr.
- **Signature**: a value Slack sends with every request, computed from the signing secret,
  the time of sending and the exact content of the request.
- **Answerable message**: a message STRIDEr replies to under the rules in FR-008.
- **The apology**: one fixed sentence STRIDEr posts when it cannot answer.
- **Held-back store**: where a message goes when the worker stopped before finishing it.
  It waits there, for at most 60 minutes, for the cleanup step.
- **Cleanup step**: a third part of the receiving service. It deals with messages in the
  held-back store: it posts the apology if one is owed and removes the eyes reaction.

## Clarifications

### Session 2026-11-16

- Q: When STRIDEr is first mentioned part-way down an existing thread, should it read the thread's earlier messages before answering? → A: Yes, once. On the first mention in a thread, the earlier messages in that thread are given to the agent as context. Later messages rely on the agent's memory.
- Q: When the agent fails to answer a message, how many more times should STRIDEr try before it posts the apology? → A: Once. Two attempts in total, then the apology.
- Q: What should happen to the eyes reaction once STRIDEr has finished with a message? → A: It is removed when the reply or the apology has been posted.
- Q: When a message can't be answered and is kept for the owner to look at, should the kept copy include the text of the message? → A: Yes, for a short time. The owner first chose identifiers only, and changed this after reading the plan: the text travels with the message so that Slack does not have to be asked for it, and a held-back message is deleted after 60 minutes. The lasting record of a failure is the log, which has no text.
- Q: What should happen when the worker stops part-way through a message, so the person has the eyes reaction and nothing else? → A: A separate cleanup step, triggered by the held-back store, posts the apology and removes the reaction. The owner proposed this on 2026-11-16. Because the cleanup step empties the held-back store, the store is no longer somewhere to look at failed messages; the log is.
- Q: What should happen in a thread that is older than the agent's memory? → A: Nothing STRIDEr does should last past the memory period (7 days by default). In an older thread, a person who addresses STRIDEr is told it no longer remembers the conversation and is asked to start a new one. From the owner's suggestion on 2026-11-16; the exact rule is the author's.
- Q: Is the eyes reaction used when STRIDEr replies with the start-again sentence in an old thread? → A: Yes. Added, then removed once the sentence is posted.
- Q: Should the spec say that later messages in a thread wait while an unfinished message is moved to the held-back store? → A: Yes. Added to FR-022 and the edge cases.
- Q: Should a message that is more than 4 minutes old when it arrives be ignored, to close the one way a message could be answered twice? → A: Yes. Proposed by the author; confirmed by the owner on 2026-11-16, together with the rule for old threads (FR-050, FR-051).
- Q: How is a person told when only part of a long reply was posted? → A: The parts of a long reply are labelled "(part 1 of 3)". If a part cannot be posted, or the worker stops between parts, a fixed sentence says the reply is incomplete and asks the person to ask again. Proposed by the author; confirmed by the owner on 2026-11-16.
- Q: When Slack cannot say whether a thread is STRIDEr's or whether the writer is a full member, what happens? → A: The call to Slack is tried again a few times first, and a person's membership is remembered for an hour so it is rarely asked. If Slack still cannot say: a reply with no mention in a thread that cannot be read gets nothing; a writer who cannot be looked up gets nothing; a full member who mentions STRIDEr in a thread that cannot be read gets the apology. All three are logged as failures. Proposed by the author; confirmed by the owner on 2026-11-16.
- Q: Should the receiving service keep its own record of which threads STRIDEr is in and which messages it has answered? → A: No. The owner removed the database from the plan on 2026-11-16. Both are found out from Slack when needed, and a message is never handled twice.
- Q: Planning found three places where the specification did not match what can be built or what Slack does. Should it be corrected? → A: Corrected by the author on 2026-11-16, for the owner to confirm: the worker, not the front door, decides whether the writer is a full member (FR-006); the worker's log record carries the other two records' identifiers instead of all three sharing one (FR-036); and Slack does not turn events off for an app with this little traffic (Edge Cases). FR-038 now names both new permissions.
- Q: Who in the Slack workspace may get an answer from STRIDEr? → A: Full members of the `serverlessops` workspace only. Guests and people from other organisations get no reaction and no reply.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A person mentions STRIDEr and gets a reply in a thread (Priority: P1)

A person in a channel STRIDEr has been added to writes a message that mentions STRIDEr.
Within a few seconds an eyes reaction appears on their message, which tells them STRIDEr has
seen it. Then the agent's reply appears in a thread under their message.

**Why this priority**: This is the feature. Everything else supports it or protects it.

**Independent Test**: In a channel STRIDEr is a member of, post a message that mentions
STRIDEr and asks a simple question. An eyes reaction appears on the message, and a reply
that answers the question appears in a thread under it.

**Acceptance Scenarios**:

1. **Given** STRIDEr is a member of a channel, **When** a person posts a message there that
   mentions STRIDEr, **Then** an eyes reaction appears on that message, the agent's reply
   is posted in a thread under it, and the reaction is then removed.
2. **Given** a message that mentions STRIDEr, **When** the agent takes a long time to
   answer, **Then** Slack is still acknowledged within its time limit and does not send the
   message again.
3. **Given** a message in a channel that does not mention STRIDEr and is not in a thread
   STRIDEr is taking part in, **When** it is posted, **Then** it gets no reaction and no
   reply.
4. **Given** a message that mentions STRIDEr, **When** the text is passed to the agent,
   **Then** the mention itself is left out and the rest of the text is unchanged.
5. **Given** a message posted by a bot or by STRIDEr itself, **When** it arrives, **Then**
   it gets no reaction and no reply, even if it mentions STRIDEr.
6. **Given** a message that mentions STRIDEr, written by a guest of the workspace or by a
   person from another organisation in a shared channel, **When** it arrives, **Then** it
   gets no reaction and no reply.

---

### User Story 2 - Only Slack can reach the agent (Priority: P1)

The event delivery address is public, and because the repository is public, so is the
address itself. Anyone can send it a request. The front door accepts a request only when its
signature proves that Slack sent it for this app, recently. Everything else is turned away
before it can reach the agent, cost model usage, or post in Slack.

**Why this priority**: Without this, the agent is open to the internet and anyone could make
STRIDEr post in the workspace. The feature must not go live without it.

**Independent Test**: Send the event delivery address a well-formed message event with no
signature, with a wrong signature, and with a correct signature that is more than five
minutes old. Each is rejected, no reaction or reply appears in Slack, and the agent is not
called.

**Acceptance Scenarios**:

1. **Given** a request with no signature, **When** it arrives, **Then** it is rejected and
   nothing is passed to the worker or the agent.
2. **Given** a request whose signature does not match its content, **When** it arrives,
   **Then** it is rejected in the same way.
3. **Given** a request with a valid signature whose time of sending is more than five
   minutes old, **When** it arrives, **Then** it is rejected in the same way.
4. **Given** a genuine request from Slack, **When** it arrives, **Then** it is accepted.
5. **Given** any request, accepted or rejected, **When** it is handled, **Then** no secret
   value and no message text is written to a log.

---

### User Story 3 - The owner connects the Slack app to the agent by following the documentation (Priority: P1)

The owner places the signing secret and the bot token in the cloud account by hand, merges
the change, and then does two things in Slack: confirms the event delivery address and
installs the app again so it gains the new permission. The documentation gives the steps in
order. After that, the address does not change, even if the receiving service is rebuilt
from nothing.

**Why this priority**: Nothing can be tried end to end until the app is connected, and some
of the steps can only be done by a person.

**Independent Test**: Starting from the state feature 006 left, follow the documented steps
and nothing else. Slack shows the event delivery address as verified, the installed app
holds the reaction permission, and User Story 1 passes.

**Acceptance Scenarios**:

1. **Given** the receiving service is deployed and the event delivery address is set in the
   Slack app's settings, **When** Slack checks the address, **Then** the check succeeds.
2. **Given** the secrets have been placed by hand, **When** the receiving service is
   deployed, **Then** it uses them, and their values are not in the repository, the
   deployment's description of itself, any log or any pipeline output.
3. **Given** the receiving service is removed and deployed again, **When** it is ready,
   **Then** it answers at the same address and nothing has to be changed in Slack.
4. **Given** the owner replaces the bot token after installing the app again, **When** they
   store the new value by the documented step, **Then** STRIDEr works again with no change
   to the repository.
5. **Given** the change is merged before the owner has installed the app again, **When**
   the Slack app pipeline runs, **Then** it fails saying the app must be installed again,
   as feature 006 defined, and passes once that is done.

---

### User Story 4 - A conversation continues in its thread (Priority: P2)

After STRIDEr has replied in a thread, the people in it carry on without mentioning STRIDEr
each time. STRIDEr answers each message in the thread and remembers what was said earlier in
it. A different thread is a different conversation and shares nothing with the first.

**Why this priority**: A threat modeling exercise is a conversation, not single questions.
Single questions already show the connection works, so this comes second.

**Independent Test**: Mention STRIDEr and tell it a fact, such as a name. In the thread,
without a mention, ask for the fact; the reply gives it. In a new thread, mention STRIDEr
and ask for the fact; the reply does not know it.

**Acceptance Scenarios**:

1. **Given** a thread in which STRIDEr has been mentioned, **When** a person posts in that
   thread without a mention, **Then** the message gets the eyes reaction and a reply in the
   same thread.
2. **Given** a thread with earlier messages STRIDEr has answered, **When** a new message
   refers to something said earlier, **Then** the reply shows the agent remembers it.
3. **Given** two threads, **When** a message in one refers to something said only in the
   other, **Then** the reply shows the agent does not know it.
4. **Given** a thread started by people in which STRIDEr has not been mentioned, **When** a
   person posts in it without a mention, **Then** the message gets no reaction and no reply.
5. **Given** such a thread, **When** a person mentions STRIDEr in a reply, **Then** STRIDEr
   answers in that thread, its answer shows it has read the thread's earlier messages, and
   from then on it answers messages in the thread without a mention.
6. **Given** two messages posted in one thread close together, **When** both are answered,
   **Then** the replies come in the order the messages were sent.

---

### User Story 5 - A person talks to STRIDEr in a direct message (Priority: P2)

A person opens a direct message with STRIDEr and writes to it without a mention. The eyes
reaction appears and the reply comes in a thread under their message. Each new top-level
message starts a new conversation; replies in a thread continue that one.

**Why this priority**: Direct messages are the second way in. They use the same path as
channels, so they add little work, but the feature is usable without them.

**Independent Test**: Send STRIDEr a direct message asking a simple question. The eyes
reaction appears and a reply is posted in a thread under the message. Reply in the thread
referring to the first message; the answer shows the agent remembers it.

**Acceptance Scenarios**:

1. **Given** a direct message to STRIDEr, **When** it is sent, **Then** it gets the eyes
   reaction and a reply in a thread under it, with no mention needed.
2. **Given** a reply in that thread, **When** it is sent, **Then** it is answered in the
   thread and the agent remembers the thread's earlier messages.
3. **Given** a second top-level direct message, **When** it is sent, **Then** it starts a
   new conversation that does not remember the first.

---

### User Story 6 - When something goes wrong, the person is told and nothing is lost (Priority: P2)

Sometimes the agent fails, or Slack sends the same event twice, or Slack cannot be reached
when the reply is ready, or the worker itself stops part-way. The person is not left with
an eyes reaction and nothing else: they get the reply or the apology, and the reaction is
removed. They never get two replies to one message. A message
that could not be answered is kept where the owner can find it.

**Why this priority**: The path has several steps and any of them can fail. Without this
the feature works when tried and confuses people when it does not.

**Independent Test**: Make the agent fail for one message, for example by deploying with a
setting that makes every call fail. The person sees the apology in the thread, and the
failure details are in the log and not in Slack. Then deliver one genuine event twice; one
reply appears.

**Acceptance Scenarios**:

1. **Given** an answerable message, **When** both attempts to get the agent's answer fail,
   **Then** the apology is posted once in the thread, the eyes reaction is removed, and
   the failure is in the log with its reason.
2. **Given** a failure, **When** the apology is posted, **Then** it contains no detail of
   what went wrong, and the detail is in the log.
3. **Given** Slack delivers the same event more than once, **When** each delivery is
   handled, **Then** the person sees one reaction and one reply.
4. **Given** an answerable message, **When** the first attempt fails and the second
   succeeds, **Then** the person sees the reply and no apology.
5. **Given** a message the agent rejects because it is longer than the agent accepts,
   **When** it is handled, **Then** the person is told in the thread that the message is too
   long, and the message is not treated as a failure.
6. **Given** a message that is only a mention with no other text, **When** it is handled,
   **Then** the person gets a short fixed reply asking what they need, and the agent is not
   called.
7. **Given** an answerable message with the eyes reaction on it, **When** the worker stops
   before posting anything, **Then** within 10 minutes the cleanup step posts the apology
   and removes the reaction.
8. **Given** the worker stopped just after posting its reply, **When** the cleanup step
   runs, **Then** it removes the reaction and posts no apology.
9. **Given** a thread older than the agent's memory, **When** a person mentions STRIDEr in
   it, **Then** they get a fixed sentence asking them to start a new conversation, and the
   agent is not called.

---

### Edge Cases

- A message is edited or deleted after it was sent: the edit or deletion is ignored.
  STRIDEr answers the original message once and does not answer again.
- A message has a file or image attached: STRIDEr answers the text alone. A message with an
  attachment and no text is treated like a message with no text when it mentions STRIDEr or
  is a direct message.
- A message joins, leaves or renames a channel, or is another notice Slack generates
  itself: ignored.
- Whether the person is a full member cannot be found out, after several tries: the
  message is not answered, nothing is shown, and the log records a failure. STRIDEr
  responds only to someone it knows it may answer (FR-053).
- A guest or a person from another organisation wrote earlier in a thread that a member
  then brings STRIDEr into: their messages are part of the thread context like any others.
  The rule is about who may ask, not whose words may be read.
- STRIDEr is mentioned in a channel it is not a member of: Slack does not deliver the
  message, so nothing happens. This is Slack's behaviour and is documented for people.
- A message in a group direct message: not delivered, because the Slack app does not ask
  for those. Out of scope; how STRIDEr should behave there is tracked in issue #13. It is
  not known whether Slack delivers a mention of STRIDEr made in a group direct message. If
  it does, STRIDEr answers it as it would in a channel.
- STRIDEr is mentioned part-way down a thread: the thread's earlier messages are given to
  the agent with that message, once. After that the agent's memory of the session is used
  and the thread is not read again.
- The thread's earlier messages are more than the agent accepts: the oldest are left out
  until the rest fit, and the agent is told that some were left out.
- A thread cannot be read from Slack, after several tries: if the message does not mention
  STRIDEr, nothing is shown, because the thread may not be STRIDEr's. If it does mention
  STRIDEr and the writer is a full member, the apology is posted; STRIDEr does not answer
  without the thread's earlier messages. Either way the log records a failure (FR-053).
- A thread is older than the agent's memory: a reply with no mention is ignored. A mention
  of STRIDEr there, or a reply in such a thread in a direct message, gets the start-again
  sentence (FR-050).
- A message is more than 4 minutes old when it reaches the front door, because Slack
  delivered it late or was retrying: it is ignored and nobody is told (FR-051).
- A person writes again in a thread while the worker has stopped part-way through their
  previous message: the new message waits about five minutes, until the unfinished one has
  moved to the held-back store, and is then answered (FR-022).
- The cleanup step itself fails: it is tried again until the message is 60 minutes old.
  After that the message is deleted, the eyes may stay, and the log is the only trace.
- The reaction cannot be added, for example because the app has not been installed again
  yet: the message is still answered, and the failure to react is logged.
- The reaction cannot be removed after the reply: it stays on the message, the failure is
  logged, and the reply is not affected.
- The agent's reply is longer than Slack accepts in one message: it is posted as several
  labelled messages in order, in the same thread, with nothing cut off. If only some of
  them can be posted, or the worker stops between them, the person is told the reply is
  incomplete (FR-052). If Slack is taking no posts at all, that sentence cannot be posted
  either.
- The agent's reply uses formatting Slack shows differently: the reply is posted so that
  it reads correctly in Slack.
- The reply is ready and Slack refuses or cannot be reached: posting is tried again. If it
  never succeeds the failure is logged; there is no way to tell the
  person.
- The apology itself cannot be posted: the failure is logged, and the worker still tries to
  remove the eyes reaction.
- The receiving service is down or being deployed when Slack sends an event: Slack tries
  again a few times over a few minutes and then gives up. That message is lost and the
  person sees nothing. Slack turns event delivery off for an app whose deliveries mostly
  fail for an hour, but not for one that receives as few events as this; the documentation
  says how to turn it on again in case that changes.
- Many requests arrive at once, genuine or not: the front door accepts up to a set rate and
  turns the rest away. Slack sends turned-away genuine events again.
- Slack sends a request that is genuine and of a kind this feature does not use: it is
  acknowledged and ignored.
- A stored secret is missing or wrong: every request is rejected, or every reply fails,
  and the log says which secret is the cause without showing its value.
- A person writes in the thread while STRIDEr is still answering their previous message:
  both are answered, in order.

## Requirements *(mandatory)*

### Functional Requirements

**Receiving events**

- **FR-001**: The receiving service MUST offer one public address that Slack can send events
  to. The address MUST be `https://engineering-agents.sandbox.serverlessops.io` followed by
  a fixed path, and MUST stay the same when the receiving service is removed and deployed
  again.
- **FR-002**: The front door MUST accept a request only when its signature matches its
  exact content and the signing secret, and its time of sending is no more than five
  minutes from the current time. The comparison MUST NOT reveal, by how long it takes, how
  much of a wrong signature was right.
- **FR-003**: A request that fails FR-002 MUST be rejected with an answer that says it was
  not authorised, MUST NOT be passed to the worker or the agent, and MUST NOT cause anything
  to be posted in Slack.
- **FR-004**: The front door MUST answer Slack's check of the event delivery address
  correctly. The check is itself subject to FR-002.
- **FR-005**: The front door MUST acknowledge every accepted event within Slack's three
  second limit, whatever the agent is doing. Answering the message MUST happen separately
  from acknowledging it.
- **FR-006**: The front door MUST acknowledge and take no further action on a genuine
  request that it can tell is not an answerable message. Two rules may be decided by the
  worker, because they need Slack to be asked: whether the writer is a full member, and
  whether a thread is one STRIDEr has been mentioned in. FR-010 holds either way.
- **FR-007**: The front door MUST limit the rate of requests it accepts, so that a flood of
  requests cannot run up unbounded cost. The limit is set in planning and MUST be above
  what the workspace produces in normal use.

**Deciding what to answer**

- **FR-008**: A message is answerable when it was written by a person who is a full member
  of the `serverlessops` workspace and one of these is true:
  1. it is in a channel and mentions STRIDEr;
  2. it is a direct message to STRIDEr;
  3. it is in a thread in which STRIDEr has already been mentioned.
- **FR-009**: The receiving service MUST NOT answer: a message from a bot or from STRIDEr
  itself; a message from a guest of the workspace or from a person in another organisation
  who shares a channel with it; an edit or a deletion; a notice Slack generates itself; or any message that
  FR-008 does not cover.
- **FR-010**: A message that is not answerable MUST get no reaction and no reply, and MUST
  NOT be sent to the agent.
- **FR-011**: When Slack delivers the same event more than once, the receiving service MUST
  act on it once.
- **FR-012**: When a message both mentions STRIDEr and is delivered to the receiving
  service as an ordinary channel message, the receiving service MUST answer it once.

**Answering**

- **FR-013**: When the worker starts on an answerable message it MUST add an eyes reaction
  to that message. The reaction means "STRIDEr is working on this" and stays through both
  attempts. The worker MUST remove it once the reply, the apology or one of the other fixed
  sentences has been posted, and MUST also try to remove it when it stops work on a message
  without having posted anything. Failing to add or to remove the reaction MUST be logged
  and MUST NOT stop the message being answered or count as a failed attempt.
- **FR-014**: The worker MUST send the agent the text of the message with the mention of
  STRIDEr removed and nothing else changed.
- **FR-015**: The worker MUST call the agent using the cloud account's own identity
  checking, as other callers inside the account do. The agent MUST NOT be opened to callers
  outside the account, and how the agent checks its callers MUST NOT change.
- **FR-016**: The worker MUST post the agent's reply in the thread under the person's
  message. A reply to a message that is already in a thread goes in that thread.
- **FR-017**: A reply longer than Slack accepts in one message MUST be posted as several
  messages in order, with no text lost. Each of them MUST end with a label saying which
  part it is and how many there are, such as "(part 1 of 3)". A reply that fits in one
  message has no label.
- **FR-052**: When only some parts of a reply could be posted, the person MUST be told,
  with a fixed sentence in the thread saying the reply is incomplete and asking them to
  ask again. The worker does this when a part cannot be posted. The cleanup step does it
  when it finds that the last thing STRIDEr posted is a part that is not the final one.
  When no part could be posted at all, the apology is used.
- **FR-018**: The reply MUST read correctly in Slack. Where the agent's formatting differs
  from Slack's, it MUST be converted or removed, not shown as stray symbols.
- **FR-046**: The first time STRIDEr answers in a channel thread that already has messages,
  the worker MUST give the agent those earlier messages along with the message being
  answered: the text of each and who wrote it, in the order they were sent. Once STRIDEr
  has answered in a thread, later messages in it are sent on their own. The apology and
  the other fixed sentences do not count as an answer.
- **FR-047**: When the earlier messages and the message being answered are together more
  than the agent accepts, the worker MUST leave out the oldest earlier messages until the
  rest fit, and MUST tell the agent that some were left out. The message being answered is
  never shortened.
- **FR-048**: The worker MUST read earlier messages only from the thread STRIDEr was
  mentioned in. It MUST NOT read the rest of the channel, or any other thread.
- **FR-019**: The worker MUST pass the Slack ID of the person who wrote the message along
  with the request, as information only. Nothing in this feature decides anything from it.

**Conversations**

- **FR-020**: Every message in one Slack thread MUST use the same session, and messages in
  different threads MUST use different sessions. The session MUST be worked out from the
  thread alone, so the same thread always gives the same session.
- **FR-021**: In a direct message, each top-level message MUST start a new thread and a new
  session, and replies in that thread MUST continue it.
- **FR-022**: Messages in one thread MUST be answered in the order they were sent. Messages
  in different threads MUST NOT wait for each other. When the worker stops before
  finishing a message, later messages in the same thread wait until that message has
  moved to the held-back store, about five minutes, and are then answered in order. Other
  threads are not held up.
- **FR-023**: How long a session is remembered is whatever the agent's memory already
  provides. This feature MUST NOT change it.

**Failures**

- **FR-024**: When the agent cannot answer, or its answer cannot be obtained, the worker
  MUST try again once. A message gets two attempts in total and no more.
- **FR-025**: When both attempts have failed, the worker MUST post the apology in the thread,
  once. The apology is one fixed sentence and MUST NOT include any detail of the failure.
- **FR-026**: A message the worker stopped before finishing MUST go to the held-back store,
  as it was received, text included. The cleanup step MUST deal with each such message:
  if STRIDEr's eyes reaction is on the message and STRIDEr has posted nothing in the
  thread since, it posts the apology and removes the reaction; if STRIDEr has posted, it
  only removes the reaction, unless FR-052 applies; if the reaction is not there, it does
  nothing visible. A
  message MUST NOT stay in the held-back store for more than 60 minutes. Every failure,
  whoever handled it, MUST be in the log with the identifiers and the reason and no text;
  the log is the record of failures.
- **FR-027**: A person MUST NOT receive more than one reply, and MUST NOT receive both a
  reply and the apology, for one message. To keep this without a record of what has been
  answered, the worker MUST NOT run a second time on a message it did not finish; the
  cleanup step of FR-026 takes over.
- **FR-053**: A call to Slack that fails MUST be tried again, at least twice more, before
  the worker gives up on it. Whether a person is a full member MAY be remembered for up
  to an hour, so that Slack is not asked for every message. When Slack still cannot say
  what the worker needs to know:
  1. a reply that does not mention STRIDEr, in a thread that cannot be read, gets nothing;
  2. a message whose writer cannot be looked up gets nothing, whatever it says;
  3. a message that mentions STRIDEr, from a full member, in a thread that cannot be read,
     gets the apology, and the agent is not called.
  Each is logged as a failure with its reason.
- **FR-050**: A thread that began longer ago than the agent keeps memory MUST be treated
  as no longer STRIDEr's. A reply in it that does not mention STRIDEr gets nothing. A
  message in it that mentions STRIDEr, or any reply in such a thread in a direct message,
  gets a fixed sentence saying STRIDEr no longer remembers the conversation and asking
  the person to start a new one; the agent is not called. The eyes reaction is added
  before the sentence is posted and removed after it, as for any reply. FR-008's
  membership rule still applies first.
- **FR-051**: The front door MUST ignore a message that is more than 4 minutes old when
  it arrives.
- **FR-028**: When the agent rejects a message for being longer than it accepts, the worker
  MUST tell the person in the thread, with a fixed sentence, that the message is too long.
  This is not a failure: it is not retried and not held back.
- **FR-029**: When an answerable message has no text once the mention is removed, the
  worker MUST post a fixed sentence asking what the person needs, and MUST NOT call the
  agent.

**Secrets and privacy**

- **FR-030**: The signing secret and the bot token MUST be placed in the cloud account by
  the owner, by hand. The receiving service MUST read them from there when it runs.
- **FR-031**: No secret value may appear in the repository, in the deployment's description
  of itself, in a log, in pipeline output, in an issue or in a pull request.
- **FR-032**: The owner MUST be able to replace either secret without changing the
  repository.
- **FR-033**: The text of a message and the text of a reply MUST NOT be written to any log,
  including the logs of the public address. This matches the agent's existing rule.
- **FR-049**: The receiving service MUST NOT keep the text of a message for longer than 60
  minutes while it waits to be answered, or for longer than 60 minutes more in the
  held-back store. It MUST NOT keep the text of a thread's earlier messages or of a reply
  at all, beyond the moment of use. After that the text exists only in Slack and in the
  agent's own memory. Text that is waiting MUST be encrypted.
- **FR-034**: Each part of the receiving service MUST have only the access it needs: the
  front door to read the signing secret and pass messages on; the worker to read the bot
  token, take messages and call this one agent; the cleanup step to read the bot token
  and take messages from the held-back store, and not to call the agent.

**Observing**

- **FR-035**: The receiving service MUST write one structured log record for each request
  the front door handles, one for each message the worker handles and one for each
  message the cleanup step handles. A record gives the
  outcome, the time taken, and the Slack identifiers of the event, channel, thread and
  person. It does not give message text.
- **FR-036**: The worker's record for a message MUST carry the identifier in the front
  door's record and the identifier in the agent's own record for the same message, so the
  three can be found together.
- **FR-037**: The public address MUST keep an access log, kept for 7 days.

**The Slack app**

- **FR-038**: The app definition MUST gain the permission to add and remove reactions and
  the permission to look up a person in the workspace, which FR-008's membership rule
  needs. Each has a comment giving its reason, as feature 006 requires of every
  permission.
- **FR-039**: `event_request_url` in `slack/settings.json` MUST be set to the address in
  FR-001, so that feature 006's pipeline sends the subscribed events to Slack.
- **FR-040**: Only the receiving service deployed from `main` is connected to Slack. A
  deployment from any other branch MUST NOT receive Slack's events.

**Delivery**

- **FR-041**: The receiving service MUST be described in the repository's existing
  deployment template and deployed by the existing pipeline, in the same run as the agent.
- **FR-042**: The public address and the three programs MUST follow the conventions of the
  `backstage-aws-sam-python-template` repository (`skeleton/crud` and `functions/crud`) for
  how an address and its programs are described, laid out, logged and tested. Two
  exceptions: Slack's route does not use that template's sign-in check, because Slack
  cannot sign in and FR-002 is the check; and the content of Slack's requests is not held
  to a strict description, because Slack decides it.
- **FR-043**: All three programs MUST have unit tests that run without contacting the cloud
  platform or Slack. They cover at least: FR-002 with a valid, missing, wrong and stale
  signature; FR-004; each rule in FR-008 and FR-009, including who wrote the message; FR-011; FR-020 and FR-021; FR-025,
  FR-028 and FR-029; FR-046 and FR-047; the three cases of FR-026; FR-050 and FR-051; FR-017's labels with both halves of FR-052; and the three cases of FR-053.
- **FR-044**: The existing agent's tests and the Slack app's tests MUST still pass.
- **FR-045**: The handbook MUST describe: what the receiving service is; the first-time
  steps in order, saying which are done by hand; how to replace a secret; how to find a
  failed message in the log; what to do when Slack has stopped sending events; and what people in
  the workspace need to know, including that STRIDEr must be added to a channel before it
  can be mentioned there.

### Key Entities

- **Event**: what Slack sends. It has an identifier that is the same each time Slack sends
  it again, a kind, and for a message the channel, the thread, the person and the text.
- **Answerable message**: an event that passed FR-008. It carries what the worker needs:
  the event identifier, the channel, the message's own time stamp, the thread it belongs
  to, the person's Slack ID and the text.
- **Session**: the agent's memory of one conversation. There is one for each Slack thread.
- **Thread context**: the messages already in a thread when STRIDEr is first mentioned in
  it. Given to the agent once, at that first mention.
- **Reply**: what the agent returned, posted in the thread as one or more messages.
- **The apology** and the four other **fixed sentences** (message too long; nothing asked;
  start again; reply incomplete):
  wording kept in the repository, not written by the agent.
- **Held-back message**: a message the worker did not finish, as it was received. It waits
  for the cleanup step, for at most 60 minutes.
- **Secrets**: the signing secret and the bot token, as placed by the owner.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A person who mentions STRIDEr in a channel it is a member of sees the eyes
  reaction within 5 seconds and a reply in a thread under their message, in 19 of 20 tries.
- **SC-002**: The same holds for a direct message to STRIDEr.
- **SC-003**: In a thread STRIDEr has replied in, a follow-up with no mention is answered,
  and the answer uses something said earlier in the thread, in 10 of 10 tries.
- **SC-004**: In 10 of 10 tries, a fact given in one thread is not known in another.
- **SC-017**: When STRIDEr is first mentioned in a thread and asked about something said
  earlier in it, the reply uses what was said, in 10 of 10 tries.
- **SC-005**: Over a day of normal use, no message that is not answerable gets a reaction or
  a reply.
- **SC-006**: Of 100 requests sent to the address without a valid, recent signature, 100 are
  rejected and none causes a call to the agent or a post in Slack.
- **SC-007**: Slack's check of the event delivery address succeeds on the first try once
  the documented steps are done.
- **SC-008**: Every accepted event is acknowledged within 3 seconds, including when the
  agent takes more than 30 seconds to answer.
- **SC-009**: The same event delivered 5 times produces one reaction and one reply.
- **SC-018**: Once a reply or the apology has been posted, the eyes reaction is gone from
  the person's message within 5 seconds, in 19 of 20 tries.
- **SC-010**: When the agent is made to fail, the person sees the apology within 5 minutes
  of their message and the log has a record of the failure with its reason. When the
  worker itself is stopped part-way, the person sees the apology within 10 minutes and the
  eyes reaction is removed.
- **SC-019**: A message from a guest or from a person in another organisation never gets a
  reaction or a reply, in 10 of 10 tries.
- **SC-011**: STRIDEr never replies to its own messages or to another bot's. A search of a
  week's messages finds no such reply.
- **SC-012**: A search of the repository, the deployment's description of itself, a week of
  logs and a week of pipeline output finds no secret value.
- **SC-013**: A search of a week of logs finds no message text and no reply text, and the
  held-back store is empty within 10 minutes of any failure.
- **SC-014**: The unit tests for all three programs pass on a machine with no access to the cloud
  account or to Slack.
- **SC-015**: Starting from the state feature 006 left, the owner connects the app by
  following the handbook alone, in under 30 minutes of their own time.
- **SC-016**: After the receiving service is removed and deployed again, STRIDEr answers
  with no change made in Slack.

## Assumptions

- **The owner chose the shape.** The project owner decided these in conversation on
  2026-11-16, and planning starts from them: the public address is on the cloud platform's
  API gateway service, in the style of the template named in FR-042; a small program
  behind it checks the signature and passes accepted messages to a queue; a second program
  takes messages from the queue, calls the agent and posts the reply; the queue has a
  dead-letter queue, which is the held-back store; and a third program, triggered by the
  dead-letter queue, cleans up after a message the second did not finish. A program has to
  do the signature check
  because the gateway's own checks are not given the content of a request, and Slack's
  signature is computed from it.
- **The agent keeps its identity checking.** The owner considered letting Slack call the
  agent directly with a sign-in token and set it aside. Believed and to be confirmed in
  planning: the agent's hosting service accepts either the cloud account's identity
  checking or a sign-in token, not both, and Slack can present neither.
- **Secrets are placed by hand.** The owner chose this over having the pipeline copy them
  from the repository hosting service. The signing secret and bot token therefore exist in
  two places, there and in the cloud account. Where in the cloud account, and under what
  names, is for planning.
- **The hosted zone exists.** The owner created a zone for `sandbox.serverlessops.io` in
  the hosting account. Assumed and to be confirmed in planning: the deployment can add a
  record and a certificate for `engineering-agents.sandbox.serverlessops.io` in it.
- **The address is public knowledge.** It is committed in `slack/settings.json` in a public
  repository. FR-002 and FR-007 are the protection, not secrecy.
- **A thread is read once.** The agent is given the text of the message being answered.
  At the first mention in a thread it is also given that thread's earlier messages
  (FR-046), as the owner decided on 2026-11-16. After that, what came before is whatever
  the agent's memory holds for the session. STRIDEr never reads a channel's history.
- **Earlier messages go in with the prompt.** The agent is not changed by this feature, so
  the thread context reaches it as part of what it is asked, within the length it already
  accepts. FR-047's rule for when it does not fit was chosen by the author. Believed and
  to be confirmed in planning: the permissions the Slack app already holds are enough to
  read a thread's messages.
- **People in a thread did not write for STRIDEr.** Mentioning STRIDEr in a thread sends
  what others wrote there earlier to the agent and its model. The owner accepted this by
  choosing to read the thread. The text is still never logged (FR-033).
- **The reaction means "working".** It is removed when STRIDEr has posted its reply or the
  apology, as the owner decided on 2026-11-16. Believed and to be tried once the app is
  connected: removing a reaction notifies nobody. Removing it for the two other fixed
  sentences, and when nothing could be posted, was added by the author to match.
- **Edits and deletions are ignored.** Added by the author; told to the owner before this
  specification was written.
- **Too long, and nothing asked, are told apart from failures** (FR-028, FR-029). Added by
  the author, because the agent already rejects both and an apology would mislead.
- **Starting values chosen by the author**: 5 seconds for the reaction (SC-001), 5 minutes
  for the apology (SC-010), 30 minutes for setup
  (SC-015), and the try counts in the success criteria.
- **How fast the agent answers is not this feature's to promise.** No criterion sets a time
  for the reply itself.
- **One workspace, one environment.** The Slack app is installed in the `serverlessops`
  workspace only, and only `main` is connected. Branch deployments are switched off (issue
  #10), so the feature is first seen working for real on `main`; unit tests and signed
  sample requests are the check before that.
- **Order of the first-time steps.** The receiving service must be deployed and its secrets
  in place before Slack can check the address, and adding the reaction permission makes
  feature 006's pipeline fail until the app is installed again. Both are expected and the
  handbook gives the order.
- **A lost event is accepted.** If the receiving service is unreachable for as long as
  Slack keeps trying, that message is never answered and the person is not told.
- **Membership is remembered for an hour.** A person who stops being a full member, for
  example by being made a guest, may still be answered for up to an hour afterwards.
  Accepted by the owner on 2026-11-16 as the price of not asking Slack every time.
- **Full members only.** Decided by the owner on 2026-11-16. Planning found that nothing
  Slack sends with a message says its writer is a guest, so the receiving service asks
  Slack about the person, which needs one more permission in the app definition (FR-038).
  That permission lets STRIDEr look up any member's profile. A person who is not answered
  is not told why.
- **Text waits for at most an hour.** Decided by the owner on 2026-11-16, in place of an
  earlier choice that held-back records carry no text. In practice a waiting message is
  answered in seconds and a held-back one is cleaned up in minutes. 60 minutes is the
  limit in each place if something is stuck, so the outside limit is about two hours.
- **The reaction is how the cleanup step knows.** The worker adds the eyes only once it
  has decided to answer. A message in the held-back store without the eyes is one nobody
  was promised anything about, so nothing is posted. If adding the eyes failed and the
  worker then stopped, the person gets no apology.
- **A crashed worker's apology is slow.** It comes five to six minutes after the worker
  stopped, because that is how long the message takes to reach the held-back store.
- **No record of its own.** The receiving service has no database. A thread is STRIDEr's
  if Slack shows a mention of STRIDEr in it; STRIDEr has answered in it if Slack shows an
  answer. The price is that every reply in any thread, in a channel STRIDEr is in, is
  looked at by the worker, and that the worker does not try an unfinished message again
  (FR-027).
- **Identifiers may be logged.** Slack IDs of people, channels and threads are written to
  logs. Text is not.
- **Dependencies**: the Slack app and its values (006); the agent and its memory (001,
  002); the agent's log record and correlation identifier (003); the build and delivery
  pipeline (004).
- **Out of scope**: the STRIDE system prompt and any change to how the agent behaves;
  knowing who a person is beyond passing their Slack ID, and signing people in; connecting
  a branch deployment to Slack; slash commands, buttons, the home tab, files and images,
  replies that appear as they are written, and more than one workspace, all to be
  addressed later; group direct messages, confirmed out of scope by the owner on
  2026-11-16 and tracked in issue #13; dashboards and alerts for the receiving service;
  answering a held-back message a second time.
- **Naming the tools.** This specification names Slack, the template repository, the
  hostname and files in this repository because the project owner's request is about them
  specifically.
