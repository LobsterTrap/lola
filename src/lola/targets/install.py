"""
Install orchestration functions for lola targets.

This module provides:
- Registry management (get_registry)
- Module copying (copy_module_to_local)
- Installation helpers for skills, commands, agents, instructions, MCPs
- The main install_to_assistant orchestration function
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 - required for running install hook scripts
from pathlib import Path
from typing import Optional, cast

from rich.console import Console

import lola.config as config
from lola.exceptions import InstallationError
from lola.models import Installation, InstallationKey, InstallationRegistry, Module
from lola.prompts import (
    is_interactive,
    prompt_agent_conflict,
    prompt_command_conflict,
    prompt_skill_conflict,
)

from .base import (
    AssistantTarget,
    _get_content_path,
    _get_skill_description,
    _skill_source_dir,
)

console = Console()


# =============================================================================
# Hook execution
# =============================================================================


def _run_install_hook(
    hook_type: str,
    script_path: str,
    module: Module,
    local_module_path: Path,
    project_path: str,
    assistant: str,
    scope: str,
) -> None:
    """Execute a pre-install or post-install hook script."""
    content_dirname = _get_content_dirname(module)
    content_path = _get_content_path(local_module_path, content_dirname)
    full_script_path = (content_path / script_path).resolve()

    if not full_script_path.exists():
        raise InstallationError(
            module.name,
            assistant,
            f"{hook_type} script not found: {script_path}",
        )

    try:
        full_script_path.relative_to(local_module_path.resolve())
    except ValueError:
        raise InstallationError(
            module.name,
            assistant,
            f"{hook_type} script outside module directory: {script_path}",
        )

    env = os.environ.copy()
    env.update(
        {
            "LOLA_MODULE_NAME": module.name,
            "LOLA_MODULE_PATH": str(local_module_path),
            "LOLA_PROJECT_PATH": project_path,
            "LOLA_ASSISTANT": assistant,
            "LOLA_SCOPE": scope,
            "LOLA_HOOK": hook_type,
        }
    )

    console.print(f"  [dim]Running {hook_type} script: {script_path}[/dim]")

    try:
        result = subprocess.run(  # nosec B603 B607 - list args (no shell), bash from PATH is intentional
            ["bash", str(full_script_path)],
            cwd=project_path,
            env=env,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise InstallationError(
                module.name,
                assistant,
                f"{hook_type} script failed (exit code {result.returncode})",
            )

    except subprocess.TimeoutExpired:
        raise InstallationError(
            module.name, assistant, f"{hook_type} script timed out after 5 minutes"
        )
    except FileNotFoundError:
        raise InstallationError(
            module.name,
            assistant,
            f"{hook_type} script is not executable: {script_path}",
        )


# =============================================================================
# Registry
# =============================================================================


def get_registry() -> InstallationRegistry:
    return InstallationRegistry(config.INSTALLED_FILE)


# =============================================================================
# Content directory helper
# =============================================================================


def _get_content_dirname(module: Module) -> Optional[str]:
    """Extract content subdirectory name from module.

    Returns:
        - None if content is at module root
        - Subdirectory name (e.g., "lola-module") if content is in subdirectory
    """
    if module.content_path == module.path:
        return None
    try:
        relative = module.content_path.relative_to(module.path)
        return str(relative)
    except ValueError:
        return None


# =============================================================================
# Install helpers
# =============================================================================


def copy_module_to_local(module: Module, local_modules_path: Path) -> Path:
    """Copy module to local .lola/modules directory."""
    dest = local_modules_path / module.name
    if dest.resolve() == module.path.resolve():
        return dest

    local_modules_path.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink() or dest.exists():
        if dest.is_symlink():
            dest.unlink()
        else:
            shutil.rmtree(dest)

    shutil.copytree(module.path, dest)
    return dest


def _check_skill_exists(
    target: AssistantTarget,
    skill_name: str,
    project_path: str | None,
    scope: str = "project",
) -> bool:
    """Check if a skill already exists at the destination."""
    if not project_path and scope == "project":
        return False

    skill_dest = target.get_skill_path(project_path or "", scope)

    if target.uses_managed_section:
        # For managed sections, we allow overwriting since skills are grouped by module
        return False
    else:
        # For file-based targets, check if directory/file exists
        if target.name == "cursor":
            return (skill_dest / f"{skill_name}.mdc").exists()
        else:
            return (skill_dest / skill_name).exists()


def _filter_selected(items: list[str], selected: set[str] | None) -> list[str]:
    """Apply a cherry-pick filter, preserving source order.

    ``selected is None`` means "install everything" (the historical default);
    any set (even empty) restricts to that subset.
    """
    if selected is None:
        return list(items)
    return [x for x in items if x in selected]


def _installed_name_for_source(
    source_name: str, installed_items: list[str], source_map: dict[str, str]
) -> str | None:
    """Return the installed name previously recorded for a source item."""
    for installed_name in installed_items:
        if source_map.get(installed_name, installed_name) == source_name:
            return installed_name
    return None


def _existing_installation(
    registry: InstallationRegistry,
    module_name: str,
    assistant: str,
    scope: str,
    project_path: str | None,
) -> Installation | None:
    """Find the exact installation currently being refreshed, if any."""
    key = InstallationKey(module_name, assistant, scope, project_path)
    return next(
        (
            inst
            for inst in registry.find(module_name)
            if InstallationKey.from_installation(inst) == key
        ),
        None,
    )


def _install_skills(
    target: AssistantTarget,
    module: Module,
    local_module_path: Path,
    project_path: str | None,
    scope: str = "project",
    force: bool = False,
    selected: set[str] | None = None,
    existing: Installation | None = None,
) -> tuple[list[str], list[str], dict[str, str]]:
    """Install skills for a target. Returns (installed, failed) lists."""
    skills_to_install = _filter_selected(module.skills, selected)
    if not skills_to_install:
        return [], [], {}

    installed: list[str] = []
    failed: list[str] = []
    source_map: dict[str, str] = {}

    # For user scope, project_path may be None
    path_context = project_path or ""
    skill_dest = target.get_skill_path(path_context, scope)

    content_dirname = _get_content_dirname(module)

    # Batch updates for managed section targets (Gemini, OpenCode)
    if target.uses_managed_section:
        batch_skills: list[tuple[str, str, Path]] = []
        for skill in skills_to_install:
            source = _skill_source_dir(local_module_path, skill, content_dirname)
            if source.exists():
                batch_skills.append((skill, _get_skill_description(source), source))
                installed.append(skill)
                source_map[skill] = skill
            else:
                failed.append(skill)
        if batch_skills:
            target.generate_skills_batch(
                skill_dest, module.name, batch_skills, project_path
            )
    else:
        overwrite_all = False
        prefix_all: str | None = None
        for skill in skills_to_install:
            source = _skill_source_dir(local_module_path, skill, content_dirname)
            existing_name = (
                _installed_name_for_source(
                    skill, existing.skills, existing.skill_sources
                )
                if existing
                else None
            )
            skill_name = existing_name or skill
            owns_existing = existing_name is not None

            if _check_skill_exists(target, skill_name, project_path, scope):
                if owns_existing or force or overwrite_all:
                    pass
                elif prefix_all is not None:
                    skill_name = f"{prefix_all}_{skill}"
                elif not is_interactive():
                    failed.append(skill)
                    continue
                else:
                    action, new_name = prompt_skill_conflict(skill, module.name)
                    if action == "skip":
                        console.print(f"  [yellow]Skipped {skill}[/yellow]")
                        continue
                    elif action == "rename":
                        skill_name = new_name
                    elif action == "prefix_all":
                        prefix_all = new_name  # user-chosen prefix
                        skill_name = f"{prefix_all}_{skill}"
                    elif action == "overwrite_all":
                        overwrite_all = True

            if target.generate_skill(source, skill_dest, skill_name, project_path):
                installed.append(skill_name)
                source_map[skill_name] = skill
            else:
                failed.append(skill)

    return installed, failed, source_map


def _install_commands(
    target: AssistantTarget,
    module: Module,
    local_module_path: Path,
    project_path: str | None,
    force: bool = False,
    scope: str = "project",
    selected: set[str] | None = None,
    existing: Installation | None = None,
) -> tuple[list[str], list[str], dict[str, str]]:
    """Install commands for a target. Returns (installed, failed) lists."""
    commands_to_install = _filter_selected(module.commands, selected)
    if not commands_to_install:
        return [], [], {}

    installed: list[str] = []
    failed: list[str] = []
    source_map: dict[str, str] = {}

    path_context = project_path or ""
    command_dest = target.get_command_path(path_context, scope)

    content_dirname = _get_content_dirname(module)
    content_path = _get_content_path(local_module_path, content_dirname)
    commands_dir = content_path / "commands"
    overwrite_all = False
    prefix_all: str | None = None
    for cmd in commands_to_install:
        source = commands_dir / f"{cmd}.md"
        existing_name = (
            _installed_name_for_source(cmd, existing.commands, existing.command_sources)
            if existing
            else None
        )
        effective_cmd = existing_name or cmd
        owns_existing = existing_name is not None

        dest_file = command_dest / target.get_command_filename(
            module.name, effective_cmd
        )
        if dest_file.exists() and not owns_existing and not force and not overwrite_all:
            if prefix_all is not None:
                effective_cmd = f"{prefix_all}-{cmd}"
            elif not is_interactive():
                failed.append(cmd)
                continue
            else:
                action, new_name = prompt_command_conflict(cmd, module.name)
                if action == "skip":
                    failed.append(cmd)
                    continue
                elif action == "rename":
                    effective_cmd = new_name
                elif action == "prefix_all":
                    prefix_all = new_name  # user-chosen prefix
                    effective_cmd = f"{prefix_all}-{cmd}"
                elif action == "overwrite_all":
                    overwrite_all = True

        if target.generate_command(source, command_dest, effective_cmd, module.name):
            installed.append(effective_cmd)
            source_map[effective_cmd] = cmd
        else:
            failed.append(cmd)

    return installed, failed, source_map


def _install_agents(
    target: AssistantTarget,
    module: Module,
    local_module_path: Path,
    project_path: str | None,
    force: bool = False,
    scope: str = "project",
    selected: set[str] | None = None,
    existing: Installation | None = None,
) -> tuple[list[str], list[str], dict[str, str]]:
    """Install agents for a target. Returns (installed, failed) lists."""
    if not target.supports_agents:
        return [], [], {}

    agents_to_install = _filter_selected(module.agents, selected)
    if not agents_to_install:
        return [], [], {}

    path_context = project_path or ""
    agent_dest = target.get_agent_path(path_context, scope)
    if not agent_dest:
        return [], [], {}

    installed: list[str] = []
    failed: list[str] = []
    source_map: dict[str, str] = {}

    content_dirname = _get_content_dirname(module)
    content_path = _get_content_path(local_module_path, content_dirname)
    agents_dir = content_path / "agents"
    overwrite_all = False
    prefix_all: str | None = None
    for agent in agents_to_install:
        source = agents_dir / f"{agent}.md"
        existing_name = (
            _installed_name_for_source(agent, existing.agents, existing.agent_sources)
            if existing
            else None
        )
        effective_agent = existing_name or agent
        owns_existing = existing_name is not None

        dest_file = agent_dest / target.get_agent_filename(module.name, effective_agent)
        if dest_file.exists() and not owns_existing and not force and not overwrite_all:
            if prefix_all is not None:
                effective_agent = f"{prefix_all}-{agent}"
            elif not is_interactive():
                failed.append(agent)
                continue
            else:
                action, new_name = prompt_agent_conflict(agent, module.name)
                if action == "skip":
                    failed.append(agent)
                    continue
                elif action == "rename":
                    effective_agent = new_name
                elif action == "prefix_all":
                    prefix_all = new_name  # user-chosen prefix
                    effective_agent = f"{prefix_all}-{agent}"
                elif action == "overwrite_all":
                    overwrite_all = True

        if target.generate_agent(source, agent_dest, effective_agent, module.name):
            installed.append(effective_agent)
            source_map[effective_agent] = agent
        else:
            failed.append(agent)

    return installed, failed, source_map


def _install_instructions(
    target: AssistantTarget,
    module: Module,
    local_module_path: Path,
    project_path: str | None,
    append_context: str | None = None,
    scope: str = "project",
) -> bool:
    """Install module instructions for a target. Returns True if installed."""
    from lola.models import INSTRUCTIONS_FILE

    if not module.has_instructions:
        return False

    if scope == "project" and not project_path:
        return False

    # Type checker: at this point project_path is guaranteed to be a string
    instructions_dest = target.get_instructions_path(cast(str, project_path), scope)

    # --append-context: insert a reference instead of verbatim copy
    if append_context:
        context_file = local_module_path / append_context
        if not context_file.exists():
            console.print(f"  [red]Context file not found: {append_context}[/red]")
            return False

        try:
            relative_path = context_file.resolve().relative_to(
                Path(cast(str, project_path)).resolve()
            )
        except ValueError:
            relative_path = context_file.resolve()

        reference = f"Read the module context from `{relative_path}`"
        return target.generate_instructions(reference, instructions_dest, module.name)

    # Default: verbatim copy of AGENTS.md
    if not module.has_instructions:
        return False

    content_dirname = _get_content_dirname(module)
    content_path = _get_content_path(local_module_path, content_dirname)
    instructions_source = content_path / INSTRUCTIONS_FILE
    if not instructions_source.exists():
        return False

    return target.generate_instructions(
        instructions_source, instructions_dest, module.name
    )


def _install_mcps(
    target: AssistantTarget,
    module: Module,
    local_module_path: Path,
    project_path: str | None,
    scope: str = "project",
    selected: set[str] | None = None,
) -> tuple[list[str], list[str], dict[str, str]]:
    """Install MCPs for a target. Returns (installed, failed) lists."""
    mcps_to_install = _filter_selected(module.mcps, selected)
    if not mcps_to_install:
        return [], [], {}

    path_context = project_path or ""
    mcp_dest = target.get_mcp_path(path_context, scope)
    if not mcp_dest:
        return [], [], {}

    content_dirname = _get_content_dirname(module)
    content_path = _get_content_path(local_module_path, content_dirname)
    mcps_file = content_path / config.MCPS_FILE
    if not mcps_file.exists():
        return [], mcps_to_install, {}

    try:
        mcps_data = json.loads(mcps_file.read_text())
        servers = mcps_data.get("mcpServers", {})
    except json.JSONDecodeError:
        return [], mcps_to_install, {}

    wanted = set(mcps_to_install)
    filtered_servers = {k: v for k, v in servers.items() if k in wanted}
    if not filtered_servers:
        return [], mcps_to_install, {}

    if target.generate_mcps(filtered_servers, mcp_dest, module.name):
        installed = list(filtered_servers.keys())
        return installed, [], {name: name for name in installed}

    return [], mcps_to_install, {}


def _print_summary(
    assistant: str,
    installed_skills: list[str],
    installed_commands: list[str],
    installed_agents: list[str],
    installed_mcps: list[str],
    has_instructions: bool,
    failed_skills: list[str],
    failed_commands: list[str],
    failed_agents: list[str],
    failed_mcps: list[str],
    module_name: str,
    verbose: bool,
) -> None:
    """Print installation summary."""
    if not (
        installed_skills
        or installed_commands
        or installed_agents
        or installed_mcps
        or has_instructions
    ):
        return

    parts: list[str] = []
    if installed_skills:
        parts.append(
            f"{len(installed_skills)} skill{'s' if len(installed_skills) != 1 else ''}"
        )
    if installed_commands:
        parts.append(
            f"{len(installed_commands)} command{'s' if len(installed_commands) != 1 else ''}"
        )
    if installed_agents:
        parts.append(
            f"{len(installed_agents)} agent{'s' if len(installed_agents) != 1 else ''}"
        )
    if installed_mcps:
        parts.append(
            f"{len(installed_mcps)} MCP{'s' if len(installed_mcps) != 1 else ''}"
        )
    if has_instructions:
        parts.append("instructions")

    console.print(f"  [green]{assistant}[/green] [dim]({', '.join(parts)})[/dim]")

    if verbose:
        for skill in installed_skills:
            console.print(f"    [green]{skill}[/green]")
        for cmd in installed_commands:
            console.print(f"    [green]/{cmd}[/green]")
        for agent in installed_agents:
            console.print(f"    [green]@{agent}[/green]")
        for mcp in installed_mcps:
            console.print(f"    [green]mcp:{mcp}[/green]")
        if has_instructions:
            console.print("    [green]instructions[/green]")

    if failed_skills or failed_commands or failed_agents or failed_mcps:
        for skill in failed_skills:
            console.print(f"    [red]{skill}[/red] [dim](source not found)[/dim]")
        for cmd in failed_commands:
            console.print(f"    [red]{cmd}[/red] [dim](source not found)[/dim]")
        for agent in failed_agents:
            console.print(f"    [red]{agent}[/red] [dim](source not found)[/dim]")
        for mcp in failed_mcps:
            console.print(f"    [red]{mcp}[/red] [dim](source not found)[/dim]")


def install_to_assistant(
    module: Module,
    assistant: str,
    scope: str,
    project_path: Optional[str],
    local_modules: Path,
    registry: InstallationRegistry,
    verbose: bool = False,
    force: bool = False,
    pre_install_script: Optional[str] = None,
    post_install_script: Optional[str] = None,
    append_context: Optional[str] = None,
    selected_skills: set[str] | None = None,
    selected_commands: set[str] | None = None,
    selected_agents: set[str] | None = None,
    selected_mcps: set[str] | None = None,
    selected_instructions: bool | None = None,
) -> int:
    """Install module to a specific assistant.

    When all ``selected_*`` arguments are ``None``, every item in the
    module is installed (the historical default). Passing any non-``None``
    value marks this as a cherry-picked install and stamps
    ``Installation.full_install = False`` so subsequent updates lock to the
    original selection. ``selected_instructions`` is a tristate:
    ``None`` (full install — install if module has instructions),
    ``True`` (cherry-pick: install instructions),
    ``False`` (cherry-pick: skip instructions).
    """
    # Late import to avoid circular imports - get_target is defined in __init__.py
    from lola.targets import get_target

    target = get_target(assistant)

    local_module_path = copy_module_to_local(module, local_modules)

    full_install = all(
        s is None
        for s in (
            selected_skills,
            selected_commands,
            selected_agents,
            selected_mcps,
            selected_instructions,
        )
    )

    if pre_install_script:
        try:
            _run_install_hook(
                "pre-install",
                pre_install_script,
                module,
                local_module_path,
                project_path or "",
                assistant,
                scope,
            )
        except InstallationError:
            if local_module_path.exists():
                shutil.rmtree(local_module_path)
            raise

    existing_installation = _existing_installation(
        registry, module.name, assistant, scope, project_path
    )

    installed_skills, failed_skills, skill_sources = _install_skills(
        target,
        module,
        local_module_path,
        project_path,
        scope,
        force,
        selected=selected_skills,
        existing=existing_installation,
    )
    installed_commands, failed_commands, command_sources = _install_commands(
        target,
        module,
        local_module_path,
        project_path,
        force,
        scope,
        selected=selected_commands,
        existing=existing_installation,
    )
    installed_agents, failed_agents, agent_sources = _install_agents(
        target,
        module,
        local_module_path,
        project_path,
        force,
        scope,
        selected=selected_agents,
        existing=existing_installation,
    )
    installed_mcps, failed_mcps, mcp_sources = _install_mcps(
        target,
        module,
        local_module_path,
        project_path,
        scope,
        selected=selected_mcps,
    )
    if selected_instructions is False:
        instructions_installed = False
    else:
        instructions_installed = _install_instructions(
            target, module, local_module_path, project_path, append_context, scope
        )

    _print_summary(
        assistant,
        installed_skills,
        installed_commands,
        installed_agents,
        installed_mcps,
        instructions_installed,
        failed_skills,
        failed_commands,
        failed_agents,
        failed_mcps,
        module.name,
        verbose,
    )

    if (
        installed_skills
        or installed_commands
        or installed_agents
        or installed_mcps
        or instructions_installed
    ):
        registry.upsert_installation(
            Installation(
                module_name=module.name,
                assistant=assistant,
                scope=scope,
                project_path=project_path,
                skills=installed_skills,
                commands=installed_commands,
                agents=installed_agents,
                mcps=installed_mcps,
                skill_sources=skill_sources,
                command_sources=command_sources,
                agent_sources=agent_sources,
                mcp_sources=mcp_sources,
                has_instructions=instructions_installed,
                append_context=append_context,
                full_install=full_install,
            ),
            cache_path=local_module_path,
        )

    if post_install_script:
        try:
            _run_install_hook(
                "post-install",
                post_install_script,
                module,
                local_module_path,
                project_path or "",
                assistant,
                scope,
            )
        except InstallationError as e:
            console.print("[yellow]Warning: post-install hook failed[/yellow]")
            console.print(f"[yellow]{e}[/yellow]")
            console.print(
                "[yellow]Installation completed but post-install hook failed[/yellow]"
            )

    return (
        len(installed_skills)
        + len(installed_commands)
        + len(installed_agents)
        + len(installed_mcps)
        + (1 if instructions_installed else 0)
    )


# =============================================================================
# Uninstall helpers
# =============================================================================


def _uninstall_skills(
    target: AssistantTarget,
    inst: Installation,
) -> tuple[list[str], list[str]]:
    """Uninstall skills for a target. Returns (removed, failed) lists."""
    if not inst.skills:
        return [], []

    removed: list[str] = []
    failed: list[str] = []

    path_context = inst.project_path or ""
    scope = inst.scope
    skill_dest = target.get_skill_path(path_context, scope)

    if target.uses_managed_section:
        if target.remove_skill(skill_dest, inst.module_name):
            return list(inst.skills), []
        return [], list(inst.skills)

    for skill in inst.skills:
        if target.remove_skill(skill_dest, skill):
            removed.append(skill)
        else:
            failed.append(skill)

    return removed, failed


def _uninstall_commands(
    target: AssistantTarget,
    inst: Installation,
) -> tuple[list[str], list[str]]:
    """Uninstall commands for a target. Returns (removed, failed) lists."""
    if not inst.commands:
        return [], []

    removed: list[str] = []
    failed: list[str] = []

    path_context = inst.project_path or ""
    scope = inst.scope
    command_dest = target.get_command_path(path_context, scope)

    for cmd in inst.commands:
        if target.remove_command(command_dest, cmd, inst.module_name):
            removed.append(cmd)
        else:
            failed.append(cmd)

    return removed, failed


def _uninstall_agents(
    target: AssistantTarget,
    inst: Installation,
) -> tuple[list[str], list[str]]:
    """Uninstall agents for a target. Returns (removed, failed) lists."""
    if not inst.agents or not target.supports_agents:
        return [], []

    path_context = inst.project_path or ""
    scope = inst.scope
    agent_dest = target.get_agent_path(path_context, scope)
    if not agent_dest:
        return [], []

    removed: list[str] = []
    failed: list[str] = []

    for agent in inst.agents:
        if target.remove_agent(agent_dest, agent, inst.module_name):
            removed.append(agent)
        else:
            failed.append(agent)

    return removed, failed


def _uninstall_instructions(
    target: AssistantTarget,
    inst: Installation,
) -> bool:
    """Uninstall module instructions for a target. Returns True if removed."""
    if not inst.has_instructions:
        return False

    path_context = inst.project_path or ""
    scope = inst.scope
    instructions_dest = target.get_instructions_path(path_context, scope)
    return target.remove_instructions(instructions_dest, inst.module_name)


def _uninstall_mcps(
    target: AssistantTarget,
    inst: Installation,
) -> tuple[list[str], list[str]]:
    """Uninstall MCPs for a target. Returns (removed, failed) lists."""
    if not inst.mcps:
        return [], []

    path_context = inst.project_path or ""
    scope = inst.scope
    mcp_dest = target.get_mcp_path(path_context, scope)
    if not mcp_dest:
        return [], []

    if target.remove_mcps(mcp_dest, inst.module_name, list(inst.mcps)):
        return list(inst.mcps), []

    return [], list(inst.mcps)


def _print_uninstall_summary(
    assistant: str,
    removed_skills: list[str],
    removed_commands: list[str],
    removed_agents: list[str],
    removed_mcps: list[str],
    had_instructions: bool,
    module_name: str,
    verbose: bool,
) -> None:
    """Print uninstall summary."""
    if not (
        removed_skills
        or removed_commands
        or removed_agents
        or removed_mcps
        or had_instructions
    ):
        return

    parts: list[str] = []
    if removed_skills:
        parts.append(
            f"{len(removed_skills)} skill{'s' if len(removed_skills) != 1 else ''}"
        )
    if removed_commands:
        parts.append(
            f"{len(removed_commands)} command{'s' if len(removed_commands) != 1 else ''}"
        )
    if removed_agents:
        parts.append(
            f"{len(removed_agents)} agent{'s' if len(removed_agents) != 1 else ''}"
        )
    if removed_mcps:
        parts.append(f"{len(removed_mcps)} MCP{'s' if len(removed_mcps) != 1 else ''}")
    if had_instructions:
        parts.append("instructions")

    console.print(f"  [green]{assistant}[/green] [dim]({', '.join(parts)})[/dim]")

    if verbose:
        for skill in removed_skills:
            console.print(f"    [dim]- {skill}[/dim]")
        for cmd in removed_commands:
            console.print(f"    [dim]- /{cmd}[/dim]")
        for agent in removed_agents:
            console.print(f"    [dim]- @{agent}[/dim]")
        for mcp in removed_mcps:
            console.print(f"    [dim]- mcp:{mcp}[/dim]")
        if had_instructions:
            console.print("    [dim]- instructions[/dim]")


def uninstall_assistant_outputs(inst: Installation, verbose: bool = False) -> int:
    """Remove assistant-owned files for one installation."""
    # Late import to avoid circular imports
    from lola.targets import get_target

    target = get_target(inst.assistant)

    removed_skills, _ = _uninstall_skills(target, inst)
    removed_commands, _ = _uninstall_commands(target, inst)
    removed_agents, _ = _uninstall_agents(target, inst)
    removed_mcps, _ = _uninstall_mcps(target, inst)
    instructions_removed = _uninstall_instructions(target, inst)

    _print_uninstall_summary(
        inst.assistant,
        removed_skills,
        removed_commands,
        removed_agents,
        removed_mcps,
        instructions_removed,
        inst.module_name,
        verbose,
    )

    return (
        len(removed_skills)
        + len(removed_commands)
        + len(removed_agents)
        + len(removed_mcps)
        + (1 if instructions_removed else 0)
    )


def uninstall_from_assistant(
    inst: Installation,
    registry: InstallationRegistry,
    verbose: bool = False,
    local_modules: Optional[Path] = None,
) -> int:
    """Compatibility wrapper for uninstalling one assistant installation."""
    removed = uninstall_assistant_outputs(inst, verbose)
    plan = registry.remove_installation(InstallationKey.from_installation(inst))

    # Older callers could pass an explicit local_modules path. Prefer the v2
    # registry plan, but honor the legacy argument when the registry has no
    # cache metadata for this installation.
    cache_paths = plan.cache_paths_to_remove
    if local_modules and not cache_paths:
        cache_paths = [local_modules / inst.module_name]
    for source_module in cache_paths:
        if source_module.is_symlink():
            source_module.unlink()
        elif source_module.exists():
            shutil.rmtree(source_module)

    return removed
