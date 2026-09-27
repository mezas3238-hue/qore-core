from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_capital_source_ledger_store import (
    VersionedCapitalSourceLedger,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_single_slot import (
    PHASE20_DEMO_SINGLE_SLOT_REGIME_ID,
    Phase20DemoSingleSlotTerminal,
    build_ctrader_demo_single_slot_known_option,
    build_ctrader_demo_single_slot_observed_opportunity,
    finalize_ctrader_demo_single_slot_phase20_policy,
    phase20_demo_single_slot_regime_sha256,
    prepare_ctrader_demo_single_slot_phase20_epoch,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardPopulationDisposition,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    DurablePhase20ForwardPolicyStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.ctrader_demo_compat import (
    CTraderDemoAccountState,
    CTraderDemoSymbolSpecification,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

OPENED = datetime(2026, 9, 27, 20, 0, tzinfo=UTC)
DECISION = OPENED + timedelta(milliseconds=400)
DEADLINE = OPENED + timedelta(seconds=2)


def _spec(symbol: str = "NDX100") -> CTraderDemoSymbolSpecification:
    return CTraderDemoSymbolSpecification(
        provider_symbol=symbol,
        bid=Decimal("99.99"),
        ask=Decimal("100.01"),
        spread_points=Decimal("2"),
        digits=2,
        point=Decimal("0.01"),
        contract_size=Decimal("1"),
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("1"),
        minimum_stop_distance_points=Decimal("1"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("10"),
        trade_enabled=True,
        session_open=True,
        observed_at=OPENED + timedelta(milliseconds=100),
        open_commission_per_lot_usd=Decimal("0"),
    )


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="single-slot-vt31-signal",
        qore_symbol="NAS100",
        provider_symbol="NDX100",
        side="long",
        entry_type="limit",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("100"),
        margin_per_volume=Decimal("10"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("100"),
        minimum_execution_steps=1,
    )


def _short_opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="single-slot-vt31-short-signal",
        qore_symbol="NAS100",
        provider_symbol="NDX100",
        side="short",
        entry_type="limit",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("101"),
        take_profit=Decimal("98"),
        stop_loss_per_volume=Decimal("100"),
        margin_per_volume=Decimal("10"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("100"),
        minimum_execution_steps=1,
    )


def _account_state() -> CTraderDemoAccountState:
    return CTraderDemoAccountState(
        balance=Decimal("1000"),
        equity=Decimal("990"),
        margin=Decimal("20"),
        free_margin=Decimal("970"),
        observed_at=OPENED + timedelta(milliseconds=50),
    )


def _capital() -> VersionedCapitalSourceLedger:
    return VersionedCapitalSourceLedger(
        generation=1,
        ledger=CapitalSourceLedger().add_source(
            source_id="phase20d-demo-assigned-base:single-slot",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("1000"),
        ),
    )


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="single-slot-demo",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _risk(tmp_path: Path) -> DurableAccountWideRiskEngine:
    return DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(tmp_path / "risk.json")
    )


def test_single_slot_candidate_seals_watch_regime_without_execution(
    tmp_path: Path,
) -> None:
    spec = _spec()
    observed = build_ctrader_demo_single_slot_observed_opportunity(
        opportunity=_opportunity(),
        provider_spec=spec,
        observed_at=OPENED + timedelta(milliseconds=200),
    )
    terminal = Phase20DemoSingleSlotTerminal(
        trader_id=TraderLineage.VT31_NAS100,
        qore_symbol="NAS100",
        observed_at=OPENED + timedelta(milliseconds=200),
        disposition=Phase20ForwardPopulationDisposition.CANDIDATE,
        reason="VALID_TRADER_OPPORTUNITY",
        opportunity=observed,
    )
    evidence = DurablePhase20ForwardEvidenceStore(
        tmp_path / "evidence.json"
    )
    policy = DurablePhase20ForwardPolicyStore(tmp_path / "policy.json")

    prepared = prepare_ctrader_demo_single_slot_phase20_epoch(
        epoch_scope="ctrader-demo:vt31:single-slot",
        opened_at=OPENED,
        deadline_at=DEADLINE,
        decision_at=DECISION,
        terminal=terminal,
        provider_spec=spec,
        evidence_store=evidence,
        account_identity=_identity(),
        account_state=_account_state(),
        risk=_risk(tmp_path),
        executed_risk_book=VersionedPhase20ExecutedRiskBook(generation=0),
        open_position_ids=(),
        pending_broker_worst_case_loss_usd=Decimal("0"),
        capital_state=_capital(),
        highest_closed_balance=Decimal("1000"),
        current_step=1,
    )

    assert prepared.regime_policy_id == PHASE20_DEMO_SINGLE_SLOT_REGIME_ID
    assert prepared.regime_policy_sha256 == (
        phase20_demo_single_slot_regime_sha256()
    )
    assert evidence.load().generation == 1
    assert policy.load().generation == 0
    assert prepared.result.decision_record.regime.posture.value == "WATCH"
    assert prepared.result.evidence.candidates[0].candidate.trader_id is (
        TraderLineage.VT31_NAS100
    )
    assert prepared.broker_mutation_performed is False

    finalized = finalize_ctrader_demo_single_slot_phase20_policy(
        prepared=prepared,
        evidence_store=evidence,
        policy_store=policy,
    )
    assert policy.load().generation == 1
    assert finalized.broker_mutation_performed is False
    assert finalized.execution_authority is False


def test_single_slot_abstain_is_retained_without_fabricated_market_context(
    tmp_path: Path,
) -> None:
    terminal = Phase20DemoSingleSlotTerminal(
        trader_id=TraderLineage.VT08_FOREX,
        qore_symbol="GBPUSD",
        observed_at=OPENED + timedelta(milliseconds=150),
        disposition=Phase20ForwardPopulationDisposition.ABSTAIN,
        reason="CAUSAL_ABSTAIN",
    )
    evidence = DurablePhase20ForwardEvidenceStore(
        tmp_path / "abstain-evidence.json"
    )
    prepared = prepare_ctrader_demo_single_slot_phase20_epoch(
        epoch_scope="ctrader-demo:vt08:GBPUSD:single-slot",
        opened_at=OPENED,
        deadline_at=DEADLINE,
        decision_at=DECISION,
        terminal=terminal,
        provider_spec=None,
        evidence_store=evidence,
        account_identity=_identity(),
        account_state=_account_state(),
        risk=_risk(tmp_path),
        executed_risk_book=VersionedPhase20ExecutedRiskBook(generation=0),
        open_position_ids=(),
        pending_broker_worst_case_loss_usd=Decimal("0"),
        capital_state=_capital(),
        highest_closed_balance=Decimal("1000"),
        current_step=2,
    )

    assert prepared.result.evidence.candidates == ()
    assert (
        prepared.result.evidence.population_slots[0].disposition
        is Phase20ForwardPopulationDisposition.ABSTAIN
    )
    assert prepared.result.evidence.regime_state.evidence_stale is True
    assert prepared.result.evidence.regime_state.provider_condition.value == (
        "UNAVAILABLE"
    )



def test_single_slot_virtual_oco_is_preserved_as_known_options(
    tmp_path: Path,
) -> None:
    spec = _spec()
    known_at = OPENED + timedelta(milliseconds=150)
    expiry = OPENED + timedelta(minutes=5)
    long_option = build_ctrader_demo_single_slot_known_option(
        opportunity=_opportunity(),
        provider_spec=spec,
        known_as_of=known_at,
        decision_step=2,
        expires_at=expiry,
    )
    short_option = build_ctrader_demo_single_slot_known_option(
        opportunity=_short_opportunity(),
        provider_spec=spec,
        known_as_of=known_at,
        decision_step=2,
        expires_at=expiry,
    )
    terminal = Phase20DemoSingleSlotTerminal(
        trader_id=TraderLineage.VT31_NAS100,
        qore_symbol="NAS100",
        observed_at=known_at,
        disposition=Phase20ForwardPopulationDisposition.ABSTAIN,
        reason="VIRTUAL_OCO_ARMED_AS_KNOWN_OPTIONS",
    )
    evidence = DurablePhase20ForwardEvidenceStore(
        tmp_path / "oco-evidence.json"
    )

    prepared = prepare_ctrader_demo_single_slot_phase20_epoch(
        epoch_scope="ctrader-demo:vt31:oco-known-options",
        opened_at=OPENED,
        deadline_at=DEADLINE,
        decision_at=DECISION,
        terminal=terminal,
        provider_spec=spec,
        evidence_store=evidence,
        account_identity=_identity(),
        account_state=_account_state(),
        risk=_risk(tmp_path),
        executed_risk_book=VersionedPhase20ExecutedRiskBook(generation=0),
        open_position_ids=(),
        pending_broker_worst_case_loss_usd=Decimal("0"),
        capital_state=_capital(),
        highest_closed_balance=Decimal("1000"),
        current_step=1,
        known_options=(long_option, short_option),
    )

    sealed = prepared.result.evidence
    assert sealed.candidates == ()
    assert len(sealed.known_options) == 2
    assert all(
        item.option.decision_step == 2
        for item in sealed.known_options
    )
    assert len(
        prepared.result.decision_record.mpc_plan.representative_option_ids
    ) == 1
    assert prepared.result.decision_record.mpc_plan.reserve_stop_risk_usd > 0
