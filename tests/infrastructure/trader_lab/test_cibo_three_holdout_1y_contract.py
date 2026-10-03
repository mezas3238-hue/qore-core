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
        "configuration_scope": "CIBO_ONLY",
        "trader_parameters_changed": False,
        "trader_profitability_used_for_gate": True,
        "measurements": {
            "all_7_traders_participate": True,
            "per_trader_under_cibo": {
                trader: {
                    "settled_count": 5 if positive else 1,
                    "final_pnl_usd": sign,
                    "profit_factor": "1.5" if positive else "0.9",
                    "expectancy_usd": sign,
                }
                for trader in REQUIRED_TRADERS
            },
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
            "cibo_function_behavior": {
                "cognitive_faculties": [
                    f"CF{i:02d}" for i in range(1, 20)
                ],
                "ce2i_tools": [f"T{i:02d}" for i in range(1, 21)],
                "capital_science": [f"GEN-C{i}" for i in range(1, 15)],
                "per_function_observability_complete": True,
            },
            "trader_profitability_used_for_gate": True,
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
        "execution_topology": "SINGLE_INTEGRATED_7_TRADER_PORTFOLIO",
        "shared_cibo_state": True,
        "shared_qore_risk_state": True,
        "shared_initial_capital_usd": "60",
        "per_trader_results_source_only": True,
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


def test_per_trader_only_group_is_rejected() -> None:
    payloads = [_group(*window) for window in GROUP_WINDOWS]
    payloads[0] = deepcopy(payloads[0])
    payloads[0]["execution_topology"] = "SEPARATE_TRADER_REPLAYS"
    try:
        evaluate_three_groups(tuple(payloads))
    except ValueError as error:
        assert "integrated 7-Trader portfolio" in str(error)
    else:
        raise AssertionError("separate Trader replays must never satisfy group sensor")


def test_all_seven_trader_profitability_must_gate_cibo_candidate() -> None:
    candidate = _candidate("cfg")
    candidate["trader_profitability_used_for_gate"] = False
    try:
        evaluate_candidate(candidate)
    except ValueError as error:
        assert "all-seven Trader profitability" in str(error)
    else:
        raise AssertionError("all-seven Trader profitability must gate CIBO research")


def test_one_nonpositive_trader_rejects_cibo_candidate() -> None:
    candidate = _candidate("cfg")
    candidate["measurements"]["per_trader_under_cibo"]["R43_GBPUSD"][
        "final_pnl_usd"
    ] = "-0.01"
    result = evaluate_candidate(candidate)
    assert result.passed is False
    assert "R43_GBPUSD:PNL" in result.failed_gates


def test_zero_settlement_trader_rejects_cibo_candidate() -> None:
    candidate = _candidate("cfg")
    candidate["measurements"]["per_trader_under_cibo"]["VT31_NAS100"][
        "settled_count"
    ] = 0
    result = evaluate_candidate(candidate)
    assert result.passed is False
    assert "VT31_NAS100:NO_SETTLEMENT" in result.failed_gates


def test_candidate_scope_must_be_cibo_only() -> None:
    candidate = _candidate("cfg")
    candidate["configuration_scope"] = "TRADER_AND_CIBO"
    try:
        evaluate_candidate(candidate)
    except ValueError as error:
        assert "CIBO-only" in str(error)
    else:
        raise AssertionError("only CIBO configurations may enter adaptive search")
