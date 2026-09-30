#!/usr/bin/env python3
"""Materialize exact provider-native metadata for GW-2 non-FX identity work.

This atlas does not infer canonical identity. It exposes the complete real
provider descriptors already sealed by GEN-2 so later evidence binding can
resolve underlying/product/contract semantics without guessing from symbols.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, cast

from shared_global_multi_asset_provider_capability_audit import _family_matches

IDENTITY = "QORE_SHARED_GW2_NONFX_PROVIDER_METADATA_ATLAS_001"
EXPECTED_PROVIDER_IDENTITY = "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
FAMILIES = ("EQUITY_INDICES", "METALS", "ENERGY")
EXPECTED_COUNTS = {"EQUITY_INDICES": 25, "METALS": 16, "ENERGY": 3}


def _sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def run(*, provider_schedule: Path, output: Path) -> dict[str, object]:
    payload = json.loads(provider_schedule.read_text())
    if payload.get("identity") != EXPECTED_PROVIDER_IDENTITY:
        raise ValueError("unexpected provider schedule identity")
    source = payload.get("symbols")
    if not isinstance(source, list):
        raise ValueError("provider schedule symbols missing")

    families: list[dict[str, object]] = []
    for family in FAMILIES:
        rows: list[dict[str, object]] = []
        for raw in source:
            if not isinstance(raw, dict):
                continue
            row = cast(dict[str, Any], raw)
            if not _family_matches(family, cast(dict[str, object], row)):
                continue

            descriptors = {
                "provider_symbol": _clean(row.get("provider_symbol")),
                "provider_native_symbol_name": _clean(
                    row.get("provider_native_symbol_name")
                ),
                "provider_description": _clean(
                    row.get("provider_description")
                ),
                "provider_asset_class_name": _clean(
                    row.get("provider_asset_class_name")
                ),
                "provider_symbol_category_name": _clean(
                    row.get("provider_symbol_category_name")
                ),
                "provider_base_asset_name": _clean(
                    row.get("provider_base_asset_name")
                ),
                "provider_base_asset_display_name": _clean(
                    row.get("provider_base_asset_display_name")
                ),
                "provider_quote_asset_name": _clean(
                    row.get("provider_quote_asset_name")
                ),
            }
            populated = tuple(
                sorted(key for key, value in descriptors.items() if value)
            )
            rows.append(
                {
                    "provider": row.get("provider"),
                    "provider_symbol_id": row.get("provider_symbol_id"),
                    **descriptors,
                    "populated_descriptor_fields": populated,
                    "descriptor_field_count": len(populated),
                    "canonical_identity_inferred": False,
                    "product_construction_inferred": False,
                    "contract_identity_inferred": False,
                }
            )

        rows.sort(
            key=lambda item: (
                str(item["provider_symbol"]),
                int(cast(int, item["provider_symbol_id"])),
            )
        )
        if len(rows) != EXPECTED_COUNTS[family]:
            raise ValueError(
                f"{family} expected {EXPECTED_COUNTS[family]} rows, got {len(rows)}"
            )

        complete_description = sum(
            bool(row["provider_description"]) for row in rows
        )
        complete_base = sum(
            bool(row["provider_base_asset_name"]) for row in rows
        )
        complete_quote = sum(
            bool(row["provider_quote_asset_name"]) for row in rows
        )
        families.append(
            {
                "family": family,
                "sensor_count": len(rows),
                "description_present_count": complete_description,
                "base_asset_present_count": complete_base,
                "quote_asset_present_count": complete_quote,
                "records": rows,
            }
        )

    result: dict[str, object] = {
        "identity": IDENTITY,
        "status": "GW2_REAL_PROVIDER_NATIVE_METADATA_MATERIALIZED",
        "provider_schedule_identity": payload["identity"],
        "provider_schedule_fingerprint_sha256": payload[
            "provider_schedule_catalog_fingerprint_sha256"
        ],
        "families": families,
        "total_sensor_count": sum(
            int(cast(int, family["sensor_count"])) for family in families
        ),
        "provider_metadata_is_canonical_proof": False,
        "automatic_identity_inference": False,
        "historical_market_data_read": False,
        "target_or_outcome_read": False,
        "protected_holdout_opened": False,
        "productive_authority": False,
    }
    result["atlas_fingerprint_sha256"] = _sha(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-schedule", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    p = run(provider_schedule=args.provider_schedule, output=args.output)
    print(
        json.dumps(
            {
                "identity": p["identity"],
                "status": p["status"],
                "total_sensor_count": p["total_sensor_count"],
                "families": [
                    {
                        "family": row["family"],
                        "sensor_count": row["sensor_count"],
                        "description_present_count": row[
                            "description_present_count"
                        ],
                        "base_asset_present_count": row[
                            "base_asset_present_count"
                        ],
                        "quote_asset_present_count": row[
                            "quote_asset_present_count"
                        ],
                    }
                    for row in cast(
                        list[dict[str, object]],
                        p["families"],
                    )
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
