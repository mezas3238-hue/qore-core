from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.universal_instrument_identity import IdentityFamilyCode
from qore.kernel.errors import InfrastructureError


class InstrumentUniverseRegistryError(InfrastructureError):
    """Base error for the date-qualified D04 instrument-universe registry."""

    __slots__ = ()


class InstrumentUniverseRegistryValidationError(InstrumentUniverseRegistryError):
    """Violation of an instrument-universe registry invariant."""

    __slots__ = ()


_SENSITIVE_TEXT_MARKERS = (
    "authorization:",
    "api-key",
    "api_key",
    "apikey",
    "access-token",
    "access_token",
    "bearer ",
    "client-secret",
    "client_secret",
    "credential=",
    "jwt=",
    "password=",
    "password:",
    "private-key",
    "private_key",
    "secret=",
    "secret:",
    "token=",
    "token:",
)


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        raise InstrumentUniverseRegistryValidationError(
            f"{field_name} must be exact date"
        )


def _validate_positive_int(value: int, *, field_name: str) -> None:
    if type(value) is not int or value <= 0:
        raise InstrumentUniverseRegistryValidationError(
            f"{field_name} must be a positive int"
        )


def _validate_code(value: str, *, field_name: str) -> None:
    if (
        type(value) is not str
        or len(value) > 96
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise InstrumentUniverseRegistryValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _contains_url_userinfo(value: str) -> bool:
    scheme_index = value.find("://")
    if scheme_index < 0:
        return False
    authority = value[scheme_index + 3 :].split("/", 1)[0]
    authority = authority.split("?", 1)[0].split("#", 1)[0]
    return "@" in authority


def _validate_text(
    value: str,
    *,
    field_name: str,
    max_length: int,
) -> None:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > max_length
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise InstrumentUniverseRegistryValidationError(
            f"{field_name} must be non-empty normalized text <= {max_length} chars"
        )
    lowered = value.lower()
    if any(marker in lowered for marker in _SENSITIVE_TEXT_MARKERS) or (
        _contains_url_userinfo(lowered)
    ):
        raise InstrumentUniverseRegistryValidationError(
            f"{field_name} must not contain credential-like material"
        )


@dataclass(frozen=True, slots=True)
class InstrumentUniverseEvidenceRef:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="instrument-universe evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class InstrumentUniverseOwnerRef:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="instrument-universe owner ref")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class InstrumentUniverseSemanticRef:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="instrument-universe semantic ref")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class InstrumentUniverseReason:
    value: str

    def __post_init__(self) -> None:
        _validate_text(
            self.value,
            field_name="instrument-universe reason",
            max_length=512,
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class InstrumentUniverseEvidenceSourceCategory(StrEnum):
    """Origin category only; category never establishes QORE semantic authority."""

    QORE_REPOSITORY = "qore-repository"
    STANDARDS_INDUSTRY_BODY = "standards-industry-body"
    REGULATORY_OFFICIAL = "regulatory-official"
    EXCHANGE_CLEARING_VENUE = "exchange-clearing-venue"
    CENTRAL_BANK_OFFICIAL_REFERENCE = "central-bank-official-reference"
    PROVIDER_PLATFORM_OFFICIAL = "provider-platform-official"


class InstrumentUniverseCoverageStatus(StrEnum):
    """Date-qualified semantic inventory status; never provider/operational support."""

    COVERED = "covered"
    PARTIAL = "partial"
    UNRESOLVED = "unresolved"
    EXCLUDED = "excluded"
    DEFERRED = "deferred"


class InstrumentUniverseOwnerStatus(StrEnum):
    """Retained owner declaration; status alone is never authority proof."""

    CERTIFIED_CONTRACT = "certified-contract"
    PARTIAL_CONTRACT = "partial-contract"
    NO_CERTIFIED_OWNER = "no-certified-owner"
    NOT_APPLICABLE = "not-applicable"


@dataclass(frozen=True, slots=True)
class InstrumentUniverseEvidenceRecord:
    """Reference metadata for retained evidence; never evidence content itself."""

    evidence_ref: InstrumentUniverseEvidenceRef
    source_category: InstrumentUniverseEvidenceSourceCategory
    source_name: str
    locator: str
    verified_on: date

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_ref, InstrumentUniverseEvidenceRef):
            raise InstrumentUniverseRegistryValidationError(
                "evidence record evidence_ref must be InstrumentUniverseEvidenceRef"
            )
        if not isinstance(
            self.source_category,
            InstrumentUniverseEvidenceSourceCategory,
        ):
            raise InstrumentUniverseRegistryValidationError(
                "evidence record source_category must be "
                "InstrumentUniverseEvidenceSourceCategory"
            )
        _validate_text(
            self.source_name,
            field_name="evidence source_name",
            max_length=160,
        )
        _validate_text(
            self.locator,
            field_name="evidence locator",
            max_length=1024,
        )
        _validate_date(self.verified_on, field_name="evidence verified_on")

    def content_logical_values(self) -> tuple[object, ...]:
        return (
            self.source_category.value,
            self.source_name,
            self.locator,
            self.verified_on.isoformat(),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.evidence_ref.logical_values(),
            *self.content_logical_values(),
        )


@dataclass(frozen=True, slots=True)
class InstrumentUniverseEntry:
    """One D04 family declaration; it grants no provider/operational authority."""

    family: IdentityFamilyCode
    coverage_status: InstrumentUniverseCoverageStatus
    owner_status: InstrumentUniverseOwnerStatus
    owner_refs: tuple[InstrumentUniverseOwnerRef, ...]
    unresolved_semantics: tuple[InstrumentUniverseSemanticRef, ...]
    evidence_refs: tuple[InstrumentUniverseEvidenceRef, ...]
    reason: InstrumentUniverseReason

    def __post_init__(self) -> None:
        if not isinstance(self.family, IdentityFamilyCode):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe family must be UMI-02 IdentityFamilyCode"
            )
        if not isinstance(self.coverage_status, InstrumentUniverseCoverageStatus):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe coverage_status must be "
                "InstrumentUniverseCoverageStatus"
            )
        if not isinstance(self.owner_status, InstrumentUniverseOwnerStatus):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe owner_status must be InstrumentUniverseOwnerStatus"
            )
        if type(self.owner_refs) is not tuple or any(
            not isinstance(item, InstrumentUniverseOwnerRef)
            for item in self.owner_refs
        ):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe owner_refs must be an immutable owner-ref tuple"
            )
        if type(self.unresolved_semantics) is not tuple or any(
            not isinstance(item, InstrumentUniverseSemanticRef)
            for item in self.unresolved_semantics
        ):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe unresolved_semantics must be an immutable "
                "semantic-ref tuple"
            )
        if type(self.evidence_refs) is not tuple or not self.evidence_refs or any(
            not isinstance(item, InstrumentUniverseEvidenceRef)
            for item in self.evidence_refs
        ):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe evidence_refs must be a non-empty immutable "
                "evidence-ref tuple"
            )
        if not isinstance(self.reason, InstrumentUniverseReason):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe reason must be InstrumentUniverseReason"
            )

        if len(set(self.owner_refs)) != len(self.owner_refs):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe owner_refs must be unique"
            )
        if len(set(self.unresolved_semantics)) != len(self.unresolved_semantics):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe unresolved_semantics must be unique"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe evidence_refs must be unique"
            )

        if self.owner_status in (
            InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            InstrumentUniverseOwnerStatus.PARTIAL_CONTRACT,
        ):
            if not self.owner_refs:
                raise InstrumentUniverseRegistryValidationError(
                    "certified/partial owner status requires explicit owner_refs"
                )
        elif self.owner_refs:
            raise InstrumentUniverseRegistryValidationError(
                "no-owner/not-applicable owner status must not retain owner_refs"
            )

        if self.coverage_status is InstrumentUniverseCoverageStatus.COVERED:
            if (
                self.owner_status
                is not InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT
            ):
                raise InstrumentUniverseRegistryValidationError(
                    "covered family requires certified-contract owner status"
                )
            if self.unresolved_semantics:
                raise InstrumentUniverseRegistryValidationError(
                    "covered family must not retain unresolved semantics"
                )
        elif self.coverage_status is InstrumentUniverseCoverageStatus.PARTIAL:
            if self.owner_status not in (
                InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
                InstrumentUniverseOwnerStatus.PARTIAL_CONTRACT,
            ):
                raise InstrumentUniverseRegistryValidationError(
                    "partial family requires a retained certified/partial QORE owner"
                )
            if not self.unresolved_semantics:
                raise InstrumentUniverseRegistryValidationError(
                    "partial family must retain unresolved semantics"
                )
        elif self.coverage_status in (
            InstrumentUniverseCoverageStatus.UNRESOLVED,
            InstrumentUniverseCoverageStatus.DEFERRED,
        ):
            if (
                self.owner_status
                is not InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER
            ):
                raise InstrumentUniverseRegistryValidationError(
                    "unresolved/deferred family requires no-certified-owner status"
                )
            if not self.unresolved_semantics:
                raise InstrumentUniverseRegistryValidationError(
                    "unresolved/deferred family must retain unresolved semantics"
                )
        elif self.coverage_status is InstrumentUniverseCoverageStatus.EXCLUDED:
            if self.owner_status is not InstrumentUniverseOwnerStatus.NOT_APPLICABLE:
                raise InstrumentUniverseRegistryValidationError(
                    "excluded family requires not-applicable owner status"
                )
            if self.unresolved_semantics:
                raise InstrumentUniverseRegistryValidationError(
                    "excluded family must not retain unresolved semantics"
                )

        object.__setattr__(
            self,
            "owner_refs",
            tuple(sorted(self.owner_refs, key=lambda item: item.value)),
        )
        object.__setattr__(
            self,
            "unresolved_semantics",
            tuple(sorted(self.unresolved_semantics, key=lambda item: item.value)),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.family.logical_values(),
            self.coverage_status.value,
            self.owner_status.value,
            tuple(item.logical_values() for item in self.owner_refs),
            tuple(item.logical_values() for item in self.unresolved_semantics),
            tuple(item.logical_values() for item in self.evidence_refs),
            self.reason.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class InstrumentUniverseRegistrySnapshot:
    """Immutable date-qualified family inventory; never self-certifying authority."""

    as_of: date
    revision: int
    entries: tuple[InstrumentUniverseEntry, ...]
    evidence: tuple[InstrumentUniverseEvidenceRecord, ...]

    def __post_init__(self) -> None:
        _validate_date(self.as_of, field_name="instrument-universe snapshot as_of")
        _validate_positive_int(
            self.revision,
            field_name="instrument-universe snapshot revision",
        )
        if type(self.entries) is not tuple or not self.entries or any(
            not isinstance(item, InstrumentUniverseEntry) for item in self.entries
        ):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe entries must be a non-empty immutable entry tuple"
            )
        if type(self.evidence) is not tuple or not self.evidence or any(
            not isinstance(item, InstrumentUniverseEvidenceRecord)
            for item in self.evidence
        ):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe evidence must be a non-empty immutable "
                "evidence-record tuple"
            )

        families = tuple(entry.family for entry in self.entries)
        if len(set(families)) != len(families):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe family may appear only once per snapshot"
            )

        evidence_refs = tuple(record.evidence_ref for record in self.evidence)
        if len(set(evidence_refs)) != len(evidence_refs):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe evidence references must be unique"
            )
        evidence_content = tuple(
            record.content_logical_values() for record in self.evidence
        )
        if len(set(evidence_content)) != len(evidence_content):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe duplicate evidence content is not allowed"
            )
        if any(record.verified_on > self.as_of for record in self.evidence):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe evidence cannot be verified after snapshot as_of"
            )

        evidence_by_ref = {record.evidence_ref: record for record in self.evidence}
        retained_refs = frozenset(evidence_by_ref)
        used_refs: set[InstrumentUniverseEvidenceRef] = set()
        for entry in self.entries:
            entry_refs = frozenset(entry.evidence_refs)
            if not entry_refs.issubset(retained_refs):
                raise InstrumentUniverseRegistryValidationError(
                    "instrument-universe entry contains dangling evidence reference"
                )
            used_refs.update(entry_refs)
            if entry.coverage_status in (
                InstrumentUniverseCoverageStatus.COVERED,
                InstrumentUniverseCoverageStatus.PARTIAL,
            ):
                categories = {
                    evidence_by_ref[evidence_ref].source_category
                    for evidence_ref in entry_refs
                }
                if (
                    InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY
                    not in categories
                ):
                    raise InstrumentUniverseRegistryValidationError(
                        "covered/partial family requires retained QORE repository "
                        "evidence"
                    )

        if used_refs != retained_refs:
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe evidence records must all be referenced by "
                "an entry"
            )

        object.__setattr__(
            self,
            "entries",
            tuple(sorted(self.entries, key=lambda item: item.family.value)),
        )
        object.__setattr__(
            self,
            "evidence",
            tuple(sorted(self.evidence, key=lambda item: item.evidence_ref.value)),
        )

    def entry_for_family(
        self,
        family: IdentityFamilyCode,
    ) -> InstrumentUniverseEntry:
        if not isinstance(family, IdentityFamilyCode):
            raise InstrumentUniverseRegistryValidationError(
                "family lookup requires UMI-02 IdentityFamilyCode"
            )
        matches = tuple(entry for entry in self.entries if entry.family == family)
        if len(matches) != 1:
            raise InstrumentUniverseRegistryValidationError(
                "exact instrument-universe family entry not found"
            )
        return matches[0]

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.as_of.isoformat(),
            self.revision,
            tuple(entry.logical_values() for entry in self.entries),
            tuple(record.logical_values() for record in self.evidence),
        )
