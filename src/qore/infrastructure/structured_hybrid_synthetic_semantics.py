from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    IdentityRelationship,
    IdentityRelationshipId,
)
from qore.kernel.errors import InfrastructureError


class StructuredHybridSyntheticSemanticsError(InfrastructureError):
    """Base error for provider-neutral structured/hybrid/synthetic semantics."""

    __slots__ = ()


class StructuredHybridSyntheticValidationError(StructuredHybridSyntheticSemanticsError):
    """Violation of a structured/hybrid/synthetic semantic invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if type(value) is not UUID:
        raise StructuredHybridSyntheticValidationError(f"{field_name} must be UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise StructuredHybridSyntheticValidationError(
            f"{field_name} must be EconomicIdentityId"
        )


def _validate_code(value: str, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise StructuredHybridSyntheticValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _validate_decimal(
    value: Decimal,
    *,
    field_name: str,
    positive: bool = False,
) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise StructuredHybridSyntheticValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if positive and value <= 0:
        raise StructuredHybridSyntheticValidationError(f"{field_name} must be positive")


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        raise StructuredHybridSyntheticValidationError(f"{field_name} must be date")


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class StructuredTermsId:
    """Local immutable terms identity; never an economic instrument identity."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="structured terms id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class StructuredFeatureId:
    """Local identity for one immutable structured feature."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="structured feature id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class StructuredEvidenceRef:
    """Opaque reference to retained evidence; never evidence content."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="structured evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class StructuredComponentRoleCode:
    """Local payoff/component qualification; never UMI-02 relationship authority."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="structured component role code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class StructuredBarrierKindCode:
    """Contractual barrier kind such as knock-in/knock-out; no event detection."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="structured barrier kind code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class StructuredObservationScheduleCode:
    """Externally governed observation schedule code; no scheduler authority."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="structured observation schedule code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class StructuredLevelUnitCode:
    """Contractual level unit/quotation basis; never inferred from magnitude."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="structured level unit code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class StructuredContractLevelKind(StrEnum):
    PRICE = "price"
    RATE = "rate"
    YIELD = "yield"
    SPREAD = "spread"
    LEVEL = "level"


class StructuredBarrierDirection(StrEnum):
    AT_OR_ABOVE = "at-or-above"
    AT_OR_BELOW = "at-or-below"


class StructuredObservationMode(StrEnum):
    CONTINUOUS = "continuous"
    DISCRETE = "discrete"


class StructuredParticipationDirection(StrEnum):
    POSITIVE = "positive"
    INVERSE = "inverse"


@dataclass(frozen=True, slots=True)
class StructuredPositiveRatio:
    """Positive exact ratio whose business meaning is supplied by the containing field."""

    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="structured ratio", positive=True)

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class StructuredContractLevel:
    """Declarative contractual level; never an observed price or option strike."""

    value: Decimal
    kind: StructuredContractLevelKind
    reference_identity_id: EconomicIdentityId
    unit: StructuredLevelUnitCode

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="structured contract level")
        if not isinstance(self.kind, StructuredContractLevelKind):
            raise StructuredHybridSyntheticValidationError(
                "structured contract level kind must be StructuredContractLevelKind"
            )
        _validate_identity(
            self.reference_identity_id,
            field_name="structured contract level reference identity",
        )
        if not isinstance(self.unit, StructuredLevelUnitCode):
            raise StructuredHybridSyntheticValidationError(
                "structured contract level unit must be StructuredLevelUnitCode"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            _canonical_decimal(self.value),
            self.kind.value,
            self.reference_identity_id.logical_values(),
            self.unit.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class StructuredObservationTerms:
    """Contractual observation cadence; it detects no event and resolves no calendar."""

    mode: StructuredObservationMode
    explicit_dates: tuple[date, ...] = ()
    schedule_code: StructuredObservationScheduleCode | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, StructuredObservationMode):
            raise StructuredHybridSyntheticValidationError(
                "structured observation mode must be StructuredObservationMode"
            )
        if type(self.explicit_dates) is not tuple:
            raise StructuredHybridSyntheticValidationError(
                "structured observation explicit_dates must be an immutable tuple"
            )
        for observation_date in self.explicit_dates:
            _validate_date(
                observation_date,
                field_name="structured observation explicit date",
            )
        if self.schedule_code is not None and not isinstance(
            self.schedule_code,
            StructuredObservationScheduleCode,
        ):
            raise StructuredHybridSyntheticValidationError(
                "structured observation schedule_code must be "
                "StructuredObservationScheduleCode or None"
            )

        if self.mode is StructuredObservationMode.CONTINUOUS:
            if self.explicit_dates or self.schedule_code is not None:
                raise StructuredHybridSyntheticValidationError(
                    "continuous observation must not carry dates or schedule code"
                )
            return

        modes = int(bool(self.explicit_dates)) + int(self.schedule_code is not None)
        if modes != 1:
            raise StructuredHybridSyntheticValidationError(
                "discrete observation requires exactly one dates or schedule-code mode"
            )
        if self.explicit_dates:
            if len(set(self.explicit_dates)) != len(self.explicit_dates):
                raise StructuredHybridSyntheticValidationError(
                    "structured observation dates must be unique"
                )
            object.__setattr__(
                self,
                "explicit_dates",
                tuple(sorted(self.explicit_dates)),
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mode.value,
            tuple(value.isoformat() for value in self.explicit_dates),
            self.schedule_code.logical_values()
            if self.schedule_code is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class StructuredComponentBinding:
    """One direct UMI-02 relationship qualified for structured-product use."""

    root_identity_id: EconomicIdentityId
    relationship: IdentityRelationship
    role: StructuredComponentRoleCode
    evidence_ref: StructuredEvidenceRef

    def __post_init__(self) -> None:
        _validate_identity(
            self.root_identity_id,
            field_name="structured component root identity",
        )
        if not isinstance(self.relationship, IdentityRelationship):
            raise StructuredHybridSyntheticValidationError(
                "structured component relationship must be IdentityRelationship"
            )
        if self.relationship.source_identity_id != self.root_identity_id:
            raise StructuredHybridSyntheticValidationError(
                "structured component relationship source must equal root identity"
            )
        if not isinstance(self.role, StructuredComponentRoleCode):
            raise StructuredHybridSyntheticValidationError(
                "structured component role must be StructuredComponentRoleCode"
            )
        if not isinstance(self.evidence_ref, StructuredEvidenceRef):
            raise StructuredHybridSyntheticValidationError(
                "structured component evidence_ref must be StructuredEvidenceRef"
            )

    @property
    def relationship_id(self) -> IdentityRelationshipId:
        return self.relationship.relationship_id

    @property
    def component_identity_id(self) -> EconomicIdentityId:
        return self.relationship.target_identity_id

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.root_identity_id.logical_values(),
            self.relationship.logical_values(),
            self.role.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class StructuredCapitalProtectionFeature:
    """Contractual principal-floor qualification; no credit/finality guarantee."""

    feature_id: StructuredFeatureId
    protected_identity_id: EconomicIdentityId
    protected_principal_ratio: StructuredPositiveRatio
    evidence_ref: StructuredEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.feature_id, StructuredFeatureId):
            raise StructuredHybridSyntheticValidationError(
                "capital protection feature_id must be StructuredFeatureId"
            )
        _validate_identity(
            self.protected_identity_id,
            field_name="capital protection protected identity",
        )
        if not isinstance(self.protected_principal_ratio, StructuredPositiveRatio):
            raise StructuredHybridSyntheticValidationError(
                "capital protection ratio must be StructuredPositiveRatio"
            )
        if not isinstance(self.evidence_ref, StructuredEvidenceRef):
            raise StructuredHybridSyntheticValidationError(
                "capital protection evidence_ref must be StructuredEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "capital-protection",
            self.feature_id.logical_values(),
            self.protected_identity_id.logical_values(),
            self.protected_principal_ratio.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class StructuredConversionFeature:
    """Declarative conversion/exchange right; it performs no conversion."""

    feature_id: StructuredFeatureId
    target_identity_id: EconomicIdentityId
    units_per_source_unit: StructuredPositiveRatio
    evidence_ref: StructuredEvidenceRef
    conversion_level: StructuredContractLevel | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.feature_id, StructuredFeatureId):
            raise StructuredHybridSyntheticValidationError(
                "conversion feature_id must be StructuredFeatureId"
            )
        _validate_identity(
            self.target_identity_id,
            field_name="conversion target identity",
        )
        if not isinstance(self.units_per_source_unit, StructuredPositiveRatio):
            raise StructuredHybridSyntheticValidationError(
                "conversion units_per_source_unit must be StructuredPositiveRatio"
            )
        if self.conversion_level is not None and not isinstance(
            self.conversion_level,
            StructuredContractLevel,
        ):
            raise StructuredHybridSyntheticValidationError(
                "conversion_level must be StructuredContractLevel or None"
            )
        if not isinstance(self.evidence_ref, StructuredEvidenceRef):
            raise StructuredHybridSyntheticValidationError(
                "conversion evidence_ref must be StructuredEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "conversion",
            self.feature_id.logical_values(),
            self.target_identity_id.logical_values(),
            self.units_per_source_unit.logical_values(),
            self.conversion_level.logical_values()
            if self.conversion_level is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class StructuredBarrierFeature:
    """Contractual barrier specification; it detects no barrier event."""

    feature_id: StructuredFeatureId
    reference_identity_id: EconomicIdentityId
    barrier_kind: StructuredBarrierKindCode
    direction: StructuredBarrierDirection
    level: StructuredContractLevel
    observation: StructuredObservationTerms
    evidence_ref: StructuredEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.feature_id, StructuredFeatureId):
            raise StructuredHybridSyntheticValidationError(
                "barrier feature_id must be StructuredFeatureId"
            )
        _validate_identity(
            self.reference_identity_id,
            field_name="barrier reference identity",
        )
        if not isinstance(self.barrier_kind, StructuredBarrierKindCode):
            raise StructuredHybridSyntheticValidationError(
                "barrier kind must be StructuredBarrierKindCode"
            )
        if not isinstance(self.direction, StructuredBarrierDirection):
            raise StructuredHybridSyntheticValidationError(
                "barrier direction must be StructuredBarrierDirection"
            )
        if not isinstance(self.level, StructuredContractLevel):
            raise StructuredHybridSyntheticValidationError(
                "barrier level must be StructuredContractLevel"
            )
        if self.level.reference_identity_id != self.reference_identity_id:
            raise StructuredHybridSyntheticValidationError(
                "barrier level reference must match barrier reference identity"
            )
        if not isinstance(self.observation, StructuredObservationTerms):
            raise StructuredHybridSyntheticValidationError(
                "barrier observation must be StructuredObservationTerms"
            )
        if not isinstance(self.evidence_ref, StructuredEvidenceRef):
            raise StructuredHybridSyntheticValidationError(
                "barrier evidence_ref must be StructuredEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "barrier",
            self.feature_id.logical_values(),
            self.reference_identity_id.logical_values(),
            self.barrier_kind.logical_values(),
            self.direction.value,
            self.level.logical_values(),
            self.observation.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class StructuredAutocallFeature:
    """Autocall contractual trigger specification; no trigger evaluation."""

    feature_id: StructuredFeatureId
    reference_identity_id: EconomicIdentityId
    trigger_level: StructuredContractLevel
    observation: StructuredObservationTerms
    redemption_ratio: StructuredPositiveRatio
    evidence_ref: StructuredEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.feature_id, StructuredFeatureId):
            raise StructuredHybridSyntheticValidationError(
                "autocall feature_id must be StructuredFeatureId"
            )
        _validate_identity(
            self.reference_identity_id,
            field_name="autocall reference identity",
        )
        if not isinstance(self.trigger_level, StructuredContractLevel):
            raise StructuredHybridSyntheticValidationError(
                "autocall trigger_level must be StructuredContractLevel"
            )
        if self.trigger_level.reference_identity_id != self.reference_identity_id:
            raise StructuredHybridSyntheticValidationError(
                "autocall trigger reference must match autocall reference identity"
            )
        if not isinstance(self.observation, StructuredObservationTerms):
            raise StructuredHybridSyntheticValidationError(
                "autocall observation must be StructuredObservationTerms"
            )
        if not isinstance(self.redemption_ratio, StructuredPositiveRatio):
            raise StructuredHybridSyntheticValidationError(
                "autocall redemption_ratio must be StructuredPositiveRatio"
            )
        if not isinstance(self.evidence_ref, StructuredEvidenceRef):
            raise StructuredHybridSyntheticValidationError(
                "autocall evidence_ref must be StructuredEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "autocall",
            self.feature_id.logical_values(),
            self.reference_identity_id.logical_values(),
            self.trigger_level.logical_values(),
            self.observation.logical_values(),
            self.redemption_ratio.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class StructuredParticipationFeature:
    """Contractual participation transform; no leverage/risk computation."""

    feature_id: StructuredFeatureId
    reference_identity_id: EconomicIdentityId
    direction: StructuredParticipationDirection
    participation_ratio: StructuredPositiveRatio
    evidence_ref: StructuredEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.feature_id, StructuredFeatureId):
            raise StructuredHybridSyntheticValidationError(
                "participation feature_id must be StructuredFeatureId"
            )
        _validate_identity(
            self.reference_identity_id,
            field_name="participation reference identity",
        )
        if not isinstance(self.direction, StructuredParticipationDirection):
            raise StructuredHybridSyntheticValidationError(
                "participation direction must be StructuredParticipationDirection"
            )
        if not isinstance(self.participation_ratio, StructuredPositiveRatio):
            raise StructuredHybridSyntheticValidationError(
                "participation ratio must be StructuredPositiveRatio"
            )
        if not isinstance(self.evidence_ref, StructuredEvidenceRef):
            raise StructuredHybridSyntheticValidationError(
                "participation evidence_ref must be StructuredEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "participation",
            self.feature_id.logical_values(),
            self.reference_identity_id.logical_values(),
            self.direction.value,
            self.participation_ratio.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class StructuredRedemptionFeature:
    """Contractual redemption qualification; no cash/position settlement mutation."""

    feature_id: StructuredFeatureId
    redemption_identity_id: EconomicIdentityId
    redemption_ratio: StructuredPositiveRatio
    evidence_ref: StructuredEvidenceRef
    redemption_date: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.feature_id, StructuredFeatureId):
            raise StructuredHybridSyntheticValidationError(
                "redemption feature_id must be StructuredFeatureId"
            )
        _validate_identity(
            self.redemption_identity_id,
            field_name="redemption identity",
        )
        if not isinstance(self.redemption_ratio, StructuredPositiveRatio):
            raise StructuredHybridSyntheticValidationError(
                "redemption ratio must be StructuredPositiveRatio"
            )
        if self.redemption_date is not None:
            _validate_date(
                self.redemption_date,
                field_name="structured redemption date",
            )
        if not isinstance(self.evidence_ref, StructuredEvidenceRef):
            raise StructuredHybridSyntheticValidationError(
                "redemption evidence_ref must be StructuredEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "redemption",
            self.feature_id.logical_values(),
            self.redemption_identity_id.logical_values(),
            self.redemption_ratio.logical_values(),
            self.redemption_date.isoformat()
            if self.redemption_date is not None
            else None,
            self.evidence_ref.logical_values(),
        )


type StructuredFeature = (
    StructuredCapitalProtectionFeature
    | StructuredConversionFeature
    | StructuredBarrierFeature
    | StructuredAutocallFeature
    | StructuredParticipationFeature
    | StructuredRedemptionFeature
)


_STRUCTURED_FEATURE_TYPES = (
    StructuredCapitalProtectionFeature,
    StructuredConversionFeature,
    StructuredBarrierFeature,
    StructuredAutocallFeature,
    StructuredParticipationFeature,
    StructuredRedemptionFeature,
)


def _feature_referenced_identities(
    feature: StructuredFeature,
) -> tuple[EconomicIdentityId, ...]:
    if isinstance(feature, StructuredCapitalProtectionFeature):
        return (feature.protected_identity_id,)
    if isinstance(feature, StructuredConversionFeature):
        return (feature.target_identity_id,)
    if isinstance(feature, StructuredBarrierFeature):
        return (feature.reference_identity_id,)
    if isinstance(feature, StructuredAutocallFeature):
        return (feature.reference_identity_id,)
    if isinstance(feature, StructuredParticipationFeature):
        return (feature.reference_identity_id,)
    return (feature.redemption_identity_id,)


@dataclass(frozen=True, slots=True)
class StructuredHybridSyntheticTerms:
    """Higher-order structured/hybrid/synthetic contractual qualification."""

    terms_id: StructuredTermsId
    instrument_identity_id: EconomicIdentityId
    components: tuple[StructuredComponentBinding, ...]
    features: tuple[StructuredFeature, ...]
    evidence_ref: StructuredEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, StructuredTermsId):
            raise StructuredHybridSyntheticValidationError(
                "structured terms_id must be StructuredTermsId"
            )
        _validate_identity(
            self.instrument_identity_id,
            field_name="structured instrument identity",
        )
        if type(self.components) is not tuple or not self.components:
            raise StructuredHybridSyntheticValidationError(
                "structured components must be a non-empty immutable tuple"
            )
        for component in self.components:
            if not isinstance(component, StructuredComponentBinding):
                raise StructuredHybridSyntheticValidationError(
                    "structured components must contain StructuredComponentBinding"
                )
            if component.root_identity_id != self.instrument_identity_id:
                raise StructuredHybridSyntheticValidationError(
                    "structured component root must equal structured instrument identity"
                )

        relationship_ids = tuple(
            component.relationship.relationship_id for component in self.components
        )
        if len(set(relationship_ids)) != len(relationship_ids):
            raise StructuredHybridSyntheticValidationError(
                "structured component relationship ids must be unique"
            )
        ordered_components = tuple(
            sorted(
                self.components,
                key=lambda component: str(
                    component.relationship.relationship_id.value
                ),
            )
        )
        object.__setattr__(self, "components", ordered_components)

        if type(self.features) is not tuple or not self.features:
            raise StructuredHybridSyntheticValidationError(
                "structured features must be a non-empty immutable tuple"
            )
        for feature in self.features:
            if not isinstance(feature, _STRUCTURED_FEATURE_TYPES):
                raise StructuredHybridSyntheticValidationError(
                    "structured features must contain certified UMI-09 feature types"
                )

        feature_ids = tuple(feature.feature_id for feature in self.features)
        if len(set(feature_ids)) != len(feature_ids):
            raise StructuredHybridSyntheticValidationError(
                "structured feature ids must be unique"
            )
        ordered_features = tuple(
            sorted(self.features, key=lambda feature: str(feature.feature_id.value))
        )
        object.__setattr__(self, "features", ordered_features)

        component_targets = {
            component.component_identity_id for component in self.components
        }
        for feature in self.features:
            for referenced_identity in _feature_referenced_identities(feature):
                if referenced_identity not in component_targets:
                    raise StructuredHybridSyntheticValidationError(
                        "structured feature identity must be a direct component target"
                    )

        if not isinstance(self.evidence_ref, StructuredEvidenceRef):
            raise StructuredHybridSyntheticValidationError(
                "structured evidence_ref must be StructuredEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "structured-hybrid-synthetic",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            tuple(component.logical_values() for component in self.components),
            tuple(feature.logical_values() for feature in self.features),
            self.evidence_ref.logical_values(),
        )
