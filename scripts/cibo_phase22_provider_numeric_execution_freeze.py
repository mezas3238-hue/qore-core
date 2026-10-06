"""Freeze Phase22 provider numeric execution specs from sealed artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.cibo_phase22_provider_numeric_execution import (
    Phase22ProviderAccountLineageReceipt,
    build_numeric_execution_specs,
    load_json_object,
    numeric_spec_freeze_payload,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-terms", type=Path, required=True)
    parser.add_argument("--empirical-execution", type=Path, required=True)
    parser.add_argument("--account-lineage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    lineage_raw = load_json_object(args.account_lineage)
    lineage = Phase22ProviderAccountLineageReceipt(
        provider_key=str(lineage_raw["provider_key"]),
        legacy_account_fingerprint_sha256=str(
            lineage_raw["legacy_account_fingerprint_sha256"]
        ),
        phase22_account_fingerprint_sha256=str(
            lineage_raw["phase22_account_fingerprint_sha256"]
        ),
        same_account_proven=bool(lineage_raw["same_account_proven"]),
    )
    specs = build_numeric_execution_specs(
        provider_terms_payload=load_json_object(args.provider_terms),
        empirical_execution_payload=load_json_object(args.empirical_execution),
        account_lineage=lineage,
    )
    payload = numeric_spec_freeze_payload(
        specs=specs,
        account_lineage=lineage,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
