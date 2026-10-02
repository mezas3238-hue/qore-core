from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.cibo_phase22_v5_store_contract import (
    PHASE22_V5_STORE_IDENTITIES,
    PHASE22_V5_STORE_ROOT_NAME,
    assert_phase22_v5_store_pristine,
)
from qore.infrastructure.cibo_phase22_v5_vt31_abi import (
    adapt_v5_vt31_market_evidence,
)


class _Source:
    series = (object(),)
    fingerprint = "sha256:" + "a" * 64
    last_closed_at = datetime(2014, 10, 19, tzinfo=UTC)
    corpus_git_sha = "b" * 40
    provider_symbol = "USTEC"


def test_v5_store_namespace_is_disjoint(tmp_path: Path) -> None:
    root = tmp_path / PHASE22_V5_STORE_ROOT_NAME
    assert_phase22_v5_store_pristine(root)
    assert len(PHASE22_V5_STORE_IDENTITIES) == 5
    assert all(
        item.relative_path.startswith("phase22-v5-stores/")
        for item in PHASE22_V5_STORE_IDENTITIES
    )
    assert all(
        "phase22-v4-stores" not in item.relative_path
        for item in PHASE22_V5_STORE_IDENTITIES
    )


def test_v5_vt31_abi_normalizes_prefixed_digest_pre_outcome() -> None:
    adapted = adapt_v5_vt31_market_evidence(_Source())

    assert len(adapted) == 6
    assert adapted[2] == "a" * 64
    assert not adapted[2].startswith("sha256:")
