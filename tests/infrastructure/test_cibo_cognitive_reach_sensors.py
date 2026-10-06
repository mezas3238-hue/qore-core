from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_cognitive_reach_sensors import (
    CiboCognitiveContributionState,
    CiboCognitiveReachSensor,
    summarize_cognitive_reach_sensors,
)


def _sensor(
    *,
    decision_id: str,
    component_code: str,
    ablation_key: str,
    gate: bool = False,
    applicable: bool = True,
    called: bool = True,
) -> CiboCognitiveReachSensor:
    stages = (
        ("FACULTY_INPUT", "NATIVE_FACULTY_ENGINE", "EXECUTIVE_SYNTHESIS", "CAPITAL_DECISION")
        if called
        else ("FACULTY_INPUT", "EXECUTIVE_SYNTHESIS", "CAPITAL_DECISION")
    )
    return CiboCognitiveReachSensor(
        decision_id=decision_id,
        component_code=component_code,
        component_kind="FACULTY",
        stage_order=10,
        status="SUCCESS" if called else "JUSTIFIED_NOT_APPLICABLE",
        input_sha256="sha256:" + "a" * 64,
        output_sha256="sha256:" + "b" * 64,
        reached_stages=stages,
        downstream_consumer="cibo-functional-coordinator",
        component_ablation_key=ablation_key,
        native_engine_called=called,
        applicable=applicable,
        downstream_consumed=True,
        constraint_or_gate_emitted=gate,
        reached_executive_synthesis=True,
        reached_capital_decision=True,
        contribution_state=CiboCognitiveContributionState.UNPROVEN,
        causal_ending_capital_delta_usd=None,
        productive_authority=False,
    )


def test_cognitive_sensor_distinguishes_reach_from_causal_contribution() -> None:
    sensor = _sensor(
        decision_id="d1",
        component_code="CF01",
        ablation_key="cognition:cf01",
    )

    assert sensor.max_reached_stage == "CAPITAL_DECISION"
    assert sensor.downstream_consumed is True
    assert sensor.reached_capital_decision is True
    assert sensor.contribution_state is CiboCognitiveContributionState.UNPROVEN
    assert sensor.causal_ending_capital_delta_usd is None


def test_cognitive_summary_requires_individual_ablation_to_name_contributor() -> None:
    sensors = (
        _sensor(
            decision_id="d1",
            component_code="CF01",
            ablation_key="cognition:cf01",
        ),
        _sensor(
            decision_id="d2",
            component_code="CF01",
            ablation_key="cognition:cf01",
            gate=True,
        ),
        _sensor(
            decision_id="d1",
            component_code="CF02",
            ablation_key="cognition:cf02",
        ),
    )

    summary = summarize_cognitive_reach_sensors(
        sensors,
        full_ending_capital_usd=Decimal("1141.70"),
        global_cognition_ablation_ending_capital_usd=Decimal("900"),
        component_ablation_ending_capital_usd={
            "cognition:cf01": Decimal("1000"),
        },
    )

    cf01 = summary["components"]["CF01"]
    cf02 = summary["components"]["CF02"]

    assert cf01["event_count"] == 2
    assert cf01["constraint_or_gate_count"] == 1
    assert cf01["individual_contribution_state"] == "ABLATION_PROVEN"
    assert cf01["individual_delta_ending_capital_vs_full_usd"] == "141.70"

    assert cf02["individual_contribution_state"] == "UNPROVEN"
    assert cf02["individual_delta_ending_capital_vs_full_usd"] is None

    global_ablation = summary["global_cognition_ablation"]
    assert global_ablation["state"] == "ABLATION_PROVEN"
    assert global_ablation["delta_ending_capital_vs_full_usd"] == "241.70"
    assert global_ablation[
        "does_not_prove_individual_component_contribution"
    ] is True
    assert summary[
        "individual_component_ablation_required_for_who_contributes"
    ] is True


def test_non_applicable_cognitive_component_cannot_claim_native_execution() -> None:
    with pytest.raises(CiboCapitalManagementError):
        _sensor(
            decision_id="d1",
            component_code="CF08",
            ablation_key="cognition:cf08",
            applicable=False,
            called=True,
        )


def test_cognitive_sensor_cannot_acquire_productive_authority() -> None:
    with pytest.raises(CiboCapitalManagementError):
        CiboCognitiveReachSensor(
            decision_id="d1",
            component_code="WORLD_MODEL",
            component_kind="COGNITIVE_SUBSTRATE",
            stage_order=1,
            status="SUCCESS",
            input_sha256="sha256:" + "a" * 64,
            output_sha256="sha256:" + "b" * 64,
            reached_stages=("WORLD_MODEL", "CAPITAL_DECISION"),
            downstream_consumer="cibo-executive-brain",
            component_ablation_key="cognition:world_model",
            productive_authority=True,
        )
