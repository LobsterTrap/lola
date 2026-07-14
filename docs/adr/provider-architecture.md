# ADR: Provider Architecture

**Status**: Proposed
**Date**: 2026-07-14
**Last Updated**: 2026-07-14
**Authors**: SecKatie
**Reviewers**:

## Context

Lola's current Python implementation has hardcoded registries for assistant targets
(`TARGETS` dict in `targets/__init__.py`) and source handlers (`SOURCE_HANDLERS` list
in `parsers.py`). Adding support for a new AI assistant or module source type requires
modifying the core codebase.

As the AI assistant ecosystem grows — new assistants, agent frameworks, skill
registries, and security scanning needs emerging regularly — this hardcoded approach
does not scale. We need a provider system that allows any developer to add support
for new capabilities without forking or modifying the Lola core binary.

This ADR is an **alternative** to the extension architecture proposed in
[PR #110](https://github.com/LobsterTrap/lola/pull/110) (YAML manifests and a
language-agnostic stdin/stdout protocol, with gRPC deferred). Both share the same
goal — pluggable targets/sources without forking core — but disagree on the host
transport. This document proposes adopting the ComplyTime-style
[hashicorp/go-plugin](https://github.com/hashicorp/go-plugin) model from the start.
The team should pick one direction; these PRs are not meant to merge together.

## Decision

Introduce a ComplyTime-style **host / provider** architecture for Lola:

- The `lola` binary is the **host**: it discovers providers, launches them, and
  orchestrates CLI flows (for example `lola install -a <target>`).
- Capabilities are **providers**: standalone binaries that speak gRPC through
  `hashicorp/go-plugin`.
- **All providers are external**, including shipped defaults. There is no special
  compiled-in path that contributors cannot copy.
- Default target and source providers live in this repository under `providers/`
  and are installed into `~/.lola/providers/` (via `LOLA_HOME`). A separate
  community provider repository may be adopted later; discovery still uses the
  same local directory.

**Provider kinds (v1 and later):**

| Kind | What it provides | v1 |
|------|------------------|----|
| `target` | Where skills are installed (assistant file formats and paths) | yes |
| `source` | How skills are fetched (transport protocols) | yes |
| `repo` | Where skills are discovered (catalogs and registries) | later |
| `runtime` | Where skills are executed (agent framework environments) | later |
| `scan` | How skills are validated (security scanning) | later |

**Conventions:**

- Binary name: `lola-provider-<name>` (for example `lola-provider-cursor`,
  `lola-provider-git`; on Windows, `lola-provider-cursor.exe`)
- CLI id and kind both come from the provider's `Describe` RPC (not the
  filename or manifest). Example: `Describe.id == "cursor"` for `-a cursor`.
  Binary naming is a packaging convention only; discovery must tolerate
  platform executable suffixes (e.g. `.exe`) when matching files.
- Sidecar manifest: YAML (`.yml` or `.yaml`) under `~/.lola/providers/`;
  discovery scans manifests and resolves each `executablePath` (platform
  executable suffixes such as `.exe` allowed)
- Defaults and docs are **Go-first**. The gRPC contract can be language-agnostic;
  see the design doc for pointers to other `go-plugin` ecosystems.

Detailed discovery rules, RPC shapes, install flow, error handling, and testing
are in the paired design document. New kinds extend the same pattern: add a
typed interface, teach the host to select that kind (and CLI id) from
`Describe`, and ship or document providers that implement it.

## Rationale

- **ComplyTime alignment**: Same subprocess + `go-plugin` + gRPC model used by
  `complyctl` providers — battle-tested and familiar to contributors in that
  ecosystem
- **Process isolation**: A panic or bug in a provider cannot crash the Lola host
- **Contributor model**: Shipped defaults are real providers under `providers/`,
  so adding `lola-provider-new-assistant` is copy-modify-install
- **Forward-compatible**: New kinds reuse discovery and launch; only interfaces
  and host call sites grow
- **Go-first, not Go-only**: Defaults are Go; gRPC leaves the door open for other
  languages without a second plugin system

## Consequences

### Positive Consequences

- Community can add assistants and sources without forking Lola
- `lola install -a <id>` resolves to a discovered target provider that performs
  the assistant-specific file writes (including managed-section edits)
- Built-in and third-party providers share one contract
- Host stays focused on CLI, registry, and orchestration

### Negative Consequences

- Subprocess and handshake overhead versus in-process code
- `hashicorp/go-plugin` (and protobuf/gRPC) are intentional dependency exceptions
  to the Go migration ADR's stdlib-first preference
- Protocol/version skew must be handled with clear user errors
- Provider inventory requires launching binaries for `Describe` (acceptable at
  expected small scale; no cache required initially)

## Alternatives Considered

### Alternative 1: Hardcoded handlers only
- Description: Continue adding targets and sources directly in the core binary
- Pros: Simple; no provider infrastructure
- Cons: Every new assistant needs a core release; community cannot contribute
  independently
- Reason for rejection: Does not scale with the AI assistant ecosystem

### Alternative 2: Shared library plugins (`plugin` stdlib / `.so`)
- Description: Load providers as in-process Go shared libraries from a directory
- Pros: No subprocess overhead; feels like normal Go interfaces
- Cons: Go-only; fragile across Go versions and platforms; weaker isolation
  (provider panic can take down the host)
- Reason for rejection: Isolation and a clear external contributor model matter
  more than in-process performance for Lola

### Alternative 3: Custom stdin/stdout JSON protocol ([PR #110](https://github.com/LobsterTrap/lola/pull/110))
- Description: Language-agnostic subprocess protocol with YAML manifests;
  gRPC deferred. Proposed as ADR “Extension Architecture” in #110.
- Pros: Minimal dependencies; easy bash/Python hello-worlds; smaller initial stack
- Cons: Reimplements versioning, logging, and handshake; diverges from ComplyTime
- Why this ADR prefers go-plugin: Align with ComplyTime/`hashicorp/go-plugin`
  instead of a bespoke protocol — open for discussion with #110’s authors

### Alternative 4: Kind or CLI id encoded in binary name or manifest
- Description: `lola-target-provider-<name>`, CLI id as binary-name suffix, and/or
  `kind:` / `id:` in the YAML manifest
- Pros: Kind/id visible without launching; cheap filtering
- Cons: Duplicates what `Describe` already returns; drift between name and
  reality; binary-suffix ids break on Windows (`.exe` becomes part of the id)
- Reason for rejection: Single source of truth for kind and CLI id is `Describe`;
  names stay simple (`lola-provider-<name>`)

## Implementation Notes

- Prerequisite: [ADR: Go Migration](go-migration.md)
- Paired design: [Provider Architecture design](../dev-guide/design/provider-architecture.md)
- v1 implements `target` and `source` providers only; `repo`, `runtime`, and
  `scan` are explicitly reserved for the same host/provider pattern
- Default providers in `providers/` replace in-process `TARGETS` /
  `SOURCE_HANDLERS` as the Go port lands

## Stretch Goals

- **Provider filesystem sandbox**: v1 relies on a contract that providers only
  write under host-supplied roots. A later hardening step may enforce that
  boundary with [nono-go](https://github.com/nolabs-ai/nono-go) (kernel
  Landlock / Seatbelt). Mechanism (host-wrap vs SDK `Apply`) is left open.

## References

- [ADR: Go Migration](go-migration.md)
- [Provider Architecture design](../dev-guide/design/provider-architecture.md)
- [hashicorp/go-plugin](https://github.com/hashicorp/go-plugin)
- [ComplyTime provider guide](https://complytime.dev/docs/projects/complytime-providers/provider-guide/)
- [complyctl](https://github.com/complytime/complyctl) / [complytime-providers](https://github.com/complytime/complytime-providers)
- [nono-go](https://github.com/nolabs-ai/nono-go) — candidate for later
  provider path sandboxing
- [Current Architecture](../dev-guide/architecture.md) — existing SourceHandler
  strategy pattern that providers generalize
- Alternative proposal: [LobsterTrap/lola#110](https://github.com/LobsterTrap/lola/pull/110)
  (extension architecture / stdin-stdout protocol)
