"""
Top-level search command.

Searches both the local module registry and all enabled marketplace caches.
"""

import click
from rich.console import Console
from rich.table import Table

from lola.cli.mod import list_registered_modules
from lola.config import CACHE_DIR, MARKET_DIR
from lola.market.search import search_market
from lola.models import Module
from lola.utils import ensure_lola_dirs

console = Console()


def _count_str(count: int, singular: str) -> str:
    return f"{count} {singular}" if count == 1 else f"{count} {singular}s"


def _search_local(query_lower: str) -> list[Module]:
    results: list[Module] = []
    for module in list_registered_modules():
        haystack = [module.name, *module.skills, *module.commands, *module.agents]
        if any(query_lower in item.lower() for item in haystack):
            results.append(module)
    return results


def _print_local(results: list[Module]) -> None:
    plural = "s" if len(results) != 1 else ""
    console.print(f"[bold]Local registry ({len(results)} module{plural})[/bold]\n")
    for module in results:
        console.print(f"  [cyan]{module.name}[/cyan]")
        skills_str = _count_str(len(module.skills), "skill")
        cmds_str = _count_str(len(module.commands), "command")
        agents_str = _count_str(len(module.agents), "agent")
        console.print(f"    [dim]{skills_str}, {cmds_str}, {agents_str}[/dim]")
    console.print()


def _print_marketplace(results: list[dict]) -> None:
    plural = "s" if len(results) != 1 else ""
    console.print(f"[bold]Marketplaces ({len(results)} module{plural})[/bold]\n")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Module")
    table.add_column("Version")
    table.add_column("Marketplace")
    table.add_column("Description")
    for r in results:
        table.add_row(r["name"], r["version"], r["marketplace"], r["description"])
    console.print(table)
    console.print()


@click.command(name="search")
@click.argument("query")
@click.option(
    "--local", "scope", flag_value="local", help="Search only the local registry"
)
@click.option(
    "--remote", "scope", flag_value="remote", help="Search only enabled marketplaces"
)
def search_cmd(query: str, scope: str | None):
    """
    Search modules in the local registry and enabled marketplaces.

    Local matches are by module name, skill name, command name, or agent name.
    Marketplace matches are by module name, description, or tag.

    QUERY: Search term to match

    \b
    Examples:
        lola search git              # search both local and remote
        lola search git --local      # only the local registry
        lola search git --remote     # only enabled marketplaces
    """
    ensure_lola_dirs()
    query_lower = query.lower()

    show_local = scope != "remote"
    show_remote = scope != "local"

    local_results = _search_local(query_lower) if show_local else []
    market_results = (
        search_market(query, MARKET_DIR, CACHE_DIR) if show_remote else []
    )

    total = len(local_results) + len(market_results)
    if total == 0:
        console.print(f"[yellow]No modules found matching '{query}'[/yellow]")
        if not show_remote:
            console.print(
                "[dim]Tip: drop --local to also search remote marketplaces[/dim]"
            )
        elif not show_local:
            console.print(
                "[dim]Tip: drop --remote to also search the local registry[/dim]"
            )
        else:
            console.print(
                "[dim]Tip: check spelling or add a marketplace with 'lola market add'[/dim]"
            )
        return

    console.print()
    if local_results:
        _print_local(local_results)
    if market_results:
        _print_marketplace(market_results)
