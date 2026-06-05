# Design: E2E BDD Testing for Lola CLI

**Created**: 2026-06-05
**Status**: Draft

## Goal

Structure E2E tests using BDD (Behavior-Driven Development) for the Lola Python CLI. The Gherkin feature files must be reusable when the project is rewritten in Go.

## Framework Choice

| Language | Framework  | Rationale |
|----------|------------|-----------|
| Python   | **behave** | Closest structural analog to godog — `features/`, `steps/`, `environment.py` map 1:1 to godog's layout. |
| Go       | **godog**  | Standard Go BDD framework, consumes the same `.feature` files unchanged. |

Both use Gherkin feature files as the single source of truth. Feature files are 100% portable; only step definitions and helpers get rewritten.

## Directory Layout

```
e2e/
├── features/                      # Gherkin files, Python steps, and support
│   ├── behave.ini                 # behave configuration
│   ├── environment.py             # behave hooks (before_scenario, after_scenario)
│   ├── steps/                     # Step definitions (behave discovers these)
│   │   ├── cli_steps.py           # Given/When/Then for CLI invocations
│   │   ├── filesystem_steps.py    # Given/Then for files and directories
│   │   └── marketplace_steps.py   # Given for HTTP-served marketplaces
│   ├── support/                   # Shared helpers
│   │   ├── cli.py                 # subprocess wrapper for `lola`
│   │   ├── fixtures.py            # Module/marketplace builders
│   │   └── http_server.py         # Local HTTP server for marketplace URLs
│   ├── mod/
│   │   ├── add.feature
│   │   ├── rm.feature
│   │   ├── ls.feature
│   │   ├── info.feature
│   │   ├── init.feature
│   │   ├── update.feature
│   │   └── search.feature
│   ├── install/
│   │   ├── install.feature
│   │   ├── uninstall.feature
│   │   ├── update.feature
│   │   ├── list.feature
│   │   └── scope.feature
│   ├── market/
│   │   ├── add.feature
│   │   ├── ls.feature
│   │   ├── rm.feature
│   │   ├── update.feature
│   │   └── set.feature
│   ├── sync.feature
│   ├── completions.feature
│   └── cli.feature
│
└── go/                            # Go step definitions (godog) — future
    ├── e2e_test.go                # godog test runner + hooks
    ├── cli_steps.go
    ├── filesystem_steps.go
    ├── marketplace_steps.go
    └── support/
        ├── cli.go
        ├── fixtures.go
        └── http_server.go
```

Steps, support modules, and `environment.py` live alongside the feature files under `e2e/features/`. Behave natively adds this directory to `sys.path`, so `from support.cli import ...` works without path manipulation. When Go is added, `e2e/go/` has its own step definitions and `godog.Options{Paths: []string{"../features"}}` points at the same `.feature` files.

```ini
# e2e/features/behave.ini
[behave]
paths = .
```

```go
// go/e2e_test.go
opts := godog.Options{Paths: []string{"../features"}}
```

## Core Design Principles

### 1. Black-box CLI testing via subprocess

Never import `lola` internals. Invoke the `lola` binary the way a user would. This makes tests valid regardless of implementation language.

```python
# python/support/cli.py
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

@dataclass
class LolaResult:
    exit_code: int
    stdout: str
    stderr: str

class LolaCLI:
    def __init__(self, lola_home: Path, work_dir: Path):
        self.env = {**os.environ, "LOLA_HOME": str(lola_home)}
        self.work_dir = work_dir

    def run(self, *args: str) -> LolaResult:
        result = subprocess.run(
            ["lola", *args],
            capture_output=True, text=True,
            cwd=self.work_dir, env=self.env,
        )
        return LolaResult(result.returncode, result.stdout, result.stderr)
```

```go
// go/support/cli.go
type LolaResult struct {
    ExitCode int
    Stdout   string
    Stderr   string
}

type LolaCLI struct {
    LolaHome string
    WorkDir  string
}

func (c *LolaCLI) Run(args ...string) LolaResult {
    cmd := exec.Command("lola", args...)
    cmd.Dir = c.WorkDir
    cmd.Env = append(os.Environ(), "LOLA_HOME="+c.LolaHome)
    var stdout, stderr bytes.Buffer
    cmd.Stdout = &stdout
    cmd.Stderr = &stderr
    err := cmd.Run()
    exitCode := 0
    if err != nil {
        var exitErr *exec.ExitError
        if errors.As(err, &exitErr) {
            exitCode = exitErr.ExitCode()
        }
    }
    return LolaResult{exitCode, stdout.String(), stderr.String()}
}
```

### 2. Scenario isolation

Every scenario gets a fresh temp directory with its own `LOLA_HOME` and project directory. No scenario can leak state to another.

```python
# python/environment.py
import shutil
import tempfile
from pathlib import Path
from support.cli import LolaCLI

def before_scenario(context, scenario):
    context.tmp_dir = Path(tempfile.mkdtemp(prefix="lola-e2e-"))
    context.lola_home = context.tmp_dir / ".lola"
    context.project_dir = context.tmp_dir / "project"
    context.project_dir.mkdir(parents=True)
    context.cli = LolaCLI(context.lola_home, context.project_dir)
    context.modules = {}
    context.http_servers = []
    context.last_result = None

def after_scenario(context, scenario):
    for server in getattr(context, "http_servers", []):
        server.stop()
    shutil.rmtree(context.tmp_dir, ignore_errors=True)
```

### 3. Thin step definitions, fat helpers

Steps delegate to helper functions immediately. This keeps steps readable and helpers testable/reusable. Steps should never contain more than 3-4 lines of glue logic.

### 4. Consistent step vocabulary

A small, reusable set of step patterns covers most scenarios. New features should compose from these before inventing new steps.

## Step Pattern Catalog

These patterns form the shared vocabulary across all features.

### CLI Execution

```gherkin
When I run lola "{command}"
When I run lola "{command}" in "{directory}"
```

### Exit Code & Output Assertions

```gherkin
Then the exit code should be {code:d}
Then the output should contain "{text}"
Then the output should not contain "{text}"
Then the output should match /{pattern}/
Then the error output should contain "{text}"
```

### Filesystem Preconditions (Given)

```gherkin
Given a module "{name}" with a skill "{skill_name}"
Given a module "{name}" with skills, commands, and agents
Given a module "{name}" at "{path}"
Given assistant directories for "{assistant}"
Given a project directory
Given the module "{name}" is registered
Given the module "{name}" is installed to "{assistant}"
Given the module "{name}" is installed to "{assistant}" with scope "{scope}"
```

### Filesystem Assertions (Then)

```gherkin
Then the file "{path}" should exist
Then the file "{path}" should not exist
Then the directory "{path}" should exist
Then the directory "{path}" should not exist
Then the file "{path}" should contain "{text}"
Then the file "{path}" should have frontmatter key "{key}" with value "{value}"
```

### Marketplace Preconditions

```gherkin
Given a marketplace "{name}" serving modules:
  | module     | version | repository                       |
  | git-module | 1.0.0   | https://github.com/user/repo.git |
Given the marketplace "{name}" is disabled
Given a local HTTP server serving "{file}" at "{url_path}"
```

### Path Interpolation

Feature files use placeholders like `{lola_home}`, `{project}`, `{module_path}`. Step definitions resolve these from the scenario context:

```python
def resolve_path(context, text):
    replacements = {
        "{lola_home}": str(context.lola_home),
        "{project}": str(context.project_dir),
        "{home}": str(Path.home()),
        "{tmp}": str(context.tmp_dir),
    }
    for name, path in context.modules.items():
        replacements[f"{{{name}_path}}"] = str(path)
        replacements["{module_path}"] = str(path)
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text
```

## Example Feature Files

### `features/mod/add.feature`

```gherkin
Feature: Module registration
  As a user, I want to register modules from various sources
  so that I can install them to my AI assistants.

  Background:
    Given a project directory

  Scenario: Add a module from a local folder
    Given a module "my-module" with skills, commands, and agents
    When I run lola "mod add {module_path}"
    Then the exit code should be 0
    And the output should contain "my-module"
    And the directory "{lola_home}/modules/my-module" should exist

  Scenario: Add a module that already exists
    Given a module "my-module" with a skill "example"
    And the module "my-module" is registered
    When I run lola "mod add {module_path}"
    Then the exit code should be 1
    And the output should contain "already"

  Scenario: Remove a registered module
    Given the module "my-module" is registered
    When I run lola "mod rm my-module"
    Then the exit code should be 0
    And the directory "{lola_home}/modules/my-module" should not exist

  Scenario: List registered modules
    Given the module "my-module" is registered
    When I run lola "mod ls"
    Then the exit code should be 0
    And the output should contain "my-module"
```

### `features/install/install.feature`

```gherkin
Feature: Module installation
  As a user, I want to install modules to AI assistants
  so that skills, commands, and agents are available in my workflow.

  Background:
    Given a project directory
    And the module "git-module" is registered
    And assistant directories for "claude-code"

  Scenario: Install a module to Claude Code
    When I run lola "install git-module -a claude-code"
    Then the exit code should be 0
    And the directory "{project}/.claude/skills" should exist
    And the output should contain "Installed"

  Scenario: Install with user scope
    When I run lola "install git-module -a claude-code --scope user"
    Then the exit code should be 0
    And the directory "{home}/.claude/skills" should exist

  Scenario: Uninstall a previously installed module
    Given the module "git-module" is installed to "claude-code"
    When I run lola "uninstall git-module -a claude-code"
    Then the exit code should be 0
    And the directory "{project}/.claude/skills/git-cheatsheet" should not exist

  Scenario: Install a module not in registry but available in marketplace
    Given a marketplace "community" serving modules:
      | module     | version | repository                       |
      | new-module | 1.0.0   | https://github.com/user/repo.git |
    When I run lola "install new-module -a claude-code"
    Then the exit code should be 0
    And the output should contain "new-module"
```

### `features/market/add.feature`

```gherkin
Feature: Marketplace management
  As a user, I want to register marketplaces
  so I can discover and install modules from curated catalogs.

  Scenario: Add a marketplace
    Given a local HTTP server serving a marketplace catalog at "/catalog.yml"
    When I run lola "market add community {server_url}/catalog.yml"
    Then the exit code should be 0
    And the file "{lola_home}/market/community.yml" should exist
    And the file "{lola_home}/market/cache/community.yml" should exist

  Scenario: List marketplaces
    Given a marketplace "community" serving modules:
      | module    | version |
      | my-module | 1.0.0   |
    When I run lola "market ls"
    Then the exit code should be 0
    And the output should contain "community"

  Scenario: Disable a marketplace excludes it from search
    Given a marketplace "community" serving modules:
      | module    | version |
      | my-module | 1.0.0   |
    When I run lola "market set community --disable"
    Then the exit code should be 0
    When I run lola "mod search my-module"
    Then the output should not contain "my-module"
```

## Marketplace HTTP Testing

For features that need to download marketplace catalogs, use a local HTTP server:

```python
# python/support/http_server.py
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

class LocalHTTPServer:
    def __init__(self, directory: Path):
        self.directory = directory
        handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
        self.server = HTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()
```

```go
// go equivalent uses net/http/httptest
server := httptest.NewServer(http.FileServer(http.Dir(directory)))
defer server.Close()
```

## Tagging Strategy

```gherkin
@slow              # Tests that take >5s (HTTP, git clone)
@marketplace       # Needs HTTP server
@wip               # Work in progress — excluded from CI
@smoke             # Fast subset for pre-commit
@claude-code       # Assistant-specific scenarios
@cursor
@gemini
@opencode
```

Run subsets:

```bash
behave --tags="@smoke"              # Pre-commit fast check
behave --tags="~@slow"              # Skip slow tests
behave --tags="@marketplace"        # Only marketplace tests
behave --tags="~@wip"               # CI default
```

## Portability Matrix

| Artifact | Portable? | Go Migration |
|----------|-----------|--------------|
| `features/**/*.feature` | **Yes** | Move unchanged |
| Step patterns (cucumber expressions) | **Yes** | Same expressions in godog |
| Step definition bodies | No | Rewrite in Go, same logic |
| `LolaCLI` helper | No | Rewrite using `os/exec`, same interface |
| Filesystem helpers | No | Rewrite using `os`/`filepath`, same interface |
| `environment.py` hooks | No | Map to `ScenarioContext.Before`/`After` |
| `LocalHTTPServer` | No | Replace with `net/http/httptest` |
| `behave.ini` | No | Replace with `godog.Options{}` |

The Go rewrite touches only step definitions and support code. Feature files and step patterns carry over unchanged.

## Relationship to Existing Tests

The existing pytest unit tests in `tests/` remain as-is. They test internal functions, data models, parsers, and target generators at the code level. The BDD E2E tests complement them by testing the CLI from the outside:

| Concern | pytest (unit/integration) | BDD E2E |
|---------|--------------------------|---------|
| Scope | Internal functions, classes | CLI binary as subprocess |
| Isolation | Mocked paths, patched imports | Real filesystem, env vars |
| Speed | Fast (no subprocess overhead) | Slower (process spawn per step) |
| Portability | Python-only | Feature files portable to Go |
| Purpose | Correctness of internals | User-visible behavior |

There is intentional overlap at the integration boundary — both test `lola install`, for example — but from different angles. The BDD tests are the ones that survive the Go rewrite.

## Makefile Integration

```makefile
# mk/dev.mk additions
e2e:  ## Run E2E BDD tests
	cd e2e/python && behave --format progress --no-capture ../features

e2e-wip:  ## Run only @wip tagged E2E scenarios
	cd e2e/python && behave --tags="@wip" --format progress ../features

e2e-smoke:  ## Run smoke E2E tests (pre-commit)
	cd e2e/python && behave --tags="@smoke" --format progress ../features
```

## Cross-OS Containerized Execution

### Problem

Lola must work on Linux, macOS, and Windows. E2E tests should verify behavior on all three operating systems, run without root privileges, and use the same feature files and step definitions regardless of the host or implementation language (Python or Go).

### Container Runtime: Podman (Rootless)

Podman runs rootless by default — no daemon, no root, no `sudo`. It is the primary runtime for containerized E2E execution. Docker-compatible Containerfiles work unchanged.

```bash
podman build -t lola-e2e-python -f e2e/containers/python.Containerfile .
podman run --rm lola-e2e-python
```

### Multi-OS Strategy

OCI containers are Linux-only. True macOS and Windows testing requires native execution on those platforms. The strategy splits into two layers:

| Layer | Linux | macOS | Windows |
|-------|-------|-------|---------|
| **Container** | Rootless Podman — primary path | Podman Machine (Linux VM) — validates container workflow | WSL2 + Podman — validates container workflow |
| **Native** | CI runner (also covered by container) | CI runner (macOS host) | CI runner (Windows host) |

- **Linux variants** (Fedora, Debian, Alpine): fully covered by containers with different base images.
- **macOS/Windows native behavior** (path separators, case sensitivity, home directory layout): covered by CI runners on real hosts.
- **Container workflow validation on macOS/Windows**: developers on those platforms use Podman Machine / WSL2 to run the Linux container tests locally.

### Directory Layout (Additions)

```
e2e/
├── features/                          # (unchanged — shared Gherkin files)
├── python/                            # (unchanged — behave steps)
├── go/                                # (unchanged — godog steps, future)
│
└── containers/
    ├── python.Containerfile           # Python + behave image
    ├── go.Containerfile               # Go + godog image (future)
    ├── base/
    │   ├── fedora.Containerfile       # Fedora base (default)
    │   ├── debian.Containerfile       # Debian base
    │   └── alpine.Containerfile       # Alpine base
    └── scripts/
        ├── run-tests.sh               # Entrypoint: run behave or godog
        └── install-lola.sh            # Build & install lola from source

.github/
└── workflows/
    └── e2e.yml                        # GitHub Actions CI matrix
```

### Containerfiles

#### Base Image (Fedora)

```dockerfile
# e2e/containers/base/fedora.Containerfile
FROM registry.fedoraproject.org/fedora:42

RUN dnf install -y --setopt=install_weak_deps=False \
    git curl ca-certificates \
    && dnf clean all

RUN useradd --create-home --shell /bin/bash tester
USER tester
WORKDIR /home/tester
```

#### Python Test Image

```dockerfile
# e2e/containers/python.Containerfile
ARG BASE=fedora
FROM localhost/lola-e2e-base-${BASE}:latest AS base

USER root
RUN dnf install -y --setopt=install_weak_deps=False \
    python3 python3-pip python3-devel \
    && dnf clean all
USER tester

COPY --chown=tester:tester . /home/tester/lola
WORKDIR /home/tester/lola

RUN python3 -m venv .venv \
    && .venv/bin/pip install --no-cache-dir . \
    && .venv/bin/pip install --no-cache-dir behave pyyaml

ENV PATH="/home/tester/lola/.venv/bin:${PATH}"

ENTRYPOINT ["e2e/containers/scripts/run-tests.sh"]
CMD ["python"]
```

Note: The `RUN` package-install commands are Fedora-specific. The Debian and Alpine Containerfiles use `apt-get` and `apk` respectively but produce the same final environment. The `BASE` build arg selects which base image to layer on.

#### Go Test Image (Future)

```dockerfile
# e2e/containers/go.Containerfile
ARG BASE=fedora
FROM localhost/lola-e2e-base-${BASE}:latest AS base

USER root
RUN dnf install -y --setopt=install_weak_deps=False golang \
    && dnf clean all
USER tester

ENV PATH="/home/tester/go/bin:${PATH}"

COPY --chown=tester:tester . /home/tester/lola
WORKDIR /home/tester/lola

RUN cd e2e/go && go mod download

ENTRYPOINT ["e2e/containers/scripts/run-tests.sh"]
CMD ["go"]
```

#### Test Entrypoint

```bash
#!/usr/bin/env bash
# e2e/containers/scripts/run-tests.sh
set -euo pipefail

LANG="${1:-python}"
TAGS="${E2E_TAGS:-~@wip}"

case "$LANG" in
    python)
        cd e2e
        exec behave --tags="$TAGS" --no-capture --format progress
        ;;
    go)
        cd e2e/go
        exec go test -v -run TestFeatures -tags="$TAGS" ./...
        ;;
    *)
        echo "Unknown language: $LANG" >&2
        exit 1
        ;;
esac
```

### Build & Run Commands

```bash
# Build base image (once)
podman build -t lola-e2e-base-fedora -f e2e/containers/base/fedora.Containerfile .

# Build and run Python E2E tests
podman build -t lola-e2e-python \
    --build-arg BASE=fedora \
    -f e2e/containers/python.Containerfile .
podman run --rm lola-e2e-python

# Run with tag filter
podman run --rm -e E2E_TAGS="@smoke" lola-e2e-python

# Run on Debian base
podman build -t lola-e2e-base-debian -f e2e/containers/base/debian.Containerfile .
podman build -t lola-e2e-python-debian \
    --build-arg BASE=debian \
    -f e2e/containers/python.Containerfile .
podman run --rm lola-e2e-python-debian
```

### Cross-OS Considerations in Feature Files

Feature files must remain OS-agnostic. Step definitions handle platform differences internally.

#### Path Separators

Feature files always use forward slashes. Step definitions normalize to the host OS:

```python
# python/support/cli.py
def resolve_path(context, text):
    resolved = _interpolate_placeholders(context, text)
    return str(Path(resolved))  # normalizes separators per OS
```

```go
// go/support/cli.go
func resolvePath(ctx *scenarioContext, text string) string {
    resolved := interpolatePlaceholders(ctx, text)
    return filepath.FromSlash(resolved)
}
```

#### Home Directory

`{home}` resolves differently per OS (`/home/tester` in containers, `/Users/x` on macOS, `C:\Users\x` on Windows). Step definitions handle this via the environment:

```python
def home_dir():
    return Path.home()
```

```go
func homeDir() string {
    home, _ := os.UserHomeDir()
    return home
}
```

#### Filesystem Case Sensitivity

macOS (HFS+/APFS default) and Windows (NTFS) are case-insensitive. Linux (ext4) is case-sensitive. Feature files should use consistent casing and avoid relying on case-insensitive lookups. Step assertions compare paths case-sensitively everywhere — if a test passes on Linux, it will pass on macOS/Windows. The reverse is what catches bugs.

#### Newlines

Lola writes text files. Step definitions that assert file content should normalize `\r\n` to `\n` before comparison so Windows output doesn't break assertions written for Unix:

```python
def read_normalized(path: Path) -> str:
    return path.read_text().replace("\r\n", "\n")
```

### CI Pipeline (GitHub Actions)

The CI matrix covers three dimensions: OS, implementation language, and Linux distribution (for containers).

```yaml
# .github/workflows/e2e.yml
name: E2E BDD Tests

on:
  pull_request:
  push:
    branches: [main]

jobs:
  e2e-container:
    name: "E2E / ${{ matrix.lang }} / ${{ matrix.distro }}"
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        lang: [python]          # add 'go' when ready
        distro: [fedora, debian, alpine]
    steps:
      - uses: actions/checkout@v4

      - name: Build base image
        run: |
          podman build -t lola-e2e-base-${{ matrix.distro }} \
            -f e2e/containers/base/${{ matrix.distro }}.Containerfile .

      - name: Build test image
        run: |
          podman build -t lola-e2e-${{ matrix.lang }}-${{ matrix.distro }} \
            --build-arg BASE=${{ matrix.distro }} \
            -f e2e/containers/${{ matrix.lang }}.Containerfile .

      - name: Run E2E tests
        run: |
          podman run --rm \
            lola-e2e-${{ matrix.lang }}-${{ matrix.distro }} \
            ${{ matrix.lang }}

  e2e-native:
    name: "E2E / ${{ matrix.lang }} / ${{ matrix.os }}"
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        lang: [python]          # add 'go' when ready
        os: [macos-latest, windows-latest]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        if: matrix.lang == 'python'
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install lola and test dependencies
        shell: bash
        run: |
          python -m venv .venv
          source .venv/bin/activate || . .venv/Scripts/activate
          pip install . behave pyyaml

      - name: Run E2E tests
        shell: bash
        run: |
          source .venv/bin/activate || . .venv/Scripts/activate
          cd e2e
          behave --tags="~@wip" --no-capture --format progress
```

### CI Matrix Summary

| Job | Runner | Method | What It Validates |
|-----|--------|--------|-------------------|
| `e2e-container` / fedora | `ubuntu-latest` | Rootless Podman | Fedora baseline (default) |
| `e2e-container` / debian | `ubuntu-latest` | Rootless Podman | Debian/dpkg-based compatibility |
| `e2e-container` / alpine | `ubuntu-latest` | Rootless Podman | Musl libc, minimal environment |
| `e2e-native` / macOS | `macos-latest` | Direct execution | Case-insensitive FS, macOS paths |
| `e2e-native` / Windows | `windows-latest` | Direct execution | NTFS, backslash paths, `%USERPROFILE%` |

When Go is added, each row doubles (`lang: [python, go]`), but the feature files stay identical — only the runner language changes.

### Local Developer Workflow

```bash
# Run locally without containers (fastest feedback loop)
cd e2e/python && behave ../features

# Run in a rootless container (reproduces CI)
make e2e-container

# Run on a specific distro
make e2e-container DISTRO=debian

# Run only smoke tests in container
make e2e-container E2E_TAGS=@smoke
```

### Makefile Integration (Updated)

```makefile
# mk/dev.mk additions
DISTRO ?= fedora
E2E_LANG ?= python
E2E_TAGS ?= ~@wip

e2e:  ## Run E2E BDD tests locally
	cd e2e/python && behave --tags="$(E2E_TAGS)" --format progress --no-capture ../features

e2e-wip:  ## Run only @wip tagged E2E scenarios
	cd e2e/python && behave --tags="@wip" --format progress ../features

e2e-smoke:  ## Run smoke E2E tests (pre-commit)
	cd e2e/python && behave --tags="@smoke" --format progress ../features

e2e-container-build:  ## Build E2E container images
	podman build -t lola-e2e-base-$(DISTRO) -f e2e/containers/base/$(DISTRO).Containerfile .
	podman build -t lola-e2e-$(E2E_LANG)-$(DISTRO) --build-arg BASE=$(DISTRO) \
		-f e2e/containers/$(E2E_LANG).Containerfile .

e2e-container: e2e-container-build  ## Run E2E tests in a rootless container
	podman run --rm -e E2E_TAGS="$(E2E_TAGS)" lola-e2e-$(E2E_LANG)-$(DISTRO) $(E2E_LANG)
```

## Dependencies

```
# e2e/python/requirements.txt (or managed via uv)
behave>=1.2.6
PyYAML>=6.0
```

No other dependencies — the E2E tests use only stdlib (`subprocess`, `tempfile`, `pathlib`, `http.server`, `threading`, `re`) plus behave and PyYAML for marketplace fixture building.
