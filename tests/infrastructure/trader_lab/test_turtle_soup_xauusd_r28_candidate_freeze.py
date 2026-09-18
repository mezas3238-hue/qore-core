from __future__ import annotations

import hashlib

from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r28_candidate_freeze as freeze,
)


def test_sha256_helper_matches_standard_library(tmp_path) -> None:
    path = tmp_path / "evidence.bin"
    path.write_bytes(b"qore-r28-freeze")
    assert freeze._sha256(path) == hashlib.sha256(b"qore-r28-freeze").hexdigest()


def test_freeze_identity_and_governance_constants_are_stable() -> None:
    assert (
        freeze.CANDIDATE_ID
        == "TURTLE_SOUP_XAUUSD_R28_VALIDATED_SPECIALIST_CANDIDATE_001"
    )
    assert freeze.R28_RUN_ID == 35305338898
    assert freeze.R28_ARTIFACT_ID == 10531258915
    assert (
        freeze.R28_GIT_SHA
        == "c35f8414ce59e26a36cdda27c2a964a426c3e5ba"
    )
