"""The agent's system prompt.

The text lives in system_prompt.md, next to this file, so it can be edited and
reviewed as prose. It is read once when the agent starts.
"""

from pathlib import Path

SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md").read_text(encoding="utf-8").strip()
