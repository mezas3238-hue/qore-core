"""Architect-B provider-attested economic identity boundary.

Materializes what the frozen provider catalogue itself explicitly says about
currently unresolved index and cryptocurrency sensors. It deliberately does
not promote provider metadata into canonical/provider-neutral, tradable,
listing, calendar, historical, relational, or execution identity.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Mapping, cast

IDENTITY = "SHARED_B_PROVIDER_ATTESTED_ECONOMIC_IDENTITY_BOUNDARY_001"
EXPECTED_PROVIDER_IDENTITY = (
    "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
)
EXPECTED_SENSOR_COUNT = 177
EXPECTED_INDEX_COUNT = 25
EXPECTED_CRYPTO_COUNT = 73


class SharedBProviderAttestedIdentityError(ValueError):
    """Provider-attested identity boundary failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _parse_datetime(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise SharedBProviderAttestedIdentityError(f"{field} missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SharedBProviderAttestedIdentityError(
            f"{field} invalid"
        ) from exc
    if parsed.tzinfo is None:
        raise SharedBProviderAttestedIdentityError(
            f"{field} must be timezone aware"
        )
    return parsed


def _required_text(row: Mapping[str, object], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SharedBProviderAttestedIdentityError(f"{field} missing")
    return value.strip()


def build_provider_attested_identity_boundary(
    *,
    provider_schedule: Mapping[str, object],
    known_at: datetime,
) -> dict[str, object]:
    """Build exact provider-attested identity evidence for index/crypto sensors."""

    if provider_schedule.get("identity") != EXPECTED_PROVIDER_IDENTITY:
        raise SharedBProviderAttestedIdentityError(
            "unexpected provider schedule identity"
        )
    if known_at.tzinfo is None:
        raise SharedBProviderAttestedIdentityError(
            "known_at must be timezone aware"
        )

    captured_at = _parse_datetime(
        provider_schedule.get("captured_at"),
        field="captured_at",
    )
    if known_at < captured_at:
        raise SharedBProviderAttestedIdentityError(
            "provider-attested identity cannot predate provider capture"
        )

    symbols = provider_schedule.get("symbols")
    if not isinstance(symbols, list) or len(symbols) != EXPECTED_SENSOR_COUNT:
        raise SharedBProviderAttestedIdentityError(
            "expected exact 177 provider symbols"
        )

    records: list[dict[str, object]] = []
    provider_keys: set[tuple[str, int]] = set()
    class_counts: dict[str, int] = {
        "INDICES": 0,
        "CRYPTOCURRENCIES": 0,
    }

    for raw in symbols:
        if not isinstance(raw, dict):
            raise SharedBProviderAttestedIdentityError(
                "provider symbol row invalid"
            )
        row = cast(dict[str, object], raw)
        asset_class = _required_text(
            row,
            "provider_asset_class_name",
        ).casefold()
        if asset_class not in {"indices", "cryptocurrencies"}:
            continue

        provider = _required_text(row, "provider")
        symbol = _required_text(row, "provider_symbol")
        description = _required_text(row, "provider_description")
        base_asset = _required_text(row, "provider_base_asset_name")
        quote_asset = _required_text(row, "provider_quote_asset_name")
        symbol_id = row.get("provider_symbol_id")
        if type(symbol_id) is not int or symbol_id <= 0:
            raise SharedBProviderAttestedIdentityError(
                "provider_symbol_id invalid"
            )

        key = (provider, symbol_id)
        if key in provider_keys:
            raise SharedBProviderAttestedIdentityError(
                "duplicate provider identity key"
            )
        provider_keys.add(key)

        normalized_class = (
            "INDICES"
            if asset_class == "indices"
            else "CRYPTOCURRENCIES"
        )
        class_counts[normalized_class] += 1
        attested_key = (
            "QORE:PROVIDER_ATTESTED:"
            f"{normalized_class}:{provider}:{symbol_id}"
        )
        records.append(
            {
                "provider": provider,
                "provider_symbol_id": symbol_id,
                "provider_symbol": symbol,
                "provider_asset_class_name": row.get(
                    "provider_asset_class_name"
                ),
                "provider_description": description,
                "provider_base_asset_name": base_asset,
                "provider_quote_asset_name": quote_asset,
                "provider_attested_economic_identity_key": attested_key,
                "provider_attested_reference_label": description,
                "identity_stage": "PROVIDER_ATTESTED_ECONOMIC_OBJECT",
                "evidence_kind": "FROZEN_PROVIDER_METADATA",
                "provider_metadata_fields_used": [
                    "provider_asset_class_name",
                    "provider_description",
                    "provider_base_asset_name",
                    "provider_quote_asset_name",
                ],
                "automatic_identity_inference": False,
                "symbol_name_similarity_used": False,
                "provider_neutral_reference_identity_verified": False,
                "canonical_economic_identity_verified": False,
                "tradable_product_identity_verified": False,
                "listing_identity_verified": False,
                "canonical_calendar_binding_verified": False,
                "historical_pre_freeze_mapping_authorized": False,
                "sensor_admission_authorized": False,
                "relational_claims_authorized": False,
                "execution_authority": False,
            }
        )

    expected_counts = {
        "INDICES": EXPECTED_INDEX_COUNT,
        "CRYPTOCURRENCIES": EXPECTED_CRYPTO_COUNT,
    }
    if class_counts != expected_counts:
        raise SharedBProviderAttestedIdentityError(
            f"unexpected index/crypto population: {class_counts}"
        )
    if len(records) != EXPECTED_INDEX_COUNT + EXPECTED_CRYPTO_COUNT:
        raise SharedBProviderAttestedIdentityError(
            "expected exact 98 unresolved sensors"
        )

    records.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": (
            "EXACT_PROVIDER_ATTESTED_ECONOMIC_BOUNDARY_MATERIALIZED"
        ),
        "provider_schedule_fingerprint_sha256": provider_schedule.get(
            "provider_schedule_catalog_fingerprint_sha256"
        ),
        "provider_catalog_captured_at": captured_at.isoformat(
            timespec="microseconds"
        ),
        "identity_known_at": known_at.isoformat(timespec="microseconds"),
        "sensor_count": len(records),
        "index_sensor_count": class_counts["INDICES"],
        "cryptocurrency_sensor_count": class_counts[
            "CRYPTOCURRENCIES"
        ],
        "provider_attested_economic_object_count": len(records),
        "provider_neutral_reference_identity_verified_count": 0,
        "canonical_economic_identity_verified_count": 0,
        "records": records,
        "provider_metadata_is_canonical_proof": False,
        "provider_description_is_tradable_identity_proof": False,
        "automatic_identity_inference": False,
        "symbol_name_similarity_used": False,
        "historical_market_data_read": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
    }
    payload["boundary_fingerprint_sha256"] = _fingerprint(payload)
    return payload
