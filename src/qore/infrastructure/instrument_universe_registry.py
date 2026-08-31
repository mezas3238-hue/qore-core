from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from re import fullmatch, search
from unicodedata import category, normalize

from qore.infrastructure.universal_instrument_identity import (
    IdentityFamilyCode,
    UniversalInstrumentIdentityValidationError,
)
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

_SENSITIVE_ASSIGNMENT_PATTERN = (
    r"(?<![a-z0-9])(?:authorization|bearer|credential|jwt|password|secret|token|"
    r"api(?:[ _-]*key)|access(?:[ _-]*token)|client(?:[ _-]*secret)|"
    r"private(?:[ _-]*key))\s*[=:]"
)

_SENSITIVE_ASSIGNMENT_LABELS = (
    "authorization",
    "bearer",
    "credential",
    "jwt",
    "password",
    "secret",
    "token",
    "apikey",
    "accesstoken",
    "clientsecret",
    "privatekey",
)

_CREDENTIAL_CONFUSABLE_PAIRS = (
    ("a", "а"),
    ("a", "α"),
    ("a", "ɑ"),
    ("b", "в"),
    ("b", "β"),
    ("c", "с"),
    ("c", "ϲ"),
    ("d", "ԁ"),
    ("d", "δ"),
    ("e", "е"),
    ("e", "ε"),
    ("e", "ɛ"),
    ("h", "һ"),
    ("h", "н"),
    ("i", "і"),
    ("i", "ι"),
    ("i", "ı"),
    ("j", "ј"),
    ("j", "ϳ"),
    ("k", "к"),
    ("k", "κ"),
    ("l", "ӏ"),
    ("l", "ι"),
    ("m", "м"),
    ("m", "μ"),
    ("n", "п"),
    ("n", "ν"),
    ("o", "о"),
    ("o", "ο"),
    ("p", "р"),
    ("p", "ρ"),
    ("s", "ѕ"),
    ("s", "σ"),
    ("t", "т"),
    ("t", "τ"),
    ("u", "υ"),
    ("v", "ν"),
    ("v", "ѵ"),
    ("w", "ω"),
    ("x", "х"),
    ("x", "χ"),
    ("y", "у"),
    ("y", "υ"),
    ("z", "з"),
    ("z", "ζ"),
)

_CREDENTIAL_DELIMITER_CONFUSABLES = (
    ("∶", ":"),
    ("꞉", ":"),
    ("∕", "/"),
    ("⁄", "/"),
    ("‐", "-"),
    ("‑", "-"),
    ("‒", "-"),
    ("–", "-"),
    ("—", "-"),
    ("−", "-"),
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
    if value.startswith("//"):
        authority_start = 2
    else:
        scheme_index = value.find("://")
        if scheme_index < 0:
            return False
        authority_start = scheme_index + 3
    authority = value[authority_start:].split("/", 1)[0]
    authority = authority.split("?", 1)[0].split("#", 1)[0]
    return "@" in authority


def _credential_character_matches(character: str, expected_ascii: str) -> bool:
    return (
        character == expected_ascii
        or (expected_ascii, character) in _CREDENTIAL_CONFUSABLE_PAIRS
    )


def _matches_sensitive_assignment_label(prefix: str, expected_label: str) -> bool:
    index = len(prefix) - 1
    expected_index = len(expected_label) - 1
    while expected_index >= 0:
        while index >= 0 and prefix[index] in " _-":
            index -= 1
        if index < 0 or not _credential_character_matches(
            prefix[index], expected_label[expected_index]
        ):
            return False
        index -= 1
        expected_index -= 1
    return index < 0 or not prefix[index].isalnum()


def _contains_confusable_sensitive_assignment(value: str) -> bool:
    for index, character in enumerate(value):
        if character not in "=:":
            continue
        prefix = value[:index].rstrip()
        if any(
            _matches_sensitive_assignment_label(prefix, expected_label)
            for expected_label in _SENSITIVE_ASSIGNMENT_LABELS
        ):
            return True
    return False


def _credential_detection_skeleton(value: str) -> str:
    normalized = normalize("NFKC", value).casefold()
    without_marks = "".join(
        character
        for character in normalized
        if category(character) not in {"Mn", "Mc", "Me"}
    )
    for confusable, canonical in _CREDENTIAL_DELIMITER_CONFUSABLES:
        without_marks = without_marks.replace(confusable, canonical)
    return without_marks


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
        or any(not character.isprintable() for character in value)
    ):
        raise InstrumentUniverseRegistryValidationError(
            f"{field_name} must be non-empty normalized text <= {max_length} chars"
        )
    detection_value = _credential_detection_skeleton(value)
    if (
        any(marker in detection_value for marker in _SENSITIVE_TEXT_MARKERS)
        or search(_SENSITIVE_ASSIGNMENT_PATTERN, detection_value) is not None
        or _contains_confusable_sensitive_assignment(detection_value)
        or _contains_url_userinfo(detection_value)
    ):
        raise InstrumentUniverseRegistryValidationError(
            f"{field_name} must not contain credential-like material"
        )


def _revalidate_identity_family(
    value: object,
    *,
    lookup: bool = False,
) -> None:
    type_error = (
        "family lookup requires UMI-02 IdentityFamilyCode with exact str value"
        if lookup
        else (
            "instrument-universe family must be UMI-02 IdentityFamilyCode "
            "with exact str value"
        )
    )
    if type(value) is not IdentityFamilyCode or type(value.value) is not str:
        raise InstrumentUniverseRegistryValidationError(type_error)
    try:
        value.__post_init__()
    except UniversalInstrumentIdentityValidationError:
        state_error = (
            "family lookup requires canonical UMI-02 IdentityFamilyCode state"
            if lookup
            else (
                "instrument-universe family must retain canonical UMI-02 "
                "IdentityFamilyCode state"
            )
        )
        raise InstrumentUniverseRegistryValidationError(state_error) from None


@dataclass(frozen=True, slots=True)
class InstrumentUniverseEvidenceRef:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="instrument-universe evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class InstrumentUniverseOwnerRef:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="instrument-universe owner ref")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class InstrumentUniverseSemanticRef:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="instrument-universe semantic ref")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
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
        self.__post_init__()
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


_CanonicalStrEnumMembers = tuple[tuple[StrEnum, str, str], ...]

_EVIDENCE_SOURCE_CATEGORY_MEMBERS: _CanonicalStrEnumMembers = (
    (
        InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        "QORE_REPOSITORY",
        "qore-repository",
    ),
    (
        InstrumentUniverseEvidenceSourceCategory.STANDARDS_INDUSTRY_BODY,
        "STANDARDS_INDUSTRY_BODY",
        "standards-industry-body",
    ),
    (
        InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL,
        "REGULATORY_OFFICIAL",
        "regulatory-official",
    ),
    (
        InstrumentUniverseEvidenceSourceCategory.EXCHANGE_CLEARING_VENUE,
        "EXCHANGE_CLEARING_VENUE",
        "exchange-clearing-venue",
    ),
    (
        InstrumentUniverseEvidenceSourceCategory.CENTRAL_BANK_OFFICIAL_REFERENCE,
        "CENTRAL_BANK_OFFICIAL_REFERENCE",
        "central-bank-official-reference",
    ),
    (
        InstrumentUniverseEvidenceSourceCategory.PROVIDER_PLATFORM_OFFICIAL,
        "PROVIDER_PLATFORM_OFFICIAL",
        "provider-platform-official",
    ),
)

_COVERAGE_STATUS_MEMBERS: _CanonicalStrEnumMembers = (
    (InstrumentUniverseCoverageStatus.COVERED, "COVERED", "covered"),
    (InstrumentUniverseCoverageStatus.PARTIAL, "PARTIAL", "partial"),
    (InstrumentUniverseCoverageStatus.UNRESOLVED, "UNRESOLVED", "unresolved"),
    (InstrumentUniverseCoverageStatus.EXCLUDED, "EXCLUDED", "excluded"),
    (InstrumentUniverseCoverageStatus.DEFERRED, "DEFERRED", "deferred"),
)

_OWNER_STATUS_MEMBERS: _CanonicalStrEnumMembers = (
    (
        InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
        "CERTIFIED_CONTRACT",
        "certified-contract",
    ),
    (
        InstrumentUniverseOwnerStatus.PARTIAL_CONTRACT,
        "PARTIAL_CONTRACT",
        "partial-contract",
    ),
    (
        InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER,
        "NO_CERTIFIED_OWNER",
        "no-certified-owner",
    ),
    (
        InstrumentUniverseOwnerStatus.NOT_APPLICABLE,
        "NOT_APPLICABLE",
        "not-applicable",
    ),
)


def _revalidate_str_enum_member(
    value: object,
    *,
    enum_type: type[StrEnum],
    canonical_members: _CanonicalStrEnumMembers,
    field_name: str,
) -> str:
    if type(value) is not enum_type:
        raise InstrumentUniverseRegistryValidationError(
            f"{field_name} must be {enum_type.__name__}"
        )

    canonical_value: str | None = None
    for member, expected_name, expected_value in canonical_members:
        if (
            type(member.name) is not str
            or member.name != expected_name
            or type(member.value) is not str
            or member.value != expected_value
        ):
            raise InstrumentUniverseRegistryValidationError(
                f"{field_name} enum must retain canonical member state"
            )
        if value is member:
            canonical_value = expected_value

    if canonical_value is None:
        raise InstrumentUniverseRegistryValidationError(
            f"{field_name} must retain a canonical enum member identity"
        )
    return canonical_value


def _revalidate_evidence_source_category(value: object) -> str:
    return _revalidate_str_enum_member(
        value,
        enum_type=InstrumentUniverseEvidenceSourceCategory,
        canonical_members=_EVIDENCE_SOURCE_CATEGORY_MEMBERS,
        field_name="evidence record source_category",
    )


def _revalidate_coverage_status(value: object) -> str:
    return _revalidate_str_enum_member(
        value,
        enum_type=InstrumentUniverseCoverageStatus,
        canonical_members=_COVERAGE_STATUS_MEMBERS,
        field_name="instrument-universe coverage_status",
    )


def _revalidate_owner_status(value: object) -> str:
    return _revalidate_str_enum_member(
        value,
        enum_type=InstrumentUniverseOwnerStatus,
        canonical_members=_OWNER_STATUS_MEMBERS,
        field_name="instrument-universe owner_status",
    )


@dataclass(frozen=True, slots=True)
class InstrumentUniverseEvidenceRecord:
    """Reference metadata for retained evidence; never evidence content itself."""

    evidence_ref: InstrumentUniverseEvidenceRef
    source_category: InstrumentUniverseEvidenceSourceCategory
    source_name: str
    locator: str
    verified_on: date

    def __post_init__(self) -> None:
        if type(self.evidence_ref) is not InstrumentUniverseEvidenceRef:
            raise InstrumentUniverseRegistryValidationError(
                "evidence record evidence_ref must be InstrumentUniverseEvidenceRef"
            )
        self.evidence_ref.__post_init__()
        _revalidate_evidence_source_category(self.source_category)
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
        self.__post_init__()
        return (
            _revalidate_evidence_source_category(self.source_category),
            self.source_name,
            self.locator,
            self.verified_on.isoformat(),
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.evidence_ref.logical_values(),
            _revalidate_evidence_source_category(self.source_category),
            self.source_name,
            self.locator,
            self.verified_on.isoformat(),
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
        _revalidate_identity_family(self.family)
        coverage_status = _revalidate_coverage_status(self.coverage_status)
        owner_status = _revalidate_owner_status(self.owner_status)
        if type(self.owner_refs) is not tuple or any(
            type(item) is not InstrumentUniverseOwnerRef for item in self.owner_refs
        ):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe owner_refs must be an immutable owner-ref tuple"
            )
        if type(self.unresolved_semantics) is not tuple or any(
            type(item) is not InstrumentUniverseSemanticRef
            for item in self.unresolved_semantics
        ):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe unresolved_semantics must be an immutable "
                "semantic-ref tuple"
            )
        if type(self.evidence_refs) is not tuple or not self.evidence_refs or any(
            type(item) is not InstrumentUniverseEvidenceRef for item in self.evidence_refs
        ):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe evidence_refs must be a non-empty immutable "
                "evidence-ref tuple"
            )
        if type(self.reason) is not InstrumentUniverseReason:
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe reason must be InstrumentUniverseReason"
            )

        for owner_ref in self.owner_refs:
            owner_ref.__post_init__()
        for semantic_ref in self.unresolved_semantics:
            semantic_ref.__post_init__()
        for evidence_ref in self.evidence_refs:
            evidence_ref.__post_init__()
        self.reason.__post_init__()

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

        if owner_status in ("certified-contract", "partial-contract"):
            if not self.owner_refs:
                raise InstrumentUniverseRegistryValidationError(
                    "certified/partial owner status requires explicit owner_refs"
                )
        elif self.owner_refs:
            raise InstrumentUniverseRegistryValidationError(
                "no-owner/not-applicable owner status must not retain owner_refs"
            )

        if coverage_status == "covered":
            if owner_status != "certified-contract":
                raise InstrumentUniverseRegistryValidationError(
                    "covered family requires certified-contract owner status"
                )
            if self.unresolved_semantics:
                raise InstrumentUniverseRegistryValidationError(
                    "covered family must not retain unresolved semantics"
                )
        elif coverage_status == "partial":
            if owner_status not in ("certified-contract", "partial-contract"):
                raise InstrumentUniverseRegistryValidationError(
                    "partial family requires a retained certified/partial QORE owner"
                )
            if not self.unresolved_semantics:
                raise InstrumentUniverseRegistryValidationError(
                    "partial family must retain unresolved semantics"
                )
        elif coverage_status in ("unresolved", "deferred"):
            if owner_status != "no-certified-owner":
                raise InstrumentUniverseRegistryValidationError(
                    "unresolved/deferred family requires no-certified-owner status"
                )
            if not self.unresolved_semantics:
                raise InstrumentUniverseRegistryValidationError(
                    "unresolved/deferred family must retain unresolved semantics"
                )
        elif coverage_status == "excluded":
            if owner_status != "not-applicable":
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
        self.__post_init__()
        return (
            self.family.logical_values(),
            _revalidate_coverage_status(self.coverage_status),
            _revalidate_owner_status(self.owner_status),
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
            type(item) is not InstrumentUniverseEntry for item in self.entries
        ):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe entries must be a non-empty immutable entry tuple"
            )
        if type(self.evidence) is not tuple or not self.evidence or any(
            type(item) is not InstrumentUniverseEvidenceRecord for item in self.evidence
        ):
            raise InstrumentUniverseRegistryValidationError(
                "instrument-universe evidence must be a non-empty immutable "
                "evidence-record tuple"
            )

        for entry in self.entries:
            entry.__post_init__()
        for record in self.evidence:
            record.__post_init__()

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
            if _revalidate_coverage_status(entry.coverage_status) in (
                "covered",
                "partial",
            ):
                categories = {
                    _revalidate_evidence_source_category(
                        evidence_by_ref[evidence_ref].source_category
                    )
                    for evidence_ref in entry_refs
                }
                if "qore-repository" not in categories:
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
        self.__post_init__()
        _revalidate_identity_family(family, lookup=True)
        matches = tuple(entry for entry in self.entries if entry.family == family)
        if len(matches) != 1:
            raise InstrumentUniverseRegistryValidationError(
                "exact instrument-universe family entry not found"
            )
        return matches[0]

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.as_of.isoformat(),
            self.revision,
            tuple(entry.logical_values() for entry in self.entries),
            tuple(record.logical_values() for record in self.evidence),
        )
