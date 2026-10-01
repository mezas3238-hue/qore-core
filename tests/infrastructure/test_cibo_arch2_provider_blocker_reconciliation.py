from __future__ import annotations

from qore.infrastructure.cibo_arch2_provider_blocker_reconciliation import (
    PROVIDER_ECONOMICS_LEDGER_BLOCKERS,
    T11_LEDGER_BLOCKERS,
    reconcile_current_empirical_provider_plane,
)


def test_current_empirical_provider_plane_reconciles_only_proven_blockers() -> None:
    rows = {
        row.workstream_id: row
        for row in reconcile_current_empirical_provider_plane()
    }

    t11 = rows["T11"]
    assert t11.observed_ledger_blockers == T11_LEDGER_BLOCKERS
    assert t11.resolved_blockers == (
        "REAL_EXECUTION_POPULATION_REQUIRED",
        "EMPIRICAL_SLIPPAGE_CALIBRATION_REQUIRED",
    )
    assert t11.remaining_blockers == (
        "REAL_CALIBRATED_FRESH_OOS_GROSS_EDGE_MODEL_REQUIRED",
        "REAL_PROVIDER_BOUND_MARKET_IMPACT_MODEL_REQUIRED",
    )
    assert t11.terminal_disposition_assigned is False
    assert t11.productive_authority is False

    provider = rows["PROVIDER_ECONOMICS"]
    assert provider.observed_ledger_blockers == PROVIDER_ECONOMICS_LEDGER_BLOCKERS
    assert provider.resolved_blockers == (
        "REAL_FORWARD_SLIPPAGE_COST_CALIBRATION_REQUIRED",
    )
    assert provider.remaining_blockers == (
        "HISTORICAL_2017_PROVIDER_USD_ECONOMICS_UNAVAILABLE",
    )
    assert provider.terminal_disposition_assigned is False
    assert provider.productive_authority is False

    for row in rows.values():
        assert any(
            ref.startswith("github-actions://36927602692/")
            for ref in row.evidence_refs
        )
        assert any(
            "CURRENT_CTRADER_DEMO_ONLY" in ref
            for ref in row.evidence_refs
        )
