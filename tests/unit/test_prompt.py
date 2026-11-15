"""Unit tests for the system prompt.

Add a test here for each rule the prompt must contain, so a rule cannot be
edited out without a test failing.
"""

import prompt


def test_the_system_prompt_is_not_empty():
    assert prompt.SYSTEM_PROMPT
