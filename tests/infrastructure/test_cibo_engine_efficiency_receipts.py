from decimal import Decimal

from qore.infrastructure.cibo_engine_efficiency_receipts import (
    build_engine_evidence_from_receipts,
)
from qore.infrastructure.cibo_engine_efficiency_sensor import (
    CiboEngineEfficiencyClass,
    measure_engine_efficiency,
)


def test_receipts_expose_called_but_unconsumed_engine() -> None:
    evidence = build_engine_evidence_from_receipts(
        engine_id="GEN-C10",
        receipts=(
            {
                "function_code": "GEN-C10",
                "native_engine_called": True,
                "native_engine_name": "GEN-C10",
                "downstream_consumer": "",
                "consumer_action": "",
                "decision_changed": False,
                "incremental_pnl_attribution_usd": "0",
                "risk_delta_usd": "0",
                "margin_delta_usd": "0",
            },
        ),
        eligible_count=1,
        opportunity_value_available_usd=Decimal("10"),
    )

    report = measure_engine_efficiency(evidence)

    assert evidence.invoked_count == 1
    assert evidence.output_consumed_count == 0
    assert report.engine_efficiency == Decimal("0")
    assert report.classification is CiboEngineEfficiencyClass.NEAR_ZERO


def test_receipts_expose_consumed_but_non_actuating_engine() -> None:
    evidence = build_engine_evidence_from_receipts(
        engine_id="T09",
        receipts=(
            {
                "tool_code": "T09",
                "engine_name": "allocate_competing_opportunities",
                "native_engine_called": True,
                "downstream_consumer": "allocator",
                "consumer_action": "competition-result-consumed",
                "decision_changed": False,
                "economic_effect_observable": False,
            },
        ),
        eligible_count=1,
        opportunity_value_available_usd=Decimal("5"),
    )

    report = measure_engine_efficiency(evidence)

    assert evidence.output_consumed_count == 1
    assert evidence.decision_changed_count == 0
    assert report.engine_efficiency == Decimal("0")


def test_receipts_capture_real_economic_effect() -> None:
    evidence = build_engine_evidence_from_receipts(
        engine_id="T14",
        receipts=(
            {
                "tool_code": "T14",
                "engine_name": "dynamic_derisk",
                "native_engine_called": True,
                "downstream_consumer": "portfolio",
                "consumer_action": "release-consumed",
                "decision_changed": True,
                "economic_effect_observable": True,
            },
        ),
        eligible_count=1,
        opportunity_value_available_usd=Decimal("5"),
        marginal_value_usd=Decimal("5"),
    )

    report = measure_engine_efficiency(evidence)

    assert evidence.economically_effective_count == 1
    assert report.engine_efficiency == Decimal("1")
    assert report.classification is CiboEngineEfficiencyClass.VALUE_ADD
