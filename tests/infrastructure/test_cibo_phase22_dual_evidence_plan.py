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


def test_dual_evidence_plan_is_stricter_and_not_activated_early() -> None:
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
    assert plan.empirical_provider_calibration_ready is False
    assert plan.activation_ready is False

    payload = phase22_dual_evidence_plan_payload()
    assert payload["holdout_consumed"] is False
    assert payload["activation_disposition"] == (
        "WAITING_FOR_EMPIRICAL_PROVIDER_CALIBRATION"
    )
