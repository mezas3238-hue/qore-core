from dataclasses import replace

from qore.kernel.identity import Identity


def test_identity_creation_and_access() -> None:
    uid = Identity(id="abc-123")
    assert uid.id == "abc-123"


def test_identity_immutability_by_replacement() -> None:
    uid = Identity(id=42)
    altered = replace(uid, id=99)
    assert uid.id == 42
    assert altered.id == 99
    assert altered is not uid


def test_identity_equality_and_hash() -> None:
    a = Identity(id="xyz")
    b = Identity(id="xyz")
    c = Identity(id="other")
    assert a == b
    assert a != c
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_identity_not_equal_to_other_type() -> None:
    identity = Identity(id=1)
    assert identity.__eq__(object()) is NotImplemented
