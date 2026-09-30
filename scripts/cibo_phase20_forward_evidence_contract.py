"""Emit synthetic Phase20D forward-evidence contract proof.

The fixture proves collection/causality rules only. It is deliberately marked
SYNTHETIC_CONTRACT and cannot qualify a policy as fresh-forward OOS.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
    CausalOpportunityExpectation,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardCandidateEvidence,
    Phase20ForwardDecisionEvidence,
    Phase20ForwardEvidenceKind,
    Phase20ForwardKnownOptionEvidence,
    Phase20ForwardOutcomeEvidence,
    Phase20ForwardPopulationDisposition,
    Phase20ForwardPopulationSlotEvidence,
    Phase20PolicyCandidateLineage,
    assess_phase20d_forward_qualification,
    build_phase20_forward_decision_record,
    phase20_forward_evidence_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_mpc import Phase20MpcKnownOption
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
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

DECISION_AT = datetime(2026, 9, 28, 5, 0, tzinfo=UTC)


def _build_fixture() -> Phase20ForwardDecisionEvidence:
    account = CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="phase20d-contract-fixture",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    mission = derive_cibo_capital_mission(account)
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R43_GBPUSD,
        signal_fingerprint="phase20d-contract-signal",
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("11"),
        margin_per_volume=Decimal("10"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
    )
    provider = ProviderEconomicObservation(
        provider_key="ctrader-demo",
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD",
        bid=Decimal("100"),
        ask=Decimal("100.1"),
        contract_size=Decimal("100000"),
        tick_size=Decimal("0.1"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
        volume_step=Decimal("1"),
        margin_per_volume=Decimal("10"),
        commission_per_volume_usd=Decimal("0"),
        slippage_reserve_per_volume_usd=Decimal("0"),
        observed_at=DECISION_AT - timedelta(seconds=1),
    )
    expectation = CausalOpportunityExpectation(
        evidence_id="phase20d-contract-expectation",
        as_of=DECISION_AT - timedelta(seconds=2),
        basis=CausalExpectationBasis.CURRENT_STATE_FORECAST,
        expected_net_value_usd=Decimal("5"),
        expected_capital_minutes=Decimal("10"),
    )
    candidate = CapitalOpportunityCandidate(
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id,
        qore_symbol=opportunity.qore_symbol,
        provider_symbol=opportunity.provider_symbol,
        decision_as_of=DECISION_AT,
        expectation=expectation,
        stop_risk_usd=Decimal("11"),
        margin_usd=Decimal("10"),
        concentration_group="GBPUSD",
        concentration_risk_usd=Decimal("11"),
    )
    known_option = Phase20ForwardKnownOptionEvidence(
        evidence_id="phase20d-contract-known-option",
        option=Phase20MpcKnownOption(
            opportunity_id="future-option-1",
            decision_step=1,
            minimum_stop_risk_usd=Decimal("5"),
            minimum_margin_usd=Decimal("10"),
        ),
        known_as_of=DECISION_AT - timedelta(seconds=5),
        active_at_decision=True,
        expires_at=DECISION_AT + timedelta(hours=1),
    )
    return Phase20ForwardDecisionEvidence(
        evidence_id="phase20d-contract-decision",
        decision_epoch_id="phase20d-contract-epoch",
        evidence_kind=Phase20ForwardEvidenceKind.SYNTHETIC_CONTRACT,
        decision_at=DECISION_AT,
        lineage=Phase20PolicyCandidateLineage(
            candidate_id=FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
            code_sha=FROZEN_PHASE20_POLICY_CANDIDATE.code_sha,
            parameter_sha256=(
                FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
            ),
            frozen_at=FROZEN_PHASE20_POLICY_CANDIDATE.frozen_at,
        ),
        account_identity=account,
        mission=mission,
        capital_snapshot_id="capital-generation-7",
        capital_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
        risk_snapshot_id="risk-generation-11",
        risk_snapshot_observed_at=DECISION_AT - timedelta(seconds=1),
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("100"),
        concentration_limit_by_group=(("GBPUSD", Decimal("20")),),
        regime_state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            risk_utilization=Decimal("0.20"),
            margin_utilization=Decimal("0.20"),
            drawdown_utilization=Decimal("0.10"),
            opportunity_count=1,
        ),
        current_step=0,
        horizon_steps=2,
        population_slots=(
            Phase20ForwardPopulationSlotEvidence(
                slot_id="R43_GBPUSD|GBPUSD|phase20d-contract-epoch",
                trader_id=TraderLineage.R43_GBPUSD,
                qore_symbol="GBPUSD",
                observed_at=DECISION_AT - timedelta(milliseconds=1),
                disposition=Phase20ForwardPopulationDisposition.CANDIDATE,
                reason="synthetic candidate fixture",
                signal_fingerprint="phase20d-contract-signal",
            ),
        ),
        candidates=(
            Phase20ForwardCandidateEvidence(
                provider_evidence_id="provider-snapshot-1",
                opportunity=opportunity,
                provider_observation=provider,
                candidate=candidate,
            ),
        ),
        known_options=(known_option,),
    )


def build_report() -> dict[str, Any]:
    decision = _build_fixture()
    record = build_phase20_forward_decision_record(decision)
    outcome = Phase20ForwardOutcomeEvidence(
        evidence_id="phase20d-contract-outcome",
        decision_evidence_sha256=phase20_forward_evidence_sha256(decision),
        signal_fingerprint="phase20d-contract-signal",
        position_id=1,
        execution_risk_evidence_id="phase20d-contract-risk",
        settlement_deal_ids=(1,),
        fill_evidence_refs=("phase20d-contract-fill",),
        observed_at=DECISION_AT + timedelta(hours=2),
        realized_net_pnl_usd=Decimal("15"),
        executed_initial_stop_risk_usd=Decimal("10"),
        realized_structural_outcome_r=Decimal("1.5"),
        outcome_reconciled=True,
    )
    qualification = assess_phase20d_forward_qualification(
        decision=decision,
        outcome=outcome,
    )
    allocator = record.allocator_decision
    selected = (
        list(allocator.allocation.selected_signal_fingerprints)
        if allocator.allocation is not None
        else []
    )
    return {
        "schema": "qore.cibo.phase20d.forward_evidence_contract.v1",
        "identity": "CIBO_PHASE20D_FORWARD_EVIDENCE_CONTRACT_V1",
        "status": (
            "SYNTHETIC_COLLECTION_CONTRACT_READY_"
            "FRESH_FORWARD_NOT_COLLECTED"
        ),
        "decision_evidence_sha256": record.evidence_sha256,
        "decision_evidence_kind": decision.evidence_kind.value,
        "lineage": {
            "candidate_id": decision.lineage.candidate_id,
            "code_sha": decision.lineage.code_sha,
            "parameter_sha256": decision.lineage.parameter_sha256,
            "policy_frozen_before_decision": (
                decision.lineage.frozen_at <= decision.decision_at
            ),
            "phase19j_burned_validation_reused": False,
        },
        "predecision_surface": {
            "provider_snapshot_precedes_decision": True,
            "causal_expectation_precedes_decision": True,
            "capital_snapshot_bound": True,
            "capital_snapshot_fresh_within_seconds": "2",
            "risk_snapshot_bound": True,
            "risk_snapshot_fresh_within_seconds": "2",
            "provider_snapshot_fresh_within_seconds": "2",
            "current_forecast_fresh_within_seconds": "2",
            "regime_inputs_bound": True,
            "known_option_known_before_decision": True,
            "known_option_active_expiry_cancel_state_bound": True,
            "outcome_present": False,
        },
        "composition": {
            "order": "PHASE20I_RESERVE_THEN_PHASE20H_ALLOCATE",
            "mpc_reserve_applied_before_allocator": (
                record.mpc_reserve_applied_before_allocator
            ),
            "allocator_input_stop_risk_headroom_usd": str(
                record.allocator_input_stop_risk_headroom_usd
            ),
            "allocator_input_margin_headroom_usd": str(
                record.allocator_input_margin_headroom_usd
            ),
            "double_reservation_authorized": False,
        },
        "phase20h": {
            "disposition": allocator.disposition.value,
            "applied_tools": list(allocator.applied_tools),
            "selected_signal_fingerprints": selected,
            "internal_optionality_reserve_stop_risk_usd": str(
                allocator.reserve_stop_risk_usd
            ),
        },
        "phase20i": {
            "considered_option_ids": list(record.mpc_plan.considered_option_ids),
            "representative_option_ids": list(
                record.mpc_plan.representative_option_ids
            ),
            "reserve_stop_risk_usd": str(
                record.mpc_plan.reserve_stop_risk_usd
            ),
            "reserve_margin_usd": str(record.mpc_plan.reserve_margin_usd),
            "horizon_fully_coverable": record.mpc_plan.horizon_fully_coverable,
        },
        "qualification_probe": {
            "synthetic_fixture_eligible_for_phase20d": qualification.eligible,
            "reasons": list(qualification.reasons),
        },
        "governance": {
            "fresh_forward_evidence_claimed": False,
            "historical_provider_economics_claimed": False,
            "phase19j_validation_reused": False,
            "policy_certified": False,
            "allocation_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
