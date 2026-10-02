from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.cibo_phase22_v4_vt31_abi import (
    adapt_v4_vt31_market_evidence,
)


class _Source:
    series = (object(),)
    fingerprint = "sha256:" + "a" * 64
    last_closed_at = datetime(2015, 4, 19, tzinfo=UTC)
    corpus_git_sha = "b" * 40
    provider_symbol = "USTEC"


def test_v4_vt31_abi_adapts_prefixed_source_digest_to_frozen_engine_digest() -> None:
    adapted = adapt_v4_vt31_market_evidence(_Source())

    assert len(adapted) == 6
    assert adapted[2] == "a" * 64
    assert not adapted[2].startswith("sha256:")
