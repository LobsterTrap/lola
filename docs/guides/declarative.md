# Declarative Module Management

Instead of installing modules one at a time, manage all your project's AI context modules declaratively using a `.lola-req` file. This works like `requirements.txt` for pip or `package.json` for npm.

## Create a .lola-req

Create a `.lola-req` in your project root with one module per line:

```
# .lola-req - AI context modules for this project

# Module names from registry or marketplace
python-tools>=1.0.0
git-workflow

# Target specific assistants
web-scraper>>claude-code
code-review>>cursor

# Direct git URLs
https://github.com/user/custom-module.git
git+https://github.com/user/another-module.git

# Git URLs with branch/tag references
https://github.com/user/module.git@main
git+https://github.com/user/module.git@v1.0.0
```

## Sync Modules

```bash
# Install all modules from .lola-req
lola sync

# Dry-run to see what would be installed
lola sync --dry-run
```

The sync command is **idempotent** - running it multiple times produces the same result.

## Version Constraints

- `==1.0.0` - Exact version
- `>=1.0.0` - Greater than or equal
- `~1.2.0` - Compatible with 1.2.x (>= 1.2.0, < 1.3.0)
- `^1.2.0` - Compatible with 1.x.x (>= 1.2.0, < 2.0.0)

## Assistant Targeting

Use `>>` to target specific assistants:

```
module-name>>claude-code    # Install only to Claude Code
module-name>>cursor         # Install only to Cursor
module-name                 # Install to all detected assistants
```
