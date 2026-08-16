from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from re import fullmatch
from uuid import UUID

from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class EventContractSemanticsError(InfrastructureError):
    """Base error for bounded static event-contract semantics."""

    __slots__ = ()


class EventContractValidationError(EventContractSemanticsError):
    """Violation of a static event-contract invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise EventContractValidationError(f"{field_name} must be UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise EventContractValidationError(
            f"{field_name} must be EconomicIdentityId"
        )


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        raise EventContractValidationError(f"{field_name} must be date")


def _validate_code(value: str, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 96
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise EventContractValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _validate_decimal(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise EventContractValidationError(
            f"{field_name} must be a non-negative finite Decimal"
        )


def _canonical_decimal(value: Decimal) -> str:
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class EventContractTermsId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="event-contract terms ID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class EventEvidenceRef:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="event-contract evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class EventSubjectReferenceId:
    """Opaque contractual subject reference; not an external-data fetch key."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="event subject reference ID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class EventResolutionAuthorityRef:
    """Opaque contractual authority reference; not a legal-identity registry."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="event resolution authority reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class EventCriterionCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event criterion code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EventOutcomeStructureCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event outcome structure code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EventOutcomeCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event outcome code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EventResolutionSourceCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event resolution source code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EventResolutionRuleCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event resolution rule code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EventCorrectionPolicyCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event correction policy code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EventSourceConflictPolicyCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event source-conflict policy code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EventCashPayout:
    amount: Decimal
    currency_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        _validate_decimal(self.amount, field_name="event contractual payout")
        _validate_identity(
            self.currency_identity_id,
            field_name="event payout currency identity",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            _canonical_decimal(self.amount),
            self.currency_identity_id.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class EventOutcomeTerms:
    outcome_code: EventOutcomeCode
    payout: EventCashPayout

    def __post_init__(self) -> None:
        if not isinstance(self.outcome_code, EventOutcomeCode):
            raise EventContractValidationError(
                "event outcome_code must be EventOutcomeCode"
            )
        if not isinstance(self.payout, EventCashPayout):
            raise EventContractValidationError(
                "event payout must be EventCashPayout"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.outcome_code.logical_values(), self.payout.logical_values())


@dataclass(frozen=True, slots=True)
class EventResolutionTerms:
    """Static resolution authority/sources/policies, never resolved outcome state."""

    authority_ref: EventResolutionAuthorityRef
    primary_source_codes: tuple[EventResolutionSourceCode, ...]
    resolution_rule_code: EventResolutionRuleCode
    correction_policy_code: EventCorrectionPolicyCode
    source_conflict_policy_code: EventSourceConflictPolicyCode
    fallback_source_codes: tuple[EventResolutionSourceCode, ...] = ()
    scheduled_resolution_date: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.authority_ref, EventResolutionAuthorityRef):
            raise EventContractValidationError(
                "event resolution authority_ref must be typed"
            )
        self._validate_sources(
            self.primary_source_codes,
            field_name="event primary resolution sources",
            allow_empty=False,
        )
        self._validate_sources(
            self.fallback_source_codes,
            field_name="event fallback resolution sources",
            allow_empty=True,
        )
        primary = set(self.primary_source_codes)
        fallback = set(self.fallback_source_codes)
        if primary.intersection(fallback):
            raise EventContractValidationError(
                "primary and fallback resolution sources must be disjoint"
            )
        if not isinstance(self.resolution_rule_code, EventResolutionRuleCode):
            raise EventContractValidationError(
                "event resolution_rule_code must be typed"
            )
        if not isinstance(self.correction_policy_code, EventCorrectionPolicyCode):
            raise EventContractValidationError(
                "event correction_policy_code must be typed"
            )
        if not isinstance(
            self.source_conflict_policy_code,
            EventSourceConflictPolicyCode,
        ):
            raise EventContractValidationError(
                "event source_conflict_policy_code must be typed"
            )
        if self.scheduled_resolution_date is not None:
            _validate_date(
                self.scheduled_resolution_date,
                field_name="event scheduled resolution date",
            )

    @staticmethod
    def _validate_sources(
        sources: tuple[EventResolutionSourceCode, ...],
        *,
        field_name: str,
        allow_empty: bool,
    ) -> None:
        if type(sources) is not tuple:
            raise EventContractValidationError(f"{field_name} must be tuple")
        if not sources and not allow_empty:
            raise EventContractValidationError(f"{field_name} must not be empty")
        for source in sources:
            if not isinstance(source, EventResolutionSourceCode):
                raise EventContractValidationError(
                    f"{field_name} must contain EventResolutionSourceCode"
                )
        if len(set(sources)) != len(sources):
            raise EventContractValidationError(
                f"{field_name} must not contain duplicate sources"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.authority_ref.logical_values(),
            tuple(source.logical_values() for source in self.primary_source_codes),
            tuple(source.logical_values() for source in self.fallback_source_codes),
            self.resolution_rule_code.logical_values(),
            self.correction_policy_code.logical_values(),
            self.source_conflict_policy_code.logical_values(),
            self.scheduled_resolution_date.isoformat()
            if self.scheduled_resolution_date is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class EventContractTerms:
    """Static event contract definition with no current/resolved outcome state."""

    terms_id: EventContractTermsId
    instrument_identity_id: EconomicIdentityId
    subject_reference_id: EventSubjectReferenceId
    criterion_code: EventCriterionCode
    outcome_structure_code: EventOutcomeStructureCode
    outcomes: tuple[EventOutcomeTerms, ...]
    resolution_terms: EventResolutionTerms
    evidence_ref: EventEvidenceRef
    expiration_date: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, EventContractTermsId):
            raise EventContractValidationError(
                "event-contract terms_id must be EventContractTermsId"
            )
        _validate_identity(
            self.instrument_identity_id,
            field_name="event-contract instrument identity",
        )
        if not isinstance(self.subject_reference_id, EventSubjectReferenceId):
            raise EventContractValidationError(
                "event-contract subject_reference_id must be typed"
            )
        if not isinstance(self.criterion_code, EventCriterionCode):
            raise EventContractValidationError(
                "event-contract criterion_code must be typed"
            )
        if not isinstance(
            self.outcome_structure_code,
            EventOutcomeStructureCode,
        ):
            raise EventContractValidationError(
                "event-contract outcome_structure_code must be typed"
            )
        if type(self.outcomes) is not tuple or len(self.outcomes) < 2:
            raise EventContractValidationError(
                "event-contract outcomes must be a tuple with at least two entries"
            )
        for outcome in self.outcomes:
            if not isinstance(outcome, EventOutcomeTerms):
                raise EventContractValidationError(
                    "event-contract outcomes must contain EventOutcomeTerms"
                )
        outcome_codes = tuple(outcome.outcome_code for outcome in self.outcomes)
        if len(set(outcome_codes)) != len(outcome_codes):
            raise EventContractValidationError(
                "event-contract outcome codes must be unique"
            )
        if not isinstance(self.resolution_terms, EventResolutionTerms):
            raise EventContractValidationError(
                "event-contract resolution_terms must be typed"
            )
        if not isinstance(self.evidence_ref, EventEvidenceRef):
            raise EventContractValidationError(
                "event-contract evidence_ref must be EventEvidenceRef"
            )
        if self.expiration_date is not None:
            _validate_date(
                self.expiration_date,
                field_name="event-contract expiration date",
            )
        scheduled = self.resolution_terms.scheduled_resolution_date
        if (
            self.expiration_date is not None
            and scheduled is not None
            and scheduled < self.expiration_date
        ):
            raise EventContractValidationError(
                "scheduled resolution date must not precede expiration date"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "event-contract",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.subject_reference_id.logical_values(),
            self.criterion_code.logical_values(),
            self.outcome_structure_code.logical_values(),
            tuple(outcome.logical_values() for outcome in self.outcomes),
            self.expiration_date.isoformat()
            if self.expiration_date is not None
            else None,
            self.resolution_terms.logical_values(),
            self.evidence_ref.logical_values(),
        )
