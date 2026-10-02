"""Architect A1 internal-readiness audit for isolated CIBO certification work.

The gate answers one narrow question: has A1 finished the engineering,
preregistration, evidence-binding and handoff infrastructure that A1 owns?

Scientific outcomes, A2-owned mechanisms, Master Ledger reconciliation and
certification remain external. Expected external dependencies are reported but
must never be converted into engineering PASS claims.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from qore.infrastructure.cibo_a1_scientific_disposition import A1_WORKSTREAMS
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

SCHEMA = "QORE_CIBO_ARCH_A1_INTERNAL_READINESS_V1"

A1_REQUIRED_ARTIFACTS = (
    "src/qore/infrastructure/cibo_a1_strict_temporal_population_lineage.py",
    "src/qore/infrastructure/cibo_t08_factor_correlation_lineage.py",
    "src/qore/infrastructure/cibo_ce2i_phase20_t09_t18_phase22_true_scarcity_lineage.py",
    "src/qore/infrastructure/cibo_ce2i_phase20_t12_t13_phase22_causal_lineage.py",
    "src/qore/infrastructure/cibo_ce2i_phase20_t15_reservation_counterfactual.py",
    "src/qore/infrastructure/cibo_a1_phase22_scientific_consumption.py",
    "src/qore/infrastructure/cibo_a1_phase22_canonical_manifest_bridge.py",
    "src/qore/infrastructure/cibo_a1_a2_scientific_dependency.py",
    "src/qore/infrastructure/cibo_a1_phase22_historical_compound_dependency.py",
    "src/qore/infrastructure/cibo_a1_t08_phase22_oos_binding.py",
    "src/qore/infrastructure/cibo_a1_ce2i_phase22_population_binding.py",
    "src/qore/infrastructure/cibo_a1_genc2_phase22_profit_graduation.py",
    "src/qore/infrastructure/cibo_a1_genc3_genc7_phase22_binding.py",
    "src/qore/infrastructure/cibo_a1_scientific_disposition.py",
    "src/qore/infrastructure/cibo_arch_a1_internal_readiness.py",
    "src/qore/infrastructure/cibo_arch_a1_integrator_handoff.py",
)

A1_REQUIRED_WORKFLOWS = (
    ".github/workflows/cibo-a1-strict-temporal-population-lineage.yml",
    ".github/workflows/cibo-t08-factor-correlation-lineage.yml",
    ".github/workflows/cibo-ce2i-phase20-t09-t18-phase22-scarcity.yml",
    ".github/workflows/cibo-ce2i-phase20-t12-t13-phase22-lineage.yml",
    ".github/workflows/cibo-ce2i-phase20-t15-reservation-counterfactual.yml",
    ".github/workflows/cibo-a1-phase22-scientific-consumption.yml",
    ".github/workflows/cibo-a1-phase22-canonical-manifest-bridge.yml",
    ".github/workflows/cibo-a1-a2-scientific-dependency.yml",
    ".github/workflows/cibo-a1-phase22-historical-compound-dependency.yml",
    ".github/workflows/cibo-a1-t08-phase22-oos-binding.yml",
    ".github/workflows/cibo-a1-ce2i-phase22-population-binding.yml",
    ".github/workflows/cibo-a1-genc2-phase22-profit-graduation.yml",
    ".github/workflows/cibo-a1-genc3-genc7-phase22-binding.yml",
    ".github/workflows/cibo-a1-scientific-disposition.yml",
    ".github/workflows/cibo-architect-a1-internal-readiness.yml",
    ".github/workflows/cibo-architect-a1-integrator-handoff.yml",
)

EXPECTED_EXTERNAL_DEPENDENCIES = (
    "CANONICAL_PHASE22_V2_TERMINAL_SCIENTIFIC_INTAKE",
    "A2_COMPOUND_ENGINE_COMPLETED_AND_PROVEN",
    "A2_INTERNAL_CAPITAL_MARKET_COMPLETED_AND_PROVEN",
    "A2_PROTECTED_BASE_CAPITAL_COMPLETED_AND_PROVEN",
    "A2_PROFIT_PROTECTION_COMPLETED_AND_PROVEN",
    "INTEGRATOR_MASTER_LEDGER_RECONCILIATION",
)


@dataclass(frozen=True, slots=True)
class ArchitectA1InternalReadinessReport:
    schema: str
    owned_workstream_count: int
    required_artifact_count: int
    required_workflow_count: int
    missing_artifacts: tuple[str, ...]
    missing_workflows: tuple[str, ...]
    expected_external_dependencies: tuple[str, ...]
    engineering_ready: bool
    scientific_closure_claimed: bool = False
    integration_authority: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise CiboCapitalManagementError(
                "Architect A1 internal-readiness schema drift"
            )
        if self.owned_workstream_count != 18 or len(A1_WORKSTREAMS) != 18:
            raise CiboCapitalManagementError(
                "Architect A1 ownership cardinality drift"
            )
        if self.required_artifact_count != len(A1_REQUIRED_ARTIFACTS):
            raise CiboCapitalManagementError(
                "Architect A1 artifact-count drift"
            )
        if self.required_workflow_count != len(A1_REQUIRED_WORKFLOWS):
            raise CiboCapitalManagementError(
                "Architect A1 workflow-count drift"
            )
        for name in ("missing_artifacts", "missing_workflows"):
            values = getattr(self, name)
            if (
                not isinstance(values, tuple)
                or len(values) != len(set(values))
                or any(not isinstance(item, str) or not item for item in values)
            ):
                raise CiboCapitalManagementError(
                    f"Architect A1 {name} invalid"
                )
        if self.expected_external_dependencies != EXPECTED_EXTERNAL_DEPENDENCIES:
            raise CiboCapitalManagementError(
                "Architect A1 external-dependency identity drift"
            )
        expected_ready = not self.missing_artifacts and not self.missing_workflows
        if self.engineering_ready != expected_ready:
            raise CiboCapitalManagementError(
                "Architect A1 engineering readiness drift"
            )
        if (
            self.scientific_closure_claimed
            or self.integration_authority
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCapitalManagementError(
                "Architect A1 readiness grants no scientific/integration authority"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_architect_a1_internal_readiness(
    repo_root: Path = Path("."),
) -> ArchitectA1InternalReadinessReport:
    """Fail closed on missing A1-owned engineering artifacts only."""

    if not isinstance(repo_root, Path):
        raise CiboCapitalManagementError(
            "Architect A1 readiness repo_root must be Path"
        )
    missing_artifacts = tuple(
        path for path in A1_REQUIRED_ARTIFACTS
        if not (repo_root / path).is_file()
    )
    missing_workflows = tuple(
        path for path in A1_REQUIRED_WORKFLOWS
        if not (repo_root / path).is_file()
    )
    return ArchitectA1InternalReadinessReport(
        schema=SCHEMA,
        owned_workstream_count=len(A1_WORKSTREAMS),
        required_artifact_count=len(A1_REQUIRED_ARTIFACTS),
        required_workflow_count=len(A1_REQUIRED_WORKFLOWS),
        missing_artifacts=missing_artifacts,
        missing_workflows=missing_workflows,
        expected_external_dependencies=EXPECTED_EXTERNAL_DEPENDENCIES,
        engineering_ready=not missing_artifacts and not missing_workflows,
    )
