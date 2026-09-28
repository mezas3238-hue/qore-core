from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_epoch import (
    Phase20ForwardObservedOpportunity,
    seal_phase20_forward_observed_epoch,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardPopulationDisposition,
    Phase20ForwardPopulationSlotEvidence,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.cibo_ce2i_phase20_robust_allocator import (
    Phase20AllocatorDisposition,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

DECISION_AT = datetime(2026, 9, 28, 5, 15, tzinfo=UTC)


def _account() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="demo-forward",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _opportunity(
    trader_id: TraderLineage,
    signal_fingerprint: str,
    symbol: str,
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trader_id,
        signal_fingerprint=signal_fingerprint,
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


def _observed(
    trader_id: TraderLineage,
    signal_fingerprint: str,
    symbol: str,
    *,
    observed_at: datetime | None = None,
) -> Phase20ForwardObservedOpportunity:
    opportunity = _opportunity(trader_id, signal_fingerprint, symbol)
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
        observed_at=(
            observed_at
            if observed_at is not None
            else DECISION_AT - timedelta(seconds=1)
        ),
    )
    return Phase20ForwardObservedOpportunity(
        provider_evidence_id=f"provider:{signal_fingerprint}",
        opportunity=opportunity,
        provider_observation=provider,
        concentration_group=symbol,
        concentration_risk_usd=Decimal("10"),
    )


def _population(
    opportunities: tuple[Phase20ForwardObservedOpportunity, ...],
) -> tuple[Phase20ForwardPopulationSlotEvidence, ...]:
    return tuple(
        Phase20ForwardPopulationSlotEvidence(
            slot_id=(
                f"{item.opportunity.trader_id.value}|"
                f"{item.opportunity.qore_symbol}"
            ),
            trader_id=item.opportunity.trader_id,
            qore_symbol=item.opportunity.qore_symbol,
            observed_at=DECISION_AT - timedelta(milliseconds=1),
            disposition=Phase20ForwardPopulationDisposition.CANDIDATE,
            reason="test candidate",
            signal_fingerprint=item.opportunity.signal_fingerprint,
        )
        for item in opportunities
    )


def _regime(opportunity_count: int) -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.10"),
        margin_utilization=Decimal("0.10"),
        drawdown_utilization=Decimal("0.10"),
        opportunity_count=opportunity_count,
    )


def _store(tmp_path: Path) -> DurablePhase20ForwardEvidenceStore:
    return DurablePhase20ForwardEvidenceStore(tmp_path / "forward.json")


def _seal(
    tmp_path: Path,
    opportunities: tuple[Phase20ForwardObservedOpportunity, ...],
):
    return seal_phase20_forward_observed_epoch(
        store=_store(tmp_path),
        decision_epoch_id="test-forward-epoch",
        decision_at=DECISION_AT,
        account_identity=_account(),
        capital_snapshot_id="capital:41",
        capital_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
        risk_snapshot_id="risk:77",
        risk_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
        hard_risk_headroom_usd=Decimal("40"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=tuple(
            sorted(
                {
                    item.concentration_group: Decimal("20")
                    for item in opportunities
                }.items()
            )
        ),
        regime_state=_regime(len(opportunities)),
        current_step=0,
        population_slots=_population(opportunities),
        opportunities=opportunities,
    )


def test_forward_epoch_builds_frozen_train_candidates_and_seals_population(
    tmp_path: Path,
) -> None:
    rows = (
        _observed(
            TraderLineage.VT31_NAS100,
            "signal-vt31",
            "NAS100",
        ),
        _observed(
            TraderLineage.R43_GBPUSD,
            "signal-r43",
            "GBPUSD",
        ),
    )

    result = _seal(tmp_path, rows)

    assert result.sealed_generation == 1
    sealed = _store(tmp_path).load()
    assert sealed.generation == 1
    assert len(sealed.decisions) == 1

    candidates = result.evidence.candidates
    assert tuple(item.candidate.signal_fingerprint for item in candidates) == tuple(
        item.opportunity.signal_fingerprint
        for item in sorted(
            rows,
            key=lambda item: (
                item.opportunity.trader_id.value,
                item.opportunity.qore_symbol,
                item.opportunity.provider_symbol,
                item.opportunity.signal_fingerprint,
                item.provider_evidence_id,
            ),
        )
    )
    assert all(
        item.candidate.expectation.basis
        is CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR
        for item in candidates
    )
    assert all(
        item.candidate.stop_risk_usd == Decimal("10")
        and item.candidate.margin_usd == Decimal("10")
        for item in candidates
    )
    assert (
        result.decision_record.allocator_decision.disposition
        is Phase20AllocatorDisposition.ALLOCATE
    )
    assert set(
        result.decision_record.allocator_decision.allocation.selected_signal_fingerprints
    ) == {"signal-vt31", "signal-r43"}


def test_forward_epoch_is_input_order_invariant_and_idempotent(
    tmp_path: Path,
) -> None:
    left = _observed(
        TraderLineage.VT31_NAS100,
        "signal-vt31",
        "NAS100",
    )
    right = _observed(
        TraderLineage.R43_GBPUSD,
        "signal-r43",
        "GBPUSD",
    )

    first = _seal(tmp_path, (left, right))
    second = _seal(tmp_path, (right, left))

    assert first.evidence.evidence_id == second.evidence.evidence_id
    assert first.decision_record.evidence_sha256 == (
        second.decision_record.evidence_sha256
    )
    assert first.sealed_generation == 1
    assert second.sealed_generation == 1
    assert _store(tmp_path).load().generation == 1


def test_forward_epoch_preserves_negative_train_prior_without_tuning(
    tmp_path: Path,
) -> None:
    result = _seal(
        tmp_path,
        (
            _observed(
                TraderLineage.R38_EURUSD,
                "signal-eurusd",
                "EURUSD",
            ),
        ),
    )

    candidate = result.evidence.candidates[0].candidate
    assert candidate.expected_net_value_usd < 0
    assert (
        result.decision_record.allocator_decision.disposition
        is Phase20AllocatorDisposition.NO_ELIGIBLE_ALLOCATION
    )
    assert result.decision_record.allocator_decision.allocation is not None
    assert (
        result.decision_record.allocator_decision.allocation.selected_signal_fingerprints
        == ()
    )


def test_forward_epoch_rejects_provider_account_mismatch_before_seal(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    base = _observed(
        TraderLineage.VT31_NAS100,
        "signal-provider-mismatch",
        "NAS100",
    )
    wrong_provider = Phase20ForwardObservedOpportunity(
        provider_evidence_id=base.provider_evidence_id,
        opportunity=base.opportunity,
        provider_observation=ProviderEconomicObservation(
            provider_key="fundednext",
            qore_symbol=base.provider_observation.qore_symbol,
            provider_symbol=base.provider_observation.provider_symbol,
            bid=base.provider_observation.bid,
            ask=base.provider_observation.ask,
            contract_size=base.provider_observation.contract_size,
            tick_size=base.provider_observation.tick_size,
            tick_value=base.provider_observation.tick_value,
            minimum_volume=base.provider_observation.minimum_volume,
            maximum_volume=base.provider_observation.maximum_volume,
            volume_step=base.provider_observation.volume_step,
            margin_per_volume=base.provider_observation.margin_per_volume,
            commission_per_volume_usd=(
                base.provider_observation.commission_per_volume_usd
            ),
            slippage_reserve_per_volume_usd=(
                base.provider_observation.slippage_reserve_per_volume_usd
            ),
            observed_at=base.provider_observation.observed_at,
        ),
        concentration_group=base.concentration_group,
        concentration_risk_usd=base.concentration_risk_usd,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="provider observation must match account provider",
    ):
        seal_phase20_forward_observed_epoch(
            store=store,
            decision_epoch_id="provider-mismatch-epoch",
            decision_at=DECISION_AT,
            account_identity=_account(),
            capital_snapshot_id="capital:41",
            capital_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
            risk_snapshot_id="risk:77",
            risk_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
            hard_risk_headroom_usd=Decimal("40"),
            margin_headroom_usd=Decimal("100"),
            concentration_limit_by_group=(("NAS100", Decimal("20")),),
            regime_state=_regime(1),
            current_step=0,
            population_slots=_population((wrong_provider,)),
            opportunities=(wrong_provider,),
        )

    assert store.load().generation == 0


def test_forward_epoch_rejects_provider_relabel_as_conflicting_rewrite(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    base = _observed(
        TraderLineage.VT31_NAS100,
        "signal-provider-relabel",
        "NAS100",
    )
    first = seal_phase20_forward_observed_epoch(
        store=store,
        decision_epoch_id="provider-relabel-epoch",
        decision_at=DECISION_AT,
        account_identity=_account(),
        capital_snapshot_id="capital:41",
        capital_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
        risk_snapshot_id="risk:77",
        risk_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
        hard_risk_headroom_usd=Decimal("40"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("NAS100", Decimal("20")),),
        regime_state=_regime(1),
        current_step=0,
        population_slots=_population((base,)),
        opportunities=(base,),
    )
    relabelled = Phase20ForwardObservedOpportunity(
        provider_evidence_id="provider:relabelled",
        opportunity=base.opportunity,
        provider_observation=base.provider_observation,
        concentration_group=base.concentration_group,
        concentration_risk_usd=base.concentration_risk_usd,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="conflicting forward decision rewrite",
    ):
        seal_phase20_forward_observed_epoch(
            store=store,
            decision_epoch_id="provider-relabel-epoch",
            decision_at=DECISION_AT,
            account_identity=_account(),
            capital_snapshot_id="capital:41",
            capital_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
            risk_snapshot_id="risk:77",
            risk_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
            hard_risk_headroom_usd=Decimal("40"),
            margin_headroom_usd=Decimal("100"),
            concentration_limit_by_group=(("NAS100", Decimal("20")),),
            regime_state=_regime(1),
            current_step=0,
            population_slots=_population((relabelled,)),
            opportunities=(relabelled,),
        )

    assert first.evidence.evidence_id == (
        "phase20d-forward-epoch:"
        + first.evidence.evidence_id.split(":", 1)[1]
    )
    assert store.load().generation == 1


def test_forward_epoch_rejects_stale_provider_before_durable_seal(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    stale = _observed(
        TraderLineage.VT31_NAS100,
        "signal-stale",
        "NAS100",
        observed_at=DECISION_AT - timedelta(seconds=3),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="provider snapshot exceeds frozen freshness bound",
    ):
        seal_phase20_forward_observed_epoch(
            store=store,
            decision_epoch_id="stale-provider-epoch",
            decision_at=DECISION_AT,
            account_identity=_account(),
            capital_snapshot_id="capital:41",
            capital_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
            risk_snapshot_id="risk:77",
            risk_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
            hard_risk_headroom_usd=Decimal("40"),
            margin_headroom_usd=Decimal("100"),
            concentration_limit_by_group=(("NAS100", Decimal("20")),),
            regime_state=_regime(1),
            current_step=0,
            population_slots=_population((stale,)),
            opportunities=(stale,),
        )

    assert store.load().generation == 0


def test_forward_epoch_seals_before_policy_evaluation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import cibo_ce2i_phase20_forward_epoch as epoch_module

    store = _store(tmp_path)
    observed = _observed(
        TraderLineage.VT31_NAS100,
        "signal-seal-first",
        "NAS100",
    )

    def _fail_after_seal(_evidence):
        raise RuntimeError("forced post-seal policy failure")

    monkeypatch.setattr(
        epoch_module,
        "build_phase20_forward_decision_record",
        _fail_after_seal,
    )

    with pytest.raises(RuntimeError, match="forced post-seal policy failure"):
        seal_phase20_forward_observed_epoch(
            store=store,
            decision_epoch_id="seal-first-epoch",
            decision_at=DECISION_AT,
            account_identity=_account(),
            capital_snapshot_id="capital:41",
            capital_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
            risk_snapshot_id="risk:77",
            risk_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
            hard_risk_headroom_usd=Decimal("40"),
            margin_headroom_usd=Decimal("100"),
            concentration_limit_by_group=(("NAS100", Decimal("20")),),
            regime_state=_regime(1),
            current_step=0,
            population_slots=_population((observed,)),
            opportunities=(observed,),
        )

    sealed = store.load()
    assert sealed.generation == 1
    assert len(sealed.decisions) == 1
