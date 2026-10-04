#!/usr/bin/env python3
"""CLI for Architect-B6 sealed pre-freeze deterministic evidence replay."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_b_pre_freeze_replay import (
    replay_pre_freeze_evidence,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--b16-artifact", type=Path, required=True)
    parser.add_argument("--b21-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    receipt = replay_pre_freeze_evidence(
        b16_zip=args.b16_artifact,
        b21_zip=args.b21_artifact,
    )
    payload = {
        "identity": "SHARED_B_PRE_FREEZE_DETERMINISTIC_REPLAY_001",
        **asdict(receipt),
        "b21_complete_claim": False,
        "b22_freeze_authorized_by_this_receipt": False,
        "reason": (
            "B6 evidence-layer deterministic replay is sealed; final B21 "
            "closure still requires terminal upstream B surface."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
