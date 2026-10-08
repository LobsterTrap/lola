# Claude Code Adapter

----
> 🦾 Written with LLM assistance [claude-opus-5]
> 💪 Reviewed by a human before submission
----

Implementation detail for
[ADR: Polyglot Format Handling](../../adr/polyglot-formats.md), and the first
adapter written under it. The ADR owns the decision and
[polyglot-formats.md](polyglot-formats.md) owns the IR, normalisation,
precedence and the export pipeline. This document owns Claude Code's field
mappings and what an export to Claude's formats may and may not claim.

Every shape below was read from installed packages rather than from a
specification, so treat it as an observation of the format in use.

The validation source is Lola's vendored copy of the schema. The `$schema`
value that `marketplace.json` carries,
`https://anthropic.com/claude-code/marketplace.schema.json`, is informational
only: as of 2026-10-08 it redirects to `www.anthropic.com` and returns 404.
Point the vendored copy at an upstream URL only once one is confirmed live.

## Package manifest

`.claude-plugin/plugin.json`. Observed across 26 installed plugins:

| Field | Seen in | Maps to |
|-------|---------|---------|
| `name` | 26 / 26 | module identity |
| `description` | 26 / 26 | module description |
| `author` | 26 / 26 | object with `name`, optional `email` |
| `version` | 9 / 26 | module version; absent means unversioned |
| `homepage` | 3 / 26 | metadata only |
| `repository` | 2 / 26 | metadata only |
| `license` | 2 / 26 | metadata only |
| `keywords` | 2 / 26 | search terms |

No observed plugin declared component paths. Commands, agents and skills are
found by convention, which is how Lola already discovers module content, so
discovery needs no new mechanism — only the directory names Claude Code uses.

Absent fields are the common case rather than the exception. Two thirds of real
plugins carry no `version`. Treat everything but `name` as optional and do not
reject a manifest for omitting metadata.

## Catalog manifest

`.claude-plugin/marketplace.json`. Top-level keys observed: `$schema`, `name`,
`owner`, `description`, `plugins`, `renames`.

Each entry in `plugins` carries `name`, `description`, `author`, and a `source`,
with optional `category` and `homepage`. In the official catalog of 286 entries,
`source` takes three shapes:

- `{"source": "url", "url": ...}` — 150 entries. Fetch from a URL; Lola's
  url / archive handler.
- `{"source": "git-subdir", "url", "path", "ref", "sha"}` — 83 entries. A
  subdirectory of a git repo at a pinned ref; Lola's git handler with
  `#subdirectory=`.
- Bare string — 53 entries. Shorthand for a URL; Lola's url handler.

All three map onto source handling Lola already has. `git-subdir` is the one
worth care: it carries both a mutable `ref` and a `sha`, and the `sha` is the
integrity pin. Recording it is only honest if it was checked, so the fetch
must verify it. There is one rule, and it checks both fields:

1. Resolve the `ref` to a commit.
2. If that commit is not the `sha`, abort the add before scan, cache write or
   install. A catalog whose `ref` and `sha` disagree is inconsistent, and Lola
   does not pick one for it.
3. Otherwise check out that commit, and write the `sha` to `.lola-origin`.

Fetching at the `sha` alone is not an alternative: it never checks the `ref`,
so it would install from an entry whose `ref` has moved without saying so. The
git source fetch must therefore take an expected SHA alongside the ref and
verify it; a fetch that accepts only a ref cannot meet this. `git-subdir`
also collides with the naming problem in issue #177, where several
`#subdirectory=` entries share one repository URL.

`renames` appears at catalog level and records plugins that changed name.
Reading it lets an installed module survive an upstream rename instead of
looking like a removal followed by an unrelated addition.

### From catalog entry to IR

The catalog is read by the `claude-marketplace` extension, not by this
adapter, so catalog-only fields need an explicit path into the module:

1. The `claude-marketplace` extension resolves the entry being installed and
   caches the catalog, including its top-level `renames` map.
2. At `mod add`, normalisation runs whichever package adapter won precedence.
   The catalog entry is not passed to it.
3. The `claude-marketplace` extension then writes the catalog-derived keys
   into the IR, whichever package adapter won, even `lola.yaml`:
   - the entry's `category` into `formats.claude-code.category`, which is what
     lets `category` round-trip
   - into `formats.claude-code.renamed_from`, only the names this module was
     formerly known as: the keys of `renames` entries whose value is this
     module's name

The extension owns exactly those two keys and the Claude package adapter
never writes them, so no package adapter writes under another format's id.
If `.claude-plugin/plugin.json` carries a field named `category` or
`renamed_from`, the catalog value wins and the add warns.

The catalog-wide rename map stays in the marketplace cache, which remains the
source used to resolve installs and updates. The IR never holds the whole
map, because a module has no business carrying other modules' history.

Unknown catalog-entry fields warn and stay in the marketplace cache. They are
not copied into the IR: a catalog entry describes a listing, not the package,
and the cache already holds it unchanged.

A module added from a path or URL, with no catalog entry, gets neither field.

## Comparison with Agent Plugins

Lola already reads the vendor-neutral format. The differences that matter here:

- Package manifest path
  - Agent Plugins: `plugin.json` at root
  - Claude Code: `.claude-plugin/plugin.json`
- Catalog manifest path
  - Agent Plugins: `.agents/plugins/marketplace.json`
  - Claude Code: `.claude-plugin/marketplace.json`
- Catalog top level
  - Agent Plugins: `interface`, `name`, `plugins`
  - Claude Code: `name`, `owner`, `description`, `plugins`, `renames`
- Per-entry extras
  - Agent Plugins: `policy.installation`, `policy.authentication`
  - Claude Code: `category`, `homepage`
- Extension mechanism
  - Agent Plugins: reverse-domain namespaces
  - Claude Code: none observed

The paths never collide, so detection is unambiguous. A package carrying both
catalogs is normal rather than a conflict: `superpowers` ships both.

Agent Plugins `policy` has no Claude equivalent. When emitting Agent Plugins
output, emit `formats.agent-plugins.policy` as stored, including
`installation` and `authentication`, when the module carries it. When the
block is absent, as for a module authored in Lola or imported from Claude,
there is nothing to derive it from, so omit it rather than defaulting it — a
wrong `authentication` value is worse than a missing one.

## Precedence

Claude's manifest sits third, behind Lola's own manifest and the Agent Plugins
root `plugin.json`. The rule itself and its reporting are general and live in
[polyglot-formats.md](polyglot-formats.md#precedence).

No surveyed package exercises the second-versus-third case. `superpowers`
ships the Agent Plugins *catalog* `.agents/plugins/marketplace.json`, not the
root package manifest `plugin.json`, so precedence never sees it. Use the
synthetic fixture described in
[polyglot-formats.md](polyglot-formats.md#testing): a package carrying both a
root `plugin.json` and `.claude-plugin/plugin.json`.

## Ingest and export mapping

The same table read in both directions. Ingest fills IR fields from the
manifest; `lola mod export --format claude-code` fills the manifest from the
IR. Here `claude-code` is the format id; that it matches the `claude-code`
target id is a coincidence of naming, not a link between the namespaces.

| IR field | `.claude-plugin/plugin.json` |
|----------|------------------------------|
| `name` | `name` |
| `description` | `description` |
| `version` | `version` |
| `author` | `author.name`, `author.email` |
| `license` | `license` |
| `homepage` | `homepage` |
| `repository` | `repository` |
| `keywords` | `keywords` |
| `formats.claude-code.category` | `category` (catalog entries) |
| `formats.claude-code.renamed_from` | catalog `renames` keys |
| `targets` | **no equivalent** |
| install hooks | **no equivalent** |

`category` has no first-class IR field because nothing outside Claude's catalog
uses it, so it round-trips through `formats.claude-code`. Everything above it
recurs across formats and is promoted. Both catalog rows arrive by the
[catalog-entry path](#from-catalog-entry-to-ir), not from `plugin.json`.

`targets` is the field that makes a Lola module install to five assistants, and
no client format has a home for it. An exported manifest is therefore a
narrower artifact than the module it came from, and export says so once rather
than implying fidelity it cannot deliver.

Claude's package manifest requires only `name`, so export to this format never
fails for a missing required field. Two thirds of the corpus omits `version`,
and an export that omits it is well-formed.

Claude declares no vendor extension mechanism, and Lola does not invent one.
See [polyglot-formats.md](polyglot-formats.md#what-export-does-not-claim) for
why.

## Schema handling

Do not fetch `https://anthropic.com/claude-code/marketplace.schema.json` at
install time. An installer that makes a network call to validate is an installer
that fails offline and leaks what is being installed.

Vendor a copy, validate against it, and refresh on a deliberate cadence. The
vendored copy is the validation source; the manifest's `$schema` value is
informational.

Unknown fields warn and do not count against schema acceptance, which is what
the Agent Plugins ADR already does and what lets a catalog add a field without
breaking every older Lola. Ignored by validation is not dropped by ingest:
the package adapter stores each unknown `.claude-plugin/plugin.json` field
verbatim under `formats.claude-code`, so a Claude round-trip keeps it. Unknown
catalog-entry fields stay in the marketplace cache instead; see
[catalog entry to IR](#from-catalog-entry-to-ir).

## Testing

Fixtures come from real packages. Hand-written examples encode assumptions
rather than testing them.

Adapter-specific cases:

- Every `source` shape in the official catalog resolves: bare string, `url`, and
  `git-subdir` with `ref` and `sha`
- A `git-subdir` entry whose `ref` resolves to its `sha` records the `sha` in
  `.lola-origin` alongside the `ref`
- A `git-subdir` entry whose `ref` resolves to a commit other than its `sha`
  aborts the add, and no cache entry or `.lola-origin` is written
- A manifest with only `name`, `description` and `author` is accepted, since
  that is two thirds of the corpus
- A catalog `renames` entry maps an installed module to its new name rather than
  reporting a removal, resolved from the marketplace cache
- A module added from a catalog records in `formats.claude-code.renamed_from`
  only the `renames` keys naming it, never the whole map
- `category` from the catalog entry survives a round-trip through
  `formats.claude-code`
- A catalog-sourced module whose `lola.yaml` or root `plugin.json` wins
  precedence still gets `category` and `renamed_from`, written by the
  `claude-marketplace` extension and not by the winning adapter
- An unknown catalog-entry field warns, stays in the marketplace cache, and
  does not appear in the IR
- Exporting `.claude-plugin/` from a module with `targets` set omits `targets`
  and reports it

Precedence, unknown-field handling, round-trip equality and the offline
validation requirement are general and tested against the list in
[polyglot-formats.md](polyglot-formats.md#testing). The 286-entry catalog is
the corpus for both.
