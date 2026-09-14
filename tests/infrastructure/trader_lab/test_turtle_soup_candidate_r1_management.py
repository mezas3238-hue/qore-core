from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import count
from uuid import UUID

import pytest

from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import (
    MarketBarOrigin,
    MarketObservationEvidenceReference,
    MarketObservationId,
    MarketOhlcField,
    MarketOhlcFieldValidity,
    MarketPrice,
    MarketPriceSide,
    MarketTimeframe,
    MarketTimeframeCode,
    QualifiedOhlcBarObservation,
)
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
from qore.infrastructure.trader_lab.turtle_soup_candidate_r1 import (
    TurtleSoupR1Config,
    TurtleSoupR1ManagementFamily,
    TurtleSoupR1Setup,
    TurtleSoupR1ValidationError,
    TurtleSoupR1Variant,
)
from qore.infrastructure.trader_lab.turtle_soup_candidate_r1_management import (
    TurtleSoupR1ExperimentalPolicyId,
    TurtleSoupR1ManagementDecision,
    TurtleSoupR1ManagementExitReason,
    frozen_policy_ids,
    policy_for,
    replay_experimental_management,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide

_IDS = count(5000)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID(int=11)),
    source_id=SourceId(UUID(int=12)),
    port_name=PortName("market-data.turtle-soup-management-test"),
)
_INSTRUMENT = Instrument("ES")
_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _field(value: str) -> MarketOhlcField:
    return MarketOhlcField(
        validity=MarketOhlcFieldValidity.VALID,
        price=MarketPrice(Decimal(value)),
    )


def _bar(
    index: int,
    *,
    o: str,
    h: str,
    lo: str,
    c: str,
) -> QualifiedOhlcBarObservation:
    opened_at = _BASE + timedelta(days=index)
    return QualifiedOhlcBarObservation(
        observation_id=MarketObservationId(UUID(int=next(_IDS))),
        instrument=_INSTRUMENT,
        source=_SOURCE,
        timeframe=MarketTimeframe(MarketTimeframeCode.D1),
        price_side=MarketPriceSide.BID,
        origin=MarketBarOrigin.NATIVE,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(days=1),
        open=_field(o),
        high=_field(h),
        low=_field(lo),
        close=_field(c),
        evidence_ref=MarketObservationEvidenceReference(UUID(int=next(_IDS))),
    )


def _setup(*, variant: TurtleSoupR1Variant) -> TurtleSoupR1Setup:
    management_family = (
        TurtleSoupR1ManagementFamily.CLASSIC_TRAILING_STOP_UNRESOLVED
        if variant is TurtleSoupR1Variant.CLASSIC
        else TurtleSoupR1ManagementFamily.PLUS_ONE_PARTIAL_2_TO_6_BARS_PLUS_TRAIL_UNRESOLVED
    )
    return TurtleSoupR1Setup(
        variant=variant,
        side=DemoTradingSetupSide.LONG,
        reference_price=Decimal("99"),
        reference_age=4 if variant is TurtleSoupR1Variant.CLASSIC else 3,
        entry_trigger_price=Decimal("100"),
        executable_entry_price=Decimal("100"),
        initial_stop_price=Decimal("98"),
        signal_opened_at=_BASE - timedelta(days=1),
        fill_at=_BASE,
        management_family=management_family,
        config_fingerprint=TurtleSoupR1Config(tick_size=Decimal("0.25")).fingerprint(),
    )


def test_grid_is_frozen_to_exactly_ten_policies() -> None:
    ids = frozen_policy_ids()
    assert len(ids) == 10
    assert len(set(ids)) == 10
    assert ids == tuple(TurtleSoupR1ExperimentalPolicyId)


def test_policy_fingerprints_are_deterministic_and_unique() -> None:
    fingerprints = tuple(policy_for(policy_id).fingerprint() for policy_id in frozen_policy_ids())
    assert len(set(fingerprints)) == len(fingerprints)
    assert all(len(value) == 64 for value in fingerprints)
    assert policy_for(TurtleSoupR1ExperimentalPolicyId.C_TRAIL1_H3).fingerprint() == (
        policy_for(TurtleSoupR1ExperimentalPolicyId.C_TRAIL1_H3).fingerprint()
    )


def test_variant_mismatch_is_rejected() -> None:
    setup = _setup(variant=TurtleSoupR1Variant.CLASSIC)
    policy = policy_for(TurtleSoupR1ExperimentalPolicyId.P_B2_F50_TRAIL1_H10)
    with pytest.raises(TurtleSoupR1ValidationError):
        replay_experimental_management(
            setup=setup,
            management_bars=(),
            policy=policy,
        )


def test_classic_one_bar_trail_ratcheting_then_stop() -> None:
    setup = _setup(variant=TurtleSoupR1Variant.CLASSIC)
    policy = policy_for(TurtleSoupR1ExperimentalPolicyId.C_TRAIL1_H6)
    bars = (
        _bar(1, o="100.5", h="103", lo="99", c="102"),
        _bar(2, o="102", h="104", lo="101", c="103"),
        _bar(3, o="100.5", h="101", lo="98", c="99"),
    )
    result = replay_experimental_management(setup=setup, management_bars=bars, policy=policy)
    assert result.decision is TurtleSoupR1ManagementDecision.CLOSED
    assert result.exit_reason is TurtleSoupR1ManagementExitReason.STOP
    assert result.final_exit_price == Decimal("100.5")
    assert result.final_stop_price == Decimal("101")
    assert result.gross_r == Decimal("0.25")


def test_classic_time_exit_closes_on_declared_horizon() -> None:
    setup = _setup(variant=TurtleSoupR1Variant.CLASSIC)
    policy = policy_for(TurtleSoupR1ExperimentalPolicyId.C_TRAIL2_H3)
    bars = (
        _bar(1, o="100.5", h="102", lo="99", c="101"),
        _bar(2, o="101", h="103", lo="99.5", c="102"),
        _bar(3, o="102", h="104", lo="100.5", c="103"),
    )
    result = replay_experimental_management(setup=setup, management_bars=bars, policy=policy)
    assert result.decision is TurtleSoupR1ManagementDecision.CLOSED
    assert result.exit_reason is TurtleSoupR1ManagementExitReason.TIME_EXIT
    assert result.final_exit_price == Decimal("103")
    assert result.gross_r == Decimal("1.5")


def test_stop_precedes_same_bar_time_exit() -> None:
    setup = _setup(variant=TurtleSoupR1Variant.CLASSIC)
    policy = policy_for(TurtleSoupR1ExperimentalPolicyId.C_TRAIL2_H3)
    bars = (
        _bar(1, o="100", h="102", lo="99", c="101"),
        _bar(2, o="101", h="103", lo="99.5", c="102"),
        _bar(3, o="101", h="105", lo="98.5", c="104"),
    )
    result = replay_experimental_management(setup=setup, management_bars=bars, policy=policy)
    assert result.exit_reason is TurtleSoupR1ManagementExitReason.STOP
    assert result.final_exit_price == Decimal("99")
    assert result.gross_r == Decimal("-0.5")


def test_gap_through_active_stop_fills_at_observed_open_under_qore_model() -> None:
    setup = _setup(variant=TurtleSoupR1Variant.CLASSIC)
    policy = policy_for(TurtleSoupR1ExperimentalPolicyId.C_TRAIL1_H6)
    bars = (
        _bar(1, o="100", h="103", lo="99", c="102"),
        _bar(2, o="98.5", h="99", lo="97", c="98"),
    )
    result = replay_experimental_management(setup=setup, management_bars=bars, policy=policy)
    assert result.exit_reason is TurtleSoupR1ManagementExitReason.STOP
    assert result.final_stop_price == Decimal("99")
    assert result.final_exit_price == Decimal("98.5")
    assert result.gross_r == Decimal("-0.75")


def test_plus_one_executes_fifty_percent_partial_only_when_profitable() -> None:
    setup = _setup(variant=TurtleSoupR1Variant.PLUS_ONE)
    policy = policy_for(TurtleSoupR1ExperimentalPolicyId.P_B2_F50_TRAIL1_H10)
    bars = (
        _bar(1, o="100", h="102", lo="99", c="101"),
        _bar(2, o="101", h="104", lo="100.5", c="103"),
        _bar(3, o="103", h="104", lo="100", c="101"),
    )
    result = replay_experimental_management(setup=setup, management_bars=bars, policy=policy)
    assert result.partial_executed is True
    assert result.partial_exit_price == Decimal("103")
    assert result.exit_reason is TurtleSoupR1ManagementExitReason.STOP
    assert result.final_exit_price == Decimal("100.5")
    assert result.gross_r == Decimal("0.875")


def test_plus_one_unprofitable_scheduled_partial_is_skipped_permanently() -> None:
    setup = _setup(variant=TurtleSoupR1Variant.PLUS_ONE)
    policy = policy_for(TurtleSoupR1ExperimentalPolicyId.P_B2_F50_TRAIL2_H10)
    bars = (
        _bar(1, o="100", h="101", lo="99", c="99.5"),
        _bar(2, o="99.5", h="100", lo="98.5", c="99"),
        _bar(3, o="99", h="102", lo="98.6", c="101"),
    )
    result = replay_experimental_management(setup=setup, management_bars=bars, policy=policy)
    assert result.partial_executed is False
    assert result.partial_exit_price is None
    assert result.decision is TurtleSoupR1ManagementDecision.CENSORED
    assert result.exit_reason is TurtleSoupR1ManagementExitReason.INSUFFICIENT_DATA


def test_insufficient_bars_are_censored_without_fabricated_pnl() -> None:
    setup = _setup(variant=TurtleSoupR1Variant.CLASSIC)
    policy = policy_for(TurtleSoupR1ExperimentalPolicyId.C_TRAIL1_H6)
    bars = (_bar(1, o="100", h="102", lo="99", c="101"),)
    result = replay_experimental_management(setup=setup, management_bars=bars, policy=policy)
    assert result.decision is TurtleSoupR1ManagementDecision.CENSORED
    assert result.exit_reason is TurtleSoupR1ManagementExitReason.INSUFFICIENT_DATA
    assert result.gross_r is None
    assert result.final_exit_price is None
