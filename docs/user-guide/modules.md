# Module Management

Lola modules (LoLaS) are portable packages of [skills and context](../concepts/skills-and-modules.md) for AI assistants. A module can contain a single skill, multiple skills, or a full AI Context Module with commands, agents, and MCP servers.

## Adding Modules

```bash
# From a git repository
lola mod add https://github.com/user/my-skills.git

# From a local folder
lola mod add ./my-local-skills

# From a zip or tar file
lola mod add ~/Downloads/skills.zip

# From a monorepo with custom content directory
lola mod add https://github.com/company/monorepo.git --module-content=packages/lola-skills

# From a flat repository (use root directory)
lola mod add https://github.com/user/flat-repo.git --module-content=/
```

## Managing Modules

```bash
# List registered modules
lola mod ls

# Show module details
lola mod info my-skills

# Update module from source
lola mod update my-skills

# Remove a module
lola mod rm my-skills
```

## Module Structure

Lola supports three module patterns:

### Single Skill

Follows the [agentskills.io](https://agentskills.io/specification) standard:

```
my-skill/
  SKILL.md           # Required
  scripts/           # Optional
```

### Skill Bundle

Multiple related skills packaged together:

```
my-bundle/
  skills/
    skill-a/SKILL.md
    skill-b/SKILL.md
```

### AI Context Module (recommended)

Complete module with instructions, skills, commands, and agents:

```
my-module/
  module/
    AGENTS.md        # Module-level instructions
    skills/
      skill-a/
        SKILL.md
        scripts/
    commands/
      review.md
    agents/
      helper.md
```

## Content Path Detection

Lola auto-detects where module content lives. It checks for a `module/` subdirectory first, then falls back to the repository root. Override with `--module-content`:

```bash
lola mod add https://github.com/company/monorepo.git --module-content=packages/ai-tools
```
