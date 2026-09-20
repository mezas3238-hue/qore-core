"""Frozen VT31 NAS100 sequence-risk certification candidate V1.

Candidate:
    VT31_NAS100_SEQUENCE_RISK_V1

Frozen development survivor:
    B0_L1LONG_X050

Exact policy extension over the current causal stack:
- current strongest ALLOC_G / SHIELD / Breaker-regime / loss-cluster stack;
- sequence state uses only already-closed prior trades;
- risk x0.50 when either:
  * pre-loss streak bucket is 0 and premarket is directional OR confirmation
    latency is 3-5m; or
  * pre-loss streak bucket is 1 and side is long.
- each trade is compressed at most once;
- no trade admission, Silver Bullet, entry, stop, target, lifecycle or rearm
  rule changes.

Research/certification only. No live, production or real-capital authority.
"""
# ruff: noqa: B009
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_causal_sequence_union_risk_frontier_v1 as union
import vt31_nas100_residual_regime_forensics_v2 as residual
import vt31_nas100_sequence_state_interaction_forensics_v1 as seq

SCHEMA = "qore.vt31.nas100.sequence_risk_candidate.v1"
CANDIDATE_ID = "VT31_NAS100_SEQUENCE_RISK_V1"
MARKET = "NAS100"
FROZEN_VARIANT = "B0_L1LONG_X050"
FROZEN_SCOPE = "B0_L1LONG"
FROZEN_MULTIPLIER = Decimal("0.50")

DEVELOPMENT_RUN_ID = 35483839558
DEVELOPMENT_HEAD_SHA = "46af9d8ebd7ea8346173683b8142fc66b30fe9be"
DEVELOPMENT_AGGREGATE_ARTIFACT_ID = 10596991898
DEVELOPMENT_AGGREGATE_DIGEST = (
    "sha256:e421a67cecef98c14f8d9fd280fc099418d2e5ef1c1abcf3cc8eec46d1c2beda"
)

DEVELOPMENT_RESULT = {
    "consumed_trade_count": 334,
    "consumed_profit_factor": "2.259299274390833557133327090",
    "consumed_max_drawdown_r": "3.654018889645883",
    "consumed_total_r": "16.040870853506235",
    "consumed_mc_positive_terminal_probability": "0.9027",
    "consumed_mc_p95_max_drawdown_r": "8.5931937219926",
    "consumed_year_1_positive": True,
    "consumed_year_2_positive": True,
    "r5_trade_count": 350,
    "r6_trade_count": 334,
    "r8_trade_count": 300,
}

FIVE_YEAR_GATES = {
    "trade_count_min": 800,
    "trade_count_max": 900,
    "profit_factor_min": "1.50",
    "total_r_min_exclusive": "0",
    "observed_max_drawdown_r_max": "6.00",
    "all_five_year_blocks_positive": True,
    "mc_positive_terminal_probability_min": "0.90",
    "mc_p95_max_drawdown_r_max": "15.00",
}


def frozen_rows(evidence_path: Path) -> list[dict[str, object]]:
    rows, _evidence, _diagnostics, _stats = alt._current_rows(evidence_path)
    annotated = seq._annotate(rows)
    return union._apply(
        annotated,
        scope=FROZEN_SCOPE,
        multiplier=FROZEN_MULTIPLIER,
    )


def contract_payload() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "market": MARKET,
        "methodology": "VT31-AM-SILVER-BULLET-CAUSAL-SEQUENCE-RISK",
        "timezone": "America/New_York",
        "source_granularity": "closed-M1",
        "silver_bullet_frozen": True,
        "frozen_variant": FROZEN_VARIANT,
        "frozen_scope": FROZEN_SCOPE,
        "frozen_multiplier": format(FROZEN_MULTIPLIER, "f"),
        "sequence_policy": {
            "prior_trade_state_only": True,
            "bucket0_condition": (
                "premarket in {bearish,bullish} OR "
                "confirmation_latency_bucket == 3_5m"
            ),
            "bucket1_condition": "side == long",
            "single_compression_per_trade": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "rearm_changed": False,
        },
        "development_binding": {
            "run_id": DEVELOPMENT_RUN_ID,
            "head_sha": DEVELOPMENT_HEAD_SHA,
            "aggregate_artifact_id": DEVELOPMENT_AGGREGATE_ARTIFACT_ID,
            "aggregate_digest": DEVELOPMENT_AGGREGATE_DIGEST,
            "development_result": DEVELOPMENT_RESULT,
        },
        "five_year_validation": {
            "window_start": "2017-07-01",
            "window_end_exclusive": "2022-07-01",
            "fresh": False,
            "status": "CONSUMED_EXTENDED_VALIDATION",
            "parameters_retuned_inside_5y": False,
            "gates": FIVE_YEAR_GATES,
        },
        "causal_firewall": {
            "future_bars": False,
            "terminal_pnl_oracle": False,
            "fold_identity_rule": False,
            "calendar_rule": False,
            "mc_block_identity_runtime_rule": False,
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


def replay(evidence_path: Path, *, partition: str) -> dict[str, object]:
    rows = frozen_rows(evidence_path)
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "contract_fingerprint": contract_fingerprint(),
        "partition": partition,
        "trade_count": len(rows),
        "metrics": residual._metrics(rows),
        "monte_carlo": engine._monte_carlo(
            rows,
            variant=f"{CANDIDATE_ID}:{partition}",
        ),
        "candidate_frozen": True,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", nargs="?", type=Path)
    parser.add_argument("--partition", default="frozen_candidate")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        print(
            json.dumps(
                {
                    "candidate_id": CANDIDATE_ID,
                    "contract_fingerprint": contract_fingerprint(),
                    "frozen_variant": FROZEN_VARIANT,
                    "development_run_id": DEVELOPMENT_RUN_ID,
                    "development_aggregate_artifact_id": (
                        DEVELOPMENT_AGGREGATE_ARTIFACT_ID
                    ),
                    "five_year_gates": FIVE_YEAR_GATES,
                },
                sort_keys=True,
            )
        )
        return

    if args.evidence is None:
        parser.error("evidence path is required unless --self-test is used")

    payload = replay(args.evidence, partition=args.partition)
    encoded = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
