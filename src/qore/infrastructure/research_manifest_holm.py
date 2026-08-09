from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.research_hypothesis_family import (
    ResearchBootstrapHypothesisFamilyEvidence,
)
from qore.infrastructure.research_multiplicity import (
    ResearchHolmFamilyId,
    ResearchHolmFamilywiseEvidence,
    ResearchHolmPolicy,
    build_research_holm_familywise_evidence,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ResearchManifestHolmError(InfrastructureError):
    """Base error for manifest-bound Holm evidence."""

    __slots__ = ()


class ResearchManifestHolmValidationError(ResearchManifestHolmError):
    """Violation of a manifest-bound Holm invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ResearchManifestHolmEvidence:
    """Holm correction bound to one structurally manifested result family.

    The Holm evidence must consume exactly the tests already bound to the family
    manifest. This prevents substituting, adding, dropping, or reordering family
    results at the multiplicity-correction boundary.

    This composition remains structural evidence. It does not prove that the
    manifest existed before outcomes were observed, and it does not authorize a
    strategy, predictive-validity claim, production deployment, or capital.
    """

    family: ResearchBootstrapHypothesisFamilyEvidence
    holm: ResearchHolmFamilywiseEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.family, ResearchBootstrapHypothesisFamilyEvidence):
            raise ResearchManifestHolmValidationError(
                "manifest-bound Holm evidence requires a hypothesis family evidence"
            )
        if not isinstance(self.holm, ResearchHolmFamilywiseEvidence):
            raise ResearchManifestHolmValidationError(
                "manifest-bound Holm evidence requires ResearchHolmFamilywiseEvidence"
            )
        if self.holm.tests != self.family.tests:
            raise ResearchManifestHolmValidationError(
                "Holm tests must exactly match the manifest-bound family results"
            )
        if self.holm.family_size != self.family.family_size:
            raise ResearchManifestHolmValidationError(
                "Holm family size must match the manifest-bound family size"
            )

    @property
    def rejection_count(self) -> int:
        return self.holm.rejection_count

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.family.logical_values(),
            self.holm.logical_values(),
        )


def build_research_manifest_holm_evidence(
    *,
    family: ResearchBootstrapHypothesisFamilyEvidence,
    family_id: ResearchHolmFamilyId,
    policy: ResearchHolmPolicy,
) -> Result[ResearchManifestHolmEvidence, InfrastructureError]:
    """Apply Holm correction only to the exact manifest-bound result family."""

    if not isinstance(family, ResearchBootstrapHypothesisFamilyEvidence):
        return Failure(
            ResearchManifestHolmValidationError(
                "family must be ResearchBootstrapHypothesisFamilyEvidence"
            )
        )
    built = build_research_holm_familywise_evidence(
        family_id=family_id,
        policy=policy,
        tests=family.tests,
    )
    if isinstance(built, Failure):
        return Failure(built.error)
    try:
        return Success(
            ResearchManifestHolmEvidence(
                family=family,
                holm=built.value,
            )
        )
    except ResearchManifestHolmError as error:
        return Failure(error)
