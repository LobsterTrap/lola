# Installation

## Prerequisites

- Python 3.13 or later
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Install from PyPI (recommended)

```bash
uv tool install lola-ai
```

Or with pip:

```bash
pip install lola-ai
```

## Install latest dev version from Git

```bash
uv tool install git+https://github.com/RedHatProductSecurity/lola
```

## Install from source

```bash
git clone https://github.com/RedHatProductSecurity/lola
cd lola
uv tool install .
```

## Verify installation

```bash
lola --help
```

## Shell Completion

Enable tab completion for module names, marketplace names, and command arguments:

```bash
# Bash
lola completions bash > ~/.local/share/bash-completion/completions/lola
source ~/.local/share/bash-completion/completions/lola

# Zsh
lola completions zsh > ~/.local/share/zsh/site-functions/_lola

# Fish
lola completions fish > ~/.config/fish/completions/lola.fish
```
