# Polyglot Format Handling

----
> 🦾 Written with LLM assistance [claude-opus-5]
> 💪 Reviewed by a human before submission
----

Implementation detail for
[ADR: Polyglot Format Handling](../../adr/polyglot-formats.md). The ADR owns
the decision; this document owns the IR schema, the normalisation algorithm,
the capability grants, and what round-trip means.

Per-format field mappings live with each adapter. The first one is the
[Claude adapter](claude-adapter.md).

## The intermediate representation

`lola.yml` is what every adapter produces and every template consumes.

| Field         | Type                       | Req | Notes                     |
|---------------|----------------------------|-----|---------------------------|
| `name`        | string                     | yes | module identity           |
| `description` | string                     | no  |                           |
| `version`     | string                     | no  | absent means unversioned  |
| `author`      | `name`, optional `email`   | no  | object                    |
| `license`     | SPDX identifier            | no  |                           |
| `homepage`    | URL                        | no  |                           |
| `repository`  | URL                        | no  |                           |
| `keywords`    | list of strings            | no  | search terms              |
| `targets`     | list of target ids         | no  | multi-assistant matrix    |
| `formats`     | map of format id to object | no  | passthrough residue       |

Only `name` is required. Two thirds of the 26 surveyed Claude plugins carry no
`version`, and a manifest is never rejected for omitting metadata.

`targets` is the field that makes a Lola module install to five assistants. No
client format has a home for it, which is the concrete reason the ADR declines
to adopt one of them as native.

### The `formats` passthrough

Fields an adapter reads but the IR has no first-class home for are preserved
verbatim, keyed by format id:

```yaml
formats:
  claude-code:
    category: workflow
    renamed_from: [old-name]
  agent-plugins:
    policy: {installation: ..., authentication: ...}
```

Rules:

- A component writes only under its own format id, and only the keys it
  owns. A format's package adapter and its `marketplace` extension share that
  id with disjoint keys; for `claude-code` the extension owns `category` and
  `renamed_from`. Any other cross-writing is a bug.
- Values are stored as read. No coercion, no defaulting, no normalisation.
  The one derived key is `claude-code.renamed_from`: the names this module was
  formerly known as, taken from catalog `renames` entries that name it. The
  catalog-wide map stays in the marketplace cache; see
  [catalog entry to IR](claude-adapter.md#from-catalog-entry-to-ir).
- The exporter for a format reads that format's block back and nothing else. A
  Claude export never consults the `agent-plugins` block.
- A field promoted to first class in a later release moves out of `formats` and
  the adapter stops writing it there. That is a breaking change to the cached
  representation and needs a cache version bump.

The name is `formats`, not `x-format`. The Claude adapter argues against
`x-`-prefixed vendor extensions in someone else's schema; foreign data held
inside Lola's own schema is a different thing, and the name should not blur the
two.

## `.lola-origin`

Written beside the normalised `lola.yml` in the module cache. Records what
normalisation decided, so none of it has to be re-derived or remembered.

```yaml
format: agent-plugins           # which adapter ran
manifest: plugin.json           # which package manifest won precedence
others_present:                 # competing package manifests, ignored
  - .claude-plugin/plugin.json
sha: 4f2c1ab...                 # catalog-supplied, verified at fetch
scan:
  extension: unicode-guard
  verdict: clean
  at: 2026-08-26T14:02:11Z
```

`sha` comes free from Claude's `git-subdir` source shape, which supplies it for
83 of the 286 entries in the official catalog. It is the integrity pin APM's
lockfile pays for separately, and it is only a pin if the fetched commit was
checked against it: the fetch aborts on mismatch, and `sha` is written only
after the check passes. The Claude adapter owns the
[verification steps](claude-adapter.md#catalog-manifest).

`others_present` lists only package manifests that lost precedence. Catalog
manifests such as `.agents/plugins/marketplace.json` are read by the
`marketplace` extension, take no part in precedence, and are not recorded
here.

## Normalisation

Runs once, on `lola mod add`. The source package is never mutated.

1. Fetch content into the module cache through the existing `source` handlers.
2. Detect every recognised manifest at the source root.
3. Apply precedence. Record the winner and the others in `.lola-origin`.
4. Run the `scan` extension over the fetched content. A failed scan aborts the
   add; the cache entry is not written.
5. Run the winning format's adapter. Mapped fields become IR fields; unmapped
   fields go to `formats` under that adapter's id. For a module added from a
   catalog, the `marketplace` extension then writes the catalog-derived keys
   it owns, whichever adapter won.
6. Write `lola.yml` and `.lola-origin` into the cache entry.

The cache entry holds exactly one Lola manifest, always named `lola.yml`.
Step 6 removes any `lola.yaml` or `lola.yml` copied from the source and writes
the normalised `lola.yml` in its place, so the `lola.yaml`-first lookup can
never find an un-normalised file beside the normalised one. Only the cache
copy changes; the source package does not.

`lola mod convert <path>` runs steps 2 through 5 against a package in place and
writes `lola.yml` into it. When Lola's own manifest already wins precedence
there is nothing to convert, so it says so and writes nothing; that also keeps
it from leaving a `lola.yml` beside a `lola.yaml` that would shadow it. It
reports the precedence decision but does not
write `.lola-origin`: that file describes a cache entry, and a converted
package is not one. It is the only operation that writes into a package Lola
did not fetch, and it runs only when invoked directly.

### Precedence

First match wins. Nothing merges.

```text
1. lola.yaml, else lola.yml      Lola's own
2. plugin.json (at root)         Agent Plugins
3. .claude-plugin/plugin.json    Claude Code
```

Rung 1 checks `lola.yaml` first and falls back to `lola.yml`. Both are Lola
manifests, so a package carrying either plus a foreign manifest keeps its
native settings, install hooks included. This preserves the current Python
implementation's lookup order (`src/lola/models.py`), which existing modules
rely on.

Merging would make the resulting module depend on which formats a package
happened to ship, which is not reproducible.

Report the choice on every add: `using .claude-plugin/plugin.json (2 other
manifests present)`. Someone who adds a Claude manifest to a package that
already has `lola.yml` and sees no change needs to be told why.

### Round-trip

`import <format>` followed by `export <format>` is **semantically identical**,
not byte-identical. Key order, indentation and whitespace are not preserved;
parsed-equal is the test.

Byte-identity is a promise the YAML and JSON serialisers cannot keep, and
asserting it produces a test that fails for reasons nobody cares about.

The claim covers **manifests only**. Skill bodies are copied verbatim and are
not part of it.

## Templates

Two populations, one engine, one dialect. The capability grant varies by
origin.

|              | Target templates        | Content templates               |
|--------------|-------------------------|---------------------------------|
| Author       | Lola, target extension  | module publisher                |
| Arrives from | the installed toolchain | a catalog                       |
| Renders      | IR → client manifest    | per-target skill markdown       |
| Grant        | trusted, host-side      | empty                           |
| Confinement  | none needed             | tier-1 WASM (see below)         |

Content-template confinement is Extension Sandboxing, proposed separately.

A content template that requests any capability is refused by the host, not
contained and then run. Extension Sandboxing's guarantee is that effects are
host-mediated: the template returns a plan, the host checks it against the
grant, and an empty grant means every requested effect is denied.
`{{ exec ... }}` in a catalog-sourced template produces a refusal, not a
subprocess.

Keeping one dialect and varying the grant puts the restriction in a single
enforcement point. A second reduced dialect for untrusted templates would be a
second thing to write, document and keep in sync with the first.

## Export

`lola mod export --format <id>` renders one format. `--all` renders every
format Lola has a registered format adapter for. Neither has a bare default.

`--all` does not consult the module's `formats` map. That map holds only
import residue, so a module authored natively in Lola has an empty one and
still exports to every format.

`--format` takes format ids only. Format ids (`claude-code`, `agent-plugins`)
name manifest formats; target ids in `targets` name the assistants a module
installs to. The namespaces are separate even though `claude-code` appears in
both, and `--all` never reads `targets`. An unknown id is an error that lists
the valid format ids:

```text
unknown format `cursor`. Valid formats: agent-plugins, claude-code
```

The render pipeline is structured, never textual:

```text
IR + formats[id]  →  template  →  data structure
                                       │
                                       ├→ marshal (JSON or YAML)
                                       ├→ validate against vendored schema
                                       └→ write
```

A template produces a data structure, so it cannot emit a stray comma into
another vendor's manifest. Invalid structure fails at marshal. Unknown fields
warn at validate and are written, because a client adding a field should not
break an older Lola.

Where a target format supports a reference, emit a reference rather than an
inlined copy. Inlined content is the copy that drifts.

### Required fields

Where a format requires a field the module does not carry, export refuses and
names both the field and the format:

```text
cannot export superpowers to codex: format requires `version`,
module has none. Set it in lola.yml or export to a format that
does not require it.
```

Lola does not synthesise a value. A `0.0.0` version means something false
downstream, and a wrong value is worse than a missing one.

Under `--all`, a refusal for one format does not stop the others. Each refused
format is reported with the message above, every other format still renders,
and the command exits non-zero so a script cannot mistake a partial export for
a complete one.

### What export does not claim

An exported manifest is a narrower artifact than the module it came from.
`targets` and install hooks have no home in any client format, and export says
so once rather than implying fidelity Lola cannot deliver.

Do not invent vendor extensions to carry what does not fit. An `x-lola-targets`
key in someone else's schema is a private convention wearing a standard's
clothes, and it will not survive their next schema revision.

## The adapter contract

A target extension supplies four things. Adding one leaves the adapter
dispatch, the normalise step, the IR schema and the export driver unchanged.

- **Ingest adapter** (manifest → IR): maps known fields, routes the rest to
  `formats[id]`.
- **Export template** (IR → manifest): returns a data structure, never text.
- **Target descriptor**: content paths, required fields, capability grant.
- **Conformance fixtures**: a real package and its expected round-trip.

Any core change a new target needs is a finding about the extension interface,
and belongs in a note on Extension Architecture rather than in a quiet patch.

## Testing

Fixtures come from real packages. Hand-written examples encode assumptions
rather than testing them. The official Claude catalog and its 286 entries are
the corpus; `superpowers` is the ready-made dual-catalog case, since it ships
both `.agents/plugins/marketplace.json` and `.claude-plugin/marketplace.json`
for the same package.

Precedence is the exception. All 26 packages surveyed carry
`.claude-plugin/plugin.json` and none carries a root `plugin.json`, so the
corpus never reaches the second rung of the ladder. Build that fixture by hand
and mark it synthetic.

- Precedence resolves to Agent Plugins for a package carrying both, reports the
  other, and records both in `.lola-origin` (synthetic fixture)
- Precedence resolves to `lola.yaml` over `lola.yml` and over any foreign
  manifest, keeping its install hooks
- Precedence is reported even when only one manifest is present
- A manifest carrying only `name`, `description` and `author` is accepted
- An unknown top-level field warns, lands in `formats`, and does not fail the
  parse
- Round-trip: `import claude → export claude` is parsed-equal, including the
  `formats` residue
- A component writing outside its own `formats` id, or a key it does not
  own, fails the test suite
- Adding a package with `lola.yaml` leaves a cache entry with only `lola.yml`,
  the normalised one, and no `lola.yaml`
- `mod convert` on a package whose own Lola manifest wins writes nothing
- Export to a format requiring an absent field fails and names field and
  format
- `--format` with an unknown id, including a target id that is not a format
  id, fails and lists the valid format ids
- `--all` exports every registered format and ignores `targets`
- `--all` on a native module with an empty `formats` map exports every
  registered format
- `--all` where one format lacks a required field reports that format with the
  refusal message, renders every other format, and exits non-zero
- Export of a module with `targets` set reports that `targets` was not carried
- A content template requesting any capability is refused
- `mod convert` writes `lola.yml`, writes no `.lola-origin`, and leaves every
  other file in the package untouched
- Adding a target extension leaves core unchanged
- Validation runs with no network access

Per-format coverage is published as a generated conformance statement rather
than asserted in prose: each requirement marked active, skipped or xfail, with
a written waiver for every skip.
