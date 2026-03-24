# MkDocs targets for documentation management
# These targets handle the pyproject.toml interference issue

.PHONY: docs-serve docs-build docs-clean docs-check

docs-sync: ## - sync docs outside of mkdocs tree to inside docs_dir
	@echo "Syncing external docs"
	@cp -rpavf README.md docs/

docs-build: docs-sync ## - build static documentation site
	@echo "Building documentation site..."
	@uv sync --extra docs
	@uv run mkdocs build

docs-serve: docs-build ## - start MkDocs development server
	@echo "Starting MkDocs development server..."
	@uv sync --extra docs
	@uv run mkdocs serve

docs-clean: ## - clean built documentation files
	@echo "Cleaning documentation build files..."
	@rm -rf site/ docs/README.md
	@echo "Documentation build files cleaned."

docs-check: ## - check documentation for issues
	@echo "Checking documentation configuration..."
	@if [ ! -f "mkdocs.yml" ]; then \
		echo "Error: mkdocs.yml not found in current directory"; \
		exit 1; \
	fi
	@uv sync --extra docs
	@uv run mkdocs build --strict
