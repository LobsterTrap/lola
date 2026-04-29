# ADR-0002: Go Migration

**Status**: Proposed
**Date**: 2026-04-28
**Authors**: Igor Brandao
**Reviewers**:

## Context

Lola is an AI Skills Package Manager written in Python 3.13 that distributes context packages to AI assistants and agents. The Python implementation successfully validated the concept and the core workflows.

We want to migrate to Go to achieve single-binary distribution aligned with CNCF self-contained tooling practices, enable cross-compilation for all major platforms, and directly integrate with skillimage.dev — a Go-native project that provides importable packages for OCI-based skill distribution. The CY26 roadmap targets this migration for Q2 2026.

The Lola + Skill Image collaboration analysis establishes the architectural relationship: skillctl is the packager (analogous to rpmbuild), OCI registries are the repos, and Lola is the resolver/installer (analogous to dnf). A Go rewrite enables Lola to import skillimage's Go packages directly as compiled-in library dependencies.

Additionally, sigstore — the industry standard for software signing — provides native Go libraries (`sigstore-go`) for signature verification. Go is the only language besides Python that has first-class sigstore library support, making it the natural choice for a tool that needs both single-binary distribution and native signature verification.

The existing `market` terminology will be renamed to `repo` during this migration, aligning with established package manager conventions as already noted in `docs/dev-guide/architecture.md`.

## Decision

Migrate Lola from Python to Go.

**Dependency principle**: Prefer Go standard library for all functionality where stdlib is sufficient. External dependencies are added only when they provide significant value that would be costly to reimplement. Keep the dependency count minimal.

**Tech stack**:

| Package | Purpose | Import | Why not stdlib |
|---------|---------|--------|----------------|
| [spf13/cobra](https://github.com/spf13/cobra) | CLI framework | `github.com/spf13/cobra` | Subcommand trees, completions, intelligent suggestions — no stdlib equivalent |
| [spf13/viper](https://github.com/spf13/viper) | Configuration | `github.com/spf13/viper` | Multi-format config, env binding, Cobra integration — handles YAML and TOML via its own dependencies |
| [go-git/go-git/v5](https://github.com/go-git/go-git) | Git operations | `github.com/go-git/go-git/v5` | Pure Go git eliminates runtime dependency on git binary |
| [pterm/pterm](https://github.com/pterm/pterm) | TUI output | `github.com/pterm/pterm` | Tables, spinners, prompts, colored output — no stdlib equivalent |
| [google/go-cmp](https://github.com/google/go-cmp) | Test struct diffing | `github.com/google/go-cmp/cmp` | Clear failure output for complex structs (test-only) |
| [sigstore/sigstore-go](https://github.com/sigstore/sigstore-go) | Signature verification | `github.com/sigstore/sigstore-go` | Sigstore bundle verification (see ADR-0005) |

**Stdlib usage** (no additional go.mod entries):

| Package | Purpose |
|---------|---------|
| `log/slog` | Structured logging |
| `net/http` | HTTP client for marketplace fetches and downloads |
| `archive/tar`, `archive/zip`, `compress/gzip` | Archive handling for module sources |
| `os/exec` | Hook script execution |
| `testing` | Test framework with table-driven tests |

Frontmatter parsing is hand-rolled: split on `---`, unmarshal with the YAML library that Viper already provides.

**Go version**: 1.25+ (matches skillimage compatibility requirement).

**Release**: [GoReleaser](https://goreleaser.com/) for cross-compilation (linux/darwin/windows, amd64/arm64), GitHub releases with checksums, SBOM generation, and Homebrew/Scoop formula generation.

**Coexistence strategy**: Python source (`src/lola/`) is tagged at `v1.x-python-final` and frozen. Go source grows in `cmd/`, `internal/`, `pkg/` within the same repository. CI runs both test suites during the transition. Python source is removed when Go reaches feature parity.

**skillimage integration**: Lola imports [skillimage](https://github.com/redhat-et/skillimage) Go packages directly:
- `pkg/oci` — pull, unpack, inspect OCI skill images
- `pkg/skillcard` — parse and validate skill metadata (YAML SkillCard)
- `pkg/lifecycle` — lifecycle state machine (draft/testing/published/deprecated/archived)

## Rationale

- **Single binary**: Go compiles to a static binary with no runtime dependencies, aligned with CNCF self-contained tooling practices
- **Cross-compilation**: GoReleaser produces binaries for all major platforms in one CI step
- **skillimage alignment**: Both projects in Go enables direct library import with shared types and compile-time safety
- **sigstore alignment**: `sigstore-go` provides native Go verification — Go is one of only two languages (alongside Python) with first-class sigstore library support
- **Minimal dependencies**: stdlib-first approach keeps the dependency tree lean; only 6 external runtime packages
- **CLI UX preserved**: All existing commands retain identical behavior

## Consequences

### Positive Consequences

- Users install Lola by downloading a single binary for their platform
- skillimage packages imported directly with shared Go types
- sigstore verification compiled in natively via sigstore-go
- GoReleaser automates cross-platform releases, Homebrew tap, Scoop bucket, SBOM generation
- Go's `internal/` package convention enforces clean public/private boundaries for the extension SDK
- `market` → `repo` rename aligns with established package manager terminology

### Negative Consequences

- Full rewrite of ~2500 LOC Python; temporary dual maintenance during coexistence
- Contributors must know Go (though Lola is straightforward CLI code)
- `go-git/v5` has a heavy transitive dependency tree (~20 packages); accepted for single-binary benefit
- Viper has a medium transitive tree; accepted for the config surface complexity it handles

## Alternatives Considered

### Alternative 1: Stay on Python
- Description: Continue with Python, use PyInstaller or shiv for single-file distribution
- Pros: No rewrite effort, existing contributor familiarity, sigstore-python available
- Cons: Cannot import skillimage Go packages natively; bundled Python runtime adds size and startup time; not a true single binary
- Reason for rejection: Does not achieve single-binary distribution aligned with CNCF practices, and cannot share types with skillimage at compile time

## Implementation Notes

See paired design document: `docs/dev-guide/design/go-migration.md`

Migration phases:
1. Freeze Python at `v1.x-python-final` tag
2. Scaffold Go project structure (see ADR-0003)
3. Implement core commands with feature parity
4. Integrate skillimage Go packages for OCI source handler
5. Remove Python source after Go passes full test matrix

## References

- [CY26 Roadmap](../concepts/roadmap.md)
- [Current Architecture](../dev-guide/architecture.md)
- [skillimage.dev](https://skillimage.dev/)
- [GoReleaser](https://goreleaser.com/)
- [spf13/cobra](https://github.com/spf13/cobra)
- [spf13/viper](https://github.com/spf13/viper)
- [go-git/go-git](https://github.com/go-git/go-git)
- [pterm/pterm](https://github.com/pterm/pterm)
- [sigstore/sigstore-go](https://github.com/sigstore/sigstore-go)
- [google/go-cmp](https://github.com/google/go-cmp)
