"""
Tests for canary_executor._base_fee — base-asset fee parsing.

The BALANCE_NOT_ENOUGH retry loop observed on the live battle log was caused
by `buy()` recording the gross `filled` from ccxt's create_order response,
while Gate.io spot market-buys charge fees in the base asset. The recorded
state was therefore ~0.001 SOL / ~0.0000016 BTC above exchange-free on every
position, and every SELL fell into the actual-balance retry path.

The fix in `buy()` calls `_base_fee()` to subtract any base-currency fees
before recording. These tests verify that `_base_fee` parses both ccxt
response shapes correctly and returns 0.0 for any malformed or non-matching
input (the helper is on the BUY hot path — it must never raise).

Compatible with `pytest` (auto-discovered by the CI workflow) AND standalone
via `python3 canary/tests/test_fee_aware_buy.py`.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

try:
    import pytest  # noqa: F401
except ImportError:
    pytest = None

HERE = Path(__file__).resolve().parent
EXECUTOR = HERE.parent / "canary_executor.py"


def _import_executor():
    spec = importlib.util.spec_from_file_location("canary_executor", EXECUTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXECUTOR}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["canary_executor"] = mod
    spec.loader.exec_module(mod)
    return mod


# ── 'fee' (singular dict) shape ──────────────────────────────────────────

def test_fee_dict_matching_base_returns_cost(ex=None):
    ex = ex or _import_executor()
    order = {"fee": {"cost": 0.00110000, "currency": "SOL"}}
    assert ex._base_fee(order, "SOL") == 0.0011

def test_fee_dict_currency_mismatch_returns_zero(ex=None):
    ex = ex or _import_executor()
    # USDT-side fee on a SOL/USDT buy: not a base-asset fee, do NOT subtract.
    order = {"fee": {"cost": 0.09, "currency": "USDT"}}
    assert ex._base_fee(order, "SOL") == 0.0

def test_fee_dict_missing_cost_returns_zero(ex=None):
    ex = ex or _import_executor()
    order = {"fee": {"currency": "SOL"}}
    assert ex._base_fee(order, "SOL") == 0.0

def test_fee_dict_null_cost_returns_zero(ex=None):
    ex = ex or _import_executor()
    order = {"fee": {"cost": None, "currency": "SOL"}}
    assert ex._base_fee(order, "SOL") == 0.0


# ── 'fees' (list of dicts) shape ─────────────────────────────────────────

def test_fees_list_sums_only_base(ex=None):
    ex = ex or _import_executor()
    order = {"fees": [
        {"cost": 0.00050000, "currency": "SOL"},
        {"cost": 0.00040000, "currency": "SOL"},
        {"cost": 0.09000000, "currency": "USDT"},
    ]}
    assert ex._base_fee(order, "SOL") == 0.0009

def test_fees_list_no_base_matches_returns_zero(ex=None):
    ex = ex or _import_executor()
    order = {"fees": [{"cost": 0.09, "currency": "USDT"}]}
    assert ex._base_fee(order, "SOL") == 0.0


# ── absent / malformed input ─────────────────────────────────────────────

def test_no_fee_or_fees_keys_returns_zero(ex=None):
    ex = ex or _import_executor()
    assert ex._base_fee({"id": "1", "filled": 1.1, "average": 86.0}, "SOL") == 0.0

def test_fee_not_dict_returns_zero(ex=None):
    ex = ex or _import_executor()
    assert ex._base_fee({"fee": "garbage"}, "SOL") == 0.0
    assert ex._base_fee({"fee": None}, "SOL") == 0.0
    assert ex._base_fee({"fee": []}, "SOL") == 0.0

def test_fees_not_list_returns_zero(ex=None):
    ex = ex or _import_executor()
    assert ex._base_fee({"fees": "garbage"}, "SOL") == 0.0
    assert ex._base_fee({"fees": {"cost": 0.001, "currency": "SOL"}}, "SOL") == 0.0

def test_fees_list_with_non_dict_entries_ignored(ex=None):
    ex = ex or _import_executor()
    order = {"fees": [None, "garbage", 42, {"cost": 0.001, "currency": "SOL"}]}
    assert ex._base_fee(order, "SOL") == 0.001


# ── combined 'fee' + 'fees' shape (defensive) ────────────────────────────

def test_both_fee_and_fees_keys_both_counted(ex=None):
    """Some exchanges (or ccxt versions) may set both. Sum both to be safe."""
    ex = ex or _import_executor()
    order = {
        "fee":  {"cost": 0.0005, "currency": "SOL"},
        "fees": [{"cost": 0.0003, "currency": "SOL"}],
    }
    assert abs(ex._base_fee(order, "SOL") - 0.0008) < 1e-12


# ── realistic Gate.io SOL/USDT scenario ──────────────────────────────────

def test_realistic_gateio_sol_usdt_buy(ex=None):
    """Mirrors the actual battle.log incident from 2026-05-20 23:41 UTC:

        BUY  SOL/USDT $94.77 -> filled=1.10100000 @ $86.02
        SELL SOL/USDT insufficient (recorded=1.10100000)
        SELL SOL/USDT 1.10000000 (actual-balance retry)

    Exchange-truth gap: 1.10100000 - 1.10000000 = 0.00100000 SOL fee.
    Recording filled - fee_in_base would have eliminated the retry."""
    ex = ex or _import_executor()
    order = {
        "id": "1067167688246",
        "filled": 1.10100000,
        "average": 86.02,
        "fee": {"cost": 0.00100000, "currency": "SOL"},
    }
    assert abs(ex._base_fee(order, "SOL") - 0.001) < 1e-12
    net = float(order["filled"]) - ex._base_fee(order, "SOL")
    # Floor at the executor's 8-decimal precision: anything tighter than
    # that is meaningless on Gate.io spot.
    assert abs(net - 1.10000000) < 1e-8


# ── standalone runner ────────────────────────────────────────────────────

def _main():
    ex = _import_executor()
    tests = [
        ("fee dict matching base returns cost", test_fee_dict_matching_base_returns_cost),
        ("fee dict currency mismatch returns 0", test_fee_dict_currency_mismatch_returns_zero),
        ("fee dict missing cost returns 0", test_fee_dict_missing_cost_returns_zero),
        ("fee dict null cost returns 0", test_fee_dict_null_cost_returns_zero),
        ("fees list sums only base", test_fees_list_sums_only_base),
        ("fees list no base matches returns 0", test_fees_list_no_base_matches_returns_zero),
        ("no fee/fees keys returns 0", test_no_fee_or_fees_keys_returns_zero),
        ("fee not dict returns 0", test_fee_not_dict_returns_zero),
        ("fees not list returns 0", test_fees_not_list_returns_zero),
        ("fees list with non-dict entries ignored", test_fees_list_with_non_dict_entries_ignored),
        ("both fee + fees both counted", test_both_fee_and_fees_keys_both_counted),
        ("realistic gateio sol/usdt buy", test_realistic_gateio_sol_usdt_buy),
    ]
    passes = 0
    fails = 0
    for name, fn in tests:
        try:
            fn(ex=ex)
            print(f"  PASS  {name}")
            passes += 1
        except AssertionError as e:
            print(f"  FAIL  {name} — {e}")
            fails += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {name} — {type(e).__name__}: {e}")
            fails += 1
    print(f"\nRESULT: {passes}/{passes + fails} passed · {fails} failed")
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    _main()
