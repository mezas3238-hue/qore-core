from __future__ import annotations

from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_nas100_edge_certification import (
    IDENTITY,
    MINIMUM_COMPATIBLE_VOLUME,
    build_edge_only_report,
    normalized_trade_rows,
    winner_preservation,
)


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


def test_universal_001_is_capability_metadata_not_edge_input() -> None:
    report = build_edge_only_report(_rows(), monte_carlo_paths=100)

    assert MINIMUM_COMPATIBLE_VOLUME == Decimal("0.01")
    assert report["minimum_compatible_volume"] == "0.01"
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
