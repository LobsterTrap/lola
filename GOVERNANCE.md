# Governance

This document defines the governance of the Lola project. It describes the roles
contributors may hold, how decisions are made, and how to participate in the project.

## Roles

### Lead

The project Lead sets the overall direction of Lola, has the final tie-break on
decisions where consensus cannot be reached, and holds Core Maintainer rights.

| Name | GitHub |
|------|--------|
| Igor Brandao | [@mrbrandao](https://github.com/mrbrandao) |

### Core Maintainer

Core Maintainers have full merge rights across the project, participate in all
governance decisions, and are responsible for nominating new Maintainers and Core
Maintainers.

| Name | GitHub |
|------|--------|
| Igor Brandao | [@mrbrandao](https://github.com/mrbrandao) |
| Katie Mulliken | [@SecKatie](https://github.com/SecKatie) |

### Maintainer

Maintainers are active contributors who have been nominated by a Core Maintainer and
approved by the existing Core Maintainers. Maintainers have merge rights and assist
in reviewing and landing contributions.

There are currently no designated Maintainers beyond the Core Maintainers listed above.

### Contributor

A Contributor is anyone who has had a pull request merged into the project. Contributors
are the starting point on the contributor ladder and are eligible to be nominated as
Maintainers over time.

## Contributor Ladder

The project has a lightweight contributor ladder:

```text
Contributor → Maintainer → Core Maintainer → Lead
```

Advancement is invitation-based — a Core Maintainer nominates a candidate based on
sustained, quality contributions over time. There is no hard commit count; what matters
is the quality and consistency of contributions and alignment with the project's goals.

Nominations are approved by lazy consensus among Core Maintainers (see
[Decision-Making](#decision-making)).

## Decision-Making

Day-to-day decisions (PR merges, bug fixes, documentation, dependency updates) use
**lazy consensus**: a Maintainer or Core Maintainer approves the change, and if no
objection is raised within 48 hours, the change lands.

Significant decisions (architectural changes, breaking changes, new major features,
adding or removing Maintainers or Core Maintainers) are discussed openly in GitHub
Issues or Discussions. If consensus cannot be reached, the Lead has the final
tie-break.

## Pull Requests

- Every PR requires at least one approval from a Maintainer or Core Maintainer.
- Authors may not approve or merge their own PRs.
- Trivial changes (typos, broken links, formatting) may be merged by any Maintainer
  after a short window with no objections.

## Releases

Lola targets a monthly release on the **last Wednesday of each month**. Patch releases
may be cut at any time when a critical fix is needed.

## Code of Conduct

This project follows the
[Contributor Covenant Code of Conduct v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
Violations may be reported to the Core Maintainers via a GitHub Discussion marked
private, or by contacting the Lead directly.

## Communication

Project discussions happen openly in
[GitHub Issues](https://github.com/LobsterTrap/lola/issues) and
[GitHub Discussions](https://github.com/LobsterTrap/lola/discussions).
A community channel is planned and will be linked here once available.

## Amendments

Changes to this document require a pull request approved by all current Core
Maintainers.
