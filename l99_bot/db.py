"""
L99 Bot — Database layer
Uses connection pool; never a bare module-level connection.
"""
import json
import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import Json

import config

logger = logging.getLogger("l99.db")

_pool: pg_pool.ThreadedConnectionPool | None = None


def init_pool() -> None:
    global _pool
    _pool = pg_pool.ThreadedConnectionPool(
        minconn=1, maxconn=5,
        dbname=config.DB_NAME, user=config.DB_USER,
        password=config.DB_PASS, host=config.DB_HOST,
        port=config.DB_PORT,
    )
    logger.info("DB connection pool initialised")


@contextmanager
def get_conn():
    if _pool is None:
        raise RuntimeError("DB pool not initialised — call init_pool() first")
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


# ── Schema bootstrap ──────────────────────────────────────────

def create_tables() -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS trades (
        id            SERIAL PRIMARY KEY,
        symbol        VARCHAR(20),
        entry_time    TIMESTAMP,
        exit_time     TIMESTAMP,
        entry_price   NUMERIC,
        exit_price    NUMERIC,
        position_size NUMERIC,
        risk_pct      NUMERIC,
        R_multiple    NUMERIC,
        fee           NUMERIC,
        slippage      NUMERIC,
        pnl           NUMERIC,
        equity_after  NUMERIC,
        status        VARCHAR(10) DEFAULT 'CLOSED'
    );

    CREATE TABLE IF NOT EXISTS signals (
        id              SERIAL PRIMARY KEY,
        symbol          VARCHAR(20),
        signal_time     TIMESTAMP,
        adx             NUMERIC,
        volume_ratio    NUMERIC,
        breakout_level  NUMERIC,
        regime_state    VARCHAR(20)
    );

    CREATE TABLE IF NOT EXISTS system_metrics (
        id              SERIAL PRIMARY KEY,
        timestamp       TIMESTAMP DEFAULT NOW(),
        live_sharpe     NUMERIC,
        drawdown        NUMERIC,
        open_positions  INTEGER,
        total_equity    NUMERIC
    );

    CREATE TABLE IF NOT EXISTS kill_events (
        id          SERIAL PRIMARY KEY,
        timestamp   TIMESTAMP DEFAULT NOW(),
        reason      TEXT,
        equity      NUMERIC
    );

    CREATE TABLE IF NOT EXISTS governance_events (
        id               SERIAL PRIMARY KEY,
        timestamp        TIMESTAMP DEFAULT NOW(),
        event_type       VARCHAR(50),
        old_state        VARCHAR(30),
        new_state        VARCHAR(30),
        reason           TEXT,
        metrics_snapshot JSONB
    );
    """
    alter = """
    ALTER TABLE trades ADD COLUMN IF NOT EXISTS risk_level       VARCHAR(20) DEFAULT 'LEVEL_NORMAL';
    ALTER TABLE trades ADD COLUMN IF NOT EXISTS allocation_weight FLOAT      DEFAULT 1.0;
    ALTER TABLE trades ADD COLUMN IF NOT EXISTS exchange_id      VARCHAR(20) DEFAULT 'BINANCE';

    CREATE TABLE IF NOT EXISTS execution_metrics (
        id                SERIAL PRIMARY KEY,
        timestamp         TIMESTAMP DEFAULT NOW(),
        exchange          VARCHAR(20),
        symbol            VARCHAR(20),
        order_id          VARCHAR(80),
        latency_ms        NUMERIC,
        spread_bps        NUMERIC,
        expected_slippage NUMERIC,
        actual_slippage   NUMERIC,
        partial_fill      BOOLEAN DEFAULT FALSE,
        maker_flag        BOOLEAN DEFAULT FALSE
    );
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
            cur.execute(alter)
    logger.info("Tables verified / created")


# ── Write helpers ─────────────────────────────────────────────

def log_trade(d: dict) -> None:
    sql = """
        INSERT INTO trades
            (symbol, entry_time, exit_time, entry_price, exit_price,
             position_size, risk_pct, R_multiple, fee, slippage,
             pnl, equity_after)
        VALUES
            (%(symbol)s, %(entry_time)s, %(exit_time)s, %(entry_price)s,
             %(exit_price)s, %(position_size)s, %(risk_pct)s,
             %(R_multiple)s, %(fee)s, %(slippage)s, %(pnl)s,
             %(equity_after)s)
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, d)
    logger.debug("Trade logged: %s", d.get("symbol"))


def log_signal(d: dict) -> None:
    sql = """
        INSERT INTO signals
            (symbol, signal_time, adx, volume_ratio, breakout_level, regime_state)
        VALUES
            (%(symbol)s, %(signal_time)s, %(adx)s, %(volume_ratio)s,
             %(breakout_level)s, %(regime_state)s)
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, d)


def log_metrics(d: dict) -> None:
    sql = """
        INSERT INTO system_metrics
            (live_sharpe, drawdown, open_positions, total_equity)
        VALUES
            (%(live_sharpe)s, %(drawdown)s, %(open_positions)s, %(total_equity)s)
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, d)


def log_kill(reason: str, equity: float) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO kill_events (reason, equity) VALUES (%s, %s)",
                (reason, equity),
            )
    logger.critical("KILL EVENT logged: %s  equity=%.2f", reason, equity)


# ── Read helpers ──────────────────────────────────────────────

def fetch_closed_pnls(limit: int = 200) -> list[float]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pnl FROM trades ORDER BY exit_time DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
    return [float(r[0]) for r in rows]


def fetch_last_n_trades(n: int) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT symbol, R_multiple, slippage, pnl
                   FROM trades ORDER BY exit_time DESC LIMIT %s""",
                (n,),
            )
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
    return [dict(zip(cols, r)) for r in rows]


# ── Governance helpers ────────────────────────────────────────

def log_governance_event(event_type: str, old_state, new_state,
                         reason: str, metrics_snapshot: dict) -> None:
    sql = """
        INSERT INTO governance_events
            (event_type, old_state, new_state, reason, metrics_snapshot)
        VALUES (%s, %s, %s, %s, %s)
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (event_type, str(old_state), str(new_state),
                              reason, Json(metrics_snapshot)))
    logger.info("Governance event: %s → %s  (%s)", old_state, new_state, reason)


def get_current_governance_state() -> str | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT new_state FROM governance_events "
                "WHERE event_type='STATE_CHANGE' ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
    return row[0] if row else None


def save_governance_baseline(metrics: dict) -> None:
    sql = """
        INSERT INTO governance_events
            (event_type, old_state, new_state, reason, metrics_snapshot)
        VALUES (%s, %s, %s, %s, %s)
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, ("BASELINE", "NONE", "NONE",
                              "baseline set at pilot approval", Json(metrics)))
    logger.info("Governance baseline saved: sharpe=%.3f", metrics.get("sharpe", 0))


def get_governance_baseline() -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT metrics_snapshot FROM governance_events "
                "WHERE event_type='BASELINE' ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
    return row[0] if row else None


def get_trade_count() -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM trades")
            return int(cur.fetchone()[0])


if __name__ == "__main__":
    init_pool()
    create_tables()
    print("Tables verified / created successfully.")
