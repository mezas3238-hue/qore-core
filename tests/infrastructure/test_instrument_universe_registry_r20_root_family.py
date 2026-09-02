from __future__ import annotations

from collections.abc import Callable
from unicodedata import category, normalize

import pytest

import qore.infrastructure.instrument_universe_registry as registry
from qore.infrastructure.universal_instrument_identity import IdentityFamilyCode

# --------------------------------------------------------------------------- #
# F-R21: printable mark -> letter casefold escape (U+0345 is the unique witness)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "value",
    [
        "tok\u0345en=PLAINTEXT-SECRET",
        "api\u0345key=PLAINTEXT-SECRET",
        "https:/\u0345/user@host",
        "tok\u0345en:PLAINTEXT-SECRET",
        "https:/\u0345/alice:password@host",
    ],
)
def test_reason_rejects_ypogegrammeni_casefold_escape(value: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


def test_only_mark_whose_casefold_leaves_the_mark_category_is_u0345() -> None:
    """Exhaustive invariant: U+0345 is the unique Mn/Mc/Me mark whose casefold
    changes it out of the mark category (into Greek iota). Filtering marks
    before casefold therefore closes the whole printable-mark escape family."""
    escaping: list[str] = []
    for codepoint in range(0x110000):
        character = chr(codepoint)
        if category(character) not in {"Mn", "Mc", "Me"}:
            continue
        folded = character.casefold()
        if any(category(part) not in {"Mn", "Mc", "Me"} for part in folded):
            escaping.append(character)
    assert escaping == ["\u0345"]


# --------------------------------------------------------------------------- #
# F-NORM-BOUNDARY: non-alnum source chars expanding to alnum/slash
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "obfuscated",
    [
        "\u2122",  # TRADE MARK SIGN -> TM
        "\u2116",  # NUMERO SIGN -> No
        "\u2121",  # TELEPHONE SIGN -> TEL
        "\u2105",  # CARE OF -> c/o
        "\u215f",  # FRACTION NUMERATOR ONE -> 1/
        "\u339d",  # SQUARE CM -> cm
        "\u00bc",  # VULGAR FRACTION ONE QUARTER -> 1/4
    ],
)
@pytest.mark.parametrize(
    "template",
    [
        "Evidence{}//alice:password@example.invalid/evidence",
        "abc{}//user@host",
    ],
)
def test_reason_rejects_nfkc_boundary_expansion_before_authority(
    obfuscated: str,
    template: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(template.format(obfuscated))


@pytest.mark.parametrize(
    "benign",
    [
        "Evidence\u2122 reference",
        "Market \u2116 5 evidence",
        "Caf\u00e9 market evidence",
    ],
)
def test_benign_nfkc_expansion_outside_authority_is_retained(benign: str) -> None:
    reason = registry.InstrumentUniverseReason(benign)

    assert reason.logical_values() == (benign,)


# --------------------------------------------------------------------------- #
# F-SLASH: bounded authority-start delimiter class
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "slash",
    [
        "\u2afd",  # DOUBLE SOLIDUS OPERATOR
        "\u29f8",  # BIG SOLIDUS
        "\u2571",  # BOX DRAWINGS LIGHT DIAGONAL
        "\U0001f67c",  # VERY HEAVY SOLIDUS
        "\u27cb",  # MATHEMATICAL RISING DIAGONAL
        "\u27cd",  # MATHEMATICAL FALLING DIAGONAL
    ],
)
def test_reason_rejects_solidus_family_authority_start(slash: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(f"https:{slash}{slash}user@host")


def test_slash_class_remains_stable_under_nfkc() -> None:
    """Every admitted authority slash must survive NFKC as itself (still a
    solidus), which is the bounded admission policy."""
    for slash in registry._URL_AUTHORITY_SLASHES:
        assert normalize("NFKC", slash) == slash, hex(ord(slash))


def test_kangxi_radical_slash_is_excluded_as_cjk_word_character() -> None:
    # U+2F03 KANGXI RADICAL SLASH NFKC-folds to U+4E3F (a CJK ideograph), so it
    # is a word character, not a slash, and must not be flagged as an authority.
    reason = registry.InstrumentUniverseReason("\u4e3f//user@host")

    assert reason.logical_values() == ("\u4e3f//user@host",)


# --------------------------------------------------------------------------- #
# F-SPACING: spacing clones of combining marks between authority slashes
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "spacing_mark",
    [
        "\u00a8",  # DIAERESIS -> space + U+0308
        "\u00b4",  # ACUTE ACCENT -> space + U+0301
        "\u02dc",  # SMALL TILDE -> space + U+0303
        "\u00af",  # MACRON -> space + U+0304
        "\u00b8",  # CEDILLA -> space + U+0327
        "\u02dd",  # DOUBLE ACUTE ACCENT -> space + U+030B
    ],
)
def test_reason_rejects_spacing_mark_clone_between_slashes(spacing_mark: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(f"https:/{spacing_mark}/user@host")


# --------------------------------------------------------------------------- #
# F-EQUALS-COLON: bounded assignment delimiter class
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "delimiter",
    [
        "\ua78a",  # MODIFIER LETTER SHORT EQUALS SIGN
        "\u2e40",  # DOUBLE HYPHEN (also a Pd dash separator)
        "\u2261",  # IDENTICAL TO
        "\u2254",  # COLON EQUALS
        "\u2255",  # EQUALS COLON
        "\u02ed",  # MODIFIER LETTER UNASPIRATED
    ],
)
def test_reason_rejects_equals_like_assignment_delimiter(delimiter: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(f"token{delimiter}PLAINTEXT-SECRET")


@pytest.mark.parametrize(
    "delimiter",
    [
        "\u0589",  # ARMENIAN FULL STOP
        "\u1361",  # ETHIOPIC WORDSPACE
        "\u205d",  # TRICOLON
        "\u2237",  # PROPORTION
        "\u05c3",  # HEBREW PUNCTUATION SOF PASUQ
        "\u02d1",  # MODIFIER LETTER HALF TRIANGULAR COLON
    ],
)
def test_reason_rejects_colon_like_assignment_delimiter(delimiter: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(f"token{delimiter}PLAINTEXT-SECRET")


def test_double_hyphen_keeps_both_dash_and_equals_roles() -> None:
    # U+2E40 is a Pd dash separator AND an equals-like assignment delimiter.
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason("api\u2e40key=PLAINTEXT-SECRET")
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason("token\u2e40PLAINTEXT-SECRET")


# --------------------------------------------------------------------------- #
# F-LABEL-GAPS: bounded homoglyph pair and composite separator tables
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "obfuscated",
    [
        "apike\u03b3=PLAINTEXT-SECRET",  # Greek gamma for y
        "ap\u026akey=PLAINTEXT-SECRET",  # small capital I for i
        "api\u0138ey=PLAINTEXT-SECRET",  # kra for k
        "pass\u026ford=PLAINTEXT-SECRET",  # turned m for w
        "\u044cearer=PLAINTEXT-SECRET",  # Cyrillic soft sign for b
        "c\u026aientsecret=PLAINTEXT-SECRET",  # small capital I for l
    ],
)
def test_reason_rejects_declared_homoglyph_labels(obfuscated: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(obfuscated)


@pytest.mark.parametrize(
    "label",
    [
        "api.key=PLAINTEXT-SECRET",
        "api\u2219key=PLAINTEXT-SECRET",  # BULLET OPERATOR
        "api\u30fbkey=PLAINTEXT-SECRET",  # KATAKANA MIDDLE DOT
        "private.key=PLAINTEXT-SECRET",
        "client\u30fbsecret=PLAINTEXT-SECRET",
        "access\u2219token=PLAINTEXT-SECRET",
    ],
)
def test_reason_rejects_declared_composite_separators(label: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(label)


# --------------------------------------------------------------------------- #
# F-FALSEPOS: NFC/NFD and casefold equivalence around authority boundaries
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "benign",
    [
        "e//user@host",
        "\u00e9//user@host",  # precomposed é
        "e\u0301//user@host",  # decomposed é
        "\u00c9//user@host",  # capital É
        "\u0130//user@host",  # capital I with dot above (casefold -> i + mark)
        "\u03b3//user@host",  # Greek gamma (a letter, not a boundary)
        "\u044c//user@host",  # Cyrillic soft sign (a letter)
    ],
)
def test_reason_accepts_letter_before_authority_without_boundary(benign: str) -> None:
    reason = registry.InstrumentUniverseReason(benign)

    assert reason.logical_values() == (benign,)


@pytest.mark.parametrize("mark", ("\u0301", "\u0327"))
def test_precomposed_and_decomposed_letters_are_equivalent(mark: str) -> None:
    precomposed = "\u00e9" if mark == "\u0301" else "\u0229"
    assert registry._credential_detection_skeleton(
        precomposed + "//user@host",
        fold_url_slash_confusables=False,
        preserve_marks=True,
    ) == registry._credential_detection_skeleton(
        "e" + mark + "//user@host",
        fold_url_slash_confusables=False,
        preserve_marks=True,
    )


# --------------------------------------------------------------------------- #
# F-ERRCONTRACT: forged/deleted retained state raises registry errors only
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: object.__delattr__(value, "value"),
        lambda value: object.__setattr__(value, "value", []),
        lambda value: object.__setattr__(value, "value", 3),
    ],
)
def test_identity_family_forged_or_deleted_state_raises_registry_error(
    mutate: Callable[[IdentityFamilyCode], None],
) -> None:
    family = IdentityFamilyCode("futures")
    mutate(family)

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="IdentityFamilyCode",
    ):
        registry._revalidate_identity_family(family)


def test_entry_with_deleted_family_value_raises_registry_error() -> None:
    family = IdentityFamilyCode("futures")
    object.__delattr__(family, "value")

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="IdentityFamilyCode",
    ):
        registry.InstrumentUniverseEntry(
            family=family,
            coverage_status=registry.InstrumentUniverseCoverageStatus.PARTIAL,
            owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(registry.InstrumentUniverseOwnerRef("umi-05.derivatives"),),
            unresolved_semantics=(
                registry.InstrumentUniverseSemanticRef("deliverable-basket"),
            ),
            evidence_refs=(registry.InstrumentUniverseEvidenceRef("qore-umi05"),),
            reason=registry.InstrumentUniverseReason("Bounded futures semantics."),
        )


@pytest.mark.parametrize("attribute", ("_name_", "_value_"))
def test_enum_deleted_state_raises_registry_error(attribute: str) -> None:
    # Corrupt a fresh module in an isolated process so the enum mutation does
    # not leak into the shared interpreter's enum singletons.
    import subprocess
    import sys

    script = f'''\
import qore.infrastructure.instrument_universe_registry as registry
member = registry.InstrumentUniverseCoverageStatus.PARTIAL
object.__delattr__(member, {attribute!r})
try:
    registry._revalidate_coverage_status(member)
except registry.InstrumentUniverseRegistryValidationError:
    print("REGISTRY_ERROR")
else:
    print("ACCEPTED")
'''
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "REGISTRY_ERROR\n"


def test_enum_wrong_runtime_value_type_raises_registry_error() -> None:
    import subprocess
    import sys

    script = '''\
import qore.infrastructure.instrument_universe_registry as registry
member = registry.InstrumentUniverseCoverageStatus.PARTIAL
object.__setattr__(member, "_value_", 12345)
try:
    registry._revalidate_coverage_status(member)
except registry.InstrumentUniverseRegistryValidationError:
    print("REGISTRY_ERROR")
else:
    print("ACCEPTED")
'''
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "REGISTRY_ERROR\n"


# --------------------------------------------------------------------------- #
# Property/metamorphic: detection is deterministic and idempotent
# --------------------------------------------------------------------------- #


def test_detection_skeleton_is_deterministic_and_idempotent() -> None:
    value = "Evidence\uFE0F//alice:password@example.invalid/evidence"

    first = registry._credential_detection_skeleton(
        value,
        fold_url_slash_confusables=False,
        preserve_marks=True,
        preserve_invisible_fillers=True,
    )
    second = registry._credential_detection_skeleton(
        value,
        fold_url_slash_confusables=False,
        preserve_marks=True,
        preserve_invisible_fillers=True,
    )
    assert first == second


def test_benign_retained_text_is_byte_identical() -> None:
    values = (
        "Cafe\u0301 market evidence",
        "Evidence\uFE0F reference",
        "Caf\u00e9 market evidence",
        "Greek \u03c3 sigma and \u03c2 final sigma evidence",
    )
    for value in values:
        reason = registry.InstrumentUniverseReason(value)
        assert reason.logical_values() == (value,)
