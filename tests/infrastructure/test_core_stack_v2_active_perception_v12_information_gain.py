from __future__ import annotations

from qore.infrastructure.core_stack_v2.active_perception_v12_information_gain import (
    MIN_POOLED_INCREMENTAL_FALSE_VETO_BPS,
    V12InformationGainFold,
    evaluate_v12_information_gain_fold,
    fit_v12_microstructure_density,
    score_v12_microstructure_micros,
    select_v12_information_gain_candidate,
    summarize_v12_candidate_information_gain,
)
from qore.infrastructure.core_stack_v2.active_perception_v12_microstructure_representation import (
    v12_microstructure_candidate_fields,
)


def _row(value: int, *, available: int = 1) -> dict[str, object]:
    result: dict[str, object] = {
        "bid_present": 1,
        "ask_present": 1,
        "bid_fresh": available,
        "ask_fresh": available,
        "causal_pair_available": available,
        "crossed_causal_quote": 0,
        "bid_age_ratio_bps": value,
        "ask_age_ratio_bps": value,
        "age_skew_ratio_bps": 0,
        "spread_bps": value,
    }
    for window_ms in (1000, 5000, 15000, 60000):
        result[f"w{window_ms}_bid_update_rate_x1000"] = value
        result[f"w{window_ms}_ask_update_rate_x1000"] = value
        result[f"w{window_ms}_total_update_rate_x1000"] = value * 2
        result[f"w{window_ms}_update_imbalance_bps"] = 0
        result[f"w{window_ms}_bid_displacement_bps"] = value
        result[f"w{window_ms}_ask_displacement_bps"] = value
        result[f"w{window_ms}_bid_path_variation_bps"] = abs(value)
        result[f"w{window_ms}_ask_path_variation_bps"] = abs(value)
        result[f"w{window_ms}_path_variation_asymmetry_bps"] = 0
    return result


def test_density_score_separates_simple_terminal_and_nonterminal_rows() -> None:
    rows = tuple(_row(9000 + index) for index in range(12)) + tuple(
        _row(1000 + index) for index in range(12)
    )
    labels = (True,) * 12 + (False,) * 12

    model = fit_v12_microstructure_density(
        candidate="M0_QUOTE_STATE",
        rows=rows,
        labels=labels,
    )

    assert score_v12_microstructure_micros(model, _row(9500)) > 0
    assert score_v12_microstructure_micros(model, _row(1050)) < 0


def test_null_pair_numerics_are_zero_filled_after_indicators_exist() -> None:
    rows = []
    labels = []
    for index in range(12):
        row = _row(9000 + index)
        rows.append(row)
        labels.append(True)
    for index in range(12):
        row = _row(1000 + index, available=0)
        row["spread_bps"] = None
        for window_ms in (1000, 5000, 15000, 60000):
            row[f"w{window_ms}_bid_displacement_bps"] = None
            row[f"w{window_ms}_ask_displacement_bps"] = None
            row[f"w{window_ms}_bid_path_variation_bps"] = None
            row[f"w{window_ms}_ask_path_variation_bps"] = None
            row[f"w{window_ms}_path_variation_asymmetry_bps"] = None
        rows.append(row)
        labels.append(False)

    model = fit_v12_microstructure_density(
        candidate="M3_FULL_CAUSAL_MICROSTRUCTURE",
        rows=rows,
        labels=labels,
    )

    assert len(model.feature_names) == 46
    assert isinstance(score_v12_microstructure_micros(model, rows[-1]), int)


def test_fold_gate_measures_veto_without_creating_new_declarations() -> None:
    labels = (True,) * 100 + (False,) * 100
    baseline = (True,) * 98 + (False,) * 2 + (True,) * 20 + (False,) * 80
    scores = (1,) * 97 + (-1,) + (1,) * 2 + ((-1,) * 10 + (1,) * 10) + (1,) * 80

    fold = evaluate_v12_information_gain_fold(
        fold_index=0,
        labels=labels,
        baseline_declared=baseline,
        microstructure_scores_micros=scores,
    )

    assert fold.baseline_true_confirmation_count == 98
    assert fold.v12_true_confirmation_count == 97
    assert fold.terminal_confirmation_retention_bps >= 9800
    assert fold.absolute_terminal_preservation_bps >= 9500
    assert fold.incremental_false_confirmation_veto_bps == 5000
    assert fold.gate_pass is True


def _fold(index: int, *, veto_bps: int, gate: bool = True) -> V12InformationGainFold:
    baseline_false = 1000
    v12_false = baseline_false - baseline_false * veto_bps // 10_000
    return V12InformationGainFold(
        fold_index=index,
        sample_count=2000,
        terminal_count=800,
        nonterminal_count=1200,
        baseline_true_confirmation_count=780,
        baseline_false_confirmation_count=baseline_false,
        v12_true_confirmation_count=770,
        v12_false_confirmation_count=v12_false,
        terminal_confirmation_retention_bps=9871,
        absolute_terminal_preservation_bps=9625,
        incremental_false_confirmation_veto_bps=veto_bps,
        absolute_false_declaration_reduction_bps=(
            (1200 - v12_false) * 10_000 // 1200
        ),
        gate_pass=gate,
    )


def test_selection_uses_lowest_complexity_eligible_candidate() -> None:
    names = tuple(v12_microstructure_candidate_fields())
    results = []
    for position, name in enumerate(names):
        veto = 400 if position == 0 else 800
        folds = tuple(_fold(index, veto_bps=veto) for index in range(4))
        results.append(
            summarize_v12_candidate_information_gain(
                candidate=name,
                folds=folds,
            )
        )

    assert results[0].pooled_incremental_false_confirmation_veto_bps < (
        MIN_POOLED_INCREMENTAL_FALSE_VETO_BPS
    )
    assert select_v12_information_gain_candidate(results) == names[1]
