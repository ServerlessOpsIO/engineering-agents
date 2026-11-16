# Feature Specification: STRIDEr Slack App Deployment

**Feature Branch**: `feature/006-slack-app-deployment`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "As a developer I can deploy my STRIDEr Slack bot using IaC and a
CI/CD pipeline." The project owner expanded this in conversation into a story, a proposed
solution, scope boundaries, dependencies and acceptance criteria, which this specification
records.

**Background**: STRIDEr is a coming Slack agent in this repository. It will lead threat
modeling exercises in Slack using the STRIDE framework. Two things have to exist before it
can: a Slack app that represents STRIDEr in the workspace, and a service on the cloud
platform that receives messages from Slack and answers them. This feature is the first of
those and nothing else. The second is a later feature, and it needs values that only exist
once the Slack app does, so the Slack app is created and deployed on its own first.

**Terms**:

- **Slack app**: the thing registered with Slack that gives STRIDEr its name, its bot user
  and its permissions in a workspace.
- **App definition**: the file in this repository that describes the Slack app. Slack calls
  this an app manifest.
- **Slack files**: the files the Slack part of the pipeline watches: the app definition and
  its settings (`slack/**`), the program that applies them (`scripts/slack_app/**`) and the
  Slack workflow file. "The app definition or its settings" in the answers below means
  these files.
- **Pipeline**: the automated jobs that run when a branch is pushed or merged to `main`.
- **Event delivery address**: the public web address Slack sends messages to. It belongs to
  the later feature.
- **App values**: the app ID, the signing secret, the client ID, the client secret and the
  bot token. The later feature reads all five.

## Clarifications

### Session 2026-11-16

- Q: Should the pipeline send the app definition to Slack on every merge to `main`, or only on merges that change the app definition? → A: Only on merges that change the app definition or its settings, plus a scheduled run, at least once a day, that undoes changes made by hand. Merges that change neither never contact Slack.
- Q: If the STRIDEr Slack app has been deleted, should the pipeline create a replacement by itself, or stop and wait for the owner? → A: Stop. Merges and scheduled runs fail with a message naming the problem and never create an app. A pipeline run that the owner starts by hand creates the app, with no commands run on the owner's own machine. The same run is used for the first-time setup.
- Q: When a merged change adds a permission, which Slack only applies after the app is installed again, should the pipeline pass, warn, or fail until the install is done? → A: Fail. The run applies the change and then fails, and scheduled runs keep failing until the app has been installed again.
- Q: When the Slack part of a run on `main` fails, should the agent's own build and deployment still go ahead? → A: Yes. The two are independent in both directions. The run as a whole shows as failed because of the Slack part.
- Q: How should the owner be told when a scheduled run fails? → A: Both by the repository hosting service's own failure notification, and by an issue opened automatically in the repository and closed when a later run passes.
- Q: Should a run fail when the installed app still holds a permission that was removed from the app definition? → A: No, it passes for now. Only a permission the app definition has and the installed app lacks fails the run. What Slack does when a permission is removed is to be found out; tracked in issue #7.
- Q: Must a reply in a thread mention STRIDEr for STRIDEr to receive it? → A: No. STRIDEr receives replies in threads it is part of without a mention. The owner accepts that this needs permissions that let STRIDEr read every message in channels it has been added to.
- Q: Should a failed merge open an issue, or only a failed scheduled run? → A: Only a failed scheduled run.
- Q: The failure issue would not be opened when a scheduled run fails before it reaches the step that applies the app definition. Should that be fixed? → A: Yes. A failed scheduled run is reported whichever part of it failed.
- Q: Slack also issues a client ID and a client secret when the app is created. Should they be kept? → A: Yes. Both are stored as secrets so the later feature's deployment can refer to them.
- Q: Is removing the Slack app or retiring STRIDEr part of this feature? → A: No. Out of scope.
- Q: Should a deleted app be told apart from Slack being unreachable or the pipeline credential being refused? → A: Yes. Each is reported as itself.
- Q: What makes an app definition invalid? → A: It fails Slack's published schema for app definitions, or this project's own rules, or Slack's own validation rejects it. Slack publishes the schema; a copy is kept in the repository.
- Q: What should happen when Slack refuses the stored bot token? → A: The run fails saying the stored bot token is no longer valid, and does not report it as a missing permission.
- Q: Where else must secrets never appear, given the repository is public? → A: In issues and pull requests. The hosting service masks stored secrets in pipeline logs.
- Q: Should the pipeline keep using a short-lived credential that is replaced on every run and has to be written back each time, or a Slack CLI service token that does not expire? → A: A service token. The owner prefers one long-lived credential that the pipeline only reads over one that every run must replace and store. The owner confirmed on 2026-11-16 that Slack's validation accepts it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A change to the app definition reaches Slack by merging (Priority: P1)

A developer edits the app definition, for example to change STRIDEr's description or add a
permission, opens a pull request, and merges it. The Slack app then matches the file. The
developer never opens the Slack console.

**Why this priority**: This is the feature. Everything else supports it or protects it.

**Independent Test**: Change the description in the app definition, merge to `main`, and
look at the app in the `serverlessops` workspace. The description has changed and nobody
did anything by hand.

**Acceptance Scenarios**:

1. **Given** the Slack app exists and matches the app definition, **When** a change to the
   app definition is merged to `main`, **Then** the Slack app matches the new definition
   with no manual step.
2. **Given** the Slack app exists and matches the app definition, **When** a merge to `main`
   changes none of the Slack files, **Then** the pipeline does not contact Slack, the Slack
   app is unchanged, and the pipeline does not fail.
3. **Given** someone changed the Slack app by hand in the Slack console, **When** the next
   scheduled run happens, or a change to the app definition is merged, whichever is first,
   **Then** the Slack app matches the app definition again.
4. **Given** Slack rejects the change or cannot be reached, **When** a run that contacts
   Slack happens, **Then** the Slack part fails and says why, the failure can be told apart
   from a failure of the agent's own build and deployment, and the agent's build and
   deployment for the same commit still complete.
5. **Given** the app is installed, **When** a merged change adds a permission, **Then** the
   run applies the change and fails, saying the app must be installed again.
6. **Given** a permission is waiting for the app to be installed again, **When** a
   scheduled run happens, **Then** it fails for that reason; **When** the app has been
   installed again, **Then** the next scheduled run passes.

---

### User Story 2 - A bad app definition is caught before it is merged (Priority: P1)

A developer pushes a branch with a mistake in the app definition. The pipeline fails on the
branch and says why. The Slack app is untouched.

**Why this priority**: There is one Slack app and no test copy. A check before merging is
the only protection it has.

**Independent Test**: Push a branch whose app definition has an unknown permission. The
pipeline fails and names the problem. The Slack app is unchanged.

**Acceptance Scenarios**:

1. **Given** a branch with an invalid app definition, **When** it is pushed, **Then** the
   pipeline fails, reports what is wrong, and changes nothing in Slack.
2. **Given** a branch with a valid app definition, **When** it is pushed, **Then** the
   pipeline passes and changes nothing in Slack.
3. **Given** a branch that changes none of the Slack files, **When** it is pushed,
   **Then** the Slack part does not run, and the existing agent build and branch deployment
   behave as they did before this feature.

---

### User Story 3 - The app is created from nothing by following the documentation (Priority: P2)

A developer starting with a workspace that has no STRIDEr app follows the documented steps
and ends with STRIDEr present in the workspace, installed, and managed by the pipeline. Every
step a person must do by hand is named, with the reason it cannot be automated.

**Why this priority**: It happens once, but if it is not written down the app cannot be
rebuilt after it is deleted or the workspace changes.

**Independent Test**: With no STRIDEr app in the workspace, follow the documentation from
the first step to the last. STRIDEr appears in the workspace with the name and permissions
in the app definition.

**Acceptance Scenarios**:

1. **Given** no STRIDEr app exists, **When** the developer starts the creation run as
   documented, **Then** the app is created from the app definition and is then managed by
   the pipeline.
2. **Given** the app has been created, **When** the developer completes the documented
   installation step, **Then** STRIDEr appears in the `serverlessops` workspace with the
   name and permissions in the app definition.
3. **Given** the documentation, **When** a reader counts the steps done by hand, **Then**
   each one is named and explained: creating the two credentials the pipeline needs,
   installing the app to the workspace, and storing the bot token.
4. **Given** the recorded app has been deleted, **When** a merge or a scheduled run
   contacts Slack, **Then** it fails, creates nothing, and names the creation run.
5. **Given** the recorded app still exists, **When** the developer starts the creation run,
   **Then** it refuses and creates nothing.

---

### User Story 4 - The later feature can read the app's values (Priority: P2)

After the app is deployed and installed, its app ID, signing secret, client ID, client
secret and bot token are stored
where the later feature's pipeline can read them, and nowhere a person can read them by
accident.

**Why this priority**: It is the reason this feature goes first. Without it the later
feature has nothing to build on.

**Independent Test**: After User Story 3, confirm the five values are stored, that the
stored app ID matches the app in Slack, and that no secret among them appears in the
repository, a pipeline log, an issue or a pull request.

**Acceptance Scenarios**:

1. **Given** the app has been created and installed, **When** the developer checks the
   store, **Then** the app ID, the signing secret, the client ID, the client secret and the
   bot token are all present.
2. **Given** any pipeline run, **When** its logs, its summary and any issue it opened are
   read, **Then** no secret value appears.
3. **Given** the repository at any commit of this feature, **When** it is searched,
   **Then** no secret value is found.

---

### User Story 5 - The event delivery address is added later without rework (Priority: P3)

When the later feature has a public address for Slack to send messages to, a developer
supplies it as a setting and merges. The Slack app is given the address and the events it
subscribes to. The app definition's structure and the pipeline do not have to be
redesigned.

**Why this priority**: It is only exercised by the later feature, but deciding it now is
what stops that feature from reopening this one.

**Independent Test**: Deploy with no address and confirm success. Then supply a placeholder
address and confirm the pipeline carries it, and the events, into what it sends to Slack.

**Acceptance Scenarios**:

1. **Given** no event delivery address is set, **When** the pipeline runs, **Then** it
   succeeds and the Slack app has no event delivery address and subscribes to no events.
2. **Given** an event delivery address is set, **When** the pipeline runs on `main`,
   **Then** the Slack app is given that address and the events listed in the app
   definition, and no file other than the setting had to change.
3. **Given** the address has been sent to Slack, **When** nobody has yet verified it in
   Slack, **Then** Slack does not deliver events. Verifying it is done once by hand, needs
   the receiving service to be answering, and belongs to the later feature.

---

### Edge Cases

- The credential the pipeline uses to change Slack apps has expired or been used up. The
  pipeline must fail with a message that says so and points to the documented recovery
  steps; it must not leave the stored credential in a state that makes the next run fail
  too without saying why.
- The Slack app was deleted by hand. Merges and scheduled runs fail and say so. The owner
  starts the creation run, which makes a new app with a new app ID, signing secret, client
  ID and client secret; the app must then be installed again and the bot token stored
  again. The documentation must
  say that everything that used the old values must be updated.
- A change to the app definition adds a permission. Slack requires the app to be installed
  again before a new permission takes effect. The run applies the change and then fails,
  saying the app must be installed again and how. Scheduled runs fail the same way until it
  has been, and pass by themselves afterwards.
- Two runs that contact Slack close together, whether merges or a merge and a scheduled
  run. The Slack app must end up matching the later one.
- The creation run creates the app and then fails to store a value: the app ID, the
  signing secret, the client ID or the client secret.
  The change already made in Slack is left in place, the run fails and says which value
  was not stored, and the documentation must cover recovery.
- The app still exists but one of its stored values has been lost. The creation run
  refuses, because the app exists. The documentation must say where the owner reads the
  value again in Slack and how to store it.
- An event delivery address is set but nothing is listening at it yet. The pipeline sends
  the address and does not check that it answers. Slack keeps the address but delivers no
  events until someone verifies it by hand (found in planning).
- A pull request from a fork, or any run that has no access to the stored credentials. It
  must be able to check the app definition as far as that is possible without credentials,
  and must never change Slack.

## Requirements *(mandatory)*

### Functional Requirements

**The app definition**

- **FR-001**: The repository MUST contain one app definition that is the single source of
  truth for the STRIDEr Slack app's name, description, bot user, permissions and the events
  it subscribes to.
- **FR-002**: The app definition MUST let people reach STRIDEr by mentioning it in a
  channel, by replying in a thread it is part of, with or without mentioning it, and by
  direct message.
- **FR-003**: The app definition MUST request only the permissions and events FR-002 needs.
  Each permission MUST have its reason recorded where a reviewer can see it.
- **FR-004**: The app definition MUST NOT define slash commands, shortcuts, modals, the
  app's home tab, or distribution to other workspaces. The app's messages tab, which Slack
  needs switched on for direct messages, is allowed.
- **FR-005**: The Slack app MUST receive events over HTTPS at an event delivery address, and
  MUST NOT use a persistent connection opened by the bot.
- **FR-006**: The event delivery address MUST be a setting that can be absent. With it
  absent the app definition is still valid and deployable. Slack does not accept
  subscribed events without an address, so while it is absent the events stay listed in
  the app definition and are left out of what is sent to Slack. Supplying the address
  later MUST NOT require changing the structure of the app definition or of the pipeline.

**The pipeline**

- **FR-007**: On every branch push that changes a Slack file, the pipeline MUST check that
  the app definition is valid, as SC-002 defines it, and MUST NOT change anything in Slack.
- **FR-008**: On every merge to `main` that changes a Slack file, the
  pipeline MUST make the Slack app match the app definition by updating the recorded app.
  It MUST NOT create an app.
- **FR-009**: A merge to `main` that changes none of the Slack files MUST NOT contact Slack, and a Slack outage or an expired pipeline credential MUST NOT
  fail it.
- **FR-010**: A scheduled run, at least once a day, MUST make the Slack app match the app
  definition on `main`, so that a change made outside the pipeline is undone within a day.
  A scheduled run that finds nothing to undo MUST succeed and leave the Slack app as it
  was. A failed scheduled run MUST be reported as FR-026 says.
- **FR-011**: A failure in a Slack step MUST fail the pipeline, MUST be identifiable as a
  Slack failure and not an agent build or deployment failure, and MUST say what a person
  should do next.
- **FR-012**: The Slack part and the agent's build and deployment MUST be independent. A
  failure of either MUST NOT stop or undo the other for the same commit, and the commit
  MUST show a failed check if either fails. They may be separate pipeline runs. The Slack
  part MUST NOT change how the existing agent build, branch deployment and `main`
  deployment behave.
- **FR-013**: There MUST be exactly one STRIDEr Slack app, in the `serverlessops` workspace,
  managed from `main`. Branches MUST NOT create or change any Slack app. A branch run may
  read the pipeline credential, because asking Slack to validate needs it.
- **FR-023**: Creating the Slack app MUST be done only by a pipeline run that a person
  starts by hand. It is used for the first-time setup and to replace a deleted app, and it
  MUST NOT require commands to be run on a person's own machine. It MUST refuse to create
  an app while the recorded app still exists.
- **FR-024**: A merge or a scheduled run that finds no app recorded, or finds the recorded
  app gone, MUST fail, MUST NOT create an app, and MUST name the run in FR-023 as the way
  forward. The app counts as gone only when Slack says it does not exist. Slack being
  unreachable, or the pipeline credential being refused, MUST be reported as that failure
  and never as a deleted app, and MUST NOT lead any run to create an app.
- **FR-025**: When the installed app lacks a permission that the app definition has, a run
  that contacts Slack MUST still apply the app definition, and MUST then fail with a
  message saying the app must be installed again and how. Scheduled runs MUST keep failing
  for this reason until the installed app holds every permission in the app definition,
  and MUST then pass without any other action. A permission the installed app holds that
  the app definition does not have MUST NOT fail the run. If the bot token is replaced by
  the install, the message MUST say that the stored bot token must be updated too.
- **FR-026**: A failed scheduled run, whichever part of it failed, MUST reach the project
  owner in two ways: the repository hosting service's own failure notification, and an issue opened in the
  repository that names the failure and what to do. While the same failure continues there
  MUST be one open issue, not one for each run. The issue MUST be closed automatically when
  a later run that contacts Slack passes. The documentation MUST say which notification
  settings the owner needs.
- **FR-027**: When Slack refuses the stored bot token, a run that contacts Slack MUST fail
  with a message saying the stored bot token is no longer valid and must be stored again.
  It MUST NOT report this as a missing permission.

**Credentials and app values**

- **FR-014**: The credentials the pipeline needs, to change Slack apps and to store values
  in the repository's hosting service, MUST be stored as secrets in that service and MUST
  NOT be in the repository. Each MUST have only the access this feature needs. The
  documentation MUST say when each expires and what a run does once it has.
- **FR-015**: The credential for changing Slack apps MUST be one that using it does not
  replace, so that no run has to write a credential back and the next run works without a
  person stepping in. Only the creation run may write to the repository's hosting service,
  and only the app's values (FR-016).
- **FR-016**: The app ID, the signing secret, the client ID and the client secret MUST be
  stored by the creation run when the app is created, where the later feature's pipeline
  can read them. All but the app ID are stored as secrets.
- **FR-017**: The bot token MUST be stored in the same place. If installing the app cannot
  be automated, a person stores it, and that step MUST be documented.
- **FR-018**: No secret value may appear in the repository, in pipeline logs or run
  summaries, in an issue or a pull request, or in any file the pipeline keeps after a run.
  The hosting service masks stored secrets in logs. A secret obtained during a run MUST be
  masked before anything else is printed.

**Scope and documentation**

- **FR-019**: This feature MUST NOT change `template.yaml`, `cfn-parameters.json`, or any
  resource on the cloud platform.
- **FR-020**: The documentation MUST describe the one-time setup from a workspace with no
  STRIDEr app to an app managed by the pipeline, and MUST name every step done by hand and
  why it is done by hand: creating the credential for changing Slack apps, creating the
  credential for storing values, installing the app, and storing the bot token.
- **FR-021**: The documentation MUST describe how to change the app afterwards, how to
  supply the event delivery address, what to do when a change needs the app to be installed
  again, and how to recover from each failure listed under Edge Cases.
- **FR-022**: Planning MUST compare two ways of making the Slack app match the app
  definition, calling Slack's own app definition service directly from the pipeline, and
  using Terraform with a community-maintained Slack provider, and MUST record the choice
  and the reasons. The project owner leans towards the first and wants a real comparison.

### Key Entities

- **App definition**: the file describing the Slack app. Holds the name, description, bot
  user, permissions and subscribed events.
- **Slack app**: the app registered in the `serverlessops` workspace. There is one. It is
  identified by its app ID.
- **Pipeline credential**: what lets the pipeline create and change Slack apps on the
  owner's behalf. A Slack CLI service token: issued to the owner, long-lived, and not
  replaced when used. The pipeline reads it and never writes it.
- **App values**: the app ID (not secret); the signing secret, client ID and client secret
  (stored as secrets, issued when the app is created); and the bot token (secret, issued
  when the app is installed). Produced here, consumed by the later feature.
- **Event delivery address**: an optional setting kept beside the app definition, not in
  it. Empty in this feature; supplied by the later feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A change to the app definition merged to `main` is visible in the Slack app
  within 10 minutes. A change that adds no permission needs zero manual steps; one that
  adds a permission needs exactly one, installing the app again.
- **SC-002**: 100% of branch pushes with an invalid app definition fail the pipeline, and
  none of them changes the Slack app. An app definition is invalid when it fails Slack's
  published schema for app definitions, fails this project's own rules (FR-003 to FR-006),
  or is rejected by Slack's own validation.
- **SC-003**: A merge to `main` that touches none of the Slack files passes without contacting Slack, and the Slack app is the same before and after.
- **SC-004**: A developer who has not done it before can go from a workspace with no
  STRIDEr app to an installed, pipeline-managed app in under 30 minutes using only the
  documentation.
- **SC-005**: The one-time setup has exactly four steps done by hand, each documented with
  its reason: creating the credential for changing Slack apps, creating the credential for
  storing values, installing the app to the workspace, and storing the bot token.
  Everything else is done by the pipeline.
- **SC-006**: After setup, STRIDEr appears in the `serverlessops` workspace with the name
  and exactly the permissions in the app definition.
- **SC-007**: After setup, all five app values are stored where the later feature can read
  them, and the stored app ID matches the app in Slack.
- **SC-008**: A search of the repository, of the logs and summaries of every pipeline run
  made for this feature, and of every issue and pull request it produced, finds zero
  secret values.
- **SC-009**: A change made by hand in the Slack console is gone within 24 hours without
  anyone merging anything.
- **SC-010**: Ten runs that contact Slack in a row, merges and scheduled runs together,
  succeed without a person touching a credential.
- **SC-011**: `template.yaml` and `cfn-parameters.json` are identical before and after this
  feature.
- **SC-012**: While scheduled runs are failing there is exactly one open issue, and it is
  closed within one day of the cause being fixed, without anyone closing it by hand.

## Assumptions

- **Storage is a starting choice.** The project owner chose the repository hosting service's
  secrets for both the pipeline credential and the app values, to be changed if it causes
  problems. One known difficulty: a pipeline cannot write those secrets with the access it
  has by default, so it will need an extra credential. Planning must design for this.
- **Facts about Slack.** Planning checked these against Slack's documentation on
  2026-11-16 and found them documented: a service token is long-lived and is not replaced
  when used; the signing secret, client ID and client secret are returned when an app is
  created; adding a permission requires the app to be installed again; subscribed events
  need an address; an address must be verified by hand. Tried by the owner on 2026-11-16:
  Slack's validation accepts a service token. Still believed and not documented: Slack's
  other app definition methods accept one too; installing an app cannot be done without a
  person; the permissions an installed app holds can be read back. `research.md` lists each with what happens if it is
  wrong.
- **Branch runs can read the pipeline's credentials**, because asking Slack to validate
  needs them. Accepted while the project owner is the only person who can push to the
  repository; to be revisited if that changes.
- **The repository is public**, so pipeline logs, run summaries, issues and pull requests
  are public.
- **Drift is overwritten, not reported.** The project owner accepted either. Overwriting is
  simpler and matches "the app definition is the single source of truth". It happens on the
  scheduled run, so a hand-made change can last up to a day.
- **The pipeline can tell what the installed app holds.** FR-025 depends on the pipeline
  being able to read the permissions the installed app actually has. This is believed
  possible and is unchecked. If it turns out not to be, FR-025 must come back to the
  project owner.
- **Before the first install, nothing is waiting.** A run that finds the app created but
  never installed does not fail under FR-025; the first-time setup covers that step.
- **Issues are for scheduled runs.** A failed merge is seen by whoever merged, so it does
  not open an issue. Confirmed by the project owner on 2026-11-16.
- **STRIDEr can read whole channels.** Receiving thread replies that do not mention it
  needs permissions that cover every message in a channel STRIDEr has been added to; Slack
  offers nothing narrower. Accepted by the project owner on 2026-11-16.
- **Removed permissions are not checked.** Whether an installed app keeps a permission
  after it is removed from the app definition is unknown; see issue #7.
- **Once a day is a starting value** for the scheduled run, chosen by the author.
- **The owner can do the manual steps.** The project owner is an admin of the
  `serverlessops` workspace and can create the pipeline credential and approve the install.
- **Independence holds for this feature only.** Nothing on the cloud platform depends on
  the Slack app yet. The later feature will, and must decide the order for itself.
- **One environment.** There is no development or per-branch Slack app, so a change is
  first seen for real on `main`. User Story 2 is the mitigation.
- **STRIDEr will not answer yet.** After this feature STRIDEr is present in the workspace
  and does nothing when spoken to. That is expected until the later feature.
- **Out of scope**: the service that receives Slack events, verifying the event delivery
  address in Slack, checking that requests really come from Slack, the agent's runtime,
  STRIDEr's prompt and behaviour, the STRIDE exercise itself, conversation memory, and
  removing the Slack app or retiring STRIDEr.
- **Naming the tools.** This specification names Slack, Terraform and files in this
  repository because the project owner's request is about them specifically. Planning
  chose to call Slack's own app definition service directly (FR-022; `research.md`,
  Decision 1).
