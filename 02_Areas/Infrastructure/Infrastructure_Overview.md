---
tags: [infrastructure, VPS, deployment]
status: active
---

# 🖥️ Infrastructure Overview

## 🌐 VPS Server
- **IP:** 167.71.24.86
- **OS:** Ubuntu (Kubernetes/Docker for microservices)
- **Monitoring:** Prometheus + Grafana visualization
- **Database:** PostgreSQL, Redis

## 🔄 GitHub Actions Workflows

| Workflow | Purpose | Run Cadence |
|---|---|---|
| `dashboard.yml` | Full snapshot — auth + balances + positions + logs | On demand |
| `status-report.yml` | Same shape as dashboard | On demand |
| `frontend-check.yml` | Verifies tradingguru.ai feed is real-time | On demand |
| `permutation-check.yml` | 3×3 KEY×SECRET matrix — catches swapped credentials | If auth fails |
| `halt-account.yml` | FAIL-CLOSED one account thread | Emergency |
| `restore-account.yml` | Restore halted account from backup | After halt |

## 🔐 Security Rules
- API keys belong only in environment variables.
- Never commit `sim_results_*.json`, `backtest_results_*.json`, `*.log`, or `.env`.
- Keyfiles stored at `/root/canary/.api_key_{main,sub1,sub2}` (chmod 0600).

## 🔗 Related Notes
- [[Multi_Account_Setup]]
- [[3-Layer Architecture]]
