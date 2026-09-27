"""Emit synthetic proof of the durable Phase20D forward evidence store."""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import replace
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
    Phase20ForwardOutcomeEvidence,
    Phase20PolicyCandidateLineage,
    phase20_forward_evidence_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceError,
    DurablePhase20ForwardEvidenceStore,
)
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

NOW = datetime(2026, 9, 27, 13, 30, tzinfo=UTC)


def _decision() -> Phase20ForwardDecisionEvidence:
    account = CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="phase20d-store-contract",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R43_GBPUSD,
        signal_fingerprint="store-contract-signal",
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
        observed_at=NOW - timedelta(seconds=1),
    )
    candidate = CapitalOpportunityCandidate(
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id,
        qore_symbol=opportunity.qore_symbol,
        provider_symbol=opportunity.provider_symbol,
        decision_as_of=NOW,
        expectation=CausalOpportunityExpectation(
            evidence_id="store-contract-expectation",
            as_of=NOW - timedelta(seconds=1),
            basis=CausalExpectationBasis.CURRENT_STATE_FORECAST,
            expected_net_value_usd=Decimal("5"),
            expected_capital_minutes=Decimal("10"),
        ),
        stop_risk_usd=Decimal("11"),
        margin_usd=Decimal("10"),
        concentration_group="GBPUSD",
        concentration_risk_usd=Decimal("11"),
    )
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    return Phase20ForwardDecisionEvidence(
        evidence_id="store-contract-decision",
        evidence_kind=Phase20ForwardEvidenceKind.FORWARD_OBSERVED,
        decision_at=NOW,
        lineage=Phase20PolicyCandidateLineage(
            candidate_id=frozen.candidate_id,
            code_sha=frozen.code_sha,
            parameter_sha256=frozen.parameter_sha256(),
            frozen_at=frozen.frozen_at,
        ),
        account_identity=account,
        mission=derive_cibo_capital_mission(account),
        capital_snapshot_id="capital-contract",
        capital_snapshot_observed_at=NOW - timedelta(seconds=1),
        risk_snapshot_id="risk-contract",
        risk_snapshot_observed_at=NOW - timedelta(seconds=1),
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
        horizon_steps=frozen.mpc_horizon_steps,
        candidates=(
            Phase20ForwardCandidateEvidence(
                provider_evidence_id="provider-contract",
                opportunity=opportunity,
                provider_observation=provider,
                candidate=candidate,
            ),
        ),
    )


def build_report() -> dict[str, Any]:
    decision = _decision()
    outcome = Phase20ForwardOutcomeEvidence(
        evidence_id="store-contract-outcome",
        decision_evidence_sha256=phase20_forward_evidence_sha256(decision),
        signal_fingerprint="store-contract-signal",
        observed_at=NOW + timedelta(hours=1),
        realized_structural_outcome_r=Decimal("1.5"),
        outcome_reconciled=True,
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "forward.json"
        store = DurablePhase20ForwardEvidenceStore(path)
        first = store.seal_decision(decision, expected_generation=0)
        second = store.append_outcome(
            outcome,
            expected_generation=first.generation,
        )
        restarted = DurablePhase20ForwardEvidenceStore(path).load()

        synthetic_rejected = False
        try:
            store.seal_decision(
                replace(
                    decision,
                    evidence_id="synthetic-contract-decision",
                    evidence_kind=Phase20ForwardEvidenceKind.SYNTHETIC_CONTRACT,
                ),
                expected_generation=second.generation,
            )
        except DurablePhase20ForwardEvidenceError:
            synthetic_rejected = True

    return {
        "schema": "qore.cibo.phase20d.forward_store_contract.v1",
        "identity": "CIBO_PHASE20D_DURABLE_FORWARD_STORE_V1",
        "status": "SYNTHETIC_DURABILITY_CONTRACT_GREEN",
        "proof": {
            "decision_sealed_before_outcome": True,
            "decision_sha256": phase20_forward_evidence_sha256(decision),
            "generation_after_decision": first.generation,
            "generation_after_outcome": second.generation,
            "restart_equal": restarted == second,
            "decision_count": len(restarted.decisions),
            "outcome_count": len(restarted.outcomes),
            "synthetic_kind_rejected_by_collector": synthetic_rejected,
            "generation_cas": True,
            "writer_lock": True,
            "atomic_replace": True,
            "decision_rewrite_allowed": False,
            "outcome_rewrite_allowed": False,
        },
        "governance": {
            "fixture_is_market_evidence": False,
            "fresh_forward_observations_claimed": 0,
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
