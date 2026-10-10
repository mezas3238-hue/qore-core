"""End-to-end fixture-based source-to-geometry waterfall contract.

These are synthetic ledgers for invariant tests, NOT market replay results.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    A1_TRACE_ID,
    IDENTITY,
    build_waterfall,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics import (
    IDENTITY as V50_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics import (
    V50GTrade,
)

BEGIN = datetime(2026, 1, 5, 9, tzinfo=UTC)


def _opp(symbol: str, index: int) -> V49Opportunity:
    return V49Opportunity(
        symbol=symbol, session="LONDON", operating_date="2026-01-05",
        h1_state_direction="BULLISH",
        h1_state_from=BEGIN.isoformat(),
        h1_state_until=(BEGIN + timedelta(hours=3)).isoformat(),
        h1_state_basis="FVG",
        m15_setup_confirmed_at=(BEGIN + timedelta(minutes=15)).isoformat(),
        m15_protected_swing_price="99",
        m1_trigger_confirmed_at=(
            BEGIN + timedelta(minutes=21 + 2 * index)
        ).isoformat(),
        m1_trigger_family=(
            "LIQUIDITY_SWEEP_CISD" if index % 2 == 0 else "FVG_RETRACE_CISD"
        ),
        decision_reference_price="100",
        structural_target_witness_price="102",
    )


def _trace(
    source: V49Opportunity, *, ready: bool, cognitive: bool
) -> dict[str, Any]:
    return {
        "identity": A1_TRACE_ID,
        "source_opportunity_id": source_id(source),
        "symbol": source.symbol,
        "session": source.session,
        "observed_at": source.m1_trigger_confirmed_at,
        "source_h1_from": source.h1_state_from,
        "source_m15_confirmed_at": source.m15_setup_confirmed_at,
        "source_m1_confirmed_at": source.m1_trigger_confirmed_at,
        "source_trigger_family": source.m1_trigger_family,
        "bridge_disposition": (
            "PASS_TO_COMPETITION" if cognitive else "ABSTAIN"
        ),
        "bridge_reasons": ("ALLOW" if cognitive else "ABSTAIN",),
        "geometry_decision": "READY" if ready else "WAIT_STOP_BREATHING",
        "geometry_reasons": ("GEOMETRY_READY" if ready else "STOP_TOO_NARROW",),
        "policy_geometry_only_eligible": ready,
        "policy_cognitive_geometry_eligible": cognitive and ready,
        "outcome_visible_to_cognition": False,
        "capital_authority_granted": False,
        "master_frame_evaluated": False,
        "global_world_model_evaluated": False,
        "nine_market_competition_evaluated": False,
        "readiness_verified": False,
        "experience_memory_scope": "PER_CANDIDATE_EMPTY_EXPERIENCE",
        "readiness_origin": "LEGACY_STATIC_WELL_SUPPORTED",
        "experience_observations": 0,
    }


def _trade(source: V49Opportunity, policy: str) -> V50GTrade:
    entry = datetime.fromisoformat(source.m1_trigger_confirmed_at)
    return V50GTrade(
        policy=policy, symbol=source.symbol, session=source.session,
        operating_date=source.operating_date, entry_at=entry.isoformat(),
        exit_at=(entry + timedelta(minutes=1)).isoformat(),
        entry_price="100", stop_price="99", target_price="102",
        planned_reward_r="2", realized_gross_r="2",
        exit_reason="TARGET", m1_bars_held=1,
        cognitive_disposition="PASS_TO_COMPETITION",
        geometry_decision="READY", trigger_family=source.m1_trigger_family,
        h1_basis=source.h1_state_basis,
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _fixture(root: Path) -> tuple[Path, Path]:
    capacity = root / "capacity"
    replay = root / "replay"
    for symbol in ("EURUSD", "AUDJPY"):
        source = [_opp(symbol, index) for index in range(3)]
        # Deliberately stagger the second market after first for global MAX3.
        if symbol == "AUDJPY":
            source = [
                replace(
                    item,
                    m1_trigger_confirmed_at=(
                        BEGIN + timedelta(minutes=31 + 2 * index)
                    ).isoformat(),
                )
                for index, item in enumerate(source)
            ]
        permits = (
            [(True, True), (True, True), (False, False)]
            if symbol == "EURUSD"
            else [(True, True), (True, False), (False, False)]
        )
        traces = [
            _trace(item, ready=ready, cognitive=cognitive)
            for item, (ready, cognitive) in zip(source, permits, strict=True)
        ]
        trades = [
            _trade(item, policy)
            for item, (ready, cognitive) in zip(source, permits, strict=True)
            for policy in (
                ("GEOMETRY_ONLY", "COGNITIVE_GEOMETRY") if ready and cognitive
                else ("GEOMETRY_ONLY",) if ready else ()
            )
        ]
        geometry = Counter(row["geometry_decision"] for row in traces)
        bridge = Counter(row["bridge_disposition"] for row in traces)
        report = {
            "identity": V50_IDENTITY,
            "symbol": symbol,
            "session": "LONDON",
            "source_opportunities": len(source),
            "geometry_decisions": sorted(geometry.items()),
            "cognitive_dispositions": sorted(bridge.items()),
            "geometry_ready": geometry["READY"],
            "missing_session_bars": 0,
            "policy_trade_rows_before_max3": {
                policy: sum(item.policy == policy for item in trades)
                for policy in ("GEOMETRY_ONLY", "COGNITIVE_GEOMETRY")
            },
            "cognitive_trace_rows": len(source),
        }
        _write_jsonl(
            capacity / symbol /
            f"capitalizer-{symbol.lower()}-v49-hf-capacity-opportunities.jsonl",
            [asdict(item) for item in source],
        )
        market = replay / symbol
        _write_jsonl(
            market / f"capitalizer-{symbol.lower()}-v50-g-trades.jsonl",
            [asdict(item) for item in trades],
        )
        _write_jsonl(market / "capitalizer-v50-g-cognitive-trace.jsonl", traces)
        (market / f"capitalizer-{symbol.lower()}-v50-g-report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )
    return capacity, replay


def test_full_trace_coverage_reconciles_two_markets_and_global_max3(
    tmp_path: Path,
) -> None:
    source_root, replay_root = _fixture(tmp_path)
    report, gates = build_waterfall(
        source_root, replay_root, expected_markets=2
    )
    assert report["identity"] == IDENTITY
    assert report["source_opportunities_total"] == 6
    assert report["a1_trace_rows"] == 6
    assert report["all_markets_trace_covered"] is True
    assert report["policy_rows_before_max3"] == {
        "GEOMETRY_ONLY": 4, "COGNITIVE_GEOMETRY": 3
    }
    assert report["policy_rows_after_max3"] == {
        "GEOMETRY_ONLY": 3, "COGNITIVE_GEOMETRY": 3
    }
    assert report["policy_rows_removed_max3"] == {
        "GEOMETRY_ONLY": 1, "COGNITIVE_GEOMETRY": 0
    }
    assert sum(row["geometry_not_ready"] for row in report["markets"]) == 2
    assert sum(
        row["cognitive_denied_among_geometry_ready"]
        for row in report["markets"]
    ) == 1
    assert len(gates) == 6
    assert not any(
        "h1_state_until" in asdict(row) or "realized_gross_r" in asdict(row)
        for row in gates
    )
    assert report["trader_certified"] is False


def test_missing_trace_fails_closed_and_report_only_is_explicit(
    tmp_path: Path,
) -> None:
    source_root, replay_root = _fixture(tmp_path)
    (replay_root / "AUDJPY" / "capitalizer-v50-g-cognitive-trace.jsonl").unlink()
    with pytest.raises(ValueError, match="A1 cognitive trace missing"):
        build_waterfall(source_root, replay_root, expected_markets=2)
    report, gates = build_waterfall(
        source_root, replay_root, expected_markets=2, require_traces=False
    )
    assert report["all_markets_trace_covered"] is False
    assert len(gates) == 3
    assert report["markets"][0]["cognitive_denied_among_geometry_ready"] is None


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("source_opportunity_id", "foreign", "source IDs"),
        ("master_frame_evaluated", True, "provenance"),
        ("outcome_visible_to_cognition", True, "provenance"),
        ("observed_at", "2026-01-05T09:20:00+00:00", "time mismatch"),
        ("policy_geometry_only_eligible", False, "eligibility"),
    ],
)
def test_bad_source_or_cognitive_evidence_is_rejected(
    tmp_path: Path, field: str, value: Any, message: str
) -> None:
    source_root, replay_root = _fixture(tmp_path)
    path = replay_root / "EURUSD" / "capitalizer-v50-g-cognitive-trace.jsonl"
    raw = [json.loads(line) for line in path.read_text().splitlines()]
    raw[0][field] = value
    _write_jsonl(path, raw)
    with pytest.raises(ValueError, match=message):
        build_waterfall(source_root, replay_root, expected_markets=2)


def test_bad_report_denominator_fails_closed(tmp_path: Path) -> None:
    source_root, replay_root = _fixture(tmp_path)
    path = replay_root / "EURUSD" / "capitalizer-eurusd-v50-g-report.json"
    raw = json.loads(path.read_text())
    raw["source_opportunities"] = 90
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="source opportunity count mismatch"):
        build_waterfall(source_root, replay_root, expected_markets=2)


def test_missing_ninth_market_is_not_a_full_certification(
    tmp_path: Path,
) -> None:
    source_root, replay_root = _fixture(tmp_path)
    with pytest.raises(ValueError, match="market coverage"):
        build_waterfall(source_root, replay_root)


def test_source_id_does_not_depend_on_future_expiry() -> None:
    item = _opp("EURUSD", 0)
    assert source_id(item) == source_id(
        replace(item, h1_state_until=(
            BEGIN + timedelta(hours=4)
        ).isoformat())
    )
