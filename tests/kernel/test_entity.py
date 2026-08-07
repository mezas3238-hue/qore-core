import pytest

from qore.kernel.entity import Entity


class User(Entity[str]):
    def __init__(self, user_id: str, name: str) -> None:
        super().__init__(user_id)
        self.name = name


class Admin(Entity[str]):
    def __init__(self, user_id: str, level: int) -> None:
        super().__init__(user_id)
        self.level = level


def test_entity_id_property_has_no_setter() -> None:
    assert User.id.fset is None


def test_entity_direct_identity_mutation_raises() -> None:
    user = User("u1", "Alice")
    with pytest.raises(AttributeError, match="Entity identity is immutable"):
        user._id = "u2"


def test_entity_equality_uses_type_and_identity() -> None:
    assert User("u1", "Alice") == User("u1", "Bob")
    assert User("u1", "Alice") != User("u2", "Alice")
    assert User("u1", "Alice") != Admin("u1", 10)


def test_equal_entities_have_equal_hashes() -> None:
    assert hash(User("u1", "Alice")) == hash(User("u1", "Bob"))


def test_entity_non_identity_attributes_are_mutable() -> None:
    user = User("u1", "Alice")
    user.name = "Alicia"
    assert user.name == "Alicia"
