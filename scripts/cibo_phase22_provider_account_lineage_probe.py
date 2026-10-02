"""Prove both historical account fingerprints are the same DEMO account."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.cibo_phase22_provider_numeric_execution import (
    build_account_lineage_receipt,
)
from qore.infrastructure.ctrader_demo_free_binding import (
    discover_free_account_binding,
)
from qore.infrastructure.ctrader_demo_free_sink import (
    credentials_from_environment,
)
from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    try:
        binding = discover_free_account_binding(client)
        receipt = build_account_lineage_receipt(binding.account.account_ref)
    finally:
        client.close()

    payload = {
        "schema": "qore.cibo.phase22.provider-account-lineage.v1",
        **receipt.payload(),
        "receipt_sha256": receipt.fingerprint(),
        "account_ref_exposed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
