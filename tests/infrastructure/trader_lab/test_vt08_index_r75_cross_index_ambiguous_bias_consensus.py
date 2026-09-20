from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r75_cross_index_ambiguous_bias_consensus as r75,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def test_r75_strict_peer_consensus_requires_both_peers() -> None:
    side, reason = r75._strict_peer_consensus(
        DemoTradingSetupSide.LONG,
        None,
    )
    assert side is None
    assert reason == "PEER_UNRESOLVED_OR_UNAVAILABLE"


def test_r75_strict_peer_consensus_rejects_disagreement() -> None:
    side, reason = r75._strict_peer_consensus(
        DemoTradingSetupSide.LONG,
        DemoTradingSetupSide.SHORT,
    )
    assert side is None
    assert reason == "PEER_DISAGREEMENT"


def test_r75_strict_peer_consensus_accepts_unanimity() -> None:
    side, reason = r75._strict_peer_consensus(
        DemoTradingSetupSide.SHORT,
        DemoTradingSetupSide.SHORT,
    )
    assert side is DemoTradingSetupSide.SHORT
    assert reason == "PEER_UNANIMOUS"


def test_r75_targets_only_r73_dominant_ambiguous_families() -> None:
    assert r75.TARGET_FAMILIES == (
        "INSIDE_NO_EXTREME_SWEEP",
        "DOUBLE_SWEEP_CLOSE_INSIDE",
    )


def test_r75_source_r74_evidence_is_frozen() -> None:
    assert r75.SOURCE_R74_RUN_ID == 35512797040
    assert r75.SOURCE_R74_ARTIFACT_ID == 10605239547
    assert r75.SOURCE_R74_ARTIFACT_DIGEST.startswith("sha256:")
