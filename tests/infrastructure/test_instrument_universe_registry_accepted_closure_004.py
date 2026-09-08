from __future__ import annotations

from datetime import date

import pytest

import qore.infrastructure.instrument_universe_registry as registry

_PD_SEPARATORS = (
    "\u058a",  # ARMENIAN HYPHEN
    "\u05be",  # HEBREW PUNCTUATION MAQAF
    "\u1400",  # CANADIAN SYLLABICS HYPHEN
    "\u1806",  # MONGOLIAN TODO SOFT HYPHEN
    "\u2010",  # HYPHEN
    "\u2011",  # NON-BREAKING HYPHEN
    "\u2012",  # FIGURE DASH
    "\u2013",  # EN DASH
    "\u2014",  # EM DASH
    "\u2015",  # HORIZONTAL BAR
    "\u2e17",  # DOUBLE OBLIQUE HYPHEN
    "\u2e1a",  # HYPHEN WITH DIAERESIS
    "\u2e3a",  # TWO-EM DASH
    "\u2e3b",  # THREE-EM DASH
    "\u2e40",  # DOUBLE HYPHEN
    "\u2e5d",  # OBLIQUE HYPHEN
    "\u301c",  # WAVE DASH
    "\u3030",  # WAVY DASH
    "\u30a0",  # KATAKANA-HIRAGANA DOUBLE HYPHEN
    "\ufe31",  # PRESENTATION FORM FOR VERTICAL EM DASH
    "\ufe32",  # PRESENTATION FORM FOR VERTICAL EN DASH
    "\ufe58",  # SMALL EM DASH
    "\ufe63",  # SMALL HYPHEN-MINUS
    "\uff0d",  # FULLWIDTH HYPHEN-MINUS
    "\U00010ead",  # YEZIDI HYPHENATION MARK
)


def _reason_rejects(value: str) -> bool:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)
    return True


def _reason_retained(value: str) -> bool:
    reason = registry.InstrumentUniverseReason(value)
    assert reason.logical_values() == (value,)
    return True


def _revalidation_rejects(value: str) -> None:
    reason = registry.InstrumentUniverseReason("Safe retained reason")
    object.__setattr__(reason, "value", value)

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        reason.__post_init__()
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        reason.logical_values()


# --- F1: bare composite families in bare/space/hyphen/underscore forms ---


@pytest.mark.parametrize("family", ("apikey", "accesstoken", "clientsecret", "privatekey"))
@pytest.mark.parametrize(
    "separator",
    ("", " ", "-", "_", "  ", "--", "__", "-_-"),
)
def test_bare_composite_family_rejects_across_separator_forms(
    family: str,
    separator: str,
) -> None:
    first, second = {
        "apikey": ("api", "key"),
        "accesstoken": ("access", "token"),
        "clientsecret": ("client", "secret"),
        "privatekey": ("private", "key"),
    }[family]
    assert _reason_rejects(f"{first}{separator}{second}")


# --- F1: historical substring semantics for embedded occurrences ---


@pytest.mark.parametrize(
    "embedded",
    [
        "prefixclientsecretpostfix",
        "prefixapi-keypostfix",
        "prefixaccesstokenpostfix",
        "prefixprivate_keypostfix",
        "xxclient-secretyy",
        "1access_token2",
        "before api key after",
    ],
)
def test_embedded_composite_family_occurrences_reject(embedded: str) -> None:
    assert _reason_rejects(embedded)


def test_composite_family_is_not_narrowed_by_token_boundaries() -> None:
    # A supported family is sensitive wherever the complete family occurs.
    assert _reason_rejects("xapikey=PLAINTEXT-SECRET")
    assert _reason_rejects("zzclientsecret=PLAINTEXT-SECRET")


# --- F3: categorical Pd -> '-' ---


@pytest.mark.parametrize("separator", _PD_SEPARATORS)
@pytest.mark.parametrize("label", ("api", "private"))
def test_categorical_pd_separator_rejects_sensitive_assignment(
    separator: str,
    label: str,
) -> None:
    assert _reason_rejects(f"{label}{separator}key=PLAINTEXT-SECRET")


@pytest.mark.parametrize("separator", _PD_SEPARATORS)
def test_categorical_pd_separator_rejects_bare_composite(separator: str) -> None:
    assert _reason_rejects(f"client{separator}secret")


# --- F3: exact residual non-Pd lookalikes U+2043 / U+00B7 / U+02F8 ---


@pytest.mark.parametrize(
    "obfuscated",
    [
        "api\u2043key=PLAINTEXT-SECRET",  # U+2043 HYPHEN BULLET
        "api\u00b7key=PLAINTEXT-SECRET",  # U+00B7 MIDDLE DOT
        "private\u2043key:PLAINTEXT-SECRET",
        "token\u02f8PLAINTEXT-SECRET",  # U+02F8 MODIFIER LETTER RAISED COLON
        "api\u2212key=PLAINTEXT-SECRET",  # U+2212 MINUS SIGN
        "token\u2236PLAINTEXT-SECRET",  # U+2236 RATIO
        "token\ua789PLAINTEXT-SECRET",  # U+A789 MODIFIER LETTER COLON
        "token\u02d0PLAINTEXT-SECRET",  # U+02D0 MODIFIER LETTER TRIANGULAR COLON
    ],
)
def test_residual_delimiter_lookalike_witnesses_reject(obfuscated: str) -> None:
    assert _reason_rejects(obfuscated)


# --- F3: retained-state re-entry rejects residual witnesses ---


@pytest.mark.parametrize(
    "corrupted",
    [
        "api\u2043key=PLAINTEXT-SECRET",
        "api\u00b7key=PLAINTEXT-SECRET",
        "token\u02f8PLAINTEXT-SECRET",
    ],
)
def test_residual_delimiter_revalidation_rejects(corrupted: str) -> None:
    _revalidation_rejects(corrupted)


# --- F3: benign text with Pd/non-Pd lookalikes retained byte-for-byte ---


@pytest.mark.parametrize(
    "benign",
    [
        "Evidence\u2043reference\u00b7text\u02f8note",
        "Evidence\u2212market\u2236reference",
        "Benign \u2014 em-dash \u2013 en-dash text",
        "Greek \u03c3 sigma and \u03c2 final sigma evidence",
        "Caf\u00e9 market evidence",
        "col\u00b7lecci\u00f3 catalana",
    ],
)
def test_benign_lookalike_text_is_retained_byte_for_byte(benign: str) -> None:
    assert _reason_retained(benign)


# --- F4: bounded homoglyph composite labels ---


@pytest.mark.parametrize(
    "obfuscated",
    [
        "cl\u0456entsecret",  # Cyrillic i
        "\u0430pikey",  # Cyrillic a
        "priv\u0430te key",  # Cyrillic a
        "access tok\u0435n",  # Cyrillic e
        "cl\u0456ent-secret",
        "\u0430pi_key",
    ],
)
def test_bare_homoglyph_composite_labels_reject(obfuscated: str) -> None:
    assert _reason_rejects(obfuscated)


# --- F4: bounded homoglyph `bearer ` scheme ---


@pytest.mark.parametrize(
    "obfuscated",
    [
        "bearer PLAINTEXT-SECRET",
        "Bearer TOKEN",
        "\u0432earer PLAINTEXT-SECRET",  # Cyrillic ve for b
        "be\u0430rer PLAINTEXT-SECRET",  # Cyrillic a
        "bear\u0435r PLAINTEXT-SECRET",  # Cyrillic e
        "\u0412earer PLAINTEXT-SECRET",  # Cyrillic capital ve for b
        "bea\u0433er PLAINTEXT-SECRET",  # Cyrillic ghe for r
    ],
)
def test_bearer_scheme_rejects_ascii_and_bounded_homoglyphs(
    obfuscated: str,
) -> None:
    assert _reason_rejects(obfuscated)


# --- F5: lunate sigma case pair closed at the root before NFKC ---


@pytest.mark.parametrize(
    "obfuscated",
    [
        "\u03f2redential=PLAINTEXT-SECRET",  # U+03F2 lower lunate sigma
        "\u03f9redential=PLAINTEXT-SECRET",  # U+03F9 capital lunate sigma
        "\u03f2redential:PLAINTEXT-SECRET",
        "\u03f2lientsecret",
        "\u03f9lientsecret",
        "\u03f2lient-secret",
        "\u03f9lient_secret",
        "\u03f2lient secret",
        "\u03f9lient\u2043secret",
        "prefix\u03f2lientsecretpostfix",
    ],
)
def test_lunate_sigma_witnesses_reject(obfuscated: str) -> None:
    assert _reason_rejects(obfuscated)


@pytest.mark.parametrize(
    "corrupted",
    [
        "\u03f2redential=PLAINTEXT-SECRET",
        "\u03f9redential=PLAINTEXT-SECRET",
        "\u03f2lientsecret",
        "\u03f9lientsecret",
    ],
)
def test_lunate_sigma_revalidation_rejects(corrupted: str) -> None:
    _revalidation_rejects(corrupted)


# --- F5: benign lower/capital lunate text retained byte-for-byte ---


@pytest.mark.parametrize(
    "benign",
    [
        "\u03f2 lower lunate sigma text",
        "\u03f9 CAPITAL LUNATE SIGMA TEXT",
        "\u03f2 and \u03f9 lunate pair",
    ],
)
def test_benign_lunate_text_is_retained_byte_for_byte(benign: str) -> None:
    assert _reason_retained(benign)


# --- F2: non-printable format controls remain rejected ---


@pytest.mark.parametrize(
    "filler",
    [
        "\u200c",  # ZWNJ
        "\u200d",  # ZWJ
        "\u200e",  # LRM
        "\u200f",  # RLM
        "\u061c",  # ALM
    ],
)
def test_format_controls_remain_rejected_before_semantic_inspection(
    filler: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="normalized text",
    ):
        registry.InstrumentUniverseReason(f"safe{filler}text")


# --- retained-state re-entry across the evidence record trust edge ---


def test_evidence_record_revalidation_rejects_residual_lookalike_locator() -> None:
    record = registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=registry.InstrumentUniverseEvidenceRef("qore-umi05"),
        source_category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        source_name="QORE repository",
        locator="qore://umi-05/futures",
        verified_on=date(2026, 8, 15),
    )
    object.__setattr__(
        record,
        "locator",
        "https://example.invalid/?api\u2043key=PLAINTEXT-SECRET",
    )

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        record.__post_init__()
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        record.content_logical_values()
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        record.logical_values()


def test_evidence_record_revalidation_rejects_lunate_source_name() -> None:
    record = registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=registry.InstrumentUniverseEvidenceRef("qore-umi05"),
        source_category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        source_name="QORE repository",
        locator="qore://umi-05/futures",
        verified_on=date(2026, 8, 15),
    )
    object.__setattr__(record, "source_name", "\u03f2lientsecret")

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        record.__post_init__()
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        record.content_logical_values()
