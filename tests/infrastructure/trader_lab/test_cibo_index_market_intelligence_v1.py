from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from qore.infrastructure.trader_lab import cibo_index_market_intelligence_v1 as mod


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _detail(symbol: str, events: int, m5: int) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "asset_class": "index",
        "evidence_tier": mod.EVIDENCE_TIER,
        "rule_promotion_allowed": False,
        "retained_m5_bars": m5,
        "overall": {"events": events},
        "by_timeframe": {},
        "by_side": {},
        "by_session": {},
        "by_weekday": {},
        "by_year": {},
        "by_quarter": {},
        "by_prior_body_alignment": {},
        "by_fvg_presence": {},
        "target_destination_v2": {},
    }


def _journey_root(root: Path, symbol: str, m5: int, events: int) -> Path:
    market_rows: list[dict[str, Any]] = [
        {
            "symbol": symbol,
            "identity": mod.JOURNEY_IDENTITY,
            "departure_at": "2024-01-02T15:30:00+00:00",
            "source_timeframe": "H1",
            "side": "long",
            "session_bucket": "new-york",
            "source_boundary_type": "PRIOR_HIGH_LOW",
        },
        {
            "symbol": symbol,
            "identity": mod.JOURNEY_IDENTITY,
            "departure_at": None,
            "source_timeframe": "H4",
            "side": "short",
            "session_bucket": "london",
            "source_boundary_type": "PRIOR_BODY",
        },
    ]
    structure_rows: list[dict[str, Any]] = [
        {
            "symbol": symbol,
            "structure_type": "PRIOR_HIGH_LOW",
            "reclaim_state": "RECLAIMED",
            "source_timeframe": "H1",
            "last_structure_before_departure": True,
            "dwell_minutes": 10,
            "penetration_depth_ticks": "4",
        }
    ]
    departure_rows: list[dict[str, Any]] = [
        {
            "symbol": symbol,
            "session_bucket": "new-york",
            "weekday": "Tuesday",
            "cisd_latency_minutes": 20,
            "reclaim_latency_minutes": 10,
            "minutes_source_event_to_departure": 15,
            "minutes_structure_creation_to_first_touch": 60,
        },
        {
            "symbol": symbol,
            "session_bucket": "london",
            "weekday": "Wednesday",
            "cisd_latency_minutes": None,
            "reclaim_latency_minutes": None,
            "minutes_source_event_to_departure": None,
            "minutes_structure_creation_to_first_touch": 120,
        },
    ]
    sequence_rows: list[dict[str, Any]] = [
        {
            "symbol": symbol,
            "sequence_status": "DETERMINISTIC_SUPPORTED_SUBSET",
            "sequence": [
                {"state": "LIQUIDITY_RAID"},
                {"state": "RECLAIM"},
                {"state": "DEPARTURE_CONFIRMATION"},
            ],
        },
        {
            "symbol": symbol,
            "sequence_status": "UNRESOLVED_STRUCTURE",
            "sequence": [{"state": "LIQUIDITY_RAID"}],
        },
    ]
    target_rows: list[dict[str, Any]] = [
        {
            "symbol": symbol,
            "candidate_type": "OPPOSITE_SOURCE_BOUNDARY",
            "first_objective_touched_24h": True,
            "time_to_first_objective_minutes": 30,
            "mfe_24h_ticks": "20",
            "mae_24h_ticks": "10",
            "candidate_distance_ticks": "8",
        },
        {
            "symbol": symbol,
            "candidate_type": "PRIOR_CANDLE_BOUNDARY",
            "first_objective_touched_24h": False,
            "time_to_first_objective_minutes": None,
            "mfe_24h_ticks": "5",
            "mae_24h_ticks": "15",
            "candidate_distance_ticks": "12",
        },
    ]
    daily_rows: list[dict[str, Any]] = [
        {
            "symbol": symbol,
            "weekday": "Tuesday",
            "regime_state": "UNRESOLVED_STRUCTURE",
            "path_efficiency": "0.4",
            "overlap_fraction": "0.5",
            "total_range": "100",
            "directional_displacement": "40",
            "close_location": "0.7",
        }
    ]
    ledgers: dict[str, tuple[str, list[dict[str, Any]]]] = {
        "MARKET_JOURNEY_LEDGER": (
            "MARKET_JOURNEY_LEDGER.jsonl",
            market_rows,
        ),
        "STRUCTURE_TOUCH_LEDGER": (
            "STRUCTURE_TOUCH_LEDGER.jsonl",
            structure_rows,
        ),
        "DEPARTURE_TIMING_LEDGER": (
            "DEPARTURE_TIMING_LEDGER.jsonl",
            departure_rows,
        ),
        "PRE_DEPARTURE_SEQUENCE_LEDGER": (
            "PRE_DEPARTURE_SEQUENCE_LEDGER.jsonl",
            sequence_rows,
        ),
        "TARGET_DESTINATION_LEDGER": (
            "TARGET_DESTINATION_LEDGER.jsonl",
            target_rows,
        ),
        "DAILY_PATH_LEDGER": (
            "DAILY_PATH_LEDGER.jsonl",
            daily_rows,
        ),
        "TRADER_MARKET_SYNC_LEDGER": (
            "TRADER_MARKET_SYNC_LEDGER.jsonl",
            list[dict[str, Any]](),
        ),
    }
    hashes: dict[str, str] = {}
    counts: dict[str, int] = {}
    for key, (name, rows) in ledgers.items():
        hashes[key] = _write_jsonl(root / name, rows)
        counts[key] = len(rows)

    manifest = {
        "identity": mod.JOURNEY_IDENTITY,
        "symbol": symbol,
        "source_run_id": mod.SOURCE_M5_RUN_ID,
        "source_git_sha": mod.SOURCE_M5_GIT_SHA,
        "retained_m5_bars": m5,
        "behavior_event_count": events,
        "ledger_counts": counts,
        "ledger_sha256": hashes,
        "structure_coverage": "DETERMINISTIC_SUPPORTED_SUBSET_FAIL_CLOSED",
        "trader_sync_status": "UNLINKED_NO_TRADER_DECISION_STREAM",
    }
    _write(root / "journey-manifest.json", manifest)
    return root


def _target_root(root: Path, symbol: str, m5: int, events: int) -> Path:
    ledger = [
        {
            "symbol": symbol,
            "candidate_type": "SOURCE_OPPOSITE_BOUNDARY",
            "source_timeframe": "H1",
            "active_untouched_at_departure": True,
            "touch_within_24h": True,
            "touch_order_ambiguous_within_m5": False,
            "candidate_distance_ticks": "8",
            "time_to_touch_minutes": 30,
        }
    ]
    episodes = [
        {
            "symbol": symbol,
            "active_candidate_count": 1,
            "touched_candidate_count_24h": 1,
            "first_touch_tied": False,
        }
    ]
    ledger_hash = _write_jsonl(root / "TARGET_DESTINATION_LEDGER_V2.jsonl", ledger)
    episode_hash = _write_jsonl(
        root / "TARGET_DESTINATION_EPISODE_V2.jsonl",
        episodes,
    )
    manifest = {
        "identity": mod.TARGET_IDENTITY,
        "symbol": symbol,
        "source_journey_run_id": mod.SOURCE_JOURNEY_RUN_ID,
        "source_journey_git_sha": mod.SOURCE_JOURNEY_GIT_SHA,
        "source_m5_run_id": mod.SOURCE_M5_RUN_ID,
        "retained_m5_bars": m5,
        "market_journey_rows": events,
        "resolved_departures": 1,
        "complete_all_dol_claim": False,
        "rule_promotion_allowed": False,
        "target_ledger_sha256": ledger_hash,
        "episode_ledger_sha256": episode_hash,
    }
    _write(root / "target-destination-v2-manifest.json", manifest)
    return root


def _sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, dict[str, Path], dict[str, Path]]:
    matrix_root = tmp_path / "matrix"
    summary_root = tmp_path / "summary"
    details: dict[str, Any] = {}
    journey_roots: dict[str, Path] = {}
    target_roots: dict[str, Path] = {}
    for index, symbol in enumerate(mod.SYMBOLS):
        m5 = 10 + index
        events = 2
        expected = dict(mod.EXPECTED[symbol])
        expected.update({"m5": m5, "events": events, "resolved_departures": 1})
        monkeypatch.setitem(mod.EXPECTED, symbol, expected)
        details[symbol] = _detail(symbol, events, m5)
        journey_roots[symbol] = _journey_root(
            tmp_path / f"journey-{symbol}",
            symbol,
            m5,
            events,
        )
        target_roots[symbol] = _target_root(
            tmp_path / f"target-{symbol}",
            symbol,
            m5,
            events,
        )

    matrix = {
        "identity": mod.MATRIX_IDENTITY,
        "evidence_tier": mod.EVIDENCE_TIER,
        "rule_promotion_allowed": False,
        "source_m5_run_id": mod.SOURCE_M5_RUN_ID,
        "source_journey_run_id": mod.SOURCE_JOURNEY_RUN_ID,
        "source_target_run_id": mod.SOURCE_TARGET_RUN_ID,
        "market_detail": details,
    }
    matrix_manifest = {
        "identity": mod.MATRIX_IDENTITY,
        "highest_automatic_evidence_tier": mod.EVIDENCE_TIER,
        "rule_promotion_allowed": False,
        "json_sha256": "fixture",
    }
    summary = {
        "identity": mod.JOURNEY_SUMMARY_IDENTITY,
        "source_run_id": mod.SOURCE_JOURNEY_RUN_ID,
        "cross_index_evidence_tier": mod.EVIDENCE_TIER,
        "rule_promotion_allowed": False,
        "cross_index": {
            "rows": 3,
            "ordered_pairs": [
                {
                    "source": "NAS100",
                    "peer": "SP500",
                    "evidence_tier": mod.EVIDENCE_TIER,
                },
                {
                    "source": "SP500",
                    "peer": "US30",
                    "evidence_tier": mod.EVIDENCE_TIER,
                },
            ],
        },
    }
    _write(matrix_root / "cibo-12-market-intelligence-matrix-v1.json", matrix)
    _write(
        matrix_root / "cibo-12-market-intelligence-matrix-v1-manifest.json",
        matrix_manifest,
    )
    _write(summary_root / "cibo-journey-10y-summary.json", summary)
    return matrix_root, summary_root, journey_roots, target_roots


def test_build_full_index_market_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matrix_root, summary_root, journey_roots, target_roots = _sources(
        tmp_path,
        monkeypatch,
    )
    output = tmp_path / "out"
    package = mod.build_package(
        matrix_root=matrix_root,
        journey_summary_root=summary_root,
        journey_roots=journey_roots,
        target_roots=target_roots,
        output=output,
    )
    assert package["identity"] == mod.PACKAGE_IDENTITY
    assert package["full_market_memory_ready"] is True
    assert package["vt08_outcomes_used"] is False
    assert package["rule_promotion_allowed"] is False
    assert package["fresh_holdout_opened"] is False
    assert package["total_behavior_events"] == 6

    dossier = json.loads(
        (output / "nas100-market-intelligence-dossier-v1.json").read_text()
    )
    assert dossier["memory_role"] == (
        "general-market-memory-independent-of-vt08-outcomes"
    )
    assert dossier["journey"]["rows"] == 2
    assert dossier["journey"]["resolved_departures"] == 1
    assert dossier["structure_touch"]["rows"] == 1
    assert dossier["pre_departure_sequences"]["rows"] == 2
    assert dossier["daily_path"]["rows"] == 1
    assert dossier["target_destination_v1"]["first_objective_touch_rate_24h"] == "0.5"
    assert dossier["target_destination_v2"]["summary"]["complete_all_dol_claim"] is False
    assert dossier["cross_index"]["causal_leader_claim"] is False


def test_journey_digest_drift_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matrix_root, summary_root, journey_roots, _target_roots = _sources(
        tmp_path,
        monkeypatch,
    )
    _ = matrix_root, summary_root
    path = journey_roots["NAS100"] / "MARKET_JOURNEY_LEDGER.jsonl"
    path.write_text(path.read_text() + "{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ledger digest drift"):
        mod._validate_journey(journey_roots["NAS100"], symbol="NAS100")


def test_target_complete_dol_claim_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _matrix_root, _summary_root, _journey_roots, target_roots = _sources(
        tmp_path,
        monkeypatch,
    )
    manifest_path = target_roots["SP500"] / "target-destination-v2-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["complete_all_dol_claim"] = True
    _write(manifest_path, manifest)
    with pytest.raises(ValueError, match="complete DOL universe"):
        mod._validate_target(target_roots["SP500"], symbol="SP500")


def test_matrix_rule_promotion_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matrix_root, summary_root, _journey_roots, _target_roots = _sources(
        tmp_path,
        monkeypatch,
    )
    path = matrix_root / "cibo-12-market-intelligence-matrix-v1.json"
    payload = json.loads(path.read_text())
    payload["rule_promotion_allowed"] = True
    _write(path, payload)
    with pytest.raises(ValueError, match="allows rule promotion"):
        mod._validate_matrix(matrix_root, summary_root)


def test_quantiles_are_deterministic() -> None:
    result = mod._quantiles(
        [mod._decimal("1"), mod._decimal("2"), mod._decimal("3"), mod._decimal("4")]
    )
    assert result["n"] == 4
    assert result["median"] == "2.5"
    assert result["p25"] == "2"
    assert result["p75"] == "3"
