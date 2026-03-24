SHELL := /bin/bash

.PHONY: help
help: ## - print the help and usage
	@printf "Project Usage:\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		sed 's/^[^:]*://' | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

include mk/mkdocs.mk
include mk/adr.mk
