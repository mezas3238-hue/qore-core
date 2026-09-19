from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from qore.infrastructure.cibo_executive_memory import CiboMemoryKind
from qore.infrastructure.trader_lab.vt08_index_three_memory_brain_v1 import (
    EXPECTED_MARKET_EPISODES,
    EXPECTED_VT08_EPISODES,
    EXPERIENCE_SCHEMA,
    IDENTITY,
    JOURNEY_SUMMARY_IDENTITY,
    MARKET_MATRIX_IDENTITY,
    SYMBOLS,
    V7_RULE_FINGERPRINT,
    Vt08IndexSituationInput,
    _strategy_payload,
    build_memory_store,
    build_situation_model,
    load_market_memory,
    memory_store_manifest,
)


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _market_detail(symbol: str) -> dict[str, Any]:
    base = {
        "events": EXPECTED_MARKET_EPISODES[symbol],
        "evidence_tier": "E1_ASSOCIATION_ONLY",
        "cisd_rate": 0.4,
        "median_cisd_latency_minutes": 40.0,
        "median_mfe_240m_ticks": "100",
        "median_mae_240m_ticks": "80",
        "opposite_source_boundary_hit_24h_rate": 0.6,
    }
    return {
        "symbol": symbol,
        "asset_class": "index",
        "evidence_tier": "E1_ASSOCIATION_ONLY",
        "rule_promotion_allowed": False,
        "retained_m5_bars": 700000,
        "overall": dict(base),
        "by_side": {
            "long": dict(base),
            "short": dict(base),
        },
        "by_session": {
            "new-york": dict(base),
        },
        "by_weekday": {
            "Monday": dict(base),
        },
        "by_prior_body_alignment": {
            "aligned": dict(base),
        },
        "by_fvg_presence": {
            "FVG_PRESENT": dict(base),
            "FVG_ABSENT": dict(base),
        },
        "target_destination_v2": {
            "episodes": EXPECTED_MARKET_EPISODES[symbol],
            "complete_all_dol_claim": False,
        },
    }


def _build_roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    matrix_root = tmp_path / "matrix"
    journey_root = tmp_path / "journey"
    experience_root = tmp_path / "experience"

    matrix = {
        "identity": MARKET_MATRIX_IDENTITY,
        "evidence_tier": "E1_ASSOCIATION_ONLY",
        "rule_promotion_allowed": False,
        "market_detail": {
            symbol: _market_detail(symbol)
            for symbol in SYMBOLS
        },
    }
    matrix_manifest = {
        "identity": MARKET_MATRIX_IDENTITY,
        "highest_automatic_evidence_tier": "E1_ASSOCIATION_ONLY",
        "rule_promotion_allowed": False,
        "source_m5_run_id": 35166210458,
        "source_journey_run_id": 35175979474,
        "source_target_run_id": 35204892665,
    }
    journey = {
        "identity": JOURNEY_SUMMARY_IDENTITY,
        "source_run_id": 35175979474,
        "rule_promotion_allowed": False,
        "cross_index_evidence_tier": "E1_ASSOCIATION_ONLY",
        "cross_index": {
            "rows": 108558,
            "ordered_pairs": [],
        },
        "symbols": [
            {
                "symbol": symbol,
                "episodes": EXPECTED_MARKET_EPISODES[symbol],
                "structure_coverage": "DETERMINISTIC_SUPPORTED_SUBSET_FAIL_CLOSED",
            }
            for symbol in SYMBOLS
        ],
    }

    _write(matrix_root / "cibo-12-market-intelligence-matrix-v1.json", matrix)
    _write(
        matrix_root / "cibo-12-market-intelligence-matrix-v1-manifest.json",
        matrix_manifest,
    )
    _write(journey_root / "cibo-journey-10y-summary.json", journey)

    experience_manifest = {
        "schema": EXPERIENCE_SCHEMA,
        "market_episode_count": 2294,
        "cross_index_cohort_count": 1765,
        "markets": list(SYMBOLS),
        "governance": {
            "fresh_holdout_opened": False,
            "specialists_frozen": False,
        },
    }
    _write(
        experience_root / "CIBO_MARKET_DOSSIER_MANIFEST.json",
        experience_manifest,
    )
    for symbol in SYMBOLS:
        metrics = {
            "sample": EXPECTED_VT08_EPISODES[symbol],
            "mean_primary_r": "0",
            "stop_rate": "0.6",
            "stopped_then_later_2r_rate": "0.4",
        }
        slice_payload = {
            "sample": 10,
            "mean_primary_r": "0",
            "stop_rate": "0.5",
        }
        dossier = {
            "schema": EXPERIENCE_SCHEMA,
            "symbol": symbol,
            "overall": metrics,
            "behavior_slices": {
                "by_anchor": {"6": dict(slice_payload)},
                "by_side": {"long": dict(slice_payload)},
                "by_model": {"same-c2-intracandle": dict(slice_payload)},
                "by_poi": {"fvg": dict(slice_payload)},
                "by_weekday": {"Monday": dict(slice_payload)},
                "by_prior_h4_range_regime": {"normal": dict(slice_payload)},
            },
            "governance": {
                "specialist_not_frozen": True,
                "fresh_holdout_opened": False,
            },
        }
        _write(experience_root / f"{symbol}_MARKET_DOSSIER.json", dossier)

    cross = {
        "schema": EXPERIENCE_SCHEMA,
        "cohort_count": 1765,
        "side_agreement_rate": "0.97",
        "leader_counts": {},
        "governance": {
            "cross_index_gate_not_selected": True,
            "fresh_holdout_opened": False,
        },
    }
    _write(experience_root / "CROSS_INDEX_MARKET_DOSSIER.json", cross)
    return matrix_root, journey_root, experience_root


def test_strategy_memory_is_exact_frozen_v7_identity() -> None:
    strategy = _strategy_payload()
    assert strategy["rule_fingerprint"] == V7_RULE_FINGERPRINT
    assert strategy["candidate_id"] == "VT08_INDEX_V7_TTRADES_SOURCE_CORRECTED_001"
    assert strategy["cibo_may_modify_strategy_identity"] is False
    rules = strategy["rule_material"]
    assert isinstance(rules, dict)
    assert rules["execution"] == "first-causal-m15-continuation-closure"
    assert rules["stop"] == "protected-swing-extreme"


def test_three_memory_store_separates_strategy_market_and_experience(
    tmp_path: Path,
) -> None:
    matrix_root, journey_root, experience_root = _build_roots(tmp_path)
    store, _sources = build_memory_store(
        matrix_root=matrix_root,
        journey_summary_root=journey_root,
        experience_root=experience_root,
    )
    items = store.retrieve()
    assert len(items) == 13

    kinds = [item.kind for item in items]
    assert kinds.count(CiboMemoryKind.SEMANTIC) == 1
    assert kinds.count(CiboMemoryKind.MARKET) == 4
    assert kinds.count(CiboMemoryKind.TRADER) == 4
    assert kinds.count(CiboMemoryKind.LONG_TERM_ARCHIVE) == 3
    assert kinds.count(CiboMemoryKind.RESEARCH) == 1

    by_subject = {item.subject_code: item for item in items}
    assert "vt08.index.strategy.identity" in by_subject
    assert "nas100.market.general-10y" in by_subject
    assert "vt08.index.nas100.experience" in by_subject

    market_item = by_subject["nas100.market.general-10y"]
    trader_item = by_subject["vt08.index.nas100.experience"]
    assert market_item.kind is CiboMemoryKind.MARKET
    assert trader_item.kind is CiboMemoryKind.TRADER
    assert "not-vt08-outcome-conditioned" in market_item.limitations
    assert "vt08-specific" in trader_item.limitations


def test_situation_model_combines_memories_without_deciding(tmp_path: Path) -> None:
    matrix_root, journey_root, experience_root = _build_roots(tmp_path)
    store, _sources = build_memory_store(
        matrix_root=matrix_root,
        journey_summary_root=journey_root,
        experience_root=experience_root,
    )
    model = build_situation_model(
        store,
        Vt08IndexSituationInput(
            symbol="NAS100",
            side="long",
            anchor_hour_new_york=6,
            weekday_new_york="Monday",
            session="new-york",
            model_kind="same-c2-intracandle",
            poi_kind="fvg",
            prior_h4_range_regime="normal",
            prior_body_alignment="aligned",
            fvg_after_raid=True,
        ),
    )
    assert model.strategy_memory["rule_fingerprint"] == V7_RULE_FINGERPRINT
    assert model.market_memory["memory_role"] == (
        "general-market-memory-independent-of-vt08-outcomes"
    )
    assert len(model.market_dimensions) == 5
    assert len(model.experience_dimensions) == 6
    assert model.unknown_dimensions == ()
    assert model.decision_authority is False
    assert model.automatic_rule_promotion is False


def test_situation_model_preserves_unknown_dimensions(tmp_path: Path) -> None:
    matrix_root, journey_root, experience_root = _build_roots(tmp_path)
    store, _sources = build_memory_store(
        matrix_root=matrix_root,
        journey_summary_root=journey_root,
        experience_root=experience_root,
    )
    model = build_situation_model(
        store,
        Vt08IndexSituationInput(
            symbol="NAS100",
            side="long",
            anchor_hour_new_york=10,
            weekday_new_york="Tuesday",
            session="london",
            model_kind="unknown-model",
            poi_kind="unknown-poi",
            prior_h4_range_regime="unknown-regime",
        ),
    )
    assert "market.session" in model.unknown_dimensions
    assert "market.weekday" in model.unknown_dimensions
    assert "experience.anchor" in model.unknown_dimensions
    assert "experience.model" in model.unknown_dimensions
    assert "experience.poi" in model.unknown_dimensions
    assert model.decision_authority is False


def test_market_memory_rejects_rule_promotion(tmp_path: Path) -> None:
    matrix_root, journey_root, _experience_root = _build_roots(tmp_path)
    manifest_path = (
        matrix_root / "cibo-12-market-intelligence-matrix-v1-manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())
    manifest["rule_promotion_allowed"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="allows rule promotion"):
        load_market_memory(matrix_root, journey_root)


def test_memory_manifest_keeps_holdout_and_authority_closed(tmp_path: Path) -> None:
    matrix_root, journey_root, experience_root = _build_roots(tmp_path)
    store, _sources = build_memory_store(
        matrix_root=matrix_root,
        journey_summary_root=journey_root,
        experience_root=experience_root,
    )
    manifest = memory_store_manifest(store)
    assert manifest["identity"] == IDENTITY
    assert manifest["three_memory_architecture"] is True
    assert manifest["fresh_holdout_opened"] is False
    assert manifest["specialists_frozen"] is False
    assert manifest["reasoning_policy_selected"] is False
    assert manifest["live_authorized"] is False
    assert manifest["real_capital_authorized"] is False
