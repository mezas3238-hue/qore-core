from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_specialist import (
    V50GeometryDecision,
    V50GeometryProposal,
    V50StopMode,
)
from qore.infrastructure.trader_lab.capitalizer_v50_target_stop_intelligence import (
    V50H1TargetCandidate,
)
from qore.infrastructure.trader_lab.capitalizer_v54_structural_partial_runner import (
    _treatment_replay,
)


def _bar(minute: int, *, high: str, low: str, close: str = "100", open_price: str = "100") -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 5, 12, 0, tzinfo=UTC) + timedelta(minutes=minute)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=1,
        digits=2,
    )


def _opportunity() -> V49Opportunity:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    return V49Opportunity(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_direction="BULLISH",
        h1_state_from=(at - timedelta(hours=1)).isoformat(),
        h1_state_until=(at + timedelta(hours=2)).isoformat(),
        h1_state_basis="TEST",
        m15_setup_confirmed_at=(at - timedelta(minutes=10)).isoformat(),
        m15_protected_swing_price="95",
        m1_trigger_confirmed_at=at.isoformat(),
        m1_trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="100",
        structural_target_witness_price="102",
    )


def _target(rank: int, price: str) -> V50H1TargetCandidate:
    return V50H1TargetCandidate(
        candidate_id=f"T{rank}",
        price=Decimal(price),
        pivot_confirmed_at=datetime(2026, 1, 5, 11, rank, tzinfo=UTC),
        distance_price=Decimal(price) - Decimal("100"),
        room_r_vs_thesis_stop=Decimal("1"),
        rank=rank,
    )


def _geometry() -> V50GeometryProposal:
    return V50GeometryProposal(
        identity="QORE_CAPITALIZER_V50_COGNITIVE_GEOMETRY_SPECIALIST",
        decision=V50GeometryDecision.READY,
        side=CapitalizerSide.LONG,
        entry_price=Decimal("100"),
        stop_mode=V50StopMode.EXECUTION_M1,
        stop_price=Decimal("99"),
        stop_risk_price=Decimal("1"),
        stop_to_noise_ratio=Decimal("5"),
        t1=_target(1, "102"),
        t1_reward_r=Decimal("2"),
        runner=_target(2, "104"),
        runner_reward_r=Decimal("4"),
        reasons=("TEST",),
    )


def test_partial_runner_realizes_half_t1_plus_half_runner() -> None:
    trade = _treatment_replay(
        opportunity=_opportunity(),
        bars=(
            _bar(0, high="102.1", low="99.5", close="102"),
            _bar(1, high="104.1", low="100.1", close="104", open_price="102"),
        ),
        geometry=_geometry(),
    )
    assert trade is not None
    assert Decimal(trade.realized_gross_r) == Decimal("3")
    assert trade.exit_reason == "RUNNER_TARGET"


def test_runner_activates_after_t1_bar_and_caps_same_bar_touch_at_t1() -> None:
    trade = _treatment_replay(
        opportunity=_opportunity(),
        bars=(_bar(0, high="104.2", low="99.5", close="103"),),
        geometry=_geometry(),
    )
    assert trade is not None
    assert Decimal(trade.realized_gross_r) == Decimal("2")
    assert trade.exit_reason == "T1_RUNNER_SAME_BAR_CAPPED_AT_T1"
    assert trade.same_bar_t1_runner_ambiguity is True


def test_post_t1_same_bar_be_and_runner_resolves_be_first() -> None:
    trade = _treatment_replay(
        opportunity=_opportunity(),
        bars=(
            _bar(0, high="102.1", low="99.5", close="102"),
            _bar(1, high="104.1", low="99.9", close="103", open_price="102"),
        ),
        geometry=_geometry(),
    )
    assert trade is not None
    assert Decimal(trade.realized_gross_r) == Decimal("1")
    assert trade.exit_reason == "RUNNER_BE_FIRST_AMBIGUOUS"
    assert trade.same_bar_be_runner_ambiguity is True


def _geometry_without_runner() -> V50GeometryProposal:
    base = _geometry()
    return V50GeometryProposal(
        identity=base.identity,
        decision=base.decision,
        side=base.side,
        entry_price=base.entry_price,
        stop_mode=base.stop_mode,
        stop_price=base.stop_price,
        stop_risk_price=base.stop_risk_price,
        stop_to_noise_ratio=base.stop_to_noise_ratio,
        t1=base.t1,
        t1_reward_r=base.t1_reward_r,
        runner=None,
        runner_reward_r=None,
        reasons=("TEST_NO_RUNNER",),
    )


def test_no_runner_keeps_full_t1_exit_identical() -> None:
    trade = _treatment_replay(
        opportunity=_opportunity(),
        bars=(_bar(0, high="102.1", low="99.5", close="102"),),
        geometry=_geometry_without_runner(),
    )
    assert trade is not None
    assert Decimal(trade.realized_gross_r) == Decimal("2")
    assert trade.exit_reason == "T1_FULL_NO_RUNNER"


def test_pre_t1_stop_is_unchanged_full_minus_one_r() -> None:
    trade = _treatment_replay(
        opportunity=_opportunity(),
        bars=(_bar(0, high="101", low="98.9", close="99"),),
        geometry=_geometry(),
    )
    assert trade is not None
    assert Decimal(trade.realized_gross_r) == Decimal("-1")
    assert trade.exit_reason == "STOP"
