# Install Hooks

Execute custom scripts before or after module installation for setup, validation, or cleanup tasks.

## Hook Types

- **Pre-install**: Runs before installation (validate prerequisites, download resources)
- **Post-install**: Runs after installation (run verification, display instructions)

## Configuration

**Module metadata** (`lola.yaml` or `module/lola.yaml`):

```yaml
hooks:
  pre-install: scripts/check-deps.sh
  post-install: scripts/verify.sh
```

**CLI flags** (override module metadata):

```bash
lola install my-module --pre-install scripts/setup.sh --post-install scripts/verify.sh
```

**Marketplace definition:**

```yaml
modules:
  - name: data-tools
    hooks:
      pre-install: scripts/check-python.sh
      post-install: scripts/install-deps.sh
```

## Hook Environment

Scripts receive these environment variables:

| Variable | Description |
|----------|-------------|
| `LOLA_MODULE_NAME` | Module being installed |
| `LOLA_MODULE_PATH` | Path to local module copy |
| `LOLA_PROJECT_PATH` | Project installation directory |
| `LOLA_ASSISTANT` | Target assistant (claude-code, cursor, etc.) |
| `LOLA_SCOPE` | Installation scope (project) |
| `LOLA_HOOK` | Hook type (pre-install or post-install) |

## Example Hook Script

```bash
#!/bin/bash
# scripts/check-deps.sh - Pre-install hook

echo "Checking dependencies for ${LOLA_MODULE_NAME}..."
echo "Installing to: ${LOLA_PROJECT_PATH}"
echo "Target assistant: ${LOLA_ASSISTANT}"

# Check for required tools
if ! command -v sed &> /dev/null; then
    echo "Error: sed is required but not installed"
    exit 1
fi

# Validate Python version
if ! python3 --version | grep -q "3\.[0-9]"; then
    echo "Error: Python 3.x is required"
    exit 1
fi

echo "All dependencies met for ${LOLA_MODULE_NAME}"
exit 0
```

## Precedence

1. **CLI flags** - highest priority
2. **Module metadata** (`lola.yaml`)
3. **Marketplace definition** - lowest priority

## Error Handling

- **Pre-install failure**: Aborts installation and cleans up
- **Post-install failure**: Shows warning but keeps installation

!!! warning
    Hooks execute with your user permissions. Only use hooks from trusted modules and review scripts before running.
