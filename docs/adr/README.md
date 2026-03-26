# Architecture Decision Records

We use ADRs to document significant architectural decisions for the Lola project.
ADRs are managed with [adr-tools](https://github.com/npryce/adr-tools).

## Quick Commands

```bash
# Create a new ADR
make adr-new use-mkdocs-for-documentation

# List existing ADRs
make adr-list

# Show help
make adr-help
```

## ADR Status

| Status | Meaning |
|--------|---------|
| **Proposed** | Under discussion, not yet accepted |
| **Accepted** | Approved and in effect |
| **Deprecated** | No longer relevant |
| **Superseded** | Replaced by a newer ADR |

## Writing ADRs

Use the [template](template.md) as a starting point. ADRs should be written
before implementing significant changes to ensure decisions are documented
and reviewed.
