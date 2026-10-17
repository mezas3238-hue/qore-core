from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2be_audusd_candidate_robustness import (
    BLOCK_LENGTHS,
    COST_STRESS_R,
    END,
    EXCLUDED_LABEL,
    IDENTITY,
    START,
    YEARS,
)


def test_r2be_candidate_and_window_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BE_AUDUSD_FROZEN_CANDIDATE_ROBUSTNESS_001"
    assert EXCLUDED_LABEL == "CONFOVERLAP_0_50_TO_0_75"
    assert START.year == 2011
    assert END.year == 2026
    assert YEARS == 15


def test_r2be_robustness_families_are_frozen() -> None:
    assert COST_STRESS_R == (0.02, 0.05, 0.10)
    assert BLOCK_LENGTHS == (2, 4, 8)
