# Quick Start

## 1. Set up the official marketplace

```bash
lola market add general https://raw.githubusercontent.com/RedHatProductSecurity/lola-market/main/general-market.yml
```

## 2. Add a module

```bash
# From the marketplace
lola search git
lola install git-workflow

# Or from a git repository
lola mod add https://github.com/user/my-skills.git

# Or from a local folder
lola mod add ./my-local-skills
```

## 3. Install to your AI assistants

```bash
# Install to all detected assistants
lola install my-skills

# Install to a specific assistant
lola install my-skills -a claude-code

# Install to a specific project directory
lola install my-skills ./my-project
```

## 4. Declarative installation (optional)

Create a `.lola-req` file in your project root:

```
# .lola-req - AI context modules for this project
python-tools>=1.0.0
git-workflow>>claude-code
https://github.com/user/custom-module.git@main
```

Then sync all modules:

```bash
lola sync
```

## 5. Manage modules

```bash
# List registered modules
lola mod ls

# List installed modules
lola list

# Update module from source
lola mod update my-skills

# Regenerate assistant files
lola update
```

## Next Steps

- [Modules](../guides/modules.md) - Module structure and management
- [Marketplace](../guides/marketplace.md) - Discover and share skills
- [Creating Modules](../guides/creating-modules.md) - Build your own modules
