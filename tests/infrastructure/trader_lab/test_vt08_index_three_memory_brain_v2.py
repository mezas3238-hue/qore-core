from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from qore.infrastructure.cibo_executive_memory import CiboMemoryKind
from qore.infrastructure.trader_lab import vt08_index_three_memory_brain_v1 as v1
from qore.infrastructure.trader_lab import vt08_index_three_memory_brain_v2 as mod


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _full_market_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    root = tmp_path / "full-market"
    manifests: dict[str, Any] = {}
    for index, symbol in enumerate(v1.SYMBOLS):
        m5 = 100 + index
        events = 20 + index
        departures = 10 + index
        matrix_slice = {
            "by_side": {"long": {"events": 10}, "short": {"events": 10}},
            "by_session": {"new-york": {"events": 10}},
            "by_weekday": {"Monday": {"events": 5}},
            "by_prior_body_alignment": {"aligned": {"events": 7}},
            "by_fvg_presence": {
                "FVG_PRESENT": {"events": 8},
                "FVG_ABSENT": {"events": 12},
            },
        }
        dossier = {
            "identity": f"CIBO_{symbol}_MARKET_INTELLIGENCE_DOSSIER_V1",
            "package_identity": mod.FULL_MARKET_PACKAGE_IDENTITY,
            "symbol": symbol,
            "evidence_tier": "E1_ASSOCIATION_ONLY",
            "memory_role": "general-market-memory-independent-of-vt08-outcomes",
            "retained_m5_bars": m5,
            "behavior_events": events,
            "resolved_departures": departures,
            "market_matrix": matrix_slice,
            "journey": {"rows": events},
            "structure_touch": {"rows": events * 2},
            "departure_timing": {"rows": events},
            "pre_departure_sequences": {"rows": events},
            "daily_path": {"rows": 3},
            "target_destination_v1": {"rows": events},
            "target_destination_v2": {
                "summary": {
                    "candidate_rows": events * 2,
                    "complete_all_dol_claim": False,
                }
            },
            "cross_index": {
                "rows": 30,
                "causal_leader_claim": False,
                "evidence_tier": "E1_ASSOCIATION_ONLY",
            },
            "knowledge_gaps": [],
            "rule_promotion_allowed": False,
        }
        path = root / f"{symbol.lower()}-market-intelligence-dossier-v1.json"
        _write(path, dossier)
        digest = _sha(path)
        manifests[symbol] = {
            "identity": dossier["identity"],
            "symbol": symbol,
            "dossier_sha256": digest,
        }
        monkeypatch.setitem(mod.EXPECTED_DOSSIER_SHA256, symbol, digest)
        monkeypatch.setitem(
            mod.EXPECTED_MARKET,
            symbol,
            (m5, events, departures),
        )

    package = {
        "identity": mod.FULL_MARKET_PACKAGE_IDENTITY,
        "evidence_tier": "E1_ASSOCIATION_ONLY",
        "full_market_memory_ready": True,
        "vt08_outcomes_used": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_opened": False,
        "total_retained_m5_bars": sum(v[0] for v in mod.EXPECTED_MARKET.values()),
        "total_behavior_events": sum(v[1] for v in mod.EXPECTED_MARKET.values()),
        "total_resolved_departures": sum(v[2] for v in mod.EXPECTED_MARKET.values()),
        "market_manifests": manifests,
    }
    _write(root / "CIBO_INDEX_MARKET_INTELLIGENCE_PACKAGE_V1.json", package)
    return root


def _experience_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "experience"
    _write(
        root / "CIBO_MARKET_DOSSIER_MANIFEST.json",
        {
            "schema": v1.EXPERIENCE_SCHEMA,
            "market_episode_count": 2294,
            "cross_index_cohort_count": 1765,
            "markets": list(v1.SYMBOLS),
            "governance": {
                "fresh_holdout_opened": False,
                "specialists_frozen": False,
            },
        },
    )
    expected = {"NAS100": 761, "SP500": 747, "US30": 786}
    for symbol in v1.SYMBOLS:
        slice_payload = {"sample": 10}
        _write(
            root / f"{symbol}_MARKET_DOSSIER.json",
            {
                "schema": v1.EXPERIENCE_SCHEMA,
                "symbol": symbol,
                "overall": {"sample": expected[symbol]},
                "behavior_slices": {
                    "by_anchor": {"6": dict(slice_payload)},
                    "by_side": {"long": dict(slice_payload)},
                    "by_model": {"same-c2-intracandle": dict(slice_payload)},
                    "by_poi": {"fvg": dict(slice_payload)},
                    "by_weekday": {"Monday": dict(slice_payload)},
                    "by_prior_h4_range_regime": {"normal": dict(slice_payload)},
                },
            },
        )
    _write(
        root / "CROSS_INDEX_MARKET_DOSSIER.json",
        {
            "schema": v1.EXPERIENCE_SCHEMA,
            "cohort_count": 1765,
        },
    )
    return root


def test_full_market_memory_is_independent_of_vt08(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _full_market_fixture(tmp_path, monkeypatch)
    package, dossiers = mod.load_full_market_memory(root)
    assert package["vt08_outcomes_used"] is False
    assert package["full_market_memory_ready"] is True
    assert set(dossiers) == set(v1.SYMBOLS)
    assert dossiers["NAS100"]["memory_role"] == (
        "general-market-memory-independent-of-vt08-outcomes"
    )


def test_full_market_memory_fails_closed_on_vt08_contamination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _full_market_fixture(tmp_path, monkeypatch)
    package_path = root / "CIBO_INDEX_MARKET_INTELLIGENCE_PACKAGE_V1.json"
    package = json.loads(package_path.read_text())
    package["vt08_outcomes_used"] = True
    _write(package_path, package)
    with pytest.raises(ValueError, match="contaminated"):
        mod.load_full_market_memory(root)


def test_v2_store_separates_full_market_and_trader_experience(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full_root = _full_market_fixture(tmp_path, monkeypatch)
    experience_root = _experience_fixture(tmp_path)
    store, _sources = mod.build_memory_store(
        full_market_root=full_root,
        experience_root=experience_root,
    )
    items = store.retrieve()
    assert len(items) == 12
    kinds = [item.kind for item in items]
    assert kinds.count(CiboMemoryKind.SEMANTIC) == 1
    assert kinds.count(CiboMemoryKind.MARKET) == 4
    assert kinds.count(CiboMemoryKind.TRADER) == 4
    assert kinds.count(CiboMemoryKind.LONG_TERM_ARCHIVE) == 2
    assert kinds.count(CiboMemoryKind.RESEARCH) == 1

    by_subject = {item.subject_code: item for item in items}
    assert by_subject["nas100.market.full-cibo"].kind is CiboMemoryKind.MARKET
    assert by_subject["vt08.index.nas100.experience"].kind is CiboMemoryKind.TRADER
    assert "not-vt08-outcome-conditioned" in (
        by_subject["nas100.market.full-cibo"].limitations
    )


def test_v2_situation_model_reads_full_market_memory_before_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full_root = _full_market_fixture(tmp_path, monkeypatch)
    experience_root = _experience_fixture(tmp_path)
    store, _sources = mod.build_memory_store(
        full_market_root=full_root,
        experience_root=experience_root,
    )
    model = mod.build_situation_model(
        store,
        mod.Vt08IndexSituationInput(
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
    assert model.market_memory_status == "FULL_CIBO_INDEX_DOSSIER_V1_PRESENT"
    assert model.full_market_memory["symbol"] == "NAS100"
    assert len(model.market_dimensions) == 5
    assert len(model.experience_dimensions) == 6
    assert model.unknown_dimensions == ()
    assert model.decision_authority is False
    assert model.automatic_rule_promotion is False


def test_v2_manifest_keeps_all_authority_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full_root = _full_market_fixture(tmp_path, monkeypatch)
    experience_root = _experience_fixture(tmp_path)
    store, _sources = mod.build_memory_store(
        full_market_root=full_root,
        experience_root=experience_root,
    )
    manifest = mod.memory_store_manifest(store)
    assert manifest["full_cibo_market_memory"] is True
    assert manifest["reasoning_policy_selected"] is False
    assert manifest["target_depth_policy_selected"] is False
    assert manifest["contextual_trailing_policy_selected"] is False
    assert manifest["structural_rearm_policy_selected"] is False
    assert manifest["specialists_frozen"] is False
    assert manifest["fresh_holdout_opened"] is False
    assert manifest["live_authorized"] is False
    assert manifest["real_capital_authorized"] is False
