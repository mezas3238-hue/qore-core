from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r72_upstream_density_loss as r72,
)


def test_r72_window_contract_preserves_frozen_samples() -> None:
    assert r72._window_contract("5Y")[2] == 2448
    assert r72._window_contract("2Y")[2] == 1017
    assert r72._window_contract("R66")[2] == 773


def test_r72_source_day_reason_uses_exact_v7_contract() -> None:
    assert {
        "NO_TWO_COMPLETE_SOURCE_DAYS",
        "AMBIGUOUS_RESOLVED_DAILY_BIAS",
        "BIAS_AVAILABLE",
    }


def test_r72_identity_is_forensics_only() -> None:
    assert r72.IDENTITY == (
        "VT08_INDEX_R72_UPSTREAM_DENSITY_LOSS_FORENSICS_001"
    )
