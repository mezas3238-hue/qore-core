from qore.infrastructure.cibo_phase22_dual_evidence_plan import (
    PHASE22_DUAL_EVIDENCE_PLAN,
    phase22_dual_evidence_plan_payload,
)
from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT,
)


def test_composed_provider_execution_calibration_is_ready() -> None:
    receipt = PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT

    assert receipt.execution_population_ready is True
    assert receipt.empirical_slippage_calibrated is True
    assert receipt.execution_model_ready is True
    assert receipt.created_positions_closed is True
    assert receipt.minimum_volume_only is True
    assert receipt.blockers == ()
    assert dict(receipt.population_entry_orders_by_symbol) == {
        "AUDJPY": 12,
        "EURUSD": 8,
        "GBPJPY": 8,
        "GBPUSD": 8,
        "NAS100": 8,
        "XAUUSD": 8,
    }
    assert dict(receipt.empirical_orders_by_symbol) == {
        "AUDJPY": 12,
        "EURUSD": 9,
        "GBPJPY": 8,
        "GBPUSD": 8,
        "NAS100": 8,
        "XAUUSD": 8,
    }


def test_dual_evidence_plan_is_stricter_and_provider_ready() -> None:
    plan = PHASE22_DUAL_EVIDENCE_PLAN

    assert plan.provider_execution_calibration_sha256 == (
        PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
    )
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
