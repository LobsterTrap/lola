# Lola - AI Context Package Manager

**Write Agent Skills and Contexts once, use everywhere.**

Lola is a universal AI Package Manager. If an agent's skills were an RPM, Lola is the DNF for it. Write your [skills and context modules](https://redhatproductsecurity.github.io/lola/concepts/skills-and-modules/) once as portable packages, then install them to any AI assistant or agent with a single command.

[![asciicast](https://asciinema.org/a/UsbI8adasbdAhAFQuiXj70eVp.svg)](https://asciinema.org/a/UsbI8adasbdAhAFQuiXj70eVp)

## Supported AI Assistants

| Assistant   | Skills | Commands | Agents |
| ----------- | ------ | -------- | ------ |
| Claude Code | Yes    | Yes      | Yes    |
| Cursor      | Yes    | Yes      | Yes    |
| Gemini CLI  | Yes    | Yes      | N/A    |
| OpenCode    | Yes    | Yes      | Yes    |

## Installation

```bash
uv tool install git+https://github.com/RedHatProductSecurity/lola
```

## Quick Start

```bash
# Set up the official marketplace
lola market add general https://raw.githubusercontent.com/RedHatProductSecurity/lola-market/main/general-market.yml

# Add a module
lola mod add https://github.com/user/my-skills.git

# Install to all detected assistants
lola install my-skills

# Or install to a specific assistant
lola install my-skills -a claude-code
```

## Declarative Installation

Create a `.lola-req` in your project:

```
python-tools>=1.0.0
git-workflow>>claude-code
https://github.com/user/module.git@main
```

```bash
lola sync
```

## Documentation

Full documentation is available at **[redhatproductsecurity.github.io/lola](https://redhatproductsecurity.github.io/lola/)**.

- [Installation](https://redhatproductsecurity.github.io/lola/getting-started/installation/) - Prerequisites and setup
- [Quick Start](https://redhatproductsecurity.github.io/lola/getting-started/quick-start/) - Get up and running
- [User Guide](https://redhatproductsecurity.github.io/lola/user-guide/modules/) - Modules, marketplace, and more
- [CLI Reference](https://redhatproductsecurity.github.io/lola/cli-reference/) - Complete command reference
- [Skills and Modules](https://redhatproductsecurity.github.io/lola/concepts/skills-and-modules/) - Understanding Agent Skills vs AI Context Modules
- [Roadmap](https://redhatproductsecurity.github.io/lola/concepts/roadmap/) - Vision and where Lola is heading

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[GPL-2.0-or-later](https://spdx.org/licenses/GPL-2.0-or-later.html)

## Authors

- Igor Brandao
- Katie Mulliken
