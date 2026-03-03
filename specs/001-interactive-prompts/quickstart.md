# Quickstart: Interactive CLI Prompts

**Branch**: `001-interactive-prompts` | **Phase**: 1

---

## For Implementers

### 1. Add the dependency

```bash
uv add InquirerPy
```

This adds `InquirerPy>=0.3.4` to `pyproject.toml` and updates `uv.lock`.

---

### 2. Create `src/lola/prompts.py`

New module with four public functions:

```python
# src/lola/prompts.py
import sys
from InquirerPy import inquirer
from InquirerPy.base.control import Choice

def is_interactive() -> bool:
    """Return True when stdin is a real TTY (not piped/CI)."""
    return sys.stdin.isatty()

def select_assistants(available: list[str]) -> list[str]:
    """
    Show a multi-select checkbox for AI assistants.
    Returns selected names, or [] if cancelled.
    """
    result = inquirer.checkbox(
        message="Select assistants to install to (Space to toggle, Enter to confirm):",
        choices=available,
    ).execute()
    return result or []

def select_module(modules: list[str]) -> str | None:
    """
    Show a single-select list for installed modules.
    Returns selected name, or None if cancelled.
    """
    return inquirer.select(
        message="Select module:",
        choices=modules,
    ).execute()

def select_marketplace(matches: list[tuple[dict, str]]) -> str | None:
    """
    Show a single-select list for marketplace conflict resolution.
    matches: list of (module_dict, marketplace_name)
    Returns chosen marketplace_name, or None if cancelled.
    """
    choices = [
        Choice(
            value=marketplace_name,
            name=f"@{marketplace_name}/{module.get('name', '?')} "
                 f"v{module.get('version', '?')} — {module.get('description', '')}",
        )
        for module, marketplace_name in matches
    ]
    return inquirer.select(
        message="Module found in multiple marketplaces. Select one:",
        choices=choices,
    ).execute()
```

---

### 3. Modify `src/lola/cli/install.py`

#### `install_cmd` — make `module_name` optional and add assistant picker

```python
@click.command(name="install")
@click.argument("module_name", required=False, default=None)   # was required
# ... rest of options unchanged ...
def install_cmd(module_name: Optional[str], assistant: Optional[str], ...):
    from lola.prompts import is_interactive, select_module, select_assistants

    # --- NEW: module picker when name omitted ---
    if module_name is None:
        if not is_interactive():
            console.print("[red]module_name required in non-interactive mode[/red]")
            console.print("[dim]Usage: lola install <module> [-a <assistant>][/dim]")
            raise SystemExit(1)
        registered = list_registered_modules()
        names = [m.name for m in registered]
        if not names:
            console.print("[yellow]No modules registered. Use 'lola mod add' first.[/yellow]")
            return
        module_name = select_module(names)
        if not module_name:
            console.print("[yellow]Cancelled[/yellow]")
            raise SystemExit(130)

    # ... existing module resolution logic unchanged ...

    # --- CHANGE: assistant picker when -a omitted ---
    if assistant is None and is_interactive():
        chosen = select_assistants(list(TARGETS.keys()))
        if not chosen:
            console.print("[yellow]No assistants selected. Cancelled.[/yellow]")
            raise SystemExit(130)
        assistants_to_install = chosen
    else:
        assistants_to_install = [assistant] if assistant else list(TARGETS.keys())
```

#### `uninstall_cmd` — make `module_name` optional

```python
@click.command(name="uninstall")
@click.argument("module_name", required=False, default=None)   # was required
# ... rest unchanged ...
def uninstall_cmd(module_name: Optional[str], ...):
    from lola.prompts import is_interactive, select_module

    if module_name is None:
        if not is_interactive():
            console.print("[red]module_name required in non-interactive mode[/red]")
            raise SystemExit(1)
        registry = get_registry()
        installed = list(dict.fromkeys(i.module_name for i in registry.all()))
        if not installed:
            console.print("[yellow]No modules installed.[/yellow]")
            return
        module_name = select_module(installed)
        if not module_name:
            console.print("[yellow]Cancelled[/yellow]")
            raise SystemExit(130)
    # ... rest unchanged ...
```

---

### 4. Modify `src/lola/market/manager.py`

#### `select_marketplace` — replace `click.prompt` with InquirerPy

```python
def select_marketplace(self, module_name, matches, show_version=True):
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0][1]

    from lola.prompts import select_marketplace as prompt_select
    return prompt_select(matches)
```

---

### 5. Update spec and add FR-010

In `spec.md`, add:
- **FR-010**: When `lola install` is run without a module name argument, lola MUST display a single-select interactive list of registered modules (same pattern as FR-003 for uninstall).

---

### 6. Tests

Create `tests/test_prompts.py`:
- Test `is_interactive()` returns `False` in CliRunner context.
- Test each prompt function with mocked `inquirer.*`.

Modify `tests/test_cli_install.py`:
- Add tests for `install_cmd` without `module_name` in non-interactive mode (expect error).
- Add tests for `install_cmd` without `module_name` with mocked interactive path.
- Add tests for `install_cmd` without `-a` in interactive mode with mocked `select_assistants`.
- Add tests for `uninstall_cmd` without `module_name`.
