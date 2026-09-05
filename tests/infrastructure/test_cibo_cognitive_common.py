"""Tests for shared CIBO Cognitive Superarchitecture primitives."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    canonical_material,
    contains_secret_material,
    fingerprint_material,
    require_exact_int,
    require_exact_str,
)


def test_fingerprint_is_deterministic_and_distinct() -> None:
    first = fingerprint_material("a", 1, True, None, (2, "b"))
    second = fingerprint_material("a", 1, True, None, (2, "b"))
    other = fingerprint_material("a", 1, True, None, (2, "c"))
    assert first == second
    assert first != other
    assert first.value != other.value


def test_fingerprint_material_rejects_float_and_dict() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        fingerprint_material(1.5)
    with pytest.raises(CiboCognitiveValidationError):
        fingerprint_material({"a": 1})


def test_bool_is_not_int_for_fingerprint_canonical_material() -> None:
    assert canonical_material(True) != canonical_material(1)
    assert canonical_material(False) != canonical_material(0)


def test_exact_int_rejects_bool() -> None:
    assert require_exact_int(5, field="score") == 5
    with pytest.raises(CiboCognitiveValidationError):
        require_exact_int(True, field="score")


def test_exact_str_rejects_subclass() -> None:
    class EvilStr(str):
        pass

    assert require_exact_str("ok", field="value") == "ok"
    with pytest.raises(CiboCognitiveValidationError):
        require_exact_str(EvilStr("ok"), field="value")


def test_fingerprint_rejects_non_hex_and_subclass() -> None:
    assert CiboCognitiveFingerprint("a" * 64).value == "a" * 64
    with pytest.raises(CiboCognitiveValidationError):
        CiboCognitiveFingerprint("not-hex")
    with pytest.raises(CiboCognitiveValidationError):
        CiboCognitiveFingerprint(12345)  # type: ignore[arg-type]


def test_secret_material_detected() -> None:
    assert contains_secret_material("api_key=sk-abcdef12345678")
    assert contains_secret_material("Authorization: Bearer abcdef1234567890")
    assert contains_secret_material("-----BEGIN PRIVATE KEY-----")
    assert contains_secret_material("https://user:pass@example.com")
    assert not contains_secret_material("ordinary cognitive summary text")


def test_canonical_material_naive_datetime_rejected() -> None:
    naive = datetime(2024, 1, 1)
    with pytest.raises(CiboCognitiveValidationError):
        fingerprint_material(naive)


def test_canonical_material_aware_datetime() -> None:
    aware = datetime(2024, 1, 1, tzinfo=UTC)
    assert fingerprint_material(aware) == fingerprint_material(aware)


class _HostileLogicalValues:
    """A duck-typed object that must be rejected as canonical material."""

    def logical_values(self) -> tuple[str]:
        return ("api_key=sk-abcdef12345678",)


class _NondeterministicLogicalValues:
    """A duck-typed object whose logical_values changes every call."""

    def __init__(self) -> None:
        self.calls = 0

    def logical_values(self) -> tuple[str]:
        self.calls += 1
        return (f"value-{self.calls}",)


def test_canonical_material_rejects_hostile_logical_values_object() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        canonical_material(_HostileLogicalValues())
    with pytest.raises(CiboCognitiveValidationError):
        fingerprint_material(_HostileLogicalValues())


def test_canonical_material_rejects_nondeterministic_logical_values_object() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        fingerprint_material(_NondeterministicLogicalValues())


def test_canonical_material_rejects_secret_bearing_string() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        canonical_material("Authorization: Bearer abcdef1234567890")
    with pytest.raises(CiboCognitiveValidationError):
        fingerprint_material("-----BEGIN PRIVATE KEY-----")


def test_canonical_material_accepts_sha256_hex_and_evidence_refs() -> None:
    digest = "a" * 64
    assert fingerprint_material(digest) == fingerprint_material(digest)
    assert fingerprint_material(f"sha256:{digest}") == fingerprint_material(f"sha256:{digest}")


def test_contains_secret_material_union_semantics() -> None:
    # Structural markers (formerly Batch008-only) plus legacy literal tokens and
    # every GitHub/Slack token variant.
    for witness in (
        "sk-proj-abcdefghijklmnopqrstuvwxyz123456",
        "AKIAIOSFODNN7EXAMPLE",
        "ghp_abcdefghijklmnopqrstuvwxyz1234",
        "gho_abcdefghijklmnopqrstuvwxyz1234",
        "ghu_abcdefghijklmnopqrstuvwxyz1234",
        "ghs_abcdefghijklmnopqrstuvwxyz1234",
        "ghr_abcdefghijklmnopqrstuvwxyz1234",
        "xoxb-123456789012-abcdefghijklmnopqrstuvwxyz",
        "xoxp-123456789012-abcdefghijklmnopqrstuvwxyz",
        "xoxa-123456789012-abcdefghijklmnopqrstuvwxyz",
        "xoxr-123456789012-abcdefghijklmnopqrstuvwxyz",
        "xoxs-123456789012-abcdefghijklmnopqrstuvwxyz",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature",
        "https://alice:correcthorsebatterystaple@example.com/x",
        "token=abc123",
        "secret=value",
        "client_secret=abcdefghijklmnopqrstuvwxyz123456",
        "private_key=abcdefghijklmnopqrstuvwxyz123456",
    ):
        assert contains_secret_material(witness), witness
    for benign in (
        "all service passwords are required to rotate",
        "the authentication failed and was retried",
        "a token of appreciation was issued",
        "sk-8",
        "https://example.com/path",
        "the bearer of good news",
        # Bare field-name mentions are not secret material (no naive substring).
        "the client_secret field must be configured",
        "the private_key is a field name in this document",
        "client_secret_demo",
    ):
        assert not contains_secret_material(benign), benign


def test_contains_secret_material_re_export_is_canonical() -> None:
    from qore.modules.cibo.cognitive_contracts import (
        contains_secret_material as canonical_detector,
    )

    assert canonical_detector is contains_secret_material


def test_contains_secret_material_requires_exact_str() -> None:
    from qore.modules.cibo.cognitive_contracts import (
        CiboCognitiveValidationError as DomainValidationError,
    )

    class Sneaky(str):
        pass

    with pytest.raises(DomainValidationError):
        contains_secret_material(Sneaky("sk-abcdefghijklmnop"))


def test_secret_detector_covers_aws_asia_basic_and_json_labels() -> None:
    for witness in (
        "ASIAIOSFODNN7EXAMPLE",
        "Basic dXNlcjpwYXNz",
        "Basic YWxpY2U6cGFzc3dvcmQ=",
        '"client_secret": "abcdefghijklmnopqrstuvwxyz123456"',
        '{"client_secret": "abcdefghijklmnopqrstuvwxyz123456"}',
        '"api_key": "abcdefghijklmnopqrstuvwxyz123456"',
        "xoxc-123456789012-abcdefghijklmnopqrstuvwxyz",
    ):
        assert contains_secret_material(witness), witness


def test_secret_detector_rejects_bearer_and_basic_prose() -> None:
    for benign in (
        "Bearer certificate",
        "Bearer obligations",
        "Bearer instruments",
        "Basic principles",
        "Basic authentication",
        "basic authentication is the http scheme",
        "Basic method",
        "Basic assumption",
    ):
        assert not contains_secret_material(benign), benign
