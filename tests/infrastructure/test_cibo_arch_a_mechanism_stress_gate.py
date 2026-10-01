from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_arch_a_mechanism_stress_gate import (
    MechanismStressObservation,
    MechanismStressVerdict,
    MechanismStressWorkstream,
    evaluate_mechanism_stress_admission,
)
from qore.infrastructure.cibo_compound_adversarial_stress import (
    CompoundStressKind,
    CompoundStressScenario,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_expansion_utility_gate import (
    EXPANSION_UTILITY_GATE_ID,
)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _scenario(
    kind: CompoundStressKind,
    index: int,
) -> CompoundStressScenario:
    return CompoundStressScenario(
        scenario_id=f"{kind.value}-{index}",
        kind=kind,
        severity=Decimal("1"),
        evidence_sha256=_sha(hex(index + 1)[2:]),
    )


def _observations() -> tuple[MechanismStressObservation, ...]:
    return tuple(
        MechanismStressObservation(
            workstream=MechanismStressWorkstream.T06,
            scenario=_scenario(kind, index),
            source_gate_id=EXPANSION_UTILITY_GATE_ID,
            source_gate_evidence_sha256=_sha("a"),
            stressed_population_sha256=_sha(str(index + 1)),
            protocol_binding_sha256=_sha("b"),
            control_candidate_id="control",
            treatment_candidate_id="treatment",
            source_gate_status="ELIGIBLE_FOR_FURTHER_RESEARCH",
            failed_dimensions=(),
            scenario_preregistered_before_outcomes=True,
            stress_transform_non_improving=True,
            control_unchanged=True,
            treatment_unchanged=True,
        )
        for index, kind in enumerate(CompoundStressKind)
    )


def test_every_frozen_stress_kind_can_pass_without_granting_authority() -> None:
    report = evaluate_mechanism_stress_admission(_observations())

    assert report.verdict is MechanismStressVerdict.STRESS_ROBUST
    assert len(report.scenario_results) == len(tuple(CompoundStressKind))
    assert report.cross_scenario_compensation_allowed is False
    assert report.productive_authority is False
    assert report.certification_ready is False


def test_one_failed_stress_kind_falsifies_whole_mechanism() -> None:
    rows = list(_observations())
    rows[3] = replace(
        rows[3],
        source_gate_status="REJECTED_SAFETY_DETERIORATION",
        failed_dimensions=("maximum_drawdown_usd",),
    )

    report = evaluate_mechanism_stress_admission(tuple(rows))

    assert report.verdict is MechanismStressVerdict.FALSIFIED
    assert report.scenario_results[3].passed is False


def test_missing_stress_kind_is_illegal() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="every frozen adversarial stress kind",
    ):
        evaluate_mechanism_stress_admission(_observations()[:-1])


def test_source_gate_identity_is_fixed_by_workstream() -> None:
    row = _observations()[0]

    with pytest.raises(
        CiboCompoundCapitalError,
        match="source gate identity drift",
    ):
        replace(row, source_gate_id="WRONG_GATE")


def test_cross_scenario_protocol_drift_is_illegal() -> None:
    rows = list(_observations())
    rows[2] = replace(rows[2], protocol_binding_sha256=_sha("c"))

    with pytest.raises(
        CiboCompoundCapitalError,
        match="comparison identity drift",
    ):
        evaluate_mechanism_stress_admission(tuple(rows))


def test_t07_reuses_expansion_source_gate() -> None:
    row = _observations()[0]
    clone = replace(
        row,
        workstream=MechanismStressWorkstream.T07,
        source_gate_id=EXPANSION_UTILITY_GATE_ID,
    )
    assert clone.workstream is MechanismStressWorkstream.T07
