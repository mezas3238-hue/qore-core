from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.infrastructure.research_lineage_canonical import (
    _canonical_state_content,
    _cjson,
    _sha256,
)
from qore.infrastructure.research_lineage_errors import (
    ResearchLineageCanonicalValueError,
    ResearchLineageError,
    ResearchLineageValidationError,
)
from qore.infrastructure.research_lineage_fingerprints import (
    ResearchStrategyStateFingerprint,
)


class ResearchStrategyStateContentProtocol(Protocol):
    """Producer-supplied deterministic state evidence projection."""

    def logical_values(self) -> Mapping[str, object]: ...


def _state_content_values(
    content: ResearchStrategyStateContentProtocol,
) -> Mapping[str, object]:
    logical_values = getattr(content, "logical_values", None)
    if not callable(logical_values):
        raise ResearchLineageValidationError(
            "exact_content must expose callable logical_values()"
        )
    try:
        values = logical_values()
    except ResearchLineageError:
        raise
    except Exception as exc:
        raise ResearchLineageValidationError(
            f"exact_content.logical_values() raised unexpected error: {exc!r}"
        ) from exc
    if not isinstance(values, Mapping):
        raise ResearchLineageValidationError(
            "exact_content.logical_values() must return a Mapping"
        )
    if any(not isinstance(key, str) for key in values):
        raise ResearchLineageValidationError(
            "exact_content.logical_values() keys must be strings"
        )
    return values


@dataclass(frozen=True, slots=True)
class ResearchStrategyState:
    evaluator_identity: ResearchDecisionEvaluatorIdentity
    evaluation_sequence_number: int
    state_schema_version: str
    exact_content: ResearchStrategyStateContentProtocol
    state_fingerprint: ResearchStrategyStateFingerprint = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(
            self.evaluator_identity,
            ResearchDecisionEvaluatorIdentity,
        ):
            raise ResearchLineageValidationError(
                "evaluator_identity must be ResearchDecisionEvaluatorIdentity"
            )
        if (
            isinstance(self.evaluation_sequence_number, bool)
            or type(self.evaluation_sequence_number) is not int
            or self.evaluation_sequence_number < 0
        ):
            raise ResearchLineageValidationError(
                "evaluation_sequence_number must be non-negative int; bool rejected"
            )
        if not isinstance(self.state_schema_version, str):
            raise ResearchLineageValidationError(
                "state_schema_version must be str"
            )
        if (
            self.state_schema_version
            != self.evaluator_identity.schema_version.value
        ):
            raise ResearchLineageValidationError(
                "state_schema_version must equal evaluator schema version"
            )
        if self.exact_content is None:
            raise ResearchLineageValidationError(
                "exact_content must not be None"
            )
        values = _state_content_values(self.exact_content)
        try:
            canonical = _canonical_state_content(values)
        except ResearchLineageCanonicalValueError:
            raise
        object.__setattr__(
            self,
            "state_fingerprint",
            _compute_state_fingerprint(self, canonical_content=canonical),
        )


def _compute_state_fingerprint(
    state: ResearchStrategyState,
    *,
    canonical_content: dict[str, object] | None = None,
) -> ResearchStrategyStateFingerprint:
    if not isinstance(state, ResearchStrategyState):
        raise ResearchLineageValidationError(
            "state must be ResearchStrategyState"
        )
    content = canonical_content
    if content is None:
        content = _canonical_state_content(
            _state_content_values(state.exact_content)
        )
    return ResearchStrategyStateFingerprint(
        value=_sha256(
            _cjson(
                {
                    "schema": "qore.research-strategy-state.v1",
                    "evaluator_family": state.evaluator_identity.family.value,
                    "evaluator_schema_version": (
                        state.evaluator_identity.schema_version.value
                    ),
                    "software_revision": (
                        state.evaluator_identity.software_revision.value
                    ),
                    "evaluation_sequence_number": (
                        state.evaluation_sequence_number
                    ),
                    "state_schema_version": state.state_schema_version,
                    "state_content": content,
                }
            )
        )
    )
