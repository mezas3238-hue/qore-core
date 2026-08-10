from __future__ import annotations

from typing import cast

import pytest

from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
    ResearchSpecialistEvaluatorFamily,
    ResearchSpecialistEvaluatorIdentity,
    ResearchSpecialistEvaluatorSchemaVersion,
)
from qore.infrastructure.research_lineage_errors import ResearchLineageValidationError
from qore.infrastructure.research_run import ResearchSoftwareRevision


def test_decision_evaluator_identity_is_typed_and_deterministic() -> None:
    identity = ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily("qore.research.decision"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1.2"),
        software_revision=ResearchSoftwareRevision("revision-1"),
    )
    assert identity.logical_values() == {
        "family": "qore.research.decision",
        "schema_version": "v1.2",
        "software_revision": "revision-1",
    }


def test_family_and_schema_fail_closed() -> None:
    with pytest.raises(ResearchLineageValidationError):
        ResearchDecisionEvaluatorFamily("QORE")
    with pytest.raises(ResearchLineageValidationError):
        ResearchDecisionEvaluatorFamily(cast(str, 1))
    with pytest.raises(ResearchLineageValidationError):
        ResearchDecisionEvaluatorSchemaVersion("1.0")
    with pytest.raises(ResearchLineageValidationError):
        ResearchDecisionEvaluatorSchemaVersion(cast(str, None))


def test_specialist_identity_uses_distinct_contract_types() -> None:
    identity = ResearchSpecialistEvaluatorIdentity(
        family=ResearchSpecialistEvaluatorFamily("qore.research.specialist"),
        schema_version=ResearchSpecialistEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("revision-1"),
    )
    assert identity.logical_values()["family"] == "qore.research.specialist"
    with pytest.raises(ResearchLineageValidationError):
        ResearchSpecialistEvaluatorIdentity(
            family=cast(ResearchSpecialistEvaluatorFamily, ResearchDecisionEvaluatorFamily("qore.x")),
            schema_version=ResearchSpecialistEvaluatorSchemaVersion("v1"),
            software_revision=ResearchSoftwareRevision("revision-1"),
        )
