from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.fixed_income_economics import (
    CompoundingConventionCode,
    DayCountConventionCode,
    FinancialTenor,
    FixedIncomeSpread,
    FixedIncomeYield,
    YieldConvention,
)
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class RateTermStructureError(InfrastructureError):
    """Base error for rate/curve/term-structure contracts."""

    __slots__ = ()


class RateTermStructureValidationError(RateTermStructureError):
    """Violation of a rate/curve/term-structure invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise RateTermStructureValidationError(f"{field_name} must be UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise RateTermStructureValidationError(
            f"{field_name} must be EconomicIdentityId"
        )


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise RateTermStructureValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise RateTermStructureValidationError(
            f"{field_name} must be timezone-aware"
        )


def _canonical_timestamp(value: datetime, *, field_name: str) -> str:
    _validate_timestamp(value, field_name=field_name)
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _validate_code(value: str, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise RateTermStructureValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _validate_decimal(
    value: Decimal,
    *,
    field_name: str,
    positive: bool = False,
) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise RateTermStructureValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if positive and value <= 0:
        raise RateTermStructureValidationError(f"{field_name} must be positive")


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class RateTermStructureSnapshotId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="rate term-structure snapshot id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class RateTermStructureNodeId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="rate term-structure node id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class RateTermStructureEvidenceRef:
    """Opaque reference to retained curve/node evidence; never evidence content."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="rate term-structure evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class RateTermStructureInputFingerprint:
    """Deterministic SHA-256 input-set fingerprint; not retained source evidence."""

    value: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, str)
            or fullmatch(r"[0-9a-f]{64}", self.value) is None
        ):
            raise RateTermStructureValidationError(
                "rate term-structure input fingerprint must be lowercase sha256 hex"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class RateTermStructureKindCode:
    """Extensible economic role such as government, swap, or OIS curve."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="rate term-structure kind code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class RateTermStructureMethodologyCode:
    """Extensible provenance methodology; this type implements no algorithm."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="rate term-structure methodology code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class RateTermStructureProvenanceKind(StrEnum):
    OBSERVED = "observed"
    COMPUTED = "computed"


class RateTermStructureMeasure(StrEnum):
    ZERO_RATE = "zero-rate"
    PAR_RATE = "par-rate"
    FORWARD_RATE = "forward-rate"
    YIELD = "yield"
    SPREAD = "spread"
    DISCOUNT_FACTOR = "discount-factor"


@dataclass(frozen=True, slots=True)
class ZeroRate:
    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="zero rate")

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class ParRate:
    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="par rate")

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class ForwardRate:
    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="forward rate")

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class DiscountFactor:
    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(
            self.value,
            field_name="discount factor",
            positive=True,
        )

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class RateCurveConvention:
    """Rate quotation convention; stores semantics and performs no calculation."""

    day_count: DayCountConventionCode
    compounding: CompoundingConventionCode
    compounding_tenor: FinancialTenor | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.day_count, DayCountConventionCode):
            raise RateTermStructureValidationError(
                "rate curve day_count must be DayCountConventionCode"
            )
        if not isinstance(self.compounding, CompoundingConventionCode):
            raise RateTermStructureValidationError(
                "rate curve compounding must be CompoundingConventionCode"
            )
        if self.compounding_tenor is not None and not isinstance(
            self.compounding_tenor, FinancialTenor
        ):
            raise RateTermStructureValidationError(
                "rate curve compounding_tenor must be FinancialTenor or None"
            )
        if self.compounding.value == "periodic" and self.compounding_tenor is None:
            raise RateTermStructureValidationError(
                "periodic rate compounding requires compounding_tenor"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "rate-convention",
            self.day_count.logical_values(),
            self.compounding.logical_values(),
            self.compounding_tenor.logical_values()
            if self.compounding_tenor is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class RateTermStructureNodeOrdinal:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise RateTermStructureValidationError(
                "rate term-structure node ordinal must be a positive int"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ForwardRatePeriod:
    """Forward interval without converting calendar/financial tenor to fixed seconds."""

    start_tenor: FinancialTenor | None
    period_tenor: FinancialTenor

    def __post_init__(self) -> None:
        if self.start_tenor is not None and not isinstance(
            self.start_tenor, FinancialTenor
        ):
            raise RateTermStructureValidationError(
                "forward rate start_tenor must be FinancialTenor or None"
            )
        if not isinstance(self.period_tenor, FinancialTenor):
            raise RateTermStructureValidationError(
                "forward rate period_tenor must be FinancialTenor"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "forward-period",
            self.start_tenor.logical_values()
            if self.start_tenor is not None
            else None,
            self.period_tenor.logical_values(),
        )


type RateTermStructureConvention = RateCurveConvention | YieldConvention
type RateTermStructureNodeCoordinate = FinancialTenor | ForwardRatePeriod
type RateTermStructureNodeValue = (
    ZeroRate
    | ParRate
    | ForwardRate
    | FixedIncomeYield
    | FixedIncomeSpread
    | DiscountFactor
)


@dataclass(frozen=True, slots=True)
class RateTermStructureProvenance:
    kind: RateTermStructureProvenanceKind
    methodology: RateTermStructureMethodologyCode
    evidence_ref: RateTermStructureEvidenceRef
    source: ExternalSourceDescriptor | None = None
    input_fingerprint: RateTermStructureInputFingerprint | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, RateTermStructureProvenanceKind):
            raise RateTermStructureValidationError(
                "rate term-structure provenance kind must be "
                "RateTermStructureProvenanceKind"
            )
        if not isinstance(self.methodology, RateTermStructureMethodologyCode):
            raise RateTermStructureValidationError(
                "rate term-structure methodology must be "
                "RateTermStructureMethodologyCode"
            )
        if not isinstance(self.evidence_ref, RateTermStructureEvidenceRef):
            raise RateTermStructureValidationError(
                "rate term-structure provenance evidence_ref must be "
                "RateTermStructureEvidenceRef"
            )
        if self.source is not None and not isinstance(
            self.source, ExternalSourceDescriptor
        ):
            raise RateTermStructureValidationError(
                "rate term-structure provenance source must be "
                "ExternalSourceDescriptor or None"
            )
        if self.input_fingerprint is not None and not isinstance(
            self.input_fingerprint, RateTermStructureInputFingerprint
        ):
            raise RateTermStructureValidationError(
                "rate term-structure input_fingerprint must be "
                "RateTermStructureInputFingerprint or None"
            )
        if self.kind is RateTermStructureProvenanceKind.OBSERVED:
            if self.source is None:
                raise RateTermStructureValidationError(
                    "observed rate term structure requires external source"
                )
            if self.input_fingerprint is not None:
                raise RateTermStructureValidationError(
                    "observed rate term structure must not claim computed "
                    "input fingerprint"
                )
        elif self.input_fingerprint is None:
            raise RateTermStructureValidationError(
                "computed rate term structure requires input fingerprint"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            self.methodology.logical_values(),
            self.evidence_ref.logical_values(),
            self.source.logical_values() if self.source is not None else None,
            self.input_fingerprint.logical_values()
            if self.input_fingerprint is not None
            else None,
        )


def _coordinate_logical_values(
    coordinate: RateTermStructureNodeCoordinate,
) -> tuple[object, ...]:
    if isinstance(coordinate, FinancialTenor):
        return ("tenor", coordinate.logical_values())
    return coordinate.logical_values()


def _coordinate_key(coordinate: RateTermStructureNodeCoordinate) -> str:
    if isinstance(coordinate, FinancialTenor):
        return f"tenor:{coordinate.value}:{coordinate.unit.value}"
    if coordinate.start_tenor is None:
        start = "spot"
    else:
        start = f"{coordinate.start_tenor.value}:{coordinate.start_tenor.unit.value}"
    return (
        f"forward:{start}:"
        f"{coordinate.period_tenor.value}:{coordinate.period_tenor.unit.value}"
    )


def _node_value_logical_values(
    value: RateTermStructureNodeValue,
) -> tuple[object, ...]:
    if isinstance(value, ZeroRate):
        return ("zero-rate", value.logical_values())
    if isinstance(value, ParRate):
        return ("par-rate", value.logical_values())
    if isinstance(value, ForwardRate):
        return ("forward-rate", value.logical_values())
    if isinstance(value, FixedIncomeYield):
        return ("yield", value.logical_values())
    if isinstance(value, FixedIncomeSpread):
        return ("spread", value.logical_values())
    return ("discount-factor", value.logical_values())


@dataclass(frozen=True, slots=True)
class RateTermStructureNode:
    node_id: RateTermStructureNodeId
    ordinal: RateTermStructureNodeOrdinal
    coordinate: RateTermStructureNodeCoordinate
    value: RateTermStructureNodeValue
    evidence_ref: RateTermStructureEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.node_id, RateTermStructureNodeId):
            raise RateTermStructureValidationError(
                "rate term-structure node_id must be RateTermStructureNodeId"
            )
        if not isinstance(self.ordinal, RateTermStructureNodeOrdinal):
            raise RateTermStructureValidationError(
                "rate term-structure ordinal must be RateTermStructureNodeOrdinal"
            )
        if not isinstance(self.coordinate, (FinancialTenor, ForwardRatePeriod)):
            raise RateTermStructureValidationError(
                "rate term-structure coordinate must be "
                "FinancialTenor or ForwardRatePeriod"
            )
        if not isinstance(
            self.value,
            (
                ZeroRate,
                ParRate,
                ForwardRate,
                FixedIncomeYield,
                FixedIncomeSpread,
                DiscountFactor,
            ),
        ):
            raise RateTermStructureValidationError(
                "rate term-structure node value must be a certified curve value type"
            )
        if not isinstance(self.evidence_ref, RateTermStructureEvidenceRef):
            raise RateTermStructureValidationError(
                "rate term-structure node evidence_ref must be "
                "RateTermStructureEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.node_id.logical_values(),
            self.ordinal.logical_values(),
            _coordinate_logical_values(self.coordinate),
            _node_value_logical_values(self.value),
            self.evidence_ref.logical_values(),
        )


def _node_matches_measure(
    measure: RateTermStructureMeasure,
    node: RateTermStructureNode,
) -> bool:
    if measure is RateTermStructureMeasure.ZERO_RATE:
        return isinstance(node.coordinate, FinancialTenor) and isinstance(
            node.value, ZeroRate
        )
    if measure is RateTermStructureMeasure.PAR_RATE:
        return isinstance(node.coordinate, FinancialTenor) and isinstance(
            node.value, ParRate
        )
    if measure is RateTermStructureMeasure.FORWARD_RATE:
        return isinstance(node.coordinate, ForwardRatePeriod) and isinstance(
            node.value, ForwardRate
        )
    if measure is RateTermStructureMeasure.YIELD:
        return isinstance(node.coordinate, FinancialTenor) and isinstance(
            node.value, FixedIncomeYield
        )
    if measure is RateTermStructureMeasure.SPREAD:
        return isinstance(node.coordinate, FinancialTenor) and isinstance(
            node.value, FixedIncomeSpread
        )
    return isinstance(node.coordinate, FinancialTenor) and isinstance(
        node.value, DiscountFactor
    )


def _convention_matches_measure(
    measure: RateTermStructureMeasure,
    convention: RateTermStructureConvention | None,
) -> bool:
    if measure in (
        RateTermStructureMeasure.ZERO_RATE,
        RateTermStructureMeasure.PAR_RATE,
        RateTermStructureMeasure.FORWARD_RATE,
    ):
        return isinstance(convention, RateCurveConvention)
    if measure is RateTermStructureMeasure.YIELD:
        return isinstance(convention, YieldConvention)
    return convention is None


def _convention_logical_values(
    convention: RateTermStructureConvention | None,
) -> tuple[object, ...] | None:
    if convention is None:
        return None
    if isinstance(convention, RateCurveConvention):
        return convention.logical_values()
    return ("yield-convention", convention.logical_values())


@dataclass(frozen=True, slots=True)
class RateTermStructureSnapshot:
    """Immutable retained curve snapshot without interpolation or valuation engine."""

    snapshot_id: RateTermStructureSnapshotId
    curve_identity_id: EconomicIdentityId
    currency_identity_id: EconomicIdentityId
    curve_kind: RateTermStructureKindCode
    measure: RateTermStructureMeasure
    convention: RateTermStructureConvention | None
    as_of: datetime
    recorded_at: datetime
    provenance: RateTermStructureProvenance
    nodes: tuple[RateTermStructureNode, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, RateTermStructureSnapshotId):
            raise RateTermStructureValidationError(
                "rate term-structure snapshot_id must be RateTermStructureSnapshotId"
            )
        _validate_identity(
            self.curve_identity_id,
            field_name="rate term-structure curve identity",
        )
        _validate_identity(
            self.currency_identity_id,
            field_name="rate term-structure currency identity",
        )
        if self.curve_identity_id == self.currency_identity_id:
            raise RateTermStructureValidationError(
                "curve identity and currency identity must differ"
            )
        if not isinstance(self.curve_kind, RateTermStructureKindCode):
            raise RateTermStructureValidationError(
                "rate term-structure curve_kind must be RateTermStructureKindCode"
            )
        if not isinstance(self.measure, RateTermStructureMeasure):
            raise RateTermStructureValidationError(
                "rate term-structure measure must be RateTermStructureMeasure"
            )
        if not _convention_matches_measure(self.measure, self.convention):
            raise RateTermStructureValidationError(
                "rate term-structure convention must match measure"
            )
        _validate_timestamp(self.as_of, field_name="rate term-structure as_of")
        _validate_timestamp(
            self.recorded_at,
            field_name="rate term-structure recorded_at",
        )
        if self.recorded_at < self.as_of:
            raise RateTermStructureValidationError(
                "rate term-structure recorded_at must not predate as_of"
            )
        if not isinstance(self.provenance, RateTermStructureProvenance):
            raise RateTermStructureValidationError(
                "rate term-structure provenance must be RateTermStructureProvenance"
            )
        if type(self.nodes) is not tuple or not self.nodes:
            raise RateTermStructureValidationError(
                "rate term-structure nodes must be a non-empty tuple"
            )
        for node in self.nodes:
            if not isinstance(node, RateTermStructureNode):
                raise RateTermStructureValidationError(
                    "rate term-structure nodes must contain RateTermStructureNode"
                )
            if not _node_matches_measure(self.measure, node):
                raise RateTermStructureValidationError(
                    "rate term-structure node coordinate/value must match measure"
                )

        node_ids = tuple(node.node_id for node in self.nodes)
        if len(set(node_ids)) != len(node_ids):
            raise RateTermStructureValidationError(
                "rate term-structure node ids must be unique"
            )

        ordinals = tuple(node.ordinal.value for node in self.nodes)
        if len(set(ordinals)) != len(ordinals):
            raise RateTermStructureValidationError(
                "rate term-structure node ordinals must be unique"
            )

        coordinate_keys = tuple(_coordinate_key(node.coordinate) for node in self.nodes)
        if len(set(coordinate_keys)) != len(coordinate_keys):
            raise RateTermStructureValidationError(
                "rate term-structure node coordinates must be unique"
            )

        ordered = tuple(sorted(self.nodes, key=lambda node: node.ordinal.value))
        expected_ordinals = tuple(range(1, len(ordered) + 1))
        actual_ordinals = tuple(node.ordinal.value for node in ordered)
        if actual_ordinals != expected_ordinals:
            raise RateTermStructureValidationError(
                "rate term-structure node ordinals must be contiguous from 1"
            )
        object.__setattr__(self, "nodes", ordered)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.snapshot_id.logical_values(),
            self.curve_identity_id.logical_values(),
            self.currency_identity_id.logical_values(),
            self.curve_kind.logical_values(),
            self.measure.value,
            _convention_logical_values(self.convention),
            _canonical_timestamp(
                self.as_of,
                field_name="rate term-structure as_of",
            ),
            _canonical_timestamp(
                self.recorded_at,
                field_name="rate term-structure recorded_at",
            ),
            self.provenance.logical_values(),
            tuple(node.logical_values() for node in self.nodes),
        )
