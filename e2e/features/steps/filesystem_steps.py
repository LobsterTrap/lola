"""Step definitions for filesystem preconditions and assertions."""

from pathlib import Path

from behave import given, then

from support.cli import resolve_path
from support.fixtures import (
    create_module_full,
    register_module,
)


@given('a module "{name}" with skills, commands, and agents')
def step_module_full(context, name):
    """Create a module source directory with one skill, command, and agent."""
    source_dir = context.tmp_dir / "sources"
    source_dir.mkdir(exist_ok=True)
    module_path = create_module_full(source_dir, name)
    context.modules[name] = module_path


@given('the module "{name}" is registered')
def step_module_registered(context, name):
    """Copy a module into LOLA_HOME/modules/ to simulate `lola mod add`."""
    assert name in context.modules, (
        f'Module "{name}" not set up. '
        f"Add a preceding 'Given a module \"{name}\" with ...' step."
    )
    register_module(context.lola_home, context.modules[name], name)


@then('the directory "{path}" should exist')
def step_dir_exists(context, path):
    """Assert that a directory exists at the resolved path."""
    resolved = resolve_path(context, path)
    assert Path(resolved).is_dir(), f"Expected directory to exist: {resolved}"


@then('the directory "{path}" should not exist')
def step_dir_not_exists(context, path):
    """Assert that no directory exists at the resolved path."""
    resolved = resolve_path(context, path)
    assert not Path(resolved).is_dir(), f"Expected directory NOT to exist: {resolved}"


@given('the module "{name}" is installed to "{assistant}"')
def step_module_installed(context, name, assistant):
    """Register a module and install it to an assistant via the CLI."""
    assert name in context.modules, (
        f'Module "{name}" not set up. '
        f"Add a preceding 'Given a module \"{name}\" with ...' step."
    )
    register_module(context.lola_home, context.modules[name], name)
    result = context.cli.run("install", name, "-a", assistant)
    assert result.exit_code == 0, (
        f"Failed to install {name} to {assistant}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
