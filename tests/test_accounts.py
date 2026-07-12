"""Unit tests for the multi-account registry (accounts.py).

Pure env-var resolution — no network, no exchange connection, no orders.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from accounts import Account, load_account, load_all, configured_accounts, ACCOUNT_NAMES

# Every env var the registry might read — cleared before each test.
_ALL_VARS = (
    "GATE_MAIN_API_KEY", "GATE_MAIN_API_SECRET",
    "GATEIO_API_KEY", "GATEIO_SECRET",
    "GATE_API_KEY", "GATE_API_SECRET",
    "GATE_SUB1_API_KEY", "GATE_SUB1_API_SECRET",
    "GATE_SUB2_API_KEY", "GATE_SUB2_API_SECRET",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in _ALL_VARS:
        monkeypatch.delenv(var, raising=False)


def test_three_known_accounts():
    assert ACCOUNT_NAMES == ("main", "sub1", "sub2")


def test_unconfigured_when_env_empty():
    accts = load_all()
    assert set(accts) == {"main", "sub1", "sub2"}
    assert all(not a.configured for a in accts.values())
    assert configured_accounts() == {}


def test_unknown_account_rejected():
    with pytest.raises(ValueError):
        load_account("sub3")


def test_name_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("GATE_SUB1_API_KEY", "k")
    monkeypatch.setenv("GATE_SUB1_API_SECRET", "s")
    assert load_account("SUB1").configured


def test_configured_requires_both_key_and_secret(monkeypatch):
    monkeypatch.setenv("GATE_SUB1_API_KEY", "only-key")
    assert load_account("sub1").configured is False
    monkeypatch.setenv("GATE_SUB1_API_SECRET", "now-secret")
    assert load_account("sub1").configured is True


def test_subaccounts_are_independent(monkeypatch):
    monkeypatch.setenv("GATE_SUB1_API_KEY", "k1")
    monkeypatch.setenv("GATE_SUB1_API_SECRET", "s1")
    monkeypatch.setenv("GATE_SUB2_API_KEY", "k2")
    monkeypatch.setenv("GATE_SUB2_API_SECRET", "s2")
    conf = configured_accounts()
    assert set(conf) == {"sub1", "sub2"}
    assert conf["sub1"].api_key == "k1"
    assert conf["sub2"].api_key == "k2"


def test_main_dedicated_vars_win(monkeypatch):
    monkeypatch.setenv("GATE_MAIN_API_KEY", "dedicated")
    monkeypatch.setenv("GATE_MAIN_API_SECRET", "ds")
    monkeypatch.setenv("GATEIO_API_KEY", "legacy")
    monkeypatch.setenv("GATEIO_SECRET", "legacy-s")
    assert load_account("main").api_key == "dedicated"


def test_main_falls_back_to_legacy_gateio_vars(monkeypatch):
    monkeypatch.setenv("GATEIO_API_KEY", "legacy")
    monkeypatch.setenv("GATEIO_SECRET", "legacy-s")
    acct = load_account("main")
    assert acct.configured
    assert acct.api_key == "legacy"


def test_main_falls_back_to_gate_api_vars(monkeypatch):
    monkeypatch.setenv("GATE_API_KEY", "alt")
    monkeypatch.setenv("GATE_API_SECRET", "alt-s")
    assert load_account("main").api_key == "alt"


def test_masked_never_leaks_secret(monkeypatch):
    monkeypatch.setenv("GATE_SUB1_API_KEY", "abcd1234")
    monkeypatch.setenv("GATE_SUB1_API_SECRET", "supersecret")
    masked = load_account("sub1").masked()
    assert "supersecret" not in masked
    assert "1234" in masked


def test_account_is_frozen():
    acct = Account(name="main", api_key="k", api_secret="s")
    with pytest.raises(Exception):
        acct.api_key = "mutated"  # type: ignore[misc]
