# ADR-0007: OCI Format

**Status**: Proposed
**Date**: 2026-04-29
**Authors**: Daniele Martinoli
**Reviewers**: []

## Status

Proposed

## Context

### Current State

Lola currently uses a multi-source distribution model:

- **Git repositories** (clone with depth 1)
- **Local archives** (zip/tar files)
- **Folder copying** (local directories)
- **Marketplace registries** (YAML catalogs with remote module references)

Skills are distributed as directory structures containing SKILL.md files with YAML frontmatter, optional scripts, commands, and agents. This format-neutral approach allows users to choose distribution methods based on their workflow preferences.

### Problem Statement

The current approach, while flexible, faces several limitations for enterprise deployments:

1. **No cryptographic verification** - No way to verify skill integrity or author identity
2. **No provenance tracking** - Cannot verify where skills originated or how they were built
3. **Limited metadata** - YAML frontmatter provides basic metadata but no standardized extensibility for discovery systems
4. **No versioning immutability** - Git tags are mutable; no digest-based pinning
5. **ConfigMap limitations** - 1 MiB size limits for Kubernetes-based deployments
6. **No audit trail** - Cannot track skill access or distribution history

These limitations become critical when deploying AI skills in regulated environments or when supply chain security is a requirement.

### Why OCI Format

The Open Container Initiative (OCI) artifact format addresses these limitations while maintaining Lola's format-neutral philosophy. OCI is proposed as **one supported format among many**, not as a replacement for existing distribution methods.

**Key Advantages:**

1. **Cryptographic Trust** - Cosign/Sigstore keyless signing with transparency logs (Rekor)
2. **Provenance Verification** - SLSA attestations for supply chain integrity
3. **Immutable Versioning** - Content-addressable storage with sha256 digests
4. **Standardized Metadata** - OCI annotations for discovery, licensing, and evaluation metrics
5. **Enterprise Infrastructure** - Reuses existing container registries and RBAC
6. **Cloud-Native Integration** - Kubernetes ImageVolumes (1.33+), volume mounting, GitOps workflows
7. **Air-Gap Support** - oc-mirror with signature preservation for disconnected environments
8. **Read-Only Runtime** - Image volumes prevent skill modification at runtime

**Format Independence:**

- OCI format can be consumed by Lola regardless of how it was built (Lola CLI, Compass pipelines, MLflow, Buildah, custom CI/CD)
- Users are not required to use Lola for building; it's an optional convenience tool
- Git, Zip, Tar formats remain fully supported with no migration required

### Comparison with Alternative Options


| Aspect                 | Git/Zip/Tar            | OCI Artifacts                 | Lola's Approach                 |
| ---------------------- | ---------------------- | ----------------------------- | ------------------------------- |
| **Distribution**       | Manual clone/download  | Standard push/pull tooling    | **Support both equally**        |
| **Integrity**          | Git commit hash        | SHA-256 content addressing    | **Verify based on source type** |
| **Signing**            | Git commit signing     | Cosign/Sigstore (keyless)     | **Optional for both**           |
| **Provenance**         | Git history only       | SLSA attestations             | **Support both approaches**     |
| **Access Control**     | Repository permissions | Registry RBAC                 | **Respect source permissions**  |
| **Runtime Mutability** | Mutable files (local)  | Read-only volumes (container) | **Mode-dependent**              |
| **Air-Gap Support**    | Manual mirroring       | oc-mirror with signatures     | **Support both workflows**      |


**Alternative AI/ML Formats Considered:**

- **Docker model-CLI** - Proprietary, Docker-specific
- **KitOps** - ML-focused, limited adoption
- **ONNX archives** - Model-only, not skill distribution
- **Hugging Face Hub** - Centralized, not self-hostable
- **MLflow** - Heavy infrastructure, not portable

**Why OCI wins:** Existing infrastructure, proven toolchain, standard compliance, mature security ecosystem, and cloud-native integration.

### Similar Projects and Industry Initiatives

**Red Hat skillimage Project** ([GitHub](https://github.com/redhat-et/skillimage))

- Library-first design for OCI-based skill distribution
- `skillctl` CLI for build/push/pull/inspect operations
- Framework-agnostic approach for any AI agent
- Kubernetes ImageVolume mounting for containerized deployments
- Demonstrates viability of OCI format for AI skills

**CNCF OCI Artifact Standardization** ([TOC Issue #1740](https://github.com/cncf/toc/issues/1740))

- TOC-approved initiative (July 2025) for AI artifact packaging
- Goals: Standardize AI artifact packaging, bridge notebooks with cloud-native YAML
- Technical streams: GPU-aware containers, unified CLI tools, ModelPack specification
- Deliverables: <10-minute "idea-to-inference" workflow, Model Openness Framework compliance

**Industry Standards:**

- [SLSA Framework](https://slsa.dev/) - Supply-chain security levels for software artifacts
- [Sigstore](https://www.sigstore.dev/) - Keyless signing with transparency logs
- [in-toto Attestation Framework](https://github.com/in-toto/attestation) - Standardized provenance envelopes

### Architectural Implications

**Enterprise Skill Management Framework:**

Organizations deploying AI skills at scale often implement a three-layer architecture for discovery, distribution, and governance:

1. **Layer 1: Distribution** (Multiple Formats)
  - OCI artifacts for enterprise deployments requiring cryptographic signing and provenance
  - Git/Zip/Tar maintained for simpler use cases and developer workflows
  - Format flexibility allows organizations to choose based on requirements
2. **Layer 2: Catalog** (Organization-Approved Content)
  - Curated catalog of validated, organization-approved skills
  - Integration with enterprise catalog systems (e.g., operator catalogs, internal registries)
  - Disconnected environment support for air-gapped deployments
  - Access control and approval workflows
3. **Layer 3: Discovery and Measurement** (Governance Platforms)
  - Enterprise governance platforms (e.g., Compass) for skill evaluation and catalog management
  - ML lifecycle platforms (e.g., MLflow) for experiment tracking and registry
  - Custom solutions for organization-specific requirements
  - **Lola's Independence** - Operates without dependency on any specific governance platform

**Lola's Deployment Modes:**

1. **Local IDE Installation** (Unpacking)
  - Pull OCI image → Extract to filesystem → Generate assistant-native files
  - Supports: Claude Code, Cursor, Gemini CLI
  - Works with all formats (OCI, Git, Zip, Tar)
2. **Containerized Agent Installation** (Volume Mounting)
  - Verify signatures → Mount OCI image as read-only volume
  - Supports: OpenCode, custom containerized agents
  - OCI-only (requires container runtime)
3. **Cloud Platform Installation** (RHOAI/OpenShift)
  - Run Lola as containerized tool → Verify + install to cluster agents
  - Supports: OpenShift AI, Kubernetes with skill operators
  - Primarily OCI for signature verification

**Plugin Bundling Concept:**
Skills should not be registered in isolation. Lola modules typically include:

- **Skills** - AI agent instructions (SKILL.md)
- **Commands** - Slash commands for workflows
- **Agents** - Specialized subagents for complex tasks

OCI artifacts package complete modules together, preserving Lola's current architecture where modules contain `skills/`, `commands/`, and `agents/` directories.

**Marketplace Integration:**
Marketplaces serve as the discovery/catalog layer and are source-agnostic. A marketplace YAML can reference modules distributed via any format:

```yaml
modules:
  - name: document-skills
    repository: oci://registry.io/lola/document-skills:2.0.0  # OCI
  - name: git-workflow
    repository: https://github.com/lola-project/git-workflow.git  # Git
  - name: local-tools
    repository: https://downloads.example.com/local-tools.zip  # Zip
```

No changes to marketplace structure are required. Users discover modules via `lola mod search`, and Lola automatically detects the distribution format from the `repository` field. This separation of concerns (discovery vs distribution) allows organizations to choose OCI for some modules while keeping Git/Zip/Tar for others.

### References

**Standards and Specifications:**

- [OCI Distribution Spec](https://github.com/opencontainers/distribution-spec)
- [SLSA Framework](https://slsa.dev/)
- [in-toto Attestation Framework](https://github.com/in-toto/attestation)

**Tools and Libraries:**

- [Red Hat skillimage](https://github.com/redhat-et/skillimage) - Library-first OCI skill distribution
- [Cosign Documentation](https://docs.sigstore.dev/cosign/)
- [Sigstore](https://www.sigstore.dev/)

**Industry Initiatives:**

- [CNCF TOC Issue #1740](https://github.com/cncf/toc/issues/1740) - OCI Artifact Standardization for AI

**Implementation Guides:**

- [Verifying Software Integrity with Sigstore (2026)](https://techbytes.app/posts/software-integrity-sigstore-cosign-cheat-sheet/)
- [How to Implement SLSA Level 3 Build Provenance](https://oneuptime.com/blog/post/2026-02-09-slsa-level3-build-provenance/view)

**Related Lola PRs:**

- [PR #109](https://github.com/LobsterTrap/lola/pull/109) - Move to Go implementation
- [PR #111](https://github.com/LobsterTrap/lola/pull/111) - Go-based implementation (continued)

**Related Documentation:**

- [OCI CLI Exploration](0007-oci-format/oci-cli-exploration.md) - Detailed command specifications and examples for OCI support

## Decision

We will add OCI artifact format as a supported distribution method for Lola modules, alongside the existing Git, Zip, Tar, and folder sources. This decision involves three key architectural changes:

### 1. OCI Format Support

Add OCI artifact format as **one supported format among many**:

- Modules can be distributed via `oci://registry.io/org/module:version` references
- OCI modules coexist with Git/Zip/Tar formats without preference
- No migration required for existing modules
- Marketplace catalogs remain source-agnostic (can reference any format)

### 2. Go-based Implementation with skillimage Library

**Implementation Language:** Rewrite Lola in Go (see PRs [#109](https://github.com/LobsterTrap/lola/pull/109), [#111](https://github.com/LobsterTrap/lola/pull/111))

**Rationale for Go:**

- **OCI ecosystem** - Native access to Go-based OCI tooling (containers/image, go-containerregistry)
- **Performance** - Single compiled binary with no runtime dependencies
- **Distribution** - Cross-platform binaries (Linux, macOS, Windows) without Python interpreter
- **skillimage integration** - Natural fit for Go library consumption

**Library Integration:** Use [Red Hat's skillimage library](https://github.com/redhat-et/skillimage) for OCI operations:

- **Rationale:** Proven, library-first design specifically built for AI skill distribution via OCI
- **Functionality:** Handles build, push, pull, inspect, verify operations
- **Compatibility:** Framework-agnostic approach aligns with Lola's multi-assistant support
- **Benefits:**
  - Avoid reimplementing OCI image manipulation
  - Leverage battle-tested code for registry operations
  - Gain Kubernetes ImageVolume support (1.33+)
  - Benefit from ongoing skillimage development and security updates

**Integration Points:**

```go
// Illustrative example: Conceptual skillimage library usage for OCI operations
// Note: Actual API signatures subject to skillimage library implementation
import "github.com/redhat-et/skillimage/pkg/oci"

// Pull OCI artifact
artifact, err := oci.Pull(ctx, "registry.io/lola/module:1.0.0")

// Extract to filesystem (for local IDE installation)
err = artifact.ExtractTo("/path/to/.lola/modules/")

// Verify signature and provenance
err = artifact.Verify(ctx, oci.WithCosign(), oci.WithSLSA())
```

**Command Specifications:** Detailed CLI command proposals (including `lola build`, `lola push`, `lola sign`, `lola verify`, etc.) are documented in [OCI CLI Exploration](0007-oci-format/oci-cli-exploration.md).

**OCI Metadata Schema:**

**Architectural Layering:**

Lola uses skillimage as a **low-level library** for OCI mechanics (push, pull, verify, layer manipulation) while defining its own semantic layer for metadata:

- **skillimage layer** - Handles OCI infrastructure operations (registry communication, image building, signature verification)
- **Lola semantic layer** - Defines domain-specific metadata using `io.lola.module.*` namespace for Lola's multi-component model

**Rationale for separate namespace:**

1. **Domain model mismatch** - skillimage is designed for single skills; Lola bundles skills + commands + agents into modules
2. **Independent evolution** - Lola can evolve its metadata schema without coupling to skillimage's SkillCard format
3. **Library vs application** - skillimage provides OCI tooling; Lola provides skill package management semantics
4. **Precedent** - Similar to Helm charts, Buildpacks, and WASM artifacts using OCI infrastructure with their own annotation namespaces

This separation allows Lola to leverage skillimage's battle-tested OCI implementation while maintaining control over its domain-specific metadata model.

Lola modules use OCI manifest annotations with the `io.lola.module.*` namespace for metadata:

```json
{
  "schemaVersion": 2,
  "config": {
    "mediaType": "application/vnd.lola.module.config.v1+json",
    "digest": "sha256:...",
    "size": 1234
  },
  "layers": [...],
  "annotations": {
    "org.opencontainers.image.version": "1.0.0",
    "org.opencontainers.image.description": "Module description",
    "org.opencontainers.image.licenses": "MIT",
    "org.opencontainers.image.source": "https://github.com/org/repo",
    "org.opencontainers.image.revision": "abc123def456",

    "io.lola.module.name": "document-skills",
    "io.lola.module.categories": "document,processing",
    "io.lola.module.tools": "read_file,grep,bash",
    "io.lola.module.skills": "summarizer,translator,formatter",
    "io.lola.module.commands": "export,convert",
    "io.lola.module.agents": "document-analyzer",

    "io.lola.evaluation.accuracy": "0.95",
    "io.lola.evaluation.latency_p95": "250ms",
    "io.lola.evaluation.cost_per_1k": "0.002",
    "io.lola.evaluation.quality_score": "4.5",
    "io.lola.evaluation.dataset": "benchmark-v1",
    "io.lola.evaluation.date": "2026-04-29"
  }
}
```

**Evaluation Metrics Storage:**

The `io.lola.evaluation.*` namespace stores skill performance metrics as string key-value pairs in OCI annotations:

**Schema and Sources:**

Evaluation metadata can be populated from multiple sources:

1. **Manual Annotation** - Developers specify metrics during `lola build`:
   ```bash
   lola build my-skill -t registry.io/org/skill:1.0.0 \
     --annotation "io.lola.evaluation.accuracy=0.95" \
     --annotation "io.lola.evaluation.dataset=benchmark-v1"
   ```

2. **CI/CD Integration** - Build pipelines inject test results:
   ```yaml
   # GitHub Actions example
   - name: Run benchmarks
     run: pytest --benchmark-json=results.json

   - name: Build with metrics
     run: |
       ACCURACY=$(jq -r '.accuracy' results.json)
       lola build . -t registry.io/org/skill:1.0.0 \
         --annotation "io.lola.evaluation.accuracy=$ACCURACY" \
         --annotation "io.lola.evaluation.date=$(date -I)"
   ```

3. **Governance Platform Export** - Platforms like Compass could export evaluation results to OCI annotation format files, which Lola could consume during build via `--annotations-file` flag.

4. **MLflow Integration** - ML experiment tracking systems could provide plugins to export logged metrics to OCI annotation format for integration with artifact builds.

**Namespace Design:**

The `io.lola.evaluation.*` namespace is intentionally flexible to support various evaluation frameworks and metrics. Organizations can define their own metric keys based on their evaluation needs. Standard metric conventions will be established once evaluation workflows are implemented and real-world usage patterns emerge.

**Benefits:**
- **Queryable** - Discovery systems can filter by performance without downloading artifacts
- **Immutable** - Metrics are part of signed OCI manifest, preventing tampering
- **Versioned** - Each artifact version has independent evaluation scores
- **Flexible** - Organizations can define custom metrics for domain-specific needs

**OCI Image Structure:**

**skillimage's Approach:**

skillimage uses a minimalist single-layer design, as documented in their `pkg/oci/build.go`:

1. **Single compressed layer** - Entire module directory packaged into one tar+gzip layer
2. **Media type profiles** - Supports two profiles:
   - **Standard**: OCI default types (`application/vnd.oci.image.layer.v1.tar+gzip`)
   - **Red Hat**: Custom types (`application/vnd.redhat.agentskill.layer.v1.tar+gzip`) for disconnected mirroring support
3. **Metadata in annotations** - All module metadata stored in OCI manifest annotations, not in layers
4. **FROM scratch** - Images built from scratch, containing only module content

**Lola's OCI Image Structure:**

Following skillimage's pattern, Lola modules are packaged with a single content layer:

```
OCI Image:
├── Config (application/vnd.lola.module.config.v1+json)
│   └── Contains: Layer digests, creation timestamp
│
└── Layer (application/vnd.lola.module.layer.v1.tar+gzip)
    └── module-root/
        ├── skills/
        │   ├── skill-1/SKILL.md
        │   └── skill-2/SKILL.md
        ├── commands/
        │   └── command.md
        └── agents/
            └── agent.md
```

**Layer Creation (from skillimage's build.go):**
- Walks module directory, creating uncompressed tar
- Skips hidden files (`.` prefix) and non-regular files
- Computes digest on uncompressed tar for `diff_ids`
- Compresses with gzip for final layer
- Stores all metadata in manifest annotations (`io.lola.module.*` namespace)

**Directory Structure After Extraction:**

When unpacked to filesystem (local mode), the structure matches Lola's current format:

```
.lola/modules/module-name/
├── skills/
│   ├── skill-name-1/
│   │   ├── SKILL.md
│   │   └── scripts/
│   └── skill-name-2/
│       └── SKILL.md
├── commands/
│   ├── command-1.md
│   └── command-2.md
└── agents/
│   └── agent-1.md
│...
```

**Architecture:**

```
lola (Go binary)
  ├── CLI framework (cobra/cli)
  ├── Core commands (mod, install, market)
  ├── Source handlers
  │   ├── Git handler (go-git)
  │   ├── Zip/Tar handler (archive/zip, archive/tar)
  │   └── OCI handler (skillimage library)
  └── Assistant generators (same logic, Go implementation)
```

### 3. Verification and Security

**Secure by Default:**

- Signature verification enabled automatically for OCI modules
- Provenance verification enabled when SLSA attestations exist
- Digest pinning for immutable references
- Development opt-out via `--skip-verification` (with warnings)

**Verification Stack:**

- Cosign for signature verification (keyless and key-based)
- SLSA provenance attestation validation
- Rekor transparency log verification
- Identity constraints via regex patterns

### Implementation Scope

**Effort Estimation Note:** Estimates assume AI-assisted development (Claude Code, Copilot, etc.) providing 40-50% productivity gains in code generation, testing, and documentation compared to traditional development.

**Phase 0 (Go Rewrite Foundation):** *Estimated: 5-7 days*

- Rewrite Lola core in Go (~6K LOC, well-structured)
- Port existing Git/Zip/Tar/marketplace functionality
- Maintain CLI interface compatibility (Click → Cobra)
- Integrate skillimage library for OCI support

**Key Complexity:** Primarily mechanical translation aided by AI. Testing behavioral equivalence is the main effort.

**Phase 1 (Initial OCI Support):** *Estimated: 4-6 days*

- OCI module addition via `lola mod add oci://...`
- Signature and provenance verification
- Local IDE installation (unpack mode)
- Integration with existing marketplace search

**Key Complexity:** Cosign/Sigstore integration. skillimage library handles core OCI mechanics, reducing effort significantly.

**Phase 2 (Building and Distribution):** *Estimated: 3-5 days*

- Optional `lola build` command for creating OCI artifacts
  - Validation integrated by default (use `--skip-validation` to bypass)
  - Generates skill.yaml from SKILL.md frontmatter for single-skill modules
  - Validates against lola.io/v1 schema for multi-skill modules
- `lola push` for registry publishing
- `lola sign` for Cosign signing

**Key Complexity:** YAML frontmatter parsing and schema validation. Builds on Phase 1 infrastructure.

**Phase 3 (Advanced Deployments):** *Estimated: 4-6 days*

- Container mode (volume mounting)
- Cloud platform installation
- Custom skill bundles

**Key Complexity:** Kubernetes manifest generation and multiple deployment mode support.

---

**Total Implementation Timeline:** 16-24 days (3-5 weeks)

**Parallelization Opportunities:**
- Phase 0 must complete first (foundation dependency)
- Phases 1-2 can partially overlap (build tooling can start once core OCI operations work)
- Phase 3 can begin once Phase 1 stabilizes

**Critical Path:** Phase 0 → Phase 1 (core functionality) → Phases 2-3 (can be prioritized based on user needs)

**Out of Scope:**

- OCI format is not mandatory (Git/Zip/Tar remain fully supported)
- Lola is not required for building OCI artifacts (optional convenience)
- No dependency on specific governance platforms (Compass, MLflow, etc.)

## Consequences

### Positive Consequences

**Security & Compliance:**
- ✅ Cryptographic verification via Cosign/Sigstore with keyless signing
- ✅ SLSA provenance tracking for supply chain audit compliance
- ✅ Immutable digest-based versioning prevents tampering
- ✅ Registry RBAC and audit logs for access control

**Enterprise Operations:**
- ✅ Air-gap support via oc-mirror with signature preservation
- ✅ Kubernetes ImageVolume support (1.33+) for containerized deployments
- ✅ Read-only runtime volumes prevent skill modification
- ✅ No ConfigMap size limits (vs 1 MiB constraint)

**Developer Experience:**
- ✅ Format neutrality - Git/Zip/Tar/OCI all equally supported
- ✅ Standard OCI tooling (podman/docker/skopeo) works out of the box
- ✅ Optional Lola build commands - use Compass, MLflow, or custom tools
- ✅ Proven skillimage library handles OCI complexity

**Implementation Benefits:**
- ✅ Leverage skillimage library (avoid reimplementing OCI mechanics)
- ✅ Go rewrite enables single binary distribution and better performance
- ✅ Native OCI ecosystem access and CNCF/Red Hat alignment
- ✅ GitOps-ready (Flux/Argo support OCI sources)

### Risks and Mitigations

**Backwards Compatibility:**
- ❌ Must preserve existing Git/Zip/Tar workflows
- ✅ Automatic format detection; no user-visible changes to commands

**skillimage Dependency:**
- ❌ External dependency on Red Hat-maintained library
- ✅ Open source, CNCF-aligned, forkable if needed

**Cross-Platform Builds:**
- ❌ Must build for multiple platforms (Linux, macOS, Windows, ARM)
- ✅ GitHub Actions matrix builds + Go's native cross-compilation

**OCI Ecosystem Evolution:**
- ❌ Specifications or tooling may change incompatibly
- ✅ skillimage tracks OCI standards; digest pinning protects against breakage

**Format Selection Confusion:**
- ❌ Users may not know when to use OCI vs Git/Zip/Tar
- ✅ Decision tree documentation + automatic format detection

