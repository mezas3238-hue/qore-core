"""Read-only join: independently sourced queue ledger + prereg draft manifest.

No outcome scores; no lease; no source rights; no frozen-prereg claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.qore_research_prereg_draft_gate_v1 import (
    build_draft_receipt,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authenticated-queue", type=Path, required=True)
    parser.add_argument("--draft-manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    queue: dict[str, Any] = json.loads(
        args.authenticated_queue.read_text(encoding="utf-8")
    )
    manifest: dict[str, Any] = json.loads(
        args.draft_manifest.read_text(encoding="utf-8")
    )
    receipt = build_draft_receipt(manifest, queue)
    assert receipt["can_execute"] is False
    assert receipt["scientific_prereg_frozen"] is False
    assert receipt["data_rights_certified"] is False
    assert receipt["can_open_holdout"] is False
    assert receipt["market_data_spend_usd"] == 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print("PREREG_DRAFT_COUNT", receipt["draft_count"])
    print("PREREG_RECEIPT_SHA256", receipt["receipt_sha256"])
    print("PREREG_DRAFT_ONLY_NO_EXECUTION_NO_SOURCE_CERT_NO_HOLDOUT")


if __name__ == "__main__":
    main()
