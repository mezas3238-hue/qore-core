"""Bind remaining A1 CE2I economic gates to the canonical Phase22 folds.

This layer covers T04/T10 economic observations plus the existing strict
temporal gates for T06/T07 and T14/T15. It does not alter their frozen
economics. It only proves that their WF1..WF4 populations are exactly the same
ones named by the A1 Phase22 scientific-consumption manifest.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_a1_phase22_scientific_consumption import (
    A1Phase22ScientificConsumptionManifest,
)
from qore.infrastructure.cibo_ce2i_t04_t10_economic_gate import (
    Ce2iT04T10EconomicGateReport,
    Ce2iT04T10FoldObservation,
    evaluate_t04_t10_economic_gate,
)
from qore.infrastructure.cibo_ce2i_temporal_utility_replication import (
    CausalParetoTemporalFoldEvidence,
    Ce2iTemporalReplicationReport,
    ExpansionTemporalFoldEvidence,
    evaluate_expansion_temporal_replication,
    evaluate_t14_t15_temporal_replication,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

GATE_ID = "CIBO_A1_CE2I_PHASE22_POPULATION_BINDING_V1"
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")


@dataclass(frozen=True, slots=True)
class A1T04T10Phase22BindingReport:
    gate_id: str
    manifest_sha256: str
    economic_gate: Ce2iT04T10EconomicGateReport
    exact_fold_population_binding: bool
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCompoundCapitalError(
                "T04/T10 Phase22 binding gate identity drift"
            )
        _sha(self.manifest_sha256)
        if not isinstance(
            self.economic_gate,
            Ce2iT04T10EconomicGateReport,
        ):
            raise CiboCompoundCapitalError(
                "T04/T10 Phase22 binding requires canonical economic gate"
            )
        if not self.exact_fold_population_binding:
            raise CiboCompoundCapitalError(
                "T04/T10 Phase22 fold population binding must be exact"
            )
        if self.productive_authority or self.certification_ready:
            raise CiboCompoundCapitalError(
                "T04/T10 Phase22 binding grants no authority"
            )


@dataclass(frozen=True, slots=True)
class A1Ce2iTemporalPhase22BindingReport:
    gate_id: str
    manifest_sha256: str
    family: str
    replication: Ce2iTemporalReplicationReport
    exact_fold_population_binding: bool
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCompoundCapitalError(
                "A1 CE2I temporal Phase22 binding gate identity drift"
            )
        _sha(self.manifest_sha256)
        if self.family not in {"T06_T07", "T14_T15"}:
            raise CiboCompoundCapitalError(
                "A1 CE2I temporal Phase22 binding family invalid"
            )
        if not isinstance(self.replication, Ce2iTemporalReplicationReport):
            raise CiboCompoundCapitalError(
                "A1 CE2I temporal Phase22 binding requires canonical replication"
            )
        if self.replication.family != self.family:
            raise CiboCompoundCapitalError(
                "A1 CE2I temporal family/report drift"
            )
        if not self.exact_fold_population_binding:
            raise CiboCompoundCapitalError(
                "A1 CE2I temporal Phase22 binding must be exact"
            )
        if self.productive_authority or self.certification_ready:
            raise CiboCompoundCapitalError(
                "A1 CE2I temporal Phase22 binding grants no authority"
            )


def bind_t04_t10_to_phase22(
    *,
    manifest: A1Phase22ScientificConsumptionManifest,
    observations: tuple[Ce2iT04T10FoldObservation, ...],
) -> A1T04T10Phase22BindingReport:
    """Evaluate T04/T10 only on the exact canonical Phase22 fold populations."""

    _manifest(manifest)
    if not observations:
        raise CiboCompoundCapitalError(
            "T04/T10 Phase22 binding requires observations"
        )
    populations = {
        item.fold_id: item.population_sha256 for item in manifest.folds
    }
    for observation in observations:
        expected = populations.get(observation.fold_id)
        if expected is None or observation.population_sha256 != expected:
            raise CiboCompoundCapitalError(
                "T04/T10 observation population differs from Phase22 fold"
            )

    report = evaluate_t04_t10_economic_gate(observations)
    return A1T04T10Phase22BindingReport(
        gate_id=GATE_ID,
        manifest_sha256=manifest.fingerprint(),
        economic_gate=report,
        exact_fold_population_binding=True,
    )


def bind_t06_t07_temporal_to_phase22(
    *,
    manifest: A1Phase22ScientificConsumptionManifest,
    treatment_candidate_id: str,
    folds: tuple[ExpansionTemporalFoldEvidence, ...],
) -> A1Ce2iTemporalPhase22BindingReport:
    """Bind the frozen T06/T07 strict replication to Phase22 WF1..WF4."""

    _manifest(manifest)
    _expansion_fold_binding(manifest, folds)
    report = evaluate_expansion_temporal_replication(
        treatment_candidate_id=treatment_candidate_id,
        folds=folds,
    )
    return A1Ce2iTemporalPhase22BindingReport(
        gate_id=GATE_ID,
        manifest_sha256=manifest.fingerprint(),
        family="T06_T07",
        replication=report,
        exact_fold_population_binding=True,
    )


def bind_t14_t15_temporal_to_phase22(
    *,
    manifest: A1Phase22ScientificConsumptionManifest,
    treatment_candidate_id: str,
    folds: tuple[CausalParetoTemporalFoldEvidence, ...],
) -> A1Ce2iTemporalPhase22BindingReport:
    """Bind the frozen T14/T15 strict replication to Phase22 WF1..WF4."""

    _manifest(manifest)
    _pareto_fold_binding(manifest, folds)
    report = evaluate_t14_t15_temporal_replication(
        treatment_candidate_id=treatment_candidate_id,
        folds=folds,
    )
    return A1Ce2iTemporalPhase22BindingReport(
        gate_id=GATE_ID,
        manifest_sha256=manifest.fingerprint(),
        family="T14_T15",
        replication=report,
        exact_fold_population_binding=True,
    )


def _expansion_fold_binding(
    manifest: A1Phase22ScientificConsumptionManifest,
    folds: tuple[ExpansionTemporalFoldEvidence, ...],
) -> None:
    by_id = {item.fold_id: item for item in folds}
    if len(folds) != 4 or tuple(sorted(by_id)) != _CANONICAL_FOLDS:
        raise CiboCompoundCapitalError(
            "T06/T07 Phase22 binding requires exactly WF1..WF4"
        )
    expected = {
        item.fold_id: item.population_sha256 for item in manifest.folds
    }
    for fold_id in _CANONICAL_FOLDS:
        if by_id[fold_id].gate_report.population_sha256 != expected[fold_id]:
            raise CiboCompoundCapitalError(
                "T06/T07 population differs from canonical Phase22 fold"
            )


def _pareto_fold_binding(
    manifest: A1Phase22ScientificConsumptionManifest,
    folds: tuple[CausalParetoTemporalFoldEvidence, ...],
) -> None:
    by_id = {item.fold_id: item for item in folds}
    if len(folds) != 4 or tuple(sorted(by_id)) != _CANONICAL_FOLDS:
        raise CiboCompoundCapitalError(
            "T14/T15 Phase22 binding requires exactly WF1..WF4"
        )
    expected = {
        item.fold_id: item.population_sha256 for item in manifest.folds
    }
    for fold_id in _CANONICAL_FOLDS:
        if by_id[fold_id].gate_report.population_sha256 != expected[fold_id]:
            raise CiboCompoundCapitalError(
                "T14/T15 population differs from canonical Phase22 fold"
            )


def _manifest(value: A1Phase22ScientificConsumptionManifest) -> None:
    if not isinstance(value, A1Phase22ScientificConsumptionManifest):
        raise CiboCompoundCapitalError(
            "A1 CE2I Phase22 binding requires canonical A1 manifest"
        )


def _sha(value: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            "A1 CE2I Phase22 binding manifest SHA invalid"
        )
