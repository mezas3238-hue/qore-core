#!/usr/bin/env python3
"""Validate GW-2 energy reference binding against sealed provider metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

IDENTITY = "QORE_SHARED_GW2_ENERGY_REFERENCE_BINDING_001"
EXPECTED_PROVIDER_IDENTITY = "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
EXPECTED_AUTHORITY_IDENTITY = "QORE_SHARED_GW2_ENERGY_REFERENCE_AUTHORITY_EVIDENCE_001"


def run(
    *,
    provider_schedule: Path,
    authority_evidence: Path,
    output: Path,
) -> dict[str, object]:
    provider = json.loads(provider_schedule.read_text())
    authority = json.loads(authority_evidence.read_text())
    if provider.get("identity") != EXPECTED_PROVIDER_IDENTITY:
        raise ValueError("unexpected provider schedule")
    if authority.get("identity") != EXPECTED_AUTHORITY_IDENTITY:
        raise ValueError("unexpected energy authority evidence")

    symbols_raw = provider.get("symbols")
    if not isinstance(symbols_raw, list):
        raise ValueError("provider symbols missing")
    symbols = {
        str(row.get("provider_symbol")): cast(dict[str, Any], row)
        for row in symbols_raw
        if isinstance(row, dict)
    }

    resolved_reference = 0
    generic_reference = 0
    records: list[dict[str, object]] = []
    bindings = authority.get("bindings")
    if not isinstance(bindings, list):
        raise ValueError("energy authority bindings missing")

    for raw in bindings:
        if not isinstance(raw, dict):
            raise ValueError("invalid energy authority binding")
        row = cast(dict[str, Any], raw)
        symbol = str(row["provider_symbol"])
        provider_row = symbols.get(symbol)
        if provider_row is None:
            raise ValueError(f"provider energy symbol missing: {symbol}")
        actual_description = str(provider_row.get("provider_description", ""))
        expected_description = str(row["provider_description_expected"])
        if actual_description != expected_description:
            raise ValueError(
                f"{symbol} provider description drift: "
                f"{actual_description!r} != {expected_description!r}"
            )

        status = str(row["reference_identity_status"])
        if status == "SUPPORTED_BY_PROVIDER_DESCRIPTION_AND_EXTERNAL_AUTHORITY":
            resolved_reference += 1
        elif status == "GENERIC_REFERENCE_ONLY":
            generic_reference += 1
        else:
            raise ValueError(f"unexpected energy reference status: {status}")

        records.append(
            {
                "provider_symbol": symbol,
                "provider_description": actual_description,
                "provider_base_asset_name": provider_row.get(
                    "provider_base_asset_name"
                ),
                "provider_quote_asset_name": provider_row.get(
                    "provider_quote_asset_name"
                ),
                "reference_identity": row["reference_identity"],
                "reference_identity_status": status,
                "authority_ids": row["authority_ids"],
                "tradable_product_identity_status": row[
                    "tradable_product_identity_status"
                ],
                "venue_status": row["venue_status"],
                "contract_month_status": row["contract_month_status"],
                "roll_semantics_status": row["roll_semantics_status"],
                "canonical_tradable_identity_verified": False,
            }
        )

    records.sort(key=lambda item: str(item["provider_symbol"]))
    result = {
        "identity": IDENTITY,
        "status": "GW2_ENERGY_REFERENCE_IDENTITY_PARTIALLY_RESOLVED",
        "records": records,
        "energy_sensor_count": len(records),
        "externally_supported_reference_count": resolved_reference,
        "generic_reference_only_count": generic_reference,
        "tradable_product_identity_verified_count": 0,
        "venue_verified_count": 0,
        "roll_semantics_verified_count": 0,
        "xng_henry_hub_mapping_authorized": False,
        "provider_description_is_product_identity": False,
        "reference_identity_is_tradable_identity": False,
        "sensor_admission_authorized": False,
        "relational_claims_authorized": False,
        "protected_holdout_opened": False,
        "productive_authority": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-schedule", type=Path, required=True)
    parser.add_argument("--authority-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    p = run(
        provider_schedule=args.provider_schedule,
        authority_evidence=args.authority_evidence,
        output=args.output,
    )
    print(
        json.dumps(
            {
                "status": p["status"],
                "energy_sensor_count": p["energy_sensor_count"],
                "externally_supported_reference_count": p[
                    "externally_supported_reference_count"
                ],
                "generic_reference_only_count": p[
                    "generic_reference_only_count"
                ],
                "tradable_product_identity_verified_count": p[
                    "tradable_product_identity_verified_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
