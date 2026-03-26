# Creating Modules

Lola modules can be a single [Agent Skill](https://agentskills.io/specification) or a full [AI Context Module](../concepts/skills-and-modules.md). An Agent Skill is a standalone `SKILL.md` with optional supporting files. An AI Context Module is a superset - it wraps one or more skills alongside `AGENTS.md`, `commands/`, and `mcp.json` inside a `module/` directory.

## Initialize an AI Context Module

```bash
lola mod init my-module
```

This creates the AI Context Module structure:

```
my-module/
  module/
    AGENTS.md           # AI main spec
    skills/
      example-skill/
        SKILL.md        # Skill following agentskills.io
    commands/
      example-command.md
    agents/
      example-agent.md
    mcps.json           # MCP settings
```

!!! note
    `lola mod init` currently creates only the AI Context Module pattern. Standalone Agent Skill initialization (`lola skill init`) is planned for a future release.

## Edit the skill

Edit your skill's `SKILL.md` following the [AgentSkills.io](https://agentskills.io/specification) standard:

```markdown
---
name: my-skill
description: When to use this skill
---

# My Skill

Instructions for the AI assistant...
```

## Add supporting files

Each skill can have its own `scripts/`, `reference/`, and `assets/` directories:

```
my-skill/
  SKILL.md
  scripts/           # Executable scripts
  reference/         # Documentation
  assets/            # Other supporting files
```

Reference them with relative paths in your `SKILL.md`:

```markdown
Use the helper script: `./scripts/helper.sh`
```

## Add an AGENTS.md

The `AGENTS.md` provides module-level context that applies across all skills in the module. This is what elevates a collection of skills into an AI Context Module.

## Add slash commands

Slash commands are custom commands that can be invoked with `/command-name` in AI assistants. Claude Code, Cursor, and Gemini CLI all support them. Create markdown files in `commands/`:

```markdown
---
description: Review a pull request
argument-hint: <pr-number>
---

Review PR #$ARGUMENTS and provide feedback.
```

Use `$ARGUMENTS` for all args or `$1`, `$2` for positional. Lola automatically converts commands to each assistant's native format (markdown for Claude Code and Cursor, TOML for Gemini CLI).

## Register and install

```bash
lola mod add ./my-module
lola install my-module
```

See [Skill Format](skill-format.md) for details on the SKILL.md specification.
