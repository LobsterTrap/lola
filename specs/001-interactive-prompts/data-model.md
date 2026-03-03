# Data Model: Interactive CLI Prompts

**Branch**: `001-interactive-prompts` | **Phase**: 1

---

This feature introduces **no new persistent data structures**. Interactive prompts are transient
UI interactions — they collect user intent at runtime and pass it to existing command logic
that already handles storage.

The data entities below describe the runtime values that flow through the prompt layer.

---

## Entities

### PromptMode

Represents whether the current process can support interactive prompts.

| Field | Type | Description |
|-------|------|-------------|
| is_tty | bool | `True` when stdin is connected to a real terminal; derived from `sys.stdin.isatty()` |

**Validation rule**: Evaluated once per command invocation, before any prompt is shown.

**State transitions**: None. Read-only flag.

---

### AssistantSelection

The result of a multi-select assistant prompt.

| Field | Type | Description |
|-------|------|-------------|
| chosen | list[str] | Zero or more assistant names from TARGETS; empty list means user cancelled |

**Validation rules**:
- Each entry in `chosen` must be a key present in `TARGETS`.
- Empty `chosen` is treated as cancellation, not as "install to zero assistants".

---

### ModuleSelection

The result of a single-select module picker.

| Field | Type | Description |
|-------|------|-------------|
| module_name | str \| None | Registered module name selected by the user; `None` means cancelled |

**Validation rules**:
- `module_name`, when not `None`, must correspond to an existing installation in the registry.

---

### MarketplaceSelection

The result of a single-select marketplace picker when a module name conflicts across marketplaces.

| Field | Type | Description |
|-------|------|-------------|
| marketplace_name | str \| None | Name of the chosen marketplace; `None` means cancelled |
| module_dict | dict | The full module entry dict from the chosen marketplace catalog |

**Validation rules**:
- `marketplace_name`, when not `None`, must be an enabled marketplace in the registry.

---

## Data Flow

```
User invokes command (no -a flag)
        │
        ▼
is_interactive()?
  ├── False → use existing default behaviour (all assistants or error)
  └── True  → call select_assistants([...])
                    │
                    ▼
              AssistantSelection.chosen
                    │
                    ├── empty → print "Cancelled", sys.exit(130)
                    └── non-empty → proceed with existing install_to_assistant() loop

User invokes uninstall (no module_name)
        │
        ▼
is_interactive()?
  ├── False → print "module_name required in non-interactive mode", sys.exit(1)
  └── True  → call select_module([installed modules])
                    │
                    ▼
              ModuleSelection.module_name
                    │
                    ├── None → print "Cancelled", sys.exit(130)
                    └── str  → proceed with existing uninstall logic
```
