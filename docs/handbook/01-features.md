# Features

## The agent

- A Python 3.14 program in `src/agent/` using the Strands Agents SDK.
- A system prompt in `src/agent/system_prompt.md`, set from the Backstage form.
- A model on Amazon Bedrock, chosen by the `ModelId` deployment parameter. It is set to
  `us.openai.gpt-6-luna`, the United States inference profile for OpenAI GPT-6 Luna, in
  `cfn-parameters.json`.
- A reasoning effort setting, `ReasoningEffort`, for how much the model reasons before it
  answers. It is `default`, which leaves the choice to the model.
- Input checks before the model is called: empty prompts and prompts over `MaxPromptChars`
  (4,000 characters by default) are rejected without spending tokens.
- A generic error reply. Failure details go to the log and never to the caller.
- Conversation memory in AgentCore Memory. Requests that share a session ID continue one
  conversation; its messages are kept for `MemoryEventExpiryDays` (7 days by default).

## Hosting

- An Amazon Bedrock AgentCore Runtime, which runs the agent as a Linux arm64 container image
  and costs nothing while idle.
- Callers authenticate with IAM. There is no public, unauthenticated endpoint.
- An IAM execution role scoped to the agent's log groups, model and image repository.

## Delivery

- Unit tests that replace the model with a fake, so they never call AWS.
- GitHub Actions workflows that test the agent, build and push its image, and deploy the stack.
  Every deploying branch gets its own stack and its own runtime.

## The STRIDEr Slack app

- A Slack app for STRIDEr, a coming agent that will lead threat modeling exercises using the
  STRIDE framework. Its definition is `slack/manifest.yaml`.
- A workflow that checks the definition on branches, applies it to Slack when it changes on
  `main`, reapplies it once a day, and creates the app only when started by hand.
- The app's ID, signing secret, client ID, client secret and bot token stored as GitHub
  values for a later feature to read.
- **STRIDEr answers.** A mention in a channel, or a direct message, gets the agent's reply in
  a thread. See [STRIDEr Slack messaging](09-slack-messaging.md). It answers as the agent
  does today; leading a STRIDE exercise is a later feature.

## The Slack receiving service

- A public address on API Gateway that accepts a request only when Slack's signature proves
  Slack sent it.
- Three Lambda functions in `src/handlers/`: one receives and queues, one asks the agent and
  posts the reply, one cleans up after a message that was not finished.
- Two SQS queues. No database: which threads STRIDEr takes part in is read from Slack.
- One Slack thread is one agent session, shared by everyone in the thread. A thread's
  earlier messages are given to the agent the first time STRIDEr answers in it.
- Only full members of the workspace are answered.
- What people write is never logged, and waits in a queue for at most an hour.
- Present only in the stack deployed from `main`.

## Observability

- One structured JSON log record per request, with a correlation ID, outcome, duration and
  token usage. Prompt and reply text are not logged.
- OpenTelemetry traces through the AWS distribution, delivered to AWS X-Ray.

## Not included

These are left for the project to add when it needs them: a chat front end other than Slack, reference
knowledge, tools and gateways, multi-agent orchestration, and dashboards or alerts.
