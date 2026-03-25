# Skill Format

SKILLs follow the [AgentSkills.io](https://agentskills.io/specification) standard - markdown context files that can be loaded by AI agents on demand for In-Context Learning (ICL).

## SKILL.md

Every skill requires a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: skill-name
description: When to use this skill
---

# Skill Title

Your instructions, workflows, and guidance for the AI assistant.

Reference supporting files using relative paths:
- `./scripts/helper.sh`
- `./reference/example.md`
```

## Agent Skill Structure

A standalone Agent Skill follows the [AgentSkills.io](https://agentskills.io/specification) standard:

```
my-skill/
  SKILL.md              # Required
  scripts/              # Optional: executable scripts
  references/           # Optional: documentation
  assets/               # Optional: other supporting files
```

## Command Files

Commands use YAML frontmatter with argument variables:

- `$ARGUMENTS` - All arguments as a single string
- `$1`, `$2`, `$3`... - Positional arguments

Commands are automatically converted to each assistant's native format.

## Learn More

- [Skills and Modules](../concepts/skills-and-modules.md) - Understanding the difference between Agent Skills and AI Context Modules
- [AgentSkills.io Specification](https://agentskills.io/specification) - The standard SKILL format
