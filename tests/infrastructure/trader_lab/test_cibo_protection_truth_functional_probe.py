from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    ingest_base_settlement,
    initialize_compound_cycle,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    RealizedProfitEquivalenceBinding,
    build_integrated_capital_truth,
)
from qore.infrastructure.cibo_profit_preservation_shadow import (
    Genc7Action,
    Genc7CapitalStateEvidence,
    Genc7PreservationProposalEvidence,
    Genc7SourceBucket,
    evaluate_genc7_profit_preservation_shadow,
)
from qore.infrastructure.cibo_protected_base_overlay import (
    ProtectedBaseClass,
    build_protected_base_snapshot,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding

NOW = datetime(2026, 10, 3, 3, 40, tzinfo=UTC)


def _tag(candidate: TraderLabCandidateBinding, suffix: str) -> str:
    return f"trader-lab:{candidate.fingerprint.value}:{suffix}"


def _identity(candidate: TraderLabCandidateBinding) -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="trader-lab",
        account_ref=_tag(candidate, "capital-account"),
        environment=MarketRuntimeEnvironment.TEST,
    )


def test_trader_lab_protected_base_reserves_only_original_capital(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=970)
    identity = _identity(candidate)
    ledger = (
        CapitalSourceLedger()
        .add_source(
            source_id=_tag(candidate, "gen0"),
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        )
        .reserve(
            reservation_id=_tag(candidate, "existing-reservation"),
            source_id=_tag(candidate, "gen0"),
            amount_usd=Decimal("20"),
        )
    )

    snapshot = build_protected_base_snapshot(
        account_identity=identity,
        ledger=ledger,
        captured_at=NOW,
        source_id=_tag(candidate, "gen0"),
        protected_base_usd=Decimal("60"),
        protection_class=ProtectedBaseClass.ECONOMICALLY_RESERVED,
        evidence_sha256="sha256:" + "a" * 64,
    )

    assert snapshot.original_base_proven_usd == Decimal("100")
    assert snapshot.original_base_available_usd == Decimal("80")
    assert snapshot.protected_base_usd == Decimal("60")
    assert snapshot.unprotected_available_base_usd == Decimal("20")
    assert snapshot.source_ledger_mutated is False
    assert snapshot.runtime_authority is False


def test_trader_lab_profit_protection_uses_exact_realized_amount(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=971)
    identity = _identity(candidate)
    state = Genc7CapitalStateEvidence(
        evidence_id=_tag(candidate, "genc7-state"),
        decision_at=NOW,
        account_identity=identity,
        current_realized_capital_usd=Decimal("92"),
        current_realized_profit_usd=Decimal("32"),
        peak_realized_profit_usd=Decimal("40"),
        current_base_capital_usd=Decimal("58"),
        peak_base_capital_usd=Decimal("60"),
        current_compound_capital_usd=Decimal("24"),
        peak_compound_capital_usd=Decimal("30"),
        protected_profit_usd=Decimal("12"),
        protected_floor_usd=Decimal("18"),
        previous_protected_floor_usd=Decimal("15"),
        strategic_reserve_usd=Decimal("5"),
        opportunity_reserve_usd=Decimal("3"),
        compoundable_usd=Decimal("14"),
        released_compound_capital_usd=Decimal("4"),
        source_evidence_sha256="sha256:" + "b" * 64,
    )
    proposal = Genc7PreservationProposalEvidence(
        proposal_id=_tag(candidate, "genc7-proposal"),
        decision_at=NOW,
        account_identity=identity,
        action=Genc7Action.PROTECT,
        source_bucket=Genc7SourceBucket.REALIZED_UNPROTECTED_PROFIT,
        amount_usd=Decimal("10"),
        evidence_sha256="sha256:" + "c" * 64,
        rationale_code="TRADER_LAB_FROZEN_PROPOSAL",
        evaluation_horizon_minutes=60,
        calibrated=True,
        capital_eligible=True,
    )

    decision = evaluate_genc7_profit_preservation_shadow(
        state=state,
        proposal=proposal,
        decision_id=_tag(candidate, "genc7-decision"),
    )

    assert state.floating_pnl_included is False
    assert state.future_outcome_present is False
    assert decision.treatment_action is Genc7Action.PROTECT
    assert decision.treatment_amount_usd == Decimal("10")
    assert decision.blocker_codes == ()
    assert decision.outcome_present_at_seal is False
    assert decision.runtime_authority is False
    assert decision.sizing_authority is False
    assert decision.risk_authority is False
    assert decision.execution_authority is False


def test_trader_lab_integrated_capital_truth_prevents_double_counting(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=972)
    identity = _identity(candidate)
    signal = _tag(candidate, "profit-signal")
    state = initialize_compound_cycle(
        account_identity=identity,
        opening_original_base_usd=Decimal("100"),
        t19_ledger=PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("100"),
            concentration_limit_by_group=(("TRADER_LAB", Decimal("10")),),
        ),
    )
    settlement = apply_settlement(
        CmaSettlementState(
            signal_fingerprint=signal,
            position_id=97201,
        ),
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=97210,
            signal_fingerprint=signal,
            position_id=97201,
            net_profit_usd=Decimal("20"),
            position_open_after=False,
        ),
    )
    event_id = _tag(candidate, "profit")
    compound_state = ingest_base_settlement(
        state,
        event_id=event_id,
        occurred_at=NOW,
        trader_id=TraderLineage.VT31_NAS100,
        settlement=settlement,
    )
    profit_source_id = _tag(candidate, "profit-source")
    source_ledger = (
        CapitalSourceLedger()
        .add_source(
            source_id=_tag(candidate, "gen0"),
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        )
        .add_source(
            source_id=profit_source_id,
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("20"),
        )
    )
    truth = build_integrated_capital_truth(
        account_identity=identity,
        source_ledger=source_ledger,
        compound_state=compound_state,
        realized_profit_bindings=(
            RealizedProfitEquivalenceBinding(
                source_id=profit_source_id,
                admission_lot_ids=(event_id + ":gen1",),
            ),
        ),
    )

    assert truth.realized_profit_proven_usd == Decimal("20")
    assert truth.compound_admitted_realized_profit_usd == Decimal("20")
    assert truth.equivalence_residual_usd == Decimal("0")
    assert truth.nonconsumed_residual_usd == Decimal("0")
    assert truth.settlement_provenance_pass is True
    assert truth.admission_coverage_pass is True
    assert truth.no_double_counting_pass is True
    assert truth.fungible_cross_dimension_total_computed is False
