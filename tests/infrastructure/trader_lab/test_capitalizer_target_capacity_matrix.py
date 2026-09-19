from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_target_capacity_matrix import (
    build_target_capacity_matrix,
)


def _write_report(
    root: Path,
    *,
    session: CapitalizerSession,
    symbol: str,
) -> None:
    target = root / session.value.lower() / symbol.lower()
    target.mkdir(parents=True)
    payload = {
        "identity": "QORE_CAPITALIZER_TARGET_CAPACITY_FORENSICS_V1",
        "hypothesis_id": "QORE_CAPITALIZER_HYPOTHESIS_CIBO_DEPARTURE_ALIGNMENT_V1",
        "symbol": symbol,
        "session": session.value,
        "aligned_departure_events": 100,
        "target_context_events": 100,
        "geometry_observations": 99,
        "target_context_coverage": "1",
        "geometry_coverage": "0.99",
        "total": {
            "event": "ALL",
            "observations": 99,
            "median_active_candidate_count": "7",
            "median_capacity_r": "1.8",
            "p25_capacity_r": "0.9",
            "p75_capacity_r": "3.2",
        },
        "by_event": [],
        "evidence_status": "CONSUMED_RESEARCH_EVIDENCE",
        "geometry_kind": "DECISION_TIME_PROSPECTIVE_CAPACITY",
        "entry_fill_used": False,
        "diagnostic_stop_proxy": "SOURCE_M5_DIRECTIONAL_EXTREME",
        "final_stop_contract_defined": False,
        "minimum_r_filter_defined": False,
        "target_outcomes_used": False,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }
    path = target / f"capitalizer-{symbol.lower()}-target-capacity-v1.json"
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_target_capacity_matrix_requires_all_nine_markets_without_r_filter(
    tmp_path: Path,
) -> None:
    for session in CapitalizerSession:
        for symbol in allowed_markets(session):
            _write_report(tmp_path, session=session, symbol=symbol)

    matrix = build_target_capacity_matrix(tmp_path)
    assert matrix.market_count == 9
    assert matrix.complete_frozen_universe is True
    assert matrix.aligned_departure_events == 900
    assert matrix.geometry_observations == 891
    assert matrix.median_market_geometry_coverage == "0.99"
    assert matrix.median_market_capacity_r == "1.8"
    assert matrix.minimum_r_filter_defined is False
    assert matrix.final_stop_contract_defined is False
    assert matrix.target_outcomes_used is False
    assert matrix.economic_candidate is False
    assert matrix.rule_promotion_allowed is False
