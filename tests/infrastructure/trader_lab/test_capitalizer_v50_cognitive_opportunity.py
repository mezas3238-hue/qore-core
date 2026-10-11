from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_experience_memory import (
    CapitalizerExperienceMemory,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    V48AggregatedBar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_metacognition_v2 import (
    CapitalizerEpistemicReadiness,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_hf_bridge import (
    V50CognitiveDisposition,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_opportunity import (
    V50CognitiveOpportunitySnapshot,
    build_v50_cognitive_snapshot,
    refinement_path,
)


def _m1(minute: int, open_: str, high: str, low: str, close: str) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 5, 12, 0, tzinfo=UTC) + timedelta(minutes=minute)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=1,
        digits=2,
    )


def _h1(hour: int, high: str, low: str) -> V48AggregatedBar:
    opened = datetime(2026, 1, 5, hour, 0, tzinfo=UTC)
    return V48AggregatedBar(
        opened_at=opened,
        closed_at=opened + timedelta(hours=1),
        source=CapitalizerSourceBar(
            open=Decimal("100"),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal("100"),
        ),
        minute_count=60,
    )


def test_snapshot_is_outcome_blind_and_exposes_refinement_specialists() -> None:
    bars = (
        _m1(0, "100", "100.2", "99.8", "100.1"),
        _m1(1, "100.1", "100.2", "99.5", "99.7"),
        _m1(2, "99.7", "100.1", "99.7", "100.0"),
        _m1(3, "100.0", "100.4", "99.9", "100.3"),
        _m1(4, "100.3", "100.5", "100.1", "100.4"),
    )
    opportunity = V49Opportunity(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_direction="BULLISH",
        h1_state_from=bars[0].opened_at.isoformat(),
        h1_state_until=(bars[-1].closed_at + timedelta(hours=2)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL:BULLISH_FVG",
        m15_setup_confirmed_at=bars[0].opened_at.isoformat(),
        m15_protected_swing_price="98.0",
        m1_trigger_confirmed_at=bars[-1].closed_at.isoformat(),
        m1_trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="100.4",
        structural_target_witness_price="100.8",
    )
    h1 = (
        _h1(9, "101", "98"),
        _h1(10, "103", "99"),
        _h1(11, "102", "100"),
    )
    snapshot = build_v50_cognitive_snapshot(
        opportunity,
        m1_bars=bars,
        h1_bars=h1,
        experience_memory=CapitalizerExperienceMemory(),
        metacognitive_readiness=CapitalizerEpistemicReadiness.WELL_SUPPORTED,
    )
    assert snapshot.outcome_visible is False
    assert snapshot.executes_trade is False
    assert snapshot.grants_capital_authority is False
    assert snapshot.stop_refinement_available is True
    assert snapshot.target_refinement_available is True
    assert snapshot.cognitive.disposition in {
        V50CognitiveDisposition.REFINE_STOP_GEOMETRY,
        V50CognitiveDisposition.REFINE_TARGET_LADDER,
        V50CognitiveDisposition.PASS_TO_COMPETITION,
    }


def test_refinement_path_routes_geometry_to_specialists() -> None:
    bars = tuple(
        _m1(index, "100", "100.1", "99.9", "100")
        for index in range(15)
    )
    opportunity = V49Opportunity(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_direction="BULLISH",
        h1_state_from=bars[0].opened_at.isoformat(),
        h1_state_until=(bars[-1].closed_at + timedelta(hours=2)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL:BULLISH_FVG",
        m15_setup_confirmed_at=bars[10].opened_at.isoformat(),
        m15_protected_swing_price="99.95",
        m1_trigger_confirmed_at=bars[-1].closed_at.isoformat(),
        m1_trigger_family="LIQUIDITY_SWEEP_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
    )
    h1 = (
        _h1(9, "101", "98"),
        _h1(10, "103", "99"),
        _h1(11, "102", "100"),
    )
    snapshot = build_v50_cognitive_snapshot(
        opportunity,
        m1_bars=bars,
        h1_bars=h1,
        experience_memory=CapitalizerExperienceMemory(),
        metacognitive_readiness=CapitalizerEpistemicReadiness.WELL_SUPPORTED,
    )
    if snapshot.cognitive.disposition is V50CognitiveDisposition.REFINE_STOP_GEOMETRY:
        assert "MARKET_STOP_COGNITIVE_ENGINE" in refinement_path(snapshot)


def test_h1_terminal_future_is_not_visible_to_cognitive_snapshot() -> None:
    """V49's retrospectively known H1 end is never pre-entry knowledge."""
    bars = tuple(_m1(i, "100", "100.1", "99.9", "100") for i in range(15))
    decision = bars[-1].closed_at
    opportunity = V49Opportunity(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_direction="BULLISH",
        h1_state_from=bars[0].opened_at.isoformat(),
        h1_state_until=(decision + timedelta(hours=1)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL:BULLISH_FVG",
        m15_setup_confirmed_at=bars[10].opened_at.isoformat(),
        m15_protected_swing_price="99.95",
        m1_trigger_confirmed_at=decision.isoformat(),
        m1_trigger_family="LIQUIDITY_SWEEP_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
    )
    h1 = (_h1(9, "101", "98"), _h1(10, "103", "99"), _h1(11, "102", "100"))

    def snapshot_for(source: V49Opportunity) -> V50CognitiveOpportunitySnapshot:
        return build_v50_cognitive_snapshot(
            source,
            m1_bars=bars,
            h1_bars=h1,
            experience_memory=CapitalizerExperienceMemory(),
            metacognitive_readiness=CapitalizerEpistemicReadiness.WELL_SUPPORTED,
        )

    baseline = snapshot_for(opportunity)
    future_changed = snapshot_for(
        replace(opportunity, h1_state_until=(decision + timedelta(days=40)).isoformat())
    )
    assert opportunity.h1_state_until != decision.isoformat()  # V49 kept intact
    assert baseline.source_opportunity.h1_state_until == decision.isoformat()
    assert future_changed.source_opportunity.h1_state_until == decision.isoformat()
    assert baseline == future_changed  # no cognitive, geometry or outcome delta
