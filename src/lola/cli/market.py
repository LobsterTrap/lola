"""
Marketplace management CLI commands.

Commands for adding, managing, and searching marketplaces.
"""

import click

from lola.cli.completions import complete_marketplace_names
from lola.config import MARKET_DIR, CACHE_DIR
from lola.market.manager import MarketplaceRegistry
from lola.prompts import is_interactive, select_marketplace_name


def _marketplace_names() -> list[str]:
    """Return sorted list of registered marketplace stem names."""
    return sorted(f.stem for f in MARKET_DIR.glob("*.yml"))


@click.group(name="market")
def market():
    """
    Manage lola marketplaces.

    Add, update, and manage marketplace catalogs.
    """
    pass


@market.command(name="add")
@click.argument("name")
@click.argument("url")
def market_add(name: str, url: str):
    """
    Add a new marketplace.

    NAME: Marketplace name (e.g., 'official')
    URL: Marketplace catalog URL
    """
    registry = MarketplaceRegistry(MARKET_DIR, CACHE_DIR)
    registry.add(name, url)


@market.command(name="ls")
@click.argument("name", required=False, shell_complete=complete_marketplace_names)
def market_ls(name: str | None):
    """
    List marketplaces or modules in a marketplace.

    Without NAME: lists all registered marketplaces.
    With NAME: lists all modules in the specified marketplace.
    """
    registry = MarketplaceRegistry(MARKET_DIR, CACHE_DIR)
    if name:
        registry.show(name)
    else:
        registry.list()


@market.command(name="set")
@click.argument(
    "name", required=False, default=None, shell_complete=complete_marketplace_names
)
@click.option("--enable", "action", flag_value="enable", help="Enable marketplace")
@click.option("--disable", "action", flag_value="disable", help="Disable marketplace")
def market_set(name: str | None, action: str):
    """
    Enable or disable a marketplace.

    If NAME is omitted in an interactive terminal, a picker is shown.

    \b
    Examples:
        lola market set my-market --enable    # Enable specific marketplace
        lola market set --enable              # Show interactive picker then enable
    """
    if name is None:
        if not is_interactive():
            click.echo("name is required in non-interactive mode", err=True)
            raise SystemExit(1)
        names = _marketplace_names()
        if not names:
            click.echo("No marketplaces registered.")
            return
        name = select_marketplace_name(names)
        if not name:
            click.echo("Cancelled")
            raise SystemExit(130)

    if not action:
        click.echo("Error: Must specify either --enable or --disable")
        raise SystemExit(1)

    registry = MarketplaceRegistry(MARKET_DIR, CACHE_DIR)

    if action == "enable":
        registry.enable(name)
    elif action == "disable":
        registry.disable(name)


@market.command(name="rm")
@click.argument(
    "name", required=False, default=None, shell_complete=complete_marketplace_names
)
def market_rm(name: str | None):
    """
    Remove a marketplace.

    If NAME is omitted in an interactive terminal, a picker is shown.

    \b
    Examples:
        lola market rm my-market    # Remove specific marketplace
        lola market rm              # Show interactive picker
    """
    if name is None:
        if not is_interactive():
            click.echo("name is required in non-interactive mode", err=True)
            raise SystemExit(1)
        names = _marketplace_names()
        if not names:
            click.echo("No marketplaces registered.")
            return
        name = select_marketplace_name(names)
        if not name:
            click.echo("Cancelled")
            raise SystemExit(130)

    registry = MarketplaceRegistry(MARKET_DIR, CACHE_DIR)
    registry.remove(name)


@market.command(name="update")
@click.argument("name", required=False, shell_complete=complete_marketplace_names)
@click.option("--all", "update_all", is_flag=True, help="Update all marketplaces")
def market_update(name: str, update_all: bool):
    """
    Update marketplace cache.

    NAME: Marketplace name (optional, updates all if not specified)
    """
    if name and update_all:
        click.echo("Error: Cannot specify both NAME and --all")
        raise SystemExit(1)

    registry = MarketplaceRegistry(MARKET_DIR, CACHE_DIR)

    if name:
        registry.update(name)
        return

    registry.update()
