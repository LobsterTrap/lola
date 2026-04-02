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

## Appending Context References

When an AI Context Module has files that reference each other, for example an `AGENTS.md` that says:

```markdown
Follow the coding conventions in `context/conventions.md`
Run the setup script at `scripts/bootstrap.sh`
```

You can use `--append-context` so the agent reads the original file where these paths resolve naturally:

```bash
lola install my-module --append-context module/AGENTS.md
```

This appends a reference in `CLAUDE.md` pointing to the file inside `.lola/modules/`:

```markdown
<!-- lola:module:my-module:start -->
Read the module context from `.lola/modules/my-module/module/AGENTS.md`
<!-- lola:module:my-module:end -->
```

Without the flag, the default behavior copies content verbatim, which works well for modules without relative path references.

!!! note
    Using `--append-context` adds an extra layer of file reading for the agent - it first reads `CLAUDE.md`, then follows the reference to read the appended context file. For best performance, we recommend structuring your module to work with the default installation when possible, using `--append-context` only when your module requires relative path references between context files.

## Content Path Detection

Lola auto-detects where module content lives. It checks for a `module/` subdirectory first, then falls back to the repository root. Override with `--module-content`:

```bash
lola mod add https://github.com/company/monorepo.git --module-content=packages/ai-tools
```
