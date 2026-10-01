"""Emit the active CIBO pre-holdout access gate without reading 2017H1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.cibo_ce2i_holdout_registry import (
    PREREGISTERED_USD60_HOLDOUT,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_freeze import (
    ACTIVE_PRE_HOLDOUT_FREEZE,
    pre_holdout_freeze_ready,
    pre_holdout_freeze_receipt_payload,
)


def build_report() -> dict[str, object]:
    manifest = ACTIVE_PRE_HOLDOUT_FREEZE
    authorized = pre_holdout_freeze_ready()
    candidate = PREREGISTERED_USD60_HOLDOUT
    return {
        "schema": "qore.cibo.pre_holdout_gate.v2",
        "status": (
            "READY_TO_UNSEAL_2017H1"
            if authorized
            else "LOCKED_UNTOUCHED"
        ),
        "authorized": authorized,
        "blockers": [] if authorized else ["PRE_HOLDOUT_FREEZE_NOT_ACTIVE"],
        "holdout_candidate_id": candidate.candidate_id,
        "holdout_outcomes_inspected": False,
        "holdout_market_data_read": False,
        "provider_economics_frozen": (
            False if manifest is None else manifest.provider_economics_frozen
        ),
        "phase20d_causal_tool_gate_passed": (
            False
            if manifest is None
            else manifest.phase20d_causal_tool_gate_passed
        ),
        "phase21_policy_freeze_sealed": (
            False
            if manifest is None
            else manifest.phase21_policy_freeze_sealed
        ),
        "calibration_freeze_manifest_sealed": (
            False if manifest is None else manifest.all_calibrations_frozen
        ),
        "freeze_receipt": (
            None
            if manifest is None
            else pre_holdout_freeze_receipt_payload()
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
