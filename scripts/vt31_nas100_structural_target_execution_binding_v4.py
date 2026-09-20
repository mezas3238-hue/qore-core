"""Frozen physical execution binding V4 for certified VT31 NAS100.

Strategy identity/economics remain:
    VT31_NAS100_STRUCTURAL_TARGET_V1
    fingerprint 089c41f98a72295278063cfc29caf8419538f68315d9f5e57be144fbdae15e08

V4 composes two physical execution invariants without altering economics:
1. CORE non-compressed +1.25R base partial versus equilibrium precedence.
2. Compressed DOL1 acceptance is learned only at the DOL1-touch M1 close.
   A dedicated 25% potential-runner subleg therefore remains open through
   that M1. If the bar rejects, the subleg is closed causally on the DOL1
   retrace observed at 75ms cadence; if accepted, it remains the certified
   DOL2 runner with PS2 protection.

Monte Carlo uses common random numbers with the frozen path-causal economics so
an execution-only relabel cannot change pass/fail for an identical PnL series.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import vt31_nas100_execution_binding_v4 as binding

SCHEMA = "qore.vt31.nas100.structural_target_execution_binding.v4"
STRATEGY_IDENTITY = "VT31_NAS100_STRUCTURAL_TARGET_V1"
CERTIFIED_STRATEGY_FINGERPRINT = (
    "089c41f98a72295278063cfc29caf8419538f68315d9f5e57be144fbdae15e08"
)
EXECUTION_BINDING_ID = "VT31_NAS100_STRUCTURAL_TARGET_EXECUTION_BINDING_V4"
DEVELOPMENT_RUN_ID = 35529831250
DEVELOPMENT_HEAD_SHA = "208a17b1226fa92f5ae13ae6faa69ed52c255783"
DEVELOPMENT_AGGREGATE_ARTIFACT_ID = 10610054712
DEVELOPMENT_AGGREGATE_DIGEST = (
    "sha256:9834bcd8025259f228161da40851dff9c674d1fb5f12a5b61e1aa1e95451ff12"
)


def contract_payload() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "strategy_identity": STRATEGY_IDENTITY,
        "certified_strategy_fingerprint": CERTIFIED_STRATEGY_FINGERPRINT,
        "execution_binding_id": EXECUTION_BINDING_ID,
        "base_target_variant": "EQ50_COMPRESSED_ACCEPT_RUN25",
        "physical_precedence": {
            "core_noncompressed_base_partial_r": "1.25",
            "base_partial_first": "PRESERVE_BASE_LIFECYCLE",
            "same_m1_partial_and_eq": "PRESERVE_BASE_LIFECYCLE",
            "eq_first": "ALLOW_CERTIFIED_EQ_OVERLAY",
            "retroactive_reallocation": False,
        },
        "dol1_acceptance_execution": {
            "potential_runner_subleg_fraction": "0.25",
            "dol1_bank_fraction_after_eq": "0.25",
            "acceptance_observed_on": "DOL1_TOUCH_M1_CLOSE",
            "accepted": "KEEP_025_DOL2_RUNNER_PS2_FROM_NEXT_M1",
            "nonaccept": "CLOSE_025_ON_CAUSAL_DOL1_RETRACE",
            "retrace_watch_ms": 75,
            "retroactive_dol1_exit": False,
        },
        "monte_carlo": {
            "common_random_numbers": True,
            "seed_identity": "PATH_CAUSAL_TARGET:<partition>",
        },
        "unchanged_economics": {
            "entry": True,
            "initial_stop": True,
            "risk_policy": True,
            "equilibrium_fraction": True,
            "dol1_policy": True,
            "runner_fraction": True,
            "runner_destination": True,
            "runner_ps2": True,
            "silver_bullet": True,
        },
        "development_binding": {
            "run_id": DEVELOPMENT_RUN_ID,
            "head_sha": DEVELOPMENT_HEAD_SHA,
            "aggregate_artifact_id": DEVELOPMENT_AGGREGATE_ARTIFACT_ID,
            "aggregate_digest": DEVELOPMENT_AGGREGATE_DIGEST,
        },
        "candidate_frozen": True,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def binding_fingerprint() -> str:
    return hashlib.sha256(
        json.dumps(
            contract_payload(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def replay(path: Path, *, partition: str) -> dict[str, object]:
    payload = binding.replay(path, partition=partition)
    return {
        "schema": SCHEMA,
        "strategy_identity": STRATEGY_IDENTITY,
        "certified_strategy_fingerprint": CERTIFIED_STRATEGY_FINGERPRINT,
        "execution_binding_id": EXECUTION_BINDING_ID,
        "execution_binding_fingerprint": binding_fingerprint(),
        "partition": partition,
        "trade_count": payload["trade_count"],
        "metrics": payload["metrics"],
        "monte_carlo": payload["monte_carlo"],
        "annual_blocks": payload["annual_blocks"],
        "binding_diagnostics": payload["binding_diagnostics"],
        "passes_economic_objectives": payload["passes_economic_objectives"],
        "candidate_frozen": True,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", nargs="?", type=Path)
    parser.add_argument("--partition", default="binding")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        print(
            json.dumps(
                {
                    "strategy_identity": STRATEGY_IDENTITY,
                    "execution_binding_id": EXECUTION_BINDING_ID,
                    "execution_binding_fingerprint": binding_fingerprint(),
                    "certified_strategy_fingerprint": CERTIFIED_STRATEGY_FINGERPRINT,
                    "development_run_id": DEVELOPMENT_RUN_ID,
                    "aggregate_artifact_id": DEVELOPMENT_AGGREGATE_ARTIFACT_ID,
                },
                sort_keys=True,
            )
        )
        return

    if args.evidence is None:
        parser.error("evidence required unless --self-test")
    payload = replay(args.evidence, partition=args.partition)
    encoded = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
