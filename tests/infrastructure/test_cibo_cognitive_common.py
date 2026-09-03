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
