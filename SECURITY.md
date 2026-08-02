# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| Latest  | ✅                 |
| < 1.0   | ❌                 |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### Private Reporting

**Please do NOT open public issues for security vulnerabilities.**

Instead, report privately via:

1. **GitHub Security Advisories** (preferred): Use the "Report a vulnerability" tab in the Security tab of this repository
2. **Email**: security@[our-domain].com (replace with actual contact)
4. **Encrypted**: PGP key available at [link-to-pgp-key]

### What to Include

Please provide:

- **Description** of the vulnerability
- **Steps to reproduce** (minimal PoC if possible)
- **Impact assessment** (what could an attacker achieve)
- **Affected versions** (if known)
- **Suggested fix** (if you have ideas)

### Response Timeline

| Severity | Initial Response | Fix Target |
|----------|------------------|------------|
| Critical | 24 hours         | 72 hours   |
| High     | 48 hours         | 1 week     |
| Medium   | 72 hours         | 2 weeks    |
| Low      | 1 week           | Next release |

## Security Features Enabled

This repository has the following GitHub security features enabled:

- ✅ **Push Protection** — Blocks secrets/tokens from being pushed
- ✅ **Private Vulnerability Reporting** — Private reporting channel enabled
- ✅ **Dependabot Alerts** — Automatic dependency vulnerability scanning
- ✅ **Dependabot Security Updates** — Auto-PR for vulnerable dependencies
- ✅ **Dependency Review** — Reviews dependency changes in PRs
- ✅ **CodeQL Code Scanning** — Automated SAST on every push/PR
- ✅ **Secret Scanning** — Detects leaked secrets in code/history
- ✅ **Secret Scanning Push Protection** — Blocks pushes containing secrets

## Branch Protection Rules

The following rules are enforced on protected branches (`main`, `release/*`):

- ✅ **Require PR before merge** — No direct pushes
- ✅ **Require approvals** — Minimum 1 review from code owners
- ✅ **Require status checks** — All CI checks must pass
- ✅ **Require linear history** — No merge commits on protected branches
- ✅ **Require signed commits** — GPG/SSH signature verification
- ✅ **Restrict pushes** — Only admins can force push
- ✅ **Dismiss stale reviews** — New commits dismiss old approvals

## Security Best Practices for Contributors

### Before Contributing

1. **Run security scans locally** — `npm audit`, `pip-audit`, `cargo audit`, etc.
2. **No secrets in code** — Use environment variables, GitHub secrets
3. **Minimal dependencies** — Audit new dependencies before adding
3. **Pin versions** — Use exact versions, avoid ranges (`^`, `~`)

### Code Review Checklist

- [ ] No hardcoded secrets, API keys, passwords
- [ ] Input validation on all user inputs
- [ ] Proper authentication/authorization checks
- [ ] No SQL injection / XSS / path traversal vectors
- [ ] Error handling doesn't leak sensitive info
- [ ] Dependencies are up-to-date and vulnerability-free

## Disclosure Policy

We follow **Coordinated Vulnerability Disclosure (CVD)**:

1. Reporter submits vulnerability privately
2. We acknowledge within stated timeline
3. We investigate and develop fix
4. We coordinate disclosure date with reporter
5. We publish advisory after fix is deployed
6. Credit given to reporter (unless anonymity requested)

## Security Contacts

- **Primary**: [Primary contact name] — [contact method]
- **Backup**: [Backup contact name] — [contact method]
- **PGP Key**: [Link to PGP public key]

---

*This policy is reviewed quarterly. Last updated: $(date +%Y-%m-%d)*