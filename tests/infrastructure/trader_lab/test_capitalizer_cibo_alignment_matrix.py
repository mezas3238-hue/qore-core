from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_cibo_alignment_matrix import (
    build_departure_alignment_matrix,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_departure_hypothesis import (
    FROZEN_DEPARTURE_ALIGNMENT_HYPOTHESIS,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)


def _write_report(
    root: Path,
    *,
    session: CapitalizerSession,
    symbol: str,
) -> None:
    target = root / session.value.lower() / symbol.lower()
    target.mkdir(parents=True)
    aggregates: list[dict[str, object]] = []
    annual: list[dict[str, object]] = []
    for event in FROZEN_DEPARTURE_ALIGNMENT_HYPOTHESIS.capitalizer_event_family:
        for tag, rate, med in (
            ("NO_EXACT_CIBO_EVENT", "0.49", "-0.01"),
            ("DEPARTURE_ALIGNED_H1", "0.62", "0.20"),
            ("DEPARTURE_OPPOSED_H1", "0.31", "-0.40"),
        ):
            aggregates.append(
                {
                    "event": event,
                    "context_tag": tag,
                    "horizon_minutes": 15,
                    "observations": 100 if tag == "DEPARTURE_ALIGNED_H1" else 1000,
                    "positive_close_rate": rate,
                    "median_close_displacement_range_units": med,
                    "median_favorable_range_units": "0.60",
                    "median_adverse_range_units": "0.40",
                }
            )
        for year in (2024, 2025):
            annual.append(
                {
                    "event": event,
                    "context_tag": "DEPARTURE_ALIGNED_H1",
                    "horizon_minutes": 15,
                    "year": year,
                    "observations": 30,
                    "positive_close_rate": "0.60",
                    "median_close_displacement_range_units": "0.15",
                }
            )

    payload = {
        "identity": "QORE_CAPITALIZER_CIBO_ALIGNMENT_FORENSICS_V1",
        "symbol": symbol,
        "session": session.value,
        "aggregates": aggregates,
        "annual": annual,
        "total_labeled_responses": 1000,
        "evidence_status": "CONSUMED_RESEARCH_EVIDENCE",
        "context_fields_causal": True,
        "outcome_fields_causal": False,
        "lookback_tuning_used": False,
        "rule_promotion_allowed": False,
        "candidate_freeze_allowed": False,
    }
    path = target / f"capitalizer-{symbol.lower()}-cibo-alignment-v1.json"
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_frozen_departure_hypothesis_is_not_an_economic_candidate() -> None:
    hypothesis = FROZEN_DEPARTURE_ALIGNMENT_HYPOTHESIS
    assert hypothesis.cibo_detector == "CAUSAL_CISD_V1"
    assert hypothesis.cibo_source_timeframe == "H1"
    assert hypothesis.direction_relation == "ALIGNED"
    assert hypothesis.temporal_join == "DEPARTURE_AT_EQUALS_M5_DECISION_AT"
    assert hypothesis.lookback_tolerance_minutes == 0
    assert hypothesis.diagnostic_horizon_minutes == 15
    assert hypothesis.economic_candidate is False
    assert hypothesis.rule_promotion_allowed is False
    assert hypothesis.fresh_holdout_claimed is False


def test_alignment_matrix_requires_all_nine_frozen_markets(tmp_path: Path) -> None:
    for session in CapitalizerSession:
        for symbol in allowed_markets(session):
            _write_report(tmp_path, session=session, symbol=symbol)

    matrix = build_departure_alignment_matrix(tmp_path)
    assert matrix.market_count == 9
    assert matrix.event_cell_count == 36
    assert matrix.complete_frozen_universe is True
    assert matrix.aligned_market_event_cells_positive_median == 36
    assert matrix.aligned_market_event_cells == 36
    assert matrix.economic_candidate is False
    assert matrix.rule_promotion_allowed is False
    assert matrix.fresh_holdout_claimed is False
    assert matrix.median_aligned_positive_close_rate == "0.62"
    assert matrix.median_baseline_positive_close_rate == "0.49"
    assert all(item.annual_years_positive_median == 2 for item in matrix.cells)
