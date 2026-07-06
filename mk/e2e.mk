# E2E BDD test targets
# Run behavior tests via behave against the installed lola CLI.
# Default format, tags, and feature paths are set in e2e/features/behave.ini.

DISTRO ?= fedora
E2E_LANG ?= python
E2E_TAGS ?= ~@wip

.PHONY: e2e e2e-wip e2e-smoke _ensure-podman-machine e2e-container-build e2e-container

e2e: ## - run E2E BDD tests locally
	@echo "Running E2E BDD tests..."
	@cd e2e/features && uv run behave --no-capture

e2e-wip: ## - run only @wip tagged E2E scenarios
	@cd e2e/features && uv run behave --tags="@wip" --no-capture

e2e-smoke: ## - run smoke E2E tests
	@cd e2e/features && uv run behave --tags="@smoke" --no-capture

_ensure-podman-machine:
	@case "$$(uname -s)" in \
		Darwin|MINGW*|MSYS*|CYGWIN*) \
			state=$$(podman machine inspect --format '{{.State}}' 2>/dev/null) || true; \
			if [ "$$state" != "running" ]; then \
				echo "Starting podman machine..."; \
				podman machine init 2>/dev/null || true; \
				podman machine start; \
			fi ;; \
	esac

e2e-container-build: _ensure-podman-machine ## - build E2E container images
	podman build -t lola-e2e-base-$(DISTRO) -f e2e/containers/base/$(DISTRO).Containerfile .
	podman build -t lola-e2e-$(E2E_LANG)-$(DISTRO) --build-arg BASE=$(DISTRO) \
		-f e2e/containers/$(E2E_LANG).Containerfile .

e2e-container: e2e-container-build ## - run E2E tests in a rootless container
	podman run --rm -v "$(CURDIR):/home/tester/lola:Z" -e E2E_TAGS="$(E2E_TAGS)" lola-e2e-$(E2E_LANG)-$(DISTRO) $(E2E_LANG)
