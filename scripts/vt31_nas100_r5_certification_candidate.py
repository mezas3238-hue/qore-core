"""Frozen VT31 NAS100 R5 certification candidate.

Identity:
    VT31_NAS100_R5

This module exposes exactly one economic policy.  It is a thin governed
selection layer over the already validated causal implementation; it does not
scan alternatives on certification evidence.

Frozen policy:
- base architecture: WAIT_1025_B060
- first-position pre-scalar risk: CORE 1.00R, SECONDARY 0.05R, SCOUT 0.02R
- alternate monthly pre-scalar budget: 0.60R
- one genuine structural rearm maximum per day
- rearm quality: causal pre-entry quality score
- rearm management: SCORE_PROTECT
- rearm pre-scalar risk: HIGH 0.10R / MID 0.05R / LOW 0.02R
- adaptive rearm budget: ACTIVITY_L
  prior-month base count <=8: 0.30R
  prior-month base count <=10: 0.17R
  otherwise: 0.04R
- global risk scalar after selection: 0.60
- no fold identity, future bar or terminal-PnL oracle is permitted.

Research/certification only.  No live or production authority is granted here.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import cast

# Lock the imported research engine to the exact frozen frontier subset.
os.environ["QORE_DD6_FRONTIER_ONLY"] = "1"
os.environ.pop("QORE_EVAL_START_DATE", None)
os.environ.pop("QORE_EVAL_END_EXCLUSIVE_DATE", None)
os.environ["QORE_INCLUDE_TRADE_ROWS"] = "1"

import vt31_nas100_causal_hybrid_rearm_v1 as engine  # noqa: E402

from qore.infrastructure.traders.vt31_nas100_cibo_market_memory import (  # noqa: E402
    cibo_market_memory_fingerprint,
)
from qore.infrastructure.traders.vt31_nas100_cognitive_memory import (  # noqa: E402
    memory_fingerprint,
    validate_memory,
)
from qore.infrastructure.traders.vt31_nas100_strategy_identity_memory import (  # noqa: E402
    strategy_identity_fingerprint,
)
from qore.infrastructure.traders.vt31_nas100_trader_experience_memory import (  # noqa: E402
    trader_experience_fingerprint,
)

SCHEMA = "qore.vt31.nas100.r5.certification_candidate.v1"
CANDIDATE_ID = "VT31_NAS100_R5"
MARKET = "NAS100"
REFERENCE_VARIANT = (
    "REARM_ADAPTIVE_ACTIVITY_L_SCORE_PROTECT_RISK_SCALAR_060"
)
DEVELOPMENT_5Y_RUN_ID = 35358805202
DEVELOPMENT_5Y_ARTIFACT_ID = 10554091357
DEVELOPMENT_5Y_ARTIFACT_ZIP_SHA256 = (
    "38359f743b86a23be1d8294d9f4e03d2613261bd7b6cff63c4ef54ffc16ec0b3"
)
DEVELOPMENT_5Y_WINDOW = ("2017-07-01", "2022-07-01")

# Frozen unseen certification interval selected prospectively from the first
# complete Monday after all VT31/CIBO consumed evidence ends (2022-07-15).
FINAL_HOLDOUT_ID = "VT31_NAS100_R5_FINAL_HOLDOUT_001"
FINAL_HOLDOUT_START = "2022-07-18T00:00:00+00:00"
FINAL_HOLDOUT_END_EXCLUSIVE = "2023-07-18T00:00:00+00:00"

FINAL_CERTIFICATION_GATES = {
    "terminal_sample_min": 125,
    "profit_factor_min": "1.50",
    "mean_r_min_exclusive": "0",
    "total_r_min_exclusive": "0",
    "observed_max_drawdown_r_max": "6.00",
    "mc_positive_terminal_probability_min": "0.90",
    "mc_p95_max_drawdown_r_max": "15.00",
}


def contract_payload() -> dict[str, object]:
    validate_memory()
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "market": MARKET,
        "methodology": "VT31-AM-SILVER-BULLET-INTELLIGENT-HYBRID-REARM",
        "timezone": "America/New_York",
        "source_granularity": "closed-M1",
        "base_variant": "WAIT_1025_B060",
        "reference_window": "09:00-10:00-NY",
        "source_window": "10:00-11:00-NY",
        "wait_release_minute_ny": 10 * 60 + 25,
        "first_position": {
            "core_pre_scalar_risk_r": "1.00",
            "secondary_pre_scalar_risk_r": "0.05",
            "scout_pre_scalar_risk_r": "0.02",
            "monthly_alternate_pre_scalar_budget_r": "0.60",
        },
        "rearm": {
            "maximum_per_day": 1,
            "requires_new_raid": True,
            "requires_new_confirmation": True,
            "requires_new_decision": True,
            "must_follow_previous_terminal_exit": True,
            "quality_score": "causal-pre-entry-v1",
            "management": "SCORE_PROTECT",
            "risk_map_pre_scalar_r": {
                "HIGH": "0.10",
                "MID": "0.05",
                "LOW": "0.02",
            },
            "activity_profile": {
                "name": "ACTIVITY_L",
                "sparse_max_prior_month_base_count": 8,
                "balanced_max_prior_month_base_count": 10,
                "sparse_pre_scalar_budget_r": "0.30",
                "balanced_pre_scalar_budget_r": "0.17",
                "dense_pre_scalar_budget_r": "0.04",
            },
        },
        "global_risk_scalar": "0.60",
        "selection_order": (
            "base/alternate selection -> structural rearm selection -> "
            "global risk scalar"
        ),
        "source_stop": "source-methodological-swing-extreme-no-buffer",
        "source_target_and_lifecycle": (
            "identical-to-causal-hybrid-WAIT_1025_B060-and-SCORE_PROTECT"
        ),
        "memory": {
            "strategy_identity_fingerprint": strategy_identity_fingerprint(),
            "cibo_market_memory_fingerprint": cibo_market_memory_fingerprint(),
            "trader_experience_memory_fingerprint": (
                trader_experience_fingerprint()
            ),
            "cognitive_bundle_fingerprint": memory_fingerprint(),
            "runtime_mutation": False,
        },
        "causal_firewall": {
            "future_bars": False,
            "terminal_pnl_oracle": False,
            "fold_identity_rule": False,
            "date_level_cibo_outcome_lookup": False,
            "risk_round_up_to_broker_minimum": False,
        },
        "development_binding": {
            "five_year_run_id": DEVELOPMENT_5Y_RUN_ID,
            "five_year_artifact_id": DEVELOPMENT_5Y_ARTIFACT_ID,
            "five_year_artifact_zip_sha256": DEVELOPMENT_5Y_ARTIFACT_ZIP_SHA256,
            "five_year_window": list(DEVELOPMENT_5Y_WINDOW),
            "five_year_trades": 806,
            "five_year_profit_factor": "2.147751559984496546692193737",
            "five_year_max_drawdown_r": "5.76313027394994178900211746",
            "five_year_total_r": "53.97656884532812305172257968",
            "five_year_all_annual_blocks_positive": True,
        },
        "final_holdout": {
            "id": FINAL_HOLDOUT_ID,
            "start_at": FINAL_HOLDOUT_START,
            "end_exclusive": FINAL_HOLDOUT_END_EXCLUSIVE,
            "selected_before_open": True,
            "overlaps_consumed_cibo_or_folds": False,
            "retuning_after_open_on_same_interval": False,
            "gates": FINAL_CERTIFICATION_GATES,
        },
        "candidate_frozen": True,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def contract_fingerprint() -> str:
    encoded = json.dumps(
        contract_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def replay(evidence_path: Path) -> dict[str, object]:
    report = engine.replay(
        evidence_path,
        partition="frozen_candidate",
    )
    variants = cast(dict[str, dict[str, object]], report["variants"])
    if REFERENCE_VARIANT not in variants:
        raise ValueError("frozen VT31 NAS100 R5 variant missing")
    selected = variants[REFERENCE_VARIANT]
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "contract_fingerprint": contract_fingerprint(),
        "reference_variant": REFERENCE_VARIANT,
        "result": selected,
        "engine_governance": report["governance"],
        "candidate_frozen": True,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        print(
            json.dumps(
                {
                    "candidate_id": CANDIDATE_ID,
                    "contract_fingerprint": contract_fingerprint(),
                    "reference_variant": REFERENCE_VARIANT,
                    "final_holdout_id": FINAL_HOLDOUT_ID,
                    "final_holdout_start": FINAL_HOLDOUT_START,
                    "final_holdout_end_exclusive": FINAL_HOLDOUT_END_EXCLUSIVE,
                },
                sort_keys=True,
            )
        )
        return

    if args.evidence is None:
        parser.error("evidence path is required unless --self-test is used")
    payload = replay(args.evidence)
    encoded = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
