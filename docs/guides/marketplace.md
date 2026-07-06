# Marketplace

The lola market is a federated catalog for discovering and distributing [skills and context modules](../concepts/skills-and-modules.md). Like DNF repositories for Linux packages, marketplaces let you search, install, and update modules from curated catalogs.

## Official Marketplace

We maintain an official, community-driven marketplace at [github.com/RedHatProductSecurity/lola-market](https://github.com/RedHatProductSecurity/lola-market).

```bash
lola market add general https://raw.githubusercontent.com/RedHatProductSecurity/lola-market/main/general-market.yml
```


## Search and Install

```bash
# Search the local registry and all enabled marketplaces
lola search authentication

# Limit to enabled marketplaces only
lola search authentication --market

# Install directly from marketplace (auto-adds and installs)
lola install git-workflow -a claude-code

# Install at a specific git ref (overrides the marketplace-pinned ref)
lola install git-workflow@v1.0.0 -a claude-code

# Install from a specific marketplace at a specific ref
lola install @my-marketplace/git-workflow@v1.0.0 -a claude-code
```

When a module exists in multiple marketplaces, Lola prompts you to select which one to use. The prompt shows each entry's pinned ref so you can make an informed choice.

Search results show a `Ref` column when any result has a pinned ref. After installing, `lola list` displays the resolved version and ref alongside each module:

```text
git-workflow
  - scope: project
    path: "/path/to/project"
    assistants: [claude-code]
    version: 2.0.0
    ref: v2.0.0
```

## Manage Marketplaces

```bash
# List registered marketplaces
lola market ls

# Update marketplace cache
lola market update general

# Update all marketplaces
lola market update

# Disable/enable a marketplace
lola market set --disable general
lola market set --enable general

# Remove a marketplace
lola market rm general
```

## Create Your Own Marketplace

Host a YAML file with this structure:

```yaml
name: My Marketplace
description: Curated collection of AI skills
version: 1.0.0
modules:
  - name: git-workflow
    description: Git workflow automation skills
    version: 1.0.0
    repository: https://github.com/user/git-workflow.git
    tags: [git, workflow]

  - name: monorepo-skills
    description: Skills from a monorepo
    version: 1.0.0
    repository: https://github.com/company/monorepo.git
    path: packages/lola-skills  # Custom content directory
    tags: [monorepo]
```

### Module Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Module name (used as the registry key) |
| `description` | ✅ | Short description shown in search results |
| `version` | ✅ | Version string (informational) |
| `repository` | ✅ | Git URL or archive URL to fetch from |
| `path` | — | Content subdirectory inside the repo (for monorepos) |
| `ref` | — | Git branch, tag, or commit SHA to pin (see below) |
| `tags` | — | List of tags for search/discovery |
| `hooks` | — | Pre/post install scripts |

### Pinning Modules to a Git Revision

Use the `ref` field to pin a module to a specific Git revision for supply-chain reproducibility:

```yaml
modules:
  # Pin to a release tag — stable, auditable
  - name: network-tools
    description: Network troubleshooting skills
    version: 2.0.0
    repository: https://github.com/partner-org/network-skills
    ref: v2.0.0
    tags: [networking]

  # Pin to a commit SHA — maximum reproducibility
  - name: verified-tools
    description: Skills validated at a known commit
    version: 1.2.0
    repository: https://github.com/org/tools
    ref: a1b2c3d4e5f6789012345678901234567890abcd
    path: packs/tools
    tags: [tools]

  # Pin to a branch — tracks branch head, less stable
  - name: dev-preview
    description: Skills from the development branch
    version: 0.9.0
    repository: https://github.com/org/tools
    ref: develop
    path: packs/tools
    tags: [preview]
```

`ref` accepts any valid Git reference: branch name, tag, or full/short commit SHA. When omitted, Lola fetches the repository's default branch (unchanged behavior).

Users can override the marketplace-pinned ref at install time:

```bash
# Override the ref defined in the marketplace YAML
lola install network-tools@main
```
