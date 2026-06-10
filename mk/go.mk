# Go build targets
# VERSION is set only when HEAD is exactly on a tag; empty string otherwise,
# which causes resolveVersion to fall through to VCS stamping.
VERSION := $(shell git describe --tags --exact-match 2>/dev/null || echo "")
LDFLAGS := -X github.com/LobsterTrap/lola/cmd.version=$(VERSION)

.PHONY: go-build go-test go-vet

go-build: ## - build lola binary (version from tag if on one, else from VCS)
	go build -ldflags "$(LDFLAGS)" -o bin/lola .

go-test: ## - run Go test suite
	go test ./...

go-vet: ## - run go vet static analysis
	go vet ./...
