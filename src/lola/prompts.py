"""Interactive prompts for lola CLI.

Provides keyboard-navigable selection prompts for:
- Checking whether stdin is a real terminal (is_interactive)
- Selecting one or more AI assistants (multi-select checkbox)
- Selecting a single module from a list (single-select)
- Selecting a marketplace by name from a list (single-select)
- Selecting a marketplace when a module name conflicts across several (single-select)
- Handling command/agent file conflicts during installation

All functions return None / [] when the user cancels, so callers can raise
SystemExit(130) to signal a user-initiated cancellation.
"""

from __future__ import annotations

import sys

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.validator import EmptyInputValidator


def is_interactive() -> bool:
    """Return True when stdin is connected to a real TTY (not piped or CI)."""
    return sys.stdin.isatty()


def select_assistants(available: list[str]) -> list[str]:
    """
    Show a multi-select checkbox for AI assistants.

    If only one assistant is available it is returned immediately without
    prompting.  Returns a (possibly empty) list of selected assistant names;
    an empty list means the user cancelled or deselected everything.
    """
    if len(available) == 1:
        return list(available)

    result = inquirer.checkbox(
        message="Select assistants to install to (Space to toggle, Enter to confirm):",
        choices=available,
    ).execute()
    return result if result is not None else []


def select_module(modules: list[str]) -> str | None:
    """
    Show a single-select list for choosing a module.

    If only one module is available it is returned immediately without
    prompting.  Returns the selected module name, or None if cancelled.
    """
    if len(modules) == 1:
        return modules[0]

    result = inquirer.select(
        message="Select module:",
        choices=modules,
    ).execute()
    return str(result) if result is not None else None


def select_marketplace_name(names: list[str]) -> str | None:
    """
    Show a single-select list for choosing a marketplace by name.

    Always prompts, even when only one marketplace is registered, so the user
    must explicitly confirm before a destructive action proceeds.
    Returns the selected marketplace name, or None if cancelled.
    """
    result = inquirer.select(
        message="Select marketplace:",
        choices=names,
    ).execute()
    return str(result) if result is not None else None


def select_install_mode() -> str | None:
    """
    Ask whether to install every module item or cherry-pick specific items.

    Returns "all", "cherry-pick", or None if cancelled.
    """
    result = inquirer.select(
        message="Install module items:",
        choices=[
            Choice(value="all", name="Install all"),
            Choice(value="cherry-pick", name="Choose items"),
        ],
    ).execute()
    return str(result) if result is not None else None


def select_module_items(
    skills: list[str],
    commands: list[str],
    agents: list[str],
    mcps: list[str],
    current: dict[str, list[str]] | None = None,
    has_instructions: bool = False,
) -> dict[str, list[str]] | None:
    """
    Show a fuzzy-searchable multi-select picker for cherry-picking module items.

    Items are listed with type prefixes (skill:, cmd:, agent:, mcp:) so a
    single picker covers every category at once. Type to fuzzy-search; Tab
    toggles an item. We rely on InquirerPy's built-in shortcuts: Alt-A /
    Ctrl-A select all, Alt-R / Ctrl-R invert. Enter confirms. (InquirerPy's
    fuzzy picker has no working deselect-all — its ``toggle-all-false``
    action is broken upstream — so we lean on "pre-select everything, then
    invert" to achieve clear-the-list.)

    When ``has_instructions`` is True, a single ``instructions: AGENTS.md``
    entry is appended.

    When ``current`` is provided (dict keyed by "skills"/"commands"/"agents"/
    "mcps"/"instructions"), items already in that set are suffixed
    " (installed)" and pre-selected, while items not in it are suffixed
    " (new)" and start deselected. When ``current`` is None (a fresh install),
    every entry starts pre-selected so confirming installs everything by
    default — use Ctrl-R to invert (clears the list on a fresh install).

    Returns a dict with keys "skills", "commands", "agents", "mcps",
    "instructions", or None if the user cancelled. The "instructions" value
    is ``["yes"]`` when selected and ``[]`` otherwise.
    """
    current_sets: dict[str, set[str]] = {
        "skills": set((current or {}).get("skills", [])),
        "commands": set((current or {}).get("commands", [])),
        "agents": set((current or {}).get("agents", [])),
        "mcps": set((current or {}).get("mcps", [])),
        "instructions": set((current or {}).get("instructions", [])),
    }

    def _make_choice(value: str, label: str, kind: str, name: str) -> Choice:
        if current is None:
            # Fresh install: pre-select everything so Enter installs all by
            # default; the picker becomes a tool for deselecting unwanted
            # items rather than building up a selection from scratch.
            return Choice(value=value, name=label, enabled=True)
        installed = name in current_sets[kind]
        suffix = " (installed)" if installed else " (new)"
        return Choice(value=value, name=label + suffix, enabled=installed)

    choices: list[Choice] = []
    for s in skills:
        choices.append(_make_choice(f"skill:{s}", f"skill: {s}", "skills", s))
    for c in commands:
        choices.append(_make_choice(f"cmd:{c}", f"cmd: /{c}", "commands", c))
    for a in agents:
        choices.append(_make_choice(f"agent:{a}", f"agent: @{a}", "agents", a))
    for m in mcps:
        choices.append(_make_choice(f"mcp:{m}", f"mcp: {m}", "mcps", m))
    if has_instructions:
        choices.append(
            _make_choice(
                "instructions:", "instructions: AGENTS.md", "instructions", "yes"
            )
        )

    # Surface the most-useful shortcuts inline at the top so users discover
    # them without having to read the bottom help line. Keep this short so
    # it fits on one line in typical terminal widths.
    instruction = "(^A all · ^R invert · Tab toggle)"
    long_instruction = "Type to fuzzy-search. Tab toggles; Enter confirms."

    # Rely on InquirerPy's defaults: Alt-A/Ctrl-A select-all,
    # Alt-R/Ctrl-R invert. No deselect-all binding — fuzzy's
    # toggle-all-false handler is broken upstream (treats `False` as
    # falsy and inverts instead of clearing).
    result = inquirer.fuzzy(
        message="Select items to install:",
        instruction=instruction,
        long_instruction=long_instruction,
        choices=choices,
        multiselect=True,
        border=True,
    ).execute()
    if result is None:
        return None

    selected: dict[str, list[str]] = {
        "skills": [],
        "commands": [],
        "agents": [],
        "mcps": [],
        "instructions": [],
    }
    for value in result:
        kind, _, name = value.partition(":")
        if kind == "skill":
            selected["skills"].append(name)
        elif kind == "cmd":
            selected["commands"].append(name)
        elif kind == "agent":
            selected["agents"].append(name)
        elif kind == "mcp":
            selected["mcps"].append(name)
        elif kind == "instructions":
            selected["instructions"].append("yes")
    return selected


def select_installations(
    installations: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """
    Show a multi-select checkbox for (project_path, assistant, label) tuples.

    Returns the selected installations; an empty list means the user cancelled
    or deselected everything.
    """
    choices = [
        Choice(value=(project, assistant, label), name=label)
        for project, assistant, label in installations
    ]
    result = inquirer.checkbox(
        message="Select installations to uninstall (Space to toggle, Enter to confirm):",
        choices=choices,
    ).execute()
    return result if result is not None else []


def select_marketplace(matches: list[tuple[dict, str]]) -> str | None:
    """
    Show a single-select list for marketplace conflict resolution.

    matches: list of (module_dict, marketplace_name) tuples.
    Returns the chosen marketplace name, or None if cancelled.
    """
    choices = [
        Choice(
            value=marketplace_name,
            name=(
                f"@{marketplace_name}/{module.get('name', '?')} "
                f"v{module.get('version', '?')} — {module.get('description', '')}"
            ),
        )
        for module, marketplace_name in matches
    ]
    result = inquirer.select(
        message="Module found in multiple marketplaces. Select one:",
        choices=choices,
    ).execute()
    return str(result) if result is not None else None


def _prompt_conflict(
    kind: str, name: str, module_name: str, rename_sep: str
) -> tuple[str, str]:
    """Prompt when a file already exists during install.

    Returns one of:
        ("overwrite_all", "")        — overwrite this and every subsequent
                                       collision
        ("prefix_all",    "prefix")  — apply ``f"{prefix}{sep}{name}"`` to this
                                       and every subsequent collision; the
                                       caller knows ``sep`` for its kind
        ("overwrite",     "")        — replace existing file
        ("rename",        "new")     — install under ``new``
        ("skip",          "")        — do not install
    """
    action = inquirer.select(
        message=f"'{name}' ({kind}) already exists. What would you like to do?",
        choices=[
            Choice("overwrite_all", name="Overwrite All"),
            Choice("prefix_all", name="Prefix All"),
            Choice("overwrite", name="Overwrite"),
            Choice("rename", name=f"Rename {kind}"),
            Choice("skip", name="Skip"),
        ],
    ).execute()
    if action == "rename":
        new_name = inquirer.text(
            message=f"New {kind} name:",
            default=f"{module_name}{rename_sep}{name}",
            validate=EmptyInputValidator(),
        ).execute()
        return "rename", str(new_name)
    if action == "prefix_all":
        prefix = inquirer.text(
            message=f"Prefix for all conflicting {kind}s (joined with '{rename_sep}'):",
            default=module_name,
            validate=EmptyInputValidator(),
        ).execute()
        return "prefix_all", str(prefix)
    return str(action) if action is not None else "skip", ""


def prompt_command_conflict(cmd_name: str, module_name: str) -> tuple[str, str]:
    """Prompt when a command file already exists. See ``_prompt_conflict``."""
    return _prompt_conflict("command", cmd_name, module_name, rename_sep="-")


def prompt_agent_conflict(agent_name: str, module_name: str) -> tuple[str, str]:
    """Prompt when an agent file already exists. See ``_prompt_conflict``."""
    return _prompt_conflict("agent", agent_name, module_name, rename_sep="-")


def prompt_skill_conflict(skill_name: str, module_name: str) -> tuple[str, str]:
    """Prompt when a skill directory already exists. See ``_prompt_conflict``.

    Defaults the rename to ``f"{module_name}_{skill_name}"`` to match the
    historical prefix convention for skills.
    """
    return _prompt_conflict("skill", skill_name, module_name, rename_sep="_")
