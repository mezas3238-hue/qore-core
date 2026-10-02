"""Bind GEN-C3..GEN-C7 economic science to one A1 Phase22 population.

The economic gates already enforce non-compensatory causal comparisons. This
module closes a separate certification-integrity gap: a green gate is not
admissible for A1 if its populations do not match the canonical Phase22
scientific-consumption manifest.

GEN-C6 remains an A1 scientific hypothesis but its global INTERNAL_CAPITAL_MARKET
engine is A2-owned. A1 therefore accepts only a read-only external engine
receipt and never implements or closes that A2 workstream here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from qore.infrastructure.cibo_a1_a2_scientific_dependency import (
    A1A2ScientificDependencyAdmission,
)
from qore.infrastructure.cibo_a1_phase22_canonical_manifest_bridge import (
    A1Phase22CanonicalScientificManifestBridge,
)
from qore.infrastructure.cibo_a1_phase22_scientific_consumption import (
    A1Phase22ScientificConsumptionManifest,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_genc3_genc6_economic_gate import (
    Genc3To6EconomicGateReport,
    Genc3To6FoldEconomicObservation,
    Genc3To6Workstream,
    evaluate_genc3_genc6_economic_gate,
)
from qore.infrastructure.cibo_profit_preservation_economic_gate import (
    Genc7CausalEconomicObservation,
    Genc7EconomicGateReport,
    evaluate_genc7_economic_gate,
)

GATE_ID = "CIBO_A1_GENC3_GENC7_PHASE22_POPULATION_BINDING_V1"
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class A1Genc3To6Phase22BindingReport:
    gate_id: str
    manifest_sha256: str
    economic_gate: Genc3To6EconomicGateReport
    bound_workstreams: tuple[Genc3To6Workstream, ...]
    genc6_external_receipt_sha256: str | None
    exact_fold_population_binding: bool
    a2_workstream_modified: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 Phase22 binding gate identity drift"
            )
        _sha(self.manifest_sha256, "manifest_sha256")
        if (
            not isinstance(self.economic_gate, Genc3To6EconomicGateReport)
            or not self.bound_workstreams
            or len(self.bound_workstreams) != len(set(self.bound_workstreams))
        ):
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 Phase22 binding report surface invalid"
            )
        if not self.exact_fold_population_binding:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 Phase22 binding must be exact"
            )
        has_genc6 = Genc3To6Workstream.GENC6 in self.bound_workstreams
        if has_genc6 != (self.genc6_external_receipt_sha256 is not None):
            raise CiboCompoundCapitalError(
                "GEN-C6 Phase22 binding external receipt drift"
            )
        if self.genc6_external_receipt_sha256 is not None:
            _sha(
                self.genc6_external_receipt_sha256,
                "genc6_external_receipt_sha256",
            )
        if (
            self.a2_workstream_modified
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 Phase22 binding governance drift"
            )


@dataclass(frozen=True, slots=True)
class A1Genc7Phase22BindingReport:
    gate_id: str
    manifest_sha256: str
    economic_gate: Genc7EconomicGateReport
    full_population_bound: bool
    canonical_four_folds_bound: bool
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCompoundCapitalError(
                "GEN-C7 Phase22 binding gate identity drift"
            )
        _sha(self.manifest_sha256, "manifest_sha256")
        if not isinstance(self.economic_gate, Genc7EconomicGateReport):
            raise CiboCompoundCapitalError(
                "GEN-C7 Phase22 binding requires canonical economic gate"
            )
        if not self.full_population_bound or not self.canonical_four_folds_bound:
            raise CiboCompoundCapitalError(
                "GEN-C7 Phase22 binding must cover exact population/WF1..WF4"
            )
        if self.productive_authority or self.certification_ready:
            raise CiboCompoundCapitalError(
                "GEN-C7 Phase22 binding grants no authority"
            )


def bind_genc3_to6_to_phase22(
    *,
    manifest: A1Phase22ScientificConsumptionManifest,
    observations: tuple[Genc3To6FoldEconomicObservation, ...],
    canonical_bridge: A1Phase22CanonicalScientificManifestBridge | None = None,
    genc6_a2_dependency: A1A2ScientificDependencyAdmission | None = None,
) -> A1Genc3To6Phase22BindingReport:
    """Evaluate GEN-C3..C6 only after exact manifest-fold binding."""

    if not isinstance(manifest, A1Phase22ScientificConsumptionManifest):
        raise CiboCompoundCapitalError(
            "GEN-C3..C6 Phase22 binding requires canonical A1 manifest"
        )
    if not observations:
        raise CiboCompoundCapitalError(
            "GEN-C3..C6 Phase22 binding requires observations"
        )

    fold_population = {
        item.fold_id: item.population_sha256 for item in manifest.folds
    }
    workstreams = tuple(
        sorted(
            {item.workstream for item in observations},
            key=lambda item: item.value,
        )
    )
    for observation in observations:
        expected = fold_population.get(observation.fold_id)
        if expected is None or observation.population_sha256 != expected:
            raise CiboCompoundCapitalError(
                "GEN-C3..C6 observation population differs from A1 Phase22 fold"
            )

    has_genc6 = Genc3To6Workstream.GENC6 in workstreams
    receipt_sha: str | None = None
    if has_genc6:
        if not isinstance(
            canonical_bridge,
            A1Phase22CanonicalScientificManifestBridge,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 A1 hypothesis requires canonical Phase22 bridge"
            )
        if (
            canonical_bridge.a1_consumption_manifest_sha256
            != manifest.fingerprint()
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 canonical bridge/A1 consumption manifest drift"
            )
        if not isinstance(
            genc6_a2_dependency,
            A1A2ScientificDependencyAdmission,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 A1 hypothesis requires proven A2 dependency admission"
            )
        if genc6_a2_dependency.a2_workstream_id != "INTERNAL_CAPITAL_MARKET":
            raise CiboCompoundCapitalError(
                "GEN-C6 A2 dependency must be INTERNAL_CAPITAL_MARKET"
            )
        if (
            genc6_a2_dependency.a1_manifest_bridge_sha256
            != canonical_bridge.fingerprint()
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 A2 dependency/canonical bridge drift"
            )
        receipt_sha = genc6_a2_dependency.fingerprint()
    elif canonical_bridge is not None or genc6_a2_dependency is not None:
        raise CiboCompoundCapitalError(
            "GEN-C6 dependency supplied without GEN-C6 observations"
        )

    economic = evaluate_genc3_genc6_economic_gate(observations)
    return A1Genc3To6Phase22BindingReport(
        gate_id=GATE_ID,
        manifest_sha256=manifest.fingerprint(),
        economic_gate=economic,
        bound_workstreams=workstreams,
        genc6_external_receipt_sha256=receipt_sha,
        exact_fold_population_binding=True,
    )


def bind_genc7_to_phase22(
    *,
    manifest: A1Phase22ScientificConsumptionManifest,
    observations: tuple[Genc7CausalEconomicObservation, ...],
) -> A1Genc7Phase22BindingReport:
    """Evaluate GEN-C7 only on the exact full Phase22 A1 population."""

    if not isinstance(manifest, A1Phase22ScientificConsumptionManifest):
        raise CiboCompoundCapitalError(
            "GEN-C7 Phase22 binding requires canonical A1 manifest"
        )
    if not observations:
        raise CiboCompoundCapitalError(
            "GEN-C7 Phase22 binding requires observations"
        )
    for observation in observations:
        if observation.population_sha256 != manifest.source_population_sha256:
            raise CiboCompoundCapitalError(
                "GEN-C7 observation population differs from A1 Phase22 manifest"
            )
        if observation.fold_ids != _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "GEN-C7 Phase22 binding requires exact WF1..WF4"
            )

    economic = evaluate_genc7_economic_gate(observations)
    return A1Genc7Phase22BindingReport(
        gate_id=GATE_ID,
        manifest_sha256=manifest.fingerprint(),
        economic_gate=economic,
        full_population_bound=True,
        canonical_four_folds_bound=True,
    )


def _sha(value: str, name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"GEN-C Phase22 binding {name} must be canonical SHA-256"
        )
