"""Unit tests for the agent entry point. The model is replaced by a fake, so nothing calls AWS."""

import json
import logging
from types import SimpleNamespace

import pytest

import main


class FakeResult:
    def __init__(self, text):
        self.text = text
        self.metrics = SimpleNamespace(accumulated_usage={"inputTokens": 11, "outputTokens": 7})

    def __str__(self):
        return self.text


class FakeAgent:
    def __init__(self, reply="  The reply.  ", error=None):
        self.reply = reply
        self.error = error
        self.prompts = []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return FakeResult(self.reply)


@pytest.fixture
def context():
    return SimpleNamespace(session_id="session-0123456789-0123456789-0123456789")


@pytest.fixture
def agent(monkeypatch):
    fake = FakeAgent()
    monkeypatch.setattr(main, "build_agent", lambda session_id, actor_id: fake)
    return fake


@pytest.fixture
def records(monkeypatch):
    """Collect the JSON request records the entry point logs."""
    collected = []

    class Collector(logging.Handler):
        def emit(self, record):
            try:
                collected.append(json.loads(record.getMessage()))
            except ValueError:
                pass

    handler = Collector()
    main.logger.addHandler(handler)
    yield collected
    main.logger.removeHandler(handler)


def test_answers_a_prompt(agent, context, records):
    reply = main.invoke({"prompt": "  What can you do?  "}, context)

    assert reply["kind"] == "answer"
    assert reply["text"] == "The reply."
    assert "requestId" in reply
    assert agent.prompts == ["What can you do?"]

    assert len(records) == 1
    assert records[0]["kind"] == "answer"
    assert records[0]["sessionId"] == context.session_id
    assert records[0]["inputTokens"] == 11
    assert records[0]["outputTokens"] == 7
    assert isinstance(records[0]["durationMs"], int)


@pytest.mark.parametrize("payload", [{}, {"prompt": ""}, {"prompt": "   "}, {"prompt": 42}, None])
def test_rejects_an_empty_prompt_without_calling_the_model(payload, agent, context, records):
    reply = main.invoke(payload, context)

    assert reply["kind"] == "input_rejection"
    assert reply["text"] == main.EMPTY_PROMPT_TEXT
    assert agent.prompts == []
    assert records[0]["kind"] == "input_rejection"


def test_rejects_a_prompt_over_the_limit(agent, context):
    reply = main.invoke({"prompt": "x" * (main.MAX_PROMPT_CHARS + 1)}, context)

    assert reply["kind"] == "input_rejection"
    assert str(main.MAX_PROMPT_CHARS) in reply["text"]
    assert agent.prompts == []


def test_accepts_a_prompt_at_the_limit(agent, context):
    reply = main.invoke({"prompt": "x" * main.MAX_PROMPT_CHARS}, context)

    assert reply["kind"] == "answer"


def test_a_failure_returns_a_generic_error(monkeypatch, context, records):
    failing = FakeAgent(error=RuntimeError("secret internal detail"))
    monkeypatch.setattr(main, "build_agent", lambda session_id, actor_id: failing)

    response = main.invoke({"prompt": "hello"}, context)

    assert response.status_code == 500
    body = json.loads(response.body)
    assert body["kind"] == "error"
    assert body["text"] == main.ERROR_TEXT
    assert "secret internal detail" not in response.body.decode()
    assert records[0]["kind"] == "error"
    assert records[0]["errorType"] == "RuntimeError"


def test_the_request_record_holds_no_prompt_or_reply_text(agent, context, records):
    main.invoke({"prompt": "a very private question"}, context)

    logged = json.dumps(records)
    assert "a very private question" not in logged
    assert "The reply." not in logged
    assert records[0]["promptChars"] == len("a very private question")


def test_a_required_setting_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("SOME_SETTING", "value")

    assert main._require_env("SOME_SETTING") == "value"


@pytest.mark.parametrize("value", [None, ""])
def test_a_missing_required_setting_stops_the_agent(value, monkeypatch):
    if value is None:
        monkeypatch.delenv("SOME_SETTING", raising=False)
    else:
        monkeypatch.setenv("SOME_SETTING", value)

    with pytest.raises(RuntimeError, match="SOME_SETTING"):
        main._require_env("SOME_SETTING")
