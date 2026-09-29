from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_dynamic_episode_edge_reserve_relief_v2 as v2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_reserved_global_episode_sequence_beam_v43 as v43,
)


def _metrics(*, pf: str, total: str, dd: str, ls: int) -> dict[str, object]:
    return {
        "profit_factor": pf,
        "total_r": total,
        "max_drawdown_r": dd,
        "max_losing_streak": ls,
        "trades": 1088,
    }


def _seed(
    symbol: str,
    entry_at: str,
    action: str,
    *,
    total: str = "1",
    dd: str = "0.2",
    in_dd: bool = True,
) -> v2.ActionSeed:
    return v2.ActionSeed(
        symbol=symbol,
        entry_at=entry_at,
        action=action,
        source_dynamic_total_delta_r=total,
        source_legacy_dd_relief_r=dd,
        source_rollout_profit_factor="1.3",
        source_in_max_dd_descent=in_dd,
    )


def test_rank_prioritizes_gate_violations_before_raw_dd() -> None:
    baseline = _metrics(pf="1.22", total="27", dd="8.7", ls=6)
    feasible = v43.SearchNode(
        depth=1,
        plan={("A", "2021-01-01T00:00:00+00:00"): "ORIGINAL"},
        metrics=_metrics(pf="1.30", total="30", dd="5.99", ls=6),
        parent_signature=None,
        mutation="ADD",
    )
    low_dd_but_bad_pf = v43.SearchNode(
        depth=1,
        plan={("B", "2021-01-01T00:00:00+00:00"): "ORIGINAL"},
        metrics=_metrics(pf="1.00", total="30", dd="5.50", ls=6),
        parent_signature=None,
        mutation="ADD",
    )

    assert v43._rank(feasible, baseline=baseline) < v43._rank(
        low_dd_but_bad_pf,
        baseline=baseline,
    )


def test_mutations_use_canonical_chronological_add_and_replacement() -> None:
    plan: v43.Plan = {
        ("EURUSD", "2021-01-02T00:00:00+00:00"): "BE_AFTER_050"
    }
    pool = (
        _seed(
            "USDJPY",
            "2021-01-01T00:00:00+00:00",
            "ORIGINAL",
        ),
        _seed(
            "EURUSD",
            "2021-01-02T00:00:00+00:00",
            "LOCK025_AFTER_075",
        ),
        _seed(
            "GBPUSD",
            "2021-01-03T00:00:00+00:00",
            "BE_AFTER_075",
        ),
    )

    rows = v43._mutations(plan, pool=pool)
    labels = {label for label, _child in rows}

    assert not any("USDJPY" in label for label in labels)
    assert any(label.startswith("REPLACE:EURUSD") for label in labels)
    assert any(label.startswith("ADD:GBPUSD") for label in labels)
    assert not any(label.startswith("DROP:") for label in labels)


def test_empty_plan_can_start_from_any_pool_timestamp() -> None:
    pool = (
        _seed(
            "USDJPY",
            "2021-01-01T00:00:00+00:00",
            "ORIGINAL",
        ),
        _seed(
            "GBPUSD",
            "2021-01-03T00:00:00+00:00",
            "BE_AFTER_075",
        ),
    )

    rows = v43._mutations({}, pool=pool)

    assert len(rows) == 2
    assert all(label.startswith("ADD:") for label, _child in rows)


def test_signature_is_order_invariant() -> None:
    left: v43.Plan = {
        ("B", "2"): "BE_AFTER_050",
        ("A", "1"): "ORIGINAL",
    }
    right: v43.Plan = {
        ("A", "1"): "ORIGINAL",
        ("B", "2"): "BE_AFTER_050",
    }

    assert v43._signature(left) == v43._signature(right)


def test_search_constants_match_frozen_predeclaration() -> None:
    assert v43.MAXDD_RELIEF_POOL == 24
    assert v43.MAXDD_RESERVE_POOL == 24
    assert v43.OUTSIDE_RELIEF_POOL == 16
    assert v43.OUTSIDE_RESERVE_POOL == 16
    assert v43.BEAM_WIDTH == 8
    assert v43.MAX_MUTATION_DEPTH == 8
