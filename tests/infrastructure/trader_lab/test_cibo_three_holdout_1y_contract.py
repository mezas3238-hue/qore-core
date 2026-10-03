from __future__ import annotations

from copy import deepcopy

from qore.infrastructure.trader_lab.cibo_three_holdout_1y_contract import (
    GROUP_WINDOWS,
    REQUIRED_TRADERS,
    evaluate_candidate,
    evaluate_three_groups,
)


def _candidate(fingerprint: str, *, positive: bool = True) -> dict[str, object]:
    sign = "1" if positive else "-1"
    return {
        "configuration_fingerprint": fingerprint,
        "measurements": {
            "all_7_traders_participate": True,
            "timeframes": ["H4", "H1", "M15", "M5", "M1"],
            "core": {
                "net_pnl_usd": sign,
                "profit_factor": "1.5" if positive else "0.9",
                "expectancy_usd": sign,
            },
            "compound": {"incremental_pnl_usd": sign},
            "compound_portfolio": {
                "incremental_pnl_usd": sign,
                "value_add_vs_compound_usd": sign,
            },
            "final_ending_capital_usd": "61" if positive else "59",
            "chronological_folds_all_positive": positive,
            "monte_carlo": {
                "median_pnl_usd": sign,
                "p05_pnl_usd": sign,
            },
            "stress": {
                "provider_cost_x2_pnl_usd": sign,
                "remove_best_3_pnl_usd": sign,
            },
            "protected_capital_breaches": 0,
            "all_required_cibo_functions_accounted_for": True,
            "qore_risk_sovereign": True,
        },
    }


def _group(group_id: str, start: str, end: str) -> dict[str, object]:
    return {
        "schema": "qore.cibo.trader-lab.1y-group-result.v1",
        "group_id": group_id,
        "start_at": start,
        "end_exclusive_at": end,
        "traders": list(REQUIRED_TRADERS),
        "adaptive_research_only": True,
        "candidates": [
            _candidate("cfg-a"),
            _candidate("cfg-b"),
            _candidate("cfg-c"),
            _candidate("cfg-bad", positive=False),
        ],
    }


def test_three_identical_full_passes_stop_all_three_holdouts() -> None:
    payloads = tuple(_group(*window) for window in GROUP_WINDOWS)
    result = evaluate_three_groups(payloads)
    assert result["status"] == "STOP_THREE_CROSS_HOLDOUT_FULL_PASS"
    assert result["cross_holdout_full_pass_count"] == 3
    assert result["cross_holdout_full_pass_fingerprints"] == [
        "cfg-a",
        "cfg-b",
        "cfg-c",
    ]


def test_positive_candidates_must_be_identical_across_groups() -> None:
    payloads = [_group(*window) for window in GROUP_WINDOWS]
    payloads[2] = deepcopy(payloads[2])
    payloads[2]["candidates"][2]["configuration_fingerprint"] = "cfg-d"
    result = evaluate_three_groups(tuple(payloads))
    assert result["status"] == "CONTINUE_SEARCH"
    assert result["cross_holdout_full_pass_count"] == 2


def test_one_negative_gate_fails_candidate() -> None:
    candidate = _candidate("cfg")
    candidate["measurements"]["monte_carlo"]["p05_pnl_usd"] = "-0.01"
    result = evaluate_candidate(candidate)
    assert result.passed is False
    assert "MC_P05" in result.failed_gates
