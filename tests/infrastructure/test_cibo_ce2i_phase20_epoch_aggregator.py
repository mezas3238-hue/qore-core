from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_phase20_epoch_aggregator import (
    Phase20DecisionEpochAggregator,
    Phase20DecisionEpochSlot,
    build_phase20_decision_epoch_id,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_epoch import (
    Phase20ForwardObservedOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardPopulationDisposition,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)

OPENED_AT = datetime(2026, 9, 27, 16, 0, tzinfo=UTC)
DEADLINE_AT = OPENED_AT + timedelta(seconds=2)


def _slot(
    trader_id: TraderLineage,
    symbol: str,
) -> Phase20DecisionEpochSlot:
    return Phase20DecisionEpochSlot(
        slot_id=f"{trader_id.value}|{symbol}",
        trader_id=trader_id,
        qore_symbol=symbol,
    )


def _observed(
    trader_id: TraderLineage,
    symbol: str,
    fingerprint: str,
) -> Phase20ForwardObservedOpportunity:
    opportunity = TraderOpportunityEnvelope(
        trader_id=trader_id,
        signal_fingerprint=fingerprint,
        qore_symbol=symbol,
        provider_symbol=symbol,
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("10"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
    )
    provider = ProviderEconomicObservation(
        provider_key="ctrader",
        qore_symbol=symbol,
        provider_symbol=symbol,
        bid=Decimal("100"),
        ask=Decimal("100"),
        contract_size=Decimal("1"),
        tick_size=Decimal("0.1"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
        volume_step=Decimal("1"),
        margin_per_volume=Decimal("10"),
        commission_per_volume_usd=Decimal("0"),
        slippage_reserve_per_volume_usd=Decimal("0"),
        observed_at=OPENED_AT + timedelta(milliseconds=100),
    )
    return Phase20ForwardObservedOpportunity(
        provider_evidence_id=f"provider:{fingerprint}",
        opportunity=opportunity,
        provider_observation=provider,
        concentration_group=symbol,
        concentration_risk_usd=Decimal("10"),
    )


def _aggregator() -> Phase20DecisionEpochAggregator:
    return Phase20DecisionEpochAggregator(
        epoch_scope="ctrader:demo-forward:m5-boundary",
        opened_at=OPENED_AT,
        deadline_at=DEADLINE_AT,
        expected_slots=(
            _slot(TraderLineage.VT31_NAS100, "NAS100"),
            _slot(TraderLineage.R43_GBPUSD, "GBPUSD"),
            _slot(TraderLineage.R34_XAUUSD, "XAUUSD"),
        ),
    )


def test_epoch_id_is_declared_before_results_and_order_invariant() -> None:
    slots = (
        _slot(TraderLineage.VT31_NAS100, "NAS100"),
        _slot(TraderLineage.R43_GBPUSD, "GBPUSD"),
    )
    left = build_phase20_decision_epoch_id(
        epoch_scope="scope",
        opened_at=OPENED_AT,
        expected_slots=slots,
    )
    right = build_phase20_decision_epoch_id(
        epoch_scope="scope",
        opened_at=OPENED_AT,
        expected_slots=tuple(reversed(slots)),
    )

    assert left == right
    assert left.startswith("phase20d-epoch:")


def test_epoch_seals_complete_candidate_and_abstain_population() -> None:
    aggregator = _aggregator()
    aggregator.record_candidate(
        slot_id="VT31_NAS100|NAS100",
        opportunity=_observed(
            TraderLineage.VT31_NAS100,
            "NAS100",
            "vt31-epoch-signal",
        ),
        observed_at=OPENED_AT + timedelta(milliseconds=200),
    )
    aggregator.record_non_candidate(
        slot_id="R43_GBPUSD|GBPUSD",
        disposition=Phase20ForwardPopulationDisposition.ABSTAIN,
        observed_at=OPENED_AT + timedelta(milliseconds=250),
        reason="NO_SETUP",
    )
    aggregator.record_non_candidate(
        slot_id="R34_XAUUSD|XAUUSD",
        disposition=Phase20ForwardPopulationDisposition.SESSION_CLOSED,
        observed_at=OPENED_AT + timedelta(milliseconds=300),
        reason="SESSION_CLOSED",
    )

    batch = aggregator.seal(
        decision_at=OPENED_AT + timedelta(milliseconds=350)
    )

    assert len(batch.population_slots) == 3
    assert len(batch.opportunities) == 1
    by_slot = {item.slot_id: item for item in batch.population_slots}
    assert (
        by_slot["VT31_NAS100|NAS100"].disposition
        is Phase20ForwardPopulationDisposition.CANDIDATE
    )
    assert (
        by_slot["R43_GBPUSD|GBPUSD"].disposition
        is Phase20ForwardPopulationDisposition.ABSTAIN
    )
    assert (
        by_slot["R34_XAUUSD|XAUUSD"].disposition
        is Phase20ForwardPopulationDisposition.SESSION_CLOSED
    )


def test_epoch_cannot_seal_early_with_unobserved_slots() -> None:
    aggregator = _aggregator()
    aggregator.record_non_candidate(
        slot_id="R43_GBPUSD|GBPUSD",
        disposition=Phase20ForwardPopulationDisposition.ABSTAIN,
        observed_at=OPENED_AT + timedelta(milliseconds=100),
        reason="NO_SETUP",
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot seal before all slots terminalize",
    ):
        aggregator.seal(
            decision_at=OPENED_AT + timedelta(milliseconds=500)
        )


def test_epoch_deadline_materializes_missing_slots_fail_closed() -> None:
    aggregator = _aggregator()
    aggregator.record_candidate(
        slot_id="VT31_NAS100|NAS100",
        opportunity=_observed(
            TraderLineage.VT31_NAS100,
            "NAS100",
            "vt31-deadline-signal",
        ),
        observed_at=OPENED_AT + timedelta(milliseconds=200),
    )

    batch = aggregator.seal(decision_at=DEADLINE_AT)

    deadline_rows = tuple(
        item
        for item in batch.population_slots
        if (
            item.disposition
            is Phase20ForwardPopulationDisposition.DEADLINE_MISSED
        )
    )
    assert len(deadline_rows) == 2
    assert all(item.observed_at == DEADLINE_AT for item in deadline_rows)
    assert len(batch.opportunities) == 1


def test_epoch_rejects_conflicting_double_terminalization() -> None:
    aggregator = _aggregator()
    aggregator.record_non_candidate(
        slot_id="R43_GBPUSD|GBPUSD",
        disposition=Phase20ForwardPopulationDisposition.ABSTAIN,
        observed_at=OPENED_AT + timedelta(milliseconds=100),
        reason="NO_SETUP",
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="already terminalized differently",
    ):
        aggregator.record_non_candidate(
            slot_id="R43_GBPUSD|GBPUSD",
            disposition=Phase20ForwardPopulationDisposition.FAIL_CLOSED,
            observed_at=OPENED_AT + timedelta(milliseconds=120),
            reason="DATA_UNAVAILABLE",
        )


def test_epoch_rejects_candidate_for_wrong_declared_slot() -> None:
    aggregator = _aggregator()

    with pytest.raises(
        CiboCapitalManagementError,
        match="does not match declared slot",
    ):
        aggregator.record_candidate(
            slot_id="R43_GBPUSD|GBPUSD",
            opportunity=_observed(
                TraderLineage.VT31_NAS100,
                "NAS100",
                "wrong-slot-signal",
            ),
            observed_at=OPENED_AT + timedelta(milliseconds=200),
        )


def test_epoch_rejects_any_result_after_seal() -> None:
    aggregator = _aggregator()
    for slot_id in (
        "VT31_NAS100|NAS100",
        "R43_GBPUSD|GBPUSD",
        "R34_XAUUSD|XAUUSD",
    ):
        aggregator.record_non_candidate(
            slot_id=slot_id,
            disposition=Phase20ForwardPopulationDisposition.ABSTAIN,
            observed_at=OPENED_AT + timedelta(milliseconds=100),
            reason="NO_SETUP",
        )
    decision_at = OPENED_AT + timedelta(milliseconds=200)
    aggregator.seal(decision_at=decision_at)

    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot be added after epoch seal",
    ):
        aggregator.record_candidate(
            slot_id="VT31_NAS100|NAS100",
            opportunity=_observed(
                TraderLineage.VT31_NAS100,
                "NAS100",
                "late-signal",
            ),
            observed_at=OPENED_AT + timedelta(milliseconds=300),
        )


def test_epoch_rejects_result_after_deadline() -> None:
    aggregator = _aggregator()

    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot arrive after epoch deadline",
    ):
        aggregator.record_non_candidate(
            slot_id="R43_GBPUSD|GBPUSD",
            disposition=Phase20ForwardPopulationDisposition.FAIL_CLOSED,
            observed_at=DEADLINE_AT + timedelta(microseconds=1),
            reason="LATE_RESULT",
        )
