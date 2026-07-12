"""
Multi-account registry for Gate.io (main + sub-accounts).

Resolves named accounts to credentials pulled from environment variables.

SAFETY: this module is paper-safe by construction. Building an ``Account``
does NOT open an exchange connection, authenticate, or place any order — it
only reads strings from the environment. Wiring an account into a live
executor is a separate, deliberately gated step (see the live-trading rules
in CLAUDE.md). Nothing here bypasses ``CONFIRM LIVE TRADING``.

Accounts
--------
    main   the primary Gate.io account
    sub1   sub-account #1
    sub2   sub-account #2

Environment variables (per account, ``*_API_KEY`` / ``*_API_SECRET``):
    main   GATE_MAIN_API_KEY / GATE_MAIN_API_SECRET
           (falls back to the legacy single-account vars
            GATEIO_API_KEY/GATEIO_SECRET, then GATE_API_KEY/GATE_API_SECRET)
    sub1   GATE_SUB1_API_KEY / GATE_SUB1_API_SECRET
    sub2   GATE_SUB2_API_KEY / GATE_SUB2_API_SECRET
"""
from __future__ import annotations

import os
from dataclasses import dataclass

ACCOUNT_NAMES = ("main", "sub1", "sub2")

# Per-account env-var resolution order. Earlier names win. ``main`` keeps
# backward compatibility with the three legacy conventions already in the repo.
_KEY_VARS = {
    "main": ("GATE_MAIN_API_KEY", "GATEIO_API_KEY", "GATE_API_KEY"),
    "sub1": ("GATE_SUB1_API_KEY",),
    "sub2": ("GATE_SUB2_API_KEY",),
}
_SECRET_VARS = {
    "main": ("GATE_MAIN_API_SECRET", "GATEIO_SECRET", "GATE_API_SECRET"),
    "sub1": ("GATE_SUB1_API_SECRET",),
    "sub2": ("GATE_SUB2_API_SECRET",),
}


@dataclass(frozen=True)
class Account:
    """Resolved credentials for one named account. Holds no live connection."""

    name: str
    api_key: str
    api_secret: str

    @property
    def configured(self) -> bool:
        """True only when both key and secret are present."""
        return bool(self.api_key and self.api_secret)

    def masked(self) -> str:
        """Human-readable summary that never leaks the secret."""
        if not self.configured:
            return f"{self.name}: <not configured>"
        tail = self.api_key[-4:] if len(self.api_key) >= 4 else "????"
        return f"{self.name}: key=…{tail} secret=<set>"


def _first_env(var_names) -> str:
    for name in var_names:
        val = os.getenv(name, "")
        if val:
            return val
    return ""


def load_account(name: str) -> Account:
    """Resolve a single named account from the environment."""
    key = name.lower()
    if key not in ACCOUNT_NAMES:
        raise ValueError(
            f"unknown account {name!r}; expected one of {ACCOUNT_NAMES}"
        )
    return Account(
        name=key,
        api_key=_first_env(_KEY_VARS[key]),
        api_secret=_first_env(_SECRET_VARS[key]),
    )


def load_all() -> dict[str, Account]:
    """Resolve every known account (main + subs)."""
    return {name: load_account(name) for name in ACCOUNT_NAMES}


def configured_accounts() -> dict[str, Account]:
    """Only the accounts that have both a key and a secret set."""
    return {n: a for n, a in load_all().items() if a.configured}


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
    for acct in load_all().values():
        print(acct.masked())
