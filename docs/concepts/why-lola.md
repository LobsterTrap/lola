# Why Lola?

The AI skills ecosystem is growing fast and there are already many great tools in this space. Lola is not trying to compete with them — it has a specific mission: **AI as Code**.

!!! quote ""
    If a Skill were a package, Lola would be the package manager for it. If an agent's skills were an RPM, Lola is the DNF for it.

If you want an AI context package manager that is simple, flexible, and supports federated repositories for you or your enterprise to create curated, trusted catalogs of skills and context — Lola is built for that.

---

## Lola's Mission

### Federated Distribution

AI context should live in open, federated catalogs — not locked in a single vendor's marketplace. Lola works like APT, pip, npm, or vim-plug: any server hosting a catalog file becomes a registry you can register and install from. Teams can self-host private catalogs and combine them with public ones.

```bash
lola market add official https://...lola-market.../catalog.yml
lola market add myorg    https://internal.myorg.com/ai-skills/catalog.yml
lola install compliance-skills
```

---

### AI as Code

We envision a Lola module as a full-stack AI context package — carrying skills, MCP configurations, commands, scripts, and tools in a single distributable unit. Installed, updated, and managed like any other dependency. See [Install Hooks](../guides/install-hooks.md) for how lifecycle automation works in practice.

---

### One Module, Any Agent

A single module contains skills, slash commands, and subagent definitions. Lola translates each to the native format of every target — today's coding assistants, and tomorrow's autonomous agents.

---

### Supply Chain Security

As skills become a standard injection point for AI context, they also become a vector for prompt injection and supply chain attacks. Lola's [roadmap](roadmap.md) addresses supply chain security as a core pillar — skill scanning, signature verification, provenance, and trusted catalogs.

---

### Declarative, Version-Controlled

A `.lola-req` file declares which modules a project needs. Commit it. Run `lola sync`. Every team member, every environment, gets the same result. AI context treated exactly like any other project dependency.

---

### Beyond Coding Assistants

Lola started with Claude Code, Cursor, Gemini CLI, and OpenCode. The vision extends to any AI agent — LangChain, CrewAI, AutoGen, and custom autonomous systems. The same module format, the same distribution mechanism, any runtime.

---

## The Landscape

There are many great tools in this space, each solving a real problem. This table focuses on the technical dimensions where tools differ — not as a competition, but to help you understand what Lola brings:

| Feature | Lola | APM | Vercel Skills | OpenPackage |
|---------|------|-----|---------------|-------------|
| **Federated / multi-registry** | ✅ Core feature | ✅ Via `apm-policy.yml` | ❌ Centralized only | ⚠️ Local only |
| **Private self-hosted registry** | ✅ | ✅ Any git host | ❌ | ⚠️ Path-based |
| **Package-level install hooks** | ✅ Pre/post with env context | ⚠️ Experimental workflows | ❌ | ❌ |
| **Supply chain security** | 🔮 On the roadmap | ✅ `apm audit`, SHA pinning | ⚠️ Optional audit | ❌ |
| **Declarative manifest** | ✅ `.lola-req` | ✅ `apm.yml` + lockfile | ❌ Auto-generated | ⚠️ No lockfile |
| **Skills** | ✅ | ✅ | ✅ | ✅ |
| **Slash commands** | ✅ | ❌ | ❌ | ✅ |
| **Subagents** | ✅ | ✅ | ❌ | ✅ |
| **MCP servers** | ✅ | ✅ | ❌ | ✅ |
| **Module dependencies** | 🔮 On the roadmap ([#28](https://github.com/lobstertrap/lola/issues/28), [#64](https://github.com/lobstertrap/lola/issues/64)) | ✅ Full transitive | ❌ | ❌ |
| **Autonomous agent roadmap** | ✅ LangChain, CrewAI, AutoGen | ❌ | ❌ | ❌ |
| **Ecosystem language** | Python | Python | Node.js | Node.js |

### Vendor Plugin Ecosystems

Every major AI assistant is building its own plugin format. These solve the same core problem as Lola modules — reusable, shareable context — but scoped to a single vendor:

| Feature | Cursor Plugins | Claude Code Plugins | Lola Modules |
|---------|---------------|---------------------|--------------|
| **Content types** | Skills, Agents, MCP, Hooks, Rules | Skills, Agents, MCP, Hooks, LSP | Skills, Commands, Agents, MCP |
| **Multi-agent** | ❌ Cursor only | ❌ Claude Code only | ✅ Any agent |
| **Distribution** | cursor.com/marketplace | claude.com/plugins | Federated Git-based |
| **Self-hosted registry** | ✅ Team marketplaces | ✅ Custom marketplaces | ✅ Any git repo |
| **Version control native** | ❌ | ❌ | ✅ |
| **Vendor lock-in** | Yes | Yes | ❌ Open standard |

The vendor plugin movement is validating the idea that reusable context packages are the right abstraction. Lola's approach: open, federated, and Git-native — so your AI context is yours, not tied to any platform.

### Broader Ecosystem

| Tool | Package Types | Multi-Registry | Hooks | Security | Marketplace |
|------|--------------|----------------|-------|----------|-------------|
| **APM** (Microsoft) | Skills, Instructions, Agents, Prompts, Hooks | ✅ Any git host | ⚠️ Exp. | `apm audit`, SHA pinning | Multiple curated repos |
| **Vercel Skills** | Skills only | ❌ | ❌ | Optional audit | skills.sh |
| **OpenPackage** | Skills, Commands, Agents, Rules, MCP, LSP | ⚠️ Local | ❌ | ❌ | ❌ |
| **Smithery** | MCP + Skills | ❌ | ❌ | OAuth | smithery.ai (100K+) |
| **mpak** | MCP + Skills | ⚠️ | ❌ | L1-L4 trust scoring | Public registry |
| **Tessl** | Skills, Docs, Rules, Context | — | — | Task evaluation | 10K+ packages |
| **Skilz** | Skills only | ❌ | ❌ | ❌ | skillzwave.ai |
| **Paks** | Skills only | ❌ | ❌ | ❌ | ❌ |
| **skillpm** | Skills only | ❌ | ❌ | ❌ | ❌ |

---

[Join the conversation on GitHub →](https://github.com/lobstertrap/lola)
