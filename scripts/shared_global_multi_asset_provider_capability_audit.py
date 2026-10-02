#!/usr/bin/env python3
"""Build a real provider-bound multi-asset world capability matrix.

This is GW-1 inventory evidence, not sensor admission or relational intelligence.
It consumes the sealed GEN-2 provider catalogue and never fabricates unavailable
markets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, cast

IDENTITY = "QORE_SHARED_GLOBAL_MULTI_ASSET_PROVIDER_CAPABILITY_001"
EXPECTED_PROVIDER_CATALOG_IDENTITY = (
    "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
)

FAMILIES = (
    "FX",
    "EQUITY_INDICES",
    "RATES",
    "VOLATILITY",
    "CREDIT",
    "METALS",
    "ENERGY",
    "AGRICULTURE",
    "SOFTS",
    "LIVESTOCK",
    "POWER",
    "FREIGHT",
    "ENVIRONMENTAL",
)

AGRICULTURE_TERMS = (
    "corn",
    "wheat",
    "soybean",
    "soy meal",
    "soy oil",
    "oats",
    "rough rice",
)
SOFT_TERMS = (
    "coffee",
    "cocoa",
    "sugar",
    "cotton",
    "orange juice",
)
LIVESTOCK_TERMS = (
    "live cattle",
    "feeder cattle",
    "lean hog",
)
ENERGY_TERMS = (
    "natural gas",
    "brent",
    "crude",
    "wti",
    "gasoil",
    "heating oil",
    "gasoline",
    "lng",
)
VOLATILITY_TERMS = ("vix", "volatility", "vol index")
RATES_TERMS = (
    "treasury",
    "bond",
    "bund",
    "gilt",
    "yield",
    "interest rate",
    "sofr",
    "euribor",
)
CREDIT_TERMS = ("credit", "itraxx", "cdx", "high yield", "investment grade")
POWER_TERMS = ("electricity", "power", "baseload", "peakload")
FREIGHT_TERMS = ("freight", "baltic", "shipping")
ENVIRONMENTAL_TERMS = ("carbon", "emission", "allowance", "eua")


class GlobalMultiAssetProviderAuditError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise GlobalMultiAssetProviderAuditError(
            "provider schedule catalogue must be a JSON object"
        )
    return cast(dict[str, Any], payload)


def _text(row: dict[str, object]) -> str:
    values = (
        row.get("provider_symbol"),
        row.get("provider_native_symbol_name"),
        row.get("provider_description"),
        row.get("provider_base_asset_name"),
        row.get("provider_base_asset_display_name"),
        row.get("provider_symbol_category_name"),
        row.get("provider_asset_class_name"),
    )
    return " ".join(
        str(value).casefold()
        for value in values
        if isinstance(value, str) and value
    )


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _family_matches(
    family: str,
    row: dict[str, object],
) -> bool:
    asset_class = str(row.get("provider_asset_class_name", "")).casefold()
    text = _text(row)

    if family == "FX":
        return asset_class == "forex"
    if family == "EQUITY_INDICES":
        return asset_class == "indices"
    if family == "METALS":
        return asset_class == "metals"
    if family == "ENERGY":
        return asset_class == "oil" or _contains_any(text, ENERGY_TERMS)
    if family == "AGRICULTURE":
        return _contains_any(text, AGRICULTURE_TERMS)
    if family == "SOFTS":
        return _contains_any(text, SOFT_TERMS)
    if family == "LIVESTOCK":
        return _contains_any(text, LIVESTOCK_TERMS)
    if family == "VOLATILITY":
        return _contains_any(text, VOLATILITY_TERMS)
    if family == "RATES":
        return _contains_any(text, RATES_TERMS)
    if family == "CREDIT":
        return _contains_any(text, CREDIT_TERMS)
    if family == "POWER":
        return _contains_any(text, POWER_TERMS)
    if family == "FREIGHT":
        return _contains_any(text, FREIGHT_TERMS)
    if family == "ENVIRONMENTAL":
        return _contains_any(text, ENVIRONMENTAL_TERMS)
    raise GlobalMultiAssetProviderAuditError(f"unknown world family: {family}")


def _candidate(row: dict[str, object]) -> dict[str, object]:
    return {
        "provider": row.get("provider"),
        "provider_symbol_id": row.get("provider_symbol_id"),
        "provider_symbol": row.get("provider_symbol"),
        "provider_native_symbol_name": row.get("provider_native_symbol_name"),
        "provider_description": row.get("provider_description"),
        "provider_asset_class_name": row.get("provider_asset_class_name"),
        "provider_symbol_category_name": row.get(
            "provider_symbol_category_name"
        ),
        "provider_base_asset_name": row.get("provider_base_asset_name"),
        "provider_quote_asset_name": row.get("provider_quote_asset_name"),
        "identity_verified": False,
        "historical_depth_verified": False,
        "relational_ready": False,
    }


def _sha(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def run(provider_schedule: Path, output: Path) -> dict[str, object]:
    provider = _load(provider_schedule)
    if provider.get("identity") != EXPECTED_PROVIDER_CATALOG_IDENTITY:
        raise GlobalMultiAssetProviderAuditError(
            "unexpected GEN-2 provider catalogue identity"
        )
    rows = provider.get("symbols")
    if not isinstance(rows, list) or not rows:
        raise GlobalMultiAssetProviderAuditError(
            "provider catalogue contains no symbols"
        )
    symbols = [
        cast(dict[str, object], row)
        for row in rows
        if isinstance(row, dict)
    ]
    if len(symbols) != len(rows):
        raise GlobalMultiAssetProviderAuditError(
            "provider catalogue contains invalid symbol rows"
        )

    family_rows = []
    for family in FAMILIES:
        candidates = [
            _candidate(row)
            for row in symbols
            if _family_matches(family, row)
        ]
        candidates.sort(
            key=lambda item: (
                str(item["provider"]),
                int(cast(int, item["provider_symbol_id"])),
            )
        )
        family_rows.append(
            {
                "family": family,
                "availability": (
                    "DISCOVERED_PROVIDER_CANDIDATES"
                    if candidates
                    else "UNAVAILABLE_IN_CURRENT_PROVIDER_EVIDENCE"
                ),
                "provider_candidate_count": len(candidates),
                "candidates": candidates,
                "provider_availability_is_canonical_identity": False,
                "automatic_sensor_admission": False,
                "historical_depth_verified": False,
                "scientific_intelligence_implemented": False,
            }
        )

    asset_class_counts: dict[str, int] = {}
    for row in symbols:
        key = str(row.get("provider_asset_class_name", "UNRESOLVED"))
        asset_class_counts[key] = asset_class_counts.get(key, 0) + 1

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "GW1_REAL_PROVIDER_CAPABILITY_MATRIX",
        "provider_catalog_identity": provider["identity"],
        "provider_catalog_fingerprint_sha256": provider[
            "provider_schedule_catalog_fingerprint_sha256"
        ],
        "provider_sensor_count": len(symbols),
        "provider_asset_class_counts": dict(sorted(asset_class_counts.items())),
        "families": family_rows,
        "provider_symbol_is_canonical_identity": False,
        "automatic_sensor_admission": False,
        "relational_claims_authorized": False,
        "historical_market_data_read": False,
        "target_or_outcome_read": False,
        "protected_holdout_opened": False,
        "productive_authority": False,
    }
    payload["matrix_fingerprint_sha256"] = _sha(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-schedule", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.provider_schedule, args.output)
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "status": payload["status"],
                "provider_sensor_count": payload["provider_sensor_count"],
                "families": [
                    {
                        "family": row["family"],
                        "availability": row["availability"],
                        "provider_candidate_count": row[
                            "provider_candidate_count"
                        ],
                    }
                    for row in cast(list[dict[str, object]], payload["families"])
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
