from __future__ import annotations

import json

from qore.infrastructure.trader_lab import cibo_xauusd_trader_memory_bridge_v1 as bridge


def _summary(hit: float, mfe: str, mae: str) -> dict[str, object]:
    return {
        "opposite_source_boundary_hit_24h_rate": hit,
        "median_mfe_240m_ticks": mfe,
        "median_mae_240m_ticks": mae,
    }


def test_dimension_vote_uses_non_pnl_market_association() -> None:
    overall = _summary(0.65, "300", "400")
    assert bridge._dimension_vote(_summary(0.70, "350", "400"), overall) == "SUPPORT"
    assert bridge._dimension_vote(_summary(0.50, "150", "400"), overall) == "CAUTION"
    assert bridge._dimension_vote(_summary(0.70, "150", "400"), overall) == "MIXED"


def test_build_memory_store_retains_archive_and_market_sections(tmp_path) -> None:
    overall = {
        **_summary(0.65, "300", "400"),
        "events": 111925,
        "evidence_tier": "E1_ASSOCIATION_ONLY",
    }
    grouped = {"H1": overall}
    dossier = {
        "identity": bridge.DOSSIER_IDENTITY,
        "symbol": "XAUUSD",
        "retained_m5_bars": 707716,
        "behavior_events": 111925,
        "overall": overall,
        "by_timeframe": grouped,
        "by_reference_type": {"prior-candle": overall},
        "by_side": {"long": overall},
        "by_session": {"london": overall},
        "by_weekday": {"Tuesday": overall},
        "by_year": {"2026": overall},
        "by_quarter": {"2026-Q3": overall},
        "by_prior_body_alignment": {"aligned": overall},
        "equal_liquidity_association": {"NOT_EXACT_EQUAL": overall},
        "fvg_after_raid_association": {"FVG_PRESENT": overall},
        "exact_c2": {"status": "synthetic"},
        "target_destination_v2": {"status": "synthetic"},
        "daily_path": {"status": "synthetic"},
        "pre_departure_sequences": {"status": "synthetic"},
        "hypothesis_status": {"synthetic": "E1_ASSOCIATION_ONLY"},
        "protected_swing_scope": "DISTANCE_DISTRIBUTIONS_ONLY_NO_TRADER_STOP_CONTRACT_YET",
        "stop_recovery_scope": "UNRESOLVED_UNTIL_TRADER_ENTRY_AND_STOP_CONTRACT_ARE_FROZEN",
        "regime_scope": "UNRESOLVED_NO_FROZEN_GENERIC_REGIME_THRESHOLD",
    }
    manifest = {
        "identity": bridge.DOSSIER_IDENTITY,
        "highest_automatic_evidence_tier": "E1_ASSOCIATION_ONLY",
        "rule_promotion_allowed": False,
    }
    (tmp_path / "xauusd-market-intelligence-dossier-v1.json").write_text(
        json.dumps(dossier)
    )
    (tmp_path / "xauusd-market-intelligence-manifest-v1.json").write_text(
        json.dumps(manifest)
    )
    store, loaded = bridge.build_memory_store(tmp_path)
    assert loaded["identity"] == bridge.DOSSIER_IDENTITY
    m = bridge.memory_store_manifest(store)
    assert m["governed_cibo_memory_store"] is True
    assert m["items"] >= 10
    assert "xauusd.market.overall" in m["subjects"]
