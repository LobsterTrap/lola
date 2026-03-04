"""Interactive prompts for lola CLI."""

from __future__ import annotations

import sys

from InquirerPy import inquirer  # type: ignore[import-untyped]
from InquirerPy.base.control import Choice  # type: ignore[import-untyped]
from InquirerPy.validator import EmptyInputValidator  # type: ignore[import-untyped]


def is_interactive() -> bool:
    """Return True if stdin is an interactive terminal."""
    return sys.stdin.isatty()


def prompt_command_conflict(cmd_name: str, module_name: str) -> tuple[str, str]:
    """Prompt when a command file already exists.

    Returns:
        ("overwrite", "")         — replace existing file
        ("rename",    "new_name") — install under new_name
        ("skip",      "")         — do not install
    """
    action = inquirer.select(
        message=f"'{cmd_name}' already exists. What would you like to do?",
        choices=[
            Choice("overwrite", name="Overwrite"),
            Choice("rename", name="Rename command"),
            Choice("skip", name="Skip"),
        ],
    ).execute()
    if action == "rename":
        new_name = inquirer.text(
            message="New command name:",
            default=f"{module_name}-{cmd_name}",
            validate=EmptyInputValidator(),
        ).execute()
        return "rename", str(new_name)
    return str(action) if action is not None else "skip", ""


def prompt_agent_conflict(agent_name: str, module_name: str) -> tuple[str, str]:
    """Prompt when an agent file already exists.

    Returns:
        ("overwrite", "")         — replace existing file
        ("rename",    "new_name") — install under new_name
        ("skip",      "")         — do not install
    """
    action = inquirer.select(
        message=f"'{agent_name}' already exists. What would you like to do?",
        choices=[
            Choice("overwrite", name="Overwrite"),
            Choice("rename", name="Rename agent"),
            Choice("skip", name="Skip"),
        ],
    ).execute()
    if action == "rename":
        new_name = inquirer.text(
            message="New agent name:",
            default=f"{module_name}-{agent_name}",
            validate=EmptyInputValidator(),
        ).execute()
        return "rename", str(new_name)
    return str(action) if action is not None else "skip", ""
