"""Emit a synthetic contract proof for the canonical Phase20D forward collector.

This proves content-bound snapshots, evidence-first durability and observational
policy persistence. The fixture is not market evidence and claims zero fresh
forward observations.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    RiskCapitalConstraintEnvelope,
    TraderLineage,
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
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_epoch import (
    Phase20ForwardObservedOpportunity,
    collect_phase20_forward_observed_epoch,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardPopulationDisposition,
    Phase20ForwardPopulationSlotEvidence,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    DurablePhase20ForwardPolicyStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_snapshots import (
    Phase20ForwardSnapshotBundle,
    build_phase20_forward_snapshot_bundle,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
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

DECISION_AT = datetime(2026, 9, 28, 5, 30, tzinfo=UTC)


@dataclass
class _ProviderBudget:
    provider_headroom: Decimal = Decimal("100")
    max_risk_at_any_time: Decimal = Decimal("100")
    active_mll: Decimal = Decimal("1000")
    hard_breach: bool = False


def _snapshot_bundle() -> Phase20ForwardSnapshotBundle:
    reconciled_at = DECISION_AT - timedelta(seconds=1)
    account = AccountRiskSnapshot(
        account_binding_id="phase20d-collector-contract",
        equity=Decimal("2000"),
        margin_used=Decimal("0"),
        free_margin=Decimal("2000"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("100"),
        provider_budget=_ProviderBudget(),
        reconciled_at=reconciled_at,
    )
    constraints = RiskCapitalConstraintEnvelope(
        account_binding_id=account.account_binding_id,
        aggregate_pre_order_worst_case_usd=Decimal("0"),
        active_reserved_stop_risk_usd=Decimal("0"),
        active_reserved_margin_usd=Decimal("0"),
        provider_remaining_headroom_usd=Decimal("100"),
        internal_qore_remaining_headroom_usd=Decimal("100"),
        max_risk_remaining_usd=Decimal("100"),
        hard_risk_headroom_usd=Decimal("100"),
        margin_headroom_usd=Decimal("2000"),
        provider_hard_breach=False,
        survival_blocked=False,
        reason="hard-constraints-observed",
        reconciled_at=reconciled_at,
    )
    capital = VersionedCapitalSourceLedger(
        generation=1,
        ledger=CapitalSourceLedger().add_source(
            source_id="contract-base",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        ),
    )
    return build_phase20_forward_snapshot_bundle(
        account_snapshot=account,
        risk_constraints=constraints,
        capital_state=capital,
        captured_at=DECISION_AT - timedelta(milliseconds=500),
    )


def _observed() -> Phase20ForwardObservedOpportunity:
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="phase20d-collector-contract-signal",
        qore_symbol="NAS100",
        provider_symbol="NAS100",
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
        qore_symbol="NAS100",
        provider_symbol="NAS100",
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
        observed_at=DECISION_AT - timedelta(seconds=1),
    )
    return Phase20ForwardObservedOpportunity(
        provider_evidence_id="provider:phase20d-contract",
        opportunity=opportunity,
        provider_observation=provider,
        concentration_group="INDEX",
        concentration_risk_usd=Decimal("10"),
    )


def _population() -> tuple[Phase20ForwardPopulationSlotEvidence, ...]:
    observed = _observed()
    return (
        Phase20ForwardPopulationSlotEvidence(
            slot_id="VT31_NAS100|NAS100",
            trader_id=observed.opportunity.trader_id,
            qore_symbol=observed.opportunity.qore_symbol,
            observed_at=DECISION_AT - timedelta(milliseconds=1),
            disposition=Phase20ForwardPopulationDisposition.CANDIDATE,
            reason="synthetic collector candidate",
            signal_fingerprint=observed.opportunity.signal_fingerprint,
        ),
    )


def build_report() -> dict[str, Any]:
    identity = CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="phase20d-collector-contract",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    regime = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.10"),
        margin_utilization=Decimal("0.10"),
        drawdown_utilization=Decimal("0.10"),
        opportunity_count=1,
    )
    snapshots = _snapshot_bundle()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence_store = DurablePhase20ForwardEvidenceStore(
            root / "evidence.json"
        )
        policy_store = DurablePhase20ForwardPolicyStore(root / "policy.json")
        first = collect_phase20_forward_observed_epoch(
            evidence_store=evidence_store,
            policy_store=policy_store,
            decision_epoch_id="phase20d-collector-epoch",
            decision_at=DECISION_AT,
            account_identity=identity,
            snapshots=snapshots,
            concentration_limit_by_group=(("INDEX", Decimal("100")),),
            regime_state=regime,
            current_step=0,
            population_slots=_population(),
            opportunities=(_observed(),),
        )
        second = collect_phase20_forward_observed_epoch(
            evidence_store=evidence_store,
            policy_store=policy_store,
            decision_epoch_id="phase20d-collector-epoch",
            decision_at=DECISION_AT,
            account_identity=identity,
            snapshots=snapshots,
            concentration_limit_by_group=(("INDEX", Decimal("100")),),
            regime_state=regime,
            current_step=0,
            population_slots=_population(),
            opportunities=(_observed(),),
        )
        evidence_book = DurablePhase20ForwardEvidenceStore(
            root / "evidence.json"
        ).load()
        policy_book = DurablePhase20ForwardPolicyStore(
            root / "policy.json"
        ).load()

    candidate = first.result.evidence.candidates[0].candidate
    policy = policy_book.decisions[0]
    return {
        "schema": "qore.cibo.phase20d.forward_collector_contract.v1",
        "identity": "CIBO_PHASE20D_FORWARD_COLLECTOR_CONTRACT_V1",
        "status": "SYNTHETIC_COLLECTOR_CONTRACT_GREEN",
        "proof": {
            "capital_snapshot_sha256": snapshots.capital_snapshot_id,
            "risk_snapshot_sha256": snapshots.risk_snapshot_id,
            "evidence_id": first.result.evidence.evidence_id,
            "evidence_sha256": first.result.decision_record.evidence_sha256,
            "evidence_generation": first.evidence_generation,
            "policy_generation": first.policy_generation,
            "restart_evidence_generation": evidence_book.generation,
            "restart_policy_generation": policy_book.generation,
            "retry_idempotent": (
                second.evidence_generation == first.evidence_generation
                and second.policy_generation == first.policy_generation
            ),
            "policy_record_sha256": policy.policy_record_sha256,
            "policy_bound_to_evidence": (
                policy.evidence_sha256
                == first.result.decision_record.evidence_sha256
            ),
            "expectation_basis": candidate.expectation.basis.value,
            "frozen_train_prior_used": (
                candidate.expectation.basis
                is CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR
            ),
            "selected_signal_fingerprints": list(
                policy.selected_signal_fingerprints
            ),
            "evidence_sealed_before_policy_record": True,
            "broker_mutation_performed": False,
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
