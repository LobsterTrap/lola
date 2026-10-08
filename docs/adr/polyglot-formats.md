# ADR: Polyglot Format Handling

**Status**: Proposed
**Date**: 2026-08-25
**Last Updated**: 2026-08-26
**Authors**: trevor-vaughan
**Reviewers**:

----
> 🦾 Written with LLM assistance [claude-opus-5]
> 💪 Reviewed by a human before submission
----

## Context

Issue #179 asks for native support for Claude Code's plugin and marketplace
formats, and states the alternative plainly: take the best ideas from Lola to
[APM](https://github.com/microsoft/apm) instead, which already consumes the
format. The issue names it as the single gap blocking adoption.

That alternative has since closed. The [Go Migration](go-migration.md) ADR
commits Lola to a Go single binary that imports skillimage's OCI packages and
sigstore-go as compiled-in libraries; APM is a Python codebase. What is left to
take from APM is its design work, not its runtime.

Nothing in `docs/` mentions `.claude-plugin` or `marketplace.json`, and nothing
in the source handles either. The gap is real. The question this ADR answers is
what shape the fix takes.

### The fan-out is the actual problem

One publisher shows what supporting every client currently costs. The
`superpowers` package, at 6.3.0, ships nine parallel manifests describing the
same plugin:

```text
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
.agents/plugins/marketplace.json
.codex-plugin/plugin.json
.cursor-plugin/plugin.json
.devin-plugin/plugin.json
.hermes-plugin/plugin.yaml
.kimi-plugin/plugin.json
gemini-extension.json
```

Nine hand-maintained descriptions of one artifact, drifting independently. This
is the problem Lola was built for, one layer up: it already exists to stop
authors writing the same context for Claude, Cursor and Gemini separately.
Packaging metadata has landed in the same state.

Answering #179 on its own terms produces a format ADR per client, which is that
same trap with Lola inside it. Adapting every format onto one internal
representation and rendering back out costs N+M instead of N×M. For the nine
manifests in one package, that is 18 pieces against 72 pairwise conversions.

### Documents this depends on

Two ADRs referenced below are in flight on their own branches and are not on
`main` yet. §6 needs the first for content template confinement; §5 needs the
second for why the verb is `export` and not `publish`.

| Reference            | Branch                     | Cited in |
|----------------------|----------------------------|----------|
| Extension Sandboxing | `adr/extension-sandboxing` | §6       |
| CLI Verb Conventions | `adr/cli-verb-conventions` | §5       |

The catalog extension kind is `marketplace`, the canonical name
[Extension Architecture](extension-architecture.md) now uses on `main`.

Merging this one first leaves those links dangling until the others land, so
merge them first or read the names as the ones they are taking.

### What `main` already ships

[ADR: Support the Agent Plugins Format](agent-plugins-format.md) is accepted
and implemented (#235). That is the baseline this ADR starts from, not future
work. It is described here as behaviour, since the Go implementation has to
reproduce it:

- A source root with `plugin.json` is read as an Agent Plugins 1.0 package and
  mapped onto the common module model. The manifest is validated locally
  against the closed v1.0.0 schema, and its `name` is the module identity.
- Unknown top-level manifest fields warn and are dropped. Unknown extension
  namespaces are dropped without a warning or validation, as the
  specification requires. Metadata such as `version`, `author` and `license`
  is validated but not kept on the module.
- Commands, agents and instructions are read from client namespaces in a
  fixed order, with `dev.getlola` authoritative. That includes
  `com.anthropic.claude` and `com.anthropic.claude-code` inside an Agent
  Plugins package. A Claude-only `.claude-plugin/` package is still not read.
- The mapping runs every time a module is loaded. Nothing normalised is
  written to the module cache.
- When `plugin.json` is present, the Agent Plugins path is taken before the
  `lola.yaml`/`lola.yml` lookup. A package carrying both therefore installs
  from `plugin.json`, and its `lola.yaml` install hooks are ignored.
- `lola mod init` writes an Agent Plugins package by default.
  `lola mod init --format lola` writes the legacy layout. `--format` there
  takes the format ids `agent-plugins` and `lola`.

Where this ADR changes any of that, the section that does so says so
explicitly.

### The formats are distinguishable

Package manifests sit on the top row, catalog manifests on the bottom:

| Agent Plugins                      | Claude Code                       |
|------------------------------------|-----------------------------------|
| `plugin.json` at root              | `.claude-plugin/plugin.json`      |
| `.agents/plugins/marketplace.json` | `.claude-plugin/marketplace.json` |

The catalogs identify themselves differently too. Agent Plugins keys on
`interface`, `name` and `plugins`; Claude Code on `name`, `owner`,
`description` and `plugins`. Per-entry, Agent Plugins carries a `policy` block
covering installation and authentication, where Claude Code carries `category`
and `homepage`. Claude Code also has a catalog-level `renames` map.

The paths never collide, so detection is unambiguous, and a package that ships
both is ordinary.

Package manifests in the wild are thin. Across 26 installed plugins, every one
carried `name`, `description` and `author`; nine carried `version`; three
`homepage`; two each `repository`, `license` and `keywords`. No plugin declared
component paths. Commands, agents and skills are discovered by convention,
which is close to how Lola already discovers module content.

## Decision

Lola adapts any packaging format in, normalises onto `lola.yml`, and renders
back out through target-aware templates.

```text
  ANY PACKAGE         NORMALIZE (once, at mod add)    EXPORT (on demand)

  .claude-plugin/ ─┐                                 ┌─→ .claude-plugin/
    plugin.json    │  ┌───────────────────────────┐  │
                   ├─→│ adapter → scan → lola.yml │──┼─→ .agents/plugins/
  plugin.json      │  │      + .lola-origin       │  │
    (Agent Plugins)│  └───────────────────────────┘  └─→ gemini-extension.json
                   │        ~/.lola/modules/             …
  lola.yml ────────┘
```

### 1. `lola.yml` is the intermediate representation

Every format Lola reads is adapted onto `lola.yml`. Lola keeps its own format
as the internal representation because `lola.yml` carries the target matrix
that installs a single module to five assistants, and no client format has a
field for it. Adopting a client format as the IR would cap what a Lola module
can say at whatever that client happens to support.

This is about the IR, not about authoring. The accepted Agent Plugins ADR made
an Agent Plugins package the default thing `lola mod init` writes, and this
ADR does not change that. An Agent Plugins package is one more input adapted
onto `lola.yml`, and `lola.yml` stays available to author in directly.

To hold what it reads, `lola.yml` grows the package-metadata layer it never
had: `version`, `author`, `license`, `homepage`, `keywords` and `repository`,
all optional. This is not new scope. The Claude adapter spec already maps
`version`, `author` and `license` outward as though they exist, while `Module`
in the source defines none of them. The dependency is already load-bearing and
undeclared.

Fields that recur across formats are promoted to first class. Vendor-specific
residue is preserved verbatim in a `formats` block keyed by format id, so
exporting that format restores it. Nothing is silently discarded on the way in.

**Change to shipped behaviour:** today, unknown `plugin.json` fields warn and
are dropped, unknown extension namespaces are dropped silently, and metadata
is validated and then discarded. Under this ADR metadata fills the IR's
metadata layer. Unknown fields and namespaces are kept verbatim under
`formats.agent-plugins` instead of being dropped. Their warnings stay as they
are, and they are still not validated or interpreted, which keeps the spec's
rule for unknown namespaces. This amends the "then ignored" in the Agent
Plugins ADR.

`formats` is a deliberate name, chosen over `x-format`. Foreign data held
inside Lola's own schema is a different thing from Lola injecting keys into
someone else's schema, and the name should not blur the two.

### 2. A target extension owns its client's format in both directions

The claude-code target extension knows how to read `.claude-plugin/plugin.json`
and how to emit it. One extension per client, ingest and export together.

This adds no sixth extension kind;
[Extension Architecture](extension-architecture.md)'s five stand as written,
and it is what the #200 / #201 / #202 series is building toward. A new tool
ships one bundle and gets read and write, rather than needing an adapter
registered in one place and a template in another.

Catalogs stay separate. `.claude-plugin/marketplace.json` is read by a
`marketplace` extension alongside the built-in `yaml-catalog`, because a
catalog describes many packages and a target describes one client. Claude Code
therefore contributes two extensions, one of each kind.

At `mod add`, after whichever package adapter won precedence has run, the
`claude-marketplace` extension writes the catalog-derived keys into the IR
itself: the entry's `category` into `formats.claude-code` so it round-trips,
and, of `renames`, only the names this module was formerly known as. It owns
those keys and no package adapter writes them. The catalog-wide rename map
and any unknown catalog-entry fields stay in the marketplace cache, which is
what resolves installs.

Adding a target must leave core unchanged: the adapter dispatch, the normalise
step, the IR schema and the export driver are untouched by target N+1. If a new
target does need a core change, that is a finding about the extension
interface, and it gets written up as one.

### 3. Normalisation happens once, at `mod add`

`lola mod add` runs the adapter once and writes the normalised `lola.yml` into
the module cache, replacing any `lola.yaml` or `lola.yml` copied from the
source so the cache entry holds exactly one Lola manifest. The source package
is never mutated implicitly. `lola mod convert` writes `lola.yml` into a
package in place, for publishers who want to migrate, and runs only when
asked. It writes no `.lola-origin`, which describes a cache entry rather than
a package, and writes nothing when Lola's own manifest already wins.

Normalising at add time settles the security boundary and the precedence
decision once. Doing it per read re-opens both on every operation.

**Change to shipped behaviour:** today the Agent Plugins mapping runs on every
module load, and nothing normalised is cached. This moves it to add time. It is
not the "Repackage on Import" alternative the Agent Plugins ADR rejected: the
package's content and layout are left as fetched, and only the normalised
manifest and `.lola-origin` are added to the cache copy.

### 4. Precedence is decided once and recorded

When a source root carries more than one recognised manifest, first match wins
and nothing merges:

```text
1. lola.yaml, else lola.yml      Lola's own
2. plugin.json (at root)         Agent Plugins
3. .claude-plugin/plugin.json    Claude Code
```

Merging would make the resulting module depend on which formats a package
happened to ship, which is not reproducible.

**Change to shipped behaviour:** today a root `plugin.json` is taken before
any `lola.yaml`/`lola.yml`, so a package carrying both loses its Lola install
hooks. This ladder puts Lola's own manifest first. Within rung 1, `lola.yaml`
still comes before `lola.yml`, as it does today.

The choice is reported on add and recorded in `.lola-origin` beside the
normalised manifest, along with the format id, the source `sha` where the
catalog supplied one and the fetched commit matched it, and the scan verdict.
Silent precedence is the failure mode here, and a file someone can read is a
better answer than a rule they have to remember.

### 5. Export is template-driven and explicit

`lola mod export --format <id>` renders the client manifests from the IR.
Format selection is required and `--all` exports every format Lola has a
registered format adapter for; neither form has a bare default, because the
point of an explicit verb is defeated by one that guesses which files to
write. `--all` is not limited to the module's `formats` map, which holds only
import residue: a module authored natively in Lola exports to every format.
Format ids
and the target ids in `targets` are separate namespaces, even where a name
such as `claude-code` appears in both, and an unknown format id is an error
that lists the valid ones.

Export never runs as a side effect of install. A package manager that rewrites
a developer's context files unasked is one they stop trusting.

`publish` is reserved for pushing to a catalog or registry. In npm and cargo it
means upload, Lola's target list includes OCI registries, and CLI Verb
Conventions (proposed separately) settles canonical names by what the surveyed
managers actually do.

Manifests render as data, not as interpolated text. A template produces a data
structure, Lola marshals it and validates against the vendored schema before
writing, so a template cannot emit a stray comma into another vendor's
`plugin.json`. Where a target format supports a reference, the exporter emits
the reference and leaves the content where it is.

Where a format requires a field the module does not carry, export refuses and
names both the field and the format. Lola does not synthesise a
value: a `0.0.0` version means something false downstream, and a wrong value is
worse than a missing one. Under `--all`, a refused format is reported with the
same message, the remaining formats still render, and the command exits
non-zero.

### 6. Untrusted templates run with an empty capability grant

Content templates are authored by publishers and arrive inside modules pulled
from catalogs. They run confined under Extension Sandboxing (proposed
separately) as tier-1 WASM with no granted capabilities. Target templates ship
with Lola or with a target extension and need no confinement.

One engine and one dialect throughout; the grant varies by origin. A second
reduced dialect for untrusted templates would be a second thing to write,
document and keep in sync with the first.

Extension Sandboxing's guarantee is that effects are host-mediated: an
extension returns a declarative plan and the host performs the effects after
checking them against granted capabilities. A content template containing
`{{ exec ... }}` therefore does not execute and get contained. It produces a
capability request the host refuses. The residual risk is a runtime escape
rather than template-level code execution.

## Rationale

- **Fan-out**: the argument was already in this ADR, applied only halfway. Nine
  manifests make the case for adapters and templates. They do not make the case
  for a tenth hand-written reader.
- **Reach, not identity**: reading more formats widens what Lola can install.
  Replacing its own would narrow what Lola can say. The two get confused.
- **The extension kinds already exist**: targets own their formats, and
  catalogs are a `marketplace` extension. Both are the first real exercises of
  the Extension Architecture interface, which is how third-party authors learn
  whether it generalises.
- **Export is the hard half**: APM already consumes Anthropic's format. Nine
  manifests in one repository is the evidence that consumption alone leaves the
  publisher's problem untouched.
- **Catalog network effect**: 286 plugins in one official marketplace is a
  corpus Lola can install from the day this lands, and a conformance corpus for
  the adapter.
- **One security boundary**: normalising once gives untrusted content a single
  way into Lola's representation, which is the one place the `scan` kind has to
  hook.

## Consequences

### Positive Consequences

- Every plugin in a Claude Code marketplace becomes installable by Lola,
  including to targets that are not Claude Code
- A publisher can maintain one source and export the client manifests, instead
  of hand-editing nine
- A new tool costs one extension bundle, where today it costs an ADR, a reader,
  an emitter and a release
- Round-trip fidelity becomes a test rather than a promise, because nothing is
  dropped silently on the way in
- Precedence and the scan verdict become inspectable facts in `.lola-origin`
  instead of behaviour someone has to reproduce to understand
- Extension Architecture's `scan` kind gets its first concrete justification

### Negative Consequences

- `lola.yml` grows a metadata layer, and every adapter that follows will put
  pressure on it again
- The `formats` passthrough is somewhere unmapped data can hide, and a bug there
  is invisible until an export produces the wrong file
- Anthropic's format is defined by a schema URL Lola does not control and can
  change without notice; validation has to tolerate unknown fields
- Exporting means Lola makes claims about other clients' formats, and a format
  Lola gets wrong produces a package that fails on someone else's tool
- Content templating cannot ship until Extension Sandboxing's tier-1 host
  exists, so #195 is gated on work this ADR does not own
- Three package manifests and two catalog formats is real surface area, and each
  one needs its own conformance tests

## Alternatives Considered

### Alternative 1: A format ADR per client

- Description: Answer #179 for Claude, then repeat for Codex, Cursor, Devin,
  Hermes and Gemini as each is asked for.
- Pros: Each decision is small, concrete, and driven by a real request.
- Cons: N×M work, and six documents that each re-decide precedence, lossiness
  and emission slightly differently. It is the drift this ADR complains about,
  reproduced inside Lola's own documentation.
- Reason for rejection: The original draft of this ADR was that document, and
  writing it made the general rule obvious.

### Alternative 2: Adopt Anthropic's format as Lola's native one

- Description: Replace `lola.yml`, as #179 asks.
- Pros: Immediate compatibility; no translation; the largest existing catalog.
- Cons: Lola's target matrix has no equivalent field, so the multi-assistant
  install that distinguishes Lola would have to move into a vendor extension of
  someone else's schema.
- Reason for rejection: It trades the reason Lola exists for the format's reach,
  and the reach is available by reading it.

### Alternative 3: Normalise lossily and report the drop

- Description: Map what maps, discard the rest, tell the user what was lost.
- Pros: A clean IR with no vendor baggage, and ingest behaves symmetrically with
  export.
- Cons: `import → export` is not identity, so a publisher who runs Lola over an
  existing `.claude-plugin/` silently loses `category` on the first cycle.
- Reason for rejection: Export exists so publishers can maintain one source. A
  converter that damages the thing it converts cannot sit in that loop.

### Alternative 4: Contribute to APM instead

- Description: #179's own stated alternative.
- Pros: Larger project, more momentum, one ecosystem rather than two. It has
  already shipped a lockfile, an install-time policy file and a generated
  conformance statement.
- Cons: APM is Python, installed as a bundled archive with a pip fallback that
  needs a Python 3.9 runtime. Lola is leaving Python for a Go binary that links
  skillimage and sigstore-go directly, and neither has a Go seam inside APM to
  contribute against.
- Reason for rejection: The two projects no longer share a runtime, so this
  stopped being a question of scope and became one of language. The design can
  still cross over, and it is borrowed below.

### Alternative 5: Treat `.claude-plugin/` as an Agent Plugins namespace

- Description: Read it through the `com.anthropic.claude-code` namespace the
  merged Agent Plugins ADR already handles.
- Pros: No new detection path.
- Cons: The namespace mechanism reads component paths *inside* an Agent Plugins
  package. A Claude-only package has no Agent Plugins manifest to hang them on.
- Reason for rejection: The two formats are siblings, not one nested in the
  other.

## Implementation Notes

Phase 1 is adapters, normalisation and target templates. It has no sandbox
dependency because the templates are Lola's own, and it closes #179.

Phase 2 is content templates. It cannot start before Extension Sandboxing's
tier-1 WASM host exists, and it closes #195.

Reading comes first within phase 1 and stands alone:

1. Adapt `.claude-plugin/plugin.json` onto the IR. Discovery by convention;
   unknown manifest fields warn, are preserved in `formats`, and never fail the
   parse.
2. Add `claude-marketplace`, a `marketplace` extension reading
   `.claude-plugin/marketplace.json`, covering all three `source` shapes. Build
   it against the extension interface with no core changes, and treat any core
   change it needs as a finding about Extension Architecture.
3. Implement precedence, write `.lola-origin`, and report the manifest used.
4. Export last, one format per change, starting with `.claude-plugin/` and
   the Agent Plugins layout. Lola writes the Agent Plugins layout today only
   as `mod init` scaffolding, not as an export from an existing module. The
   other five are named but not committed to here.

Conformance fixtures come from real packages. Hand-written examples encode the
assumptions they are supposed to test. The official catalog and its 286 entries
are the obvious corpus, and `superpowers` gives the adapter a package described
by two catalog formats at once, `.claude-plugin/marketplace.json` and
`.agents/plugins/marketplace.json`.

Precedence is the one rule the corpus cannot exercise. Every one of the 26
packages surveyed carries `.claude-plugin/plugin.json` and none carries a root
`plugin.json`, so no real package reaches the second rung of §4's ladder. That
fixture has to be constructed, and the test suite should say plainly that it is
synthetic.

The schema URL is not fetched at install time. Validate against a vendored copy
on a known cadence, the same way the Agent Plugins ADR validates locally
without retrieving its schema.

### Borrowed from APM

APM reached several of these problems first and published its answers. Five
carry over even though the codebase cannot:

1. **Export is an explicit verb.** APM writes agent files on `apm compile`,
   with `--target` choosing which, rather than as a side effect of install.
   §5 works the same way and for the same reason, with `--format` in place
   of `--target` because Lola's target ids name install assistants.
2. **Emit references where the format allows one.** For Claude Code, APM writes
   `@apm_modules/...` pointers instead of inlining bodies. Inlined content is
   the copy that drifts.
3. **Pin what the catalog already hands you.** `apm.lock.yaml` records an
   integrity hash per entry. Anthropic's `git-subdir` source carries `sha` for
   free; Lola verifies the fetched commit against it, aborts on mismatch,
   and `.lola-origin` records it.
4. **Scan what gets installed.** APM checks every install for hidden Unicode.
   Extension Architecture already reserves a `scan` kind and lists no
   implementation for it. Installing from a 286-entry catalog nobody here
   curates is the case that justifies the first one, because the payload is
   instructions to an agent and the agent is the thing that runs them.
5. **Publish a conformance statement, not a conformance claim.** APM generates
   `CONFORMANCE.md` from its own suite, marking each requirement active,
   skipped or xfail and writing out a waiver for every skip. Three package
   manifests and two catalog formats is the situation that needs the same
   discipline: say per format what is tested, and admit what is not.

Not borrowed here: APM's `apm-policy.yml` install policy. It is a good idea and
belongs to a different ADR than this one.

### Out of scope

- **Templating engine selection.** This ADR says template-driven, not `jet`.
  The engine is its own decision, gated behind dependency vetting.
- **Module identity across catalogs.** Stays with #177, which owns the case
  where several `#subdirectory=` entries share one repository URL.
- **Install policy.** See the note above.
- **The remaining five export formats.** Named, not committed.

## References

- Issue #179 — native support for the Claude Code plugin format
- Issue #195 — inline templating, closed by phase 2
- Issue #232 — Agent Plugins spec support, satisfied by
  [agent-plugins-format.md](agent-plugins-format.md)
- Issue #177 — module naming across catalogs
- Issues #200, #201, #202 — the target extension series this builds on
- [Claude adapter](../dev-guide/design/claude-adapter.md) — the first adapter
- [Polyglot formats design](../dev-guide/design/polyglot-formats.md) — IR
  schema, normalisation and capability grants
- [ADR: Support the Agent Plugins Format](agent-plugins-format.md) — the
  vendor-neutral sibling format
- [ADR: Extension Architecture](extension-architecture.md) — the `target`,
  `marketplace` and `scan` kinds this uses
- ADR: Extension Sandboxing, proposed separately — confinement for content
  templates
- ADR: CLI Verb Conventions, proposed separately — why `export` and not
  `publish`
- [ADR: Go Migration](go-migration.md) — why contributing to APM is closed
- [Agent Plugins specification](https://agent-plugins.org/)
- [APM](https://github.com/microsoft/apm) — the alternative named in #179, and
  the source of the lessons above
- [APM conformance](https://github.com/microsoft/apm/blob/main/CONFORMANCE.md)
  — the per-requirement statement the fifth borrowed lesson points at
