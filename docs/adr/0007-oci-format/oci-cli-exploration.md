# OCI CLI Exploration: Command Specifications and Examples

**Purpose:** Technical reference material for OCI CLI command specifications
**Date:** 2026-04-29
**Related:** [ADR 0007: OCI Format](../0007-oci-format.md)

## Overview

This document provides detailed CLI command specifications for OCI artifact distribution in Lola, supporting the architectural decisions made in [ADR 0007](../0007-oci-format.md). It presents command syntax, usage examples, and implementation considerations based on the approved OCI format support strategy.

**Status:** This document reflects the architectural decisions in ADR 0007. Command designs and option names are proposals for implementation and may be refined during development.

## Architectural Foundation

Per [ADR 0007](../0007-oci-format.md), Lola's OCI implementation is built on the following architectural decisions:

### skillimage Library Integration

Lola uses [Red Hat's skillimage library](https://github.com/redhat-et/skillimage) as a **low-level library** for OCI mechanics:
- **skillimage layer** - Handles OCI infrastructure (registry communication, image building, signature verification)
- **Lola semantic layer** - Defines domain-specific metadata using `io.lola.module.*` namespace

This separation allows Lola to leverage skillimage's battle-tested OCI implementation while maintaining control over its domain-specific metadata model for modules (skills + commands + agents).

### OCI Image Structure

Following skillimage's minimalist approach, Lola modules are packaged as **single-layer OCI images**:

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

**Layer Creation:**
- Walks module directory, creating uncompressed tar
- Skips hidden files (`.` prefix) and non-regular files
- Computes digest on uncompressed tar for `diff_ids`
- Compresses with gzip for final layer
- Stores all metadata in manifest annotations (`io.lola.module.*` namespace)

### Go Rewrite

Lola will be rewritten in Go to:
- Enable native skillimage library integration
- Provide single compiled binary distribution
- Access Go-based OCI tooling ecosystem
- Deliver better performance than interpreted Python

## Design Considerations

The following design principles could guide CLI development for OCI support:

1. **Format Neutrality** - No format should be preferred; commands could work uniformly across OCI, Git, Zip, Tar
2. **Backward Compatibility** - Existing commands should continue to work unchanged
3. **Optional Building** - OCI build commands could be optional; users might use Compass, MLflow, or custom tools
4. **Mode Awareness** - Installation could adapt to deployment mode (local, containerized, cloud)

---

## Table of Contents

1. [New Commands](#new-commands)
   - [Module Metadata and SkillCard](#module-metadata-and-skillcard)
2. [Modified Commands](#modified-commands)
   - [Workflow Pattern: Add Then Install](#workflow-pattern-add-then-install)
3. [CLI Examples by Use Case](#cli-examples-by-use-case)
4. [Error Handling](#error-handling)
5. [Configuration](#configuration)
6. [Possible Implementation Phasing](#possible-implementation-phasing)
7. [Future Enhancements](#future-enhancements-not-for-initial-version)
8. [Backward Compatibility](#backward-compatibility)

---

## Possible New Commands

These commands represent potential additions to support OCI workflows. Each command specification is a starting point for discussion.

### `lola build` - Build OCI Artifact (Optional)

**Purpose:** Create an OCI artifact from a Lola module directory.

**Note:** This would be an optional convenience command. Users could alternatively use Compass, MLflow, Buildah, etc.

**Module Metadata:** See [Module Metadata and SkillCard](#module-metadata-and-skillcard) for details on skill.yaml requirements and auto-generation from SKILL.md frontmatter.

```bash
lola build [OPTIONS] <MODULE_PATH>

Arguments:
  <MODULE_PATH>           Path to module directory (default: current directory)

Options:
  -t, --tag <TAG>         OCI image tag (e.g., registry.io/org/skill:1.0.0)
  -o, --output <PATH>     Output path for OCI layout (default: .lola/build/)
  --compression <TYPE>    Compression type: gzip, zstd, none (default: gzip)
  -h, --help             Show help

Examples:
  # Build OCI artifact with tag
  lola build -t registry.io/myorg/my-skill:1.0.0

  # Build from specific directory
  lola build ./modules/document-skills -t localhost/doc-skills:latest

  # Build without validation (use with caution)

Output:
  ✓ Validating module structure...
  ✓ Found 3 skills, 2 commands, 1 agent
  ✓ Building OCI artifact...
  ✓ Created layers: module-metadata (1.2 KB), skills (45 KB), commands (8 KB), agents (12 KB)
  ✓ OCI artifact: registry.io/myorg/my-skill:1.0.0
  ✓ Digest: sha256:abc123def456...
  ✓ Saved to: .lola/build/my-skill.tar
```

### Module Metadata and SkillCard

**Purpose:** Define module-level metadata for OCI annotations and marketplace catalogs.

**File:** `skill.yaml` (optional for single-skill modules, required for multi-skill modules)

**When it's used:**
- **Optional:** Single-skill modules can omit this file. `lola build` will generate it from SKILL.md frontmatter.
- **Required:** Multi-skill modules must provide this file to define module-level metadata.
- **Validation:** If present, `lola build` validates the schema before building.
- **OCI Inclusion:** The built OCI artifact always includes the skill card (either from file or auto-generated).

**Schema:**
```yaml
apiVersion: lola.io/v1
kind: Module
metadata:
  name: my-skill-module        # Module name (required)
  version: 1.0.0               # Semantic version (required)
  description: Brief description of the module (required)
  author: Author Name          # Optional
  license: MIT                 # SPDX license identifier (optional)
  repository: https://github.com/org/repo  # Source repository (optional)

spec:
  # Module-level metadata
  categories:                  # Skill categories (optional)
    - code-analysis
    - security

  tools:                       # Required tools across all skills (optional)
    - read_file
    - grep
    - bash

  skills:                      # Skill inventory (auto-populated from directory scan)
    - name: analyzer
      path: skills/analyzer
    - name: reviewer
      path: skills/reviewer
```

**Example for single-skill module (skill.yaml auto-generated from SKILL.md frontmatter):**
```markdown
# skills/analyzer/SKILL.md
---
name: analyzer
description: Analyze code for improvements
tools:
  - read_file
  - grep
categories:
  - code-analysis
license: MIT
---

# Code Analyzer
This skill analyzes code and suggests improvements...
```

When you run `lola build`, it will automatically generate:
```yaml
apiVersion: lola.io/v1
kind: Module
metadata:
  name: analyzer
  version: 1.0.0
  description: Analyze code for improvements
  license: MIT
spec:
  categories:
    - code-analysis
  tools:
    - read_file
    - grep
  skills:
    - name: analyzer
      path: skills/analyzer
```

**Example for multi-skill module (skill.yaml required):**
```yaml
# skill.yaml (required at module root)
apiVersion: lola.io/v1
kind: Module
metadata:
  name: code-tools
  version: 2.0.0
  description: Collection of code analysis and review tools
  author: Development Team
  license: Apache-2.0

spec:
  categories:
    - code-analysis
    - code-review
  tools:
    - read_file
    - grep
    - bash
  skills:
    - name: analyzer
      path: skills/analyzer
    - name: reviewer
      path: skills/reviewer
    - name: formatter
      path: skills/formatter
```

**OCI Annotations Mapping:**

The skill.yaml metadata is mapped to OCI manifest annotations:
```json
{
  "annotations": {
    "org.opencontainers.image.version": "1.0.0",
    "org.opencontainers.image.description": "Analyze code for improvements",
    "org.opencontainers.image.licenses": "MIT",
    "io.lola.module.name": "analyzer",
    "io.lola.module.categories": "code-analysis",
    "io.lola.module.tools": "read_file,grep",
    "io.lola.module.skills": "analyzer"
  }
}
```

---

### Module Validation - Implementation Approaches

**Purpose:** Validate module structure, metadata, and frontmatter before building OCI artifacts.

**Approved Approach:** Per [ADR 0007](../0007-oci-format.md), **Option B (Integrated Validation)** has been selected as the implementation approach. Validation is integrated into `lola build` and runs by default, aligning with the secure-by-default philosophy.

The three options considered were:

---

#### Option A: Separate `lola validate` Command

**Approach:** Standalone validation command independent of build process.

```bash
lola validate [OPTIONS] <MODULE_PATH>

Arguments:
  <MODULE_PATH>           Path to module directory (default: current directory)

Options:
  --strict                Enable strict validation mode (fail on warnings)
  -h, --help             Show help

Examples:
  # Validate current directory
  lola validate .

  # Validate specific module
  lola validate ./my-skill

  # Strict mode (fail on warnings)
  lola validate ./my-skill --strict

Output:
  Validating module: my-skill

  Module Structure:
    ✓ Module directory structure valid
    ✓ Found 3 skills, 2 commands, 1 agent

  Metadata Validation:
    ✓ skill.yaml: Schema valid (apiVersion: lola.io/v1)
    ✓ skill.yaml: All required fields present

  SKILL.md Validation:
    ✓ skills/analyzer/SKILL.md: Frontmatter valid
    ✓ skills/reviewer/SKILL.md: Frontmatter valid
    ✓ skills/formatter/SKILL.md: Frontmatter valid

  Commands:
    ✓ commands/export.md: Valid
    ! commands/test.md: Warning - No frontmatter found

  ✓ Validation successful (1 warning)

  Ready to build with: lola build my-skill -t registry.io/org/skill:1.0.0
```

**Pros:**
- ✅ Developers can validate without building (faster feedback)
- ✅ CI/CD can run validation as separate step
- ✅ Clear separation of concerns

**Cons:**
- ❌ Extra command to remember
- ❌ Developers might forget to validate before building

---

#### Option B: Integrated Validation (Recommended)

**Approach:** Validation automatically runs as part of `lola build` command.

```bash
lola build [OPTIONS] <MODULE_PATH>

Arguments:
  <MODULE_PATH>           Path to module directory (default: current directory)

Options:
  -t, --tag <TAG>         OCI image tag (e.g., registry.io/org/skill:1.0.0)
  --skip-validation       Skip validation (not recommended)
  -h, --help             Show help

Examples:
  # Build with automatic validation (default behavior)
  lola build my-skill -t registry.io/org/skill:1.0.0

  # Skip validation (not recommended)
  lola build my-skill -t registry.io/org/skill:1.0.0 --skip-validation

Output:
  Building module: my-skill

  Validation:
    ✓ Module structure valid
    ✓ Found 3 skills, 2 commands, 1 agent
    ✓ skill.yaml: Schema valid
    ✓ SKILL.md frontmatter: All valid
    ! commands/test.md: Warning - No frontmatter found

  Building OCI artifact:
    ✓ Generating skill.yaml from SKILL.md frontmatter
    ✓ Creating OCI layers...
    ✓ OCI artifact: registry.io/org/skill:1.0.0
    ✓ Digest: sha256:abc123def456...
```

**Pros:**
- ✅ **Secure by default** - validation always runs
- ✅ Catch errors before build (saves time)
- ✅ No extra command to remember
- ✅ Consistent with verification approach (enabled by default)

**Cons:**
- ❌ Cannot validate without building (but validation is fast)
- ❌ Adds small overhead to build time

**Recommended:** This approach aligns with the secure-by-default philosophy used for signature verification.

---

#### Option C: Validate-Only Flag

**Approach:** Add `--validate-only` flag to `lola build` command.

```bash
lola build [OPTIONS] <MODULE_PATH>

Arguments:
  <MODULE_PATH>           Path to module directory (default: current directory)

Options:
  -t, --tag <TAG>         OCI image tag (required unless --validate-only)
  --validate-only         Validate without building
  --skip-validation       Skip validation (not recommended)
  -h, --help             Show help

Examples:
  # Validate only (no build)
  lola build my-skill --validate-only

  # Build with automatic validation (default)
  lola build my-skill -t registry.io/org/skill:1.0.0

  # Skip validation (not recommended)
  lola build my-skill -t registry.io/org/skill:1.0.0 --skip-validation

Output (--validate-only):
  Validating module: my-skill

  Module Structure:
    ✓ Module directory structure valid
    ✓ Found 3 skills, 2 commands, 1 agent

  Metadata Validation:
    ✓ skill.yaml: Schema valid
    ✓ SKILL.md frontmatter: All valid

  ✓ Validation successful (1 warning)

  To build: lola build my-skill -t registry.io/org/skill:1.0.0
```

**Pros:**
- ✅ Single command for both validation and building
- ✅ Validation always runs by default
- ✅ Can validate without building using flag

**Cons:**
- ❌ Flag syntax slightly less intuitive than separate command
- ❌ Overloads `lola build` with multiple responsibilities

---

#### Validation Checks (All Options)

Regardless of implementation approach, validation performs these checks:

- **Module structure:** Verify skills/, commands/, agents/ directories
- **skill.yaml schema:** Validate against lola.io/v1 schema (if present)
- **SKILL.md frontmatter:** Parse and validate required fields (name, description)
- **File naming:** Check for invalid characters or naming conflicts
- **Duplicate components:** Detect duplicate skill/command/agent names
- **Required files:** Ensure SKILL.md exists for each skill
- **Version semantics:** Validate semantic version format

---

#### Recommendation

**Option B (Integrated Validation)** is recommended because:
1. Aligns with secure-by-default philosophy (like signature verification)
2. Prevents invalid modules from being built
3. No extra command to remember
4. Can be skipped with `--skip-validation` for advanced use cases

If validation-only capability is needed, **Option C** provides the best of both worlds.

---

### `lola push` - Push OCI Artifact to Registry

**Purpose:** Push a built OCI artifact to a container registry.

**Note:** Authentication is delegated to podman/skopeo/docker. Use `podman login <registry>` before pushing. The `--registry-config` option allows overriding the default auth location if needed.

```bash
lola push [OPTIONS] <SOURCE> <DESTINATION>

Arguments:
  <SOURCE>               Source OCI artifact location:
                         - OCI layout directory (e.g., .lola/build/my-skill)
                         - oci:<path> - Explicit OCI layout reference
                         - oci-archive:<path> - OCI archive tar file
  <DESTINATION>          Registry reference (e.g., registry.io/org/skill:1.0.0)

Options:
  --registry-config <PATH>  Path to registry auth config (default: ~/.docker/config.json)
  --insecure               Allow insecure registry connections
  --skip-tls-verify        Skip TLS verification (not recommended)
  -h, --help              Show help

Examples:
  # Push from default build output
  lola push .lola/build/my-skill registry.io/myorg/my-skill:1.0.0

  # Push with explicit OCI layout reference
  lola push oci:.lola/build/my-skill registry.io/myorg/my-skill:1.0.0

  # Push from OCI archive
  lola push oci-archive:./my-skill.tar registry.io/myorg/my-skill:1.0.0

  # Push with custom auth config (override default)
  lola push .lola/build/my-skill registry.io/myorg/my-skill:1.0.0 --registry-config ~/custom-auth.json

  # Push to local registry (development)
  lola push .lola/build/my-skill localhost:5000/my-skill:dev --insecure

Output:
  ✓ Authenticating with registry.io...
  ✓ Pushing layer sha256:abc123... (1.2 KB)
  ✓ Pushing layer sha256:def456... (45 KB)
  ✓ Pushing layer sha256:ghi789... (8 KB)
  ✓ Pushing manifest sha256:jkl012...
  ✓ Published: registry.io/myorg/my-skill:1.0.0
  ✓ Digest: sha256:jkl012mno345...
```

### `lola sign` - Sign OCI Artifact

**Purpose:** Cryptographically sign an OCI artifact using Cosign.

**IMPORTANT:** This command signs **remote images** already in a registry. The image must be pushed to the registry before signing. Signatures are uploaded to the registry alongside the image.

```bash
lola sign [OPTIONS] <IMAGE_REF>

Arguments:
  <IMAGE_REF>            Registry reference to REMOTE image (must be pushed first)
                         Example: registry.io/org/skill:1.0.0

Options:
  --key <PATH>           Path to private key (default: keyless with OIDC)
  --identity <IDENTITY>  OIDC identity for keyless signing
  --issuer <URL>         OIDC issuer URL (default: GitHub)
  --rekor-url <URL>      Rekor transparency log URL (default: public instance)
  --no-rekor             Don't upload signature to transparency log
  --yes                  Skip confirmation prompts
  -h, --help            Show help

Examples:
  # Standard workflow: build → push → sign
  lola build my-skill -t registry.io/myorg/skill:1.0.0
  lola push .lola/build/my-skill registry.io/myorg/skill:1.0.0
  lola sign registry.io/myorg/skill:1.0.0  # Signs remote image

  # Keyless signing (OIDC, recommended)
  lola sign registry.io/myorg/my-skill:1.0.0

  # Keyless signing with explicit OIDC settings
  lola sign registry.io/myorg/my-skill:1.0.0 \
    --identity user@example.com \
    --issuer https://github.com/login/oauth

  # Sign with private key
  lola sign registry.io/myorg/my-skill:1.0.0 --key ~/.lola/cosign.key

  # Sign without transparency log (not recommended)
  lola sign registry.io/myorg/my-skill:1.0.0 --no-rekor --yes

Output:
  ✓ Signing with OIDC identity: user@example.com
  ✓ Opening browser for authentication...
  ✓ OIDC authentication successful
  ✓ Generating ephemeral key pair...
  ✓ Signing manifest sha256:jkl012...
  ✓ Uploading signature to Rekor transparency log...
  ✓ Signature uploaded: https://rekor.sigstore.dev/api/v1/log/entries/abc123
  ✓ Artifact signed: registry.io/myorg/my-skill:1.0.0
```

### `lola verify` - Verify OCI Artifact Signatures

**Purpose:** Verify signatures and provenance of an OCI artifact.

```bash
lola verify [OPTIONS] <IMAGE_REF>

Arguments:
  <IMAGE_REF>                   OCI image reference to verify

Options:
  --certificate-identity <ID>   Expected certificate identity (regex)
  --certificate-oidc-issuer <URL> Expected OIDC issuer
  --key <PATH>                  Public key path (for key-based verification)
  --require-provenance          Require SLSA provenance attestation
  --allowed-builder <REGEX>     Allowed builder identity (regex)
  --policy <PATH>               Path to policy file
  -h, --help                   Show help

Examples:
  # Verify keyless signature
  lola verify registry.io/myorg/my-skill:1.0.0 \
    --certificate-identity="^user@example\\.com$" \
    --certificate-oidc-issuer="https://github.com/login/oauth"

  # Verify Red Hat signature
  lola verify oci://registry.io/redhat/skills/cve-remediation:1.0.0 \
    --certificate-identity="^https://github\\.com/redhat/.*" \
    --require-provenance \
    --allowed-builder="^https://github\\.com/redhat/.*"

  # Verify with public key
  lola verify registry.io/myorg/my-skill:1.0.0 --key ~/.lola/cosign.pub

  # Verify with policy file
  lola verify registry.io/myorg/my-skill:1.0.0 --policy .lola/verify-policy.yaml

Output:
  ✓ Verifying signature for registry.io/myorg/my-skill:1.0.0
  ✓ Signature valid: signed by user@example.com
  ✓ Transparency log entry verified: https://rekor.sigstore.dev/api/v1/log/entries/abc123
  ✓ SLSA provenance found and verified
  ✓ Builder: https://github.com/myorg/my-skill/.github/workflows/build.yml
  ✓ Source: https://github.com/myorg/my-skill@abc123def456
  ✓ Verification successful
```

### `lola inspect` - Inspect OCI Artifact Metadata

**Purpose:** Display metadata and annotations of an OCI artifact without installing.

```bash
lola inspect [OPTIONS] <IMAGE_REF>

Arguments:
  <IMAGE_REF>            OCI image reference to inspect

Options:
  --format <FORMAT>      Output format: table, json, yaml (default: table)
  --show-layers          Show detailed layer information
  --show-annotations     Show all OCI annotations
  -h, --help            Show help

Examples:
  # Inspect OCI artifact
  lola inspect registry.io/lola/document-skills:2.0.0

  # Inspect with layer details
  lola inspect registry.io/lola/document-skills:2.0.0 --show-layers

  # Output as JSON
  lola inspect registry.io/lola/document-skills:2.0.0 --format json

Output:
  OCI Artifact: registry.io/lola/document-skills:2.0.0

  Metadata:
    Digest:      sha256:abc123def456...
    Created:     2026-04-29T10:00:00Z
    Version:     2.0.0
    License:     MIT
    Source:      https://github.com/lola-project/document-skills
    Revision:    abc123def456

  Skills (3):
    - summarizer          (document processing)
    - translator          (language translation)
    - formatter           (document formatting)

  Commands (2):
    - export
    - convert

  Agents (1):
    - document-analyzer

  Signature Status:
    ✓ Signed by: user@example.com
    ✓ Transparency log: verified

  Provenance:
    ✓ SLSA Level: 3
    ✓ Builder: GitHub Actions
    ✓ Source: https://github.com/lola-project/document-skills@abc123
```

---

## Possible Command Modifications

These modifications show how existing commands could be enhanced to support OCI artifacts while maintaining backward compatibility.

### `lola mod add` - Enhanced to Support OCI Sources

**Potential Changes:** Add OCI registry support alongside existing Git/Zip/Tar/Folder sources

**Current Behavior:** `lola mod add <source>` registers modules from Git, Zip, Tar, or local folders to `~/.lola/modules/`

**Proposed Enhancement:** Support OCI registry references as sources

```bash
lola mod add [OPTIONS] <SOURCE>

Arguments:
  <SOURCE>               Source URL or path
                         - OCI: oci://registry.io/org/skill:1.0.0
                         - Git: https://github.com/user/repo.git
                         - Zip: https://example.com/skill.zip
                         - Tar: https://example.com/skill.tar.gz
                         - Folder: ./local-skill/

Options:
  # Security options (OCI only)
  --skip-verification     Skip signature and provenance verification (not recommended)
  --allowed-identity <REGEX> Allowed signer identity pattern (default: any valid signature)
  --pin-digest            Store immutable digest reference (default: true for OCI)

  # General options
  -h, --help             Show help

Security Defaults for OCI Modules:
  ✓ Signature verification: ENABLED by default
  ✓ Provenance verification: ENABLED by default (if attestation exists)
  ✓ Digest pinning: ENABLED by default

  Use --skip-verification to disable (shows prominent warning)

Examples:
  # Add from OCI registry (signature verified by default)
  lola mod add oci://registry.io/lola/document-skills:2.0.0

  # Add from OCI with identity constraint
  lola mod add oci://registry.io/redhat/skills/cve-remediation:1.0.0 \
    --allowed-identity="^https://github\\.com/redhat/.*"

  # Skip verification for development/testing (NOT RECOMMENDED)
  lola mod add oci://localhost/my-skill:dev --skip-verification

  # Add from Git (backward compatible, no verification)
  lola mod add https://github.com/lola-project/skills/document-analyzer.git

  # Add from Zip
  lola mod add https://example.com/modules/my-skill.zip

  # Add from local folder
  lola mod add ./modules/my-skill

Output (with verification):
  ✓ Resolving source: oci://registry.io/lola/document-skills:2.0.0
  ✓ Pulling OCI artifact...
  ✓ Digest: sha256:abc123def456...
  ✓ Verifying signature...
  ✓ Signature valid: signed by user@example.com
  ✓ Verifying provenance...
  ✓ Provenance valid: SLSA Level 3
  ✓ Module added: document-skills (2.0.0)
  ✓ Format: OCI
  ✓ Signed: ✓ (user@example.com)
  ✓ SLSA: Level 3

  To install:
    lola install document-skills -a claude-code

Output (with --skip-verification):
  ⚠️  WARNING: Signature verification disabled
  ⚠️  This module has not been verified and may be untrusted
  ⚠️  Only use --skip-verification for development or trusted sources

  ✓ Resolving source: oci://localhost/my-skill:dev
  ✓ Pulling OCI artifact...
  ✓ Digest: sha256:xyz789...
  ⚠️  Module added WITHOUT verification: my-skill (dev)
  ✓ Format: OCI
  ✗ Signed: Not verified
  ✗ SLSA: Not verified

  To install:
    lola install my-skill -a claude-code
```

**Registry Storage:**

OCI modules are stored with metadata in the module registry:
```json
{
  "name": "document-skills",
  "version": "2.0.0",
  "format": "oci",
  "source": "oci://registry.io/lola/document-skills:2.0.0",
  "digest": "sha256:abc123def456...",
  "signature": {
    "verified": true,
    "signer": "user@example.com",
    "slsa_level": 3
  },
  "added_date": "2026-04-29T10:00:00Z"
}
```

---

### `lola install` - Enhanced with OCI-Aware Installation

**Potential Changes:** Add mode detection and OCI-specific installation strategies

**Current Behavior:** `lola install <module> -a <assistant>` installs a registered module to the specified assistant

**Proposed Enhancement:** Support deployment mode selection for different environments

**Important:** For **local mode** (default), OCI modules are unpacked to the filesystem just like Git/Zip/Tar modules. The installation process extracts the OCI artifact contents and generates assistant-specific files. For **container mode**, OCI images are volume-mounted without unpacking. For **cloud mode**, deployment depends on the target platform.

```bash
lola install [OPTIONS] <MODULE>

Arguments:
  <MODULE>               Module name from registry (use 'lola mod ls' to see available)

Options:
  -a, --assistant <NAME>  Target assistant (claude-code, cursor, gemini-cli, openclaw, opencode)
  --mode <MODE>           Deployment mode: local, container, cloud (default: local)

  # Container mode options
  --output <PATH>         Output manifest file for container mode
  --manifest-type <TYPE>  kubernetes, docker-compose (default: kubernetes)

  # Cloud mode options (future enhancements)
  --namespace <NS>        Kubernetes namespace (cloud mode)
  --operator              Install via Kubernetes operator (future concept - not on roadmap)

  # General options
  --force                 Overwrite existing installation
  -h, --help             Show help

Examples:
  # Install from registry (current behavior, default mode)
  lola install document-skills -a claude-code

  # Container mode - generate Kubernetes manifest
  lola install code-tools --mode container --output opencode-deployment.yaml

  # Cloud mode - install to OpenShift cluster
  lola install cve-remediation --mode cloud --namespace ai-workloads

Output (local mode - OCI module unpacked to filesystem):
  ✓ Installing module: document-skills (2.0.0)
  ✓ Source: oci://registry.io/lola/document-skills:2.0.0
  ✓ Pulling OCI artifact...
  ✓ Extracting OCI layers to temp directory
  ✓ Generating assistant-specific files
  ✓ Copying to: ~/.claude/skills/
  ✓ Installed 3 skills: summarizer, translator, formatter
  ✓ Installed 2 commands: export, convert

  Note: OCI modules are unpacked to the filesystem for local installation

Output (container mode - OCI image volume-mounted, NOT unpacked):
  ✓ Installing module: code-tools (1.5.0)
  ✓ Source: oci://registry.io/lola/code-tools:1.5.0
  ✓ Generating Kubernetes manifest with ImageVolume
  ✓ Written to: opencode-deployment.yaml

  Note: Container mode mounts OCI image as read-only volume (no unpacking)

  Next steps:
    kubectl apply -f opencode-deployment.yaml

Output (cloud mode - using Job approach):
  ✓ Installing module: cve-remediation (1.0.0)
  ✓ Verifying signature: ✓ (signed by Red Hat)
  ✓ Creating Kubernetes Job in namespace: ai-workloads
  ✓ Job created: install-cve-remediation

  Next steps:
    oc logs -n ai-workloads job/install-cve-remediation
    oc get jobs -n ai-workloads

Output (cloud mode - hypothetical operator approach, not on roadmap):
  ✓ Installing module: cve-remediation (1.0.0)
  ✓ Verifying signature: ✓ (signed by Red Hat)
  ✓ Creating SkillInstallation resource in namespace: ai-workloads
  ✓ Skill installed successfully
```

### `lola mod ls` - Enhanced Output for OCI Modules

**Potential Changes:** Display digest and signature verification status for OCI modules

**Note:** The `lola mod ls` command continues to work as it does today. The only change is that OCI modules will display additional metadata fields.

```bash
# Command remains unchanged
lola mod ls

Output:
  Modules (3):

  document-skills (2.0.0)
    Format:    OCI
    Source:    registry.io/lola/document-skills:2.0.0
    Digest:    sha256:abc123def456...
    Signed:    ✓ (user@example.com)
    SLSA:      Level 3
    Installed: ~/.claude/skills/ (3 skills, 2 commands, 1 agent)
    Date:      2026-04-29 10:00:00

  git-workflow (1.0.0)
    Format:    Git
    Source:    https://github.com/lola-project/git-workflow.git
    Commit:    abc123def456
    Installed: ~/.claude/commands/ (5 commands)
    Date:      2026-04-28 15:30:00

  local-dev-tools (dev)
    Format:    Folder
    Source:    ./modules/local-dev-tools
    Installed: ~/.claude/skills/ (2 skills)
    Date:      2026-04-27 09:15:00
```

**OCI-Specific Fields:**
- `Format: OCI` - Indicates module source format
- `Digest` - Immutable content-addressable identifier (sha256)
- `Signed` - Signature verification status with signer identity
- `SLSA` - Supply chain security level (if provenance attestation exists)

---

## Workflow Pattern: Add Then Install

**Important Architectural Note:** To maintain consistency with Lola's current behavior, the workflow for OCI modules follows the existing two-step pattern:

1. **`lola mod add <source>`** - Registers the module to `~/.lola/modules/` (local module registry)
2. **`lola install <module> -a <assistant>`** - Installs from registry to the specified assistant

This pattern applies to **all formats** (OCI, Git, Zip, Tar, folder):

```bash
# Step 1: Add to registry (any format)
lola mod add oci://registry.io/lola/document-skills:2.0.0
lola mod add https://github.com/user/repo.git
lola mod add https://example.com/module.zip

# Step 2: Install from registry (format-agnostic)
lola install document-skills -a claude-code
lola install repo -a claude-code
lola install module -a claude-code
```

**Benefits of this approach:**
- **Consistency:** Same workflow for all formats
- **Caching:** Modules are pulled once, installed many times
- **Verification:** Signature/provenance checks happen at `mod add` time
- **Registry Management:** Central place to manage all modules (`lola mod ls`)
- **Offline Installation:** Once added, modules can be installed without network access

**OCI-Specific Enhancements:**
- **Secure by default:** Signature and provenance verification enabled automatically
- Digest pinning enabled by default for immutable references
- Identity constraints with `--allowed-identity` for enterprise policies
- OCI metadata (digest, signature status, SLSA level) stored in registry
- Development opt-out with `--skip-verification` (shows prominent warnings)

---

## Marketplace and OCI Format Integration

**Key Architectural Clarification:** Marketplaces and OCI format serve different purposes in Lola's architecture:

- **Marketplaces** = Discovery/catalog layer (YAML files listing available modules)
- **OCI format** = Distribution/storage layer (how skill content is packaged and delivered)

These layers are independent and complementary.

### Marketplaces are Source-Agnostic

Marketplaces contain YAML catalogs that reference modules distributed via **any format** (OCI, Git, Zip, Tar). The `repository` field simply contains the source URL:

```yaml
# marketplace.yml
name: Lola Community Marketplace
version: 1.0.0
modules:
  # Module distributed via OCI
  - name: document-skills
    version: 2.0.0
    repository: oci://registry.io/lola/document-skills:2.0.0
    description: Document processing skills
    tags: [document, processing]

  # Module distributed via Git
  - name: git-workflow
    version: 1.0.0
    repository: https://github.com/lola-project/git-workflow.git
    description: Git workflow automation
    tags: [git, workflow]

  # Module distributed via Zip
  - name: local-tools
    version: 1.5.0
    repository: https://downloads.example.com/local-tools.zip
    description: Local development tools
    tags: [dev, tools]
```

### No Impact on Marketplace Configuration

Adding OCI format support requires **no changes** to marketplace structure:

- ✅ **Same YAML structure** - No schema changes
- ✅ **Same `repository` field** - Contains `oci://` URLs instead of `https://` Git URLs
- ✅ **Same discovery workflow** - `lola mod search` works identically
- ✅ **Auto-install still works** - `lola install <module>` detects source format automatically

### Discovery → Distribution → Consumption Flow

```bash
# 1. User searches marketplace (discovery layer)
lola mod search document

# Output shows modules from marketplace catalog:
#   document-skills (2.0.0)
#     Source: oci://registry.io/lola/document-skills:2.0.0
#     Tags: document, processing

# 2. User installs (Lola auto-detects OCI format from repository field)
lola install document-skills -a claude-code

# Behind the scenes:
#   - Lola reads marketplace catalog entry
#   - Sees repository: oci://registry.io/lola/document-skills:2.0.0
#   - Automatically runs OCI-specific installation logic:
#     a. Verifies signature (if enabled)
#     b. Pulls OCI artifact from registry
#     c. Unpacks to filesystem (local mode)
#     d. Generates assistant-specific files
```

### Example: Multi-Format Marketplace

A single marketplace can contain modules distributed via different formats:

```yaml
name: Enterprise Skills Marketplace
version: 1.0.0
modules:
  # Signed OCI artifacts (preferred for production)
  - name: security-scanner
    version: 3.0.0
    repository: oci://registry.io/enterprise/security-scanner:3.0.0
    tags: [security, signed, verified]

  # Git repositories (for open development)
  - name: community-tools
    version: 1.5.0
    repository: https://github.com/community/tools.git
    tags: [community, development]

  # Archive files (for air-gapped environments)
  - name: offline-analyzer
    version: 2.0.0
    repository: https://downloads.internal.com/offline-analyzer.tar.gz
    tags: [offline, internal]
```

**User experience is identical** regardless of distribution format:

```bash
# Search finds all modules
lola mod search security
# Shows: security-scanner (OCI), community-tools (Git), offline-analyzer (Tar)

# Install works the same way
lola install security-scanner -a claude-code   # Auto-detects OCI
lola install community-tools -a claude-code    # Auto-detects Git
lola install offline-analyzer -a claude-code   # Auto-detects Tar
```

### Key Benefits

1. **Format flexibility** - Organizations choose distribution method per module based on requirements
2. **No migration required** - Existing Git/Zip/Tar marketplaces continue working
3. **Gradual adoption** - Add OCI modules to marketplace without disrupting existing entries
4. **Unified discovery** - Users search once, find modules regardless of distribution format

---

## CLI Examples by Use Case

### Use Case 1: Developer Building and Publishing a Skill

```bash
# 1. Create skill module (standard Lola structure)
mkdir -p my-skill/skills/analyzer

cat > my-skill/skills/analyzer/SKILL.md <<'EOF'
---
name: analyzer
description: Analyze code for improvements
tools:
  - read_file
  - grep
  - bash
categories:
  - code-analysis
license: MIT
---

# Code Analyzer

This skill analyzes code and suggests improvements.

## What it does
- Reads source files
- Searches for patterns
- Executes analysis commands
EOF

# 2. Validate module structure
# See "Module Validation" section for three implementation options (A, B, C)
# Recommended: Option B (integrated validation) - validation runs automatically during build

# Using recommended Option B (integrated validation):
lola build my-skill -t registry.io/myorg/code-analyzer:1.0.0
# Building module: my-skill
#
# Validation:
#   ✓ Module structure valid
#   ✓ Found 1 skill
#   ✓ SKILL.md frontmatter valid
#
# Building OCI artifact:
#   ✓ Generating skill.yaml from SKILL.md frontmatter...
#   (continues with build process)

# 3. Test locally
lola install oci://localhost/code-analyzer:1.0.0 -a claude-code --force
# ✓ Installed to ~/.claude/skills/

# 4. Publish to registry
lola push .lola/build/my-skill registry.io/myorg/code-analyzer:1.0.0
# ✓ Published: registry.io/myorg/code-analyzer:1.0.0

# 5. Sign artifact
lola sign registry.io/myorg/code-analyzer:1.0.0
# ✓ Artifact signed

# 6. Verify it works
lola verify registry.io/myorg/code-analyzer:1.0.0 \
  --certificate-identity="user@myorg.com"
# ✓ Verification successful
```

### Use Case 2: Enterprise User Installing Verified Skill

```bash
# 1. Search for Red Hat skills (uses marketplace search in initial version)
# Direct OCI registry search is a future enhancement
lola mod search security

# 2. Inspect skill before adding to registry
lola inspect registry.io/redhat/skills/cve-remediation:1.0.0
# Shows: metadata, skills, signature status, provenance

# 3. Add to module registry (verification automatic, with identity constraint)
lola mod add oci://registry.io/redhat/skills/cve-remediation:1.0.0 \
  --allowed-identity="^https://github\\.com/redhat/.*"
# ✓ Resolving source: oci://registry.io/redhat/skills/cve-remediation:1.0.0
# ✓ Pulling OCI artifact...
# ✓ Verifying signature...
# ✓ Signature valid: signed by https://github.com/redhat/skills
# ✓ Identity matches policy: ^https://github\.com/redhat/.*
# ✓ Verifying provenance...
# ✓ Provenance valid: SLSA Level 3
# ✓ Module added: cve-remediation (1.0.0)
# ✓ Format: OCI
# ✓ Signed: ✓ (https://github.com/redhat/skills)
# ✓ SLSA: Level 3

# 4. Install to assistant (uses cached module from registry)
lola install cve-remediation -a claude-code
# ✓ Installing from registry: cve-remediation (1.0.0)
# ✓ Installed to ~/.claude/skills/

# 5. List modules (signature and SLSA info always shown for OCI modules)
lola mod ls
# Shows digest, signature, and SLSA level for OCI modules

# Optional: Explicitly verify before adding (if you want to check first)
# lola verify registry.io/redhat/skills/cve-remediation:1.0.0 \
#   --certificate-identity="^https://github\\.com/redhat/.*"
```

### Use Case 3: DevOps Creating Containerized Deployment

```bash
# 1. Add module to registry
lola mod add oci://registry.io/lola/code-tools:1.5.0

# 2. Generate container deployment manifest
lola install code-tools \
  --mode container \
  --output opencode-deployment.yaml

# 3. Review generated manifest
cat opencode-deployment.yaml
# Shows Kubernetes Pod with ImageVolume

# 4. Deploy to cluster
kubectl apply -f opencode-deployment.yaml

# 5. Verify deployment
kubectl get pods -l app=opencode
kubectl describe pod opencode-agent
```

### Use Case 4: Platform Admin Installing to RHOAI

**Note:** This use case shows two approaches - a practical approach using Kubernetes Jobs (available today) and a conceptual operator-based approach (future vision, not on roadmap).

#### Approach A: Using Kubernetes Job (Practical)

```bash
# 1. Create Kubernetes Job to run Lola installation
cat <<EOF | oc apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: install-cve-skill
  namespace: ai-workloads
spec:
  template:
    spec:
      containers:
      - name: lola-installer
        image: registry.io/lola/lola-cli:latest
        command:
        - /bin/sh
        - -c
        - |
          # Add module with verification
          lola mod add oci://registry.io/redhat/skills/cve-remediation:1.0.0 \
            --allowed-identity="^https://github\\.com/redhat/.*"

          # Install to shared volume (for AI agent to access)
          lola install cve-remediation -a opencode --force

          # Copy to ConfigMap or shared storage
          oc create configmap cve-skill --from-file=/root/.opencode/
        env:
        - name: LOLA_HOME
          value: /workspace/.lola
        volumeMounts:
        - name: workspace
          mountPath: /workspace
      volumes:
      - name: workspace
        emptyDir: {}
      restartPolicy: Never
EOF

# 2. Check job status
oc get jobs -n ai-workloads

# 3. View installation logs
oc logs -n ai-workloads job/install-cve-skill

# 4. Verify skill installed (check ConfigMap or shared volume)
oc get configmap cve-skill -n ai-workloads
```

#### Approach B: Using Kubernetes Operator (Future Vision - Not on Roadmap)

**This approach envisions a future Lola operator that doesn't currently exist and is not on the implementation roadmap.**

```bash
# Hypothetical operator-based workflow:

# 1. Add verified module to registry (verification automatic)
lola mod add oci://registry.io/redhat/skills/cve-remediation:1.0.0 \
  --allowed-identity="^https://github\\.com/redhat/.*"

# 2. Create SkillInstallation CRD (operator watches for this)
cat <<EOF | oc apply -f -
apiVersion: lola.io/v1
kind: SkillInstallation
metadata:
  name: cve-remediation
  namespace: ai-workloads
spec:
  source:
    oci:
      image: registry.io/redhat/skills/cve-remediation:1.0.0
  verification:
    requireSignature: true
    allowedIdentities:
      - "^https://github\\.com/redhat/.*"
  target:
    agent: opencode-cluster-agent
EOF

# 3. Check installation status
oc get skillinstallation -n ai-workloads

# 4. Describe skill
oc describe skillinstallation cve-remediation -n ai-workloads

# 5. List all skills on cluster
oc get skills
```

**Note:** The operator approach (Approach B) is a future concept that would require:
- Custom Lola Kubernetes operator implementation
- `SkillInstallation` and `Skill` CRDs
- Operator logic to reconcile skill installations
- Integration with cluster RBAC and policies

This is not currently planned for implementation. Use Approach A (Kubernetes Job) for practical cloud deployments.

### Use Case 5: Creating Custom Skill Bundle (Shopping Cart)

**Note:** This use case demonstrates a future feature. The `lola bundle create` command is planned for Phase 4 implementation. See [Future Enhancements](#future-enhancements-not-for-initial-version) for details.

```bash
# 1. Browse available skills
lola mod search document
lola mod search code

# 2. Inspect skills to understand contents
lola inspect registry.io/lola/document-skills:2.0.0
lola inspect registry.io/lola/code-tools:1.5.0

# 3. Create custom bundle (FUTURE FEATURE)
lola bundle create my-workflow \
  --from registry.io/lola/document-skills:2.0.0 --select skills/summarizer \
  --from registry.io/lola/document-skills:2.0.0 --select skills/translator \
  --from registry.io/lola/code-tools:1.5.0 --select skills/reviewer \
  --from registry.io/lola/git-workflow:1.0.0 --select commands/commit \
  -t registry.io/myorg/bundles/my-workflow:1.0.0 \
  --publish

# 4. Install custom bundle
lola install oci://registry.io/myorg/bundles/my-workflow:1.0.0 -a claude-code

# 5. Verify bundle contents
lola mod ls --installed
# Shows bundle with selected components
```

### Use Case 6: Multi-Format Installation (Format Agnostic)

```bash
# Add from different sources (format detection automatic)
lola mod add oci://registry.io/lola/document-skills:2.0.0
lola mod add https://github.com/lola-project/git-workflow.git
lola mod add https://downloads.example.com/skills/my-skill.zip
lola mod add ./modules/my-local-skill

# Install any module using same command (format-agnostic)
lola install document-skills -a claude-code
lola install git-workflow -a claude-code
lola install my-skill -a claude-code
lola install my-local-skill -a claude-code

# All produce identical user experience:
# ✓ Installing from registry: <module> (<version>)
# ✓ Installed to ~/.claude/skills/
```

---

## Error Handling

### Common Errors and Messages

#### Source Resolution Errors

```bash
$ lola install oci://invalid-registry/skill:1.0.0 -a claude-code
Error: Failed to resolve OCI image
  Image: invalid-registry/skill:1.0.0
  Reason: Registry not found

  Troubleshooting:
    - Check registry URL is correct
    - Verify network connectivity: ping invalid-registry
    - Check registry authentication: podman login invalid-registry (or docker login)
    - Test with podman/skopeo: podman pull oci://invalid-registry/skill:1.0.0

Exit code: 1
```

#### Verification Failures

```bash
$ lola install oci://registry.io/skill:1.0.0 -a claude-code --verify-signature
Error: Signature verification failed
  Image: registry.io/skill:1.0.0
  Reason: No valid signatures found

  Expected:
    - Certificate identity matching allowed pattern
    - Valid transparency log entry

  Found:
    - No signatures

  Options:
    - Remove --verify-signature flag to install without verification
    - Contact skill author to add signatures: lola sign <image>
    - Verify with custom policy: lola verify <image> --policy policy.yaml

Exit code: 2
```

#### Mode Detection Warnings

```bash
$ lola install oci://registry.io/skill:1.0.0
Warning: Could not auto-detect deployment mode

  Please specify mode explicitly:
    --mode local       (Install to local IDE)
    --mode container   (Generate container manifests)
    --mode cloud       (Deploy to Kubernetes cluster)

  Example:
    lola install oci://registry.io/skill:1.0.0 --mode local -a claude-code

Exit code: 0 (continues with prompt)
```

#### Build Validation Errors

```bash
$ lola build ./my-invalid-skill -t registry.io/skill:1.0.0
Error: Module validation failed
  Path: ./my-invalid-skill

  Issues found:
    ✗ skill.yaml: Missing required field 'metadata.version'
    ✗ skill.yaml: Invalid apiVersion 'v2' (expected 'lola.io/v1')
    ✗ skills/analyzer/SKILL.md: File not found
    ✗ skills/reviewer/SKILL.md: Frontmatter missing required field 'description'
    ! commands/test.md: Warning - No frontmatter found

  Tip: For single-skill modules, you can omit skill.yaml and use SKILL.md frontmatter instead.

Exit code: 1
```

---

## Configuration (Optional)

### Enterprise Policy Enforcement

**File:** `~/.lola/config.yaml` (optional)

Lola works with secure defaults and CLI flags for most use cases. Configuration files are **optional** and primarily useful for enterprise environments that need to enforce organization-wide security policies.

**Secure defaults (no config file needed):**
- Signature verification: **Enabled** for OCI modules (use `--skip-verification` flag to disable)
- Provenance verification: **Enabled** for OCI modules (use `--skip-provenance` flag to disable)
- Registry authentication: Delegated to `podman login`, `docker login`, or `skopeo login`
- Deployment mode: Auto-detected (use `--mode` flag to override)

**When you need a config file:**

Organizations can use `~/.lola/config.yaml` to enforce **identity constraints** on allowed signers and builders:

```yaml
# Optional: Enterprise policy enforcement
verification:
  # Only accept signatures from approved organizations
  allowed_identities:
    - "^https://github\\.com/myorg/.*"
    - "^https://github\\.com/redhat/.*"

  # Only accept builds from approved CI/CD pipelines
  allowed_builders:
    - "^https://github\\.com/.*/.github/workflows/.*"
```

**How identity constraints work:**
- If `allowed_identities` is set, only modules signed by matching identities are accepted
- If `allowed_builders` is set, only modules built by matching CI/CD systems are accepted
- If these are not set (or no config file exists), any valid signature/provenance is accepted
- These constraints cannot be bypassed with CLI flags (enforces enterprise policy)

### Registry Authentication (Delegated to OCI Tools)

Lola uses the underlying OCI tool's authentication mechanism. Configure registry access using standard OCI tooling:

```bash
# Using podman (recommended)
podman login registry.io
podman login ghcr.io

# Using docker
docker login registry.io
docker login ghcr.io

# Using skopeo
skopeo login registry.io
```

**Registry settings** (insecure registries, TLS verification) are also configured via the OCI tool:

```bash
# Podman/Skopeo: /etc/containers/registries.conf
[[registry]]
location = "localhost:5000"
insecure = true

# Docker: /etc/docker/daemon.json
{
  "insecure-registries": ["localhost:5000"]
}
```

### Environment Variables

Environment variables for overriding defaults:

```bash
# Deployment mode (override auto-detection)
export LOLA_MODE=local  # local, container, cloud

# OCI build settings (optional)
export LOLA_PLATFORM=linux/amd64  # Target platform for builds
export LOLA_COMPRESSION=zstd      # Compression algorithm for OCI layers
```

**Note:** Standard OCI environment variables (`REGISTRY_AUTH_FILE`, `DOCKER_CONFIG`, etc.) are respected when using the underlying OCI tools.

---

## Implementation Phasing

Per [ADR 0007](../0007-oci-format.md), the implementation follows these phases:

### Phase 0: Go Rewrite Foundation

**Scope:**
- Rewrite Lola core in Go
- Port existing Git/Zip/Tar/marketplace functionality
- Maintain CLI interface compatibility
- Integrate skillimage library for OCI support

**No New Commands:** This phase focuses on language migration and library integration.

### Phase 1: Initial OCI Support

**Commands:**

- `lola mod add oci://registry.io/org/module:version` - Add OCI modules to registry
- `lola install <module> -a <assistant>` - Install with OCI support (existing command enhanced)
- `lola inspect <oci-ref>` - Inspect OCI artifact metadata
- `lola mod ls` - Enhanced to show OCI digests and signature status

**Features:**
- OCI module addition via `lola mod add oci://...`
- **Signature and provenance verification** (enabled by default)
- Local IDE installation (unpack mode)
- Integration with existing marketplace search
- Digest pinning for immutable references

**Focus:** Format-agnostic installation with OCI as one option, secure by default

### Phase 2: Building and Distribution

**Commands:**

- `lola build <module> -t <tag>` - Build OCI artifacts (optional convenience)
- `lola push <source> <destination>` - Push to registry
- `lola sign <image-ref>` - Sign with Cosign

**Features:**
- Optional `lola build` command for creating OCI artifacts
- Registry publishing with `lola push`
- Cosign signing for supply chain security
- **Validation integrated into `lola build`** (Option B from validation discussion)

**Implementation Note:** Validation is integrated into `lola build` (secure by default). Use `--skip-validation` flag to bypass if needed.

**Focus:** Optional build commands for users who want Lola-based building

### Phase 3: Advanced Deployments

**Commands:**

- `lola install --mode container` - Generate container manifests
- `lola install --mode cloud` - Cloud platform deployment
- `lola verify <image-ref>` - Explicit verification command

**Features:**
- Container mode (volume mounting)
- Cloud platform installation
- Custom skill bundles
- Enhanced policy enforcement

**Focus:** Multi-mode deployment support

### Phase 4: Future Enhancements

**Commands:**

- `lola bundle create` - Custom skill bundles (see [Future Enhancements](#future-enhancements-not-for-initial-version))
- `lola mod search --source registry` - Direct OCI registry search (see [Future Enhancements](#future-enhancements-not-for-initial-version))

**Focus:** Shopping cart model and advanced discovery

**Note:** The `lola bundle` and enhanced `lola mod search` commands are detailed in the [Future Enhancements](#future-enhancements-not-for-initial-version) section.

---

## Future Enhancements (Not for Initial Version)

The following commands represent advanced features planned for future development phases but not included in the initial OCI format support implementation.

### `lola bundle` - Create Custom Skill Bundle

**Purpose:** Create a custom OCI bundle from selected skills/commands/agents across multiple modules (shopping cart model).

**Planned Timeline:** Phase 4 (Advanced Features)

```bash
lola bundle create [OPTIONS] <BUNDLE_NAME>

Arguments:
  <BUNDLE_NAME>          Name for the custom bundle

Options:
  --from <IMAGE_REF>     Source OCI image reference
  --select <PATH>        Component path to include (e.g., skills/summarizer)
  -t, --tag <TAG>        Tag for output bundle (default: registry.io/lola/bundles/<name>:latest)
  --publish              Publish bundle after creation
  -h, --help            Show help

Examples:
  # Create bundle from multiple sources
  lola bundle create my-workflow \
    --from registry.io/lola/document-skills:2.0.0 --select skills/summarizer \
    --from registry.io/lola/code-tools:1.5.0 --select skills/reviewer \
    --from registry.io/lola/git-workflow:1.0.0 --select commands/commit \
    -t registry.io/myorg/bundles/my-workflow:1.0.0

  # Create and publish bundle
  lola bundle create my-bundle \
    --from registry.io/lola/doc-skills:1.0.0 --select skills/pdf-generator \
    --from registry.io/lola/doc-skills:1.0.0 --select skills/xlsx-editor \
    --publish

  # List components in a bundle
  lola bundle list oci://registry.io/myorg/bundles/my-workflow:1.0.0

Output:
  ✓ Creating bundle: my-workflow
  ✓ Pulling source: registry.io/lola/document-skills:2.0.0
  ✓ Extracting: skills/summarizer
  ✓ Pulling source: registry.io/lola/code-tools:1.5.0
  ✓ Extracting: skills/reviewer
  ✓ Pulling source: registry.io/lola/git-workflow:1.0.0
  ✓ Extracting: commands/commit
  ✓ Building bundle with 2 skills, 1 command
  ✓ Bundle created: registry.io/myorg/bundles/my-workflow:1.0.0
  ✓ Digest: sha256:xyz789abc123...

  Bundle contents:
    skills/
      summarizer/          (from document-skills:2.0.0)
      reviewer/            (from code-tools:1.5.0)
    commands:
      commit.md            (from git-workflow:1.0.0)
```

### `lola mod search` - Enhanced with OCI Registry Search

**Purpose:** Add ability to search OCI registries directly in addition to marketplace catalogs.

**Planned Timeline:** Phase 3 or 4

**Current Behavior:** `lola mod search` searches marketplace YAML catalogs (which may contain references to OCI images, Git repos, etc.)

**Planned Enhancement:** Direct OCI registry search with registry-specific queries.

```bash
lola mod search [OPTIONS] <QUERY>

Arguments:
  <QUERY>                Search query

Options:
  --source <SOURCE>      Search source: marketplace, registry, all (default: marketplace)
  --registry <URL>       OCI registry to search (can specify multiple)
  --format <FORMAT>      Output format: table, json (default: table)
  -h, --help            Show help

Examples:
  # Search marketplaces (current behavior, default)
  lola mod search document

  # Search all sources (FUTURE FEATURE)
  lola mod search document --source all

  # Search specific OCI registry (FUTURE FEATURE)
  lola mod search document --source registry --registry registry.io/lola

  # Search multiple registries (FUTURE FEATURE)
  lola mod search security \
    --source registry \
    --registry registry.io/redhat \
    --registry ghcr.io/lola-project

Output:
  Found 5 modules matching "document":

  From: OCI Registry (registry.io/lola)
    ✓ document-skills:2.0.0
      - Skills: summarizer, translator, formatter (3)
      - Signed: ✓ | SLSA: Level 3
      - Source: oci://registry.io/lola/document-skills:2.0.0

    ✓ office-suite:1.0.0
      - Skills: pdf-generator, xlsx-editor (2)
      - Signed: ✓ | SLSA: Level 2
      - Source: oci://registry.io/lola/office-suite:1.0.0

  From: Marketplace (lola-community)
    document-analyzer:1.5.0
      - Skills: analyzer (1)
      - Source: https://github.com/community/document-analyzer.git

  To install:
    lola install oci://registry.io/lola/document-skills:2.0.0 -a claude-code
```

---

## Backward Compatibility

**All existing commands continue to work unchanged:**

```bash
# These still work exactly as before
lola install https://github.com/user/repo.git -a claude-code
lola install ./local-module -a cursor
lola mod add https://github.com/user/repo.git
lola mod ls
lola update
```

**No breaking changes** - OCI support is purely additive.

---

## Using This Document

This exploration document provides:

1. **Command Specifications** - Detailed syntax and options for potential new commands
2. **Usage Examples** - Real-world scenarios showing how commands might be used
3. **Error Handling** - Examples of error messages and troubleshooting flows
4. **Configuration Options** - Possible configuration file structures

**Next Steps for ADR Development:**

1. Review command structure and gather stakeholder feedback
2. Prioritize commands based on user needs and use cases
3. Decide on phasing approach (if any)
4. Finalize configuration schema
5. Create formal ADR with architectural decisions

---

**Document Type:** Technical Exploration / Reference Material
**Purpose:** Support future ADR development on OCI CLI extensions
**Status:** Draft for discussion
**Last Updated:** 2026-04-29