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
    ("n", "η"),
    ("o", "о"),
    ("o", "ο"),
    ("p", "р"),
    ("p", "ρ"),
    ("r", "г"),
    ("s", "ѕ"),
    ("s", "σ"),
    ("t", "т"),
    ("t", "τ"),
    ("u", "υ"),
    ("u", "и"),
    ("v", "ν"),
    ("v", "ѵ"),
    ("w", "ω"),
    ("x", "х"),
    ("x", "χ"),
    ("y", "у"),
    ("y", "υ"),
    ("y", "γ"),
    ("z", "з"),
    ("z", "ζ"),
    ("i", "ɪ"),
    ("l", "ɪ"),
    ("k", "ĸ"),
    ("w", "ɯ"),
    ("b", "ь"),
)

_CREDENTIAL_DELIMITER_CONFUSABLES = (
    ("∶", ":"),
    ("꞉", ":"),
    ("ː", ":"),
    ("˸", ":"),
    ("։", ":"),
    ("፡", ":"),
    ("⁝", ":"),
    ("∷", ":"),
    ("׃", ":"),
    ("ˑ", ":"),
    ("꞊", "="),
    ("≡", "="),
    ("≔", "="),
    ("≕", "="),
    ("˭", "="),
    ("∕", "/"),
    ("⁄", "/"),
    ("⫽", "/"),
    ("⧸", "/"),
    ("╱", "/"),
    ("🙼", "/"),
    ("⟋", "/"),
    ("⟍", "/"),
    ("−", "-"),
    ("⁃", "-"),
    ("·", "-"),
)

# Bounded authority-start delimiter class. These are the solidus/slash-family
# characters that remain a slash under NFKC and may open a URL authority start.
# Deliberately excluded:
#   - U+2E17 DOUBLE OBLIQUE HYPHEN: Pd dash, folded to "-" by the root fold and
#     covered by the dash-separator class;
#   - U+2F03 KANGXI RADICAL SLASH: NFKC-folds to U+4E3F (a CJK ideograph, a
#     word character), so it is not a slash after normalization.
# This is not a glyph-shape blanket: only the solidus/diagonal operator family
# that survives NFKC as a slash is admitted.
_URL_AUTHORITY_SLASHES = "/∕⁄⫽⧸╱🙼⟋⟍"

# Bounded composite-label separator class. Includes the ASCII separators and the
# dot/middle-dot family used by `api.key`, `api∙key`, and `api・key`. Slash-like
# separators are intentionally excluded (they are handled by the authority-slash
# class, not the composite-separator class).
_CREDENTIAL_COMPOSITE_SEPARATORS = " _-∙・."

_CREDENTIAL_COMPOSITE_FAMILIES = (
    ("api", "key"),
    ("access", "token"),
    ("client", "secret"),
    ("private", "key"),
)

_CREDENTIAL_BARE_SCHEME_MARKERS = ("bearer ",)

_CREDENTIAL_INVISIBLE_FILLERS = frozenset(("ᅟ", "ᅠ", "⠀"))

# Non-word, non-slash, non-terminator sentinel used to preserve a source token
# boundary (whitespace, marks, fillers, and multi-character expansions) through
# the URL detection skeleton.
_URL_AUTHORITY_BOUNDARY_SENTINEL = "¤"


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
    slashes = _URL_AUTHORITY_SLASHES
    return (
        search(
            rf"(?:[a-z][a-z0-9+.-]*:[{slashes}]{{2}}|"
            rf"(?<![^\W_{slashes}])[{slashes}]{{2}})[^/?#\s]*@",
            value,
        )
        is not None
    )


def _credential_character_matches(character: str, expected_ascii: str) -> bool:
    return (
        character == expected_ascii
        or (expected_ascii, character) in _CREDENTIAL_CONFUSABLE_PAIRS
    )


def _matches_homoglyph_word(
    skeleton: str,
    start: int,
    word: str,
) -> int | None:
    if start + len(word) > len(skeleton):
        return None
    for offset, expected_ascii in enumerate(word):
        if not _credential_character_matches(
            skeleton[start + offset],
            expected_ascii,
        ):
            return None
    return start + len(word)


def _contains_composite_credential_family(skeleton: str) -> bool:
    for first, second in _CREDENTIAL_COMPOSITE_FAMILIES:
        index = 0
        while index <= len(skeleton) - len(first) - len(second):
            after_first = _matches_homoglyph_word(skeleton, index, first)
            if after_first is not None:
                cursor = after_first
                while (
                    cursor < len(skeleton)
                    and skeleton[cursor] in _CREDENTIAL_COMPOSITE_SEPARATORS
                ):
                    cursor += 1
                if _matches_homoglyph_word(skeleton, cursor, second) is not None:
                    return True
            index += 1
    return False


def _contains_bare_scheme_homoglyph(skeleton: str) -> bool:
    for marker in _CREDENTIAL_BARE_SCHEME_MARKERS:
        index = 0
        while index <= len(skeleton) - len(marker):
            if _matches_homoglyph_word(skeleton, index, marker) is not None:
                return True
            index += 1
    return False


def _matches_sensitive_assignment_label(prefix: str, expected_label: str) -> bool:
    index = len(prefix) - 1
    expected_index = len(expected_label) - 1
    while expected_index >= 0:
        while (
            index >= 0 and prefix[index] in _CREDENTIAL_COMPOSITE_SEPARATORS
        ):
            index -= 1
        if index < 0 or not _credential_character_matches(
            prefix[index], expected_label[expected_index]
        ):
            return False
        index -= 1
        expected_index -= 1
    # A complete declared sensitive label was consumed, so detection succeeds
    # regardless of a preceding alphanumeric prefix. The residual left-boundary
    # rejection previously let homoglyph labels with a Unicode/ASCII alphanumeric
    # prefix (e.g. `xtоken=`, `αtоken=`) escape the confusable-assignment path.
    return True


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


_MARK_CATEGORIES = frozenset(("Mn", "Mc", "Me"))


def _fold_credential_detection_root(
    value: str,
    *,
    fold_equals_confusables: bool = False,
) -> str:
    folded: list[str] = []
    for character in value:
        if fold_equals_confusables and character == "\u2e40":
            # U+2E40 DOUBLE HYPHEN doubles as an equals-sign assignment
            # delimiter in the assignment skeleton; in the primary skeleton it
            # remains a Pd dash separator.
            folded.append("=")
        elif category(character) == "Pd":
            folded.append("-")
        elif character in ("\u03f2", "\u03f9"):
            folded.append("c")
        else:
            folded.append(character)
    return "".join(folded)


def _is_spacing_mark_clone(normalized: str) -> bool:
    """True when a NFKC expansion is whitespace plus combining marks only."""
    has_mark = False
    for part in normalized:
        if part.isspace():
            continue
        if category(part) in _MARK_CATEGORIES:
            has_mark = True
            continue
        return False
    return has_mark


def _preserve_nfkc_url_authority_terminators(value: str) -> str:
    protected_parts: list[str] = []
    for character in value:
        normalized_character = normalize("NFKC", character)

        if character in "/?#" or character.isspace():
            # Source authority slash, terminator, or whitespace: keep the
            # canonical form so the source boundary significance is unchanged.
            protected_parts.append(normalized_character)
            continue

        if character.isalnum() and all(
            normalized_part.isalnum() for normalized_part in normalized_character
        ):
            # Source alphanumeric whose NFKC expansion stays alphanumeric.
            protected_parts.append(normalized_character)
            continue

        if len(normalized_character) == 1:
            # A single-character expansion keeps the source's boundary class.
            if normalized_character == "/":
                # A compatibility char folding to an ASCII slash becomes the
                # non-terminator authority-slash sentinel.
                protected_parts.append("∕")
            elif normalized_character == "?":
                protected_parts.append("¿")
            elif normalized_character == "#":
                protected_parts.append("♯")
            elif normalized_character.isspace():
                protected_parts.append(_URL_AUTHORITY_BOUNDARY_SENTINEL)
            else:
                protected_parts.append(normalized_character)
            continue

        if _is_spacing_mark_clone(normalized_character):
            # A spacing clone of a combining mark (e.g. U+00A8 -> space +
            # U+0308) is treated as its mark; the mark filter then removes it in
            # mark-removing skeletons and the boundary skeleton preserves it as
            # a printable boundary.
            protected_parts.append(
                "".join(
                    part for part in normalized_character if not part.isspace()
                )
            )
            continue

        # A multi-character expansion that introduces alphanumerics, slashes,
        # terminators, or whitespace would change the source character's
        # non-alphanumeric/non-slash boundary significance. Collapse it to a
        # single non-alphanumeric boundary sentinel so a scheme-relative "//"
        # authority start stays at its original token boundary.
        protected_parts.append(_URL_AUTHORITY_BOUNDARY_SENTINEL)

    return "".join(protected_parts)


def _casefold_preserving_source_marks(value: str) -> str:
    """casefold non-mark characters while leaving source marks untouched.

    Marks that casefold itself introduces (e.g. U+0130 -> "i" + U+0307) are
    stripped so they do not become spurious lookbehind boundaries; source marks
    are preserved so they keep acting as printable token boundaries.
    """
    return "".join(
        character
        if category(character) in _MARK_CATEGORIES
        else "".join(
            part
            for part in character.casefold()
            if category(part) not in _MARK_CATEGORIES
        )
        for character in value
    )


def _credential_detection_skeleton(
    value: str,
    *,
    fold_url_slash_confusables: bool = True,
    preserve_invisible_fillers: bool = False,
    preserve_marks: bool = False,
    fold_equals_confusables: bool = False,
) -> str:
    root_value = _fold_credential_detection_root(
        value,
        fold_equals_confusables=fold_equals_confusables,
    )
    normalization_source = (
        root_value
        if fold_url_slash_confusables
        else _preserve_nfkc_url_authority_terminators(root_value)
    )
    compatibility = normalize("NFKC", normalization_source)

    if preserve_marks:
        # Boundary-preserving skeleton. Compose first (NFC) so a combining mark
        # that is canonically part of a precomposed letter (e + U+0301 -> é)
        # folds back into the letter instead of becoming a spurious boundary.
        # Protect the remaining standalone marks from casefold (U+0345 would
        # otherwise become Greek iota) so they survive as printable boundaries.
        composed = normalize("NFC", compatibility)
        casefolded = _casefold_preserving_source_marks(composed)
        normalized = normalize("NFC", casefolded)
    else:
        # Mark-removing skeleton. Strip marks before casefold (so U+0345 is
        # removed while still a mark) and again after casefold (so marks
        # introduced by casefold, e.g. U+0130 -> i + U+0307, are removed too).
        decomposed = normalize("NFD", compatibility)
        stripped = "".join(
            character
            for character in decomposed
            if category(character) not in _MARK_CATEGORIES
        )
        normalized = normalize("NFD", stripped.casefold())

    filtered_parts: list[str] = []
    for character in normalized:
        is_mark = category(character) in _MARK_CATEGORIES
        is_filler = character in _CREDENTIAL_INVISIBLE_FILLERS
        if is_mark:
            if preserve_marks:
                # Preserve the printable mark as a non-word boundary sentinel so
                # a scheme-relative "//" authority start stays at its original
                # token boundary instead of concatenating with a preceding word.
                filtered_parts.append(_URL_AUTHORITY_BOUNDARY_SENTINEL)
            continue
        if is_filler:
            if preserve_invisible_fillers:
                filtered_parts.append(_URL_AUTHORITY_BOUNDARY_SENTINEL)
            continue
        filtered_parts.append(character)
    filtered = "".join(filtered_parts)
    for confusable, canonical in _CREDENTIAL_DELIMITER_CONFUSABLES:
        if not fold_url_slash_confusables and canonical == "/":
            continue
        filtered = filtered.replace(confusable, canonical)
    return filtered


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
    # Assignment skeleton additionally folds the bounded equals/colon
    # assignment-delimiter class. U+2E40 DOUBLE HYPHEN is a Pd dash (kept as "-"
    # in the primary skeleton for the composite-separator role) but doubles as
    # an equals sign, so the assignment checks run against a skeleton that folds
    # it to "=".
    assignment_detection_value = _credential_detection_skeleton(
        value,
        fold_equals_confusables=True,
    )
    url_detection_value = _credential_detection_skeleton(
        value,
        fold_url_slash_confusables=False,
    )
    # A boundary-preserving URL skeleton keeps invisible printable fillers and
    # printable Mn/Mc/Me marks in place so a scheme-relative "//" authority
    # start remains at its original token boundary. Deleting such a printable
    # non-alphanumeric/non-slash source character would concatenate an
    # alphanumeric prefix with the "//" and defeat the negative-lookbehind
    # boundary guard. The mark/filler-removing skeleton above still catches a
    # mark or filler placed between the two authority slashes, inside userinfo,
    # inside the scheme, or inside a sensitive credential label. All skeletons
    # are detection-only; retained/projected source text is never rewritten.
    url_boundary_detection_value = _credential_detection_skeleton(
        value,
        fold_url_slash_confusables=False,
        preserve_invisible_fillers=True,
        preserve_marks=True,
    )
    if (
        any(marker in detection_value for marker in _SENSITIVE_TEXT_MARKERS)
        or _contains_composite_credential_family(detection_value)
        or _contains_bare_scheme_homoglyph(detection_value)
        or search(_SENSITIVE_ASSIGNMENT_PATTERN, assignment_detection_value)
        is not None
        or _contains_confusable_sensitive_assignment(assignment_detection_value)
        or _contains_url_userinfo(url_detection_value)
        or _contains_url_userinfo(url_boundary_detection_value)
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
    state_error = (
        "family lookup requires canonical UMI-02 IdentityFamilyCode state"
        if lookup
        else (
            "instrument-universe family must retain canonical UMI-02 "
            "IdentityFamilyCode state"
        )
    )
    if type(value) is not IdentityFamilyCode:
        raise InstrumentUniverseRegistryValidationError(type_error)
    try:
        exact_value_type = type(value.value) is str
    except AttributeError:
        raise InstrumentUniverseRegistryValidationError(type_error) from None
    if not exact_value_type:
        raise InstrumentUniverseRegistryValidationError(type_error)
    try:
        value.__post_init__()
    except UniversalInstrumentIdentityValidationError:
        raise InstrumentUniverseRegistryValidationError(state_error) from None
    except (AttributeError, TypeError):
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
        try:
            member_name = member.name
            member_value = member.value
        except (AttributeError, TypeError):
            raise InstrumentUniverseRegistryValidationError(
                f"{field_name} enum must retain canonical member state"
            ) from None
        if (
            type(member_name) is not str
            or member_name != expected_name
            or type(member_value) is not str
            or member_value != expected_value
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
