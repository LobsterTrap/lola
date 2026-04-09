# Home

**Write Agent Skills and Contexts once, use everywhere.**

Lola is a universal AI Context Package Manager. If an agent's skills were an RPM, Lola is the DNF for it. Write your [skills and context modules](concepts/skills-and-modules.md) once as portable packages, then install them to any AI assistant or agent with a single command.

As the shift from prompt engineering to context engineering accelerates, SKILLs have emerged as a standard for AI In-Context Learning (ICL). Lola centralizes the distribution of these [skills and context modules](concepts/skills-and-modules.md), solving the fragmentation across AI assistants.

```bash
# Write once
lola mod add https://github.com/myorg/compliance-skills.git

# Use everywhere
lola install compliance-skills

# Skills now in: Claude Code, Cursor, Gemini CLI, OpenCode
```

## Supported AI Assistants

| Assistant   | Skills                                  | Commands                          | Agents                          |
| ----------- | --------------------------------------- | --------------------------------- | ------------------------------- |
| Claude Code | `.claude/skills/<skill>/SKILL.md`       | `.claude/commands/<cmd>.md`       | `.claude/agents/<agent>.md`     |
| Cursor      | `.cursor/skills/<skill>/SKILL.md`       | `.cursor/commands/<cmd>.md`       | `.cursor/agents/<agent>.md`     |
| Gemini CLI  | `GEMINI.md`                             | `.gemini/commands/<cmd>.toml`     | N/A                             |
| OpenCode    | `AGENTS.md`                             | `.opencode/commands/<cmd>.md`     | `.opencode/agents/<agent>.md`   |

## Quick Install

```bash
uv tool install git+https://github.com/RedHatProductSecurity/lola
```

## Next Steps

- [Installation](getting-started/installation.md) - Prerequisites and setup options
- [Quick Start](getting-started/quick-start.md) - Get up and running in minutes
- [Guides](guides/modules.md) - Module management, marketplace, and more
- [CLI Reference](cli-reference/index.md) - Complete command reference
- [Skills and Modules](concepts/skills-and-modules.md) - Understanding skills vs context modules
- [Roadmap](concepts/roadmap.md) - Vision and where Lola is heading
