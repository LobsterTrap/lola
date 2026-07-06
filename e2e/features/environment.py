"""Behave environment hooks for E2E scenario isolation."""

import shutil
import tempfile
from pathlib import Path

from support.cli import LolaCLI


def before_scenario(context, scenario):
    """Set up an isolated temp environment for each scenario."""
    # Isolated temp directory per scenario — no state leaks between scenarios
    context.tmp_dir = Path(tempfile.mkdtemp(prefix="lola-e2e-"))
    # LOLA_HOME override — subprocess reads this env var instead of ~/.lola
    context.lola_home = context.tmp_dir / ".lola"
    # Working directory for CLI invocations (simulates a user's project)
    context.project_dir = context.tmp_dir / "project"
    context.project_dir.mkdir(parents=True)
    # CLI wrapper that runs `lola` as a subprocess with LOLA_HOME set
    context.cli = LolaCLI(context.lola_home, context.project_dir)
    # Registry of module source paths created by Given steps, keyed by name
    context.modules = {}
    # HTTP servers started by marketplace steps, stopped in after_scenario
    context.http_servers = []
    # Most recent LolaResult from a "When I run lola" step
    context.last_result = None


def after_scenario(context, scenario):
    """Stop any HTTP servers and remove the scenario's temp directory."""
    for server in getattr(context, "http_servers", []):
        server.stop()
    shutil.rmtree(context.tmp_dir, ignore_errors=True)
