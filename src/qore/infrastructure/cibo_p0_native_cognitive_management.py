"""P0 RESEARCH adapter: native CIBO cognitive sensor evidence -> economic plan.

A deterministic translation of REAL causal native sensor states, NOT native
authorization of a broker order or proof of managed price-path execution.
Legacy capital_disposition is NEVER an input to the management decision.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation


class NativeCognitiveManagementError(ValueError):
    pass


def _sensor(row: dict, code: str) -> tuple[dict, dict]:
    sensors = row.get("cognitive_sensors")
    if not isinstance(sensors, list):
        raise NativeCognitiveManagementError("native cognitive sensor list missing")
    matches = [x for x in sensors if isinstance(x, dict) and x.get("component_code") == code]
    if len(matches) != 1 or matches[0].get("native_output_consumed") is not True:
        raise NativeCognitiveManagementError(f"native {code} evidence missing/not consumed")
    found = matches[0]
    try:
        inputs = dict(found["input_metrics"])
        outputs = dict(found["output_metrics"])
    except (TypeError, ValueError, KeyError) as exc:
        raise NativeCognitiveManagementError(f"native {code} metrics invalid") from exc
    return inputs, outputs


def _decimal(raw: object, name: str) -> Decimal:
    try:
        n = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise NativeCognitiveManagementError(f"{name} invalid") from exc
    if not n.is_finite():
        raise NativeCognitiveManagementError(f"{name} non-finite")
    return n


def native_sensor_management_plan(row: dict) -> dict:
    """Build one non-veto paper plan using calibration, routing, scenarios and audit.

    The native brain supplies observations; this transparent research adapter
    maps them to a maximum *requested* all-in risk <= 5% NAV. Physical QDLE,
    portfolio solvency, margin, fees and stop validation still constrain lots.
    """
    _, cal = _sensor(row, "CALIBRATION")
    _, routing = _sensor(row, "REASONING_ROUTING")
    _, scenarios = _sensor(row, "SCENARIO_ENGINE")
    _, meta = _sensor(row, "METACOGNITION")
    _, causal = _sensor(row, "CAUSAL_REASONING")
    _, synthesis = _sensor(row, "EXECUTIVE_SYNTHESIS")
    confidence = _decimal(cal.get("confidence_band"), "confidence_band")
    if not Decimal(0) <= confidence <= Decimal(100):
        raise NativeCognitiveManagementError("confidence_band outside 0..100")
    if cal.get("abstention_required") not in ("True", "False"):
        raise NativeCognitiveManagementError("native calibration abstention flag invalid")
    count = _decimal(scenarios.get("scenario_count"), "scenario_count")
    if count < 1 or count != count.to_integral_value():
        raise NativeCognitiveManagementError("native scenario coverage missing")
    evidence_sufficiency = meta.get("evidence_sufficiency")
    if not evidence_sufficiency or not routing.get("decision") or not causal.get("status"):
        raise NativeCognitiveManagementError("native uncertainty/causality evidence missing")
    if not synthesis.get("directive") or not synthesis.get("uncertainty"):
        raise NativeCognitiveManagementError("native executive synthesis missing")
    abstain = cal["abstention_required"] == "True"
    challenged = evidence_sufficiency != "sufficient"
    if abstain or challenged or confidence < 34:
        mode = "BANK"
        risk_share = Decimal("0.25")
    elif confidence < 67:
        mode = "MEDIUM"
        risk_share = Decimal("0.50")
    else:
        mode = "ATTACK"
        risk_share = Decimal("1.00")
    # Never an admission gate: even abstaining cognitive evidence yields
    # an economic management request (subject to physical QDLE feasibility).
    template = {
        "BANK": ("0.75", "0.75", "1.1", "0.5", "-0.35"),
        "MEDIUM": ("1", "1", "1.5", "0.75", "-0.5"),
        "ATTACK": ("1.5", "1.5", "2", "1", "-0.75"),
    }[mode]
    exit_policy = dict(zip(
        ("partial_at_r", "breakeven_at_r", "trailing_activate_at_r",
         "trailing_distance_r", "defensive_close_at_r"), template
    ))
    risk_fraction = Decimal("0.05") * risk_share
    return {
        "mode": mode,
        "requested_risk_fraction_of_current_qore_nav": format(risk_fraction, "f"),
        "exit_policy_SHADOW": exit_policy,
        "native_confidence_band": format(confidence, "f"),
        "native_calibration_abstention": abstain,
        "native_reasoning_route": routing["decision"],
        "native_metacognitive_evidence_sufficiency": evidence_sufficiency,
        "native_causal_status": causal["status"],
        "native_scenario_count": int(count),
        "native_executive_directive": synthesis["directive"],
        "native_executive_uncertainty": synthesis["uncertainty"],
        "producer": "P0_DETERMINISTIC_SENSOR_DERIVED_RESEARCH_ADAPTER_NOT_NATIVE_BROKER_AUTHORIZATION",
        "native_disposition_used_for_policy": False,
        "risk_fraction_is_upper_request_not_guaranteed_executable_volume": True,
        "exit_policy_actually_executed": False,
    }
