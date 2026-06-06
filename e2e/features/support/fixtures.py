"""Helpers for creating module and marketplace structures on disk."""

import shutil
from pathlib import Path


def create_module_with_skill(base_dir: Path, name: str, skill_name: str) -> Path:
    """Create a minimal module directory with a single skill.

    Uses flat structure (no module/ subdir) so the directory name
    becomes the module name when registered with `lola mod add`.
    """
    module_dir = base_dir / name
    skill_dir = module_dir / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\ndescription: {skill_name} skill\n---\n\n# {skill_name}\n\nA test skill.\n",
        encoding="utf-8",
    )
    return module_dir


def create_module_full(base_dir: Path, name: str) -> Path:
    """Create a module directory with one skill, one command, and one agent.

    Uses flat structure (no module/ subdir) so the directory name
    becomes the module name when registered with `lola mod add`.
    """
    module_dir = base_dir / name

    skill_dir = module_dir / "skills" / "skill1"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: skill1 description\n---\n\n# Skill 1\n\nA test skill.\n",
        encoding="utf-8",
    )

    cmd_dir = module_dir / "commands"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "cmd1.md").write_text(
        "---\ndescription: cmd1 description\n---\n\n# Command 1\n\nA test command.\n",
        encoding="utf-8",
    )

    agent_dir = module_dir / "agents"
    agent_dir.mkdir(parents=True)
    (agent_dir / "agent1.md").write_text(
        "---\ndescription: agent1 description\n---\n\n# Agent 1\n\nA test agent.\n",
        encoding="utf-8",
    )

    return module_dir


def register_module(lola_home: Path, module_path: Path, name: str) -> Path:
    """Copy a module source directory into LOLA_HOME/modules/ to simulate registration."""
    modules_dir = lola_home / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)
    dest = modules_dir / name
    shutil.copytree(module_path, dest)
    return dest
