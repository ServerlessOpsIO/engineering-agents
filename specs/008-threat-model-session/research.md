# Research: STRIDEr Leads a Threat Modelling Session

**Date**: 2026-11-19 | **Spec**: `specs/008-threat-model-session/spec.md`

Each fact below is marked with how it is known:

- **Documented**: read on the named vendor page on 2026-11-19.
- **Source**: read in the source code of the version this repository pins.
- **Inferred**: follows from the documentation or source, and is not stated outright.
- **Believed**: from memory, common practice or a third party. Not in the documentation.

Nothing here has been tried against AWS, Slack or GitHub. "Open items" at the end lists
what must be tried and what happens if it turns out wrong.

## Facts checked: the agent's framework and memory

| # | Fact | Status | Source |
|---|------|--------|--------|
| F1 | Strands 1.65.0, which this repository pins, includes a plugin for the Agent Skills format (`strands.vended_plugins.skills`). It lists each skill's name and description in the system prompt and gives the model a `skills` tool. Calling it returns the skill's instructions **as a tool result**. | Source | `vended_plugins/skills/agent_skills.py` |
| F2 | The same package has a `Skill` class that reads and validates a `SKILL.md` (`Skill.from_file(path, strict=True)`), including the `allowed-tools` and `metadata` front matter. | Source | `vended_plugins/skills/skill.py` |
| F3 | With no conversation manager given, an agent keeps only the **last 40 messages** in the model's view. Older ones stay in memory and are not shown. A tool call and its result are two messages. | Source, Documented | `sliding_window_conversation_manager.py`; strandsagents.com, conversation management |
| F4 | The summarising manager acts only when the model's context overflows. | Source | `summarizing_conversation_manager.py` |
| F5 | The AgentCore memory session manager restores every message of the conversation on each request (up to 10,000 events) and applies the window after. It stores tool calls and results. `filter_restored_tool_context=True` leaves them out when restoring. | Source | `bedrock_agentcore/memory/integrations/strands/session_manager.py`, `config.py` (1.26.0) |
| F6 | The same session manager saves and restores the agent's key-value state (`agent.state`) with the conversation. | Source | as F5 |
| F7 | One stored message may be 100 KB; one event 10 MB. Writes are limited to 5 a second per conversation. | Documented | AgentCore devguide, limits |
| F8 | A failed read of the conversation returns an empty list, not an error. A memory fault would look like a conversation that has forgotten everything. | Source | as F5 |
| F9 | The runtime allows a 15-minute request. This stack sets idle timeout 300 s and maximum lifetime 1,800 s, after which the container is discarded and the next request restores from memory. | Documented, Source | AgentCore devguide, limits; `template.yaml` |
| F11 | Strands reads the agent's system prompt and its list of tools afresh before each call to the model within one request, and runs `BeforeModelCallEvent` hooks first. Tools can be added to and removed from the registry (`register_tool`, `remove`). | Source | `event_loop/event_loop.py`, `tools/registry.py`, `hooks/events.py` (1.65.0) |
| F10 | A runtime in `PUBLIC` network mode, as this one is, can make outbound HTTPS requests. Whether its outbound addresses are shared with other AWS customers is not documented. | Documented; the second part unknown | AWS CDK and networking blog |

## Facts checked: the model

| # | Fact | Status | Source |
|---|------|--------|--------|
| M1 | Nova 2 Lite (`us.amazon.nova-2-lite-v1:0`): 1,000,000-token context, 64,000 output tokens, tool calling supported, structured output not supported. Reasoning is off unless configured. | Documented | Bedrock model card |
| M2 | "Its performance (including system prompt adherence and tool use) can decline slightly as the context size increases." | Documented | Nova 2 user guide, advanced prompting |
| M3 | Long material should come first and instructions last. Rules are best given in named sections with strong words (DO NOT, MUST). Tools should be referred to by name. | Documented | Nova 2 user guide, prompting pages |
| M4 | AWS suggests splitting the work when there are more than 20 tools or a workflow regularly passes 15 to 20 turns. | Documented | Nova 2 user guide |
| M5 | About 150 output tokens a second with reasoning off. | Believed | A third-party benchmark, seen in search results only |
| M6 | The model card gives "EOL no sooner than Dec 02, 2026". That is a floor, not an announcement. | Documented | Bedrock model card |

## Facts checked: Slack

| # | Fact | Status | Source (docs.slack.dev unless noted) |
|---|------|--------|--------------------------------------|
| S1 | `markdown_text` is turned into Slack's own blocks. A pipe table becomes a Slack table, limited to 100 rows, 20 cells a row and 10,000 characters across a message's tables. | Documented | reference/methods/chat.postMessage; block-kit markdown and table blocks |
| S2 | Nothing documents what copying a displayed message gives. Since the message is stored as blocks, it is not the Markdown that was sent. | Inferred | No page says |
| S3 | A document inside a code block is limited to 12,000 characters a message, and an inner fence (the diagram's) closes the outer one. Whether a longer outer fence works is not documented. | Documented, Inferred | as S1; messaging/formatting-message-text |
| S4 | A file is uploaded in three steps (`files.getUploadURLExternal`, a POST of the bytes, `files.completeUploadExternal`), which `slack_sdk` 3.47.0 does in one call: `files_upload_v2(content=…, filename=…, title=…, channel=…, thread_ts=…)`. It accepts a string and needs no `files:read`. | Documented, Source | messaging/working-with-files; `slack_sdk/web/client.py` |
| S5 | Uploading needs the bot permission `files:write`. A new permission reaches the installed app only when the app is installed again. | Documented | reference/methods/files.completeUploadExternal; app-management/distribution |
| S6 | The app must be in the channel it uploads to (`not_in_channel`). STRIDEr is in any channel it is answering in. | Documented | as S5 |
| S7 | Uploading into a direct message by its `D…` ID is not stated in so many words. | Inferred | `channel_id` is "where the file will be shared" |
| S8 | How Slack previews a `.md` file is not documented. The file is stored as uploaded. | Inferred | reference/objects/file-object |
| S9 | A canvas takes Markdown and has no documented way to give it back. Free workspaces are limited to one per channel. | Documented | reference/methods/canvases.create |
| S10 | `users.info` returns `profile.display_name`, `profile.real_name` and `real_name` with the permission the app already has. Any may be missing or empty. `name` must not be used. Slack shows the full name when no display name is set. | Documented | reference/objects/user-object; Slack help, "Change your display name" |
| S11 | In message text a person is `<@U…>` or `<@W…>`, sometimes with `\|label`. Only `&`, `<` and `>` are escaped, as `&amp;`, `&lt;`, `&gt;`. | Documented | messaging/formatting-message-text |

## Facts checked: GitHub

| # | Fact | Status | Source (docs.github.com) |
|---|------|--------|--------------------------|
| G1 | Without a credential: 60 requests an hour **for each originating address**. A `User-Agent` header is required. A 404 counts. Over the limit gives 403 or 429 with `x-ratelimit-remaining: 0`. | Documented | rest, rate limits |
| G2 | `GET /repos/{owner}/{repo}` returns `private`, `visibility`, `default_branch`, `size`, `owner.login`, `full_name`. A private repository and a missing one both give 404. Names are not case sensitive. | Documented | rest/repos |
| G3 | A renamed or transferred repository answers 301. After a transfer, the old name can come to point at a repository with a different owner. | Documented | rest; repositories, transferring |
| G4 | `GET /repos/{owner}/{repo}/git/trees/{ref}?recursive=1` lists every file in one request, up to 100,000 entries or 7 MB, with a `truncated` flag and the commit's tree. | Documented | rest/git/trees |
| G5 | `raw.githubusercontent.com/{owner}/{repo}/{commit}/{path}` serves a file's bytes and is not counted in the 60. It has limits of its own, which are not published; over them it answers 429. | Documented in part | changelog, 2025-05-08 |
| G6 | A repository name is up to 100 characters of ASCII letters, digits, `.`, `-` and `_`. | Documented for GitHub Enterprise Server; believed the same on github.com | repositories, creating a new repository |

## Facts checked: method

| # | Fact | Status | Source |
|---|------|--------|--------|
| T1 | The severity table in FR-044 matches the OWASP Risk Rating Methodology, cell for cell. | Documented | owasp.org, OWASP Risk Rating Methodology |
| T2 | The methodology has 16 factors in four groups of four: threat agent (skill level, motive, opportunity, size), vulnerability (ease of discovery, ease of exploit, awareness, intrusion detection), technical impact (loss of confidentiality, integrity, availability, accountability), business impact (financial damage, reputation damage, non-compliance, privacy violation). | Documented | as T1 |
| T3 | The page is licensed CC BY-SA 4.0 (the site's footer). Its author is Jeff Williams. | Documented | as T1 |
| T4 | STRIDE by kind of element: external party S, R; process all six; data flow T, I, D; data store T, I, D. | Documented | Hernan, Lambert, Ostwald, Shostack, "Uncover Security Design Flaws Using The STRIDE Approach", MSDN Magazine, November 2006, figure 5 |
| T5 | Repudiation applies to a data store when it holds logs. | Documented | Shostack, "Experiences Threat Modeling at Microsoft", 2008 |

## The search for an existing skill (FR-006, FR-007)

Searched on 2026-11-19. The owner makes the final choice.

### Where

| Place | Result |
|-------|--------|
| `anthropics/skills`, `anthropics/claude-plugins-official`, `anthropics/claude-code`, `anthropics/knowledge-work-plugins` | Nothing for threat modelling. |
| `anthropics` organisation, code search | `anthropics/defending-code-reference-harness`, `.claude/skills/threat-model` (candidate A). |
| `openai/skills` | `skills/.curated/security-threat-model` (candidate B). Repackaged in `trailofbits/skills-curated`. |
| `trailofbits/skills` | Nothing. |
| `github/awesome-copilot` | `skills/threat-model-analyst` (candidate G). |
| `microsoft` organisation | `microsoft/hve-core`, `security-planning` (candidate H). |
| OWASP organisation | No skill for leading a STRIDE session. |
| `awslabs`, `aws-samples` | Two, both wrappers round a server or a command-line tool. |
| `vercel-labs/agent-skills`; agentskills.io | Nothing; the second is the specification only. |
| skills.sh | Listings found through web search; its own search page gave nothing. The most installed is `wshobson/agents`, `stride-analysis-patterns` (candidate E). |
| skillsmp.com, claude-plugins.dev | Refused the request (403, 402). **Not searched.** |
| Six "awesome" lists on GitHub | Only candidate B and one unrelated skill. |
| GitHub code search, `SKILL.md` with "STRIDE" | About 9,900 hits, mostly single files and copies of E. Candidates were picked by organisation, stars and fit. |

### Candidates read

Each was read at the commit given. "Read in full" means every file in the skill's folder.

| | Skill | Licence | Read | What it is | Verdict |
|---|-------|---------|------|-----------|---------|
| A | `anthropics/defending-code-reference-harness`, `.claude/skills/threat-model` (`d3bea6b`) | Apache-2.0 | In full | Three modes. Its interview mode leads a conversation with a system's owner, one question at a time, and is the only candidate designed as a conversation. No components and data flows, no diagram, no coverage table, no transfer or avoid. The agent still proposes attack classes and a mitigation "if the owner punts". Its other modes need a shell, file writing and subagents. | **Closest. Not adopted.** Use its interview structure as a guide. |
| B | `openai/skills`, `security-threat-model` (`49f948f`) | Apache-2.0 | In full | Analyses a repository in one go and writes a report. Not STRIDE. The agent does all the work. | Rejected. Its rules for a safe subset of Mermaid are worth using. |
| C | `Codeminer42/skills`, `threat-model` (`c8daf5d`) | MIT | In full | The agent maps the code; people agree the premise and make the acceptance decisions. Edits the repository's agent instructions. | Rejected. Its opening questions and "the agent accepts nothing" are worth using. |
| D | `briiirussell/cybersecurity-skills`, `threat-modeling` (`b198754`) | MIT | In full | One file. Covers every stage, with the four decisions and a Mermaid example. The agent does the analysis. Needs only file reading. | Rejected as a base: the agent does the work. Nearest to our stages. |
| E | `wshobson/agents`, `stride-analysis-patterns` (`4220308`) | MIT | In full | Reference material, not a way of working: questions for each STRIDE category and a table of categories by element. | Rejected as a base. A source for the question lists. |
| F | `jmanico/grim-prompter`, `threat-model` (`2a94457`) | MIT | Two files of about 350 | Unattended analysis. States explicitly that it does not interview. | Rejected. Its rule "do not make up a threat to fill a category" is worth using. |
| G | `github/awesome-copilot`, `threat-model-analyst` (`1683f50`) | MIT | In part | One-shot analysis writing five files. About 330 KB. | Rejected: too large, the agent does the work. Its coverage table layout is like ours. |
| H | `microsoft/hve-core`, `security-planning` (`cfbba35`) | MIT | In part | Supports a separate planning agent and drives Microsoft's desktop tool. Needs Python scripts. | Rejected: needs scripts. |

Eleven more were looked at and set aside: three have no licence and may not be copied;
the rest need a server, a command-line tool or subagents, or are specific to one
organisation. No file read contained hidden instructions or anything that sends data
elsewhere.

### Recommendation

**Write our own skill.** Every candidate except A's interview mode has the agent name the
threats, rate them and choose the mitigations, which is the one thing STRIDEr must not
do. Removing that from any of them leaves little. All but D and E also need abilities the
agent lacks. And the model is small, so the skill must be short and in the shape of our
stages and our tools.

Nothing is copied. The skill is written in our own words. `SOURCE.md` in the skill's
folder credits what it draws on: A for the shape of an interview, B for the Mermaid
rules, C, D, E and F for the ideas named above, the two Microsoft papers for the table of
categories by element, and OWASP for the rating method.

## Decisions

### Decision 1: the session is a record kept by code, not a memory kept by the model

- **Decision**: Everything the written model is made from is kept as structured data in
  the agent's state: the session record (`data-model.md`). The model changes it only by
  calling tools (`contracts/session-tools.md`). Code makes the written model and the
  facilitator's notes from the record (`contracts/written-model.md`).
- **Rationale**: Three facts force it. The framework shows the model only the last 40
  messages (F3), and a session is several hundred. The model follows its rules less well
  as its context grows (M2). And the written model must be complete, correctly formed and
  delivered inside 100 seconds (FR-037 to FR-039). With a record:
  - Nothing is lost when old messages leave the window.
  - The written model's structure, its diagram, its coverage table and its severities are
    always right, and are unit-tested without a model.
  - Writing it takes no model time, so its length cannot break the 100-second limit.
  - Rules that can be counted are kept by code: one hint per element per stage, notes only
    at the end, "act on the next message", a held-back repository finding, who took part,
    and the mark on a change made after the notes.
- **What it costs**: 25 small tools and a renderer to write and test, where the
  alternative was prose. The model must call the tools reliably; the fixed session tests
  that. What the model passes to a tool is still its own account of what people said
  (FR-024), which only a person reading a transcript can check.
- **Alternatives considered**:
  - *The conversation is the session, and the model writes the document.* Rejected: it
    needs the whole conversation in view every turn, which M2 warns against, and a long
    document written by the model inside 100 seconds, with nothing to guarantee its form.
  - *Keep every message in view* (no window). Rejected for the same reason.
  - *Summarise old messages.* Rejected: the summary is written by the model and can lose
    or change what a participant decided.

### Decision 2: what the model sees of the conversation

- **Decision**: The default window of 40 messages. Tool calls and their results are left
  out when the conversation is restored (`filter_restored_tool_context`, F5).
- **Rationale**: The record carries the facts; the recent messages carry the thread of
  talk. Leaving out old tool traffic keeps repository files from being sent to the model
  again on every later turn, which would slow it, cost more, and keep any planted text in
  front of it.
- **Consequence**: What the model reads from a repository is gone after the request that
  read it. Anything worth keeping must be recorded as a finding in that request.

### Decision 3: how the model is told what to do

- **Decision**: For each request the agent builds the system prompt from, in order: the
  session record; the active skill's instructions; the reference file for the current
  stage only; the list of skills; the persona. The tools offered are those of the current
  stage.
- **Rebuilt before every model call**, by a hook (F11), and not once for each request.
  A tool can start a session or change the stage in the middle of a request, and the
  model's next words must follow the new stage's instructions. The owner chose this on
  2026-11-19 over letting the instructions lag one message behind. It is read in the
  framework's source and not yet tried (open item O9).
- **Rationale**: M3 (instructions last, so the persona's rules are read last) and M4. A
  small prompt and few tools are the best defence against a small model losing its rules.
  The stage's reference file is the Agent Skills format's own idea of loading detail only
  when needed.

### Decision 4: skills are loaded by our code, using the framework's reader

- **Decision**: Skills live in `src/agent/skills/<name>/`. They are read and validated
  at start-up with the framework's `Skill` class, strictly (F2). The framework's plugin
  (F1) is not used. A skill becomes active when the model calls `start_session`; from
  then on its instructions are in the system prompt for as long as its record exists, which includes after the session has
  finished, until a new one starts.
- **Rationale**: The plugin delivers a skill's instructions as a tool result. Under
  Decision 2 that result is gone by the next request, and under F3 it would leave the
  window anyway. A skill's instructions must be present on every turn of a session.
- **FR-004 is met**: the format is the published one, and the skill is taken up only when
  a session is asked for. Before that the model sees its name and description only.
- **Adding a skill** is adding a folder. A skill that needs tools the agent lacks also
  needs their code. The persona is not touched (SC-014).

### Decision 5: the persona

- **Decision**: `src/agent/system_prompt.md` becomes `src/agent/persona.md`. It holds
  who STRIDEr is, how it speaks, and the rules of FR-003, each under a fixed heading that
  the unit tests look for. It names no stage and no tool.
- **The owner approves its wording** before the feature is complete (FR-003). A draft is
  written in the first task that touches it and brought to the owner on its own.

### Decision 6: staying quiet

- **Decision**: The model stays quiet by replying with the marker `[[quiet]]` and nothing
  else. The agent turns that into a reply of kind `no_reply`. Whether quiet is allowed is
  decided by code from the request: only in a channel thread, when the message does not
  mention STRIDEr, during a session. Otherwise the message is marked "a reply is
  required", and if the marker still comes back the model is asked once more.
- **Rationale**: FR-027 and FR-028 are then kept by code. A marker costs one model call.
- **Alternative considered**: a `stay_quiet` tool. Rejected: after a tool call the model
  speaks again, which costs a second call and leaves words in memory that nobody saw.

### Decision 7: the written model is delivered as a file

- **Decision**: The worker uploads each document to the conversation as a Markdown file
  (S4). The app gains the permission `files:write` and must be installed again (S5).
- **Rationale**: It is the only way the Markdown reaches a person exactly as written
  (S1 to S3). It also removes the question of length.
- **Cost**: one new permission, which lets the app upload files to any conversation it
  is in; installing the app again; a third kind of call to Slack in the worker.
- **Alternatives considered**: a code block (several messages to stitch, and the
  diagram's fence breaks it); formatted text (cannot be copied back out as Markdown); a
  canvas (same, and limited on a free workspace).
- **The spec changed** to match: US1 scenario 6, FR-038 and FR-039 no longer speak of
  numbered parts for the model.

### Decision 8: reading a repository

- **Decision**: Three tools (`contracts/session-tools.md`). One request to GitHub for
  the repository, one for its list of files, then each file from
  `raw.githubusercontent.com` at the commit the list was taken at (G2, G4, G5). The list
  is kept in the agent's state, so a session costs two counted requests for each
  repository. Standard library only; no new package.
- **Kept by code**: the owner is fixed by a setting; the name must have been written by a
  person in the conversation; redirects are not followed (G3); the answer must say the
  owner is the organisation and the repository is public; a path must be in the list;
  30,000 characters a file, 8 files a request, 30 a session; 10 seconds a request.
- **Planted instructions** (FR-033): content is returned between markers with a line
  saying it is content. The model has no tool that acts on the world, so the worst a
  planted instruction can do is make STRIDEr say something or record something false.
  The persona's rule and Decision 2 limit that.
- **No credential**, as the owner decided. See open item O3.

### Decision 9: categories by kind of element

- **Decision**: External party S, R. Component all six. Data flow T, I, D. Data store T,
  R, I, D (T4, T5). A trust boundary is not an element and has no row.
- **Rationale**: The 2006 table, with repudiation kept for data stores because many hold
  logs and the participants can record "none found" in one word when theirs does not.
  Sources disagree on this cell; the skill says why it is there.

### Decision 10: people's names

- **Decision**: The worker takes the name from the lookup it already makes (S10), cleans
  it (`data-model.md`) and sends it. It replaces mentions of people with names. The
  agent adds each speaker to the participants by code.
- **A name is treated as untrusted text**: a display name is chosen by its owner and
  goes in front of the model. Cleaning removes line breaks and markup and limits length.

### Decision 11: the OWASP material

- **Decision**: The factors are restated in our own words in the rating stage's
  reference file, as questions STRIDEr may ask. The table is in code. `SOURCE.md`
  credits the methodology, its author and its licence (T3), and the written model's
  Method section links to it.

### Decision 12: the fixed session

- **Decision**: `scripts/play_session.py` plays the turns of a YAML file and checks what
  code can check (`contracts/agent-interface.md`). Each turn is written to stand alone,
  whatever STRIDEr asked before it.
- **It is run three times** for acceptance, because one run of a model proves little.
  What must pass is in the spec, "How acceptance is judged" (owner, 2026-11-19):
  structure always; the rule against doing the work always; the rest of the behaviour
  recorded on the stopgap model and held to two of three on its replacement.

## Open items

| # | What is not known | How it is found out | If it is wrong |
|---|-------------------|---------------------|----------------|
| O1 | **Whether Nova 2 Lite can hold the rules and call the tools through a whole session.** The largest risk. | An early task plays the fixed session as soon as the skill's first draft and the tools exist. | Shorten the skill and try once more. If it still cannot, stop: Nova 2 Lite is a stopgap, and the owner decides whether to wait for the model that replaces it. `ReasoningEffort` is not tried (issue #20). |
| O2 | Whether the agent's traces carry message text. **Looked at on 2026-11-19, read-only, in the `main` stack's account.** Read in source: Strands 1.65.0 puts user messages, replies, the system prompt, tool arguments and tool results on its spans unless `OTEL_SEMCONV_STABILITY_OPT_IN` carries `gen_ai_unredacted_attributes=`; the Bedrock call instrumentor captures content only when `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` is true. Neither is set in this stack. Seen in the account: X-Ray's trace destination is `XRay` and its indexing is 0%, which is CloudWatch Transaction Search turned off; seven six-hour windows across the last three days held no trace; the runtime's `otel-rt-logs` stream holds ordinary log records with no `gen_ai` field and no body over 320 characters. **So no message text is being stored today, because no traces are.** Not proven for every hour of the last 30 days. | Done, as far as it can be without traces. | Text would start to be stored the moment Transaction Search is turned on, which the handbook lists as a prerequisite. Task T006 sets both settings first. |
| O3 | Whether GitHub's limit of 60 an hour is usable from the runtime's outbound address (F10, G1). | Scenario G of the quickstart, and the log's count of refusals afterwards. | STRIDEr says it cannot read and carries on, as designed. The lasting answer is a credential, which is issue #18. |
| O4 | Uploading a file into a direct message, and how Slack shows a `.md` file (S7, S8). | Scenario D and E. | Try `snippet_type`. If a direct message refuses the upload, the person sees the document-not-posted sentence. No fallback is built in advance; task T031 stops and the owner decides. |
| O5 | That leaving tool traffic out on restore never leaves the conversation in an order the model rejects. | A unit test in task T018, covering a turn that failed part-way, which the fixed session cannot produce; then the fixed session. | Where two messages from a person are left running, the agent joins them (`contracts/agent-interface.md`). If the order still fails: keep tool traffic, and cut a file's content down to a line once recorded. |
| O6 | That the agent's state is restored on every request, including after the container is discarded (F6, F9). | Scenario E, step 4. | Without it there is no feature. Nothing suggests it fails. |
| O7 | That a memory fault shows as an empty session (F8). | Cannot be forced. | A participant is told there is no session in progress. Accepted; noted in the handbook. |
| O9 | That changing the system prompt and the tools from a `BeforeModelCallEvent` hook takes effect on the very next model call (F11). | A unit test in task T018 with a fake model that records what it was sent on each call; then the fixed session's first turn. | Fall back to having the tool's answer carry the next stage's guidance, with full instructions from the next message. |
| O8 | Speed (M5): several tool calls and a reply inside 100 seconds. | The fixed session reports each turn's time. | Lower the number of files read in one request. |
