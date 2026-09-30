"""Emit Architect-B exclusive open-work ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_b_open_work_ledger import (
    build_shared_b_open_work_ledger,
)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()

    payload=build_shared_b_open_work_ledger()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(
        json.dumps(payload,sort_keys=True,indent=2)+"\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "identity":payload["identity"],
        "mandatory_item_count":payload["mandatory_item_count"],
        "completed_and_proven_count":payload["completed_and_proven_count"],
        "required_open_count":payload["required_open_count"],
        "zero_open_required_work":payload["zero_open_required_work"],
    },sort_keys=True))


if __name__=="__main__":
    main()
