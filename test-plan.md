# Manual Test Plan: Interactive Prompts

*2026-03-04T15:57:25Z by Showboat 0.6.1*
<!-- showboat-id: ccd04435-d709-4112-a75b-fe6d8bee0aaa -->

This plan covers the three interactive prompt additions on the `001-interactive-prompts` branch:

1. `lola mod update` — new `--all` flag, non-interactive guard, three-option action menu
2. `lola market update` — non-interactive guard, three-option action menu
3. `lola market rm` — new `--force` flag, confirmation dialog before deletion

**Sections A–C** are automated (run by this document). **Section D** requires a real TTY and must be done manually.

## Setup

Create an isolated LOLA_HOME and register a test module so there is real data to act on.

```bash

set -e
export LOLA_HOME=/tmp/lola-test-home
rm -rf $LOLA_HOME

# Create a minimal module directory that lola mod add can register
mkdir -p /tmp/lola-test-module/skills/greet
cat > /tmp/lola-test-module/skills/greet/SKILL.md << 'EOF'
---
name: greet
description: Say hello
---
Say hello to the user.
EOF

echo 'Module directory created.'
ls /tmp/lola-test-module/skills/greet/

```

```output
Module directory created.
SKILL.md
```

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
export LOLA_HOME=/tmp/lola-test-home
lola mod add /tmp/lola-test-module

```

```output
Adding module from folder...

Added lola-test-module
  Path: /tmp/lola-test-home/modules/lola-test-module
  Skills: 1
  Commands: 0
  Agents: 0

Skills
  greet

Next steps:
  1. lola install lola-test-module -a <assistant> -s <scope>
```

Now add a test marketplace by creating the reference and cache YAML files directly (no network needed).

```bash

export LOLA_HOME=/tmp/lola-test-home
mkdir -p $LOLA_HOME/market/cache

cat > $LOLA_HOME/market/test-market.yml << 'EOF'
url: https://example.com/test-market.yml
enabled: true
EOF

cat > $LOLA_HOME/market/cache/test-market.yml << 'EOF'
name: Test Marketplace
description: A test catalog
version: 1.0.0
modules:
  - name: sample-mod
    description: A sample module
    version: 1.0.0
    repository: https://github.com/example/sample.git
EOF

echo 'Marketplace registered.'
ls $LOLA_HOME/market/

```

```output
Marketplace registered.
cache
test-market.yml
```

---

## A. `lola mod update` — new flags and non-interactive guard

### A1. `--help` shows the `--all` flag

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
lola mod update --help

```

```output
Usage: lola mod update [OPTIONS] [MODULE_NAME]

  Update module(s) from their original source.

  Re-fetches the module from the source it was added from (git repo, folder,
  zip, or tar file). After updating, run 'lola update' to regenerate assistant
  files.

  Examples:
      lola mod update                    # Interactive: choose modules or update all
      lola mod update --all              # Update all modules
      lola mod update my-module          # Update specific module

Options:
  --all   Update all registered modules
  --help  Show this message and exit.
```

✅ `--all` flag appears in help and examples reflect the new interactive behaviour.

### A2. Non-interactive mode with no argument → error (exit 1)

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
export LOLA_HOME=/tmp/lola-test-home
lola mod update < /dev/null
echo "Exit code: $?"

```

```output
module_name is required in non-interactive mode, or use --all
Exit code: 1
```

✅ Error message and exit code 1 as expected.

### A3. MODULE_NAME and `--all` together → conflict error (exit 1)

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
export LOLA_HOME=/tmp/lola-test-home
lola mod update lola-test-module --all
echo "Exit code: $?"

```

```output
Error: Cannot specify both MODULE_NAME and --all
Exit code: 1
```

✅ Conflict correctly rejected.

### A4. `--all` updates all registered modules

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
export LOLA_HOME=/tmp/lola-test-home
lola mod update --all
echo "Exit code: $?"

```

```output
Updating 1 module(s)...

  lola-test-module
    Updated from folder source

Updated 1 module

Run 'lola update' to regenerate assistant files
Exit code: 0
```

✅ All modules updated.

### A5. MODULE_NAME updates only that module

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
export LOLA_HOME=/tmp/lola-test-home
lola mod update lola-test-module
echo "Exit code: $?"

```

```output
Updating lola-test-module...
Updated from folder source
  Skills: 1

Run 'lola update' to regenerate assistant files
Exit code: 0
```

✅ Single module updated.

---

## B. `lola market update` — non-interactive guard and `--all` flag

### B1. `--help` documents the interactive behaviour

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
lola market update --help

```

```output
Usage: lola market update [OPTIONS] [NAME]

  Update marketplace cache.

  If NAME and --all are both omitted in an interactive terminal, an action
  menu is shown. In non-interactive mode one of them must be supplied.

  Examples:
      lola market update my-market   # Update specific marketplace
      lola market update --all       # Update all marketplaces
      lola market update             # Interactive: choose or update all

Options:
  --all   Update all marketplaces
  --help  Show this message and exit.
```

✅ Help shows interactive mode note and `--all` flag.

### B2. Non-interactive mode with no argument → error (exit 1)

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
export LOLA_HOME=/tmp/lola-test-home
lola market update < /dev/null
echo "Exit code: $?"

```

```output
name is required in non-interactive mode, or use --all
Exit code: 1
```

✅ Error message and exit 1 as expected.

### B3. NAME and `--all` together → conflict error

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
export LOLA_HOME=/tmp/lola-test-home
lola market update test-market --all
echo "Exit code: $?"

```

```output
Error: Cannot specify both NAME and --all
Exit code: 1
```

✅ Conflict correctly rejected.

### B4. NAME updates only that marketplace

> **Manual step:** In a real environment with a live marketplace URL, run:
> ```
> lola market update <your-marketplace-name>
> ```
> Expected: only that marketplace is refreshed. The automated test for `--all` is skipped here because the test marketplace URL is not live.

---

## C. `lola market rm` — `--force` flag and confirmation dialog

### C1. `--help` shows the `--force` flag

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
lola market rm --help

```

```output
Usage: lola market rm [OPTIONS] [NAME]

  Remove a marketplace.

  If NAME is omitted in an interactive terminal, a picker is shown.

  Examples:
      lola market rm my-market           # Remove specific marketplace
      lola market rm                     # Show interactive picker
      lola market rm my-market --force   # Skip confirmation

Options:
  -f, --force  Skip confirmation prompt
  --help       Show this message and exit.
```

✅ `-f/--force` flag is listed in help.

### C2. `--force` removes without prompting

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
export LOLA_HOME=/tmp/lola-test-home

echo 'Before:'
ls $LOLA_HOME/market/

lola market rm test-market --force
echo "Exit code: $?"

echo 'After:'
ls $LOLA_HOME/market/ 2>/dev/null || echo '(empty)'

```

```output
Before:
cache
test-market.yml
Removed marketplace 'test-market'
Exit code: 0
After:
cache
```

✅ Marketplace removed immediately with no prompt.

### C3. Without `--force`, confirmation is shown and 'n' cancels

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
export LOLA_HOME=/tmp/lola-test-home

# Re-create the marketplace files for this test
mkdir -p $LOLA_HOME/market/cache
echo 'url: https://example.com/test.yml' > $LOLA_HOME/market/test-market.yml
echo 'enabled: true' >> $LOLA_HOME/market/test-market.yml
echo 'name: Test\nversion: 1.0.0\nmodules: []' > $LOLA_HOME/market/cache/test-market.yml

# Pipe 'n' to decline the confirmation
echo 'n' | lola market rm test-market
echo "Exit code: $?"

echo 'Still exists:'
ls $LOLA_HOME/market/

```

```output
Remove marketplace 'test-market'?
  Reference: /tmp/lola-test-home/market/test-market.yml
  Cache:     /tmp/lola-test-home/market/cache/test-market.yml

Continue? [y/N]: Cancelled
Exit code: 0
Still exists:
cache
test-market.yml
```

✅ Shows reference and cache paths. Answering 'n' cancels without removing.

### C4. Answering 'y' confirms and removes

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
export LOLA_HOME=/tmp/lola-test-home

echo 'y' | lola market rm test-market
echo "Exit code: $?"
echo 'After:'
ls $LOLA_HOME/market/ 2>/dev/null || echo '(empty)'

```

```output
Remove marketplace 'test-market'?
  Reference: /tmp/lola-test-home/market/test-market.yml
  Cache:     /tmp/lola-test-home/market/cache/test-market.yml

Continue? [y/N]: Removed marketplace 'test-market'
Exit code: 0
After:
cache
```

✅ Answering 'y' removes the marketplace.

### C5. Non-interactive mode requires NAME

```bash

source /Users/jmullike/Projects/lola/.venv/bin/activate
export LOLA_HOME=/tmp/lola-test-home
lola market rm < /dev/null
echo "Exit code: $?"

```

```output
name is required in non-interactive mode
Exit code: 1
```

✅ Non-interactive mode rejects missing NAME.

---

## D. Interactive TTY Tests (manual — must be run in a real terminal)

These tests require a real TTY so the arrow-key picker renders correctly. Run each command in your terminal and follow the instructions.

### D1. `lola mod update` — three-option action menu

**Setup:** ensure at least one module is registered (`lola mod ls`).

**Run:**

```
lola mod update
```

**Expected UI:**

```
? Update modules:
  ❯ Update all
    Choose modules to update
    Cancel
```

**Scenarios to exercise:**

| Scenario | Action | Expected result |
|---|---|---|
| D1-a | Arrow ↓ to **Choose modules to update**, Enter | Multi-select module picker appears; Space toggles, Enter confirms; selected modules are updated |
| D1-b | Arrow ↓ to **Cancel**, Enter | Prints "Cancelled", exits 130 |
| D1-c | Press Escape or Ctrl-C | Prints "Cancelled", exits 130 |
| D1-d | Stay on **Update all**, Enter | All registered modules are updated |

### D2. `lola market update` — three-option action menu

**Setup:** ensure at least one marketplace is registered (`lola market ls`).

**Run:**

```
lola market update
```

**Expected UI:**

```
? Update marketplaces:
  ❯ Update all
    Choose marketplace to update
    Cancel
```

**Scenarios to exercise:**

| Scenario | Action | Expected result |
|---|---|---|
| D2-a | Arrow ↓ to **Choose marketplace to update**, Enter | Single-select picker shows registered marketplaces; arrow keys navigate; Enter confirms and updates that marketplace |
| D2-b | Arrow ↓ to **Cancel**, Enter | Prints "Cancelled", exits 130 |
| D2-c | Press Escape | Prints "Cancelled", exits 130 |
| D2-d | Stay on **Update all**, Enter | All marketplaces are updated |

### D3. `lola market rm` — picker then confirmation

**Setup:** ensure at least one marketplace is registered.

**Run:**

```
lola market rm
```

**Scenarios to exercise:**

| Scenario | Action | Expected result |
|---|---|---|
| D3-a | Select a marketplace with Enter, then type `y` + Enter | Marketplace is removed |
| D3-b | Select a marketplace with Enter, then type `n` + Enter | Prints "Cancelled", marketplace is **not** removed |
| D3-c | Escape at the picker | Prints "Cancelled", exits 130, nothing removed |

**Also test with an explicit name but no `--force`:**

```
lola market rm <name>
```

Expected: skips picker, shows confirmation dialog directly.

---

## Summary

| Test | Type | Status |
|---|---|---|
| A1. `mod update --help` shows `--all` | Automated | ✅ |
| A2. `mod update` non-interactive → error | Automated | ✅ |
| A3. `mod update name --all` → conflict | Automated | ✅ |
| A4. `mod update --all` updates all | Automated | ✅ |
| A5. `mod update name` updates one | Automated | ✅ |
| B1. `market update --help` shows interactive note | Automated | ✅ |
| B2. `market update` non-interactive → error | Automated | ✅ |
| B3. `market update name --all` → conflict | Automated | ✅ |
| C1. `market rm --help` shows `--force` | Automated | ✅ |
| C2. `market rm name --force` removes immediately | Automated | ✅ |
| C3. `market rm name` then 'n' → cancelled | Automated | ✅ |
| C4. `market rm name` then 'y' → removed | Automated | ✅ |
| C5. `market rm` non-interactive → error | Automated | ✅ |
| D1. `mod update` interactive action menu | Manual | ⬜ |
| D2. `market update` interactive action menu | Manual | ⬜ |
| D3. `market rm` interactive picker + confirm | Manual | ⬜ |
