"""Frozen physical-execution binding for certified VT31 NAS100.

Strategy identity remains:
    VT31_NAS100_STRUCTURAL_TARGET_V1

Certified strategy contract fingerprint remains:
    089c41f98a72295278063cfc29caf8419538f68315d9f5e57be144fbdae15e08

This binding adds no economic parameter. It freezes one physically necessary
precedence rule for the live executor:

- CORE non-compressed retains its certified +1.25R partial lifecycle.
- If that base partial is first (or same M1 as EQ), the base lifecycle is
  preserved and the later EQ overlay may not retroactively reallocate already
  realized exposure.
- If EQ is first, the existing EQ50_COMPRESSED_ACCEPT_RUN25 overlay remains
  eligible exactly as certified.

Entry, stop, risk, EQ fraction, DOL1, runner selector, runner target and PS2
remain unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import vt31_nas100_path_causal_target_ladder_v2 as binding

SCHEMA = "qore.vt31.nas100.structural_target_execution_binding.v2"
STRATEGY_IDENTITY = "VT31_NAS100_STRUCTURAL_TARGET_V1"
CERTIFIED_STRATEGY_FINGERPRINT = (
    "089c41f98a72295278063cfc29caf8419538f68315d9f5e57be144fbdae15e08"
)
EXECUTION_BINDING_ID = "VT31_NAS100_STRUCTURAL_TARGET_EXECUTION_BINDING_V2"
DEVELOPMENT_RUN_ID = 35523529809
DEVELOPMENT_HEAD_SHA = "dbfb10f460ae639c196f6531fea75514a1d0f002"
DEVELOPMENT_AGGREGATE_ARTIFACT_ID = 10609341253
DEVELOPMENT_AGGREGATE_DIGEST = (
    "sha256:c3ab417feff0ba75d81ed45bc87e7f2dcb89eb189e7ed37159286cab781bd67b"
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
        "unchanged_economics": {
            "entry": True,
            "initial_stop": True,
            "risk_policy": True,
            "equilibrium_fraction": True,
            "dol1_policy": True,
            "runner_selector": True,
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
    encoded = json.dumps(
        contract_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


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
        "path_diagnostics": payload["path_diagnostics"],
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
