# Contributing

We welcome contributions to Lola! For the full contributing guide, see [CONTRIBUTING.md](https://github.com/RedHatProductSecurity/lola/blob/main/CONTRIBUTING.md).

## Quick Start

```bash
git clone https://github.com/RedHatProductSecurity/lola
cd lola
uv sync --group dev
source .venv/bin/activate
```

## Development Commands

```bash
# Run tests
pytest
pytest tests/test_cli_mod.py     # Single file
pytest -k test_add               # Pattern match
pytest --cov=src/lola            # With coverage

# Linting and type checking
ruff check src tests
ruff format --check src tests

# Run the CLI
lola --help
lola mod ls
```

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

## AI-Assisted Contributions

We encourage the use of AI tools for contributions. If AI was used, include an `AI Disclosure` section in your PR describing how it was used.
