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
lola search authentication --remote

# Install directly from marketplace (auto-adds and installs)
lola install git-workflow -a claude-code
```

When a module exists in multiple marketplaces, Lola prompts you to select which one to use.

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
