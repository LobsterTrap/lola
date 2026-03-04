"""CLI utility functions shared across commands."""

from typing import NoReturn

from rich.console import Console

from lola.exceptions import LolaError

_console = Console()


def handle_lola_error(e: LolaError) -> NoReturn:
    """Handle a LolaError by printing an error message and exiting.

    Args:
        e: The LolaError to handle

    Raises:
        SystemExit: Always exits with code 1
    """
    _console.print(f"[red]{e}[/red]")
    raise SystemExit(1)
