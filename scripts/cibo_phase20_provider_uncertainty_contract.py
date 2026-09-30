"""Emit Phase 20A/B provider-uncertainty contract proof vectors.

The vectors are synthetic and exist only to prove ambiguity-set and
partial-identification semantics. They are not provider calibration, historical
economics, policy evidence, or trading authority.
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
from qore.infrastructure.cibo_ce2i_phase20_provider_ambiguity import (
    Phase20AmbiguityEvidenceClass,
    Phase20DecimalInterval,
    Phase20ProviderAmbiguitySet,
    partially_identify_phase20_minimum_seed,
)


def _interval(lower: str, upper: str) -> Phase20DecimalInterval:
    return Phase20DecimalInterval(
        lower=Decimal(lower),
        upper=Decimal(upper),
    )


def _causal() -> CiboReplayCausalTrade:
    return CiboReplayCausalTrade(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="phase20-contract-proof",
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
        source_evidence_ids=("synthetic:phase20-contract-proof",),
        economics_status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
    )


def _ambiguity(
    *,
    ambiguity_id: str,
    liquidity_lower: str = "1",
) -> Phase20ProviderAmbiguitySet:
    return Phase20ProviderAmbiguitySet(
        ambiguity_id=ambiguity_id,
        evidence_id="synthetic-contract-fixture",
        evidence_class=(
            Phase20AmbiguityEvidenceClass.EXPLICIT_COUNTERFACTUAL_BOUND
        ),
        provider_key="synthetic-provider",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        tick_size=_interval("0.1", "0.1"),
        tick_value=_interval("1", "1.2"),
        spread_ticks=_interval("1", "3"),
        commission_per_volume_usd=_interval("1", "2"),
        slippage_reserve_per_volume_usd=_interval("0", "2"),
        margin_per_volume_usd=_interval("10", "20"),
        minimum_volume=_interval("0.01", "0.02"),
        maximum_volume=_interval("10", "20"),
        volume_step=_interval("0.01", "0.02"),
        available_liquidity_volume=_interval(liquidity_lower, "2"),
        execution_delay_ms=_interval("50", "500"),
    )


def _serialize(result: Any) -> dict[str, Any]:
    return {
        "ambiguity_id": result.ambiguity_id,
        "status": result.status.value,
        "minimum_executable_volume": {
            "lower": str(result.minimum_executable_volume_lower),
            "upper": str(result.minimum_executable_volume_upper),
        },
        "stop_loss_per_volume_usd": {
            "lower": str(result.stop_loss_per_volume_usd_lower),
            "upper": str(result.stop_loss_per_volume_usd_upper),
        },
        "minimum_stop_risk_usd": {
            "lower": str(result.minimum_stop_risk_usd_lower),
            "upper": str(result.minimum_stop_risk_usd_upper),
        },
        "minimum_margin_usd": {
            "lower": str(result.minimum_margin_usd_lower),
            "upper": str(result.minimum_margin_usd_upper),
        },
        "liquidity_volume": {
            "guaranteed": str(result.guaranteed_liquidity_volume),
            "possible": str(result.possible_liquidity_volume),
        },
        "execution_delay_ms": {
            "lower": str(result.execution_delay_ms_lower),
            "upper": str(result.execution_delay_ms_upper),
        },
        "reason": result.reason,
    }


def build_report() -> dict[str, Any]:
    causal = _causal()
    cases = (
        (
            "ROBUST_FEASIBLE_PROOF",
            _ambiguity(ambiguity_id="robust-feasible"),
            Decimal("10"),
            Decimal("10"),
        ),
        (
            "ROBUST_INFEASIBLE_PROOF",
            _ambiguity(ambiguity_id="robust-infeasible"),
            Decimal("0.01"),
            Decimal("10"),
        ),
        (
            "PARTIAL_IDENTIFICATION_PROOF",
            _ambiguity(ambiguity_id="partial"),
            Decimal("0.45"),
            Decimal("10"),
        ),
    )
    results = []
    for case_id, ambiguity, risk_headroom, margin_headroom in cases:
        evidence = partially_identify_phase20_minimum_seed(
            causal=causal,
            ambiguity=ambiguity,
            hard_risk_headroom_usd=risk_headroom,
            margin_headroom_usd=margin_headroom,
        )
        results.append(
            {
                "case_id": case_id,
                "risk_headroom_usd": str(risk_headroom),
                "margin_headroom_usd": str(margin_headroom),
                "result": _serialize(evidence),
            }
        )

    return {
        "schema": "qore.cibo.phase20.provider_uncertainty_contract.v1",
        "identity": "CIBO_PHASE20A_B_PROVIDER_UNCERTAINTY_CONTRACT_V1",
        "status": "CONTRACT_GREEN_EMPIRICAL_CALIBRATION_PENDING",
        "fixtures": {
            "synthetic_only": True,
            "provider_calibration_claimed": False,
            "historical_economics_claimed": False,
            "outcome_tuned": False,
            "policy_pass_tuned": False,
        },
        "proof_vectors": results,
        "supported_identification_statuses": [
            "ROBUSTLY_FEASIBLE",
            "ROBUSTLY_INFEASIBLE",
            "PARTIALLY_IDENTIFIED",
        ],
        "uncertainty_dimensions": [
            "tick_size",
            "tick_value",
            "spread_ticks",
            "commission_per_volume_usd",
            "slippage_reserve_per_volume_usd",
            "margin_per_volume_usd",
            "minimum_volume",
            "maximum_volume",
            "volume_step",
            "available_liquidity_volume",
            "execution_delay_ms",
        ],
        "governance": {
            "historical_exact_claimed": False,
            "allocation_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
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
