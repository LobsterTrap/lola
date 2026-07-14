# Provider Architecture — Design

Paired with [ADR: Provider Architecture](../../adr/provider-architecture.md).

This document records the host/provider layout agreed for the Go port. It is
intentionally more detailed than the ADR while still leaving protobuf field
lists and release packaging to implementation.

## Goals

- Let contributors add a new assistant or fetch transport by dropping a
  `lola-provider-<name>` binary (plus YAML manifest) into `~/.lola/providers/`
- Make `lola install <module> -a <target-id>` resolve that target provider and
  have **the provider** write assistant files (including managed-section edits)
- Ship every default target and source as a real external provider under
  in-repo `providers/` so defaults are the contributor template
- Start with `target` + `source`; extend the same pattern for `repo`, `runtime`,
  and `scan` later

## Non-goals (for this design)

- Community provider repository layout (decide later)
- Describe-result caching (not needed at expected scale)
- Non-Go provider SDKs (document possibility only)
- Full protobuf schemas (defined when `pkg/provider` is implemented)

## Architecture

```text
┌───────────┐   discover / launch / orchestrate    ┌──────────────────────┐
│ lola host │ ───────────────────────────────────► │ lola-provider-<name> │
│           │ ◄── gRPC via hashicorp/go-plugin ─── │  (target | source)   │
└───────────┘                                      └──────────────────────┘
      │                                                       │
      │ installed.yml, CLI                                    │ writes under
      ▼                                                       ▼
 ~/.lola/                                     modules / project / user roots
```

**Host responsibilities**

- Discover manifests under `~/.lola/providers/`, resolve their binaries, and
  launch providers with `hashicorp/go-plugin`
- Call `Describe` and kind-specific RPCs
- Pass explicit filesystem roots in requests
- Update the installation registry (`installed.yml`) from successful results

**Provider responsibilities**

- Implement `Describe` (reports `id`, `kind`, version, health, capabilities)
- Perform kind-specific work, including **all filesystem writes** for that work
- Stay within the roots passed by the host

## Naming and discovery

| Item | Convention |
|------|------------|
| Binary | `lola-provider-<name>` (Windows: `lola-provider-<name>.exe`) |
| Manifest | `lola-provider-<name>.yml` **or** `.yaml` (not both) |
| Install dir | `$LOLA_HOME/providers/` (default `~/.lola/providers/`) |
| CLI id | From `Describe.id` (e.g. `"cursor"` → `-a cursor`) |
| Kind | From `Describe.kind` only |

Identity for CLI selection comes from `Describe.id`. The binary name is only a
packaging convention; it need not equal the CLI id. Discovery starts from
sidecar manifests; each manifest's `executablePath` must resolve to an
on-disk binary next to it (platform suffix allowed).

### Manifest (YAML)

```yaml
metadata:
  description: Cursor assistant target
  version: 0.1.0
executablePath: lola-provider-cursor
sha256: "<sha256-of-binary>"
configuration: []
```

### Discovery algorithm

1. Scan `$LOLA_HOME/providers/` for manifests named `lola-provider-*.yml` or
   `lola-provider-*.yaml`
2. If both `.yml` and `.yaml` exist for the same stem (e.g.
   `lola-provider-cursor`) → reject with error
3. Resolve `executablePath` to a binary beside the manifest (accept platform
   suffixes, e.g. `lola-provider-cursor` → `lola-provider-cursor.exe` on
   Windows); missing/non-executable → reject
4. When `sha256` is set, verify before launch; mismatch → reject
5. Launch and call `Describe` to obtain `id`, `kind`, health, and version
6. Reject providers with empty `Describe.id`, or duplicate `id` values among
   discovered providers

Orphan binaries (no matching manifest) are ignored. The manifest is the
registration record; the binary is what it points at.

`Describe` is cheap once connected; cost is process spawn + go-plugin handshake
(typically tens of milliseconds per provider on a laptop). At small provider
counts, launch-on-demand without a cache is fine. Resolving `-a <id>` and
listing targets requires `Describe` (or a prior inventory pass) so the host
knows each provider's `id` and `kind`.

## Provider kinds

### v1: `target` and `source`

Shared:

- `Describe(ctx) → { id, kind, version, healthy, capabilities, config schema }`  
  `id` is the stable CLI selector (e.g. `cursor` for `-a cursor`).

**SourceProvider** — fetch / materialize modules:

- `Fetch(ctx, req) → result`  
  Host passes source URI/ref and a destination under `$LOLA_HOME/modules/`
  (default `~/.lola/modules/<module-name>`). Provider writes the module tree
  there.

**TargetProvider** — install / uninstall assistant files:

- `Install(ctx, req) → result`  
  Host passes module path, project/user roots, selection, scope. Provider
  writes assistant files however that target requires.
- `Uninstall(ctx, req) → result`  
  Provider removes or reverts what it owns under the given roots.

`Update` may reuse `Install` (replace) in v1; a dedicated RPC can be added later
if needed.

### Extending with new kinds

When a feature needs a new kind (e.g. `repo`, `runtime`, `scan`):

1. Add a typed Go interface + gRPC service for that kind
2. Teach the host to filter providers whose `Describe.kind` matches
3. Add default and/or community providers named `lola-provider-<name>`
4. No change to discovery directory, manifest shape, or go-plugin lifecycle

## Install flow

`lola install <module> -a cursor`:

1. Resolve module identity (local registry / repo config)
2. If content is not local, select a `source` provider and call `Fetch` into
   `$LOLA_HOME/modules/`
3. Resolve `-a cursor` to the provider whose `Describe.id == "cursor"` and
   `Describe.kind == target`
4. Call `Install` with module path and scope roots
5. On success, host records the installation in `installed.yml`

Uninstall mirrors step 3–4 with `Uninstall`, then updates the registry.

## Repository layout

```text
providers/
  target/
    claude-code/       # builds lola-provider-claude-code
    cursor/
    gemini-cli/
    openclaw/
    opencode/
    …
  source/
    git/               # builds lola-provider-git
    zip/
    tar/
    folder/
    …
pkg/provider/          # public SDK: Serve(), interfaces, protos, client helpers
internal/provider/     # host discovery, launch, orchestration
```

All shipped built-in targets and sources are real providers under `providers/`.
That tree is the contributor model.

Package names may adjust with the Go scaffold; keep the public SDK vs host
internal split.

## Authoring language

- Shipped defaults and documentation examples are **Go**
- Providers call something like `provider.Serve(impl)` in `main` (ComplyTime-shaped)
- The wire protocol is gRPC, so other languages are possible in principle
- Point authors at existing go-plugin ecosystems for non-Go patterns:
  - [hashicorp/go-plugin](https://github.com/hashicorp/go-plugin) (examples, gRPC)
  - [ComplyTime providers](https://github.com/complytime/complytime-providers)
  - HashiCorp tools that embed go-plugin (Terraform/Vault provider model)

## Error handling

| Case | Behavior |
|------|----------|
| Unreadable / invalid manifest | Skip provider; warn |
| Both `.yml` and `.yaml` for same stem | Reject that provider; error |
| `executablePath` missing / not executable | Reject provider; error |
| sha256 mismatch | Do not launch; error |
| Spawn / `Describe` failure | Unhealthy; exclude from selection |
| Empty or duplicate `Describe.id` | Reject provider; error |
| Unknown `-a` id | Error; list known target ids |
| Orphan binary (no manifest) | Ignore |
| No source provider for URI | Error with install/add hint |
| RPC / provider failure | Fail the CLI command; surface provider message |
| Partial writes | No host-invented rollback; providers should be idempotent; `Uninstall` is recovery |
| Protocol version mismatch | Human-readable too old/new error |

Providers must not write outside host-supplied roots (contract). Stronger
enforcement can be added later.

## Testing

**Host**

- Unit: discovery (manifest-first), manifest parse, sha256 reject, dual-extension
  conflict, missing binary, duplicate ids
- Integration: test provider binaries implementing go-plugin + minimal RPCs
- CLI: temp `LOLA_HOME` + project dir through `install` / `uninstall`

**Default providers**

- Table-driven / golden tests per target and source under temp roots
- One e2e path using a ship-like `~/.lola/providers/` layout

## Relationship to Go migration

Adding `hashicorp/go-plugin` (and protobuf/gRPC as required by that stack) is an
intentional exception to the Go migration ADR's stdlib-first dependency rule.
The value is ComplyTime alignment, isolation, and a single contributor-facing
provider model.

## Open implementation items

- Exact protobuf messages and go-plugin handshake / protocol version numbers
- How releases copy `providers/` build artifacts into user `~/.lola/providers/`
- Whether `configuration` in manifests drives interactive prompts in v1
- Community provider distribution (separate repo vs only local drop-in)
