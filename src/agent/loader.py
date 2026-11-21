"""Reads the agent's skills.

A skill is a folder under skills/ in the published Agent Skills format: a
SKILL.md with front matter and instructions, one reference file for each stage
it names, and a SOURCE.md saying where it came from and under what licence.

Skills are read once, when the agent starts, and the agent does not start with
a skill that is malformed. Nothing is fetched: a skill is whatever is in the
image.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from strands.vended_plugins.skills import Skill

SKILLS_DIR = Path(__file__).parent / "skills"

_LICENCE = re.compile(r"^\s*(?:[-*]\s*)?\**licen[cs]e\**\s*:\s*\S+", re.IGNORECASE | re.MULTILINE)


class SkillError(Exception):
    """A skill cannot be used as it is."""


@dataclass(frozen=True)
class LoadedSkill:
    name: str
    description: str
    instructions: str
    allowed_tools: tuple
    stages: tuple
    path: Path

    def reference(self, stage):
        """Return the reference text for one stage."""
        return (self.path / "references" / f"{stage}.md").read_text(encoding="utf-8").strip()


def _load(folder):
    try:
        skill = Skill.from_file(folder, strict=True)
    except (ValueError, FileNotFoundError) as error:
        raise SkillError(f"{folder.name}: {error}") from error
    if not (skill.instructions or "").strip():
        raise SkillError(f"{folder.name}: SKILL.md has no instructions")

    stages = tuple(str(skill.metadata.get("stages") or "").split())
    for stage in stages:
        if not (folder / "references" / f"{stage}.md").is_file():
            raise SkillError(f"{folder.name}: no references/{stage}.md for the stage '{stage}'")

    source = folder / "SOURCE.md"
    if not source.is_file():
        raise SkillError(f"{folder.name}: no SOURCE.md saying where the skill came from")
    if not _LICENCE.search(source.read_text(encoding="utf-8")):
        raise SkillError(f"{folder.name}: SOURCE.md names no licence (a line 'Licence: …')")

    return LoadedSkill(
        name=skill.name,
        description=" ".join(skill.description.split()),
        instructions=skill.instructions.strip(),
        allowed_tools=tuple(skill.allowed_tools or ()),
        stages=stages,
        path=folder,
    )


def load_skills(directory=SKILLS_DIR):
    """Return every skill in the directory, by name. Raises SkillError for a bad one."""
    directory = Path(directory)
    skills = {}
    for folder in sorted(p for p in directory.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        skill = _load(folder)
        skills[skill.name] = skill
    return skills


SKILLS = load_skills()
