from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

import pytest

from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_lineage_errors import (
    ResearchLineageCanonicalValueError,
    ResearchLineageValidationError,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.infrastructure.research_strategy_state import (
    ResearchStrategyState,
    ResearchStrategyStateContentProtocol,
)

_IDENTITY = ResearchDecisionEvaluatorIdentity(
    family=ResearchDecisionEvaluatorFamily("test.reference"),
    schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
    software_revision=ResearchSoftwareRevision("revision-1"),
)


@dataclass(frozen=True, slots=True)
class _Content:
    value: object

    def logical_values(self) -> Mapping[str, object]:
        return {"value": self.value}


class _BadReturn:
    def logical_values(self) -> object:
        return ("not", "a", "mapping")


class _BadKeys:
    def logical_values(self) -> Mapping[object, object]:
        return {1: "bad"}


def test_state_fingerprint_is_computed_and_content_bound() -> None:
    first = ResearchStrategyState(
        evaluator_identity=_IDENTITY,
        evaluation_sequence_number=0,
        state_schema_version="v1",
        exact_content=_Content(1),
    )
    second = ResearchStrategyState(
        evaluator_identity=_IDENTITY,
        evaluation_sequence_number=0,
        state_schema_version="v1",
        exact_content=_Content(2),
    )
    assert first.state_fingerprint != second.state_fingerprint


def test_state_rejects_bool_sequence_and_schema_mismatch() -> None:
    with pytest.raises(ResearchLineageValidationError):
        ResearchStrategyState(
            evaluator_identity=_IDENTITY,
            evaluation_sequence_number=cast(int, True),
            state_schema_version="v1",
            exact_content=_Content(1),
        )
    with pytest.raises(ResearchLineageValidationError):
        ResearchStrategyState(
            evaluator_identity=_IDENTITY,
            evaluation_sequence_number=0,
            state_schema_version="v2",
            exact_content=_Content(1),
        )


def test_state_content_contract_fails_closed() -> None:
    with pytest.raises(ResearchLineageValidationError):
        ResearchStrategyState(
            evaluator_identity=_IDENTITY,
            evaluation_sequence_number=0,
            state_schema_version="v1",
            exact_content=cast(ResearchStrategyStateContentProtocol, None),
        )
    with pytest.raises(ResearchLineageValidationError):
        ResearchStrategyState(
            evaluator_identity=_IDENTITY,
            evaluation_sequence_number=0,
            state_schema_version="v1",
            exact_content=cast(
                ResearchStrategyStateContentProtocol,
                _BadReturn(),
            ),
        )
    with pytest.raises(ResearchLineageValidationError):
        ResearchStrategyState(
            evaluator_identity=_IDENTITY,
            evaluation_sequence_number=0,
            state_schema_version="v1",
            exact_content=cast(
                ResearchStrategyStateContentProtocol,
                _BadKeys(),
            ),
        )


def test_state_content_rejects_unsupported_nested_value() -> None:
    with pytest.raises(ResearchLineageCanonicalValueError):
        ResearchStrategyState(
            evaluator_identity=_IDENTITY,
            evaluation_sequence_number=0,
            state_schema_version="v1",
            exact_content=_Content(object()),
        )
