from __future__ import annotations

from decimal import Decimal
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round3 as mod
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7


def _candidate(
    *,
    sample: int,
    pf: str,
    dd: str,
    pf10: str = "1.10",
    dd10: str = "13",
    halves: int = 2,
    quarters: int = 7,
    mean: str = "0.10",
) -> dict[str, Any]:
    return {
        "positive_halves": halves,
        "positive_quarters": quarters,
        "primary_stress": {
            "sample": sample,
            "profit_factor": pf,
            "max_drawdown_r": dd,
            "mean_r": mean,
        },
        "secondary_stress": {
            "sample": sample,
            "profit_factor": pf10,
            "max_drawdown_r": dd10,
            "mean_r": mean,
        },
    }


def test_round3_uses_every_frozen_v7_executable_anchor() -> None:
    assert mod.ANCHORS == tuple(v7.EXECUTABLE_H4_ANCHORS_NY)
    assert mod.ANCHORS == (22, 2, 6, 10)
    anchor_sets = mod._anchor_sets()
    assert (22,) in anchor_sets
    assert (2, 6, 10) in anchor_sets
    assert (22, 2, 6, 10) in anchor_sets
    assert len(anchor_sets) == 15


def test_round3_goal_requires_activity_pf_dd_stress_and_stability() -> None:
    passing = _candidate(sample=650, pf="1.20", dd="10")
    assert mod._goal(passing) is True

    assert mod._goal(_candidate(sample=599, pf="1.50", dd="5")) is False
    assert mod._goal(_candidate(sample=650, pf="1.14", dd="5")) is False
    assert mod._goal(_candidate(sample=650, pf="1.50", dd="12.01")) is False
    assert mod._goal(
        _candidate(sample=650, pf="1.50", dd="5", pf10="1.04")
    ) is False
    assert mod._goal(
        _candidate(sample=650, pf="1.50", dd="5", dd10="15.01")
    ) is False
    assert mod._goal(
        _candidate(sample=650, pf="1.50", dd="5", halves=1)
    ) is False
    assert mod._goal(
        _candidate(sample=650, pf="1.50", dd="5", quarters=5)
    ) is False


def test_activity_tiers_do_not_hide_frequency() -> None:
    candidates = [
        _candidate(sample=410, pf="1.05", dd="20"),
        _candidate(sample=305, pf="1.18", dd="11"),
        _candidate(sample=205, pf="1.40", dd="7"),
        _candidate(sample=120, pf="2.00", dd="3"),
    ]
    tiers = mod._tier_best(candidates)
    assert tiers["400"] is candidates[0]
    assert tiers["300"] is candidates[1]
    assert tiers["200"] is candidates[2]
    assert tiers["100"] is candidates[3]


def test_rank_prefers_stability_before_pf() -> None:
    stable = _candidate(sample=650, pf="1.20", dd="10")
    unstable = _candidate(sample=650, pf="2.00", dd="2", halves=1, quarters=4)
    assert mod._rank(stable) > mod._rank(unstable)


def test_round3_contract_goals_are_explicit() -> None:
    assert mod.PF_GOAL == Decimal("1.15")
    assert mod.DD_GOAL == Decimal("12")
    assert mod.ACTIVITY_FLOORS == (100, 200, 300, 400, 500, 600, 700, 800)
    assert mod.IDENTITY == "VT08_INDEX_CIBO_2Y_TUNING_ROUND3_ANCHOR_COMPLETE"
