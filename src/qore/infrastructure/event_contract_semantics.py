from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from re import fullmatch
from typing import Never
from uuid import UUID

from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class EventContractSemanticsError(InfrastructureError):
    """Base error for bounded static event-contract semantics."""

    __slots__ = ()


class EventContractValidationError(EventContractSemanticsError):
    """Violation of a static event-contract invariant."""

    __slots__ = ()


def _fail(message: str) -> Never:
    raise EventContractValidationError(message)


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if type(value) is not UUID:
        _fail(f"{field_name} must be exact UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if type(value) is not EconomicIdentityId:
        _fail(f"{field_name} must be exact EconomicIdentityId")
    _validate_uuid(value.value, field_name=f"{field_name}.value")


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        _fail(f"{field_name} must be exact date")


def _validate_code(value: str, *, field_name: str) -> None:
    valid = (
        type(value) is str
        and bool(value)
        and len(value) <= 96
        and fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is not None
    )
    if not valid:
        _fail(f"{field_name} must use canonical lowercase code syntax")


def _validate_decimal(value: Decimal, *, field_name: str) -> None:
    if type(value) is not Decimal or not value.is_finite():
        _fail(f"{field_name} must be a finite exact Decimal")
    if value < 0:
        _fail(f"{field_name} must be non-negative")


def _canonical_decimal(value: Decimal) -> str:
    """Context-independent compact finite-Decimal representation."""

    parts = value.as_tuple()
    digits = list(parts.digits)
    if not any(digits):
        return "0"

    exponent = int(parts.exponent)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1

    digit_text = "".join(str(digit) for digit in digits)
    sign = "-" if parts.sign else ""
    adjusted_exponent = exponent + len(digits) - 1
    mantissa = digit_text[0]
    if len(digit_text) > 1:
        mantissa += "." + digit_text[1:]
    exponent_sign = "+" if adjusted_exponent >= 0 else ""
    compact = f"{sign}{mantissa}e{exponent_sign}{adjusted_exponent}"

    if exponent >= 0:
        fixed_length = len(sign) + len(digit_text) + exponent
    else:
        point = len(digit_text) + exponent
        if point > 0:
            fixed_length = len(sign) + len(digit_text) + 1
        else:
            fixed_length = len(sign) + 2 + (-point) + len(digit_text)

    if fixed_length > len(compact) + 1:
        return compact

    if exponent >= 0:
        fixed = digit_text + ("0" * exponent)
    else:
        point = len(digit_text) + exponent
        if point > 0:
            fixed = digit_text[:point] + "." + digit_text[point:]
        else:
            fixed = "0." + ("0" * (-point)) + digit_text
    return sign + fixed


def _identity_values(value: EconomicIdentityId, *, field_name: str) -> tuple[str, ...]:
    _validate_identity(value, field_name=field_name)
    return (str(value.value),)


@dataclass(frozen=True, slots=True)
class EventContractTermsId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="event-contract terms ID")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class EventEvidenceRef:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="event-contract evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class EventSubjectReferenceId:
    """Opaque contractual subject reference; never an external-data fetch key."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="event subject reference ID")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class EventResolutionAuthorityRef:
    """Opaque contractual resolution-authority reference; not legal identity."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="event resolution authority reference")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class EventCriterionCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event criterion code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EventOutcomeStructureCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event outcome structure code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EventOutcomeCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event outcome code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EventResolutionSourceCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event resolution source code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EventResolutionRuleCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event resolution rule code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EventCorrectionPolicyCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event correction policy code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EventSourceConflictPolicyCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="event source-conflict policy code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


def _validate_terms_id_child(value: EventContractTermsId) -> None:
    if type(value) is not EventContractTermsId:
        _fail("event-contract terms_id must be exact EventContractTermsId")
    _validate_uuid(value.value, field_name="event-contract terms_id.value")


def _validate_evidence_child(value: EventEvidenceRef) -> None:
    if type(value) is not EventEvidenceRef:
        _fail("event-contract evidence_ref must be exact EventEvidenceRef")
    _validate_uuid(value.value, field_name="event-contract evidence_ref.value")


def _validate_subject_child(value: EventSubjectReferenceId) -> None:
    if type(value) is not EventSubjectReferenceId:
        _fail("event-contract subject_reference_id must be exact EventSubjectReferenceId")
    _validate_uuid(value.value, field_name="event-contract subject_reference_id.value")


def _validate_authority_child(value: EventResolutionAuthorityRef) -> None:
    if type(value) is not EventResolutionAuthorityRef:
        _fail("event resolution authority_ref must be exact EventResolutionAuthorityRef")
    _validate_uuid(value.value, field_name="event resolution authority_ref.value")


def _validate_criterion_child(value: EventCriterionCode) -> None:
    if type(value) is not EventCriterionCode:
        _fail("event-contract criterion_code must be exact EventCriterionCode")
    _validate_code(value.value, field_name="event criterion code")


def _validate_structure_child(value: EventOutcomeStructureCode) -> None:
    if type(value) is not EventOutcomeStructureCode:
        _fail("event-contract outcome_structure_code must be exact EventOutcomeStructureCode")
    _validate_code(value.value, field_name="event outcome structure code")


def _validate_outcome_code_child(value: EventOutcomeCode) -> None:
    if type(value) is not EventOutcomeCode:
        _fail("event outcome_code must be exact EventOutcomeCode")
    _validate_code(value.value, field_name="event outcome code")


def _validate_source_child(value: EventResolutionSourceCode, *, field_name: str) -> None:
    if type(value) is not EventResolutionSourceCode:
        _fail(f"{field_name} must contain exact EventResolutionSourceCode")
    _validate_code(value.value, field_name="event resolution source code")


def _validate_rule_child(value: EventResolutionRuleCode) -> None:
    if type(value) is not EventResolutionRuleCode:
        _fail("event resolution_rule_code must be exact EventResolutionRuleCode")
    _validate_code(value.value, field_name="event resolution rule code")


def _validate_correction_child(value: EventCorrectionPolicyCode) -> None:
    if type(value) is not EventCorrectionPolicyCode:
        _fail("event correction_policy_code must be exact EventCorrectionPolicyCode")
    _validate_code(value.value, field_name="event correction policy code")


def _validate_conflict_child(value: EventSourceConflictPolicyCode) -> None:
    if type(value) is not EventSourceConflictPolicyCode:
        _fail("event source_conflict_policy_code must be exact EventSourceConflictPolicyCode")
    _validate_code(value.value, field_name="event source-conflict policy code")


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
        self.__post_init__()
        return (
            _canonical_decimal(self.amount),
            _identity_values(
                self.currency_identity_id,
                field_name="event payout currency identity",
            ),
        )


def _validate_payout_child(value: EventCashPayout) -> None:
    if type(value) is not EventCashPayout:
        _fail("event payout must be exact EventCashPayout")
    value.__post_init__()


@dataclass(frozen=True, slots=True)
class EventOutcomeTerms:
    outcome_code: EventOutcomeCode
    payout: EventCashPayout

    def __post_init__(self) -> None:
        _validate_outcome_code_child(self.outcome_code)
        _validate_payout_child(self.payout)

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (self.outcome_code.logical_values(), self.payout.logical_values())


def _validate_outcome_child(value: EventOutcomeTerms) -> None:
    if type(value) is not EventOutcomeTerms:
        _fail("event-contract outcomes must contain exact EventOutcomeTerms")
    value.__post_init__()


def _outcome_sort_key(value: EventOutcomeTerms) -> tuple[str, str, str]:
    _validate_outcome_child(value)
    return (
        value.outcome_code.value,
        str(value.payout.currency_identity_id.value),
        _canonical_decimal(value.payout.amount),
    )


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
        _validate_authority_child(self.authority_ref)
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
        primary_values = {source.value for source in self.primary_source_codes}
        fallback_values = {source.value for source in self.fallback_source_codes}
        if primary_values.intersection(fallback_values):
            _fail("primary and fallback resolution sources must be disjoint")
        _validate_rule_child(self.resolution_rule_code)
        _validate_correction_child(self.correction_policy_code)
        _validate_conflict_child(self.source_conflict_policy_code)
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
            _fail(f"{field_name} must be exact tuple")
        if not sources and not allow_empty:
            _fail(f"{field_name} must not be empty")
        values: list[str] = []
        for source in sources:
            _validate_source_child(source, field_name=field_name)
            values.append(source.value)
        if len(set(values)) != len(values):
            _fail(f"{field_name} must not contain duplicate sources")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
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


def _validate_resolution_child(value: EventResolutionTerms) -> None:
    if type(value) is not EventResolutionTerms:
        _fail("event-contract resolution_terms must be exact EventResolutionTerms")
    value.__post_init__()


@dataclass(frozen=True, slots=True)
class EventContractTerms:
    """Static event-contract definition with no current/resolved outcome state."""

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
        _validate_terms_id_child(self.terms_id)
        _validate_identity(
            self.instrument_identity_id,
            field_name="event-contract instrument identity",
        )
        _validate_subject_child(self.subject_reference_id)
        _validate_criterion_child(self.criterion_code)
        _validate_structure_child(self.outcome_structure_code)
        if type(self.outcomes) is not tuple or len(self.outcomes) < 2:
            _fail("event-contract outcomes must be an exact tuple with at least two entries")
        for outcome in self.outcomes:
            _validate_outcome_child(outcome)
        outcome_codes = tuple(outcome.outcome_code.value for outcome in self.outcomes)
        if len(set(outcome_codes)) != len(outcome_codes):
            _fail("event-contract outcome codes must be unique")
        canonical_outcomes = tuple(sorted(self.outcomes, key=_outcome_sort_key))
        object.__setattr__(self, "outcomes", canonical_outcomes)
        _validate_resolution_child(self.resolution_terms)
        _validate_evidence_child(self.evidence_ref)
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
            _fail("scheduled resolution date must not precede expiration date")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "event-contract",
            self.terms_id.logical_values(),
            _identity_values(
                self.instrument_identity_id,
                field_name="event-contract instrument identity",
            ),
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
