"""Emit the active CIBO Phase22 V2 pre-holdout gate without fresh execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.cibo_ce2i_holdout_registry import (
    ACTIVE_USD60_HOLDOUT_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_freeze_v2 import (
    evaluate_phase22_v2_pre_holdout_readiness,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    phase22_v2_holdout_source_receipt_payload,
)


def build_report() -> dict[str, object]:
    readiness = evaluate_phase22_v2_pre_holdout_readiness()
    candidate = ACTIVE_USD60_HOLDOUT_CANDIDATE
    return {
        "schema": "qore.cibo.phase22.v2-pre-holdout-gate.v1",
        "status": readiness.state.value,
        "authorized": readiness.ready_to_unseal_v2,
        "blockers": list(readiness.blockers),
        "holdout_candidate_id": candidate.candidate_id,
        "window": {
            "start": candidate.start_at.isoformat(),
            "end_exclusive": candidate.end_exclusive_at.isoformat(),
        },
        "source_receipt": phase22_v2_holdout_source_receipt_payload(),
        "pre_holdout_v2": readiness.as_dict(),
        "fresh_outcomes_executed": False,
        "productive_authority": False,
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
