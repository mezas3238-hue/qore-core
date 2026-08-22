from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.structured_hybrid_synthetic_semantics import (
    StructuredBarrierFeature,
    StructuredConversionFeature,
    StructuredEvidenceRef,
    StructuredFeatureId,
    StructuredHybridSyntheticTerms,
    StructuredParticipationFeature,
    StructuredRedemptionFeature,
)
from qore.kernel.errors import InfrastructureError


class StructuredNotePayoffSemanticsError(InfrastructureError):
    """Base error for structured-note conditional payoff semantics."""

    __slots__ = ()


class StructuredNotePayoffValidationError(StructuredNotePayoffSemanticsError):
    """Violation of a structured-note conditional payoff invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if type(value) is not UUID:
        raise StructuredNotePayoffValidationError(f"{field_name} must be UUID")


@dataclass(frozen=True, slots=True)
class StructuredNotePayoffTermsId:
    """Local immutable payoff-map identity; never an economic instrument identity."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="structured-note payoff terms id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class StructuredNotePayoffBranchId:
    """Local immutable branch identity; never an event or settlement identity."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="structured-note payoff branch id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class StructuredNoteConditionMode(StrEnum):
    """Set-like combination rule for static barrier conditions."""

    ALL = "all"
    ANY = "any"


class StructuredNoteOutcomeKind(StrEnum):
    """Bounded maturity-outcome forms composed from certified UMI-09 features."""

    REDEMPTION = "redemption"
    REDEMPTION_WITH_PARTICIPATION = "redemption-with-participation"
    PARTICIPATION = "participation"
    CONVERSION = "conversion"


@dataclass(frozen=True, slots=True)
class StructuredNotePayoffOutcome:
    """One static branch outcome; no payoff calculation or settlement mutation."""

    kind: StructuredNoteOutcomeKind
    redemption_feature_id: StructuredFeatureId | None = None
    participation_feature_id: StructuredFeatureId | None = None
    conversion_feature_id: StructuredFeatureId | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, StructuredNoteOutcomeKind):
            raise StructuredNotePayoffValidationError(
                "structured-note outcome kind must be StructuredNoteOutcomeKind"
            )
        if self.redemption_feature_id is not None and not isinstance(
            self.redemption_feature_id,
            StructuredFeatureId,
        ):
            raise StructuredNotePayoffValidationError(
                "redemption_feature_id must be StructuredFeatureId or None"
            )
        if self.participation_feature_id is not None and not isinstance(
            self.participation_feature_id,
            StructuredFeatureId,
        ):
            raise StructuredNotePayoffValidationError(
                "participation_feature_id must be StructuredFeatureId or None"
            )
        if self.conversion_feature_id is not None and not isinstance(
            self.conversion_feature_id,
            StructuredFeatureId,
        ):
            raise StructuredNotePayoffValidationError(
                "conversion_feature_id must be StructuredFeatureId or None"
            )

        has_redemption = self.redemption_feature_id is not None
        has_participation = self.participation_feature_id is not None
        has_conversion = self.conversion_feature_id is not None

        if self.kind is StructuredNoteOutcomeKind.REDEMPTION:
            valid = has_redemption and not has_participation and not has_conversion
        elif self.kind is StructuredNoteOutcomeKind.REDEMPTION_WITH_PARTICIPATION:
            valid = has_redemption and has_participation and not has_conversion
        elif self.kind is StructuredNoteOutcomeKind.PARTICIPATION:
            valid = not has_redemption and has_participation and not has_conversion
        else:
            valid = not has_redemption and not has_participation and has_conversion

        if not valid:
            raise StructuredNotePayoffValidationError(
                "structured-note outcome feature references do not match outcome kind"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            self.redemption_feature_id.logical_values()
            if self.redemption_feature_id is not None
            else None,
            self.participation_feature_id.logical_values()
            if self.participation_feature_id is not None
            else None,
            self.conversion_feature_id.logical_values()
            if self.conversion_feature_id is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class StructuredNotePayoffBranch:
    """One ordered first-match branch over certified static UMI-09 features."""

    branch_id: StructuredNotePayoffBranchId
    ordinal: int
    condition_mode: StructuredNoteConditionMode | None
    condition_feature_ids: tuple[StructuredFeatureId, ...]
    outcome: StructuredNotePayoffOutcome
    evidence_ref: StructuredEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.branch_id, StructuredNotePayoffBranchId):
            raise StructuredNotePayoffValidationError(
                "structured-note branch_id must be StructuredNotePayoffBranchId"
            )
        if type(self.ordinal) is not int or self.ordinal <= 0:
            raise StructuredNotePayoffValidationError(
                "structured-note branch ordinal must be a positive int"
            )
        if self.condition_mode is not None and not isinstance(
            self.condition_mode,
            StructuredNoteConditionMode,
        ):
            raise StructuredNotePayoffValidationError(
                "structured-note condition_mode must be StructuredNoteConditionMode or None"
            )
        if type(self.condition_feature_ids) is not tuple:
            raise StructuredNotePayoffValidationError(
                "structured-note condition_feature_ids must be an immutable tuple"
            )
        for feature_id in self.condition_feature_ids:
            if not isinstance(feature_id, StructuredFeatureId):
                raise StructuredNotePayoffValidationError(
                    "structured-note conditions must contain StructuredFeatureId"
                )
        if len(set(self.condition_feature_ids)) != len(self.condition_feature_ids):
            raise StructuredNotePayoffValidationError(
                "structured-note condition feature ids must be unique"
            )
        if self.condition_mode is None:
            if self.condition_feature_ids:
                raise StructuredNotePayoffValidationError(
                    "structured-note fallback branch must not carry conditions"
                )
        elif not self.condition_feature_ids:
            raise StructuredNotePayoffValidationError(
                "structured-note conditional branch requires condition feature ids"
            )
        else:
            object.__setattr__(
                self,
                "condition_feature_ids",
                tuple(
                    sorted(
                        self.condition_feature_ids,
                        key=lambda feature_id: str(feature_id.value),
                    )
                ),
            )
        if not isinstance(self.outcome, StructuredNotePayoffOutcome):
            raise StructuredNotePayoffValidationError(
                "structured-note outcome must be StructuredNotePayoffOutcome"
            )
        if not isinstance(self.evidence_ref, StructuredEvidenceRef):
            raise StructuredNotePayoffValidationError(
                "structured-note branch evidence_ref must be StructuredEvidenceRef"
            )

    @property
    def is_fallback(self) -> bool:
        return self.condition_mode is None

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.branch_id.logical_values(),
            self.ordinal,
            self.condition_mode.value if self.condition_mode is not None else None,
            tuple(feature_id.logical_values() for feature_id in self.condition_feature_ids),
            self.outcome.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class StructuredNotePayoffTerms:
    """Conditional structured-note payoff qualification over exact UMI-09 terms."""

    terms_id: StructuredNotePayoffTermsId
    structured_terms: StructuredHybridSyntheticTerms
    branches: tuple[StructuredNotePayoffBranch, ...]
    evidence_ref: StructuredEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, StructuredNotePayoffTermsId):
            raise StructuredNotePayoffValidationError(
                "structured-note terms_id must be StructuredNotePayoffTermsId"
            )
        if not isinstance(self.structured_terms, StructuredHybridSyntheticTerms):
            raise StructuredNotePayoffValidationError(
                "structured_terms must be StructuredHybridSyntheticTerms"
            )
        if type(self.branches) is not tuple or len(self.branches) < 2:
            raise StructuredNotePayoffValidationError(
                "structured-note branches must be an immutable tuple with at least two branches"
            )
        for branch in self.branches:
            if not isinstance(branch, StructuredNotePayoffBranch):
                raise StructuredNotePayoffValidationError(
                    "structured-note branches must contain StructuredNotePayoffBranch"
                )

        branch_ids = tuple(branch.branch_id for branch in self.branches)
        if len(set(branch_ids)) != len(branch_ids):
            raise StructuredNotePayoffValidationError(
                "structured-note branch ids must be unique"
            )

        ordinals = tuple(branch.ordinal for branch in self.branches)
        if len(set(ordinals)) != len(ordinals):
            raise StructuredNotePayoffValidationError(
                "structured-note branch ordinals must be unique"
            )
        if set(ordinals) != set(range(1, len(self.branches) + 1)):
            raise StructuredNotePayoffValidationError(
                "structured-note branch ordinals must be contiguous from one"
            )
        ordered_branches = tuple(sorted(self.branches, key=lambda branch: branch.ordinal))
        object.__setattr__(self, "branches", ordered_branches)

        fallback_branches = tuple(branch for branch in self.branches if branch.is_fallback)
        if len(fallback_branches) != 1:
            raise StructuredNotePayoffValidationError(
                "structured-note payoff requires exactly one fallback branch"
            )
        if not self.branches[-1].is_fallback:
            raise StructuredNotePayoffValidationError(
                "structured-note fallback branch must be last"
            )

        condition_signatures = tuple(
            (branch.condition_mode, branch.condition_feature_ids)
            for branch in self.branches
            if not branch.is_fallback
        )
        if len(set(condition_signatures)) != len(condition_signatures):
            raise StructuredNotePayoffValidationError(
                "structured-note conditional branch signatures must be unique"
            )

        features_by_id = {
            feature.feature_id: feature for feature in self.structured_terms.features
        }

        for branch in self.branches:
            for feature_id in branch.condition_feature_ids:
                condition_feature = features_by_id.get(feature_id)
                if not isinstance(condition_feature, StructuredBarrierFeature):
                    raise StructuredNotePayoffValidationError(
                        "structured-note condition feature must resolve to StructuredBarrierFeature"
                    )
            outcome = branch.outcome
            if outcome.redemption_feature_id is not None:
                redemption_feature = features_by_id.get(outcome.redemption_feature_id)
                if not isinstance(redemption_feature, StructuredRedemptionFeature):
                    raise StructuredNotePayoffValidationError(
                        "structured-note redemption outcome must resolve to "
                        "StructuredRedemptionFeature"
                    )
            if outcome.participation_feature_id is not None:
                participation_feature = features_by_id.get(
                    outcome.participation_feature_id
                )
                if not isinstance(
                    participation_feature,
                    StructuredParticipationFeature,
                ):
                    raise StructuredNotePayoffValidationError(
                        "structured-note participation outcome must resolve to "
                        "StructuredParticipationFeature"
                    )
            if outcome.conversion_feature_id is not None:
                conversion_feature = features_by_id.get(outcome.conversion_feature_id)
                if not isinstance(conversion_feature, StructuredConversionFeature):
                    raise StructuredNotePayoffValidationError(
                        "structured-note conversion outcome must resolve to "
                        "StructuredConversionFeature"
                    )

        if not isinstance(self.evidence_ref, StructuredEvidenceRef):
            raise StructuredNotePayoffValidationError(
                "structured-note evidence_ref must be StructuredEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "structured-note-payoff",
            self.terms_id.logical_values(),
            self.structured_terms.logical_values(),
            tuple(branch.logical_values() for branch in self.branches),
            self.evidence_ref.logical_values(),
        )
