# Development workflow targets
# install, uninstall, test, lint — all driven through uv against the local .venv.

# Pin uv to the project-local virtualenv. This overrides any global
# UV_PROJECT_ENVIRONMENT a developer may have set, guaranteeing every
# `uv sync` / `uv run` here targets ./.venv.
export UV_PROJECT_ENVIRONMENT := $(CURDIR)/.venv

# Necessary for operating systems with old pythons
export UV_MANAGED_PYTHON := 1

.PHONY: install uninstall test lint clean distclean run

install: ## - install project + dev dependencies into local .venv (creates/updates .venv as needed)
	@echo "Syncing dev environment into $(UV_PROJECT_ENVIRONMENT)..."
	@uv sync --group dev
	@uv tool install --force --editable .

uninstall: ## - remove the lola-ai package from the local .venv (dev deps remain)
	@echo "Uninstalling lola-ai from $(UV_PROJECT_ENVIRONMENT)...";
	@uv pip uninstall lola-ai || echo "Nothing to uninstall";

test: ## - run the pytest suite
	@echo "Running tests..."
	@uv run pytest

run: ## - run the installed lola CLI; pass args via ARGS="..." (e.g., make run ARGS="mod ls")
	@uv run lola $(ARGS)

lint: ## - run ruff (check + format check) and mypy on src
	@echo "Running ruff check..."
	@uv run ruff check src tests
	@echo "Running ruff format check..."
	@uv run ruff format --check src tests
	@echo "Running mypy..."
	@uv run mypy src

# Subtrees clean must never descend into: virtualenv, lola state, git internals.
# -prune (not -not -path) is required to skip the subtree entirely — otherwise
# find still descends and hits permission errors inside .lola/modules/.
CLEAN_PRUNE := \( -path './.venv' -o -path './.lola' -o -path './.git' \) -prune

clean: ## - remove build artifacts, caches, coverage, and Python bytecode (leaves .venv intact)
	@echo "Cleaning build artifacts..."
	@rm -rf build/ dist/
	@find . $(CLEAN_PRUNE) -o -type d -name '*.egg-info' -exec rm -rf {} +
	@echo "Cleaning lint, type-check, and test caches..."
	@rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/
	@echo "Cleaning coverage artifacts..."
	@rm -rf .coverage htmlcov/
	@echo "Cleaning test output..."
	@rm -rf .test-output/
	@echo "Cleaning Python bytecode..."
	@find . $(CLEAN_PRUNE) -o -type d -name __pycache__ -exec rm -rf {} +
	@find . $(CLEAN_PRUNE) -o -type f -name '*.pyc' -exec rm -f {} +
	@echo "Done."

distclean: clean docs-clean ## - deep clean: also removes .venv and generated _version.py (slow to rebuild)
	@echo "Removing virtual environment at $(UV_PROJECT_ENVIRONMENT)..."
	@rm -rf "$(UV_PROJECT_ENVIRONMENT)"
	@echo "Removing hatch-vcs generated _version.py..."
	@rm -f src/lola/_version.py
	@echo "Done. Run 'make install' to rebuild the environment."
