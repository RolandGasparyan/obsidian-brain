# research/

Sandboxed research and exploration modules. **Isolated from the live trading
stack.** Anything under this directory:

- has **no** access to live API keys
- has **no** order-execution path
- does **not** import from `canary/`
- is **not** referenced by any systemd service, workflow, or live runtime
- must **not** be wired into `canary_executor.py`, `canary_strategy.py`, or
  the L99 / governance / arming chain without an ADR

The whole point of this directory is to give us a place to evaluate new
libraries, frameworks, and ideas without putting the SHA256-locked
`MA50W10` strategy or live accounts at risk.

## tradingagents/

[TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) —
multi-agent LLM trading framework. Vendored as a **pinned git submodule**.

### Boundary

This is a sandbox install only. It does **not** make trading decisions for
TITAN / VELOCITY / SENTINEL. The cinematic-only disclosure on the L3
leaderboard remains true: every live account still executes the same
SHA256-locked `MA50W10` strategy.

See [`../governance/ADR-005-tradingagents-integration.md`](../governance/ADR-005-tradingagents-integration.md)
for the governance discussion. The ADR is **DRAFT** — no live integration
has been authorized.

### Fetching

After clone:

```
git submodule update --init --recursive research/tradingagents
```

### Running (optional, in an isolated venv)

```
python3 -m venv .venv-tradingagents
. .venv-tradingagents/bin/activate
pip install -r research/tradingagents/requirements.txt   # if present
# Use a dedicated .env that does NOT contain live exchange keys.
```

**Do not** source live exchange credentials into the research venv. Use
paper/sandbox API keys or a stubbed key file. The `canary/` arming
pipeline is the only place live keys belong.

### Updating the pin

```
cd research/tradingagents
git fetch origin
git checkout <new-commit-sha>
cd ../..
git add research/tradingagents
git commit -m "research: bump TradingAgents pin to <sha>"
```

Pin changes should be reviewed as a normal PR. Do not auto-bump.
