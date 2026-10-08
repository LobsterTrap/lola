# Assistant File Ownership

----
> 🦾 Written with LLM assistance [claude-opus-5]
> 💪 Reviewed by a human before submission
----

Implementation detail for [ADR: Assistant File
Ownership](../../adr/assistant-file-ownership.md). The ADR owns the
decision; this document owns the module format, the per-target layout, the
reference syntax, and the migration.

Requirements here are stated as behaviour, so they hold for any implementation
of Lola, including a future Go one. Python names appear only where they
describe today's code: in Current behaviour, and where the migration has to
undo something that code does.

## Current behaviour

`src/lola/targets/base.py` provides two mixins that write into markdown files:

- `ManagedSectionTarget` — skills are rendered into a `lola:skills` managed
  section of `MANAGED_FILE`, one `### <module>` heading per module. Only
  `gemini-cli` uses it, with `MANAGED_FILE = "GEMINI.md"`.
- `ManagedInstructionsTarget` — module instructions are rendered into a managed
  section of `INSTRUCTIONS_FILE`. Used by `claude-code` (`CLAUDE.md`),
  `opencode` (`AGENTS.md`), `copilot-*` (`.github/copilot-instructions.md`)
  and `gemini-cli` (`GEMINI.md`). `GeminiTarget` mixes in both.

`ManagedInstructionsTarget` wraps what it writes:

```html
<!-- lola:instructions:start -->
<!-- lola:module:example:start -->
...module content, inlined verbatim...
<!-- lola:module:example:end -->
<!-- lola:instructions:end -->
```

`generate_instructions` resolves the module's content and inlines it.
`remove_instructions` finds the module's markers and removes that block,
dropping the whole section when the last module goes. The markers are reliable;
the problem is what sits between them.

`cursor` uses neither mixin. `CursorTarget.generate_instructions` writes
`.cursor/rules/<module>-instructions.mdc` with `alwaysApply: true`, and
`remove_instructions` unlinks it.

`openclaw` uses neither mixin and does not override the base implementations.
`BaseAssistantTarget.generate_instructions` returns `False`, so the
`.openclaw/instructions.md` path `OpenClawTarget` declares is never written.
It delivers no instructions today.

## OpenClaw workspaces

`openclaw` paths are relative to an OpenClaw workspace rather than a project.
Lola selects the workspace from `lola install --workspace`, and every
implementation must resolve it the same way:

- no value: `~/.openclaw/workspace`
- a bare name: `~/.openclaw/workspace-<name>`
- a value containing a path separator: that path, with `~` expanded
- `--scope user`: the default workspace

`--workspace` is rejected for any assistant other than `openclaw`.

## Module format

In the legacy layout, a module's instructions source is
`module/INSTRUCTIONS.md`. OpenCode's own `AGENTS.md` is a host file, not a
module source, and is unaffected.

An Agent Plugins package's instructions source is the path its manifest
declares, falling back to `dev.getlola/AGENTS.md`, as the [Agent Plugins Format
ADR](../../adr/agent-plugins-format.md) defines. Delivery, scope rules and
migration below apply to it unchanged. The table and warning in this section
apply to the legacy layout only; the open question about the plugin fallback
is recorded in the ownership ADR.

Lola classifies every legacy-layout module into one of three states.
"Present" means present and non-empty:

| `INSTRUCTIONS.md` | `AGENTS.md` | Module state              |
|-------------------|-------------|---------------------------|
| present           | either      | ships instructions        |
| absent            | present     | legacy instructions only  |
| absent            | absent      | no instructions           |

"Legacy instructions only" drives the warning and nothing else. It never causes
content to be written.

`lola mod init --format lola` scaffolds `module/INSTRUCTIONS.md` instead of
`module/AGENTS.md`, and the remediation text Lola prints for legacy module
structures names the new file. The default `lola mod init` emits an Agent
Plugins package, whose scaffold is governed by the Agent Plugins Format ADR.

### Legacy warning

Emitted at `lola mod add` and again at `lola install`, because the person who
registers a module is often not the person who can fix it:

```text
warning: git-module ships AGENTS.md but no INSTRUCTIONS.md.
         Lola no longer reads AGENTS.md; its instructions were NOT installed.

         If you maintain this module, rename
           module/AGENTS.md -> module/INSTRUCTIONS.md
         If not, open an issue upstream.

         Skills, commands and agents were installed normally.
```

There is no flag to inject the legacy file anyway.

## Target layout after this change

Owned instructions path, and the reference written into a user file if any:

- `cursor`: `.cursor/rules/<module>-instructions.mdc`. No reference.
- `copilot-cli`: `.github/instructions/<module>.instructions.md`. No reference.
- `copilot-vscode`: inherited from `copilot-cli`.
- `opencode`: `.opencode/lola/<module>.md`. Glob in `opencode.json`.
- `openclaw`: none. Instructions are not delivered; install reports it.
- `claude-code`: `.claude/lola/<module>.md`. `@.claude/lola/<module>.md` in
  `CLAUDE.md`.
- `gemini-cli`: `.gemini/lola/<module>.md`. `@.gemini/lola/<module>.md` in
  `GEMINI.md`.

`gemini-cli` skills move from the `GEMINI.md` managed section to
`.gemini/skills/<skill>/SKILL.md`, copied the same way `claude-code` copies
skills, with `~/.gemini/skills/` at user scope.

Per-module files are the unit that is created and deleted, so uninstalling one
module never rewrites another's content. There is no generated `index.md`.

At `--scope user` the same layout applies under the user's assistant directory,
with the exceptions covered below.

## Reference syntax

Each row is verified against the host's current documentation.

**`cursor`** resolves `.mdc` rules with `alwaysApply: true` without any
reference. Unchanged from today.

**`copilot-*`** resolves `.github/instructions/**/*.instructions.md` when the
file's `applyTo` frontmatter matches. Lola writes `applyTo: "**"` so module
instructions are always on:

```markdown
---
applyTo: "**"
---
```

**`opencode`** does not parse file references inside `AGENTS.md` — upstream is
explicit about this. Its documented mechanism for extra instruction files is
the `instructions` array in `opencode.json`, which accepts globs, so Lola adds
one entry:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": [".opencode/lola/*.md"]
}
```

The entry is added when the first instructions-shipping module is installed and
removed when uninstall deletes the last file under `.opencode/lola/`. Because it
is a glob, installs and uninstalls in between leave it alone. Both writes merge
into any existing config, the same way Lola already merges MCP server entries
into host JSON configs: other `instructions` entries and other keys
are preserved. If removing the glob leaves `instructions` empty, the key is
removed.

**`claude-code`** resolves `@path` imports inside `CLAUDE.md`. This repository
relies on it: `CLAUDE.md` begins with `@AGENTS.md`. One line per
instructions-shipping module goes inside the existing markers:

```markdown
<!-- lola:instructions:start -->
@.claude/lola/git-module.md
@.claude/lola/deploy-module.md
<!-- lola:instructions:end -->
```

**`gemini-cli`** resolves `@file.md` imports inside `GEMINI.md`, so it uses the
same shape, pointing at `.gemini/lola/<module>.md`. Skills no longer go in
`GEMINI.md` at all: Gemini CLI discovers `.gemini/skills/` and
`~/.gemini/skills/` from v0.26.0, where Agent Skills became enabled by default.
Lola does not use the `.agents/skills/` alias Gemini CLI also reads, because
other hosts read it too and two targets sharing one directory cannot uninstall
independently.

**`openclaw`** has no reference to write. Within a workspace it injects
always-on content only from fixed bootstrap basenames at the workspace root
(`AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, `BOOTSTRAP.md`,
`MEMORY.md`), which the user owns. The bundled `bootstrap-extra-files` hook
loads extra files only once the user enables it in OpenClaw's configuration,
and only with those basenames. Lola delivers no instructions to `openclaw` and
reports that at install.

Record the finding in each target's module docstring so the next reader does not
re-derive it.

## Scope rules

**`claude-code` and `gemini-cli` are project scope only for instructions.** The
pointer would have to go in `~/.claude/CLAUDE.md` or `~/.gemini/GEMINI.md`.
Writing the owned file without the pointer would leave content nothing reads,
so Lola writes neither and reports why. Skills at user scope are unaffected —
both hosts read their user skills directory unprompted.

Dropping user-scope instructions is a **breaking change** for both targets:
`--scope user` stops writing `~/.claude/CLAUDE.md` and the global `GEMINI.md`,
and reports that instructions are project scope only. For `gemini-cli` it ships
together with the Gemini CLI v0.26.0 minimum, and user-scope skills go to
`~/.gemini/skills/`.

Lola's `gemini-cli` target currently writes user-scope `GEMINI.md` to
`~/GEMINI.md`,
while Gemini CLI's documented global context file is `~/.gemini/GEMINI.md`.
Lola writes neither from now on. Migration cleans both (see Which file), so
existing user-scope managed sections are removed on the next `lola update` or
`lola uninstall`.

At user scope, install and update write only inside each assistant's own
directories. The one exception is migration cleanup: it removes Lola's legacy
blocks from the user-level files listed under Which file, such as
`~/GEMINI.md`, and never adds content to them.

## Migration

One-way removal. There is no new mechanism to migrate into, so nothing is
dual-written and there is no flag day.

### When it runs

Removal runs during `lola install`, `lola update` and `lola uninstall`. One
shared legacy-section cleaner serves every target that previously wrote a
managed section; the parsing is non-trivial and must not be duplicated per
target.

Uninstall is a trigger because a user can upgrade Lola and uninstall a module
without running install or update first. The new uninstall path only removes
the new owned file and reference, so without this
the legacy block would outlive the installation record and keep loading.

### Which file

The file is resolved from the installation record's stored `scope` using the
target's **legacy** destination, not the new layout:

| Target        | `scope: project`                  | `scope: user`         |
|---------------|-----------------------------------|-----------------------|
| `claude-code` | `CLAUDE.md`                       | `~/.claude/CLAUDE.md` |
| `opencode`    | `AGENTS.md`                       | see below             |
| `copilot-*`   | `.github/copilot-instructions.md` | see below             |
| `gemini-cli`  | `GEMINI.md`                       | see below             |

Project-scope paths are relative to the installation's project root. These are
the paths current Lola writes, so they are what migration must clean.

For `opencode` at `scope: user`, the file is `opencode/AGENTS.md` under
`$XDG_CONFIG_HOME` when that variable is set, otherwise
`~/.config/opencode/AGENTS.md`.

For `copilot-cli` and `copilot-vscode` at `scope: user`, the file is
`~/.copilot/copilot-instructions.md`.

For `gemini-cli` at `scope: user`, migration checks both `~/GEMINI.md`, where
Lola writes today, and `~/.gemini/GEMINI.md`, Gemini CLI's
documented global file. Both the `lola:instructions` and `lola:skills`
sections are handled, with the same comparison and the same condition table as
every other legacy block. A file without Lola's markers is left untouched, so
checking a file Lola never wrote is harmless.

### What is compared

A block is compared against what Lola would have generated from the
project-local module copy at `.lola/modules/<name>/`, with the record's stored
options including any stored `--append-context` value. That copy is the
source the block was generated from. The refreshed copy is not: today update
refreshes the copy before processing instructions (`copy_module_to_local()` in
`_build_update_context()`), so after a module
changes, or renames `AGENTS.md` to `INSTRUCTIONS.md`, comparing against the
refreshed copy would report every untouched block as hand-edited.

So comparison runs before the copy changes: before install or update
refreshes it, and before uninstall removes `.lola/modules/<name>/`. At
user scope the copy lives under the current directory's `.lola/modules/`, as it
does today; if it is absent there, the block is kept and reported. A legacy
copy that is a symlink to the global module is compared as found.

For each module block inside a `lola:instructions` section, and each
`### <module>` entry inside `gemini-cli`'s `lola:skills` section:

| Condition                              | Action                   |
|----------------------------------------|--------------------------|
| Block matches what Lola would generate | Remove                   |
| Block differs from generated content   | Keep, report hand-edited |
| No project-local copy to compare with  | Keep, report             |
| Module content present, markers absent | Leave file, report       |
| Last block removed                     | Remove enclosing section |

Reading a legacy `AGENTS.md` in order to compare against it is permitted. Lola
declines to inject it, not to look at it.

Every file changed and every difference kept is reported:

```text
Removed stale instructions block from CLAUDE.md
  - git-module (matched generated content)
Kept in AGENTS.md (hand-edited, remove manually):
  - deploy-module
Found undelimited module content, not touched:
  - GEMINI.md: legacy-module
```

### What migration will not do

If the markers around a block were removed by hand, the content is
indistinguishable from the user's own writing. Lola does not guess. It leaves
the file untouched and reports that it found module content it cannot delimit,
naming the file and the module.

This is the only correct behaviour available: deleting unmarked lines risks
destroying the user's work, and leaving a duplicate is visible and recoverable.

### `--append-context`

Deleted rather than aliased. It is accepted on the command line *and* persisted
in installation records, so removal covers stored state as well as the flag.
Update never replays a stored value. Today it does: `_update_instructions()`
in `src/lola/cli/install.py` checks the stored value before the normal
instructions path and re-inlines content, and that branch is removed. The
stored value is read only as a comparison input during migration.

## Implementation shape

Every target that delivers instructions writes and removes its own per-module
files and references, as `cursor` does today. No target renders module content
into a user-authored file, and `gemini-cli` installs skills as directories.
`copilot-vscode` behaves exactly as `copilot-cli` for instructions.

Cleaning up previous installations is a separate concern from a target's own
uninstall path, so the legacy-section cleaner is a shared component, not part
of any target. It understands both legacy formats: per-module markers inside
`lola:instructions`, and `### <module>` entries inside `lola:skills`. It is the
only place that format knowledge survives. Without it existing installations
can never be cleaned up.

In today's code this means no target uses `ManagedInstructionsTarget` or
`ManagedSectionTarget` any more, so neither has a remaining writer.

## Testing

- A module with no `INSTRUCTIONS.md` writes no owned file, no reference, and
  touches no user file, on every target
- A module with a legacy `AGENTS.md` only warns, injects nothing, and still
  installs skills, commands and agents
- A module with both files uses `INSTRUCTIONS.md` and warns about nothing
- Uninstalling instructions leaves a user file byte-identical to its pre-install
  state, for every target, including when the user edited around the block
- Installing two modules and uninstalling one leaves the other's owned file
  untouched and its reference line unchanged
- `opencode.json` gains exactly one glob entry, idempotent across repeated
  installs, and merges into an existing config without disturbing other keys
- Uninstalling the last `opencode` instructions module removes the glob and
  leaves other `instructions` entries and keys intact
- `gemini-cli` installs skills to `.gemini/skills/`, or `~/.gemini/skills/` at
  user scope, and writes no `lola:skills` section
- `openclaw` writes no instructions file and reports that instructions are not
  delivered, for both the default workspace and `--workspace <name>`
- Migration on a file with a hand-edited module block keeps the user's version
  and reports it
- Migration on a file with removed markers changes nothing and reports it
- Migration removes an unedited block after the global module has changed, and
  after it renamed `AGENTS.md` to `INSTRUCTIONS.md`, proving comparison uses the
  pre-refresh project copy
- `lola uninstall`, with no install or update since upgrading, removes the
  module's legacy block
- Migration for a `scope: user` record cleans `~/.claude/CLAUDE.md`, or
  `~/GEMINI.md` and `~/.gemini/GEMINI.md`, not the operated project's file
- `lola update` and `lola uninstall` on a `gemini-cli` `scope: user` record
  remove unedited `lola:instructions` and `lola:skills` blocks from the
  user-level `GEMINI.md`, keep hand-edited ones, and report both
- `lola update` on an existing record with a stored `--append-context` value
  does not write inline content to any user file
- `claude-code --scope user` and `gemini-cli --scope user` install nothing
  outside the host's own directory and report that instructions are project
  scope only
- `--scope user` install and update write nothing under `$HOME` outside the
  assistant's own directory, on every target, except migration removing legacy
  blocks from the user-level files listed under Which file
- Migration for `opencode` and `copilot-*` `scope: user` records cleans
  `~/.config/opencode/AGENTS.md` (or its `$XDG_CONFIG_HOME` equivalent) and
  `~/.copilot/copilot-instructions.md`
- Round-trip: install, migrate, uninstall, and confirm no Lola-owned file or
  reference remains
- E2E BDD coverage for the legacy warning, per the new-CLI-behaviour rule
