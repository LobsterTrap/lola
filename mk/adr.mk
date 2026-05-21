# ADR (Architecture Decision Records) Management

ADR_DIR := docs/adr
ADR_TEMPLATE := $(ADR_DIR)/template.md

.PHONY: adr-new adr-list adr-help

adr-new: ## - Create new ADR: make adr-new topic-name
	@if [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		echo "Usage: make adr-new topic-name"; \
		echo "Example: make adr-new go-migration"; \
		exit 1; \
	fi
	@NAME=$(filter-out $@,$(MAKECMDGOALS)); \
	DEST=$(ADR_DIR)/$$NAME.md; \
	if [ -f "$$DEST" ]; then \
		echo "Error: $$DEST already exists"; \
		exit 1; \
	fi; \
	cp $(ADR_TEMPLATE) $$DEST && echo "Created $$DEST"

adr-list: ## - List all ADRs
	@cd $(ADR_DIR) 2>/dev/null && ls -1 *.md | grep -v template | grep -v README | sort || \
		echo "No ADRs found. Create one with: make adr-new topic-name"

adr-help: ## - Show ADR usage and examples
	@echo "Lola ADR (Architecture Decision Records) Management"
	@echo ""
	@echo "Commands:"
	@echo "  make adr-new topic-name  - Create new ADR from template"
	@echo "  make adr-list            - List all ADRs"
	@echo "  make adr-help            - Show this help"
	@echo ""
	@echo "Examples:"
	@echo "  make adr-new go-migration"
	@echo "  make adr-new use-postgresql"
	@echo ""
	@echo "ADRs live in $(ADR_DIR)/ as <topic-name>.md"

# Prevent make from treating arguments as targets
%:
	@:
