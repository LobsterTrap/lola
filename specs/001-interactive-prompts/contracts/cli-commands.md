# CLI Command Contracts: Interactive Prompts

**Branch**: `001-interactive-prompts` | **Phase**: 1

Describes the before/after behaviour of each affected command. "Before" is current behaviour;
"After" is the behaviour after this feature is implemented.

---

## `lola install [MODULE] [-a ASSISTANT]`

### Signature change

```
# Before (module_name required)
lola install <module_name> [-a <assistant>] [project_path]

# After (module_name optional when interactive)
lola install [module_name] [-a <assistant>] [project_path]
```

### Behaviour matrix

| module_name | -a flag | TTY? | Behaviour (After) |
|-------------|---------|------|-------------------|
| provided    | provided | any | Unchanged: install specified module to specified assistant |
| provided    | omitted  | Yes | **NEW**: Show multi-select assistant picker → install to chosen |
| provided    | omitted  | No  | Unchanged: install to all assistants (current default) |
| omitted     | provided | Yes | **NEW**: Show module picker from registry → install to specified assistant |
| omitted     | provided | No  | Error: "module_name required in non-interactive mode" |
| omitted     | omitted  | Yes | **NEW**: Show module picker, then assistant picker |
| omitted     | omitted  | No  | Error: "module_name required in non-interactive mode" |

### Exit codes

| Condition | Exit code |
|-----------|-----------|
| Successful install | 0 |
| User cancels module picker | 130 |
| User cancels assistant picker | 130 |
| Non-interactive, module_name missing | 1 |
| Module not found | 1 |

---

## `lola uninstall [MODULE] [-a ASSISTANT]`

### Signature change

```
# Before (module_name required positional argument)
lola uninstall <module_name> [-a <assistant>] [project_path]

# After (module_name optional when interactive)
lola uninstall [module_name] [-a <assistant>] [project_path]
```

### Behaviour matrix

| module_name | TTY? | Behaviour (After) |
|-------------|------|-------------------|
| provided    | any  | Unchanged: uninstall specified module |
| omitted     | Yes  | **NEW**: Show single-select picker of installed modules → uninstall chosen |
| omitted     | No   | Error: "module_name required in non-interactive mode" |

### Exit codes

| Condition | Exit code |
|-----------|-----------|
| Successful uninstall | 0 |
| User cancels module picker | 130 |
| Non-interactive, module_name missing | 1 |
| No modules installed (picker would be empty) | 0 (print message, no picker shown) |

---

## `lola install <MODULE>` — Marketplace Conflict Resolution

*This is not a signature change; it is a UI improvement inside the existing flow.*

### Behaviour change

| Condition | Before | After |
|-----------|--------|-------|
| Module found in 1 marketplace | Auto-selected (unchanged) | Unchanged |
| Module found in N marketplaces | `click.prompt` with numbered list | **NEW**: InquirerPy `select` with descriptions |
| User cancels | N/A (click.prompt loops) | Clean exit, no installation |

---

## Backward Compatibility

All existing explicit flag usage is **fully preserved**:

```bash
lola install my-module -a claude-code          # Works exactly as before
lola uninstall my-module                        # Works exactly as before
lola install @marketplace/my-module            # Works exactly as before
```

Scripts and CI pipelines that pass module names and assistant flags explicitly will see
no behaviour change. The interactive paths are only activated when arguments are omitted
AND stdin is a TTY.
