from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId, DomainMetadataValue
from qore.functional.decisions import (
    DecisionId,
    DecisionMetadata,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionStatus,
    DecisionType,
    DecisionValidationError,
    FunctionalDecision,
)

_DECISION_ID = DecisionId(UUID("00000000-0000-0000-0000-000000000001"))
_CORRELATION_ID = CorrelationId(UUID("00000000-0000-0000-0000-000000000002"))
_CAUSATION_ID = CausationId(UUID("00000000-0000-0000-0000-000000000003"))
_TIMESTAMP = datetime(2026, 8, 7, 18, 0, tzinfo=UTC)


def _metadata() -> DecisionMetadata:
    return DecisionMetadata(
        correlation_id=_CORRELATION_ID,
        causation_id=_CAUSATION_ID,
        attributes={"scope": "global", "sequence": 1},
    )


def _reason() -> DecisionReason:
    return DecisionReason(
        code=DecisionReasonCode("policy.accepted"),
        summary="Policy conditions are satisfied",
        attributes={"rule": "base"},
    )


class TestDecisionValueContracts:
    @pytest.mark.parametrize("value", ["", "UPPER", "with space", ".invalid"])
    def test_decision_type_rejects_invalid_values(self, value: str) -> None:
        with pytest.raises(DecisionValidationError):
            DecisionType(value)

    @pytest.mark.parametrize("value", ["", "UPPER", "with space", "-invalid"])
    def test_reason_code_rejects_invalid_values(self, value: str) -> None:
        with pytest.raises(DecisionValidationError):
            DecisionReasonCode(value)

    def test_reason_requires_non_empty_summary(self) -> None:
        with pytest.raises(DecisionValidationError, match="summary"):
            DecisionReason(
                code=DecisionReasonCode("policy.rejected"),
                summary="   ",
            )


class TestDecisionMetadata:
    def test_metadata_is_defensively_copied_sorted_and_immutable(self) -> None:
        source: dict[str, DomainMetadataValue] = {"z": 2, "a": 1}
        metadata = DecisionMetadata(
            correlation_id=_CORRELATION_ID,
            attributes=source,
        )

        source["a"] = 99

        assert tuple(metadata.attributes.items()) == (("a", 1), ("z", 2))
        with pytest.raises(TypeError):
            metadata.attributes["a"] = 3  # type: ignore[index]

    @pytest.mark.parametrize("key", ["correlation_id", "causation_id"])
    def test_metadata_rejects_reserved_keys(self, key: str) -> None:
        with pytest.raises(DecisionValidationError, match="reserved"):
            DecisionMetadata(
                correlation_id=_CORRELATION_ID,
                attributes={key: "override"},
            )

    def test_metadata_rejects_mutable_nested_values(self) -> None:
        mutable = cast(DomainMetadataValue, ["not", "immutable"])
        with pytest.raises(DecisionValidationError, match="immutable"):
            DecisionMetadata(
                correlation_id=_CORRELATION_ID,
                attributes={"bad": mutable},
            )

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
    def test_metadata_rejects_non_finite_floats(self, value: float) -> None:
        with pytest.raises(DecisionValidationError, match="finite"):
            DecisionMetadata(
                correlation_id=_CORRELATION_ID,
                attributes={"bad": value},
            )

    def test_reason_attributes_are_defensively_copied(self) -> None:
        source: dict[str, DomainMetadataValue] = {"z": "last", "a": "first"}
        reason = DecisionReason(
            code=DecisionReasonCode("risk.checked"),
            summary="Risk evaluation completed",
            attributes=source,
        )

        source["a"] = "changed"

        assert tuple(reason.attributes.items()) == (("a", "first"), ("z", "last"))


class TestFunctionalDecision:
    def test_pending_decision_has_no_outcome(self) -> None:
        decision = FunctionalDecision(
            decision_id=_DECISION_ID,
            timestamp=_TIMESTAMP,
            decision_type=DecisionType("governance.review"),
            status=DecisionStatus.PENDING,
            priority=DecisionPriority.NORMAL,
            metadata=_metadata(),
        )

        assert decision.outcome is None
        assert decision.reasons == ()

    def test_pending_decision_rejects_outcome(self) -> None:
        with pytest.raises(DecisionValidationError, match="pending"):
            FunctionalDecision(
                decision_id=_DECISION_ID,
                timestamp=_TIMESTAMP,
                decision_type=DecisionType("governance.review"),
                status=DecisionStatus.PENDING,
                priority=DecisionPriority.NORMAL,
                metadata=_metadata(),
                outcome=DecisionOutcome.APPROVED,
            )

    def test_resolved_decision_requires_outcome(self) -> None:
        with pytest.raises(DecisionValidationError, match="outcome"):
            FunctionalDecision(
                decision_id=_DECISION_ID,
                timestamp=_TIMESTAMP,
                decision_type=DecisionType("governance.review"),
                status=DecisionStatus.RESOLVED,
                priority=DecisionPriority.HIGH,
                metadata=_metadata(),
                reasons=(_reason(),),
            )

    def test_resolved_decision_requires_reason(self) -> None:
        with pytest.raises(DecisionValidationError, match="reason"):
            FunctionalDecision(
                decision_id=_DECISION_ID,
                timestamp=_TIMESTAMP,
                decision_type=DecisionType("governance.review"),
                status=DecisionStatus.RESOLVED,
                priority=DecisionPriority.HIGH,
                metadata=_metadata(),
                outcome=DecisionOutcome.BLOCKED,
            )

    @pytest.mark.parametrize(
        "outcome",
        [
            DecisionOutcome.APPROVED,
            DecisionOutcome.REJECTED,
            DecisionOutcome.BLOCKED,
            DecisionOutcome.DEGRADED,
        ],
    )
    def test_resolved_decision_supports_every_closed_outcome(
        self,
        outcome: DecisionOutcome,
    ) -> None:
        decision = FunctionalDecision(
            decision_id=_DECISION_ID,
            timestamp=_TIMESTAMP,
            decision_type=DecisionType("governance.review"),
            status=DecisionStatus.RESOLVED,
            priority=DecisionPriority.CRITICAL,
            metadata=_metadata(),
            reasons=(_reason(),),
            outcome=outcome,
        )

        assert decision.outcome is outcome

    def test_decision_is_frozen(self) -> None:
        decision = FunctionalDecision(
            decision_id=_DECISION_ID,
            timestamp=_TIMESTAMP,
            decision_type=DecisionType("governance.review"),
            status=DecisionStatus.PENDING,
            priority=DecisionPriority.LOW,
            metadata=_metadata(),
        )

        with pytest.raises(FrozenInstanceError):
            decision.status = DecisionStatus.RESOLVED  # type: ignore[misc]

    def test_logical_values_are_deterministic_for_equal_inputs(self) -> None:
        first = FunctionalDecision(
            decision_id=_DECISION_ID,
            timestamp=_TIMESTAMP,
            decision_type=DecisionType("governance.review"),
            status=DecisionStatus.RESOLVED,
            priority=DecisionPriority.HIGH,
            metadata=DecisionMetadata(
                correlation_id=_CORRELATION_ID,
                causation_id=_CAUSATION_ID,
                attributes={"z": 2, "a": 1},
            ),
            reasons=(
                DecisionReason(
                    code=DecisionReasonCode("policy.accepted"),
                    summary="Accepted",
                    attributes={"z": 2, "a": 1},
                ),
            ),
            outcome=DecisionOutcome.APPROVED,
        )
        second = FunctionalDecision(
            decision_id=_DECISION_ID,
            timestamp=_TIMESTAMP,
            decision_type=DecisionType("governance.review"),
            status=DecisionStatus.RESOLVED,
            priority=DecisionPriority.HIGH,
            metadata=DecisionMetadata(
                correlation_id=_CORRELATION_ID,
                causation_id=_CAUSATION_ID,
                attributes={"a": 1, "z": 2},
            ),
            reasons=(
                DecisionReason(
                    code=DecisionReasonCode("policy.accepted"),
                    summary="Accepted",
                    attributes={"a": 1, "z": 2},
                ),
            ),
            outcome=DecisionOutcome.APPROVED,
        )

        assert first.logical_values() == second.logical_values()
        assert first.logical_values()[0] == str(_DECISION_ID.value)
        assert first.logical_values()[1] == _TIMESTAMP.isoformat()
