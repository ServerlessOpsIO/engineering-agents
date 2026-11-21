"""A scripted model for tests: it says what it is told to, and remembers what it was sent.

It is a real Strands model, so a test that uses it runs the framework's own loop:
hooks, the tool registry and the tools themselves.
"""

import json

from strands.models import Model


class FakeModel(Model):
    """Plays a script. Each step is a string (words) or a list of (tool name, arguments)."""

    def __init__(self, script=()):
        self.script = list(script)
        self.calls = []  # one per model call: {"system": str, "tools": [names], "messages": [...]}

    def update_config(self, **model_config):
        pass

    def get_config(self):
        return {"model_id": "fake"}

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        raise NotImplementedError
        yield  # pragma: no cover

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        self.calls.append({
            "system": system_prompt or "",
            "tools": [spec["name"] for spec in tool_specs or []],
            "messages": json.loads(json.dumps(messages)),
        })
        step = self.script.pop(0) if self.script else "The reply."
        if isinstance(step, Exception):
            raise step
        yield {"messageStart": {"role": "assistant"}}
        if isinstance(step, str):
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": step}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
        else:
            for number, (name, arguments) in enumerate(step):
                yield {"contentBlockStart": {"start": {"toolUse": {
                    "toolUseId": f"tool-{len(self.calls)}-{number}", "name": name}}}}
                yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(arguments)}}}}
                yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        yield {"metadata": {
            "usage": {"inputTokens": 11, "outputTokens": 7, "totalTokens": 18},
            "metrics": {"latencyMs": 1},
        }}
