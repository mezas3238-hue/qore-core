from __future__ import annotations

from qore.infrastructure.research_lineage_errors import (
    ResearchEvaluatorIdentityMismatchError,
    ResearchExecutionSessionValidationError,
    ResearchExecutionTraceValidationError,
    ResearchLineageCanonicalValueError,
    ResearchLineageError,
    ResearchLineageFingerprintError,
    ResearchLineageValidationError,
    ResearchSpecialistEvaluatorIdentityMismatchError,
)
from qore.kernel.errors import InfrastructureError


def test_research_lineage_error_hierarchy_is_infrastructure_bounded() -> None:
    assert issubclass(ResearchLineageError, InfrastructureError)
    assert issubclass(ResearchLineageValidationError, ResearchLineageError)
    assert issubclass(ResearchLineageFingerprintError, ResearchLineageError)
    assert issubclass(ResearchLineageCanonicalValueError, ResearchLineageError)
    assert issubclass(
        ResearchExecutionSessionValidationError,
        ResearchLineageValidationError,
    )
    assert issubclass(
        ResearchExecutionTraceValidationError,
        ResearchLineageValidationError,
    )
    assert issubclass(ResearchEvaluatorIdentityMismatchError, ResearchLineageError)
    assert issubclass(
        ResearchSpecialistEvaluatorIdentityMismatchError,
        ResearchLineageError,
    )
