from __future__ import annotations

from qore.kernel.errors import InfrastructureError


class ResearchLineageError(InfrastructureError):
    """Base error for research-lineage evidence infrastructure."""

    __slots__ = ()


class ResearchLineageValidationError(ResearchLineageError):
    """Violation of a research-lineage invariant."""

    __slots__ = ()


class ResearchLineageFingerprintError(ResearchLineageError):
    """Malformed or inconsistent research-lineage fingerprint."""

    __slots__ = ()


class ResearchLineageCanonicalValueError(ResearchLineageError):
    """Unsupported or ambiguous value in exact canonical evidence."""

    __slots__ = ()


class ResearchExecutionSessionValidationError(ResearchLineageValidationError):
    """Violation of an exact research execution-session invariant."""

    __slots__ = ()


class ResearchExecutionTraceValidationError(ResearchLineageValidationError):
    """Violation of an exact research execution-trace invariant."""

    __slots__ = ()


class ResearchEvaluatorIdentityMismatchError(ResearchLineageError):
    """A decision evaluator does not match the retained trace identity."""

    __slots__ = ()


class ResearchSpecialistEvaluatorIdentityMismatchError(ResearchLineageError):
    """A specialist evaluator does not match retained specialist evidence."""

    __slots__ = ()
