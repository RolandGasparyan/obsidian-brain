# Three-Project Verification and Render Release Runbook

Date: 2026-07-13
Owner: Roland Gasparyan
Status: Deployment blocked; one repository audited, two inaccessible.

## Projects

- RolandGasparyan/BOOKING-AI-AGENT — GitHub connector and public lookup return Not Found.
- - RolandGasparyan/6-empires-os — accessible; audited at main commit a3f450d6c537.
- - RolandGasparyan/trading-guru-empire — GitHub connector and public lookup return Not Found.
## Release gates

1. Restore repository and GitHub CLI access.
2. 2. Remove or rotate exposed credentials before any deployment.
3. 3. Fix critical/high security, correctness, data-integrity, and CI blockers on a non-default branch.
4. 4. Add required API integration, web, sync-service, data-quality, and deployment regression tests.
5. 5. Make CI fail when no tests run and pin deployment to the CI-approved SHA.
6. 6. Require real datastore readiness; fail deployment when health probes fail.
7. 7. Upgrade vulnerable production dependencies and re-run npm audit and pip-audit.
8. 8. Add migrations, backup/restore coverage, and a tested rollback procedure.
9. 9. Create and validate a Render Blueprint only after the application passes gates 1-8.
10. 10. Deploy to staging, verify health/logs/metrics, then record production go/no-go.
## Confirmed verification results for 6-empires-os

- API Docker image: PASS.
- - Web Docker image and 21-route production build: PASS.
- - TypeScript type-check: PASS.
- - Compose validation: PASS with obsolete version warning.
- - Disposable production-style stack: PASS for PostgreSQL, Redis, API, and web startup.
- - API smoke: PASS for health, registration, login, identity, refresh rotation, and logout.
- - Web smoke: PASS for root and founder login routes.
- - Datastore readiness test: FAIL — health returns 200 OK while PostgreSQL is stopped.
- - Python tests: FAIL — zero tests collected; CI explicitly accepts this.
- - Web lint: FAIL — prompts for missing ESLint configuration instead of running non-interactively.
- - Python lint: FAIL — 14 findings.
- - GitHub Action syntax: PASS with actionlint.
- - Web production dependencies: FAIL — 1 critical and 3 moderate findings.
- - API dependencies: FAIL — 25 advisories across 6 packages.
- - Git history secret scan: FAIL — 8 potential findings; separate manual review confirmed credential material in brain data.
## Critical release blockers

- Remote root command injection in the publicly proxied empire-sync key endpoint.
- - Credential/private brain material is committed and publicly served; rotate affected credentials and sanitize history/data.
- - Public registration can grant founder privileges based only on the submitted founder email.
- - CI passes with zero tests; deploy workflow is not pinned to the approved commit and can report success after failed probes.
- - Synthetic financial/operational metrics are presented as live data.
- - Database failures are swallowed while the API reports healthy/successful durable writes.
- - No production schema migrations; backups omit persisted components and restore procedures drift.
- - Internal agent tasks, memory, chat history, and WebSocket events are readable without authentication.
## CI and deployment status

- Latest CI run for a3f450d6c537: success, but it contains no effective test baseline.
- - Latest Deploy to VPS run: failed at the SSH deploy step.
- - Recent pattern: repeated CI successes followed by failed deployments.
- - Detailed Actions logs are blocked because local GitHub CLI authentication is invalid.
- - No render.yaml exists. The API container is hard-coded to port 8000 and is not Render-ready as written.
- - Render CLI/MCP authentication is unavailable; production deployment must not start before the release blockers are fixed.
## Next approved remediation stage

On a new branch, fix one security finding at a time, beginning with: disable the public sync control plane and shell execution; rotate and remove exposed credentials; remove founder-by-email self-registration; enforce authentication on internal reads/WebSockets; then establish truthful readiness, migrations, a real test baseline, dependency upgrades, and SHA-pinned fail-closed deployment.
