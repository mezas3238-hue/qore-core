#!/usr/bin/env python3
"""GW-2 provider-bound canonical identity resolution audit.

This program consumes real provider-native identity metadata plus the frozen
GEN-2 unresolved mapping worklist and GW-1 world-family candidates. It does not
manufacture canonical identities from provider symbols. Instead it determines,
per real provider sensor, which economic identity evidence is already present
and which evidence is still required before a UMI canonical mapping may exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, cast

IDENTITY = "QORE_SHARED_GW2_CANONICAL_IDENTITY_RESOLUTION_001"
EXPECTED_PROVIDER_IDENTITY = "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
EXPECTED_GW1_IDENTITY = "QORE_SHARED_GLOBAL_MULTI_ASSET_PROVIDER_CAPABILITY_001"
TARGET_FAMILIES = ("FX", "EQUITY_INDICES", "METALS", "ENERGY")


class GW2IdentityResolutionError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise GW2IdentityResolutionError(f"{path} must contain a JSON object")
    return cast(dict[str, Any], payload)


def _sha(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _nonempty(row: dict[str, object], field: str) -> bool:
    value = row.get(field)
    return isinstance(value, str) and bool(value.strip())


def _provider_key(row: dict[str, object]) -> tuple[str, int]:
    provider = row.get("provider")
    symbol_id = row.get("provider_symbol_id")
    if not isinstance(provider, str) or not provider:
        raise GW2IdentityResolutionError("provider identity missing")
    if type(symbol_id) is not int or symbol_id <= 0:
        raise GW2IdentityResolutionError("provider_symbol_id invalid")
    return provider, symbol_id


def _family_requirements(
    family: str,
    row: dict[str, object],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Return provider fields, canonical evidence obligations and hard blockers."""

    provider_fields: list[str] = [
        "provider_symbol",
        "provider_native_symbol_name",
        "provider_asset_class_name",
    ]
    obligations: list[str] = [
        "PROVIDER_NATIVE_EXTERNAL_IDENTIFIER",
        "EFFECTIVE_DATED_EXTERNAL_TO_CANONICAL_MAPPING",
        "CANONICAL_ECONOMIC_IDENTITY_EVIDENCE",
    ]
    blockers: list[str] = []

    if family == "FX":
        provider_fields.extend(
            ("provider_base_asset_name", "provider_quote_asset_name")
        )
        obligations.extend(
            (
                "BASE_CURRENCY_CANONICAL_IDENTITY",
                "QUOTE_CURRENCY_CANONICAL_IDENTITY",
                "PRODUCT_CONSTRUCTION_EVIDENCE",
                "DISTRIBUTED_OTC_SCOPE_EVIDENCE",
            )
        )
    elif family == "EQUITY_INDICES":
        provider_fields.append("provider_description")
        obligations.extend(
            (
                "UNDERLYING_INDEX_CANONICAL_IDENTITY",
                "INDEX_PROVIDER_OR_METHODOLOGY_EVIDENCE",
                "PRODUCT_CONSTRUCTION_EVIDENCE",
                "VALUATION_CURRENCY_EVIDENCE",
            )
        )
    elif family == "METALS":
        provider_fields.extend(
            ("provider_base_asset_name", "provider_quote_asset_name")
        )
        obligations.extend(
            (
                "COMMODITY_REFERENCE_CANONICAL_IDENTITY",
                "PRODUCT_CONSTRUCTION_EVIDENCE",
                "PRICING_CURRENCY_EVIDENCE",
                "QUANTITY_UNIT_EVIDENCE",
            )
        )
    elif family == "ENERGY":
        provider_fields.append("provider_description")
        obligations.extend(
            (
                "COMMODITY_REFERENCE_CANONICAL_IDENTITY",
                "PRODUCT_CONSTRUCTION_EVIDENCE",
                "PRICING_CURRENCY_EVIDENCE",
                "QUANTITY_UNIT_EVIDENCE",
                "CONTRACT_OR_REFERENCE_SERIES_SEMANTICS",
                "ROLL_DELIVERY_EXPIRY_EVIDENCE_IF_DERIVATIVE",
            )
        )
    else:
        raise GW2IdentityResolutionError(f"unsupported GW-2 family {family}")

    missing = [field for field in provider_fields if not _nonempty(row, field)]
    blockers.extend(f"MISSING_PROVIDER_METADATA:{field}" for field in missing)

    # GEN-2 law: provider-native descriptors are evidence, never canonical truth.
    blockers.append("EXTERNAL_CANONICAL_IDENTITY_EVIDENCE_REQUIRED")
    return (
        tuple(sorted(set(provider_fields))),
        tuple(sorted(set(obligations))),
        tuple(sorted(set(blockers))),
    )


def run(
    *,
    provider_schedule: Path,
    mapping_registry: Path,
    gw1_matrix: Path,
    output: Path,
) -> dict[str, object]:
    provider = _load(provider_schedule)
    mapping = _load(mapping_registry)
    gw1 = _load(gw1_matrix)

    if provider.get("identity") != EXPECTED_PROVIDER_IDENTITY:
        raise GW2IdentityResolutionError("unexpected provider schedule identity")
    if gw1.get("identity") != EXPECTED_GW1_IDENTITY:
        raise GW2IdentityResolutionError("unexpected GW-1 matrix identity")
    if mapping.get("status") != "UNRESOLVED_BASELINE_FROZEN":
        raise GW2IdentityResolutionError(
            "GW-2 requires frozen unresolved GEN-2 mapping baseline"
        )
    if mapping.get("verified_count") != 0:
        raise GW2IdentityResolutionError(
            "unexpected pre-existing canonical verification in GEN-2 baseline"
        )
    if mapping.get("automatic_identity_inference") is not False:
        raise GW2IdentityResolutionError(
            "automatic provider-to-canonical inference must remain disabled"
        )

    provider_rows = provider.get("symbols")
    if not isinstance(provider_rows, list):
        raise GW2IdentityResolutionError("provider schedule symbols missing")
    by_key = {
        _provider_key(cast(dict[str, object], row)): cast(dict[str, object], row)
        for row in provider_rows
        if isinstance(row, dict)
    }

    worklist = mapping.get("provider_evidence_worklist")
    if not isinstance(worklist, list):
        raise GW2IdentityResolutionError("GEN-2 provider evidence worklist missing")
    mapping_by_key = {
        _provider_key(cast(dict[str, object], row)): cast(dict[str, object], row)
        for row in worklist
        if isinstance(row, dict)
    }

    families = gw1.get("families")
    if not isinstance(families, list):
        raise GW2IdentityResolutionError("GW-1 family matrix missing")

    result_rows: list[dict[str, object]] = []
    family_summaries: list[dict[str, object]] = []
    for family in TARGET_FAMILIES:
        source_family = next(
            (
                cast(dict[str, object], item)
                for item in families
                if isinstance(item, dict) and item.get("family") == family
            ),
            None,
        )
        if source_family is None:
            raise GW2IdentityResolutionError(f"GW-1 family missing: {family}")
        candidates = source_family.get("candidates")
        if not isinstance(candidates, list):
            raise GW2IdentityResolutionError(f"GW-1 candidates missing: {family}")

        complete_descriptors = 0
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise GW2IdentityResolutionError("invalid GW-1 candidate row")
            key = _provider_key(cast(dict[str, object], candidate))
            row = by_key.get(key)
            work = mapping_by_key.get(key)
            if row is None or work is None:
                raise GW2IdentityResolutionError(
                    f"candidate {key} absent from sealed GEN-2 evidence"
                )

            fields, obligations, blockers = _family_requirements(family, row)
            descriptor_complete = not any(
                item.startswith("MISSING_PROVIDER_METADATA:")
                for item in blockers
            )
            complete_descriptors += int(descriptor_complete)

            current_mapping_status = work.get("current_mapping_status")
            if current_mapping_status != "UNRESOLVED":
                raise GW2IdentityResolutionError(
                    "GW-2 refuses non-unresolved baseline mapping"
                )

            result_rows.append(
                {
                    "family": family,
                    "provider": key[0],
                    "provider_symbol_id": key[1],
                    "provider_symbol": row.get("provider_symbol"),
                    "provider_native_symbol_name": row.get(
                        "provider_native_symbol_name"
                    ),
                    "provider_description": row.get("provider_description"),
                    "provider_asset_class_name": row.get(
                        "provider_asset_class_name"
                    ),
                    "provider_symbol_category_name": row.get(
                        "provider_symbol_category_name"
                    ),
                    "provider_base_asset_name": row.get(
                        "provider_base_asset_name"
                    ),
                    "provider_quote_asset_name": row.get(
                        "provider_quote_asset_name"
                    ),
                    "current_market_structure": work.get(
                        "current_market_structure"
                    ),
                    "venue_evidence_rule": work.get("venue_evidence_rule"),
                    "provider_descriptor_required_fields": fields,
                    "provider_descriptor_complete": descriptor_complete,
                    "canonical_evidence_obligations": obligations,
                    "resolution_blockers": blockers,
                    "canonical_identity_verified": False,
                    "canonical_economic_identity_id": None,
                    "listing_identity_id": None,
                    "automatic_identity_inference": False,
                    "sensor_admission_authorized": False,
                    "relational_claims_authorized": False,
                }
            )

        family_summaries.append(
            {
                "family": family,
                "candidate_count": len(candidates),
                "provider_descriptor_complete_count": complete_descriptors,
                "canonical_identity_verified_count": 0,
                "canonical_identity_unresolved_count": len(candidates),
            }
        )

    result_rows.sort(
        key=lambda item: (
            str(item["family"]),
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    family_summaries.sort(key=lambda item: str(item["family"]))

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "GW2_REAL_PROVIDER_IDENTITY_EVIDENCE_BOUND_UNRESOLVED",
        "provider_schedule_fingerprint_sha256": provider[
            "provider_schedule_catalog_fingerprint_sha256"
        ],
        "gen2_mapping_registry_fingerprint_sha256": mapping[
            "canonical_mapping_registry_fingerprint_sha256"
        ],
        "gw1_matrix_fingerprint_sha256": gw1["matrix_fingerprint_sha256"],
        "target_families": TARGET_FAMILIES,
        "family_summaries": family_summaries,
        "record_count": len(result_rows),
        "records": result_rows,
        "canonical_identity_verified_count": 0,
        "canonical_identity_unresolved_count": len(result_rows),
        "provider_symbol_is_canonical_identity": False,
        "provider_native_metadata_is_canonical_proof": False,
        "automatic_identity_inference": False,
        "sensor_admission_authorized": False,
        "relational_claims_authorized": False,
        "historical_market_data_read": False,
        "target_or_outcome_read": False,
        "protected_holdout_opened": False,
        "productive_authority": False,
    }
    payload["resolution_fingerprint_sha256"] = _sha(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-schedule", type=Path, required=True)
    parser.add_argument("--mapping-registry", type=Path, required=True)
    parser.add_argument("--gw1-matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        provider_schedule=args.provider_schedule,
        mapping_registry=args.mapping_registry,
        gw1_matrix=args.gw1_matrix,
        output=args.output,
    )
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "status": payload["status"],
                "record_count": payload["record_count"],
                "canonical_identity_verified_count": payload[
                    "canonical_identity_verified_count"
                ],
                "family_summaries": payload["family_summaries"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
