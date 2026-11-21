"""What the model is told, built afresh before every call to it.

There are two kinds of instruction, kept apart (FR-001). The persona, in
persona.md, says who STRIDEr is, how it speaks and the rules that always hold.
A skill, under skills/, says how to carry out one kind of task.

The order matters: the model follows best what comes last, so the record comes
first and the persona's rules last (research.md, Decision 3).
"""

from pathlib import Path

import loader
from session.summary import summarise

PERSONA = (Path(__file__).parent / "persona.md").read_text(encoding="utf-8").strip()

QUIET_MARKER = "[[quiet]]"
MAY_STAY_QUIET = "[You may stay quiet]"
REPLY_REQUIRED = "[A reply is required]"
REPLY_REQUIRED_NUDGE = "A reply is required."


def _skills_section(skills):
    lines = [
        "# AVAILABLE SKILLS",
        "",
        "Each skill is taken up only when the task calls for it. To take one up, use the "
        "`start_session` tool; its instructions are then given to you.",
        "",
    ]
    lines.extend(f"- **{skill.name}**: {skill.description}" for skill in skills.values())
    return "\n".join(lines)


def build_system_prompt(record, repositories=None, thread_ends_at=None, warn_end=False, skills=None):
    """Return the system prompt for the record as it stands.

    A pure function of its arguments, so that it can be called before every
    model call and always match the record.
    """
    skills = loader.SKILLS if skills is None else skills
    parts = ["# SESSION RECORD\n\n" + summarise(record, repositories, thread_ends_at, warn_end)]
    skill = skills.get(record["skill"]) if record else None
    if skill:
        parts.append(f"# SKILL: {skill.name}\n\n{skill.instructions}")
        if record["stage"] in skill.stages:
            parts.append(f"# CURRENT STAGE: {record['stage']}\n\n{skill.reference(record['stage'])}")
    parts.append(_skills_section(skills))
    parts.append("# PERSONA\n\n" + PERSONA)
    return "\n\n".join(parts)


def user_message(prompt, speaker_name, quiet_allowed):
    """Return the message as the model is given it: who wrote it, and whether a reply is needed."""
    marker = MAY_STAY_QUIET if quiet_allowed else REPLY_REQUIRED
    return f"[From: {speaker_name}] {marker}\n{prompt}"


def is_quiet(text):
    """Say whether a reply is the quiet marker and nothing else."""
    return text.strip() == QUIET_MARKER


def without_marker(text):
    """Return a reply with the quiet marker taken out."""
    return text.replace(QUIET_MARKER, "").strip()
