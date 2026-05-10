"""
Install CLI commands.

Commands for installing, uninstalling, updating, and listing module installations.
"""

from dataclasses import dataclass, field
import shutil
from pathlib import Path
from typing import Any, Optional

import click
from rich.console import Console

from lola.cli.completions import complete_module_names, complete_installed_module_names
from lola.config import MODULES_DIR, MARKET_DIR, CACHE_DIR
from lola.exceptions import (
    ModuleInvalidError,
    ModuleNotFoundError,
    PathNotFoundError,
    ValidationError,
)
from lola.models import Installation, InstallationRegistry, Module
from lola.market.manager import parse_market_ref, MarketplaceRegistry
from lola.parsers import fetch_module_as_name, detect_source_type
from lola.cli.mod import (
    save_source_info,
    load_registered_module,
    list_registered_modules,
)
from lola.prompts import (
    is_interactive,
    select_assistants,
    select_installations,
    select_module,
    select_module_items,
)
from lola.targets import (
    AssistantTarget,
    OpenClawTarget,
    TARGETS,
    _get_content_path,
    _get_skill_description,
    _skill_source_dir,
    copy_module_to_local,
    get_registry,
    get_target,
    install_to_assistant,
)
from lola.utils import ensure_lola_dirs, get_local_modules_path
from lola.cli.utils import handle_lola_error

console = Console()


def _expand_csv(values: tuple[str, ...]) -> list[str]:
    """Expand a click multiple=True tuple, splitting any comma-separated values.

    ``--skill foo,bar --skill baz`` and ``--skill foo --skill bar --skill baz``
    are both flattened to ``["foo", "bar", "baz"]``. Whitespace and empty
    entries are dropped.
    """
    out: list[str] = []
    for v in values:
        for part in v.split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def _resolve_install_path(
    assistant: Optional[str],
    project_path: str,
    workspace: Optional[str],
) -> str:
    """Resolve the effective install path for an assistant.

    For openclaw, overrides project_path with the configured workspace.
    Raises UsageError if --workspace is used with a non-openclaw assistant.
    """
    if workspace and assistant != "openclaw":
        raise click.UsageError("--workspace is only valid with -a openclaw")
    if assistant == "openclaw":
        return str(OpenClawTarget.resolve_workspace(workspace))
    return project_path


def _fetch_from_marketplace(
    marketplace_name: str, module_name: str
) -> tuple[Path, dict]:
    """
    Fetch module from specified marketplace.

    Args:
        marketplace_name: Name of the marketplace
        module_name: Name of the module

    Returns:
        Tuple of (module_path, module_metadata) where module_metadata
        is the marketplace module dict (may contain hooks)

    Raises:
        SystemExit: If marketplace/module not found or fetch fails
    """
    from lola.models import Marketplace

    ref_file = MARKET_DIR / f"{marketplace_name}.yml"

    if not ref_file.exists():
        console.print(f"[red]Marketplace '{marketplace_name}' not found[/red]")
        console.print("[dim]Use 'lola market ls' to see available marketplaces[/dim]")
        raise SystemExit(1)

    # Check if marketplace is enabled FIRST
    marketplace_ref = Marketplace.from_reference(ref_file)
    if not marketplace_ref.enabled:
        console.print(f"[red]Marketplace '{marketplace_name}' is disabled[/red]")
        raise SystemExit(1)

    # Now load cache and look up module
    cache_file = CACHE_DIR / f"{marketplace_name}.yml"
    if not cache_file.exists():
        console.print(f"[red]Marketplace '{marketplace_name}' cache not found[/red]")
        console.print(f"[dim]Try 'lola market update {marketplace_name}'[/dim]")
        raise SystemExit(1)

    marketplace = Marketplace.from_cache(cache_file)

    # Look up module directly
    module_dict = next(
        (m for m in marketplace.modules if m.get("name") == module_name), None
    )

    if not module_dict:
        console.print(
            f"[red]Module '{module_name}' not found in marketplace '{marketplace_name}'[/red]"
        )
        raise SystemExit(1)

    repository: str | None = module_dict.get("repository")
    if not repository or not isinstance(repository, str):
        console.print(f"[red]Module '{module_name}' has no repository URL[/red]")
        raise SystemExit(1)
    content_dirname = module_dict.get("path")
    console.print(f"[green]Found '{module_name}' in '{marketplace_name}'[/green]")
    console.print(f"[dim]Repository: {repository}[/dim]")

    try:
        source_type = detect_source_type(repository)
        module_path = fetch_module_as_name(
            repository, MODULES_DIR, module_name, content_dirname
        )
        save_source_info(module_path, repository, source_type, content_dirname)
        console.print(f"[green]Added {module_name}[/green]")
        return module_path, module_dict
    except Exception as e:
        console.print(f"[red]Failed to fetch module: {e}[/red]")
        raise SystemExit(1)


# =============================================================================
# Update command helper types and functions
# =============================================================================


@dataclass
class UpdateResult:
    """Result of updating a single installation."""

    skills_ok: int = 0
    skills_failed: int = 0
    commands_ok: int = 0
    commands_failed: int = 0
    agents_ok: int = 0
    agents_failed: int = 0
    mcps_ok: int = 0
    mcps_failed: int = 0
    instructions_ok: bool = False
    orphans_removed: int = 0
    error: str | None = None


@dataclass
class UpdateContext:
    """Context for update operations on a single installation."""

    inst: Installation
    global_module: Module
    source_module: Path
    target: AssistantTarget
    registry: InstallationRegistry
    current_skills: set[str] = field(default_factory=set)
    current_commands: set[str] = field(default_factory=set)
    current_agents: set[str] = field(default_factory=set)
    current_mcps: set[str] = field(default_factory=set)
    has_instructions: bool = False
    orphaned_skills: set[str] = field(default_factory=set)
    orphaned_commands: set[str] = field(default_factory=set)
    orphaned_agents: set[str] = field(default_factory=set)
    orphaned_mcps: set[str] = field(default_factory=set)
    installed_skills: set[str] = field(default_factory=set)  # Actual installed names
    installed_commands: set[str] = field(default_factory=set)
    installed_agents: set[str] = field(default_factory=set)
    installed_mcps: set[str] = field(default_factory=set)


def _validate_installation_for_update(inst: Installation) -> tuple[bool, str | None]:
    """
    Validate that an installation can be updated.

    Returns (is_valid, error_message).
    """
    # Check if project path still exists for project-scoped installations
    if inst.scope == "project":
        if inst.project_path and not Path(inst.project_path).exists():
            return False, "project path no longer exists"

        # For project scope, project_path is required
        if not inst.project_path:
            return False, "project scope requires project path"

    # Get the global module to refresh from
    global_module_path = MODULES_DIR / inst.module_name
    if not global_module_path.exists():
        return False, "module not found in registry"

    global_module = load_registered_module(global_module_path)
    if not global_module:
        return False, "invalid module"

    # Validate module structure and skill files
    is_valid, errors = global_module.validate()
    if not is_valid:
        return False, f"validation errors: {', '.join(errors)}"

    return True, None


def _build_update_context(
    inst: Installation, registry: InstallationRegistry
) -> UpdateContext | None:
    """
    Build the context needed for updating an installation.

    Returns None if the installation cannot be updated.
    """
    global_module_path = MODULES_DIR / inst.module_name
    global_module = load_registered_module(global_module_path)
    if not global_module:
        return None

    # For user scope, use current directory for local_modules symlink
    # For project scope, use the installation's project_path
    if inst.scope == "user":
        local_modules = get_local_modules_path(str(Path.cwd()))
    else:
        local_modules = get_local_modules_path(inst.project_path)

    target = get_target(inst.assistant)

    # Refresh the local copy from global module
    source_module = copy_module_to_local(global_module, local_modules)

    # Compute current skills (unprefixed), commands, agents, and mcps from the module
    current_skills = set(global_module.skills)
    current_commands = set(global_module.commands)
    current_agents = set(global_module.agents)
    current_mcps = set(global_module.mcps)

    # Find orphaned items (in registry but not in module)
    orphaned_skills = set(inst.skills) - current_skills
    orphaned_commands = set(inst.commands) - current_commands
    orphaned_agents = set(inst.agents) - current_agents
    orphaned_mcps = set(inst.mcps) - current_mcps

    return UpdateContext(
        inst=inst,
        global_module=global_module,
        source_module=source_module,
        target=target,
        registry=registry,
        current_skills=current_skills,
        current_commands=current_commands,
        current_agents=current_agents,
        current_mcps=current_mcps,
        has_instructions=global_module.has_instructions,
        orphaned_skills=orphaned_skills,
        orphaned_commands=orphaned_commands,
        orphaned_agents=orphaned_agents,
        orphaned_mcps=orphaned_mcps,
    )


def _remove_orphaned_skills(ctx: UpdateContext, skill_dest: Path, verbose: bool) -> int:
    """Remove orphaned skill files. Returns count of removed items."""
    if not ctx.orphaned_skills or ctx.target.uses_managed_section:
        return 0

    removed = 0
    for skill in ctx.orphaned_skills:
        if ctx.target.remove_skill(skill_dest, skill):
            removed += 1
            if verbose:
                console.print(f"      [yellow]- {skill}[/yellow] [dim](orphaned)[/dim]")
    return removed


def _remove_orphaned_commands(ctx: UpdateContext, verbose: bool) -> int:
    """Remove orphaned command files. Returns count of removed items."""
    if not ctx.orphaned_commands:
        return 0

    removed = 0
    path_context = ctx.inst.project_path or ""
    scope = ctx.inst.scope
    command_dest = ctx.target.get_command_path(path_context, scope)
    for cmd_name in ctx.orphaned_commands:
        if ctx.target.remove_command(command_dest, cmd_name, ctx.inst.module_name):
            removed += 1
            if verbose:
                console.print(
                    f"      [yellow]- /{cmd_name}[/yellow] [dim](orphaned)[/dim]"
                )
    return removed


def _remove_orphaned_agents(ctx: UpdateContext, verbose: bool) -> int:
    """Remove orphaned agent files. Returns count of removed items."""
    if not ctx.orphaned_agents:
        return 0

    path_context = ctx.inst.project_path or ""
    scope = ctx.inst.scope
    agent_dest = ctx.target.get_agent_path(path_context, scope)
    if not agent_dest:
        return 0

    removed = 0
    for agent_name in ctx.orphaned_agents:
        if ctx.target.remove_agent(agent_dest, agent_name, ctx.inst.module_name):
            removed += 1
            if verbose:
                console.print(
                    f"      [yellow]- @{agent_name}[/yellow] [dim](orphaned)[/dim]"
                )
    return removed


def _remove_orphaned_mcps(ctx: UpdateContext, verbose: bool) -> int:
    """Remove orphaned MCP servers. Returns count of removed items."""
    if not ctx.orphaned_mcps:
        return 0

    path_context = ctx.inst.project_path or ""
    scope = ctx.inst.scope
    mcp_dest = ctx.target.get_mcp_path(path_context, scope)
    if not mcp_dest:
        return 0

    if ctx.target.remove_mcps(mcp_dest, ctx.inst.module_name, list(ctx.orphaned_mcps)):
        if verbose:
            for mcp_name in ctx.orphaned_mcps:
                console.print(
                    f"      [yellow]- mcp:{mcp_name}[/yellow] [dim](orphaned)[/dim]"
                )
        return len(ctx.orphaned_mcps)
    return 0


def _skill_owned_by_other_module(ctx: UpdateContext, skill_name: str) -> str | None:
    """
    Check if a skill name is owned by another module.

    Returns the owning module name if found, None otherwise.
    """
    for inst in ctx.registry.all():
        # Skip our own module
        if inst.module_name == ctx.inst.module_name:
            continue
        # Must be same project path and assistant
        if inst.project_path != ctx.inst.project_path:
            continue
        if inst.assistant != ctx.inst.assistant:
            continue
        # Check if this module has the skill installed
        if skill_name in inst.skills:
            return inst.module_name
    return None


def _resolve_update_items(
    ctx: UpdateContext, module_items: list[str], inst_items: list[str]
) -> list[str]:
    """Pick which items to regenerate during an update.

    Full installs follow the source module; cherry-picked installs lock to the
    original selection so newly-upstream items are NOT silently picked up.
    """
    if ctx.inst.full_install:
        return list(module_items)
    locked = set(inst_items)
    return [name for name in module_items if name in locked]


def _update_skills(
    ctx: UpdateContext, skill_dest: Path, verbose: bool
) -> tuple[int, int]:
    """
    Update skills for an installation.

    Returns (success_count, failed_count).
    """
    if not ctx.global_module.skills:
        return 0, 0

    skills_to_update = _resolve_update_items(
        ctx, ctx.global_module.skills, ctx.inst.skills
    )
    if not skills_to_update:
        return 0, 0

    skills_ok = 0
    skills_failed = 0

    if ctx.target.uses_managed_section:
        # Managed section targets: Update entries in GEMINI.md/AGENTS.md
        batch_skills = []
        for skill in skills_to_update:
            source = _skill_source_dir(ctx.source_module, skill)
            if source.exists():
                description = _get_skill_description(source)
                batch_skills.append((skill, description, source))
                ctx.installed_skills.add(skill)
                skills_ok += 1
                if verbose:
                    console.print(f"      [green]{skill}[/green]")
            else:
                skills_failed += 1
                if verbose:
                    console.print(
                        f"      [red]{skill}[/red] [dim](source not found)[/dim]"
                    )
        if batch_skills:
            ctx.target.generate_skills_batch(
                skill_dest,
                ctx.inst.module_name,
                batch_skills,
                ctx.inst.project_path,
            )
    else:
        for skill in skills_to_update:
            source = _skill_source_dir(ctx.source_module, skill)

            # Check if another module owns this skill name
            skill_name = skill
            owner = _skill_owned_by_other_module(ctx, skill)
            if owner:
                # Use prefixed name to avoid conflict
                skill_name = f"{ctx.inst.module_name}_{skill}"
                if verbose:
                    console.print(
                        f"      [yellow]{skill}[/yellow] [dim](using {skill_name}, "
                        f"'{skill}' owned by {owner})[/dim]"
                    )

            success = ctx.target.generate_skill(
                source, skill_dest, skill_name, ctx.inst.project_path
            )

            if success:
                ctx.installed_skills.add(skill_name)
                skills_ok += 1
                if verbose and not owner:
                    console.print(f"      [green]{skill_name}[/green]")
            else:
                skills_failed += 1
                if verbose:
                    console.print(
                        f"      [red]{skill}[/red] [dim](source not found)[/dim]"
                    )

    return skills_ok, skills_failed


def _update_commands(ctx: UpdateContext, verbose: bool) -> tuple[int, int]:
    """
    Update commands for an installation.

    Returns (success_count, failed_count).
    """
    if not ctx.global_module.commands:
        return 0, 0

    commands_to_update = _resolve_update_items(
        ctx, ctx.global_module.commands, ctx.inst.commands
    )
    if not commands_to_update:
        return 0, 0

    commands_ok = 0
    commands_failed = 0

    path_context = ctx.inst.project_path or ""
    scope = ctx.inst.scope
    command_dest = ctx.target.get_command_path(path_context, scope)
    content_path = _get_content_path(ctx.source_module)
    commands_dir = content_path / "commands"

    for cmd_name in commands_to_update:
        source = commands_dir / f"{cmd_name}.md"
        success = ctx.target.generate_command(
            source, command_dest, cmd_name, ctx.inst.module_name
        )

        if success:
            ctx.installed_commands.add(cmd_name)
            commands_ok += 1
            if verbose:
                console.print(f"      [green]/{cmd_name}[/green]")
        else:
            commands_failed += 1
            if verbose:
                console.print(
                    f"      [red]{cmd_name}[/red] [dim](source not found)[/dim]"
                )

    return commands_ok, commands_failed


def _update_agents(ctx: UpdateContext, verbose: bool) -> tuple[int, int]:
    """
    Update agents for an installation.

    Returns (success_count, failed_count).
    """
    if not ctx.global_module.agents or not ctx.target.supports_agents:
        return 0, 0

    agents_to_update = _resolve_update_items(
        ctx, ctx.global_module.agents, ctx.inst.agents
    )
    if not agents_to_update:
        return 0, 0

    path_context = ctx.inst.project_path or ""
    scope = ctx.inst.scope
    agent_dest = ctx.target.get_agent_path(path_context, scope)
    if not agent_dest:
        return 0, 0

    agents_ok = 0
    agents_failed = 0

    content_path = _get_content_path(ctx.source_module)
    agents_dir = content_path / "agents"
    for agent_name in agents_to_update:
        source = agents_dir / f"{agent_name}.md"
        success = ctx.target.generate_agent(
            source, agent_dest, agent_name, ctx.inst.module_name
        )

        if success:
            ctx.installed_agents.add(agent_name)
            agents_ok += 1
            if verbose:
                console.print(f"      [green]@{agent_name}[/green]")
        else:
            agents_failed += 1
            if verbose:
                console.print(
                    f"      [red]{agent_name}[/red] [dim](source not found)[/dim]"
                )

    return agents_ok, agents_failed


def _update_instructions(ctx: UpdateContext, verbose: bool) -> bool:
    """
    Update module instructions for an installation.

    Returns True if instructions were successfully installed.
    """
    from lola.models import INSTRUCTIONS_FILE

    path_context = ctx.inst.project_path or ""
    scope = ctx.inst.scope

    if not ctx.has_instructions:
        # Always attempt removal - handles stale installation records
        instructions_dest = ctx.target.get_instructions_path(path_context, scope)
        ctx.target.remove_instructions(instructions_dest, ctx.inst.module_name)
        if verbose:
            console.print("      [yellow]- instructions[/yellow] [dim](removed)[/dim]")
        return False

    instructions_dest = ctx.target.get_instructions_path(path_context, scope)

    # Respect --append-context from the original installation
    if ctx.inst.append_context:
        from lola.targets.install import _install_instructions

        success = _install_instructions(
            ctx.target,
            ctx.global_module,
            ctx.source_module,
            ctx.inst.project_path,
            ctx.inst.append_context,
            scope,
        )
        if success and verbose:
            console.print("      [green]instructions (appended)[/green]")
        return success

    content_path = _get_content_path(ctx.source_module)
    instructions_source = content_path / INSTRUCTIONS_FILE
    if not instructions_source.exists():
        return False

    success = ctx.target.generate_instructions(
        instructions_source, instructions_dest, ctx.inst.module_name
    )

    if success and verbose:
        console.print("      [green]instructions[/green]")

    return success


def _update_mcps(ctx: UpdateContext, verbose: bool) -> tuple[int, int]:
    """
    Update MCPs for an installation.

    Returns (success_count, failed_count).
    """
    import json
    from lola.config import MCPS_FILE

    if not ctx.global_module.mcps:
        return 0, 0

    mcps_to_update = _resolve_update_items(ctx, ctx.global_module.mcps, ctx.inst.mcps)
    if not mcps_to_update:
        return 0, 0

    path_context = ctx.inst.project_path or ""
    scope = ctx.inst.scope
    mcp_dest = ctx.target.get_mcp_path(path_context, scope)
    if not mcp_dest:
        return 0, 0

    # Load mcps.json from source module (respecting module/ subdirectory)
    content_path = _get_content_path(ctx.source_module)
    mcps_file = content_path / MCPS_FILE
    if not mcps_file.exists():
        return 0, len(mcps_to_update)

    try:
        mcps_data = json.loads(mcps_file.read_text())
        servers = mcps_data.get("mcpServers", {})
    except json.JSONDecodeError:
        return 0, len(mcps_to_update)

    wanted = set(mcps_to_update)
    servers = {k: v for k, v in servers.items() if k in wanted}
    if not servers:
        return 0, len(mcps_to_update)

    # Generate MCPs
    if ctx.target.generate_mcps(servers, mcp_dest, ctx.inst.module_name):
        for mcp_name in servers.keys():
            ctx.installed_mcps.add(mcp_name)
            if verbose:
                console.print(f"      [green]mcp:{mcp_name}[/green]")
        return len(servers), 0

    return 0, len(mcps_to_update)


def _process_single_installation(ctx: UpdateContext, verbose: bool) -> UpdateResult:
    """
    Process a single installation update.

    Removes orphaned items and regenerates all skills, commands, agents, MCPs, and instructions.
    """
    result = UpdateResult()

    # Get scope-aware paths
    path_context = ctx.inst.project_path or ""
    scope = ctx.inst.scope

    skill_dest = ctx.target.get_skill_path(path_context, scope)

    # Remove orphaned items
    result.orphans_removed += _remove_orphaned_skills(ctx, skill_dest, verbose)
    result.orphans_removed += _remove_orphaned_commands(ctx, verbose)
    result.orphans_removed += _remove_orphaned_agents(ctx, verbose)
    result.orphans_removed += _remove_orphaned_mcps(ctx, verbose)

    # Update skills
    result.skills_ok, result.skills_failed = _update_skills(ctx, skill_dest, verbose)

    # Update commands
    result.commands_ok, result.commands_failed = _update_commands(ctx, verbose)

    # Update agents
    result.agents_ok, result.agents_failed = _update_agents(ctx, verbose)

    # Update MCPs
    result.mcps_ok, result.mcps_failed = _update_mcps(ctx, verbose)

    # Update instructions
    result.instructions_ok = _update_instructions(ctx, verbose)

    return result


def _format_update_summary(result: UpdateResult) -> str:
    """Format the summary string for an update result."""
    parts = []
    if result.skills_ok > 0:
        parts.append(
            f"{result.skills_ok} {'skill' if result.skills_ok == 1 else 'skills'}"
        )
    if result.commands_ok > 0:
        parts.append(
            f"{result.commands_ok} {'command' if result.commands_ok == 1 else 'commands'}"
        )
    if result.agents_ok > 0:
        parts.append(
            f"{result.agents_ok} {'agent' if result.agents_ok == 1 else 'agents'}"
        )
    if result.mcps_ok > 0:
        parts.append(f"{result.mcps_ok} {'MCP' if result.mcps_ok == 1 else 'MCPs'}")
    if result.instructions_ok:
        parts.append("instructions")

    summary = ", ".join(parts) if parts else "no items"

    # Build status indicators
    status_parts = []
    total_failed = (
        result.skills_failed
        + result.commands_failed
        + result.agents_failed
        + result.mcps_failed
    )
    if total_failed > 0:
        status_parts.append(f"[red]{total_failed} failed[/red]")
    if result.orphans_removed > 0:
        status_parts.append(
            f"[yellow]{result.orphans_removed} orphaned removed[/yellow]"
        )

    status_suffix = f" ({', '.join(status_parts)})" if status_parts else ""

    return f"({summary}){status_suffix}"


@click.command(name="install")
@click.argument(
    "module_name", required=False, default=None, shell_complete=complete_module_names
)
@click.option(
    "-a",
    "--assistant",
    type=click.Choice(list(TARGETS.keys())),
    default=None,
    help="AI assistant to install skills for (default: prompt interactively, or all in non-interactive mode)",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show detailed output for each skill and command",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Overwrite existing skills without prompting",
)
@click.option(
    "--pre-install",
    type=click.Path(exists=False),
    default=None,
    help="Run script before installing (use instead of module's hook)",
)
@click.option(
    "--post-install",
    type=click.Path(exists=False),
    default=None,
    help="Run script after installing (use instead of module's hook)",
)
@click.option(
    "--append-context",
    type=str,
    default=None,
    help="Append a context reference instead of copying instructions verbatim. "
    "Pass the path to the main context file relative to the module root "
    "(e.g., module/AGENTS.md).",
)
@click.option(
    "--workspace",
    type=str,
    default=None,
    help="OpenClaw workspace name or absolute path (only valid with -a openclaw). "
    "Defaults to ~/.openclaw/workspace. "
    "Pass a name like 'work' to target ~/.openclaw/workspace-work.",
)
@click.option(
    "--scope",
    type=click.Choice(["project", "user"]),
    default="project",
    help="Installation scope: project (default) or user",
)
@click.option(
    "--skill",
    "skill_filters",
    multiple=True,
    help="Cherry-pick a skill to install. Repeat or use a comma-separated list. "
    "Omit to install every skill (or use the interactive picker).",
)
@click.option(
    "--command",
    "command_filters",
    multiple=True,
    help="Cherry-pick a command to install. Repeat or use a comma-separated list.",
)
@click.option(
    "--agent",
    "agent_filters",
    multiple=True,
    help="Cherry-pick an agent to install. Repeat or use a comma-separated list.",
)
@click.option(
    "--mcp",
    "mcp_filters",
    multiple=True,
    help="Cherry-pick an MCP to install. Repeat or use a comma-separated list.",
)
@click.option(
    "-y",
    "--yes",
    "yes",
    is_flag=True,
    help="Skip the interactive picker and install everything (or just what was passed via --skill/--command/--agent/--mcp).",
)
@click.argument("project_path", required=False, default="./")
def install_cmd(
    module_name: Optional[str],
    assistant: Optional[str],
    verbose: bool,
    force: bool,
    pre_install: Optional[str],
    post_install: Optional[str],
    append_context: Optional[str],
    workspace: Optional[str],
    scope: str,
    skill_filters: tuple[str, ...],
    command_filters: tuple[str, ...],
    agent_filters: tuple[str, ...],
    mcp_filters: tuple[str, ...],
    yes: bool,
    project_path: str,
):
    """
    Install a module's skills to AI assistants.

    MODULE_NAME is optional when running interactively — omit it to pick
    from registered modules via an interactive prompt.  If no assistant is
    specified, you are prompted to choose one (or all in non-interactive mode).

    \b
    Examples:
        lola install                                   # Pick module and assistants interactively
        lola install my-module                         # Pick assistants interactively
        lola install my-module -a claude-code          # Specific assistant, no prompt
        lola install my-module ./my-project            # Install in a specific project directory
        lola install my-module --append-context module/AGENTS.md   # Append context reference
        lola install my-module -a openclaw             # Install to ~/.openclaw/workspace/skills/
        lola install my-module -a openclaw --workspace work        # Install to workspace-work
        lola install my-module -a openclaw --workspace /custom/path  # Install to custom path

    \b
    Cherry-pick a subset of items:
        lola install my-module                         # Picker with "All" pre-selected
        lola install my-module -y                      # Install everything, skip picker
        lola install my-module --skill pr-review --skill commit
        lola install my-module --skill pr-review,commit --command review
        lola install my-module --agent reviewer
    """
    project_path = _resolve_install_path(assistant, project_path, workspace)

    ensure_lola_dirs()

    # Resolve module_name interactively when omitted
    if module_name is None:
        if not is_interactive():
            console.print("[red]module_name is required in non-interactive mode[/red]")
            console.print("[dim]Usage: lola install <module> [-a <assistant>][/dim]")
            raise SystemExit(1)
        registered = list_registered_modules()
        names = [m.name for m in registered]
        if not names:
            console.print(
                "[yellow]No modules registered. Use 'lola mod add' first.[/yellow]"
            )
            return
        module_name = select_module(names)
        if not module_name:
            console.print("[yellow]Cancelled[/yellow]")
            raise SystemExit(130)

    # Validation: user scope and explicit project path are mutually exclusive
    if scope == "user" and project_path != "./":
        console.print(
            "[red]Error: --scope user cannot be used with a project path argument[/red]"
        )
        console.print(
            "[dim]Use 'lola install <module> --scope user' for user-wide installation[/dim]"
        )
        raise SystemExit(1)

    # For user scope, set project_path to None for Installation record
    if scope == "user":
        install_project_path = None
        # Still need current directory for symlink creation
        current_dir = str(Path.cwd().resolve())
        local_modules = get_local_modules_path(current_dir)
    else:
        # Project scope: validate and resolve project path
        install_project_path = str(Path(project_path).resolve())
        if not Path(install_project_path).exists():
            handle_lola_error(PathNotFoundError(install_project_path, "Project path"))
        local_modules = get_local_modules_path(install_project_path)

    # Default to global registry
    module_path = MODULES_DIR / module_name
    marketplace_hooks = {}
    module_dict: dict[str, Any] = {}

    # Override with marketplace if reference provided
    marketplace_ref = parse_market_ref(module_name)
    if marketplace_ref:
        marketplace_name, current_module_name = marketplace_ref
        module_path, module_dict = _fetch_from_marketplace(
            marketplace_name, current_module_name
        )
        module_name = current_module_name
        marketplace_hooks = module_dict.get("hooks", {})

    # If module not found locally and no marketplace specified, search marketplaces
    if not module_path.exists() and not marketplace_ref:
        from lola.config import MARKET_DIR, CACHE_DIR

        mp_registry = MarketplaceRegistry(MARKET_DIR, CACHE_DIR)
        matches = mp_registry.search_module_all(module_name)

        if matches:
            selected_marketplace = mp_registry.select_marketplace(module_name, matches)
            if selected_marketplace is None:
                console.print("[yellow]Cancelled[/yellow]")
                raise SystemExit(130)
            module_path, module_dict = _fetch_from_marketplace(
                selected_marketplace, module_name
            )
            marketplace_hooks = module_dict.get("hooks", {})

    # Verify module exists
    if not module_path.exists():
        console.print("[dim]Use 'lola mod ls' to see available modules[/dim]")
        console.print("[dim]Use 'lola mod add <source>' to add a module[/dim]")
        console.print(
            "[dim]Or install from marketplace: lola install @marketplace/module[/dim]"
        )
        handle_lola_error(ModuleNotFoundError(module_name))

    module = load_registered_module(module_path)
    if not module:
        console.print(
            "[dim]Expected structure: skills/<name>/SKILL.md, commands/*.md, or agents/*.md[/dim]"
        )
        handle_lola_error(ModuleInvalidError(module_name))
    assert module is not None  # nosec B101 - type narrowing after NoReturn, not a runtime guard

    # Validate module structure and skill files
    try:
        module.validate_or_raise()
    except ValidationError as e:
        handle_lola_error(e)

    if (
        not module.skills
        and not module.commands
        and not module.agents
        and not module.mcps
        and not module.has_instructions
    ):
        console.print(
            f"[yellow]Module '{module_name}' has no skills, commands, agents, MCPs, or instructions defined[/yellow]"
        )
        return

    # Resolve cherry-pick selection.
    # Precedence: explicit flags > -y > interactive picker > install everything.
    skill_list = _expand_csv(skill_filters)
    command_list = _expand_csv(command_filters)
    agent_list = _expand_csv(agent_filters)
    mcp_list = _expand_csv(mcp_filters)
    flags_used = bool(skill_list or command_list or agent_list or mcp_list)

    selected_skills: set[str] | None = None
    selected_commands: set[str] | None = None
    selected_agents: set[str] | None = None
    selected_mcps: set[str] | None = None

    if flags_used:
        unknown: list[str] = []
        for requested, available in (
            (skill_list, set(module.skills)),
            (command_list, set(module.commands)),
            (agent_list, set(module.agents)),
            (mcp_list, set(module.mcps)),
        ):
            unknown.extend(n for n in requested if n not in available)
        if unknown:
            console.print(f"[red]Unknown items: {', '.join(unknown)}[/red]")
            console.print(
                "[dim]Use 'lola mod info <module>' to see available skills, commands, agents, and MCPs[/dim]"
            )
            raise SystemExit(1)
        # Omitted categories install nothing of that type — passing any flag
        # is an exact selection across all four.
        selected_skills = set(skill_list)
        selected_commands = set(command_list)
        selected_agents = set(agent_list)
        selected_mcps = set(mcp_list)
    elif (
        not yes
        and is_interactive()
        and (
            len(module.skills)
            + len(module.commands)
            + len(module.agents)
            + len(module.mcps)
        )
        > 1
    ):
        picked = select_module_items(
            list(module.skills),
            list(module.commands),
            list(module.agents),
            list(module.mcps),
        )
        if picked is None:
            console.print("[yellow]Cancelled[/yellow]")
            raise SystemExit(130)
        # The picker returns subsets of the originals, so equal length implies
        # equal contents — cheaper than four set comparisons.
        is_full = (
            len(picked["skills"]) == len(module.skills)
            and len(picked["commands"]) == len(module.commands)
            and len(picked["agents"]) == len(module.agents)
            and len(picked["mcps"]) == len(module.mcps)
        )
        if not is_full:
            selected_skills = set(picked["skills"])
            selected_commands = set(picked["commands"])
            selected_agents = set(picked["agents"])
            selected_mcps = set(picked["mcps"])
            if not (
                selected_skills or selected_commands or selected_agents or selected_mcps
            ):
                console.print("[yellow]Nothing selected. Cancelled.[/yellow]")
                raise SystemExit(130)

    # Get registry
    registry = get_registry()

    # Determine which assistants to install to
    if assistant:
        assistants_to_install = [assistant]
    elif is_interactive():
        chosen = select_assistants(list(TARGETS.keys()))
        if not chosen:
            console.print("[yellow]No assistants selected. Cancelled.[/yellow]")
            raise SystemExit(130)
        assistants_to_install = chosen
    else:
        # Non-interactive: preserve original default (all assistants)
        assistants_to_install = list(TARGETS.keys())

    # Resolve hooks with precedence: CLI flags > module lola.yaml > marketplace
    effective_pre_install = (
        pre_install or module.pre_install_hook or marketplace_hooks.get("pre-install")
    )
    effective_post_install = (
        post_install
        or module.post_install_hook
        or marketplace_hooks.get("post-install")
    )

    display_path = install_project_path or "~/.lola (user scope)"
    console.print(f"\n[bold]Installing {module_name} -> {display_path}[/bold]")
    console.print()

    total_installed = 0
    for asst in assistants_to_install:
        total_installed += install_to_assistant(
            module,
            asst,
            scope,
            install_project_path,
            local_modules,
            registry,
            verbose,
            force,
            effective_pre_install,
            effective_post_install,
            append_context,
            selected_skills=selected_skills,
            selected_commands=selected_commands,
            selected_agents=selected_agents,
            selected_mcps=selected_mcps,
        )

    # Update installation records with version from marketplace metadata
    if module_dict and module_dict.get("version"):
        version = module_dict.get("version")
        for asst in assistants_to_install:
            installations = registry.find(module_name)
            for inst in installations:
                if (
                    inst.assistant == asst
                    and inst.scope == scope
                    and inst.project_path == install_project_path
                ):
                    inst.version = version
                    registry.add(inst)  # Update the record

    console.print()
    console.print(
        f"[green]Installed to {len(assistants_to_install)} assistant{'s' if len(assistants_to_install) != 1 else ''}[/green]"
    )


@click.command(name="uninstall")
@click.argument(
    "module_name",
    required=False,
    default=None,
    shell_complete=complete_installed_module_names,
)
@click.option(
    "-a",
    "--assistant",
    type=click.Choice(list(TARGETS.keys())),
    default=None,
    help="AI assistant to uninstall from (optional)",
)
@click.option(
    "-v", "--verbose", is_flag=True, help="Show detailed output for each file removed"
)
@click.argument("project_path", required=False, default=None)
@click.option(
    "-f", "--force", is_flag=True, help="Force uninstall without confirmation"
)
@click.option(
    "--scope",
    type=click.Choice(["project", "user"]),
    default=None,
    help="Filter by installation scope",
)
def uninstall_cmd(
    module_name: Optional[str],
    assistant: Optional[str],
    verbose: bool,
    project_path: Optional[str],
    force: bool,
    scope: Optional[str],
):
    """
    Uninstall a module's skills from AI assistants.

    Removes generated skill files but keeps the module in the registry.
    Use 'lola mod rm' to fully remove a module.

    When module_name is omitted in an interactive terminal, a picker is shown
    listing all installed modules. Cancelling the picker exits with code 130.

    \b
    Examples:
        lola uninstall my-module
        lola uninstall my-module -a claude-code
        lola uninstall my-module -a cursor ./my-project
        lola uninstall                          # interactive picker
    """
    ensure_lola_dirs()

    # Resolve module_name interactively when omitted
    if module_name is None:
        if not is_interactive():
            console.print("[red]module_name is required in non-interactive mode[/red]")
            raise SystemExit(1)
        registry = get_registry()
        installed_names = sorted({inst.module_name for inst in registry.all()})
        if not installed_names:
            console.print("[yellow]No modules installed.[/yellow]")
            return
        module_name = select_module(installed_names)
        if not module_name:
            console.print("[yellow]Cancelled[/yellow]")
            raise SystemExit(130)

    registry = get_registry()
    installations = registry.find(module_name)

    if not installations:
        console.print(f"[yellow]No installations found for '{module_name}'[/yellow]")
        console.print("[dim]Use 'lola list' to see all installed modules[/dim]")
        return

    # Filter by assistant/project_path/scope if provided
    original_count = len(installations)
    if assistant:
        installations = [i for i in installations if i.assistant == assistant]
    if project_path:
        project_path = str(Path(project_path).resolve())
        installations = [i for i in installations if i.project_path == project_path]
    if scope:
        installations = [i for i in installations if i.scope == scope]

    if not installations:
        # Show more helpful error based on what filters were applied
        if scope:
            console.print(
                f"[yellow]'{module_name}' is installed but not with --scope {scope}[/yellow]"
            )
            console.print(
                f"[dim]Found {original_count} installation(s) with other scope(s). Use 'lola list' to see all.[/dim]"
            )
        else:
            console.print("[yellow]No matching installations found[/yellow]")
        return

    # Show what will be uninstalled
    console.print(f"\n[bold]Uninstalling {module_name}[/bold]")
    console.print()

    # Group installations by (scope, project) for cleaner display
    by_scope_project: dict[str, list[Installation]] = {}
    for inst in installations:
        # For user scope, show "user scope" instead of path
        if inst.scope == "user":
            key = "user scope"
        else:
            key = inst.project_path or "project (no path)"
        if key not in by_scope_project:
            by_scope_project[key] = []
        by_scope_project[key].append(inst)

    for location, insts in by_scope_project.items():
        assistants = [i.assistant for i in insts]
        skill_count = len(insts[0].skills) if insts[0].skills else 0
        cmd_count = len(insts[0].commands) if insts[0].commands else 0
        agent_count = len(insts[0].agents) if insts[0].agents else 0
        mcp_count = len(insts[0].mcps) if insts[0].mcps else 0
        has_instructions = insts[0].has_instructions

        parts = []
        if skill_count:
            parts.append(f"{skill_count} skill{'s' if skill_count != 1 else ''}")
        if cmd_count:
            parts.append(f"{cmd_count} command{'s' if cmd_count != 1 else ''}")
        if agent_count:
            parts.append(f"{agent_count} agent{'s' if agent_count != 1 else ''}")
        if mcp_count:
            parts.append(f"{mcp_count} MCP{'s' if mcp_count != 1 else ''}")
        if has_instructions:
            parts.append("instructions")

        summary = ", ".join(parts) if parts else "no items"
        console.print(f"  [dim]{location}[/dim]")
        console.print(f"    {', '.join(assistants)} [dim]({summary})[/dim]")

    console.print()

    # Confirm if multiple installations and not forced
    if len(installations) > 1 and not force:
        if is_interactive():
            choices = []
            for inst in installations:
                project_label = inst.project_path or "~/.lola (user scope)"
                label = f"{project_label} ({inst.assistant})"
                choices.append((inst.project_path or "", inst.assistant, label))
            selected = select_installations(choices)
            if not selected:
                console.print("[yellow]Cancelled[/yellow]")
                return
            selected_keys = {(p, a) for p, a, _ in selected}
            installations = [
                i
                for i in installations
                if ((i.project_path or ""), i.assistant) in selected_keys
            ]
        else:
            console.print("[yellow]Multiple installations found[/yellow]")
            console.print(
                "[dim]Use -a <assistant> to target specific installation[/dim]"
            )
            console.print("[dim]Use -f/--force to uninstall all[/dim]")
            console.print()
            if not click.confirm("Uninstall all?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

    # Uninstall each
    removed_count = 0
    for inst in installations:
        target = get_target(inst.assistant)

        # Get scope-aware paths for removal
        path_context = inst.project_path or ""
        inst_scope = inst.scope

        # Remove skill files
        if inst.skills:
            skill_dest = target.get_skill_path(path_context, inst_scope)

            if target.uses_managed_section:
                # Managed section targets: remove module section from GEMINI.md/AGENTS.md
                if target.remove_skill(skill_dest, module_name):
                    removed_count += 1
                    if verbose:
                        console.print(
                            f"  [green]Removed skills from {skill_dest}[/green]"
                        )
            else:
                for skill in inst.skills:
                    if target.remove_skill(skill_dest, skill):
                        removed_count += 1
                        if verbose:
                            console.print(f"  [green]Removed {skill}[/green]")

        # Remove command files
        if inst.commands:
            command_dest = target.get_command_path(path_context, inst_scope)

            for cmd_name in inst.commands:
                if target.remove_command(command_dest, cmd_name, module_name):
                    removed_count += 1
                    if verbose:
                        filename = target.get_command_filename(module_name, cmd_name)
                        console.print(
                            f"  [green]Removed {command_dest / filename}[/green]"
                        )

        # Remove agent files
        if inst.agents:
            agent_dest = target.get_agent_path(path_context, inst_scope)

            if agent_dest:
                for agent_name in inst.agents:
                    if target.remove_agent(agent_dest, agent_name, module_name):
                        removed_count += 1
                        if verbose:
                            filename = target.get_agent_filename(
                                module_name, agent_name
                            )
                            console.print(
                                f"  [green]Removed {agent_dest / filename}[/green]"
                            )

        # Remove instructions
        if inst.has_instructions:
            instructions_dest = target.get_instructions_path(path_context, inst_scope)
            if target.remove_instructions(instructions_dest, module_name):
                removed_count += 1
                if verbose:
                    console.print(
                        f"  [green]Removed instructions from {instructions_dest}[/green]"
                    )

        # Remove MCP servers
        if inst.mcps:
            mcp_dest = target.get_mcp_path(path_context, inst_scope)
            if mcp_dest and target.remove_mcps(mcp_dest, module_name, list(inst.mcps)):
                removed_count += len(inst.mcps)
                if verbose:
                    console.print(f"  [green]Removed MCPs from {mcp_dest}[/green]")

        # Also remove the project-local module copy
        if inst.scope == "project" and inst.project_path:
            local_modules = get_local_modules_path(inst.project_path)
            source_module = local_modules / module_name
            if source_module.is_symlink():
                source_module.unlink()
                removed_count += 1
                if verbose:
                    console.print(f"  [green]Removed symlink {source_module}[/green]")
            elif source_module.exists():
                # Handle legacy copies
                shutil.rmtree(source_module)
                removed_count += 1
                if verbose:
                    console.print(f"  [green]Removed {source_module}[/green]")
        elif inst.scope == "user":
            # For user scope, use current directory for symlink
            local_modules = get_local_modules_path(str(Path.cwd()))
            source_module = local_modules / module_name
            if source_module.is_symlink():
                source_module.unlink()
                removed_count += 1
                if verbose:
                    console.print(f"  [green]Removed symlink {source_module}[/green]")

        # Remove from registry
        registry.remove(
            module_name,
            assistant=inst.assistant,
            scope=inst.scope,
            project_path=inst.project_path,
        )

    console.print(
        f"[green]Uninstalled from {len(installations)} installation{'s' if len(installations) != 1 else ''}[/green]"
    )


@click.command(name="update")
@click.argument(
    "module_name",
    required=False,
    default=None,
    shell_complete=complete_installed_module_names,
)
@click.option(
    "-a",
    "--assistant",
    type=click.Choice(list(TARGETS.keys())),
    default=None,
    help="Filter by AI assistant",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show detailed output for each skill and command",
)
def update_cmd(module_name: Optional[str], assistant: Optional[str], verbose: bool):
    """
    Regenerate assistant files from source in .lola/modules/.

    Use this after modifying skills in .lola/modules/ to update the
    generated files for all assistants.

    \b
    Examples:
        lola update                    # Update all modules
        lola update my-module          # Update specific module
        lola update -a cursor          # Update only Cursor files
        lola update -v                 # Verbose output
    """
    ensure_lola_dirs()

    registry = get_registry()
    installations = registry.all()

    if module_name:
        installations = [i for i in installations if i.module_name == module_name]
    if assistant:
        installations = [i for i in installations if i.assistant == assistant]

    if not installations:
        console.print("[yellow]No installations to update[/yellow]")
        return

    # Group installations by module name for cleaner display
    by_module: dict[str, list[Installation]] = {}
    for inst in installations:
        if inst.module_name not in by_module:
            by_module[inst.module_name] = []
        by_module[inst.module_name].append(inst)

    module_word = "module" if len(by_module) == 1 else "modules"
    console.print(f"\n[bold]Updating {len(by_module)} {module_word}[/bold]")
    console.print()

    stale_installations: list[Installation] = []

    for mod_name, mod_installations in by_module.items():
        console.print(f"[bold]{mod_name}[/bold]")

        # Group by (scope, path) for display
        by_scope_path: dict[tuple[str, str | None], list[Installation]] = {}
        for inst in mod_installations:
            key = (inst.scope, inst.project_path)
            if key not in by_scope_path:
                by_scope_path[key] = []
            by_scope_path[key].append(inst)

        for (scope, project_path), scope_insts in by_scope_path.items():
            console.print(f"  [dim]scope:[/dim] {scope}")
            if project_path:
                console.print(f'  [dim]path:[/dim] "{project_path}"')

            for inst in scope_insts:
                # Validate installation
                is_valid, error_msg = _validate_installation_for_update(inst)
                if not is_valid:
                    console.print(f"    [red]{inst.assistant}: {error_msg}[/red]")
                    if error_msg == "project path no longer exists":
                        stale_installations.append(inst)
                    continue

                # Build context for update
                ctx = _build_update_context(inst, registry)
                if not ctx:
                    console.print(
                        f"    [red]{inst.assistant}: failed to build context[/red]"
                    )
                    continue

                # Process the installation update
                result = _process_single_installation(ctx, verbose)

                # Cherry-picked installs lock to what we regenerated; full
                # installs track upstream so new items get picked up.
                inst.skills = list(ctx.installed_skills)
                if inst.full_install:
                    inst.commands = list(ctx.current_commands)
                    inst.agents = list(ctx.current_agents)
                    inst.mcps = list(ctx.current_mcps)
                else:
                    inst.commands = list(ctx.installed_commands)
                    inst.agents = list(ctx.installed_agents)
                    inst.mcps = list(ctx.installed_mcps)
                inst.has_instructions = result.instructions_ok
                registry.add(inst)

                # Print summary line for this installation
                summary = _format_update_summary(result)
                console.print(
                    f"    [green]{inst.assistant}[/green] [dim]{summary}[/dim]"
                )

    console.print()
    if stale_installations:
        console.print(
            f"[yellow]Found {len(stale_installations)} stale installation(s)[/yellow]"
        )
    console.print("[green]Update complete[/green]")


@click.command(name="list")
@click.option(
    "-a",
    "--assistant",
    type=click.Choice(list(TARGETS.keys())),
    default=None,
    help="Filter by AI assistant",
)
def list_installed_cmd(assistant: Optional[str]):
    """
    List all installed modules.

    Shows where each module's skills have been installed.
    """
    ensure_lola_dirs()

    registry = get_registry()
    installations = registry.all()

    if assistant:
        installations = [i for i in installations if i.assistant == assistant]

    if not installations:
        console.print("[yellow]No modules installed[/yellow]")
        console.print()
        console.print("[dim]Install modules with: lola install <module>[/dim]")
        return

    # Group by module name
    by_module: dict[str, list[Installation]] = {}
    for inst in installations:
        if inst.module_name not in by_module:
            by_module[inst.module_name] = []
        by_module[inst.module_name].append(inst)

    # Pluralize correctly
    module_word = "module" if len(by_module) == 1 else "modules"
    console.print(f"\n[bold]Installed ({len(by_module)} {module_word})[/bold]")
    console.print()

    for mod_name, insts in by_module.items():
        console.print(f"[bold]{mod_name}[/bold]")

        # Group installations by (scope, path) to consolidate assistants
        by_scope_path: dict[tuple[str, str | None], list[Installation]] = {}
        for inst in insts:
            key = (inst.scope, inst.project_path)
            if key not in by_scope_path:
                by_scope_path[key] = []
            by_scope_path[key].append(inst)

        for (scope, project_path), scope_insts in by_scope_path.items():
            # Collect all assistants for this scope/path
            assistants = sorted(set(inst.assistant for inst in scope_insts))
            assistants_str = ", ".join(assistants)

            console.print(f"  - [dim]scope:[/dim] {scope}")
            if project_path:
                console.print(f'    [dim]path:[/dim] "{project_path}"')
            console.print(f"    [dim]assistants:[/dim] \\[{assistants_str}]")

            for inst in scope_insts:
                if inst.append_context:
                    console.print(
                        f"    [dim]append-context ({inst.assistant}):[/dim] {inst.append_context}"
                    )
        console.print()
