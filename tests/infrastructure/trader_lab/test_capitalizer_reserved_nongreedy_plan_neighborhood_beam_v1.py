from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_dynamic_episode_edge_reserve_relief_v2 as v2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_reserved_nongreedy_plan_neighborhood_beam_v1 as beam,
)


def _metrics(*, pf: str, total: str, dd: str, ls: int) -> dict[str, object]:
    return {
        "profit_factor": pf,
        "total_r": total,
        "max_drawdown_r": dd,
        "max_losing_streak": ls,
        "trades": 1088,
    }


def _seed(symbol: str, entry_at: str, action: str, *, total: str, dd: str) -> v2.ActionSeed:
    return v2.ActionSeed(
        symbol=symbol,
        entry_at=entry_at,
        action=action,
        source_dynamic_total_delta_r=total,
        source_legacy_dd_relief_r=dd,
        source_rollout_profit_factor="1.3",
        source_in_max_dd_descent=True,
    )


def test_rank_prioritizes_gate_violations_before_raw_dd() -> None:
    baseline = _metrics(pf="1.22", total="27", dd="8.7", ls=6)
    feasible = beam.SearchNode(
        depth=1,
        plan={("A", "2021-01-01T00:00:00+00:00"): "ORIGINAL"},
        metrics=_metrics(pf="1.30", total="30", dd="5.99", ls=6),
        parent_signature=None,
        mutation="SET",
    )
    low_dd_but_bad_pf = beam.SearchNode(
        depth=1,
        plan={("B", "2021-01-01T00:00:00+00:00"): "ORIGINAL"},
        metrics=_metrics(pf="1.00", total="30", dd="5.50", ls=6),
        parent_signature=None,
        mutation="SET",
    )

    assert beam._rank(feasible, baseline=baseline) < beam._rank(
        low_dd_but_bad_pf,
        baseline=baseline,
    )


def test_mutations_include_drop_add_and_replace() -> None:
    plan: beam.Plan = {
        ("EURUSD", "2021-01-01T00:00:00+00:00"): "BE_AFTER_050"
    }
    pool = (
        _seed(
            "EURUSD",
            "2021-01-01T00:00:00+00:00",
            "LOCK025_AFTER_075",
            total="1",
            dd="0.2",
        ),
        _seed(
            "GBPUSD",
            "2021-01-01T01:00:00+00:00",
            "BE_AFTER_075",
            total="2",
            dd="0.1",
        ),
    )

    rows = beam._mutations(plan, pool=pool)
    labels = {label for label, _child in rows}

    assert any(label.startswith("DROP:EURUSD") for label in labels)
    assert any("BE_AFTER_050->LOCK025_AFTER_075" in label for label in labels)
    assert any("NONE->BE_AFTER_075" in label for label in labels)


def test_signature_is_order_invariant() -> None:
    left: beam.Plan = {
        ("B", "2"): "BE_AFTER_050",
        ("A", "1"): "ORIGINAL",
    }
    right: beam.Plan = {
        ("A", "1"): "ORIGINAL",
        ("B", "2"): "BE_AFTER_050",
    }

    assert beam._signature(left) == beam._signature(right)


def test_search_constants_are_frozen() -> None:
    assert beam.RELIEF_POOL == 24
    assert beam.RESERVE_POOL == 24
    assert beam.BEAM_WIDTH == 6
    assert beam.MAX_MUTATION_DEPTH == 4
