"""Architect-A admission gate for mechanism-specific adversarial stress.

This gate does not simulate stress and does not replace any economic gate.
Instead it defines the evidence law for admitting stress results: every frozen
CIBO adversarial stress kind must be preregistered, must preserve one control
and treatment identity, and must pass the mechanism's own frozen economic gate.
No scenario can rescue another and no production authority is granted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_adaptive_compound_speed_economic_gate import (
    GENC8_ECONOMIC_GATE_ID,
)
from qore.infrastructure.cibo_compound_adversarial_stress import (
    CompoundStressKind,
    CompoundStressScenario,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_ce2i_t04_t10_economic_gate import (
    GATE_ID as T04_T10_ECONOMIC_GATE_ID,
)
from qore.infrastructure.cibo_expansion_utility_gate import (
    EXPANSION_UTILITY_GATE_ID,
)
from qore.infrastructure.cibo_genc11_genc13_utility_gate import (
    GATE_ID as GENC11_GENC13_UTILITY_GATE_ID,
)
from qore.infrastructure.cibo_genc12_economic_gate import (
    GENC12_ECONOMIC_GATE_ID,
)
from qore.infrastructure.cibo_profit_preservation_economic_gate import (
    GENC7_ECONOMIC_GATE_ID,
)
from qore.infrastructure.cibo_t14_t15_utility_gate import (
    T14_T15_UTILITY_GATE_ID,
)

GATE_ID = "CIBO_ARCH_A_MECHANISM_ADVERSARIAL_STRESS_ADMISSION_V1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PASS_STATUS = "ELIGIBLE_FOR_FURTHER_RESEARCH"
_REQUIRED_STRESS_KINDS = tuple(CompoundStressKind)


class MechanismStressWorkstream(StrEnum):
    T04 = "T04"
    T06 = "T06"
    T07 = "T07"
    T10 = "T10"
    T14 = "T14"
    T15 = "T15"
    GENC7 = "GEN-C7"
    GENC8 = "GEN-C8"
    GENC11 = "GEN-C11"
    GENC12 = "GEN-C12"
    GENC13 = "GEN-C13"


_SOURCE_GATE_BY_WORKSTREAM = {
    MechanismStressWorkstream.T04: T04_T10_ECONOMIC_GATE_ID,
    MechanismStressWorkstream.T06: EXPANSION_UTILITY_GATE_ID,
    MechanismStressWorkstream.T07: EXPANSION_UTILITY_GATE_ID,
    MechanismStressWorkstream.T10: T04_T10_ECONOMIC_GATE_ID,
    MechanismStressWorkstream.T14: T14_T15_UTILITY_GATE_ID,
    MechanismStressWorkstream.T15: T14_T15_UTILITY_GATE_ID,
    MechanismStressWorkstream.GENC7: GENC7_ECONOMIC_GATE_ID,
    MechanismStressWorkstream.GENC8: GENC8_ECONOMIC_GATE_ID,
    MechanismStressWorkstream.GENC11: GENC11_GENC13_UTILITY_GATE_ID,
    MechanismStressWorkstream.GENC12: GENC12_ECONOMIC_GATE_ID,
    MechanismStressWorkstream.GENC13: GENC11_GENC13_UTILITY_GATE_ID,
}


class MechanismStressVerdict(StrEnum):
    STRESS_ROBUST = "STRESS_ROBUST"
    FALSIFIED = "FALSIFIED"


@dataclass(frozen=True, slots=True)
class MechanismStressObservation:
    workstream: MechanismStressWorkstream
    scenario: CompoundStressScenario
    source_gate_id: str
    source_gate_evidence_sha256: str
    stressed_population_sha256: str
    protocol_binding_sha256: str
    control_candidate_id: str
    treatment_candidate_id: str
    source_gate_status: str
    failed_dimensions: tuple[str, ...]
    scenario_preregistered_before_outcomes: bool
    stress_transform_non_improving: bool
    control_unchanged: bool
    treatment_unchanged: bool
    future_outcome_used: bool = False
    weighted_score_used: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if type(self.workstream) is not MechanismStressWorkstream:
            raise CiboCompoundCapitalError(
                "mechanism stress workstream is invalid"
            )
        if not isinstance(self.scenario, CompoundStressScenario):
            raise CiboCompoundCapitalError(
                "mechanism stress requires canonical Compound stress scenario"
            )
        expected_gate = _SOURCE_GATE_BY_WORKSTREAM[self.workstream]
        if self.source_gate_id != expected_gate:
            raise CiboCompoundCapitalError(
                "mechanism stress source gate identity drift"
            )
        for name in (
            "source_gate_evidence_sha256",
            "stressed_population_sha256",
            "protocol_binding_sha256",
        ):
            _sha(getattr(self, name), name)
        if (
            not self.control_candidate_id
            or not self.treatment_candidate_id
            or self.control_candidate_id == self.treatment_candidate_id
        ):
            raise CiboCompoundCapitalError(
                "mechanism stress control/treatment identity is invalid"
            )
        if not self.source_gate_status:
            raise CiboCompoundCapitalError(
                "mechanism stress source gate status is required"
            )
        if len(self.failed_dimensions) != len(set(self.failed_dimensions)):
            raise CiboCompoundCapitalError(
                "mechanism stress failed dimensions must be unique"
            )
        for name in (
            "scenario_preregistered_before_outcomes",
            "stress_transform_non_improving",
            "control_unchanged",
            "treatment_unchanged",
            "future_outcome_used",
            "weighted_score_used",
            "productive_authority",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"mechanism stress {name} must be bool"
                )
        if (
            not self.scenario_preregistered_before_outcomes
            or not self.stress_transform_non_improving
            or not self.control_unchanged
            or not self.treatment_unchanged
            or self.future_outcome_used
            or self.weighted_score_used
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "mechanism stress governance drift"
            )


@dataclass(frozen=True, slots=True)
class MechanismStressScenarioResult:
    scenario_kind: CompoundStressKind
    scenario_id: str
    passed: bool
    source_gate_status: str
    failed_dimensions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MechanismStressGateReport:
    gate_id: str
    workstream: MechanismStressWorkstream
    source_gate_id: str
    control_candidate_id: str
    treatment_candidate_id: str
    protocol_binding_sha256: str
    scenario_results: tuple[MechanismStressScenarioResult, ...]
    verdict: MechanismStressVerdict
    all_required_stress_kinds_present: bool = True
    cross_scenario_compensation_allowed: bool = False
    winner_selected_after_outcomes: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCompoundCapitalError(
                "mechanism stress admission gate identity drift"
            )
        if self.source_gate_id != _SOURCE_GATE_BY_WORKSTREAM[self.workstream]:
            raise CiboCompoundCapitalError(
                "mechanism stress report source-gate drift"
            )
        _sha(self.protocol_binding_sha256, "protocol_binding_sha256")
        kinds = tuple(item.scenario_kind for item in self.scenario_results)
        if kinds != _REQUIRED_STRESS_KINDS:
            raise CiboCompoundCapitalError(
                "mechanism stress report requires canonical stress-kind order"
            )
        expected = all(item.passed for item in self.scenario_results)
        if (
            (self.verdict is MechanismStressVerdict.STRESS_ROBUST)
            != expected
        ):
            raise CiboCompoundCapitalError(
                "mechanism stress verdict/result mismatch"
            )
        if (
            not self.all_required_stress_kinds_present
            or self.cross_scenario_compensation_allowed
            or self.winner_selected_after_outcomes
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "mechanism stress report governance drift"
            )


def evaluate_mechanism_stress_admission(
    observations: tuple[MechanismStressObservation, ...],
) -> MechanismStressGateReport:
    """Require every frozen stress kind to pass the mechanism's source gate."""

    if not observations:
        raise CiboCompoundCapitalError(
            "mechanism stress observations are required"
        )
    workstreams = {item.workstream for item in observations}
    source_gates = {item.source_gate_id for item in observations}
    controls = {item.control_candidate_id for item in observations}
    treatments = {item.treatment_candidate_id for item in observations}
    protocols = {item.protocol_binding_sha256 for item in observations}

    if (
        len(workstreams) != 1
        or len(source_gates) != 1
        or len(controls) != 1
        or len(treatments) != 1
        or len(protocols) != 1
    ):
        raise CiboCompoundCapitalError(
            "mechanism stress comparison identity drift"
        )

    by_kind = {item.scenario.kind: item for item in observations}
    if (
        len(observations) != len(_REQUIRED_STRESS_KINDS)
        or set(by_kind) != set(_REQUIRED_STRESS_KINDS)
    ):
        raise CiboCompoundCapitalError(
            "mechanism stress requires every frozen adversarial stress kind"
        )
    scenario_ids = tuple(item.scenario.scenario_id for item in observations)
    if len(scenario_ids) != len(set(scenario_ids)):
        raise CiboCompoundCapitalError(
            "mechanism stress scenario ids must be unique"
        )
    stress_populations = {
        item.stressed_population_sha256 for item in observations
    }
    if len(stress_populations) != len(_REQUIRED_STRESS_KINDS):
        raise CiboCompoundCapitalError(
            "mechanism stress scenarios require distinct stressed populations"
        )

    results: list[MechanismStressScenarioResult] = []
    for kind in _REQUIRED_STRESS_KINDS:
        item = by_kind[kind]
        passed = (
            item.source_gate_status == _PASS_STATUS
            and not item.failed_dimensions
        )
        results.append(
            MechanismStressScenarioResult(
                scenario_kind=kind,
                scenario_id=item.scenario.scenario_id,
                passed=passed,
                source_gate_status=item.source_gate_status,
                failed_dimensions=item.failed_dimensions,
            )
        )

    verdict = (
        MechanismStressVerdict.STRESS_ROBUST
        if all(item.passed for item in results)
        else MechanismStressVerdict.FALSIFIED
    )
    first = observations[0]
    return MechanismStressGateReport(
        gate_id=GATE_ID,
        workstream=first.workstream,
        source_gate_id=first.source_gate_id,
        control_candidate_id=first.control_candidate_id,
        treatment_candidate_id=first.treatment_candidate_id,
        protocol_binding_sha256=first.protocol_binding_sha256,
        scenario_results=tuple(results),
        verdict=verdict,
    )


def _sha(value: str, name: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"mechanism stress {name} must be canonical SHA-256"
        )
