# Architecture Decision Records

We use ADRs to document significant architectural decisions for the Lola project.

## Creating an ADR

```bash
make adr-new topic-name
```

This copies the template to `docs/adr/topic-name.md`. Fill in the sections and open a PR.

## Naming Convention

ADR files use descriptive kebab-case names — no sequential numbers, no date prefix.
The date lives inside the document (`**Date**: YYYY-MM-DD`), not in the filename.
Topic names must be unique — two ADRs cannot cover the same topic simultaneously.

Examples:

```text
docs/adr/go-migration.md
docs/adr/use-postgresql.md
docs/adr/drop-redis-cache.md
```

## ADR Status

| Status | Meaning |
|--------|---------|
| **Proposed** | Under discussion, not yet accepted |
| **Accepted** | Approved and in effect |
| **Deprecated** | No longer relevant |
| **Superseded** | Replaced by a newer ADR |

## Writing ADRs

ADRs should be written before implementing significant changes to ensure decisions are
documented and reviewed. Use the [template](template.md) as a starting point.

## Updating the Template

If the ADR template needs to change (new sections, updated structure, etc.), document
the change here — describe what changed, why, and what existing ADRs are affected.
Then update `template.md` and submit the changes in a PR.
