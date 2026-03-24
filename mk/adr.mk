# ADR (Architecture Decision Records) Management
# Uses adr-tools: https://github.com/npryce/adr-tools

ADR_DIR := docs/adr

.PHONY: adr-new adr-list adr-help

adr-new: ## - Create new ADR: make adr-new TOPIC-NAME
	@command -v adr >/dev/null 2>&1 || { \
		echo "adr-tools not found. Install via:"; \
		echo "  asdf plugin add adr-tools && asdf install adr-tools latest"; \
		echo "  Or: https://github.com/npryce/adr-tools"; \
		exit 1; \
	}
	@if [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		echo "Usage: make adr-new TOPIC-NAME"; \
		echo "Example: make adr-new use-mkdocs-for-documentation"; \
		exit 1; \
	fi
	@mkdir -p $(ADR_DIR)
	@cd $(ADR_DIR) && adr new $(filter-out $@,$(MAKECMDGOALS))

adr-list: ## - List all ADRs
	@cd $(ADR_DIR) 2>/dev/null && ls -1 *.md | grep -E '^[0-9]' | sort || \
		echo "No ADRs found. Create one with: make adr-new TOPIC-NAME"

adr-help: ## - Show ADR usage and examples
	@echo "Lola ADR (Architecture Decision Records) Management"
	@echo "Powered by adr-tools: https://github.com/npryce/adr-tools"
	@echo ""
	@echo "Commands:"
	@echo "  make adr-new TOPIC-NAME  - Create new ADR"
	@echo "  make adr-list            - List all ADRs"
	@echo "  make adr-help            - Show this help"
	@echo ""
	@echo "Examples:"
	@echo "  make adr-new use-mkdocs-for-documentation"
	@echo ""
	@echo "For advanced operations (supersede, link, generate),"
	@echo "use adr-tools directly in $(ADR_DIR)/:"
	@echo "  cd $(ADR_DIR) && adr new -s 3 \"Use X instead of Y\""
	@echo "  cd $(ADR_DIR) && adr link 5 Amends 3 \"Amended by\""
	@echo ""
	@echo "Full reference: https://github.com/npryce/adr-tools"

# Prevent make from treating arguments as targets
%:
	@:
