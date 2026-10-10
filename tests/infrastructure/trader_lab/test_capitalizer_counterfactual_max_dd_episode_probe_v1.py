from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_counterfactual_max_dd_episode_probe_v1 as probe,
)


def test_probe_identity() -> None:
    assert probe.IDENTITY == (
        "QORE_CAPITALIZER_COUNTERFACTUAL_MAX_DD_EPISODE_PROBE_V1"
    )
