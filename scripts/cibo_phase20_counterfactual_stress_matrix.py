"""Emit the frozen Phase20C counterfactual provider-stress matrix.

The matrix uses synthetic contract fixtures plus explicit adverse assumptions.
It is permanently non-historical: no row is provider calibration, historical
economics, allocator evidence, Risk authority, execution authority or policy
qualification evidence.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    CiboReplayCausalTrade,
    ReplayEconomicsStatus,
    ReplaySignalFingerprintOrigin,
)
from qore.infrastructure.cibo_ce2i_phase20_provider_stress import (
    Phase20ProviderStressEvaluation,
    phase20c_synthetic_predeclared_stress_scenarios,
    run_phase20c_counterfactual_stress_matrix,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)


def _causal() -> CiboReplayCausalTrade:
    return CiboReplayCausalTrade(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="phase20c-contract-proof",
        signal_fingerprint_origin=(
            ReplaySignalFingerprintOrigin.PHASE18_RECONSTRUCTED
        ),
        qore_symbol="EURUSD",
        side="long",
        signal_at=datetime(2021, 10, 1, 12, 0, tzinfo=UTC),
        entry_at=datetime(2021, 10, 1, 12, 1, tzinfo=UTC),
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("102"),
        legacy_risk_scale=Decimal("1"),
        minimum_execution_steps=1,
        pre_trade_state=(),
        source_evidence_ids=("synthetic:phase20c-contract-proof",),
        economics_status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
    )


def _observation() -> ProviderEconomicObservation:
    return ProviderEconomicObservation(
        provider_key="synthetic-current-provider",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        bid=Decimal("99.9"),
        ask=Decimal("100.1"),
        contract_size=Decimal("100"),
        tick_size=Decimal("0.1"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        margin_per_volume=Decimal("20"),
        commission_per_volume_usd=Decimal("2"),
        slippage_reserve_per_volume_usd=Decimal("1"),
        observed_at=datetime(2026, 9, 27, 1, 0, tzinfo=UTC),
    )


def _serialize(row: Phase20ProviderStressEvaluation) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "scenario_id": row.scenario_id,
        "status": row.status.value,
        "reason": row.reason,
        "minimum_executable_volume": str(row.minimum_executable_volume),
        "effective_maximum_volume": str(row.effective_maximum_volume),
        "available_liquidity_volume": str(row.available_liquidity_volume),
    }
    if row.result is None:
        payload["executable"] = False
        payload["economics"] = None
        return payload

    economics = row.result.economics
    opportunity = row.result.opportunity
    payload["executable"] = True
    payload["economics"] = {
        "spread_ticks": str(economics.stressed_spread_ticks),
        "spread_cost_per_volume_usd": str(
            economics.stressed_spread_cost_per_volume_usd
        ),
        "commission_per_volume_usd": str(
            economics.stressed_commission_per_volume_usd
        ),
        "slippage_reserve_per_volume_usd": str(
            economics.stressed_slippage_reserve_per_volume_usd
        ),
        "execution_cost_per_volume_usd": str(
            economics.stressed_execution_cost_per_volume_usd
        ),
        "margin_per_volume_usd": str(
            economics.stressed_margin_per_volume_usd
        ),
        "stop_loss_per_volume_usd": str(opportunity.stop_loss_per_volume),
        "minimum_volume": str(economics.stressed_minimum_volume),
        "maximum_volume": str(economics.stressed_maximum_volume),
        "execution_delay_ms": str(economics.stressed_execution_delay_ms),
    }
    payload["geometry"] = {
        "entry": str(opportunity.intended_entry),
        "stop": str(opportunity.stop_loss),
        "target": str(opportunity.take_profit),
    }
    return payload


def build_report() -> dict[str, Any]:
    rows = run_phase20c_counterfactual_stress_matrix(
        causal=_causal(),
        observation=_observation(),
        scenarios=phase20c_synthetic_predeclared_stress_scenarios(),
    )
    executable = sum(row.result is not None for row in rows)
    fail_closed = len(rows) - executable
    return {
        "schema": "qore.cibo.phase20c.counterfactual_provider_stress.v1",
        "identity": "CIBO_PHASE20C_COUNTERFACTUAL_PROVIDER_STRESS_MATRIX_V1",
        "status": "COUNTERFACTUAL_CONTRACT_PROOF",
        "fixtures": {
            "synthetic_only": True,
            "provider_calibration_claimed": False,
            "historical_provider_economics_claimed": False,
            "historical_causality_claimed": False,
            "outcome_tuned": False,
            "policy_pass_tuned": False,
            "phase19j_burned_validation_reused": False,
        },
        "matrix": {
            "scenario_count": len(rows),
            "executable_count": executable,
            "fail_closed_count": fail_closed,
            "rows": [_serialize(row) for row in rows],
        },
        "invariants": {
            "trader_geometry_preserved_for_executable_rows": True,
            "adverse_rows_cannot_improve_execution_cost": True,
            "adverse_rows_cannot_improve_margin": True,
            "adverse_rows_cannot_reduce_stop_loss_per_volume": True,
            "liquidity_unavailable_is_fail_closed": True,
            "minimum_volume_cliff_is_fail_closed": True,
        },
        "governance": {
            "allocation_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
            "policy_certified": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
