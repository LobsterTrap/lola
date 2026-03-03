# Research: Interactive CLI Prompts

**Branch**: `001-interactive-prompts` | **Phase**: 0

---

## Decision 1: Interactive Prompt Library

**Decision**: InquirerPy 0.3.4

**Rationale**:
- InquirerPy provides `inquirer.checkbox()` (multi-select) and `inquirer.select()` (single-select) with a single, consistent import pattern.
- Built on `prompt_toolkit`, which handles raw terminal input, ANSI sequences, and platform differences (including Windows Terminal).
- Latest stable version is 0.3.4; no breaking changes since 0.3.0.
- Inline prompts: renders below the current Rich output without clearing the screen, unlike full-screen TUI frameworks (textual, urwid).
- Tested with Click CLI wrappers in numerous projects.

**Alternatives considered**:
- **pytermgui**: More suited to full widget-based UIs; too heavy for simple selection prompts; smaller community.
- **urwid**: Battle-tested but very low-level; requires manual event loop management; excessive for 2-item prompts.
- **questionary**: Similar API to InquirerPy but fewer active maintainers and older `prompt_toolkit` bindings.
- **simple-term-menu**: Single-purpose, but no built-in multi-select; would need two libraries.
- **click.prompt with IntRange**: Already used in `select_marketplace`; no visual navigation, error-prone for users.

---

## Decision 2: Non-Interactive Detection

**Decision**: `sys.stdin.isatty()`

**Rationale**:
- Standard POSIX mechanism; works reliably on macOS, Linux, and Windows (WSL2 and Windows Terminal).
- InquirerPy itself uses `prompt_toolkit`'s input detection, which calls `isatty()` internally and raises `prompt_toolkit.input.base.InputHookNotSupported` or renders nothing in non-interactive mode. Calling `isatty()` before prompt construction gives us full control over the fallback message.
- Avoids the ambiguity of `TERM=dumb` detection, which is not universally set in CI environments.

**Alternatives considered**:
- Checking `TERM == "dumb"` or `CI` env var: fragile, not universally set.
- Catching InquirerPy exceptions: less readable, mixes flow control with error handling.

---

## Decision 3: Install Command Behavior When No `-a` Flag Is Given

**Decision**: Prompt in interactive mode; install to **all** assistants in non-interactive mode (preserving current behaviour).

**Rationale**:
- The current behaviour ("no flag → all assistants") is documented and users relying on scripts/CI expect it.
- Changing it to "error in non-interactive mode" would be a breaking change.
- The interactive path is purely additive: when a TTY is detected, ask; otherwise, silently use the existing default.

---

## Decision 4: Uninstall Command Module Selection

**Decision**: Make `module_name` an optional Click argument; if absent and stdin is a TTY, show InquirerPy select from the installation registry; if absent and non-interactive, error with a message.

**Rationale**:
- `uninstall` currently requires the module name as a positional argument, causing a Click usage error if omitted.
- Making it optional (default `None`) allows graceful handling in both paths.
- The error in non-interactive mode (missing module name) is the correct CLI behaviour since there is no safe default.

---

## Decision 5: Architecture — Where to Put Prompt Logic

**Decision**: New module `src/lola/prompts.py` exposing three public functions:
- `is_interactive() -> bool`
- `select_assistants(available: list[str]) -> list[str]`
- `select_module(modules: list[str]) -> str | None`
- `select_marketplace(matches: list[tuple[dict, str]]) -> str | None`

**Rationale**:
- Keeps prompt logic out of CLI command bodies; commands stay testable by mocking at the module level.
- Centralises the `is_interactive()` check so all commands apply it consistently.
- `market/manager.py`'s `select_marketplace` method delegates to `prompts.select_marketplace` for the selection UI, keeping business logic and UI separate.

---

## Decision 6: Dependency Declaration

**Decision**: Add `InquirerPy>=0.3.4` to `[project.dependencies]` in `pyproject.toml`.

**Rationale**:
- It is a runtime dependency (not dev-only) since prompts appear during normal use.
- 0.3.4 is the only stable release at the 0.3.x level; `>=0.3.4` pins to the tested API while allowing patch updates.

---

## Decision 7: Testing Strategy

**Decision**: Mock `src.lola.prompts.is_interactive`, `src.lola.prompts.select_assistants`, and `src.lola.prompts.select_module` at the module boundary in tests.

**Rationale**:
- InquirerPy requires a real TTY to render. Click's `CliRunner` captures stdout but uses a non-TTY stdin by default, which makes `isatty()` return False.
- Patching `is_interactive` to return `True` and patching the prompt functions to return fixture values lets tests exercise both the interactive and non-interactive paths deterministically.
- No actual terminal interaction needed in the test suite.
