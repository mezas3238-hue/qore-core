from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_destination_evidence_binding_audit_2r_v1 as destination,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)
from qore.infrastructure.trader_lab.capitalizer_target_context import (
    CapitalizerTargetCandidate,
    CapitalizerTargetContext,
)


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _rebase_row(
    *,
    symbol: str,
    entry_at: str,
    closeback_at: str | None,
) -> dict[str, object]:
    observations: list[str] = []
    if closeback_at is not None:
        observations.append(f"M5_CLOSEBACK_AT:{closeback_at}")
    return {
        "symbol": symbol,
        "session": "ASIA",
        "operating_date": "2026-01-05",
        "side": "LONG",
        "entry_at": entry_at,
        "provenance": "CAUSAL_ARBITRATION_BASE",
        "microstructure_observations": observations,
    }


def _context(
    *,
    symbol: str,
    departure_at: str,
    known_at: str,
    structural_at: str,
) -> CapitalizerTargetContext:
    candidate = CapitalizerTargetCandidate(
        candidate_id="H1:PDH:1",
        family="PDH",
        timeframe="H1",
        price=Decimal("101"),
        distance_ticks=Decimal("20"),
        known_at=_dt(known_at),
        structural_opened_at=_dt(structural_at),
    )
    return CapitalizerTargetContext(
        symbol=symbol,
        side=CapitalizerSide.LONG,
        departure_at=_dt(departure_at),
        candidates=(candidate,),
    )


def test_destination_binding_respects_departure_and_structural_causality() -> None:
    rows = (
        _rebase_row(
            symbol="AUDJPY",
            entry_at="2026-01-05T00:20:00+00:00",
            closeback_at="2026-01-05T00:15:00+00:00",
        ),
        _rebase_row(
            symbol="GBPJPY",
            entry_at="2026-01-05T00:20:00+00:00",
            closeback_at=None,
        ),
        _rebase_row(
            symbol="USDJPY",
            entry_at="2026-01-05T00:20:00+00:00",
            closeback_at="2026-01-05T00:25:00+00:00",
        ),
        _rebase_row(
            symbol="AUDUSD",
            entry_at="2026-01-05T00:20:00+00:00",
            closeback_at="2026-01-05T00:15:00+00:00",
        ),
    )
    contexts = (
        _context(
            symbol="AUDJPY",
            departure_at="2026-01-05T00:15:00+00:00",
            known_at="2026-01-05T00:10:00+00:00",
            structural_at="2026-01-05T00:05:00+00:00",
        ),
        _context(
            symbol="USDJPY",
            departure_at="2026-01-05T00:25:00+00:00",
            known_at="2026-01-05T00:10:00+00:00",
            structural_at="2026-01-05T00:05:00+00:00",
        ),
        _context(
            symbol="AUDUSD",
            departure_at="2026-01-05T00:15:00+00:00",
            known_at="2026-01-05T00:10:00+00:00",
            structural_at="2026-01-05T00:16:00+00:00",
        ),
    )

    bound = destination._bind_rows(rows, contexts)

    first = bound[0]
    assert first.target_context_match_found is True
    assert first.target_context_causal is True
    assert first.destination_evidence_at_departure_bound is True
    assert first.active_candidate_count_at_departure == 1
    assert first.nearest_distance_ticks_at_departure == "20"
    assert first.candidate_families_at_departure == ("PDH",)
    assert first.candidate_timeframes_at_departure == ("H1",)
    assert first.post_departure_result_fields_used is False
    assert first.destination_intelligence_at_entry_supported is False

    missing = bound[1]
    assert missing.m5_closeback_at is None
    assert missing.target_context_match_found is False
    assert missing.destination_evidence_at_departure_bound is False

    future_departure = bound[2]
    assert future_departure.target_context_match_found is True
    assert future_departure.target_context_causal is False
    assert future_departure.destination_evidence_at_departure_bound is False

    future_structure = bound[3]
    assert future_structure.target_context_match_found is True
    assert future_structure.target_context_causal is False
    assert future_structure.destination_evidence_at_departure_bound is False
