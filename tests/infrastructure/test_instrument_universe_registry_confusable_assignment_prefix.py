from __future__ import annotations

import pytest

import qore.infrastructure.instrument_universe_registry as registry


@pytest.mark.parametrize(
    "obfuscated_value",
    [
        "αtоken=PLAINTEXT-SECRET",  # Greek α prefix + Cyrillic о (U+043E)
        "αtоken:PLAINTEXT-SECRET",
        "xtоken=PLAINTEXT-SECRET",  # ASCII x prefix + Cyrillic о (U+043E)
        "xtоken:PLAINTEXT-SECRET",
    ],
)
def test_constructor_rejects_primary_prefixed_confusable_escape_witnesses(
    obfuscated_value: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(obfuscated_value)


@pytest.mark.parametrize(
    "obfuscated_value",
    [
        "tоken=PLAINTEXT-SECRET",  # Cyrillic о (U+043E)
        "tоken:PLAINTEXT-SECRET",
    ],
)
def test_constructor_rejects_bare_confusable_assignment_baseline(
    obfuscated_value: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(obfuscated_value)


@pytest.mark.parametrize(
    "obfuscated_value",
    [
        # ASCII prefix `x` — all 11 declared labels, each with >= 1 confusable.
        "xauthоrization=PLAINTEXT-SECRET",  # authorization: Cyrillic о
        "xbеarer=PLAINTEXT-SECRET",  # bearer: Cyrillic е
        "xcrеdential=PLAINTEXT-SECRET",  # credential: Cyrillic е
        "xјwt=PLAINTEXT-SECRET",  # jwt: Cyrillic ј (U+0458)
        "xpaѕѕword=PLAINTEXT-SECRET",  # password: Cyrillic ѕ (U+0455) x2
        "xsеcret=PLAINTEXT-SECRET",  # secret: Cyrillic е
        "xtоken=PLAINTEXT-SECRET",  # token: Cyrillic о
        "xapikеy=PLAINTEXT-SECRET",  # apikey: Cyrillic е
        "xaccesstоken=PLAINTEXT-SECRET",  # accesstoken: Cyrillic о
        "xclientsеcret=PLAINTEXT-SECRET",  # clientsecret: Cyrillic е
        "xprivatekеy=PLAINTEXT-SECRET",  # privatekey: Cyrillic е
        # Unicode confusable prefix `α` — all 11 labels, same substitutions.
        "αauthоrization=PLAINTEXT-SECRET",
        "αbеarer=PLAINTEXT-SECRET",
        "αcrеdential=PLAINTEXT-SECRET",
        "αјwt=PLAINTEXT-SECRET",
        "αpaѕѕword=PLAINTEXT-SECRET",
        "αsеcret=PLAINTEXT-SECRET",
        "αtоken=PLAINTEXT-SECRET",
        "αapikеy=PLAINTEXT-SECRET",
        "αaccesstоken=PLAINTEXT-SECRET",
        "αclientsеcret=PLAINTEXT-SECRET",
        "αprivatekеy=PLAINTEXT-SECRET",
    ],
)
def test_constructor_rejects_alphanumeric_prefix_for_all_sensitive_labels(
    obfuscated_value: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(obfuscated_value)


@pytest.mark.parametrize(
    "obfuscated_value",
    [
        # Composite families in joined-with-separator and spaced forms.
        "xapi_kеy=PLAINTEXT-SECRET",  # api key: underscore + Cyrillic е
        "xapi kеy=PLAINTEXT-SECRET",  # api key: space + Cyrillic е
        "xapi-kеy=PLAINTEXT-SECRET",  # api key: hyphen + Cyrillic е
        "xapi.kеy=PLAINTEXT-SECRET",  # api key: dot + Cyrillic е
        "xapi∙kеy=PLAINTEXT-SECRET",  # api key: middle dot (U+00B7)
        "xapi・kеy=PLAINTEXT-SECRET",  # api key: katakana middle dot (U+30FB)
        "xaccess_tоken=PLAINTEXT-SECRET",  # access token: underscore
        "xaccess tоken=PLAINTEXT-SECRET",  # access token: space
        "xclient_sеcret=PLAINTEXT-SECRET",  # client secret: underscore
        "xclient sеcret=PLAINTEXT-SECRET",  # client secret: space
        "xprivate_kеy=PLAINTEXT-SECRET",  # private key: underscore
        "xprivate kеy=PLAINTEXT-SECRET",  # private key: space
        # Unicode confusable prefix `α` on the separator forms.
        "αapi_kеy=PLAINTEXT-SECRET",
        "αaccess_tоken=PLAINTEXT-SECRET",
        "αclient_sеcret=PLAINTEXT-SECRET",
        "αprivate_kеy=PLAINTEXT-SECRET",
    ],
)
def test_constructor_rejects_composite_confusable_separator_forms(
    obfuscated_value: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(obfuscated_value)


@pytest.mark.parametrize(
    "delimiter",
    [
        "=",  # ASCII equals sign
        ":",  # ASCII colon
        "＝",  # U+FF1D FULLWIDTH EQUALS SIGN
        "∶",  # U+2236 RATIO
        "⹀",  # U+2E40 DOUBLE HYPHEN
    ],
)
def test_constructor_rejects_prefixed_confusable_assignment_across_delimiters(
    delimiter: str,
) -> None:
    value = f"xtоken{delimiter}PLAINTEXT-SECRET"

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize(
    "safe_value",
    [
        "tokenx=PLAINTEXT-SECRET",
        "secrety=PLAINTEXT-SECRET",
        "password1=PLAINTEXT-SECRET",
        "bearerx:PLAINTEXT-SECRET",
        "credentialz:PLAINTEXT-SECRET",
        "authorization_x=PLAINTEXT-SECRET",
        "tokenizer=PLAINTEXT-SECRET",
        "secretsauce=PLAINTEXT-SECRET",
    ],
)
def test_constructor_accepts_suffixed_non_label_values(safe_value: str) -> None:
    reason = registry.InstrumentUniverseReason(safe_value)

    assert reason.logical_values() == (safe_value,)


@pytest.mark.parametrize(
    "corrupted_value",
    [
        "αtоken=PLAINTEXT-SECRET",  # Greek α prefix + Cyrillic о
        "xtоken=PLAINTEXT-SECRET",  # ASCII x prefix + Cyrillic о
    ],
)
def test_revalidation_rejects_prefixed_confusable_assignment(
    corrupted_value: str,
) -> None:
    reason = registry.InstrumentUniverseReason("Safe retained reason")
    object.__setattr__(reason, "value", corrupted_value)

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


def test_legitimate_unicode_reason_remains_byte_identical() -> None:
    value = "Αγορά evidence — рынок № 42"

    reason = registry.InstrumentUniverseReason(value)

    projected = reason.logical_values()
    assert projected == (value,)
    assert projected[0].encode("utf-8") == value.encode("utf-8")
