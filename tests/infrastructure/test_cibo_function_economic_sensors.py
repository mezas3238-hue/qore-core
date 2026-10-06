from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_function_economic_sensors import (
    CiboFunctionEconomicSensor,
    CiboSensorCausalState,
    summarize_function_sensors,
)


def _sensor(
    *,
    decision_id: str,
    function_code: str,
    gate: bool = False,
    ablation_key: str | None = None,
    risk_delta: Decimal = Decimal("0"),
) -> CiboFunctionEconomicSensor:
    return CiboFunctionEconomicSensor(
        decision_id=decision_id,
        function_code=function_code,
        stage_order=1,
        input_sha256="sha256:" + "a" * 64,
        output_sha256="sha256:" + "b" * 64,
        input_metrics=(("input", "1"),),
        output_metrics=(("output", "2"),),
        called=True,
        downstream_consumed=True,
        decision_gate_triggered=gate,
        risk_delta_usd=risk_delta,
        margin_delta_usd=Decimal("0"),
        ablation_key=ablation_key,
        causal_state=CiboSensorCausalState.UNPROVEN,
        causal_ending_capital_delta_usd=None,
        productive_authority=False,
    )


def test_sensor_is_observational_and_cannot_claim_unproven_causal_pnl() -> None:
    sensor = _sensor(
        decision_id="d1",
        function_code="SIZING",
        ablation_key="sizing",
    )

    assert sensor.productive_authority is False
    assert sensor.causal_state is CiboSensorCausalState.UNPROVEN
    assert sensor.causal_ending_capital_delta_usd is None

    with pytest.raises(CiboCapitalManagementError):
        CiboFunctionEconomicSensor(
            decision_id="d1",
            function_code="SIZING",
            stage_order=1,
            input_sha256="sha256:" + "a" * 64,
            output_sha256="sha256:" + "b" * 64,
            input_metrics=(("input", "1"),),
            output_metrics=(("output", "2"),),
            ablation_key="sizing",
            causal_state=CiboSensorCausalState.UNPROVEN,
            causal_ending_capital_delta_usd=Decimal("10"),
        )


def test_sensor_summary_separates_activity_from_ablation_economics() -> None:
    sensors = (
        _sensor(
            decision_id="d1",
            function_code="SIZING",
            gate=True,
            ablation_key="sizing",
            risk_delta=Decimal("-2"),
        ),
        _sensor(
            decision_id="d2",
            function_code="SIZING",
            gate=False,
            ablation_key="sizing",
            risk_delta=Decimal("3"),
        ),
        _sensor(
            decision_id="d1",
            function_code="COGNITION",
            gate=False,
            ablation_key="cognition",
        ),
    )

    summary = summarize_function_sensors(
        sensors,
        full_ending_capital_usd=Decimal("1141.70"),
        ablation_ending_capital_usd={
            "sizing": Decimal("1000"),
            "cognition": Decimal("1100"),
        },
    )

    sizing = summary["function_summary"]["SIZING"]
    assert sizing["call_count"] == 2
    assert sizing["downstream_consumed_count"] == 2
    assert sizing["decision_gate_triggered_count"] == 1
    assert sizing["risk_delta_usd"] == "1"

    causal = summary["causal_ablation_summary"]
    assert causal["sizing"]["causal_state"] == "ABLATION_PROVEN"
    assert causal["sizing"]["delta_ending_capital_vs_full_usd"] == "141.70"
    assert causal["cognition"]["delta_ending_capital_vs_full_usd"] == "41.70"
    assert causal["adaptive_leverage"]["causal_state"] == "UNPROVEN"
    assert (
        summary[
            "causal_deltas_are_group_level_not_additive_across_member_sensors"
        ]
        is True
    )
    assert summary["productive_authority"] is False


def test_sensor_rejects_productive_authority() -> None:
    with pytest.raises(CiboCapitalManagementError):
        CiboFunctionEconomicSensor(
            decision_id="d1",
            function_code="BAD_SENSOR",
            stage_order=1,
            input_sha256="sha256:" + "a" * 64,
            output_sha256="sha256:" + "b" * 64,
            input_metrics=(("input", "1"),),
            output_metrics=(("output", "2"),),
            productive_authority=True,
        )
