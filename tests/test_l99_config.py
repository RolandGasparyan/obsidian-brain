"""Tests for l99.config — unified configuration."""
from __future__ import annotations

import os

import pytest

from l99.config import CONFIG, EngineId, EnginePaths, GATE_VIP0, FeeTier


class TestConfig:
    def test_starting_equity_is_3k(self):
        assert CONFIG.starting_equity == 3000.0

    def test_engine_ids_match_doctrine(self):
        assert EngineId.GODMODE.value  == "godmode"
        assert EngineId.AEGIS.value    == "aegis_alpha"
        assert EngineId.PREDATOR.value == "quant_predator"

    def test_fee_tier_known(self):
        assert isinstance(CONFIG.fees, FeeTier)
        # Spot maker 0.10%, taker 0.15%
        assert CONFIG.fees.spot_maker_pct == pytest.approx(0.001)
        assert CONFIG.fees.spot_taker_pct == pytest.approx(0.0015)
        # Futures VIP 0 third-party estimate
        assert CONFIG.fees.futures_maker_pct == pytest.approx(0.0002)
        assert CONFIG.fees.futures_taker_pct == pytest.approx(0.0005)

    def test_allocation_matches_doctrine(self):
        """CHAMPION_MODE.md §2.2: stages 1→4 alloc shifts toward predator."""
        a1 = CONFIG.allocation(1)
        a4 = CONFIG.allocation(4)
        assert a1["godmode"]   == pytest.approx(0.40)
        assert a1["aegis_alpha"] == pytest.approx(0.40)
        assert a1["quant_predator"] == pytest.approx(0.20)
        assert a4["godmode"]   == pytest.approx(0.10)
        assert a4["aegis_alpha"] == pytest.approx(0.30)
        assert a4["quant_predator"] == pytest.approx(0.60)
        # All allocations sum to 1.0
        for stage in (1, 2, 3, 4):
            total = sum(CONFIG.allocation(stage).values())
            assert total == pytest.approx(1.0, abs=1e-9), \
                f"stage {stage} alloc sum {total} != 1.0"

    def test_allocation_clamps_invalid_stage(self):
        # stage 0 → treats as 1
        assert CONFIG.allocation(0) == CONFIG.allocation(1)
        # stage 99 → treats as 4
        assert CONFIG.allocation(99) == CONFIG.allocation(4)

    def test_engine_paths_creates_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("l99.config.DATA_ROOT", tmp_path)
        p = EnginePaths.for_engine(EngineId.AEGIS)
        assert p.journal.parent.exists()
        assert p.journal.parent.name == "aegis_alpha"

    def test_is_engine_enabled(self):
        assert CONFIG.is_engine_enabled(EngineId.GODMODE) == CONFIG.enable_godmode
        assert CONFIG.is_engine_enabled(EngineId.AEGIS) == CONFIG.enable_aegis
        assert CONFIG.is_engine_enabled(EngineId.PREDATOR) == CONFIG.enable_predator
