# Installation

## Prerequisites

- Python 3.13 or later

## Install

=== "uv (recommended)"

    ```bash
    uv tool install lola-ai
    ```

    Don't have uv? [Install it here](https://docs.astral.sh/uv/getting-started/installation/).

=== "pip"

    ```bash
    pip install lola-ai
    ```

=== "Latest from Git"

    ```bash
    uv tool install git+https://github.com/RedHatProductSecurity/lola
    ```

=== "From source"

    ```bash
    git clone https://github.com/RedHatProductSecurity/lola
    cd lola
    uv tool install .
    ```

## Verify

```bash
lola --help
```

## Shell Completion

Enable tab completion for module names, marketplace names, and command arguments:

=== "Bash"

    ```bash
    lola completions bash > ~/.local/share/bash-completion/completions/lola
    source ~/.local/share/bash-completion/completions/lola
    ```

=== "Zsh"

    ```bash
    lola completions zsh > ~/.local/share/zsh/site-functions/_lola
    ```

=== "Fish"

    ```bash
    lola completions fish > ~/.config/fish/completions/lola.fish
    ```
