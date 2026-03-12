"""
completions:
    Shell completion support for lola CLI
"""

import click
from click.shell_completion import CompletionItem

from lola.config import MODULES_DIR, MARKET_DIR, INSTALLED_FILE
from lola.models import InstallationRegistry


def complete_module_names(ctx, param, incomplete):
    """Complete registered module names from MODULES_DIR."""
    if not MODULES_DIR.exists():
        return []

    try:
        modules = [
            CompletionItem(d.name)
            for d in MODULES_DIR.iterdir()
            if d.is_dir() and d.name.startswith(incomplete)
        ]
        return modules
    except Exception:
        return []


def complete_marketplace_names(ctx, param, incomplete):
    """Complete marketplace names from MARKET_DIR/*.yml files."""
    if not MARKET_DIR.exists():
        return []

    try:
        marketplaces = [
            CompletionItem(f.stem)
            for f in MARKET_DIR.glob("*.yml")
            if f.stem.startswith(incomplete)
        ]
        return marketplaces
    except Exception:
        return []


def complete_installed_module_names(ctx, param, incomplete):
    """Complete installed module names from InstallationRegistry."""
    if not INSTALLED_FILE.exists():
        return []

    try:
        registry = InstallationRegistry(INSTALLED_FILE)
        # Get unique module names from all installations
        module_names = set(inst.module_name for inst in registry.all())
        modules = [
            CompletionItem(name) for name in module_names if name.startswith(incomplete)
        ]
        return modules
    except Exception:
        return []


@click.command(name="completions")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completions_cmd(shell: str):
    """
    Generate shell completion script.

    \b
    Usage:
        # System-wide install (for RPM packaging):
        lola completions bash > /usr/share/bash-completion/completions/lola
        lola completions zsh  > /usr/share/zsh/site-functions/_lola
        lola completions fish > /usr/share/fish/vendor_completions.d/lola.fish

        # Per-user install:
        lola completions bash > ~/.local/share/bash-completion/completions/lola

        # Evaluate in current shell:
        eval "$(lola completions bash)"
    """
    from click.shell_completion import get_completion_class

    # Get the completion class for the specified shell
    completion_class = get_completion_class(shell)

    if completion_class is None:
        click.echo(f"Error: Unsupported shell '{shell}'", err=True)
        raise SystemExit(1)

    # Get the root command (main CLI group)
    # We need to traverse up to find the root command
    ctx = click.get_current_context()
    root_cmd = ctx.find_root().command

    # Create a completion instance
    completion = completion_class(root_cmd, {}, "lola", "_LOLA_COMPLETE")

    # Generate and output the completion script source
    script = completion.source()
    click.echo(script)
