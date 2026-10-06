"""Emit Phase20I forecastless receding-horizon optionality evidence."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_phase20_mpc import (
    Phase20MpcCapacityPlan,
    Phase20MpcKnownOption,
    plan_phase20i_receding_horizon_capacity,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboRegimePosture


def _option(
    opportunity_id: str,
    step: int,
    risk: str,
    margin: str,
) -> Phase20MpcKnownOption:
    return Phase20MpcKnownOption(
        opportunity_id=opportunity_id,
        decision_step=step,
        minimum_stop_risk_usd=Decimal(risk),
        minimum_margin_usd=Decimal(margin),
    )


def _row(scenario_id: str, plan: Phase20MpcCapacityPlan) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "current_step": plan.current_step,
        "horizon_steps": plan.horizon_steps,
        "horizon_end_step": plan.horizon_end_step,
        "posture": plan.posture.value,
        "considered_option_ids": list(plan.considered_option_ids),
        "representative_option_ids": list(plan.representative_option_ids),
        "reserve_stop_risk_usd": str(plan.reserve_stop_risk_usd),
        "reserve_margin_usd": str(plan.reserve_margin_usd),
        "deployable_stop_risk_usd": str(
            plan.deployable_stop_risk_usd
        ),
        "deployable_margin_usd": str(plan.deployable_margin_usd),
        "horizon_fully_coverable": plan.horizon_fully_coverable,
        "reason": plan.reason,
    }


def build_report() -> dict[str, Any]:
    options = (
        _option("step1", 1, "4", "20"),
        _option("step2", 2, "6", "30"),
        _option("step4", 4, "15", "90"),
    )
    first = plan_phase20i_receding_horizon_capacity(
        current_step=0,
        horizon_steps=2,
        posture=CiboRegimePosture.STABLE,
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("100"),
        known_options=options,
    )
    replanned = plan_phase20i_receding_horizon_capacity(
        current_step=2,
        horizon_steps=2,
        posture=CiboRegimePosture.STABLE,
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("100"),
        known_options=options,
    )
    recovery = plan_phase20i_receding_horizon_capacity(
        current_step=0,
        horizon_steps=3,
        posture=CiboRegimePosture.RECOVERY,
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        known_options=options,
    )
    insufficient = plan_phase20i_receding_horizon_capacity(
        current_step=0,
        horizon_steps=2,
        posture=CiboRegimePosture.STABLE,
        hard_risk_headroom_usd=Decimal("5"),
        margin_headroom_usd=Decimal("20"),
        known_options=(_option("too-large", 1, "10", "40"),),
    )
    return {
        "schema": "qore.cibo.phase20i.forecastless_mpc_contract.v1",
        "identity": "CIBO_PHASE20I_FORECASTLESS_MPC_V1",
        "status": "SYNTHETIC_RESEARCH_CONTRACT",
        "plans": [
            _row("INITIAL_HORIZON", first),
            _row("RECEDING_REPLAN", replanned),
            _row("RECOVERY", recovery),
            _row("INSUFFICIENT_HEADROOM", insufficient),
        ],
        "governance": {
            "forecast_model_used": False,
            "outcome_aware": False,
            "validation_tuned": False,
            "phase19j_burned_validation_reused": False,
            "historical_provider_economics_claimed": False,
            "policy_certified": False,
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
