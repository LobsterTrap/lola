# Skills and Context Modules

Lola distributes two types of AI context packages: **Agent Skills** and **AI Context Modules**.

## Agent Skill

An Agent Skill is a standalone context file following the [AgentSkills.io](https://agentskills.io/specification) standard. It is the fundamental unit of AI context - a markdown file (`SKILL.md`) with optional supporting assets that can be loaded by an agent on demand for In-Context Learning (ICL).

```
my-skill/
  SKILL.md              # Required: skill definition
  scripts/              # Optional: executable scripts
  reference/            # Optional: documentation
  assets/               # Optional: other supporting files
```

A skill injects context into the LLM's runtime memory, guiding it to return more precise results. It translates your workflows and knowledge into transferable instructions an agent can execute.

## AI Context Module

An AI Context Module is a superset of a skill. It wraps one or more skills inside a `module/` directory alongside additional assets:

```
my-project/
  module/                   # AI Module Directory
    AGENTS.md               # AI Main Spec
    commands/               # Assistant Commands
    mcp.json                # MCP Settings
    my-skill-A/             # Skill following agentskills.io
      SKILL.md
      scripts/
      reference/
      assets/
    my-skill-N/             # Another Skill
      SKILL.md
      scripts/
      reference/
      assets/
```

SKILLs are not everything. We also need MCP settings, agent personas, system prompts, commands, or custom bootstrap dependencies. The AI Context Module solves this by packaging an entire AI context - multiple skills plus all the supporting configuration - into a single distributable unit.

AI Context Modules also solve the problem where a developer wants to integrate their codebase with AI context. A module can live inside a project, allowing skills to reference scripts, functions, or assets from the codebase itself. This is useful when you want to mix your codebase with agent knowledge - inheriting bootstrap scripts or utility functions into skills and commands. In this way, AI Context Modules extend skills to provide AI knowledge at a broader project level.

## When to Use Each

| | Agent Skill | AI Context Module |
|---|---|---|
| **Use case** | Single focused capability | Complete agent context |
| **Contents** | SKILL.md + optional assets | Multiple skills + AGENTS.md + commands + MCP |
| **Standard** | [AgentSkills.io](https://agentskills.io/specification) | Lola extension of the standard |
| **Example** | A code review skill | A full DevSecOps module with review, security, and compliance skills |
| **Init** | Manual or future `lola skill init` | `lola mod init` |

## AI as Code

The vision behind AI Context Modules is **AI as Code**: agent settings, MCP configurations, skills, and context dependencies - all managed as code, versioned, and distributable as packages. With Lola, your entire AI agent context tree can be deployed and shared across teams and tools.
