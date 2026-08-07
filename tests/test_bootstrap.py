"""Executable evidence for the QORE Genesis bootstrap."""

from dataclasses import replace

import qore
from qore.core.bootstrap import CoreIdentity, bootstrap


def test_qore_package_is_importable() -> None:
    assert qore.__name__ == "qore"


def test_bootstrap_returns_genesis_identity() -> None:
    identity = bootstrap()

    assert isinstance(identity, CoreIdentity)
    assert identity.name == "QORE"
    assert identity.version == "0.1.0"
    assert identity.mode == "GENESIS"


def test_core_identity_is_immutable() -> None:
    identity = bootstrap()
    altered = replace(identity, mode="ALTERED")

    assert identity.mode == "GENESIS"
    assert altered.mode == "ALTERED"
    assert altered is not identity
