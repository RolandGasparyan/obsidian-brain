# Decision: Scalp Battle Live Deploy — 2026-06-01

**Operator:** Roland Gasparyan  
**Date:** 2026-06-01  
**Authorized by:** Operator explicit confirmation (chat)

## Scope
Deploy `scalp_battle_live.py` to DO VPS (167.71.24.86) for real Gate.io spot trading.

## Strategy
- CMO(9) > 20 + EMA3 < EMA8 → SHORT signal
- Pairs: FLOKI/WIF/OP/SHIB/DOT/ADA/UNI/ATOM/BNB
- Trade size: $5 USDT per trade
- TP: 0.25% | SL: 0.15%
- Cooldown: 45s per pair

## Safety Invariants (Layer 1 — unchanged)
- SHORT-only (no LONG orders)
- Daily DD cap: TITAN $31.59 | VELOCITY $4.00 | SENTINEL $4.00
- Cold wallet floor: TITAN $100 | VELOCITY/SENTINEL $50
- Max 3 concurrent positions per agent

## Rollback
```bash
systemctl stop scalp-battle-live
systemctl disable scalp-battle-live
```

## SHA256
$(sha256sum /home/ubuntu/scalp_battle_live.py | awk '{print $1}')
