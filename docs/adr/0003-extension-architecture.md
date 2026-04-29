# ADR-0003: Extension Architecture

**Status**: Proposed
**Date**: 2026-04-28
**Authors**: Igor Brandao
**Reviewers**:

## Context

Lola's current Python implementation has hardcoded registries for assistant targets (`TARGETS` dict in `targets/__init__.py`) and source handlers (`SOURCE_HANDLERS` list in `parsers.py`). Adding support for a new AI assistant or a new module source type requires modifying the core codebase. As the AI assistant ecosystem grows rapidly — with new assistants, agent frameworks, skill registries, and security scanning needs emerging regularly — this hardcoded approach does not scale.

We need an extension system that allows any developer to add support for new assistants, catalogs, runtimes, source transports, and security scanners without forking or modifying the Lola core binary.

## Decision

Introduce a formal extension system with 5 extension kinds, YAML manifests, and a language-agnostic communication protocol.

**Extension kinds**:

| Kind | What it extends | Built-in examples |
|------|----------------|-------------------|
| `target` | Where skills are installed (assistant file formats and paths) | claude-code, cursor, gemini-cli, openclaw, opencode |
| `repo` | Where skills are discovered (catalogs and registries) | yaml-catalog, oci-registry |
| `runtime` | Where skills are executed (agent framework environments) | — (future) |
| `source` | How skills are fetched (transport protocols) | git, zip, tar, folder, oci |
| `scan` | How skills are validated (security scanning) | — (future) |

**Extension manifest** (`extension.yaml`):

```yaml
name: "Windsurf Target"
kind: target
description: "Adds Windsurf IDE as a Lola target"
executable: "lola-ext-windsurf"
version: "1.0.0"
author: "Community Member"
license: "Apache-2.0"
```

**Built-in vs external**:

- **Built-in extensions** are compiled into the Lola binary. They implement Go interfaces defined in `pkg/sdk/` and are registered at startup via factory maps. No manifest or discovery needed.
- **External extensions** live in the extension directory (default `~/.lola/extensions/`, configurable) with an `extension.yaml` manifest and an executable binary or script. They communicate with core via stdin/stdout. Any programming language that reads stdin and writes stdout can implement an extension.

**Extension protocol**: The initial protocol uses stdin/stdout for simplicity. The architecture is designed to support gRPC as a future transport option for extensions that need streaming, concurrent calls, or richer type safety. The extension interface abstractions in `pkg/sdk/` are transport-agnostic — switching from stdin/stdout to gRPC would not require changes to extension interfaces, only to the transport layer in `internal/extensions/`.

**Extension management**: `lola ext add|rm|ls|info` manages installed external extensions.

**Extensible kind system**: Adding a new kind in the future requires only: define a new interface in `pkg/sdk/`, add an implementation in `pkg/builtin/`, and register it in the factory map. No core architecture changes.

## Rationale

- **Language-agnostic**: External extensions can be written in bash, Python, Go, or any language
- **Process isolation**: External extensions run as separate processes, protecting core stability
- **Clean interface boundaries**: Go interfaces in `pkg/sdk/` define a stable, transport-agnostic contract
- **Forward-compatible**: New kinds can be added without architectural changes; gRPC transport can be added without changing extension interfaces

## Consequences

### Positive Consequences

- Community can add support for new assistants without forking Lola
- Custom skill catalogs (enterprise registries, community hubs) are addable as repo extensions
- Security scanning is pluggable via scan extensions
- Built-in extensions share the same interface as externals, ensuring consistency
- Extension directory is configurable for enterprise environments
- gRPC can be adopted as an additional transport without breaking existing extensions

### Negative Consequences

- External extensions have subprocess overhead compared to compiled built-ins
- Extension protocol must be versioned to avoid breaking changes
- Extension discovery adds startup cost (scanning directories)

## Alternatives Considered

### Alternative 1: Hardcoded handlers only
- Description: Continue adding new targets and sources directly to the core codebase
- Pros: Simple, no extension infrastructure needed
- Cons: Every new assistant requires a core release; community cannot contribute independently
- Reason for rejection: Does not scale with the growing AI assistant ecosystem

### Alternative 2: Shared library plugins (.so files)
- Description: Extensions as dynamically linked shared libraries
- Pros: No subprocess overhead, full Go type safety
- Cons: Not language-agnostic (Go-only), platform-specific binary compatibility issues
- Reason for rejection: Language-agnostic extensions are a core requirement

### Alternative 3: gRPC as initial protocol
- Description: Use gRPC from day one instead of stdin/stdout
- Pros: Strongly typed, supports streaming, concurrent calls, well-established
- Cons: Higher initial complexity, requires protobuf compilation for extension authors
- Reason for deferral: Start with stdin/stdout for simplicity; gRPC is a planned future transport. The interface layer is designed to support both.

## Implementation Notes

See paired design document: `docs/dev-guide/design/extension-architecture.md`

## References

- [ADR-0002: Go Migration](0002-go-migration.md) — prerequisite decision
- [Current Architecture](../dev-guide/architecture.md) — existing SourceHandler strategy pattern that extensions generalize
