# ADR: Assistant File Ownership

**Status**: Proposed
**Date**: 2026-08-25
**Last Updated**: 2026-10-08
**Authors**: trevor-vaughan
**Reviewers**:

----
> 🦾 Written with LLM assistance [claude-opus-5]
> 💪 Reviewed by a human before submission
----

## Context

Class, function and file names in this section and in References describe the
current Python implementation. The Decision is stated as behaviour, which any
implementation of Lola, including a future Go one, must provide.

Lola generates assistant files on install. Two reports say it generates some of
them in files it does not own.

Issue #158 describes `lola install` inlining a module's entire `AGENTS.md` into
the user's own `CLAUDE.md`, `AGENTS.md` or `GEMINI.md`. These are files the user
maintains by hand and every assistant reloads on every turn. At user scope
`ClaudeCodeTarget.get_instructions_path` resolves to `~/.claude/CLAUDE.md`, so
material installed for one project is loaded in every unrelated one.

Issue #148 describes the same behaviour from a maintainer's position. The
maintainer checks `AGENTS.md` into git and uses `lola sync` to recommend modules
to contributors. Injected content makes the tracked file change whenever a skill
changes or a contributor pins a different version, and contributors who do not
use Lola get a file describing modules they do not have.

The current behaviour is not unmarked. `ManagedInstructionsTarget` wraps
everything it adds in HTML comment delimiters, one pair around the whole section
and one pair per module, and `remove_instructions` deletes a module's block
cleanly. Removal works. What the markers do not change is that the content
itself is copied into a file the user owns, so the file still changes size and
still churns in version control.

### The content is redundant

Both reports are about where the content goes. The prior question is whether it
needs to go anywhere.

Every target Lola supports discovers skills on its own and reads each skill's
`description` frontmatter to decide when to load it. Verified against each
host's current documentation, the skill directories each host reads are:

- `claude-code`: `.claude/skills/`
- `cursor`: `.cursor/skills/`, `.claude/skills/`, `.agents/skills/`
- `opencode`: `.opencode/skills/`, `.claude/skills/`, `.agents/skills/`
- `copilot-cli`: `.github/skills/`, `.claude/skills/`, `~/.copilot/skills/`
- `copilot-vscode`: inherits `copilot-cli` paths by subclassing
- `openclaw`: `<workspace>/skills/`, `<workspace>/.agents/skills/`
- `gemini-cli`: `.gemini/skills/`, `.agents/skills/`, and the same pair
  under `~/` at user scope

A module-level instructions blob that lists a module's own skills therefore
restates metadata the host already parses, and charges the user's context
budget for it on every turn. `examples/git-module/module/AGENTS.md` is exactly
this: four bullets naming a skill, two commands and an agent, every one of
which every target discovers unaided.

`gemini-cli` is the most recent addition to that list. Agent Skills shipped as
an experimental preview in Gemini CLI v0.23.0 and became enabled by default in
v0.26.0. Before then `GEMINI.md` was the only way skills reached Gemini CLI,
which is why Lola's `gemini-cli` target renders skills into a managed section
of `GEMINI.md` today.

### `AGENTS.md` is the wrong name for the payload

`lola install` copies the module into the consumer's repository at
`.lola/modules/<name>/`. Copilot reads `AGENTS.md` files stored anywhere in a
repository, taking the nearest one in the directory tree, and OpenCode walks up
from the working directory loading them. So when an agent works on files under
`.lola/modules/<name>/`, that module's `AGENTS.md` becomes its governing
instructions — unmarked, unintended, and outside the reach of
`remove_instructions`. The blast radius is narrow, but it exists whether or not
Lola injects anything.

The name also makes intent unreadable. `Module.has_instructions` is derived from
whether `AGENTS.md` exists and is non-empty, so an author who writes one for
human contributors gets it injected into every consumer's context file as a side
effect. Presence is being read as intent.

The codebase already carries the confusion, twice, for opposite things:
`models.py` defines `INSTRUCTIONS_FILE = "AGENTS.md"` as a **source** Lola
reads, and `OpenCodeTarget` defines `INSTRUCTIONS_FILE = "AGENTS.md"` as a
**destination** Lola writes.

Lola reads two module formats. The legacy layout keeps instructions at
`module/AGENTS.md`. An Agent Plugins 1.0 package, the default `lola mod init`
layout, declares its instructions as a manifest path under an extension
namespace; today the loader also falls back to `dev.getlola/AGENTS.md` when
none is declared
([ADR: Agent Plugins Format](agent-plugins-format.md)).

### The targets do not agree with each other today

| Target        | Skills                      | Instructions              |
|---------------|-----------------------------|---------------------------|
| `cursor`      | `.cursor/skills/`           | `.cursor/rules/` (`.mdc`) |
| `claude-code` | `.claude/skills/`           | `CLAUDE.md`               |
| `opencode`    | `.opencode/` directories    | `AGENTS.md`               |
| `gemini-cli`  | `GEMINI.md` managed section | `GEMINI.md`               |

At user scope `claude-code` writes `~/.claude/CLAUDE.md` and `gemini-cli`
writes `~/GEMINI.md`.

The Cursor target already works the way this ADR proposes.
`CursorTarget.generate_instructions` writes one `.mdc` file per module with
`alwaysApply: true`, in a directory Lola owns, and `remove_instructions` deletes
that file. Nothing of the user's is touched.

## Decision

**Lola writes generated content only into paths it owns. Module instructions are
opt-in, and reach each assistant through that assistant's own documented
always-on mechanism.**

Commands, agents and MCP servers are unaffected. Skills are unaffected on every
target except `gemini-cli`, whose skills move out of `GEMINI.md` into the skills
directory Gemini CLI now discovers (section 5).

### 1. The module's instructions file is renamed

`module/AGENTS.md` becomes `module/INSTRUCTIONS.md`.

`AGENTS.md` is an ecosystem convention with an established meaning — a file
hosts themselves read. `INSTRUCTIONS.md` carries no prior meaning, so nobody
creates one by accident: presence *is* intent, and no manifest flag is needed to
express it. After the rename a module's `AGENTS.md` means what the ecosystem
says it means — instructions for agents working *on the module* — and a module
shipping both files is correct.

The rename applies only to the file Lola reads from a module. OpenCode's own
`AGENTS.md` is a host file, not a module source, and the rename does not affect
it.

The rename covers the legacy layout. In an Agent Plugins package the
instructions source is the path its manifest declares, as the Agent Plugins
Format ADR defines; sections 3 to 6 apply to that content unchanged. A
`dev.getlola/AGENTS.md` that the manifest does not declare is not delivered;
see Implementation Notes.

### 2. A legacy `AGENTS.md` is not injected

A legacy-layout module with `module/AGENTS.md` and no `module/INSTRUCTIONS.md`
warns at `lola mod add` and at `lola install`, names the rename as the fix,
and installs its skills, commands and agents normally. Its instructions are
not installed.

There is no override flag. The fix is renaming one file; an override would be a
permanent feature preserving a transitional ambiguity.

### 3. Each target uses its own always-on mechanism

Where `INSTRUCTIONS.md` is delivered, and whether a user-authored file is
touched:

- `cursor`: `.cursor/rules/<module>-instructions.mdc` with
  `alwaysApply: true`. No user file.
- `copilot-cli`: `.github/instructions/<module>.instructions.md` with
  `applyTo: "**"`. No user file.
- `copilot-vscode`: inherited from `copilot-cli`. No user file.
- `opencode`: `.opencode/lola/<module>.md` plus a glob in `opencode.json`.
  No user file.
- `openclaw`: not delivered; install reports it. No user file.
- `claude-code`: `.claude/lola/<module>.md` plus one `@` line in `CLAUDE.md`.
- `gemini-cli`: `.gemini/lola/<module>.md` plus one `@` line in `GEMINI.md`.

`cursor` already behaves this way and does not change. The `opencode.json` write
follows the precedent Lola already sets when merging MCP server entries into
`.vscode/mcp.json` and the other host MCP configs: machine-owned
configuration, not prose. OpenCode documents
the `instructions` array, including globs, as the supported way to load extra
instruction files. Because Lola's entry is a glob, it is added when the first
instructions-shipping module is installed and removed when the last one is
uninstalled, and is not rewritten for the modules in between. Other entries in
the array are left untouched.

`openclaw` paths are relative to an OpenClaw workspace, not to a project
repository. Lola resolves the workspace from `lola install --workspace`: no
value means `~/.openclaw/workspace`, a bare name selects
`~/.openclaw/workspace-<name>`, a path is used as given, and `--scope user` is
the default workspace. Within a workspace OpenClaw injects always-on content
only from fixed bootstrap files at the workspace root (`AGENTS.md`, `SOUL.md`
and similar), which the user owns. Its bundled `bootstrap-extra-files` hook can
load more, but only after the user enables it in OpenClaw's own configuration,
and only files with those same basenames. Neither is a Lola-owned path that
loads without user action, so `openclaw` continues to deliver no instructions,
as it does today. Its skills are unaffected.

A target that cannot deliver instructions reports that at install time. No
target writes an owned file that nothing will read.

### 4. `claude-code` and `gemini-cli` get a pointer, not an index

Both hosts resolve `@path` imports inside their context file. The reference is
one `@` line per instructions-shipping module, inside the existing markers:

```markdown
<!-- lola:instructions:start -->
@.claude/lola/git-module.md
<!-- lola:instructions:end -->
```

`gemini-cli` uses the same shape in `GEMINI.md`, pointing at
`.gemini/lola/<module>.md`.

There is no generated `index.md`. #148 is about content churn — the tracked file
changing when a skill or a version changes — and direct lines already prevent
that, because a line changes only when the set of instructions-shipping modules
changes. An index would additionally absorb set churn, which is rare now that
instructions are opt-in, at the cost of a generated file, a resolution hop, and
a context file that no longer shows what it loads.

### 5. Scope rules

`claude-code` and `gemini-cli` instructions are **project scope only**. At
`--scope user` the pointer would have to go in `~/.claude/CLAUDE.md` or
`~/.gemini/GEMINI.md`, which Lola does not write, and writing the owned file
without the pointer would leave content nothing reads. Lola writes nothing and
says why. Skills installed at user scope are still found, because both hosts
read their user skills directory without being told.

`gemini-cli` skills are written to `.gemini/skills/`, or `~/.gemini/skills/`
at user scope, instead of a managed section of `GEMINI.md`. This requires
Gemini CLI v0.26.0 or later, the first release with Agent Skills enabled by
default; the minimum is recorded in the `gemini-cli` target's maintainer
documentation and in the user-facing target documentation. Lola never writes
loose skills into the shared `.agents/skills/` alias: Cursor, OpenCode,
OpenClaw and Gemini CLI all read it, so two targets installing into it would
share one directory and uninstalling one would remove skills the other still
expects.

That rule is about loose entries in a shared directory, not about the
`.agents/` tree. An Agent Plugins module that declares no `targets` installs by
default to the shared Agent Plugins location, `.agents/plugins/<name>/`, or
`~/.agents/plugins/<name>/` at user scope, following the example in section
9.1 of the Agent Plugins specification; that default is decided separately
(PR #243). There Lola owns the whole per-plugin directory: it is recorded with
the installation, nothing else writes inside it, and uninstall removes it as a
unit. Uninstalling one plugin cannot remove another's files, so the argument
against `.agents/skills/` does not apply, and `.agents/plugins/<name>/` is an
owned path under this ADR.

With that change no install or update adds content to a user-authored file at
user scope; the only user-level edits left are migration removing Lola's own
legacy blocks. The `gemini-cli` exception previously recorded here is
withdrawn. Dropping user-scope instructions for `claude-code` and `gemini-cli`
is a **breaking change**; see Negative Consequences.

### 6. No configuration is added

`--append-context` is deleted rather than aliased. No `instructions.mode` or
`instructions.targets` setting is introduced. With nothing written to a
user-authored file unless a module declares instructions, and only two targets
touching one at all, there is no knob worth offering.

## Rationale

- **The cheapest fix for redundant content is not to generate it.** The prior
  design answered "where should this content go" with indirection for every
  target. Verifying the hosts first showed every one of them discovers skills
  unaided, which removes the question rather than answering it.
- **A package manager owns its own namespace.** DNF does not append to
  `/etc/profile`; it installs into paths it can list, verify and remove.
- **The pattern is already in the codebase.** Cursor's `.mdc` approach is not a
  new design to be proven; it is in use today, and neither report names it.
- **Opt-in by naming beats opt-in by flag.** A file nobody creates by accident
  encodes intent without new configuration to document, discover or maintain.
- **Global scope is the sharpest edge.** A project-scoped write shows up in `git
  status`. Writing `~/.claude/CLAUDE.md` does not, and it affects work that has
  nothing to do with the module.
- **This is the same principle as extension sandboxing.** Host-mediated
  effects say an extension does not choose what gets written or where. Owning
  the namespace says the same thing about the host's own output.

## Consequences

### Positive Consequences

- A tracked `AGENTS.md`, `CLAUDE.md` or `GEMINI.md` stops changing when module
  versions change, so `lola sync` becomes usable in a shared repository
- Most modules stop consuming context on every turn for content their host
  already derives from skill frontmatter
- Uninstall deletes the module's owned file. Beyond that, `claude-code` and
  `gemini-cli` remove the module's one pointer line, and `opencode` removes its
  glob when the last instructions-shipping module goes. No uninstall has to
  find and cut module content out of a user's prose
- A module's `AGENTS.md` stops being ambient instructions inside
  `.lola/modules/`
- User scope stops leaking one project's context into every other project, and
  no install or update adds content to a user-authored file at user scope
- No new configuration surface is created

### Negative Consequences

- Breaking change for module authors: every module shipping `AGENTS.md` must
  rename it, and until it does, its instructions are silently not delivered —
  mitigated by a warning at both `mod add` and `install`, but it is still a
  behaviour change users did not ask for
- Behaviour change for existing installs: content currently inside a managed
  block has to be removed from files the user owns
- One more layer of indirection for a `claude-code` or `gemini-cli` reader,
  who must follow the pointer to see what a module contributes
- **Breaking change for `claude-code` and `gemini-cli`.** User-scope
  instructions, which both have today, are dropped: `--scope user` no longer
  writes `~/.claude/CLAUDE.md` or a global `GEMINI.md`, and reports that
  instructions are project scope only. On `lola update` and `lola uninstall`,
  migration removes Lola's old managed sections from those user-level files
  under the same rules as every other legacy block
- **Breaking change for `gemini-cli`.** Skills move from `GEMINI.md` to
  `.gemini/skills/` and `~/.gemini/skills/`, so Gemini CLI v0.26.0 or later is
  required; earlier releases cannot discover skills from a directory
- `openclaw` still receives no instructions
- Five delivery mechanisms to maintain and test instead of one, because each
  follows its host rather than a Lola convention

## Alternatives Considered

### Alternative 1: Keep inlining, add an opt-out flag

- Description: Leave the default and let anyone affected pass a flag.
- Pros: No migration, no behaviour change, smallest diff.
- Cons: Both reporters hit the problem before they knew a flag existed. A
  default that requires a flag to be safe is not a safe default.
- Reason for rejection: It addresses the complaint without addressing the cause.

### Alternative 2: Owned file plus pointer for every target

- Description: The previous form of this ADR. Every target gets
  `<owned>/lola/<module>.md` and a generated `index.md`, with a one-line pointer
  written into whichever user file the host reads.
- Pros: One mechanism, uniform across targets, no per-host special cases.
- Cons: Generalises a problem only `claude-code` and `gemini-cli` actually have,
  and still delivers skill listings no host needs — paying the indirection cost
  to solve a problem created by generating the content at all.
- Reason for rejection: Superseded by verifying host capabilities first.

### Alternative 3: Write to a single shared `lola.md` per project

- Description: One Lola-owned file for all modules, as #148 suggests.
- Pros: Very simple; one pointer, one file.
- Cons: Uninstalling one module means editing a file that holds several, which
  reintroduces the text-surgery problem inside Lola's own namespace.
- Reason for rejection: Per-module files remain the unit that gets created and
  deleted.

### Alternative 4: Never write user-authored files at all, including a pointer

- Description: Lola writes only its own directories and documents that the user
  must add the reference by hand.
- Pros: The strongest possible ownership boundary.
- Cons: Nothing works until a manual step is completed, and the failure is
  silent — the assistant simply behaves as though no module were installed.
- Reason for rejection: A package manager whose output does nothing until the
  user edits a file by hand is not finished. The decision above gets most of the
  benefit anyway: five of seven targets need no user-file write.

### Alternative 5: Drop instructions support entirely

- Description: Remove the concept. Modules ship skills, commands, agents and
  MCP servers only.
- Pros: Deletes the problem outright, and the most code.
- Cons: Always-on rules are a real category that skills cannot express — a skill
  loads when its description matches, whereas "line limit is 80 characters" must
  always apply. `cursor` supports this correctly today, so removal is a
  regression there.
- Reason for rejection: The category is legitimate; only its default was wrong.

## Implementation Notes

The migration is one-way removal. There is no new mechanism to migrate into, so
the previous four-phase dual-write sequence does not apply.

Removal runs during `lola install`, `lola update` and `lola uninstall`.
Uninstall is included because a user can upgrade Lola and uninstall a module
without ever running install or update, and the new uninstall path only knows
about the new owned files and references. This is Lola deleting
content Lola wrote, delimited by markers Lola placed, and it is reversible
through version control like any other write.

The file to clean is resolved from each installation record's stored scope
using the legacy destination, not the new one: the project's file for
`scope: project`, and the user-level file the old code wrote for
`scope: user` (`~/.claude/CLAUDE.md` for `claude-code`). For `gemini-cli` at
`scope: user` both `~/GEMINI.md`, where current code writes, and
`~/.gemini/GEMINI.md`, Gemini CLI's documented global file, are checked; a
file without Lola's markers is left alone, so checking both is safe.

A block is compared against what Lola would have generated from the
project-local module copy at `.lola/modules/<name>/`, using the record's stored
options, because that copy is the source the block was generated from.
Comparison therefore runs before anything replaces or deletes that copy:
before update refreshes it from the registered module, and before uninstall
removes it. Comparing against the refreshed copy would mark every
block from a since-changed module as hand-edited. For each module block inside
a `lola:instructions` section, and for each module's entry in `gemini-cli`'s
`lola:skills` section:

| Condition                              | Action                   |
|----------------------------------------|--------------------------|
| Block matches what Lola would generate | Remove                   |
| Block differs from generated content   | Keep, report hand-edited |
| No project-local copy to compare with  | Keep, report             |
| Module content present, markers absent | Leave file, report       |
| Last block removed                     | Remove enclosing section |

Reading a legacy `AGENTS.md` in order to compare against it is permitted; Lola
declines to inject it, not to look at it.

Where markers were removed by hand, the content is indistinguishable from the
user's own writing. Lola leaves the file untouched and reports the file and
module, rather than guessing which lines were once its own. Deleting unmarked
lines risks destroying the user's work; leaving a duplicate is visible and
recoverable.

`--append-context` is recorded in installation records as well as accepted on
the command line, so removing it means handling stored state, not only a CLI
argument. The update path that replays a stored value today is deleted; the
stored value is read only as a comparison input during migration.

Two facts were confirmed while revising this decision. Neither changes it.

1. `BaseAssistantTarget.generate_instructions` returns `False` by default and
   `openclaw` does not override it, so `openclaw` delivers no instructions today
   and its declared `.openclaw/instructions.md` path is unused. That remains
   true; the unused path is removed.
2. Gemini CLI's global context file is `~/.gemini/GEMINI.md`, not the
   `~/GEMINI.md` Lola writes today. Under this decision Lola writes neither;
   both remain only as legacy paths migration cleans.

One fact is still open and is confirmed before the code depending on it is
written: whether Copilot in VS Code loads skills is confirmed for `copilot-cli`
but not for `copilot-vscode`. Since the latter subclasses the former, both write
identical paths either way; only the documented exception list changes.

**Agent Plugins instructions must be declared.** The accepted Agent Plugins
Format ADR and the shipped loader fall back to `dev.getlola/AGENTS.md` when
`plugin.json` declares no instructions path. That conflicts with this ADR, and
this ADR governs delivery.

Modules arrive from the Internet, and Lola must not pull in anything unexpected
that will control agent behaviour. Instructions are therefore delivered only
when they are explicitly declared, so that they can be reviewed: a path
declared in `plugin.json`, or `INSTRUCTIONS.md` in the legacy layout. A file is
never picked up merely because it is present. This is the same
presence-is-not-intent rule section 1 applies to the legacy layout, and it also
keeps an undeclared `AGENTS.md` copied into `.lola/modules/<name>/` from being
treated as content Lola delivers.

The default `lola mod init` scaffold already declares
`./dev.getlola/AGENTS.md` in `plugin.json`, so scaffolded packages are
unaffected. The Agent Plugins Format ADR and the loader need a follow-up change
to drop the implicit fallback; this PR does not change them.

## References

- Issue #158 — excessive material written into `AGENTS.md` and friends
- Issue #148 — `lola sync` opt-out of changes to `AGENTS.md`
- [ADR: Extension Architecture](extension-architecture.md) — target
  extension kind
- [ADR: Agent Plugins Format](agent-plugins-format.md) — package layout and
  the `dev.getlola` instructions declaration
- [Agent Plugins specification](https://agent-plugins.org/specification) —
  section 9.1, the shared `.agents/plugins/` location
- ADR: Extension Sandboxing, proposed separately — the same ownership
  principle applied to extension effects
- [Design: Assistant File
  Ownership](../dev-guide/design/assistant-file-ownership.md) — layout,
  reference syntax and migration detail
- `src/lola/targets/base.py` — current managed-section writers and MCP config
  merging
- `src/lola/targets/cursor.py` — the owned-file pattern this ADR generalises
- `src/lola/targets/openclaw.py` — current OpenClaw workspace resolution
- [Cursor agent skills](https://cursor.com/docs/context/skills)
- [OpenCode rules](https://opencode.ai/docs/rules/) and
  [skills](https://opencode.ai/docs/skills/)
- [Copilot custom instructions support][copilot-instructions]
- [Copilot CLI agent skills][copilot-cli-skills]
- [Gemini CLI context files][gemini-context]
- [Gemini CLI Agent Skills discovery tiers][gemini-skills]
- [Gemini CLI changelog][gemini-changelog] — v0.23.0 and v0.26.0
- [OpenClaw agent workspace][openclaw-workspace] and
  [bundled hooks][openclaw-hooks]
- [OpenClaw skills loading order][openclaw-skills]

[copilot-instructions]: https://docs.github.com/en/copilot/reference/custom-instructions-support
[copilot-cli-skills]: https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills
[gemini-context]: https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md
[gemini-skills]: https://geminicli.com/docs/cli/skills/#discovery-tiers
[gemini-changelog]: https://github.com/google-gemini/gemini-cli/blob/main/docs/changelogs/index.md
[openclaw-workspace]: https://docs.openclaw.ai/concepts/agent-workspace
[openclaw-hooks]: https://docs.openclaw.ai/automation/hooks/bundled-hooks
[openclaw-skills]: https://docs.openclaw.ai/tools/skills
