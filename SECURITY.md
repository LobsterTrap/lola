# Security Policy

## Supported Versions

Lola is currently pre-1.0. Security fixes are applied to the **latest release only**.
We encourage all users to keep Lola up to date.

| Version | Supported |
|---------|-----------|
| Latest  | Yes |
| Older releases | No |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

To report a vulnerability, use GitHub's private vulnerability reporting:
[Report a vulnerability](https://github.com/LobsterTrap/lola/security/advisories/new)

Do not use public GitHub issues or discussions for vulnerability details as they
are visible to everyone.

Please include the following in your report:

- A description of the vulnerability and its potential impact
- Steps to reproduce the issue
- Any suggested mitigations or patches, if available

## Disclosure Policy

We follow a coordinated disclosure process:

1. **Acknowledge** — We will acknowledge receipt of your report within **5 business days**.
2. **Investigate** — We will investigate and keep you informed of our progress.
3. **Fix** — We aim to release a fix within **30 days** of confirmation. Complex
   vulnerabilities may take longer; we will communicate any delays.
4. **Disclose** — We will coordinate the public disclosure date with you. We ask that
   you do not disclose the vulnerability publicly until a fix is available.

We are committed to recognizing reporters who responsibly disclose vulnerabilities.

## Security Best Practices

- Always install Lola from the official PyPI package (`pip install lola-ai`) or the
  official GitHub releases.
- Verify release checksums when downloading binaries directly.
- Review any skills or modules before installing them, as they may contain executable
  scripts that run on your system.
- Keep Lola updated to the latest release to receive security patches.

## Scope

Security issues in Lola's own code are in scope. The following are generally out of
scope:

- Vulnerabilities in third-party skills or modules distributed via the marketplace
- Issues in the AI assistants Lola installs to (Claude Code, Cursor, etc.)
- Social engineering attacks
