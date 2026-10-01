from collections import Counter, defaultdict

from qore.infrastructure.cibo_arch2_t11_experiment_plan import (
    T11_MARKET_IMPACT_EXPERIMENT_PLAN,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    REQUIRED_SYMBOLS,
)


def test_t11_plan_freezes_exact_population_before_evidence() -> None:
    plan = T11_MARKET_IMPACT_EXPERIMENT_PLAN

    assert plan.episode_count == 144
    assert plan.child_entry_count == 216
    assert plan.broker_mutation_authorized is False
    assert plan.phase22_v2_consumption_authorized is False
    assert plan.productive_authority is False
    assert plan.fingerprint().startswith("sha256:")


def test_t11_plan_has_exact_symbol_phase_pair_surface() -> None:
    plan = T11_MARKET_IMPACT_EXPERIMENT_PLAN
    counts = Counter((item.qore_symbol, item.phase) for item in plan.episodes)

    for symbol in REQUIRED_SYMBOLS:
        assert counts[(symbol, "CALIBRATION")] == 16
        assert counts[(symbol, "VALIDATION")] == 8


def test_t11_plan_balances_sides_and_alternates_level_order() -> None:
    plan = T11_MARKET_IMPACT_EXPERIMENT_PLAN
    pairs = defaultdict(list)
    for item in plan.episodes:
        pairs[(item.qore_symbol, item.phase, item.pair_index)].append(item)

    for (_symbol, phase, pair_index), rows in pairs.items():
        ordered = sorted(rows, key=lambda item: item.level_order_position)
        expected = (1, 2) if pair_index % 2 else (2, 1)
        assert tuple(item.child_count for item in ordered) == expected
        expected_side = "long" if pair_index % 2 else "short"
        assert {item.side for item in rows} == {expected_side}
        assert all(item.deposit_asset == "USD" for item in rows)
        assert all(
            item.both_children_open_before_close_required is True
            for item in rows
        )
        if phase == "VALIDATION":
            assert {item.fold_index for item in rows} == {pair_index}
        else:
            assert {item.fold_index for item in rows} == {0}


def test_t11_plan_has_balanced_long_short_pairs_per_phase_and_symbol() -> None:
    plan = T11_MARKET_IMPACT_EXPERIMENT_PLAN
    seen = {}
    for item in plan.episodes:
        key = (item.qore_symbol, item.phase, item.pair_index)
        seen.setdefault(key, item.side)

    counts = Counter(
        (symbol, phase, side)
        for (symbol, phase, _pair), side in seen.items()
    )
    for symbol in REQUIRED_SYMBOLS:
        assert counts[(symbol, "CALIBRATION", "long")] == 4
        assert counts[(symbol, "CALIBRATION", "short")] == 4
        assert counts[(symbol, "VALIDATION", "long")] == 2
        assert counts[(symbol, "VALIDATION", "short")] == 2
