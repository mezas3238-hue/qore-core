from __future__ import annotations

import re
from dataclasses import dataclass

from qore.infrastructure.research_lineage_errors import ResearchLineageValidationError
from qore.infrastructure.research_run import ResearchSoftwareRevision

_FAMILY_RE = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)*$")
_SCHEMA_RE = re.compile(r"^v\d+(\.\d+)*$")


def _validate_family(value: str, *, field_name: str) -> None:
    if not isinstance(value, str):
        raise ResearchLineageValidationError(f"{field_name} must be str")
    if _FAMILY_RE.fullmatch(value) is None:
        raise ResearchLineageValidationError(
            f"{field_name} must match [a-z][a-z0-9]*(\\.[a-z][a-z0-9]*)*"
        )


def _validate_schema(value: str, *, field_name: str) -> None:
    if not isinstance(value, str):
        raise ResearchLineageValidationError(f"{field_name} must be str")
    if _SCHEMA_RE.fullmatch(value) is None:
        raise ResearchLineageValidationError(
            f"{field_name} must match v\\d+(\\.\\d+)*"
        )


@dataclass(frozen=True, slots=True)
class ResearchDecisionEvaluatorFamily:
    value: str

    def __post_init__(self) -> None:
        _validate_family(self.value, field_name="decision evaluator family")

    def logical_values(self) -> dict[str, str]:
        return {"family": self.value}


@dataclass(frozen=True, slots=True)
class ResearchDecisionEvaluatorSchemaVersion:
    value: str

    def __post_init__(self) -> None:
        _validate_schema(self.value, field_name="decision evaluator schema_version")

    def logical_values(self) -> dict[str, str]:
        return {"schema_version": self.value}


@dataclass(frozen=True, slots=True)
class ResearchDecisionEvaluatorIdentity:
    family: ResearchDecisionEvaluatorFamily
    schema_version: ResearchDecisionEvaluatorSchemaVersion
    software_revision: ResearchSoftwareRevision

    def __post_init__(self) -> None:
        if not isinstance(self.family, ResearchDecisionEvaluatorFamily):
            raise ResearchLineageValidationError(
                "family must be ResearchDecisionEvaluatorFamily"
            )
        if not isinstance(
            self.schema_version,
            ResearchDecisionEvaluatorSchemaVersion,
        ):
            raise ResearchLineageValidationError(
                "schema_version must be ResearchDecisionEvaluatorSchemaVersion"
            )
        if not isinstance(self.software_revision, ResearchSoftwareRevision):
            raise ResearchLineageValidationError(
                "software_revision must be ResearchSoftwareRevision"
            )

    def logical_values(self) -> dict[str, str]:
        return {
            "family": self.family.value,
            "schema_version": self.schema_version.value,
            "software_revision": self.software_revision.value,
        }


@dataclass(frozen=True, slots=True)
class ResearchSpecialistEvaluatorFamily:
    value: str

    def __post_init__(self) -> None:
        _validate_family(self.value, field_name="specialist evaluator family")

    def logical_values(self) -> dict[str, str]:
        return {"family": self.value}


@dataclass(frozen=True, slots=True)
class ResearchSpecialistEvaluatorSchemaVersion:
    value: str

    def __post_init__(self) -> None:
        _validate_schema(self.value, field_name="specialist evaluator schema_version")

    def logical_values(self) -> dict[str, str]:
        return {"schema_version": self.value}


@dataclass(frozen=True, slots=True)
class ResearchSpecialistEvaluatorIdentity:
    family: ResearchSpecialistEvaluatorFamily
    schema_version: ResearchSpecialistEvaluatorSchemaVersion
    software_revision: ResearchSoftwareRevision

    def __post_init__(self) -> None:
        if not isinstance(self.family, ResearchSpecialistEvaluatorFamily):
            raise ResearchLineageValidationError(
                "family must be ResearchSpecialistEvaluatorFamily"
            )
        if not isinstance(
            self.schema_version,
            ResearchSpecialistEvaluatorSchemaVersion,
        ):
            raise ResearchLineageValidationError(
                "schema_version must be ResearchSpecialistEvaluatorSchemaVersion"
            )
        if not isinstance(self.software_revision, ResearchSoftwareRevision):
            raise ResearchLineageValidationError(
                "software_revision must be ResearchSoftwareRevision"
            )

    def logical_values(self) -> dict[str, str]:
        return {
            "family": self.family.value,
            "schema_version": self.schema_version.value,
            "software_revision": self.software_revision.value,
        }
