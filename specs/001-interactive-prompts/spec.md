# Feature Specification: Interactive CLI Prompts

**Feature Branch**: `001-interactive-prompts`
**Created**: 2026-03-03
**Status**: Draft
**Input**: User description: "Integrate interactive TUI prompts into lola CLI so that when users omit required options, they are asked for them interactively rather than receiving an error or silently using defaults."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Interactive Assistant Selection on Install (Priority: P1)

A user runs `lola install <module>` without specifying which AI assistant(s) to install to.
Instead of silently installing to all assistants or erroring, lola presents an interactive
multi-select checklist showing all available AI assistants. The user navigates with arrow
keys, toggles selections with Space, and confirms with Enter.

**Why this priority**: This is the most common interaction point where users are expected to
specify an option they may not know ahead of time. Getting it wrong (installing to unwanted
assistants) creates cleanup work.

**Independent Test**: Can be fully tested by running `lola install <any-registered-module>`
without the `-a` flag, verifying that an interactive checklist appears, making a selection,
and confirming that only the selected assistants receive the installed module.

**Acceptance Scenarios**:

1. **Given** a module is registered and no `-a` flag is passed, **When** the user runs `lola install <module>`, **Then** an interactive multi-select prompt appears listing all available assistants.
2. **Given** the interactive prompt is displayed, **When** the user selects one or more assistants and confirms, **Then** the module is installed only to the selected assistants.
3. **Given** the interactive prompt is displayed, **When** the user cancels (Escape or Ctrl+C), **Then** lola exits cleanly with a cancellation message and performs no installation.
4. **Given** lola is invoked with `-a <assistant>`, **When** install runs, **Then** no interactive prompt appears and the specified assistant is used directly.

---

### User Story 2 - Interactive Module Selection on Uninstall (Priority: P2)

A user runs `lola uninstall` without specifying a module name. Instead of erroring,
lola presents an interactive searchable list of installed modules. The user types to
filter, navigates with arrow keys, and confirms with Enter to select which module to uninstall.

**Why this priority**: Uninstalling a wrong module is harder to recover from than a failed
install. Interactive selection reduces typos and the need to separately run `lola ls` first.

**Independent Test**: Can be fully tested by running `lola uninstall` with at least one module
installed, verifying the picker appears, selecting a module, and confirming removal.

**Acceptance Scenarios**:

1. **Given** one or more modules are installed, **When** the user runs `lola uninstall` without arguments, **Then** an interactive list of installed module names appears.
2. **Given** the interactive list is displayed, **When** the user selects a module and confirms, **Then** lola proceeds with the uninstall flow for that module (including any existing confirmation prompts).
3. **Given** no modules are installed, **When** the user runs `lola uninstall` without arguments, **Then** a clear message is shown ("No modules installed") and no prompt appears.
4. **Given** the interactive list is displayed, **When** the user cancels, **Then** lola exits cleanly with no side effects.

---

### User Story 3 - Interactive Marketplace Selection on Conflict (Priority: P3)

A user runs `lola install <module>` where the module name exists in multiple enabled
marketplaces. Instead of a numbered-list text prompt, lola presents an interactive
select list showing each marketplace option with its version and description.

**Why this priority**: This is a less frequent flow but the current numbered-prompt UX is
inconsistent with the rest of the interactive experience once P1 and P2 are in place.

**Independent Test**: Can be fully tested with two marketplaces enabled that both contain
a module with the same name, then running `lola install <module>` and verifying the
interactive list replaces the old numbered prompt.

**Acceptance Scenarios**:

1. **Given** a module name matches entries in multiple enabled marketplaces, **When** the user runs `lola install <module>`, **Then** an interactive select list appears showing marketplace names, module versions, and descriptions.
2. **Given** the marketplace select prompt is displayed, **When** the user selects an entry and confirms, **Then** the module is fetched from that marketplace.
3. **Given** the marketplace select prompt is displayed, **When** the user cancels, **Then** lola exits cleanly with no installation.

---

### Edge Cases

- What happens when lola's stdin is not a terminal (piped, redirected, CI environment)? The system must detect non-interactive mode and fall back gracefully — either requiring explicit flags, or erroring with a clear message indicating how to pass the flag.
- What happens when there is only one assistant available? The single item should be auto-selected without displaying a prompt.
- What happens when the user's terminal does not support ANSI escape sequences? Prompts must degrade gracefully or fall back to plain text input.
- What happens if the user sends SIGINT during a multi-step prompt? Lola must exit cleanly without partial side effects (no half-installed modules, no registry corruption).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When `lola install <module>` is run without `-a/--assistant`, lola MUST display a multi-select interactive prompt listing all available AI assistants instead of silently using all or erroring.
- **FR-002**: The multi-select prompt MUST allow selecting zero or more assistants; selecting zero and confirming MUST cancel the operation with an appropriate message.
- **FR-003**: When `lola uninstall` is run without a module name argument, lola MUST display a searchable single-select interactive list of currently installed modules.
- **FR-004**: When a module name resolves to entries in more than one enabled marketplace, lola MUST display an interactive single-select list showing all matching entries with their marketplace name, version, and description.
- **FR-005**: All interactive prompts MUST support keyboard navigation: arrow keys to move, Space to toggle (multi-select), Enter to confirm, Escape/Ctrl+C to cancel.
- **FR-006**: Cancelling any interactive prompt MUST result in a clean exit with a cancellation message and no side effects (no files written, no registry changes).
- **FR-007**: When stdin is not a terminal (piped or redirected input), lola MUST skip interactive prompts and behave as it does today — requiring flags explicitly and showing a clear message that indicates which flag is required.
- **FR-008**: Existing explicit flag usage (e.g., `-a claude-code`) MUST continue to work exactly as before; prompts are only triggered when the option is genuinely absent.
- **FR-009**: The interactive prompt capability MUST be shipped as a declared runtime dependency of the lola package.
- **FR-010**: When `lola install` is run without a module name argument, lola MUST display a single-select interactive list of registered modules (same pattern as FR-003 for uninstall).

### Key Entities

- **Interactive Prompt**: A terminal UI element that captures structured user input (single-select or multi-select) via keyboard navigation; replaces typed-number or skipped option inputs.
- **Non-interactive Mode**: Execution context where stdin is not a TTY (CI pipelines, shell piping, script automation); prompts must not block or fail unexpectedly in this mode.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can select target assistants for `lola install` without typing any flag, completing the selection in under 30 seconds for a list of 4 items.
- **SC-002**: Users can identify and uninstall a module without first running a separate list command; the full flow (open picker → select → confirm) completes in under 60 seconds.
- **SC-003**: Zero unintended installations or removals occur as a result of the interactive prompts replacing silent defaults.
- **SC-004**: All existing automated invocations of lola (CI, scripts) that pass explicit flags continue to work without modification after this feature is introduced.
- **SC-005**: Cancelling any prompt at any stage produces a non-zero exit code and leaves the system state identical to before the command was run.

## Assumptions

- The terminal environment used by lola's primary users supports standard ANSI escape sequences (macOS Terminal, iTerm2, most Linux terminals, Windows Terminal).
- InquirerPy has been selected as the interactive prompt library; all prompt requirements above are implementable with it.
- The lola TARGETS dict (currently 4 assistants) is small enough that a full-screen TUI framework is not needed; a simple inline prompt is sufficient.
- Non-interactive fallback means erroring with a descriptive message (e.g., "Use -a/--assistant to specify an assistant in non-interactive mode"), not silently installing to all assistants.
