#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(realpath "$(dirname "$0")")"
REPO_DIR="$(realpath "${SCRIPT_DIR}/../../..")"

TEST_LANG="${1:-python}"
TAGS="${E2E_TAGS:-~@wip}"

cat <<EOF

---------------------
  Running BDD tests
---------------------

EOF

case "$TEST_LANG" in
    python)
        # run from e2e directory
        pip install --no-deps -e "${REPO_DIR}" >/dev/null 2>/dev/null
        cd "${REPO_DIR}/e2e"
        exec behave --tags="$TAGS" --no-capture --format progress
        ;;
    go)
        # run from e2e/go directory
        cd "${REPO_DIR}/e2e/go"
        exec godog --tags="$TAGS" ../features
        ;;
    *)
        echo "Unknown language: $TEST_LANG" >&2
        exit 1
        ;;
esac
