# ADR: OCI Format

**Status**: Proposed
**Date**: 2026-04-29
**Authors**: Daniele Martinoli
**Reviewers**: []

## Context

Lola distributes modules (skills, commands, agents) via Git, Zip/Tar, local folders, and marketplace YAML catalogs. That model works for many teams but lacks enterprise supply-chain controls: cryptographic verification, SLSA-style provenance, digest-pinned immutable versions, and registry-native RBAC for regulated or air-gapped environments.

The [Open Container Initiative (OCI)](https://github.com/opencontainers/distribution-spec) artifact format addresses those gaps. OCI is **one supported format among many**—not a replacement for Git/Zip/Tar. Users may build artifacts with Lola, [skillimage](https://github.com/redhat-et/skillimage), or existing CI/CD; Lola consumes OCI references such as `oci://registry.io/org/module:version` the same way it consumes Git URLs.

Industry alignment: [Red Hat skillimage](https://github.com/redhat-et/skillimage) (library-first OCI skill distribution) and [CNCF TOC Issue #1740](https://github.com/cncf/toc/issues/1740) (OCI artifact standardization for AI). Marketplace discovery stays source-agnostic: `repository` may point at OCI, Git, or archive URLs without schema changes.

Implementation depends on the [Go Migration](go-migration.md) ADR (single binary, skillimage and sigstore-go integration).

## Decision

We will add OCI artifact distribution for Lola modules alongside existing sources.

1. **OCI as an optional format**
   - Support `oci://` module references; no migration for current modules.
   - Marketplace catalogs remain format-neutral.
   - Modules still bundle `skills/`, `commands/`, and `agents/`.

2. **Go implementation via skillimage**
   - Use skillimage for pull, push, verify, and single-layer packaging.
   - Lola defines semantics in the `io.lola.module.*` annotation namespace (skillimage handles OCI mechanics; Lola models multi-component modules).
   - Packaging follows skillimage’s single content layer pattern; details in [OCI CLI Exploration](oci-format/oci-cli-exploration.md).

3. **Verify before materialize**
   - Signature and provenance verification enabled by default for OCI modules.
   - `--skip-verification` disables both (development only, with warnings).
   - Illustrative consumption flow:

```go
import "github.com/redhat-et/skillimage/pkg/oci"

artifact, err := oci.Pull(ctx, "registry.io/lola/module:1.0.0")
err = artifact.Verify(ctx, oci.WithCosign(), oci.WithSLSA())
err = artifact.ExtractTo("/path/to/.lola/modules/") // after verification succeeds
```

CLI command proposals (`lola build`, `lola push`, `lola sign`, `lola verify`, phasing, metadata schema) live in [OCI CLI Exploration](oci-format/oci-cli-exploration.md).

4. **Deployment modes** (installation adapts by target; see CLI exploration for `lola install --mode`)
   - **Local (default)** — Pull OCI artifact, verify, unpack to `~/.lola/modules/` and generate assistant-native files (Claude Code, Cursor, Gemini CLI, etc.). Git/Zip/Tar use the same path.
   - **Container** — Mount the OCI image as a read-only volume for containerized agents (e.g. OpenCode); no unpack. Requires a container runtime; OCI-only.
   - **Cloud** — Verify and install into cluster workloads (e.g. OpenShift/Kubernetes Jobs or operator-driven flows); primarily for signed OCI modules in regulated environments.

## Rationale

- **Format neutrality** — Teams keep Git/Zip/Tar workflows; OCI is for registry-backed, verifiable distribution.
- **Reuse infrastructure** — Container registries, Cosign/Sigstore, oc-mirror, and Kubernetes ImageVolumes (1.33+) instead of bespoke packaging.
- **skillimage** — Avoid reimplementing OCI; align with Red Hat/CNCF direction for agent skills.
- **Separate metadata namespace** — Lola modules are not single-skill SkillCards; `io.lola.module.*` can evolve independently.

## Consequences

### Positive Consequences

- Cosign/Sigstore verification and optional SLSA provenance for audit requirements
- Digest-pinned, immutable artifact versions
- Registry RBAC and standard pull tooling (podman, skopeo, etc.)
- Air-gap mirroring with signatures; read-only mounts for containerized agents
- No change required for existing Git/Zip/Tar users

### Negative Consequences

- **Backwards compatibility** — Must preserve non-OCI flows; mitigated by automatic format detection.
- **skillimage dependency** — External library; mitigated by open source and forkability.
- **Format choice** — Users may be unsure when to use OCI; mitigated by docs in CLI exploration and defaults.
- **Go rewrite scope** — OCI ships with Go migration; see [go-migration.md](go-migration.md).

## Alternatives Considered

### Alternative 1: Git/Zip/Tar only
- **Pros:** No new format or registry operations.
- **Cons:** No digest pinning, limited provenance, weak enterprise registry story.
- **Rejected:** Does not meet supply-chain requirements for target deployments.

### Alternative 2: Other AI packaging formats
- **Examples:** Docker model-CLI (proprietary), KitOps, ONNX-only bundles, centralized hubs.
- **Cons:** Poor fit for multi-component Lola modules or self-hosted registries.
- **Rejected:** OCI reuses mature registry and signing tooling.

## Implementation Notes

Phases (detail and estimates in [OCI CLI Exploration](oci-format/oci-cli-exploration.md#implementation-phasing)):

| Phase | Focus |
|-------|--------|
| 0 | Go rewrite; port Git/Zip/Tar/marketplace; skillimage integration |
| 1 | `lola mod add oci://…`, verify-by-default, local unpack install |
| 2 | Optional `lola build` / `lola push` / `lola sign` |
| 3 | Container volume mount and cloud deployment modes |

**Out of scope:** Mandatory OCI-only distribution; requiring Lola to build artifacts; coupling to a specific governance platform (Compass, MLflow, etc.).

## References

- [Go Migration](go-migration.md)
- [OCI CLI Exploration](oci-format/oci-cli-exploration.md)
- [OCI Distribution Spec](https://github.com/opencontainers/distribution-spec)
- [Red Hat skillimage](https://github.com/redhat-et/skillimage)
- [CNCF TOC Issue #1740](https://github.com/cncf/toc/issues/1740)
- [SLSA Framework](https://slsa.dev/)
- [Verifying signatures with Cosign](https://docs.sigstore.dev/cosign/verifying/verify/)
- [Sigstore quickstart with Cosign](https://docs.sigstore.dev/quickstart/quickstart-cosign/)
- [Cosign signing overview](https://docs.sigstore.dev/cosign/signing/overview/)
- [PR #109](https://github.com/LobsterTrap/lola/pull/109), [PR #111](https://github.com/LobsterTrap/lola/pull/111) — Go implementation
