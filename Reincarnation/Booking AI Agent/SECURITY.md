# Security policy

## Reporting a vulnerability

Do not include secrets, personal booking data, or working exploit payloads in a
public issue. Report vulnerabilities privately through the repository owner's
GitHub security contact or private security-advisory channel. Include the
affected revision, impact, reproduction steps, and a minimal redacted proof.

Rotate any credential included in a report before sharing it. The maintainer
should acknowledge a valid report, establish severity, and coordinate a fix and
disclosure timeline before publishing details.

## Supported code

Security fixes target the current `main` branch. Older deployments should be
upgraded rather than patched independently.

## Production checklist

- Generate unique 32-byte-or-longer values for every enabled webhook/admin
  secret; never leave `CHANGE_ME` or reuse a secret between providers.
- Keep `/opt/reincarnation_booking/shared/.env` owned by `www-data` with mode
  `0600`. Keep the data directory at `0700`.
- Use an encrypted server volume or encrypted host filesystem. SQLite file
  permissions protect local access but are not a replacement for disk
  encryption.
- Bind Uvicorn only to loopback and expose it through the supplied TLS Nginx
  configuration.
- Pin the SSH host key in `SSH_KNOWN_HOSTS`; never disable host-key checking.
- Restrict admin routes by VPN or an explicit Nginx IP allowlist where possible,
  in addition to the admin secret.
- Keep the service at one worker unless sessions, schedulers, and the database
  are moved to multi-instance infrastructure.
- Leave festival outreach and social publishing disabled until a human approves
  the target list, copy, legal basis, and rate limits.
- Define retention periods for booking PII, application logs, and database
  backups. Securely remove expired copies according to the organization's data
  policy.
- Run both test suites, Ruff, Bandit, and `pip-audit` before deployment. Install
  with `--require-hashes` from the checked-in lock file.
- Rotate secrets immediately after suspected disclosure and re-register provider
  webhooks where required.

## Residual operational boundaries

The admin API uses a strong shared secret, not individual administrator accounts
or role-based access control. Treat it as a privileged service interface, keep
it behind network restrictions, and rotate it regularly. The SQLite design is
appropriate for a single protected instance; multi-host or high-availability
operation requires a transactional server database and centralized session/job
storage.
