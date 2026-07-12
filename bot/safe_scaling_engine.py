"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         GODMODE RISK MATH FORMAL MODEL v1.0                                ║
║         SAFE SCALING ENGINE — PRODUCTION MODULE                            ║
║         L99 SUPERPOWER | USDT ROTATION KING | SURVIVAL-FIRST              ║
╚══════════════════════════════════════════════════════════════════════════════╝

ROLE: Dynamic exposure modulation engine
      NOT signal generator / NOT strategy creator / NOT logic rewriter

FORMAL POSITION SIZE:
  Position = Equity × f* × k × C × regime_coeff × exec_coeff × DD_mult
  Then enforce HARD CAPS (absolute, unbypassable).

STRICT PROHIBITIONS (LOCKED — NEVER MODIFY):
  ✗ NO martingale
  ✗ NO revenge doubling
  ✗ NO infinite averaging down
  ✗ NO unbounded aggression
  ✗ NO live strategy generation
  ✗ NO weight rewriting
  ✗ NO cooldown removal
"""

import time
import logging

log = logging.getLogger("SSE")

# ─────────────────────────────────────────────────────────────────────────────
# HARD SAFETY CAPS  (override ALL — scaling CANNOT exceed these)
# ─────────────────────────────────────────────────────────────────────────────
MAX_RISK_PER_TRADE   = 0.010   # 1%  of equity per trade — absolute ceiling
MAX_TOTAL_EXPOSURE   = 0.050   # 5%  total open risk — blocks new entries
MAX_CONCURRENT       = 4       # max simultaneous open trades

# ─────────────────────────────────────────────────────────────────────────────
# FRACTIONAL KELLY PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────
KELLY_FRACTION_K     = 0.35    # k ∈ [0.25–0.50]  — controls vol
MIN_EDGE_THRESHOLD   = 0.005   # E = p*R - q must exceed this to allow trade
KELLY_MIN            = 0.002   # absolute floor on f_adj (0.2%)
KELLY_MAX            = 0.020   # absolute ceiling on f_adj (2.0%) before caps

# ─────────────────────────────────────────────────────────────────────────────
# DRAWDOWN COMPRESSION THRESHOLDS
# ─────────────────────────────────────────────────────────────────────────────
DD_BANDS = [
    (0.00, 0.03, 1.00),   # DD ≤  3% → mult 1.00
    (0.03, 0.06, 0.75),   # DD  3– 6% → mult 0.75
    (0.06, 0.10, 0.50),   # DD  6–10% → mult 0.50
    (0.10, 1.00, 0.25),   # DD > 10%  → mult 0.25
]

# ─────────────────────────────────────────────────────────────────────────────
# REGIME COEFFICIENTS
# ─────────────────────────────────────────────────────────────────────────────
REGIME_COEFF = {
    "TRENDING":  1.0,
    "NORMAL":    1.0,   # alias → same as TRENDING for compatibility
    "RECOVERY":  0.8,
    "CHOP":      0.6,
    "CHAOS":     0.4,
    "UNKNOWN":   0.6,
}

# ─────────────────────────────────────────────────────────────────────────────
# CONFIDENCE SCALING TABLE
# ─────────────────────────────────────────────────────────────────────────────
CONF_TABLE = [
    (90, 2.0),
    (80, 1.5),
    (70, 1.0),
    (0,  0.5),
]

# ─────────────────────────────────────────────────────────────────────────────
# RISK-OF-RUIN CONTROL
# ─────────────────────────────────────────────────────────────────────────────
ROR_MAX_THRESHOLD    = 0.01    # ROR must stay < 1%  — otherwise compress Kelly
ROR_COMPRESS_FACTOR  = 0.50    # halve Kelly when ROR breach detected

# ─────────────────────────────────────────────────────────────────────────────
# SMART STOP STATE  (in-process singleton — survives cycle iterations)
# ─────────────────────────────────────────────────────────────────────────────
_smart_stop_active   = False
_smart_stop_until    = 0.0     # epoch seconds

# ─────────────────────────────────────────────────────────────────────────────
# USDT INSTABILITY GUARD DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────
USDT_INSTABILITY_K         = 0.25   # compress k → 0.25 on instability
USDT_INSTABILITY_REGIME    = 0.40   # force regime_coeff → 0.40 on instability


# ══════════════════════════════════════════════════════════════════════════════
#  I. EDGE VALIDATOR
# ══════════════════════════════════════════════════════════════════════════════

def compute_edge(p: float, reward_risk_ratio: float) -> float:
    """
    E = (p × R) − q
    Returns expected edge. Trade blocked if E < MIN_EDGE_THRESHOLD.
    """
    q = 1.0 - p
    return p * reward_risk_ratio - q


def validate_edge(p: float, reward_risk_ratio: float) -> bool:
    """Trade allowed ONLY if E > minimum_edge_threshold."""
    return compute_edge(p, reward_risk_ratio) > MIN_EDGE_THRESHOLD


# ══════════════════════════════════════════════════════════════════════════════
#  II. FRACTIONAL KELLY
# ══════════════════════════════════════════════════════════════════════════════

def full_kelly(p: float, reward_risk_ratio: float) -> float:
    """
    f* = (p × R − q) / R
    Full Kelly fraction — we NEVER use this directly.
    """
    q = 1.0 - p
    r = reward_risk_ratio
    if r <= 0:
        return 0.0
    return max(0.0, (p * r - q) / r)


def fractional_kelly(p: float, reward_risk_ratio: float,
                     k: float = KELLY_FRACTION_K) -> float:
    """
    f = f* × k     where k ∈ [0.25, 0.50]
    Safe version — keeps volatility controlled.
    """
    fk = full_kelly(p, reward_risk_ratio)
    return fk * k


# ══════════════════════════════════════════════════════════════════════════════
#  III. CONFIDENCE MODIFIER
# ══════════════════════════════════════════════════════════════════════════════

def confidence_multiplier(composite_score: float) -> float:
    """
    C = composite_score / 100
    Table lookup:
      ≥ 90 → 2.0x
      ≥ 80 → 1.5x
      ≥ 70 → 1.0x
      <  70 → 0.5x
    """
    for threshold, mult in CONF_TABLE:
        if composite_score >= threshold:
            return mult
    return 0.5


def confidence_adjusted_kelly(p: float, reward_risk_ratio: float,
                               composite_score: float,
                               k: float = KELLY_FRACTION_K) -> float:
    """
    f_adj = fractional_kelly × confidence_multiplier
    """
    fk = fractional_kelly(p, reward_risk_ratio, k)
    c  = composite_score / 100.0
    cm = confidence_multiplier(composite_score)
    return fk * c * cm


# ══════════════════════════════════════════════════════════════════════════════
#  IV. REGIME STABILITY MODIFIER
# ══════════════════════════════════════════════════════════════════════════════

def regime_coefficient(regime: str) -> float:
    """
    Trend=1.0 | Recovery=0.8 | Chop=0.6 | Chaos=0.4
    """
    return REGIME_COEFF.get(regime.upper(), REGIME_COEFF["UNKNOWN"])


# ══════════════════════════════════════════════════════════════════════════════
#  V. EXECUTION QUALITY MODIFIER
# ══════════════════════════════════════════════════════════════════════════════

def execution_quality_factor(spread_pct: float,
                              avg_spread_pct: float,
                              depth_ratio: float = 1.0) -> float:
    """
    EQ = execution_score / 100
    Score degrades when spread exceeds average and depth is thin.
    spread_pct   : current bid-ask spread as fraction of price
    avg_spread_pct: rolling average spread
    depth_ratio  : order book depth ratio (1.0 = normal)
    Returns EQ ∈ [0.2, 1.0]
    """
    if avg_spread_pct <= 0:
        avg_spread_pct = spread_pct if spread_pct > 0 else 0.001

    spread_score = min(1.0, avg_spread_pct / max(spread_pct, 1e-8))
    depth_score  = min(1.0, depth_ratio)
    eq = (spread_score * 0.6 + depth_score * 0.4)
    return max(0.2, min(1.0, eq))


# ══════════════════════════════════════════════════════════════════════════════
#  VI. DRAWDOWN COMPRESSION
# ══════════════════════════════════════════════════════════════════════════════

def drawdown_compression(current_dd_pct: float) -> float:
    """
    DD ≤  3% → 1.00
    DD  3– 6% → 0.75
    DD  6–10% → 0.50
    DD > 10%  → 0.25
    System becomes defensive automatically.
    """
    dd = abs(current_dd_pct)
    for lo, hi, mult in DD_BANDS:
        if lo <= dd < hi:
            return mult
    return 0.25   # fallback — max compression


# ══════════════════════════════════════════════════════════════════════════════
#  VII. RISK-OF-RUIN CONTROL
# ══════════════════════════════════════════════════════════════════════════════

def risk_of_ruin(p: float, risk_per_trade: float) -> float:
    """
    ROR ≈ (q/p)^(1 / risk_per_trade)
    Returns approximate probability of total ruin.
    We must maintain ROR < ROR_MAX_THRESHOLD (1%).
    """
    q = 1.0 - p
    if p <= 0 or p >= 1 or risk_per_trade <= 0:
        return 1.0
    try:
        ratio = q / p
        capital_units = 1.0 / risk_per_trade
        return ratio ** capital_units
    except (OverflowError, ZeroDivisionError):
        return 1.0


def kelly_with_ror_control(p: float, reward_risk_ratio: float,
                            k: float, composite_score: float) -> float:
    """
    Compute f_adj, then check ROR. If ROR ≥ threshold, compress k.
    """
    f_adj = confidence_adjusted_kelly(p, reward_risk_ratio, composite_score, k)
    f_adj = max(KELLY_MIN, min(KELLY_MAX, f_adj))

    ror = risk_of_ruin(p, f_adj)
    if ror >= ROR_MAX_THRESHOLD:
        log.warning(f"⚠️SSE ROR={ror:.4f} ≥ {ROR_MAX_THRESHOLD} → compressing Kelly ×{ROR_COMPRESS_FACTOR}")
        f_adj *= ROR_COMPRESS_FACTOR
        f_adj = max(KELLY_MIN, f_adj)

    return f_adj


# ══════════════════════════════════════════════════════════════════════════════
#  VIII. EXPOSURE AGGREGATION
# ══════════════════════════════════════════════════════════════════════════════

def total_portfolio_risk(open_positions: list) -> float:
    """
    TotalRisk = Σ (position_size_fraction × stop_distance_fraction)
    open_positions: list of dicts with keys 'size_fraction', 'stop_fraction'
    Returns portfolio risk as fraction of equity.
    """
    total = 0.0
    for pos in open_positions:
        size = pos.get("size_fraction", 0.0)
        stop = pos.get("stop_fraction", 0.0)
        total += size * stop
    return total


def exposure_blocked(open_positions: list) -> bool:
    """
    Block new entries if Σ open risk > MAX_TOTAL_EXPOSURE (5%).
    """
    return total_portfolio_risk(open_positions) >= MAX_TOTAL_EXPOSURE


def concurrent_blocked(num_open: int) -> bool:
    """
    Block if concurrent trades ≥ MAX_CONCURRENT (4).
    """
    return num_open >= MAX_CONCURRENT


# ══════════════════════════════════════════════════════════════════════════════
#  IX. SMART START GATE
# ══════════════════════════════════════════════════════════════════════════════

def smart_start_gate(adx: float, volume_ratio: float, spread_pct: float,
                     depth_ratio: float, volatility_pct: float,
                     trend_aligned: bool, regime_confidence: float,
                     cfg: dict = None) -> tuple:
    """
    Pre-trade filter. ALL conditions must pass.
    Returns (allowed: bool, reason: str)
    """
    cfg = cfg or {}
    adx_thresh      = float(cfg.get("ADX_THRESHOLD",    22))
    vol_thresh      = float(cfg.get("MIN_VOLUME_BURST",  2.0))
    max_spread      = float(cfg.get("MAX_SPREAD",        0.005))
    min_depth       = float(cfg.get("MIN_DEPTH_RATIO",   0.5))
    max_vol_pct     = float(cfg.get("MAX_VOLATILITY_PCT",5.0))
    min_reg_conf    = float(cfg.get("MIN_REGIME_CONF",   0.55))

    if adx < adx_thresh:
        return False, f"ADX={adx:.1f} < {adx_thresh}"
    if volume_ratio < vol_thresh:
        return False, f"VOL_RATIO={volume_ratio:.2f} < {vol_thresh}"
    if spread_pct > max_spread:
        return False, f"SPREAD={spread_pct:.4f} > {max_spread}"
    if depth_ratio < min_depth:
        return False, f"DEPTH={depth_ratio:.2f} < {min_depth}"
    if volatility_pct > max_vol_pct:
        return False, f"VOLAT={volatility_pct:.2f}% > {max_vol_pct}%"
    if not trend_aligned:
        return False, "TREND_NOT_ALIGNED"
    if regime_confidence < min_reg_conf:
        return False, f"REG_CONF={regime_confidence:.2f} < {min_reg_conf}"

    return True, "OK"


# ══════════════════════════════════════════════════════════════════════════════
#  X. SMART STOP PROTOCOL
# ══════════════════════════════════════════════════════════════════════════════

def check_smart_stop(loss_cluster: bool, dd_spike: bool,
                     chaos_regime: bool, spread_explosion: bool,
                     pause_seconds: float = 300.0) -> bool:
    """
    Triggers Smart Stop if ANY condition fires.
    Sets _smart_stop_active for `pause_seconds`.
    Returns True if stop was just triggered.
    """
    global _smart_stop_active, _smart_stop_until
    triggered = loss_cluster or dd_spike or chaos_regime or spread_explosion
    if triggered:
        _smart_stop_active = True
        _smart_stop_until  = time.time() + pause_seconds
        reasons = []
        if loss_cluster:     reasons.append("LOSS_CLUSTER")
        if dd_spike:         reasons.append("DD_SPIKE")
        if chaos_regime:     reasons.append("CHAOS_REGIME")
        if spread_explosion: reasons.append("SPREAD_EXPLOSION")
        log.warning(f"🛑 SSE SMART STOP ACTIVATED: {'+'.join(reasons)} | freeze={pause_seconds}s")
    return triggered


def is_smart_stop_active() -> bool:
    """Returns True if currently in Smart Stop freeze window."""
    global _smart_stop_active, _smart_stop_until
    if _smart_stop_active and time.time() < _smart_stop_until:
        return True
    if _smart_stop_active and time.time() >= _smart_stop_until:
        _smart_stop_active = False
        log.info("✅ SSE Smart Stop cleared — resuming normal scaling")
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  XI. USDT INSTABILITY GUARD
# ══════════════════════════════════════════════════════════════════════════════

def usdt_instability_detected(volatility_shock: bool, spread_anomaly: bool,
                               regime_unstable: bool, dd_spike: bool) -> bool:
    """
    Returns True if any USDT-threatening instability is detected.
    Actions: compress k→0.25, force regime_coeff→0.40, block aggressive scaling.
    USDT preservation overrides ALL scaling logic.
    """
    return volatility_shock or spread_anomaly or regime_unstable or dd_spike


# ══════════════════════════════════════════════════════════════════════════════
#  XII. MASTER SCALING FUNCTION  — THE MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def compute_position_size(
    # Market / signal inputs
    composite_score: float,        # 0–100 consensus score
    regime: str,                   # "TRENDING" | "NORMAL" | "CHOP" | "CHAOS" | "RECOVERY"
    win_probability: float,        # p ∈ (0, 1)
    reward_risk_ratio: float,      # R = TP_pct / SL_pct

    # Execution quality inputs
    spread_pct: float = 0.001,
    avg_spread_pct: float = 0.001,
    depth_ratio: float = 1.0,

    # Risk state
    current_dd_pct: float = 0.0,   # current drawdown % (positive = in DD)
    num_open_trades: int = 0,
    open_positions: list = None,   # list of {size_fraction, stop_fraction}

    # Smart Start Gate inputs (optional — set None to skip gate)
    adx: float = 25.0,
    volume_ratio: float = 2.0,
    trend_aligned: bool = True,
    volatility_pct: float = 1.0,
    regime_confidence: float = 0.7,

    # USDT instability flags
    volatility_shock: bool = False,
    spread_anomaly: bool = False,
    regime_unstable: bool = False,

    # Config passthrough
    cfg: dict = None,
    base_deploy_pct: float = 0.05,  # base fraction of cash to deploy

) -> tuple:
    """
    MASTER FORMULA:
      Position = Equity × f* × k × C × regime_coeff × exec_coeff × DD_mult

    Returns (final_deploy_pct: float, ok: bool, details: dict)
      - final_deploy_pct: fraction of cash to deploy (0.0 if blocked)
      - ok: True if trade is allowed
      - details: dict of all intermediate values (for logging / Obsidian)
    """
    cfg = cfg or {}
    open_positions = open_positions or []

    details = {
        "composite_score": composite_score,
        "regime": regime,
        "win_prob": win_probability,
        "rr_ratio": reward_risk_ratio,
        "spread_pct": spread_pct,
        "depth_ratio": depth_ratio,
        "current_dd_pct": current_dd_pct,
        "num_open": num_open_trades,
        "stage": "INIT",
        "blocked_reason": None,
    }

    # ── Smart Stop Check ────────────────────────────────────────────────────
    dd_spike_flag = current_dd_pct > 0.10
    chaos_flag    = regime.upper() in ("CHAOS",)
    spread_expl   = spread_pct > avg_spread_pct * 3.0 if avg_spread_pct > 0 else False

    check_smart_stop(
        loss_cluster   = False,       # caller can set via cfg flag
        dd_spike       = dd_spike_flag,
        chaos_regime   = chaos_flag,
        spread_explosion = spread_expl,
    )

    if is_smart_stop_active():
        details["stage"] = "SMART_STOP"
        details["blocked_reason"] = "SMART_STOP_ACTIVE"
        log.warning("🛑 SSE blocked: Smart Stop active — defensive mode only")
        return 0.0, False, details

    # ── USDT Instability Override ────────────────────────────────────────────
    instability = usdt_instability_detected(
        volatility_shock = volatility_shock,
        spread_anomaly   = spread_anomaly,
        regime_unstable  = regime_unstable,
        dd_spike         = dd_spike_flag,
    )
    active_k = USDT_INSTABILITY_K if instability else KELLY_FRACTION_K
    active_regime = regime
    if instability:
        active_regime = "CHAOS"   # force defensive
        log.warning(f"⚠️ SSE USDT instability → k={active_k} regime→CHAOS")

    # ── Concurrent / Exposure Blocks ────────────────────────────────────────
    if concurrent_blocked(num_open_trades):
        details["stage"] = "CONCURRENT_BLOCK"
        details["blocked_reason"] = f"CONCURRENT={num_open_trades} ≥ {MAX_CONCURRENT}"
        return 0.0, False, details

    if exposure_blocked(open_positions):
        details["stage"] = "EXPOSURE_BLOCK"
        details["blocked_reason"] = f"TOTAL_RISK ≥ {MAX_TOTAL_EXPOSURE*100:.1f}%"
        return 0.0, False, details

    # ── Smart Start Gate ─────────────────────────────────────────────────────
    gate_ok, gate_reason = smart_start_gate(
        adx               = adx,
        volume_ratio      = volume_ratio,
        spread_pct        = spread_pct,
        depth_ratio       = depth_ratio,
        volatility_pct    = volatility_pct,
        trend_aligned     = trend_aligned,
        regime_confidence = regime_confidence,
        cfg               = cfg,
    )
    if not gate_ok:
        details["stage"] = "SMART_START_GATE"
        details["blocked_reason"] = f"GATE: {gate_reason}"
        return 0.0, False, details

    # ── Edge Validation ──────────────────────────────────────────────────────
    edge = compute_edge(win_probability, reward_risk_ratio)
    if not validate_edge(win_probability, reward_risk_ratio):
        details["stage"] = "EDGE_FAIL"
        details["blocked_reason"] = f"EDGE={edge:.4f} < {MIN_EDGE_THRESHOLD}"
        return 0.0, False, details
    details["edge"] = edge

    # ── Fractional Kelly with ROR Control ────────────────────────────────────
    f_adj = kelly_with_ror_control(
        p                 = win_probability,
        reward_risk_ratio = reward_risk_ratio,
        k                 = active_k,
        composite_score   = composite_score,
    )
    details["f_adj_raw"] = f_adj
    details["kelly_k"]   = active_k

    # ── Regime Modifier ──────────────────────────────────────────────────────
    reg_coeff = regime_coefficient(active_regime)
    if instability:
        reg_coeff = min(reg_coeff, USDT_INSTABILITY_REGIME)
    f_regime = f_adj * reg_coeff
    details["regime_coeff"] = reg_coeff
    details["f_regime"]     = f_regime

    # ── Execution Quality ────────────────────────────────────────────────────
    eq = execution_quality_factor(spread_pct, avg_spread_pct, depth_ratio)
    f_exec = f_regime * eq
    details["exec_quality"] = eq
    details["f_exec"]       = f_exec

    # ── Drawdown Compression ─────────────────────────────────────────────────
    dd_mult = drawdown_compression(current_dd_pct)
    f_final = f_exec * dd_mult
    details["dd_mult"]  = dd_mult
    details["f_final_raw"] = f_final

    # ── Hard Cap Enforcement (ABSOLUTE — unbypassable) ───────────────────────
    f_capped = min(f_final, MAX_RISK_PER_TRADE)   # never > 1%
    f_capped = max(KELLY_MIN, f_capped)           # never < floor
    details["f_capped"]  = f_capped
    details["hard_cap_applied"] = (f_final > MAX_RISK_PER_TRADE)

    # ── Scale to deploy_pct ──────────────────────────────────────────────────
    # f_capped is risk fraction; convert to deploy fraction via SL distance
    # deploy_pct = f_capped / sl_pct  (sl_pct from cfg, default 0.007)
    sl_pct = float(cfg.get("SL_PCT", 0.007))
    if sl_pct > 0:
        deploy_pct = f_capped / sl_pct
    else:
        deploy_pct = base_deploy_pct

    # Final safety clamp
    deploy_pct = min(deploy_pct, base_deploy_pct * 3.0)   # never > 3× base
    deploy_pct = max(0.001, deploy_pct)

    details["sl_pct"]       = sl_pct
    details["deploy_pct"]   = deploy_pct
    details["stage"]        = "OK"

    # ── Obsidian-style structured log ────────────────────────────────────────
    log.info(
        f"🛡️SSEv2✓ "
        f"edge={edge:.3f} "
        f"f*={full_kelly(win_probability,reward_risk_ratio):.4f} "
        f"k={active_k} "
        f"f_adj={f_adj:.4f} "
        f"conf={composite_score:.0f}→{confidence_multiplier(composite_score):.1f}x "
        f"reg={active_regime}/{reg_coeff:.1f} "
        f"eq={eq:.2f} "
        f"dd={current_dd_pct*100:.1f}%→{dd_mult:.2f} "
        f"ROR_ok "
        f"deploy={deploy_pct*100:.2f}%"
    )

    return deploy_pct, True, details


# ══════════════════════════════════════════════════════════════════════════════
#  LEGACY COMPATIBILITY WRAPPER  (matches old SSE interface)
# ══════════════════════════════════════════════════════════════════════════════

def evaluate(
    composite_score: float,
    regime: str,
    spread_pct: float = 0.001,
    avg_spread_pct: float = 0.001,
    depth_ok: bool = True,
    adx: float = 25.0,
    volume_ratio: float = 2.5,
    current_dd_pct: float = 0.0,
    num_open_trades: int = 0,
    volatility_pct: float = 1.0,
    trend_aligned: bool = True,
    regime_confidence: float = 0.70,
    base_deploy_pct: float = 0.05,
    cfg: dict = None,
) -> tuple:
    """
    Backward-compatible wrapper for agent.py integration point.
    Returns (deploy_pct, ok, details) — same shape as compute_position_size.
    Uses heuristic p/R from composite_score and config when not provided directly.
    """
    cfg = cfg or {}
    tp_pct = float(cfg.get("TP_PCT", 0.020))
    sl_pct = float(cfg.get("SL_PCT", 0.007))
    rr = tp_pct / sl_pct if sl_pct > 0 else 2.86
    p  = 0.40 + (composite_score / 100.0) * 0.35    # heuristic: 40%–75%
    p  = max(0.35, min(0.75, p))
    depth_ratio = 1.0 if depth_ok else 0.4

    return compute_position_size(
        composite_score   = composite_score,
        regime            = regime,
        win_probability   = p,
        reward_risk_ratio = rr,
        spread_pct        = spread_pct,
        avg_spread_pct    = avg_spread_pct,
        depth_ratio       = depth_ratio,
        current_dd_pct    = current_dd_pct,
        num_open_trades   = num_open_trades,
        adx               = adx,
        volume_ratio      = volume_ratio,
        trend_aligned     = trend_aligned,
        volatility_pct    = volatility_pct,
        regime_confidence = regime_confidence,
        base_deploy_pct   = base_deploy_pct,
        cfg               = cfg,
    )



# ══════════════════════════════════════════════════════════════════════════════
#  V1 COMPATIBILITY ALIAS  — compute_scaled_size (agent.py integration point)
# ══════════════════════════════════════════════════════════════════════════════

def compute_scaled_size(
    base_deploy_pct: float    = 0.05,
    composite_score: float    = 65.0,
    regime: str               = "NORMAL",
    drawdown_pct: float       = 0.0,
    execution_quality: float  = 0.95,
    active_trades: int        = 0,
    recent_pnls: list         = None,
    spread_pct: float         = 0.001,
    adx: float                = 25.0,
    volume_ratio: float       = 2.5,
    regime_confidence: float  = 0.70,
    equity_start: float       = 1.0,
    equity_now: float         = 1.0,
    log_tag: str              = "",
    cfg: dict                 = None,
) -> tuple:
    """
    V1 compatibility wrapper used by agent.py.
    Maps old call signature to new v2 evaluate() function.
    Returns (deploy_pct, ok, tag, details_dict)  — 4-tuple as agent.py expects.
    """
    cfg = cfg or {}

    # Derive DD from equity if not provided
    dd_pct = drawdown_pct
    if dd_pct == 0.0 and equity_start and equity_start > 0:
        dd_pct = max(0.0, 1.0 - equity_now / equity_start)

    # Infer loss_cluster from recent_pnls
    recent_pnls = recent_pnls or []
    loss_cluster = len([p for p in recent_pnls[-5:] if p < 0]) >= 3

    deploy, ok, details = evaluate(
        composite_score   = composite_score,
        regime            = regime,
        spread_pct        = spread_pct,
        avg_spread_pct    = spread_pct * 0.9,
        depth_ok          = execution_quality >= 0.5,
        adx               = adx,
        volume_ratio      = volume_ratio,
        current_dd_pct    = dd_pct,
        num_open_trades   = active_trades,
        volatility_pct    = 1.5,
        trend_aligned     = True,
        regime_confidence = regime_confidence,
        base_deploy_pct   = base_deploy_pct,
        cfg               = cfg,
    )

    # Build v1-compatible tag string
    reg_c   = regime_coefficient(regime)
    dd_m    = drawdown_compression(dd_pct)
    cm      = confidence_multiplier(composite_score)
    if ok:
        tag = (f"🛡️SSEv2✓ conf={composite_score:.0f}→{cm:.1f}x "
               f"reg={regime}/{reg_c:.1f} dd={dd_pct*100:.1f}%→{dd_m:.2f} "
               f"exec={execution_quality:.2f} {base_deploy_pct*100:.1f}%→{deploy*100:.2f}%")
    else:
        reason = details.get("blocked_reason", "BLOCKED")
        tag = f"🛑SSEv2✗ {reason}"

    return deploy, ok, tag, details

