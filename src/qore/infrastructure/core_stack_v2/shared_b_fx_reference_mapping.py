"""Architect-B FX provider-to-reference mapping.

This boundary authorizes only current observation mapping from an exact cTrader
provider symbol identity to a provider-neutral FX pair reference object after
the provider's explicit base/quote descriptors and both component identities
have been independently verified.

It does not certify a tradable instrument, venue/listing, calendar, historical
pre-freeze mapping, or productive authority.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Final

IDENTITY: Final = "SHARED_B_GW2_FX_PROVIDER_REFERENCE_MAPPING_001"
EXPECTED_PROVIDER_SCHEDULE_IDENTITY: Final = (
    "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
)
EXPECTED_COMPONENT_IDENTITY: Final = "SHARED_B_GW2_CNH_COMPONENT_IDENTITY_001"


class SharedBFxReferenceMappingError(ValueError):
    """FX provider/reference mapping evidence failed closed."""


def _fingerprint(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _aware(value: datetime, *, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise SharedBFxReferenceMappingError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def resolve_current_fx_reference_mappings(
    *,
    provider_schedule: dict[str, object],
    component_resolution: dict[str, object],
    mapping_known_at: datetime,
) -> dict[str, object]:
    known_at = _aware(mapping_known_at, name="mapping_known_at")

    if provider_schedule.get("identity") != EXPECTED_PROVIDER_SCHEDULE_IDENTITY:
        raise SharedBFxReferenceMappingError("unexpected provider schedule identity")
    if component_resolution.get("identity") != EXPECTED_COMPONENT_IDENTITY:
        raise SharedBFxReferenceMappingError("unexpected FX component identity")
    if component_resolution.get("currency_component_identity_verified_count") != 21:
        raise SharedBFxReferenceMappingError("FX component universe incomplete")
    if component_resolution.get("fx_pairs_with_all_currency_components_verified") != 60:
        raise SharedBFxReferenceMappingError("FX pair component coverage incomplete")
    if component_resolution.get("provider_symbol_to_reference_mapping_authorized") is not False:
        raise SharedBFxReferenceMappingError("upstream component evidence widened authority")

    frozen_raw = provider_schedule.get("catalog_frozen_at")
    if not isinstance(frozen_raw, str):
        raise SharedBFxReferenceMappingError("provider schedule freeze time missing")
    try:
        frozen_at = datetime.fromisoformat(frozen_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SharedBFxReferenceMappingError("provider freeze time invalid") from exc
    frozen_at = _aware(frozen_at, name="catalog_frozen_at")
    if known_at < frozen_at:
        raise SharedBFxReferenceMappingError(
            "mapping knowledge cutoff cannot predate provider freeze"
        )

    symbols = provider_schedule.get("symbols")
    pairs = component_resolution.get("pairs")
    if not isinstance(symbols, list) or not isinstance(pairs, list):
        raise SharedBFxReferenceMappingError("provider/pair evidence missing")

    provider_fx: dict[tuple[str, int], dict[str, object]] = {}
    for raw in symbols:
        if not isinstance(raw, dict):
            continue
        if str(raw.get("provider_asset_class_name", "")).casefold() != "forex":
            continue
        provider = raw.get("provider")
        symbol_id = raw.get("provider_symbol_id")
        if not isinstance(provider, str) or type(symbol_id) is not int or symbol_id <= 0:
            raise SharedBFxReferenceMappingError("FX provider identity invalid")
        key = (provider, symbol_id)
        if key in provider_fx:
            raise SharedBFxReferenceMappingError("duplicate FX provider identity")
        provider_fx[key] = raw

    if len(provider_fx) != 60:
        raise SharedBFxReferenceMappingError(
            f"expected 60 provider FX symbols, got {len(provider_fx)}"
        )

    component_pairs: dict[tuple[str, int], dict[str, object]] = {}
    for raw in pairs:
        if not isinstance(raw, dict):
            raise SharedBFxReferenceMappingError("FX component pair invalid")
        provider = raw.get("provider")
        symbol_id = raw.get("provider_symbol_id")
        if not isinstance(provider, str) or type(symbol_id) is not int or symbol_id <= 0:
            raise SharedBFxReferenceMappingError("component provider identity invalid")
        if raw.get("currency_components_verified") is not True:
            raise SharedBFxReferenceMappingError("unverified FX components remain")
        ref = raw.get("provider_neutral_reference_key")
        if not isinstance(ref, str) or not ref.startswith("QORE:FX_REFERENCE:"):
            raise SharedBFxReferenceMappingError("provider-neutral reference key missing")
        key = (provider, symbol_id)
        if key in component_pairs:
            raise SharedBFxReferenceMappingError("duplicate component pair identity")
        component_pairs[key] = raw

    if set(provider_fx) != set(component_pairs):
        raise SharedBFxReferenceMappingError(
            "provider schedule/component pair populations differ"
        )

    mappings: list[dict[str, object]] = []
    reference_keys: set[str] = set()
    for key in sorted(provider_fx):
        provider_row = provider_fx[key]
        component_row = component_pairs[key]
        symbol = provider_row.get("provider_symbol")
        base = provider_row.get("provider_base_asset_name")
        quote = provider_row.get("provider_quote_asset_name")
        if (
            symbol != component_row.get("provider_symbol")
            or base != component_row.get("base_currency_code")
            or quote != component_row.get("quote_currency_code")
        ):
            raise SharedBFxReferenceMappingError(
                f"provider descriptor drift for {key[0]}:{key[1]}"
            )
        if not all(isinstance(value, str) and value.strip() for value in (symbol, base, quote)):
            raise SharedBFxReferenceMappingError("FX descriptor incomplete")

        reference_key = str(component_row["provider_neutral_reference_key"])
        expected_reference = f"QORE:FX_REFERENCE:{base}/{quote}"
        if reference_key != expected_reference:
            raise SharedBFxReferenceMappingError("FX reference construction mismatch")
        reference_keys.add(reference_key)
        mappings.append(
            {
                "provider": key[0],
                "provider_symbol_id": key[1],
                "provider_symbol": symbol,
                "provider_native_symbol_name": provider_row.get(
                    "provider_native_symbol_name"
                ),
                "base_currency_code": base,
                "quote_currency_code": quote,
                "reference_key": reference_key,
                "mapping_scope": "CURRENT_OBSERVATION_REFERENCE_ONLY",
                "effective_from": frozen_at.isoformat(timespec="microseconds"),
                "effective_until": None,
                "known_at": known_at.isoformat(timespec="microseconds"),
                "historical_pre_freeze_mapping_authorized": False,
                "tradable_instrument_identity_verified": False,
                "listing_identity_verified": False,
                "calendar_mapping_authorized": False,
                "relational_claims_authorized": False,
                "execution_authority": False,
            }
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "CURRENT_FX_PROVIDER_TO_REFERENCE_MAPPING_COMPLETE",
        "provider_schedule_fingerprint_sha256": provider_schedule.get(
            "provider_schedule_catalog_fingerprint_sha256"
        ),
        "component_resolution_fingerprint_sha256": component_resolution.get(
            "resolution_fingerprint_sha256"
        ),
        "catalog_frozen_at": frozen_at.isoformat(timespec="microseconds"),
        "mapping_known_at": known_at.isoformat(timespec="microseconds"),
        "provider_fx_symbol_count": len(mappings),
        "mapped_provider_fx_symbol_count": len(mappings),
        "provider_neutral_reference_count": len(reference_keys),
        "mappings": mappings,
        "provider_symbol_to_reference_mapping_authorized": True,
        "mapping_authority_scope": "CURRENT_OBSERVATION_REFERENCE_ONLY",
        "historical_pre_freeze_mapping_authorized": False,
        "canonical_tradable_identity_verified_count": 0,
        "listing_identity_verified_count": 0,
        "calendar_mapping_authorized": False,
        "relational_claims_authorized": False,
        "historical_market_data_read": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "productive_authority": False,
    }
    payload["mapping_fingerprint_sha256"] = _fingerprint(payload)
    return payload
