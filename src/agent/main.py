"""Agent entry point for Amazon Bedrock AgentCore Runtime.

Serves POST /invocations and GET /ping on port 8080 through BedrockAgentCoreApp.
The wire format is described in docs/handbook/04-architecture.md and in
specs/008-threat-model-session/contracts/agent-interface.md.

What the model is told and which tools it is offered are rebuilt before every
call to the model, from the session record, so they always match it.

Prompt text, reply text, people's names, tool arguments and documents are never
logged.
"""

import datetime
import json
import logging
import os
import re
import sys
import time

from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from starlette.responses import JSONResponse
from strands import Agent
from strands.hooks import BeforeModelCallEvent
from strands.models import BedrockModel
from strands.tools.executors import SequentialToolExecutor

import prompt as prompts
from github import Repositories
from session import record as rec
from session.tools import CHANNEL_THREAD, DIRECT_MESSAGE, Turn, make_tools, tools_for


def _require_env(name):
    """Return a required environment variable, or stop the agent from starting."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"The {name} environment variable is not set.")
    return value


MODEL_ID = _require_env("MODEL_ID")
# How much the model reasons before answering. Unset, empty or "default" leaves
# the choice to the model.
REASONING_EFFORT = os.environ.get("REASONING_EFFORT")
MAX_PROMPT_CHARS = int(os.environ.get("MAX_PROMPT_CHARS", "4000"))
MEMORY_ID = os.environ.get("MEMORY_ID")
DEFAULT_ACTOR_ID = "default"

EMPTY_PROMPT_TEXT = "Please send a prompt."
LONG_PROMPT_TEXT = "The prompt is too long. The limit is {limit} characters."
ERROR_TEXT = "The agent could not produce a reply. Try again later."

UNKNOWN_SPEAKER = "Someone"
NAME_CHARS = 80
END_WARNING_SECONDS = 24 * 60 * 60

logger = logging.getLogger("agent")
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
    logger.propagate = False

app = BedrockAgentCoreApp()

_model = None


class QuietWhenAReplyWasRequired(Exception):
    """The model stayed quiet twice when it had to reply. The caller treats it as a failure."""


def get_model():
    """Create the model client on first use so importing this module calls nothing."""
    global _model
    if _model is None:
        options = {"model_id": MODEL_ID}
        if REASONING_EFFORT and REASONING_EFFORT != "default":
            options["additional_request_fields"] = {"reasoning": {"effort": REASONING_EFFORT}}
        _model = BedrockModel(**options)
    return _model


def build_agent(session_id, actor_id):
    """Return an agent for one request.

    With MEMORY_ID set, the session's earlier messages and the agent's state are
    loaded from AgentCore Memory, and this exchange is saved to it. Tool calls
    and their results are left out of what is restored, so that a file read from
    a repository is not sent to the model again on every later turn. Without
    MEMORY_ID, the agent starts empty.
    """
    session_manager = None
    if MEMORY_ID and session_id:
        session_manager = AgentCoreMemorySessionManager(
            AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=session_id,
                actor_id=actor_id,
                filter_restored_tool_context=True,
            )
        )
    return Agent(
        model=get_model(),
        system_prompt=prompts.build_system_prompt(None),
        callback_handler=None,
        session_manager=session_manager,
        # The tools change one record, so they run one after another.
        tool_executor=SequentialToolExecutor(),
    )


def clean_name(name):
    """Return a person's name made safe to put in front of the model.

    A display name is text its owner chose. Line breaks and markup are removed
    and its length is limited, so it cannot pass for anything but a name.
    """
    if not isinstance(name, str):
        return UNKNOWN_SPEAKER
    name = re.sub(r"[\x00-\x1f\x7f]", " ", name)
    name = re.sub(r"[<>`\[\]]", "", name)
    name = re.sub(r"\s+", " ", name).strip()[:NAME_CHARS].strip()
    return name or UNKNOWN_SPEAKER


def _end_time(value):
    """Return when the thread stops being answered as (text, datetime), or (None, None)."""
    if not isinstance(value, str):
        return None, None
    try:
        when = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None, None
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    when = when.astimezone(datetime.timezone.utc)
    return when.strftime("%Y-%m-%d %H:%M"), when


def normalise(messages):
    """Make restored messages a sequence a model accepts, in place.

    With tool traffic left out, or after a request that failed part-way, two
    messages from the same side can be left running, or the conversation can
    begin with the model's words. Runs are joined into one message and leading
    model messages are dropped.
    """
    joined = []
    for message in messages:
        if joined and joined[-1]["role"] == message["role"]:
            joined[-1] = {"role": message["role"],
                          "content": list(joined[-1]["content"]) + list(message["content"])}
        elif joined or message["role"] == "user":
            joined.append(message)
    messages[:] = joined
    return messages


def _sync_tools(agent, tools, offered):
    """Make the agent's tool registry hold exactly the offered tools."""
    registry = agent.tool_registry
    for name in list(registry.registry):
        if name not in offered:
            registry.remove(name)
    for name in offered:
        if name in tools and name not in registry.registry:
            registry.register_tool(tools[name])


def _token_usage(result):
    usage = getattr(getattr(result, "metrics", None), "accumulated_usage", None) or {}
    return usage.get("inputTokens"), usage.get("outputTokens")


def _log_request(record, started):
    """Write the one log record for a request. Prompt and reply text are never logged."""
    record["durationMs"] = int((time.monotonic() - started) * 1000)
    logger.info(json.dumps(record))


def _answer(agent, payload, prompt, log, now):
    """Run one message through the agent. Return (kind, text, documents)."""
    speaker = clean_name(payload.get("speakerName"))
    conversation_type = payload.get("conversationType")
    if conversation_type != CHANNEL_THREAD:
        conversation_type = DIRECT_MESSAGE
    addressed = payload.get("addressed") is not False
    message_id = payload.get("messageId")
    message_id = message_id if isinstance(message_id, str) and message_id else None
    ends_text, ends_at = _end_time(payload.get("threadEndsAt"))
    if conversation_type != CHANNEL_THREAD:
        ends_text, ends_at = None, None

    state = agent.state
    rec.begin_message(state, message_id)
    session = rec.load(state)
    warn_end = False
    if session:
        session.next_turn()
        session.add_person(speaker)
        left = (ends_at - now).total_seconds() if ends_at else None
        if (session.in_progress and left is not None and 0 < left < END_WARNING_SECONDS
                and not session["endWarned"]):
            session.data["endWarned"] = True
            warn_end = True
        rec.save(state, session)
    quiet_allowed = bool(
        session and session.in_progress and conversation_type == CHANNEL_THREAD and not addressed
    )

    turn = Turn(state, speaker, conversation_type, ends_text, today=now.date().isoformat())

    def person_texts():
        """What people have written: this message, and theirs among those still in view."""
        texts = [prompt]
        for message in agent.messages:
            if message["role"] == "user":
                texts.extend(block["text"] for block in message["content"] if "text" in block)
        return texts

    repositories = Repositories(state, person_texts)
    tools = make_tools(turn, extra=repositories.tools())

    def before_model_call(event):
        current = rec.load(state)
        agent.system_prompt = prompts.build_system_prompt(
            current, rec.load_repositories(state), ends_text, warn_end
        )
        _sync_tools(agent, tools, tools_for(current))

    agent.hooks.add_callback(BeforeModelCallEvent, before_model_call)
    normalise(agent.messages)

    result = agent(prompts.user_message(prompt, speaker, quiet_allowed))
    text = str(result).strip()
    if prompts.is_quiet(text) and not quiet_allowed:
        result = agent(prompts.REPLY_REQUIRED_NUDGE)
        text = str(result).strip()
        if prompts.is_quiet(text):
            raise QuietWhenAReplyWasRequired()

    rec.end_message(state)
    manager = getattr(agent, "_session_manager", None)
    if manager is not None:
        manager.sync_agent(agent)

    current = rec.load(state)
    if current:
        log["skill"], log["stage"] = current["skill"], current["stage"]
    log["toolCalls"] = turn.tool_calls + repositories.tool_calls
    if repositories.repository:
        # The repository's name and a count may be logged. No path, and no content.
        log["repository"] = repositories.repository
        log["repositoryFilesRead"] = repositories.files_this_request
    log["documents"] = len(turn.documents)
    log["inputTokens"], log["outputTokens"] = _token_usage(result)

    if prompts.is_quiet(text):
        return "no_reply", "", []
    text = prompts.without_marker(text)
    if not text:
        raise QuietWhenAReplyWasRequired()
    return "answer", text, turn.documents


@app.entrypoint
def invoke(payload, context):
    started = time.monotonic()
    request_id = BedrockAgentCoreContext.get_request_id()
    session_id = getattr(context, "session_id", None)
    payload = payload if isinstance(payload, dict) else {}
    prompt = payload.get("prompt")
    prompt = prompt.strip() if isinstance(prompt, str) else ""
    actor_id = payload.get("actorId")
    actor_id = actor_id if isinstance(actor_id, str) and actor_id else DEFAULT_ACTOR_ID

    record = {
        "requestId": request_id,
        "sessionId": session_id,
        "promptChars": len(prompt),
    }

    if not prompt:
        record["kind"] = "input_rejection"
        _log_request(record, started)
        return {"kind": "input_rejection", "text": EMPTY_PROMPT_TEXT, "requestId": request_id}

    if len(prompt) > MAX_PROMPT_CHARS:
        record["kind"] = "input_rejection"
        _log_request(record, started)
        return {
            "kind": "input_rejection",
            "text": LONG_PROMPT_TEXT.format(limit=MAX_PROMPT_CHARS),
            "requestId": request_id,
        }

    record["modelId"] = MODEL_ID
    try:
        agent = build_agent(session_id, actor_id)
        now = datetime.datetime.now(datetime.timezone.utc)
        kind, text, documents = _answer(agent, payload, prompt, record, now)
    except Exception as error:  # Any failure becomes a generic reply; detail goes to the log.
        record["kind"] = "error"
        record["errorType"] = type(error).__name__
        _log_request(record, started)
        # The traceback names the place, not the words: no exception here carries what
        # a person wrote, and tools log their own faults by type alone.
        logger.exception("Request %s failed", request_id)
        return JSONResponse(
            {"kind": "error", "text": ERROR_TEXT, "requestId": request_id},
            status_code=500,
        )

    record["kind"] = kind
    _log_request(record, started)
    reply = {"kind": kind, "text": text, "requestId": request_id}
    if documents:
        reply["documents"] = documents
    return reply


if __name__ == "__main__":
    app.run()
