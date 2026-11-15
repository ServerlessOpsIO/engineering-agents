"""Agent entry point for Amazon Bedrock AgentCore Runtime.

Serves POST /invocations and GET /ping on port 8080 through BedrockAgentCoreApp.
The wire format is described in docs/handbook/04-architecture.md.
"""

import json
import logging
import os
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
from strands.models import BedrockModel

from prompt import SYSTEM_PROMPT


def _require_env(name):
    """Return a required environment variable, or stop the agent from starting."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"The {name} environment variable is not set.")
    return value


MODEL_ID = _require_env("MODEL_ID")
MAX_PROMPT_CHARS = int(os.environ.get("MAX_PROMPT_CHARS", "4000"))
MEMORY_ID = os.environ.get("MEMORY_ID")
DEFAULT_ACTOR_ID = "default"

EMPTY_PROMPT_TEXT = "Please send a prompt."
LONG_PROMPT_TEXT = "The prompt is too long. The limit is {limit} characters."
ERROR_TEXT = "The agent could not produce a reply. Try again later."

logger = logging.getLogger("agent")
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
    logger.propagate = False

app = BedrockAgentCoreApp()

_model = None


def get_model():
    """Create the model client on first use so importing this module calls nothing."""
    global _model
    if _model is None:
        _model = BedrockModel(model_id=MODEL_ID)
    return _model


def build_agent(session_id, actor_id):
    """Return an agent for one request.

    With MEMORY_ID set, the session's earlier messages are loaded from AgentCore
    Memory and this exchange is saved to it. Without it, the agent starts empty.
    """
    session_manager = None
    if MEMORY_ID and session_id:
        session_manager = AgentCoreMemorySessionManager(
            AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=session_id,
                actor_id=actor_id,
            )
        )
    return Agent(
        model=get_model(),
        system_prompt=SYSTEM_PROMPT,
        callback_handler=None,
        session_manager=session_manager,
    )


def _token_usage(result):
    usage = getattr(getattr(result, "metrics", None), "accumulated_usage", None) or {}
    return usage.get("inputTokens"), usage.get("outputTokens")


def _log_request(record, started):
    """Write the one log record for a request. Prompt and reply text are never logged."""
    record["durationMs"] = int((time.monotonic() - started) * 1000)
    logger.info(json.dumps(record))


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
        result = build_agent(session_id, actor_id)(prompt)
        text = str(result).strip()
    except Exception as error:  # Any failure becomes a generic reply; detail goes to the log.
        record["kind"] = "error"
        record["errorType"] = type(error).__name__
        _log_request(record, started)
        logger.exception("Request %s failed", request_id)
        return JSONResponse(
            {"kind": "error", "text": ERROR_TEXT, "requestId": request_id},
            status_code=500,
        )

    record["kind"] = "answer"
    record["inputTokens"], record["outputTokens"] = _token_usage(result)
    _log_request(record, started)
    return {"kind": "answer", "text": text, "requestId": request_id}


if __name__ == "__main__":
    app.run()
