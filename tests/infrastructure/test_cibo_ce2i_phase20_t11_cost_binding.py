import json
from datetime import timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_outcome_reconciliation import (
    Phase20ExecutedRiskEvidence,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_t11_cost_binding import (
    assess_phase20_t11_cost_binding,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
)
from qore.infrastructure.cibo_cma_settlement_store import (
    VersionedCmaSettlementBook,
)

BASE = FROZEN_PHASE20D_QUALIFICATION_PLAN.frozen_at + timedelta(hours=1)


def _evidence():
    decision_at = BASE
    signal = "t11-cost-signal"
    payload = {
        "evidence_kind": "FORWARD_OBSERVED",
        "population_slots": [
            {
                "trader_id": TraderLineage.R43_GBPUSD.value,
                "signal_fingerprint": signal,
            }
        ],
        "candidates": [
            {
                "candidate": {
                    "signal_fingerprint": signal,
                    "qore_symbol": "GBPUSD",
                    "provider_symbol": "GBPUSD",
                    "trader_id": TraderLineage.R43_GBPUSD.value,
                },
                "provider_evidence_id": "provider-snapshot-1",
                "opportunity": {
                    "trader_id": TraderLineage.R43_GBPUSD.value,
                    "signal_fingerprint": signal,
                    "qore_symbol": "GBPUSD",
                    "provider_symbol": "GBPUSD",
                    "side": "long",
                    "entry_type": "MARKET",
                    "intended_entry": "100",
                    "stop_loss": "99",
                    "take_profit": "102",
                    "stop_loss_per_volume": "100",
                    "margin_per_volume": "50",
                    "volume_step": "0.01",
                    "minimum_volume": "0.01",
                    "maximum_volume": "100",
                    "minimum_execution_steps": 1,
                    "decision_context": [],
                },
                "provider_observation": {
                    "provider_key": "CTRADER_DEMO",
                    "qore_symbol": "GBPUSD",
                    "provider_symbol": "GBPUSD",
                    "bid": "99.99",
                    "ask": "100.01",
                    "contract_size": "100000",
                    "tick_size": "0.01",
                    "tick_value": "1",
                    "minimum_volume": "0.01",
                    "maximum_volume": "100",
                    "volume_step": "0.01",
                    "margin_per_volume": "50",
                    "commission_per_volume_usd": "0.5",
                    "slippage_reserve_per_volume_usd": "0",
                    "observed_at": (
                        decision_at - timedelta(milliseconds=100)
                    ).isoformat(),
                },
            }
        ],
    }
    decision = Phase20ForwardDecisionSeal(
        evidence_id="decision-1",
        decision_epoch_id="epoch-1",
        evidence_sha256="sha256:" + ("1" * 64),
        decision_at=decision_at,
        candidate_id="phase20-candidate",
        code_sha="a" * 40,
        parameter_sha256="sha256:" + ("b" * 64),
        signal_fingerprints=(signal,),
        canonical_payload_json=json.dumps(payload, sort_keys=True),
        collector_git_sha="c" * 40,
        sealed_at=decision_at + timedelta(milliseconds=100),
        seal_deadline_at=decision_at + timedelta(seconds=2),
    )
    risk = Phase20ExecutedRiskEvidence(
        evidence_id="executed-risk-1",
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=signal,
        qore_symbol="GBPUSD",
        provider_order_ref="order-1",
        side="long",
        position_id=101,
        authorized_source_volume=Decimal("0.01"),
        filled_source_volume=Decimal("0.01"),
        weighted_fill_price=Decimal("100"),
        intended_entry_price=Decimal("100"),
        structural_stop_price=Decimal("99"),
        stop_risk_per_volume_at_intended_entry_usd=Decimal("100"),
        executed_initial_stop_risk_usd=Decimal("1"),
        observed_at=decision_at + timedelta(seconds=1),
        fill_evidence_refs=("fill-1",),
        fill_reconciled=True,
        mutation_outcome_known=True,
        capital_deployed_at=decision_at + timedelta(milliseconds=500),
    )
    evidence = VersionedPhase20ForwardEvidenceBook(
        generation=1,
        decisions=(decision,),
        outcomes=(),
    )
    risks = VersionedPhase20ExecutedRiskBook(
        generation=1,
        evidences=(risk,),
    )
    return evidence, risks, signal


def test_t11_binds_realized_entry_commission_and_quoted_spread() -> None:
    evidence, risks, signal = _evidence()
    settlement = VersionedCmaSettlementBook(
        generation=1,
        states=(
            CmaSettlementState(
                signal_fingerprint=signal,
                position_id=101,
                records=(
                    CmaSettlementRecord(
                        event="CTRADER_DEMO_ENTRY_COST_SETTLEMENT",
                        deal_id=7001,
                        signal_fingerprint=signal,
                        position_id=101,
                        net_profit_usd=Decimal("-0.01"),
                        position_open_after=True,
                    ),
                ),
                position_closed=False,
            ),
        ),
    )

    audit = assess_phase20_t11_cost_binding(
        evidence_book=evidence,
        executed_risk_book=risks,
        settlement_book=settlement,
    )

    assert audit.execution_instances == 1
    assert audit.provider_spread_bound_instances == 1
    assert audit.settlement_bound_instances == 1
    assert audit.realized_entry_commission_instances == 1
    assert audit.total_predecision_quoted_spread_usd == Decimal("0.02")
    assert audit.total_realized_entry_commission_usd == Decimal("-0.01")
    assert audit.quoted_spread_coverage_complete is True
    assert audit.realized_entry_commission_coverage_complete is True
    assert audit.realized_spread_component_identified is False
    assert audit.execution_cost_model_ready is False
    assert "REALIZED_SPREAD_COMPONENT_NOT_SEPARATELY_IDENTIFIED" in audit.blockers


def test_t11_cost_binding_fails_closed_when_commission_settlement_missing() -> None:
    evidence, risks, signal = _evidence()
    settlement = VersionedCmaSettlementBook(
        generation=0,
        states=(
            CmaSettlementState(
                signal_fingerprint=signal,
                position_id=101,
            ),
        ),
    )

    audit = assess_phase20_t11_cost_binding(
        evidence_book=evidence,
        executed_risk_book=risks,
        settlement_book=settlement,
    )

    assert audit.provider_spread_bound_instances == 1
    assert audit.realized_entry_commission_instances == 0
    assert audit.realized_entry_commission_coverage_complete is False
    assert (
        "T11_REALIZED_ENTRY_COMMISSION_COVERAGE_INCOMPLETE:0/1"
        in audit.blockers
    )


def test_t11_cost_binding_excludes_non_forward_executions() -> None:
    evidence, risks, signal = _evidence()
    fresh = risks.evidences[0]
    legacy = Phase20ExecutedRiskEvidence(
        evidence_id="executed-risk-legacy",
        decision_evidence_sha256="sha256:" + ("2" * 64),
        signal_fingerprint="legacy-signal",
        qore_symbol="GBPUSD",
        provider_order_ref="legacy-order",
        side="long",
        position_id=202,
        authorized_source_volume=Decimal("0.01"),
        filled_source_volume=Decimal("0.01"),
        weighted_fill_price=Decimal("100"),
        intended_entry_price=Decimal("100"),
        structural_stop_price=Decimal("99"),
        stop_risk_per_volume_at_intended_entry_usd=Decimal("100"),
        executed_initial_stop_risk_usd=Decimal("1"),
        observed_at=BASE + timedelta(seconds=1),
        fill_evidence_refs=("legacy-fill",),
        fill_reconciled=True,
        mutation_outcome_known=True,
        capital_deployed_at=BASE + timedelta(milliseconds=500),
    )
    risks = VersionedPhase20ExecutedRiskBook(
        generation=2,
        evidences=(fresh, legacy),
    )
    settlement = VersionedCmaSettlementBook(
        generation=1,
        states=(
            CmaSettlementState(
                signal_fingerprint=signal,
                position_id=101,
                records=(
                    CmaSettlementRecord(
                        event="CTRADER_DEMO_ENTRY_COST_SETTLEMENT",
                        deal_id=7002,
                        signal_fingerprint=signal,
                        position_id=101,
                        net_profit_usd=Decimal("-0.01"),
                        position_open_after=True,
                    ),
                ),
                position_closed=False,
            ),
        ),
    )

    audit = assess_phase20_t11_cost_binding(
        evidence_book=evidence,
        executed_risk_book=risks,
        settlement_book=settlement,
    )

    assert audit.execution_instances == 1
    assert audit.unbound_execution_instances == 0
    assert audit.realized_entry_commission_instances == 1
