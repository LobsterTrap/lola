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

import click
from rich.console import Console

import lola.config as config
from lola.exceptions import InstallationError
from lola.models import Installation, InstallationRegistry, Module
from lola.prompts import is_interactive, prompt_agent_conflict, prompt_command_conflict

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


def _install_skills(
    target: AssistantTarget,
    module: Module,
    local_module_path: Path,
    project_path: str | None,
    scope: str = "project",
    force: bool = False,
    selected: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Install skills for a target. Returns (installed, failed) lists."""
    skills_to_install = _filter_selected(module.skills, selected)
    if not skills_to_install:
        return [], []

    installed: list[str] = []
    failed: list[str] = []

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
            else:
                failed.append(skill)
        if batch_skills:
            target.generate_skills_batch(
                skill_dest, module.name, batch_skills, project_path
            )
    else:
        for skill in skills_to_install:
            source = _skill_source_dir(local_module_path, skill, content_dirname)
            skill_name = skill  # Use unprefixed name by default

            # Check if skill already exists
            if _check_skill_exists(target, skill_name, project_path, scope):
                if force:
                    # Force mode: overwrite without prompting
                    pass
                elif click.confirm(
                    f"Skill '{skill_name}' already exists. Overwrite?", default=False
                ):
                    # User chose to overwrite
                    pass
                elif click.confirm(
                    f"Use prefixed name '{module.name}_{skill}' instead?", default=True
                ):
                    # User chose to use prefixed name
                    skill_name = f"{module.name}_{skill}"
                else:
                    # User declined both options, skip this skill
                    console.print(f"  [yellow]Skipped {skill}[/yellow]")
                    continue

            if target.generate_skill(source, skill_dest, skill_name, project_path):
                installed.append(skill_name)
            else:
                failed.append(skill)

    return installed, failed


def _install_commands(
    target: AssistantTarget,
    module: Module,
    local_module_path: Path,
    project_path: str | None,
    force: bool = False,
    scope: str = "project",
    selected: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Install commands for a target. Returns (installed, failed) lists."""
    commands_to_install = _filter_selected(module.commands, selected)
    if not commands_to_install:
        return [], []

    installed: list[str] = []
    failed: list[str] = []

    path_context = project_path or ""
    command_dest = target.get_command_path(path_context, scope)

    content_dirname = _get_content_dirname(module)
    content_path = _get_content_path(local_module_path, content_dirname)
    commands_dir = content_path / "commands"
    for cmd in commands_to_install:
        source = commands_dir / f"{cmd}.md"
        effective_cmd = cmd

        dest_file = command_dest / target.get_command_filename(module.name, cmd)
        if dest_file.exists() and not force:
            if not is_interactive():
                failed.append(cmd)
                continue
            action, new_name = prompt_command_conflict(cmd, module.name)
            if action == "skip":
                failed.append(cmd)
                continue
            elif action == "rename":
                effective_cmd = new_name

        if target.generate_command(source, command_dest, effective_cmd, module.name):
            installed.append(effective_cmd)
        else:
            failed.append(cmd)

    return installed, failed


def _install_agents(
    target: AssistantTarget,
    module: Module,
    local_module_path: Path,
    project_path: str | None,
    force: bool = False,
    scope: str = "project",
    selected: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Install agents for a target. Returns (installed, failed) lists."""
    if not target.supports_agents:
        return [], []

    agents_to_install = _filter_selected(module.agents, selected)
    if not agents_to_install:
        return [], []

    path_context = project_path or ""
    agent_dest = target.get_agent_path(path_context, scope)
    if not agent_dest:
        return [], []

    installed: list[str] = []
    failed: list[str] = []

    content_dirname = _get_content_dirname(module)
    content_path = _get_content_path(local_module_path, content_dirname)
    agents_dir = content_path / "agents"
    for agent in agents_to_install:
        source = agents_dir / f"{agent}.md"
        effective_agent = agent

        dest_file = agent_dest / target.get_agent_filename(module.name, agent)
        if dest_file.exists() and not force:
            if not is_interactive():
                failed.append(agent)
                continue
            action, new_name = prompt_agent_conflict(agent, module.name)
            if action == "skip":
                failed.append(agent)
                continue
            elif action == "rename":
                effective_agent = new_name

        if target.generate_agent(source, agent_dest, effective_agent, module.name):
            installed.append(effective_agent)
        else:
            failed.append(agent)

    return installed, failed


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
) -> tuple[list[str], list[str]]:
    """Install MCPs for a target. Returns (installed, failed) lists."""
    mcps_to_install = _filter_selected(module.mcps, selected)
    if not mcps_to_install:
        return [], []

    path_context = project_path or ""
    mcp_dest = target.get_mcp_path(path_context, scope)
    if not mcp_dest:
        return [], []

    content_dirname = _get_content_dirname(module)
    content_path = _get_content_path(local_module_path, content_dirname)
    mcps_file = content_path / config.MCPS_FILE
    if not mcps_file.exists():
        return [], mcps_to_install

    try:
        mcps_data = json.loads(mcps_file.read_text())
        servers = mcps_data.get("mcpServers", {})
    except json.JSONDecodeError:
        return [], mcps_to_install

    wanted = set(mcps_to_install)
    filtered_servers = {k: v for k, v in servers.items() if k in wanted}
    if not filtered_servers:
        return [], mcps_to_install

    if target.generate_mcps(filtered_servers, mcp_dest, module.name):
        return list(filtered_servers.keys()), []

    return [], mcps_to_install


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
) -> int:
    """Install module to a specific assistant.

    When all four ``selected_*`` arguments are ``None``, every item in the
    module is installed (the historical default). Passing any non-``None``
    set marks this as a cherry-picked install and stamps
    ``Installation.full_install = False`` so subsequent updates lock to the
    original selection.
    """
    # Late import to avoid circular imports - get_target is defined in __init__.py
    from lola.targets import get_target

    target = get_target(assistant)

    local_module_path = copy_module_to_local(module, local_modules)

    full_install = all(
        s is None
        for s in (selected_skills, selected_commands, selected_agents, selected_mcps)
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

    installed_skills, failed_skills = _install_skills(
        target,
        module,
        local_module_path,
        project_path,
        scope,
        force,
        selected=selected_skills,
    )
    installed_commands, failed_commands = _install_commands(
        target,
        module,
        local_module_path,
        project_path,
        force,
        scope,
        selected=selected_commands,
    )
    installed_agents, failed_agents = _install_agents(
        target,
        module,
        local_module_path,
        project_path,
        force,
        scope,
        selected=selected_agents,
    )
    installed_mcps, failed_mcps = _install_mcps(
        target,
        module,
        local_module_path,
        project_path,
        scope,
        selected=selected_mcps,
    )
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
        registry.add(
            Installation(
                module_name=module.name,
                assistant=assistant,
                scope=scope,
                project_path=project_path,
                skills=installed_skills,
                commands=installed_commands,
                agents=installed_agents,
                mcps=installed_mcps,
                has_instructions=instructions_installed,
                append_context=append_context,
                full_install=full_install,
            )
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


def uninstall_from_assistant(
    inst: Installation,
    registry: InstallationRegistry,
    verbose: bool = False,
    local_modules: Optional[Path] = None,
) -> int:
    """Uninstall module from a specific assistant.

    Args:
        inst: Installation record describing what to remove
        registry: Registry to remove installation from
        verbose: Print detailed output
        local_modules: Optional path to local modules directory for cleanup

    Returns:
        Count of items removed
    """
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

    # Clean up local module copy if requested
    if local_modules:
        source_module = local_modules / inst.module_name
        if source_module.is_symlink():
            source_module.unlink()
        elif source_module.exists():
            shutil.rmtree(source_module)

    # Remove from registry
    registry.remove(inst.module_name, inst.assistant)

    return (
        len(removed_skills)
        + len(removed_commands)
        + len(removed_agents)
        + len(removed_mcps)
        + (1 if instructions_removed else 0)
    )
