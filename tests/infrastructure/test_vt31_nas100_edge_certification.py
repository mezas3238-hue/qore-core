from __future__ import annotations

from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_nas100_edge_certification import (
    IDENTITY,
    R_RUNTIME_ALLOWED,
    SIZING_FOR_CERTIFICATION_FORBIDDEN,
    VOLUME_AGNOSTIC,
    build_edge_only_report,
    normalized_trade_rows,
    validate_max_intelligence_governance,
    validate_pure_edge_runtime_governance,
    winner_preservation,
)


def _pure_runtime_governance() -> dict[str, object]:
    return {
        "r_used_for_admission": False,
        "r_used_for_entry": False,
        "r_used_for_invalidation": False,
        "r_used_for_stop_movement": False,
        "r_used_for_breakeven": False,
        "r_used_for_target": False,
        "r_used_for_exit": False,
        "r_used_for_trailing": False,
        "r_used_for_partials": False,
        "r_used_for_volume": False,
        "sizing_used": False,
        "leverage_used": False,
        "compounding_used": False,
        "capital_weighting_used": False,
        "volume_agnostic": True,
        "r_role": "runtime_strategy_and_evaluation_allowed",
    }


def _max_intelligence_governance() -> dict[str, object]:
    return {
        "maximum_intelligence_required": True,
        "max_intelligence_ready": True,
        "applicable_domains_all_consulted": True,
        "unwired_domains": [],
        "bypassed_available_domains": [],
    }


def _rows() -> list[dict[str, object]]:
    return [
        {
            "trade_id": "t1",
            "signal_at": "2024-01-02T15:00:00+00:00",
            "era": "E1",
            "fold": "F1",
            "r_multiple": "2.0",
            "capital_weighted_net_r": "0.02",
            "requested_risk_r": "0.01",
            "global_risk_scalar": "0.10",
            "volume": "0.01",
            "leverage": "1",
        },
        {
            "trade_id": "t2",
            "signal_at": "2024-02-02T15:00:00+00:00",
            "era": "E1",
            "fold": "F1",
            "r_multiple": "-1.0",
            "capital_weighted_net_r": "-100",
            "requested_risk_r": "100",
            "global_risk_scalar": "9",
            "volume": "50",
            "leverage": "100",
        },
        {
            "trade_id": "t3",
            "signal_at": "2025-01-02T15:00:00+00:00",
            "era": "E2",
            "fold": "F2",
            "r_multiple": "3.0",
            "capital_weighted_net_r": "0.0003",
            "requested_risk_r": "0.0001",
            "global_risk_scalar": "0.01",
            "volume": "0.01",
            "leverage": "1",
        },
        {
            "trade_id": "t4",
            "signal_at": "2025-02-02T15:00:00+00:00",
            "era": "E2",
            "fold": "F2",
            "r_multiple": "-1.0",
            "capital_weighted_net_r": "-999",
            "requested_risk_r": "999",
            "global_risk_scalar": "99",
            "volume": "99",
            "leverage": "500",
        },
    ]


def test_normalization_uses_structural_r_only_and_audits_capital_fields() -> None:
    rows = normalized_trade_rows(_rows(), friction_r=Decimal("0.05"))

    assert [row["normalized_trade_r"] for row in rows] == [
        "1.95",
        "-1.05",
        "2.95",
        "-1.05",
    ]
    assert rows[0]["ignored_capital_fields"]["volume"] == "0.01"
    assert "capital_weighted_net_r" not in rows[0]
    assert "requested_risk_r" not in rows[0]
    assert "volume" not in rows[0]


def test_edge_metrics_are_invariant_to_sizing_leverage_and_volume() -> None:
    original = _rows()
    mutated = [dict(row) for row in original]
    for index, row in enumerate(mutated, start=1):
        row["capital_weighted_net_r"] = str(index * -1000000)
        row["requested_risk_r"] = str(index * 500000)
        row["global_risk_scalar"] = str(index * 777)
        row["volume"] = str(index * 123)
        row["leverage"] = str(index * 999)

    left = build_edge_only_report(original, monte_carlo_paths=200)
    right = build_edge_only_report(mutated, monte_carlo_paths=200)

    assert left["metrics"] == right["metrics"]
    assert left["temporal_metrics"] == right["temporal_metrics"]
    assert left["monte_carlo"] == right["monte_carlo"]
    assert left["cost_stress"] == right["cost_stress"]
    assert left["gates"] == right["gates"]


def test_capital_weighted_result_cannot_replace_structural_r_multiple() -> None:
    with pytest.raises(
        ValueError,
        match="structural r_multiple",
    ):
        normalized_trade_rows(
            [
                {
                    "trade_id": "capital-only",
                    "capital_weighted_net_r": "99",
                    "requested_risk_r": "10",
                }
            ]
        )


def test_volume_is_provider_metadata_not_trader_edge_input() -> None:
    report = build_edge_only_report(_rows(), monte_carlo_paths=100)

    assert VOLUME_AGNOSTIC is True
    assert report["volume_agnostic"] is True
    assert report["volume_constraints_authority"] == "provider-adapter-only"
    assert "minimum_compatible_volume" not in report
    assert report["volume_used_for_edge_metrics"] is False
    assert report["capital_fields_used_for_edge_metrics"] == []


def test_winner_preservation_is_measured_by_trade_identity_and_r() -> None:
    baseline = normalized_trade_rows(
        [
            {"trade_id": "a", "r_multiple": "2"},
            {"trade_id": "b", "r_multiple": "4"},
            {"trade_id": "c", "r_multiple": "-1"},
        ]
    )
    managed = normalized_trade_rows(
        [
            {"trade_id": "a", "r_multiple": "1.5"},
            {"trade_id": "b", "r_multiple": "-0.2"},
            {"trade_id": "c", "r_multiple": "-0.5"},
        ]
    )

    result = winner_preservation(baseline, managed)

    assert result["baseline_winner_count"] == 2
    assert result["retained_winner_count"] == 1
    assert result["winner_count_preservation"] == "0.5"
    assert result["winner_r_preservation"] == "0.25"


def test_temporal_report_is_by_year_era_and_fold() -> None:
    report = build_edge_only_report(_rows(), monte_carlo_paths=100)
    temporal = report["temporal_metrics"]

    assert set(temporal["year"]) == {"2024", "2025"}
    assert set(temporal["era"]) == {"E1", "E2"}
    assert set(temporal["fold"]) == {"F1", "F2"}


def test_cost_stress_is_applied_per_trade_in_normalized_r() -> None:
    report = build_edge_only_report(_rows(), monte_carlo_paths=100)

    pf_zero = Decimal(report["cost_stress"]["0"]["profit_factor"])
    pf_severe = Decimal(report["cost_stress"]["0.10"]["profit_factor"])

    assert pf_severe < pf_zero


def test_monte_carlo_is_deterministic_and_edge_only() -> None:
    first = build_edge_only_report(_rows(), monte_carlo_paths=250)
    second = build_edge_only_report(_rows(), monte_carlo_paths=250)

    assert first["monte_carlo"] == second["monte_carlo"]


def test_development_module_cannot_claim_certification_or_open_holdout() -> None:
    report = build_edge_only_report(_rows(), monte_carlo_paths=100)

    assert report["identity"] == IDENTITY
    assert report["candidate_frozen"] is False
    assert report["opens_new_holdout"] is False
    assert report["candidate_certified"] is False
    assert report["live_authorized"] is False
    assert report["real_capital_authorized"] is False
    assert report["production_authorized"] is False


def test_final_sharpe_sortino_gates_remain_unbound_until_convention_freeze() -> None:
    report = build_edge_only_report(_rows(), monte_carlo_paths=100)

    assert report["gates"]["sharpe"] is None
    assert report["gates"]["sortino"] is None
    assert report["risk_adjusted_certification_binding_complete"] is False
    assert report["ready_for_candidate_freeze"] is False
    assert (
        report["risk_adjusted_metric_binding"]["sharpe"]["status"]
        == "UNBOUND_FINAL_CERTIFICATION_CONVENTION"
    )
    assert (
        report["risk_adjusted_metric_binding"]["sortino"]["status"]
        == "UNBOUND_FINAL_CERTIFICATION_CONVENTION"
    )


def test_empty_sample_cannot_pass_profit_factor_gates() -> None:
    report = build_edge_only_report([], monte_carlo_paths=100)

    assert report["metrics"]["trade_count"] == 0
    assert report["gates"]["combined_pf"] is False
    assert report["gates"]["severe_cost_pf"] is False
    assert report["passes_available_development_gates"] is False


def test_positive_no_loss_sample_has_infinite_pf_semantics_without_capital() -> None:
    report = build_edge_only_report(
        [
            {"trade_id": "a", "r_multiple": "1.5"},
            {"trade_id": "b", "r_multiple": "0.8"},
        ],
        monte_carlo_paths=100,
    )

    assert report["metrics"]["profit_factor"] is None
    assert report["gates"]["combined_pf"] is True
    assert report["gates"]["severe_cost_pf"] is True
    assert report["certification_basis"] == "entries-profits-edge-only"
    assert report["equal_trade_weight"] is True
    assert report["sizing_authority"] is False
    assert report["leverage_authority"] is False
    assert report["compounding_authority"] is False
    assert report["portfolio_weighting_authority"] is False



def test_runtime_governance_allows_r_driven_breakeven() -> None:
    governance = _pure_runtime_governance()
    governance["r_used_for_breakeven"] = True
    governance["r_used_for_target"] = True
    governance["r_used_for_trailing"] = True

    result = validate_pure_edge_runtime_governance(governance)

    assert R_RUNTIME_ALLOWED is True
    assert SIZING_FOR_CERTIFICATION_FORBIDDEN is True
    assert result["verified"] is True
    assert result["violations"] == []


def test_runtime_governance_rejects_r_driven_volume_sizing() -> None:
    governance = _pure_runtime_governance()
    governance["r_used_for_volume"] = True

    result = validate_pure_edge_runtime_governance(governance)

    assert result["verified"] is False
    assert "r_used_for_volume" in result["violations"]


def test_runtime_governance_accepts_market_native_volume_agnostic_execution() -> None:
    result = validate_pure_edge_runtime_governance(
        _pure_runtime_governance()
    )

    assert result["verified"] is True
    assert result["violations"] == []


def test_report_fails_closed_when_runtime_purity_is_unproven() -> None:
    report = build_edge_only_report(_rows(), monte_carlo_paths=100)

    assert report["r_role"] == "runtime_strategy_and_evaluation_allowed"
    assert report["r_runtime_allowed"] is True
    assert report["r_runtime_execution_authority"] is True
    assert report["runtime_purity"]["verified"] is False
    assert report["runtime_purity_gate"] is False
    assert report["passes_available_development_gates"] is False
    assert report["runtime_purity_required_for_freeze"] is True


def test_report_binds_verified_pure_edge_runtime_governance() -> None:
    report = build_edge_only_report(
        _rows(),
        monte_carlo_paths=100,
        runtime_governance=_pure_runtime_governance(),
    )

    assert report["runtime_purity"]["verified"] is True
    assert report["runtime_purity"]["violations"] == []
    assert report["runtime_purity_gate"] is True
    assert report["passes_available_development_gates"] == (
        report["passes_economic_development_gates"]
    )


def test_maximum_intelligence_gate_fails_when_any_domain_is_unwired() -> None:
    governance = _max_intelligence_governance()
    governance["max_intelligence_ready"] = False
    governance["unwired_domains"] = ["M15_CONTEXT"]

    result = validate_max_intelligence_governance(governance)

    assert result["verified"] is False
    assert "max_intelligence_ready" in result["blockers"]
    assert "unwired_domains" in result["blockers"]


def test_maximum_intelligence_gate_accepts_complete_cognition() -> None:
    result = validate_max_intelligence_governance(
        _max_intelligence_governance()
    )

    assert result["verified"] is True
    assert result["blockers"] == []
    assert result["maximum_intelligence_required_for_freeze"] is True


def test_edge_report_exposes_maximum_intelligence_freeze_gate() -> None:
    incomplete = build_edge_only_report(
        _rows(),
        monte_carlo_paths=100,
        runtime_governance=_pure_runtime_governance(),
    )
    complete = build_edge_only_report(
        _rows(),
        monte_carlo_paths=100,
        runtime_governance=_pure_runtime_governance(),
        intelligence_governance=_max_intelligence_governance(),
    )

    assert incomplete["maximum_intelligence_gate"] is False
    assert (
        incomplete["maximum_intelligence"]["blockers"]
        == ["intelligence_governance_missing"]
    )
    assert complete["maximum_intelligence_gate"] is True
    assert complete["maximum_intelligence"]["verified"] is True
    assert complete["maximum_intelligence_required_for_freeze"] is True
