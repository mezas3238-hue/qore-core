from qore.infrastructure.cibo_phase22_demo_empirical_provider_receipt import (
    ARTIFACT_DIGEST as EMPIRICAL_ARTIFACT_DIGEST,
)
from qore.infrastructure.cibo_phase22_demo_empirical_provider_receipt import (
    ARTIFACT_ID as EMPIRICAL_ARTIFACT_ID,
)
from qore.infrastructure.cibo_phase22_demo_empirical_provider_receipt import (
    PHASE22_DEMO_EMPIRICAL_PROVIDER_RECEIPT,
)
from qore.infrastructure.cibo_phase22_demo_empirical_provider_receipt import (
    RUN_ID as EMPIRICAL_RUN_ID,
)
from qore.infrastructure.cibo_phase22_demo_execution_population_receipt import (
    ARTIFACT_DIGEST,
    ARTIFACT_ID,
    PHASE22_DEMO_EXECUTION_POPULATION_RECEIPT,
    RUN_ID,
)
from qore.infrastructure.cibo_phase22_dual_evidence_plan import (
    PHASE22_DUAL_EVIDENCE_PLAN,
    phase22_dual_evidence_plan_payload,
)


def test_real_demo_execution_population_is_already_sufficient() -> None:
    receipt = PHASE22_DEMO_EXECUTION_POPULATION_RECEIPT

    assert RUN_ID == 36922694706
    assert ARTIFACT_ID == 11192332824
    assert ARTIFACT_DIGEST.startswith("sha256:")
    assert receipt.execution_population_ready is True
    assert receipt.causal_quote_reconstruction_ready is False
    assert dict(receipt.execution_counts) == {
        "AUDJPY": 12,
        "EURUSD": 8,
        "GBPJPY": 8,
        "GBPUSD": 8,
        "NAS100": 8,
        "XAUUSD": 8,
    }


def test_empirical_provider_receipt_is_causal_and_complete() -> None:
    receipt = PHASE22_DEMO_EMPIRICAL_PROVIDER_RECEIPT

    assert EMPIRICAL_RUN_ID == 36927602692
    assert EMPIRICAL_ARTIFACT_ID == 11194039517
    assert EMPIRICAL_ARTIFACT_DIGEST == (
        "sha256:5957a77cceb44c15319785aa26a1a057"
        "4fef46535ff7ce69fcec3757d02972c4"
    )
    assert receipt.qore_deals_found == 53
    assert receipt.observation_count == 53
    assert dict(receipt.distinct_orders_by_symbol) == {
        "AUDJPY": 12,
        "EURUSD": 9,
        "GBPJPY": 8,
        "GBPUSD": 8,
        "NAS100": 8,
        "XAUUSD": 8,
    }
    assert receipt.empirical_slippage_calibrated is True
    assert receipt.execution_model_ready is True
    assert receipt.blockers == ()
    assert receipt.broker_mutation_performed is False
    assert receipt.holdout_outcomes_used is False


def test_dual_evidence_plan_is_stricter_and_provider_ready() -> None:
    plan = PHASE22_DUAL_EVIDENCE_PLAN

    assert plan.protocol_frozen_before_holdout_outcomes is True
    assert plan.require_historical_holdout_market_plane is True
    assert plan.require_real_current_demo_execution_plane is True
    assert plan.require_empirical_causal_quote_slippage is True
    assert plan.forbid_historical_provider_fill_claims is True
    assert plan.forbid_historical_provider_order_refs is True
    assert plan.forbid_historical_provider_deal_refs is True
    assert plan.forbid_historical_provider_settlement_claims is True
    assert plan.forbid_synthetic_fill_evidence is True
    assert plan.forbid_holdout_mining is True
    assert plan.execution_population_ready is True
    assert plan.empirical_provider_calibration_ready is True
    assert plan.activation_ready is True

    payload = phase22_dual_evidence_plan_payload()
    assert payload["holdout_consumed"] is False
    assert payload["activation_disposition"] == "READY_TO_ACTIVATE"
