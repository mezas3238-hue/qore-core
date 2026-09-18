from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.cibo_market_atlas_journey_contract_v1 import (
    PROVIDER_INDEX_MAP,
    CrossIndexJourney,
    DepartureTiming,
    EvidenceRole,
    StructureTouch,
    StructureType,
    TargetCandidate,
    TargetOutcome,
    assert_no_outcome_leakage,
)

T0 = datetime(2026, 9, 16, 14, 0, tzinfo=UTC)
D = Decimal


def test_provider_index_mapping_is_explicit_and_canonical() -> None:
    assert PROVIDER_INDEX_MAP == {
        "NAS100": "USTEC",
        "SP500": "US500",
        "US30": "US30",
    }


def test_structure_touch_preserves_pre_departure_chronology() -> None:
    touch = StructureTouch(
        episode_id="episode-1",
        event_id="touch-1",
        symbol="NAS100",
        structure_type=StructureType.BREAKER_BLOCK,
        detector_version="ict.breaker.v1",
        source_timeframe="M15",
        created_at=T0,
        first_touch_at=T0 + timedelta(minutes=10),
        last_touch_at=T0 + timedelta(minutes=20),
        price_low=D("100"),
        price_high=D("110"),
        distance_from_source_ticks=D("50"),
        distance_from_opposite_ticks=D("150"),
        penetration_ticks=D("5"),
        dwell_minutes=10,
        revisit_count=1,
        last_before_departure=True,
    )
    assert touch.evidence_role is EvidenceRole.CAUSAL_FEATURE
    assert touch.last_before_departure is True


def test_structure_touch_rejects_future_first_touch() -> None:
    with pytest.raises(ValueError, match="structure chronology"):
        StructureTouch(
            episode_id="episode-1",
            event_id="touch-1",
            symbol="NAS100",
            structure_type=StructureType.UNRESOLVED_STRUCTURE,
            detector_version="unresolved.v1",
            source_timeframe="M5",
            created_at=T0 + timedelta(minutes=10),
            first_touch_at=T0,
            last_touch_at=T0 + timedelta(minutes=20),
            price_low=D("100"),
            price_high=D("110"),
            distance_from_source_ticks=D("1"),
            distance_from_opposite_ticks=D("2"),
            penetration_ticks=D("0"),
            dwell_minutes=0,
            revisit_count=0,
            last_before_departure=False,
        )


def test_departure_timing_captures_minutes_after_final_structure() -> None:
    timing = DepartureTiming(
        episode_id="episode-1",
        symbol="SP500",
        source_event_at=T0,
        final_structure_at=T0 + timedelta(minutes=15),
        departure_at=T0 + timedelta(minutes=35),
        structure_to_departure_minutes=20,
        source_to_departure_minutes=35,
        ny_minute_of_day=10 * 60 + 35,
        weekday=2,
    )
    assert timing.structure_to_departure_minutes == 20
    assert timing.evidence_role is EvidenceRole.CAUSAL_FEATURE


def test_target_candidate_is_causal_but_target_outcome_is_not() -> None:
    candidate = TargetCandidate(
        episode_id="episode-1",
        candidate_id="dol-1",
        objective_type="OPPOSITE_DAILY_LIQUIDITY",
        price=D("200"),
        distance_ticks=D("100"),
        detector_version="dol.v1",
    )
    outcome = TargetOutcome(
        episode_id="episode-1",
        candidate_id="dol-1",
        reached=True,
        reached_at=T0 + timedelta(hours=2),
        minutes_to_reach=120,
        extension_beyond_ticks=D("40"),
        path_drawdown_ticks=D("15"),
    )
    assert candidate.evidence_role is EvidenceRole.CAUSAL_FEATURE
    assert outcome.evidence_role is EvidenceRole.OUTCOME_ONLY


def test_outcome_evidence_fails_closed_in_causal_features() -> None:
    with pytest.raises(ValueError, match="OUTCOME_ONLY"):
        assert_no_outcome_leakage(
            (EvidenceRole.CAUSAL_FEATURE, EvidenceRole.OUTCOME_ONLY)
        )


def test_cross_index_journey_rejects_unknown_index_identity() -> None:
    with pytest.raises(ValueError, match="canonical frozen index"):
        CrossIndexJourney(
            episode_id="episode-1",
            observed_at=T0,
            nas100_state="EXPANSION",
            sp500_state="COMPRESSION",
            us30_state="COMPRESSION",
            lead_symbol="SPXUSD",
            lag_symbol="US30",
            lead_lag_minutes=10,
            agreement=False,
            divergence=True,
            evidence_role=EvidenceRole.OUTCOME_ONLY,
        )
