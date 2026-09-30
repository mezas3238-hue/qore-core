"""Architect-B commodity observation identity pack.

Combines already-sealed metal reference, energy reference and dated GC futures
identity evidence into one provider-facing observation mapping. It does not
invent energy product identities, continuous futures, front contracts, roll
semantics, scientific admission or productive authority.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Final

IDENTITY: Final = "SHARED_B_COMMODITY_OBSERVATION_IDENTITY_PACK_001"


class SharedBCommodityIdentityError(ValueError):
    """Commodity observation identity evidence failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _aware(value: datetime, *, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SharedBCommodityIdentityError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def build_commodity_observation_identity_pack(
    *,
    provider_schedule: dict[str, object],
    metals_evidence: dict[str, object],
    energy_evidence: dict[str, object],
    gc_contract_evidence: dict[str, object],
    known_at: datetime,
) -> dict[str, object]:
    known = _aware(known_at, name="known_at")

    if provider_schedule.get("identity") != (
        "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
    ):
        raise SharedBCommodityIdentityError("unexpected provider schedule")
    if metals_evidence.get("identity") != (
        "QORE_SHARED_GW2_METALS_ISO4217_REFERENCE_EVIDENCE_001"
    ):
        raise SharedBCommodityIdentityError("unexpected metals evidence")
    if energy_evidence.get("identity") != (
        "QORE_SHARED_GW2_ENERGY_REFERENCE_BINDING_001"
    ):
        raise SharedBCommodityIdentityError("unexpected energy evidence")
    if gc_contract_evidence.get("identity") != (
        "QORE_SHARED_GW2_GC_FUTURES_CONTRACT_BINDING_001"
    ):
        raise SharedBCommodityIdentityError("unexpected GC contract evidence")

    captured_raw = provider_schedule.get("captured_at")
    if not isinstance(captured_raw, str):
        raise SharedBCommodityIdentityError("provider captured_at missing")
    try:
        captured = datetime.fromisoformat(captured_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SharedBCommodityIdentityError("provider captured_at invalid") from exc
    captured = _aware(captured, name="provider captured_at")
    if known < captured:
        raise SharedBCommodityIdentityError(
            "commodity mapping knowledge cannot predate provider capture"
        )

    raw_symbols = provider_schedule.get("symbols")
    if not isinstance(raw_symbols, list):
        raise SharedBCommodityIdentityError("provider symbol catalogue missing")
    by_symbol: dict[str, dict[str, object]] = {}
    for raw in raw_symbols:
        if not isinstance(raw, dict):
            continue
        symbol = raw.get("provider_symbol")
        if not isinstance(symbol, str) or not symbol:
            continue
        if symbol in by_symbol:
            raise SharedBCommodityIdentityError(
                f"duplicate provider symbol: {symbol}"
            )
        by_symbol[symbol] = raw

    records: list[dict[str, object]] = []

    metal_rows = metals_evidence.get("reference_evidence")
    if not isinstance(metal_rows, list) or len(metal_rows) != 11:
        raise SharedBCommodityIdentityError(
            "expected exact 11 metal reference rows"
        )
    for raw in metal_rows:
        if not isinstance(raw, dict):
            raise SharedBCommodityIdentityError("metal evidence row invalid")
        symbol = raw.get("provider_symbol")
        symbol_id = raw.get("provider_symbol_id")
        reference = raw.get("provider_neutral_reference_key")
        if (
            raw.get("components_verified") is not True
            or not isinstance(symbol, str)
            or type(symbol_id) is not int
            or not isinstance(reference, str)
        ):
            raise SharedBCommodityIdentityError(
                "metal reference evidence incomplete"
            )
        provider = by_symbol.get(symbol)
        if provider is None or provider.get("provider_symbol_id") != symbol_id:
            raise SharedBCommodityIdentityError(
                f"metal provider identity drift: {symbol}"
            )
        if (
            provider.get("provider_base_asset_name") != raw.get("metal_code")
            or provider.get("provider_quote_asset_name")
            != raw.get("quote_currency_code")
        ):
            raise SharedBCommodityIdentityError(
                f"metal provider components drift: {symbol}"
            )
        records.append(
            {
                "provider": provider.get("provider"),
                "provider_symbol": symbol,
                "provider_symbol_id": symbol_id,
                "asset_world": "METALS",
                "identity_kind": "REFERENCE_OBJECT",
                "observation_identity": reference,
                "identity_status": "COMPONENT_VERIFIED_REFERENCE",
                "effective_from": captured.isoformat(timespec="microseconds"),
                "known_at": known.isoformat(timespec="microseconds"),
                "historical_pre_freeze_mapping_authorized": False,
                "tradable_product_identity_verified": False,
                "front_contract_verified": False,
                "roll_semantics_verified": False,
                "continuous_series_verified": False,
                "relational_claims_authorized": False,
                "execution_authority": False,
            }
        )

    energy_rows = energy_evidence.get("records")
    if not isinstance(energy_rows, list) or len(energy_rows) != 3:
        raise SharedBCommodityIdentityError("expected exact three energy rows")
    for raw in energy_rows:
        if not isinstance(raw, dict):
            raise SharedBCommodityIdentityError("energy evidence row invalid")
        symbol = raw.get("provider_symbol")
        reference = raw.get("reference_identity")
        status = raw.get("reference_identity_status")
        if not isinstance(symbol, str) or not isinstance(reference, str):
            raise SharedBCommodityIdentityError(
                "energy reference evidence incomplete"
            )
        provider = by_symbol.get(symbol)
        if provider is None:
            raise SharedBCommodityIdentityError(
                f"energy provider identity missing: {symbol}"
            )
        if (
            provider.get("provider_description")
            != raw.get("provider_description")
            or provider.get("provider_base_asset_name")
            != raw.get("provider_base_asset_name")
            or provider.get("provider_quote_asset_name")
            != raw.get("provider_quote_asset_name")
        ):
            raise SharedBCommodityIdentityError(
                f"energy provider descriptor drift: {symbol}"
            )
        if status not in {
            "SUPPORTED_BY_PROVIDER_DESCRIPTION_AND_EXTERNAL_AUTHORITY",
            "GENERIC_REFERENCE_ONLY",
        }:
            raise SharedBCommodityIdentityError(
                f"energy reference status invalid: {symbol}"
            )
        records.append(
            {
                "provider": provider.get("provider"),
                "provider_symbol": symbol,
                "provider_symbol_id": provider.get("provider_symbol_id"),
                "asset_world": "ENERGY",
                "identity_kind": "REFERENCE_OBJECT",
                "observation_identity": reference,
                "identity_status": status,
                "effective_from": captured.isoformat(timespec="microseconds"),
                "known_at": known.isoformat(timespec="microseconds"),
                "historical_pre_freeze_mapping_authorized": False,
                "tradable_product_identity_verified": False,
                "front_contract_verified": False,
                "roll_semantics_verified": False,
                "continuous_series_verified": False,
                "relational_claims_authorized": False,
                "execution_authority": False,
            }
        )

    gc_rows = gc_contract_evidence.get("records")
    if not isinstance(gc_rows, list) or len(gc_rows) != 5:
        raise SharedBCommodityIdentityError("expected exact five GC contracts")
    for raw in gc_rows:
        if not isinstance(raw, dict):
            raise SharedBCommodityIdentityError("GC contract row invalid")
        symbol = raw.get("provider_symbol")
        if (
            not isinstance(symbol, str)
            or raw.get("contract_identity_verified") is not True
            or raw.get("venue") != "COMEX"
            or raw.get("economic_underlying") != "GOLD"
        ):
            raise SharedBCommodityIdentityError(
                "GC dated contract evidence incomplete"
            )
        provider = by_symbol.get(symbol)
        if provider is None or provider.get("provider_description") != raw.get(
            "provider_description"
        ):
            raise SharedBCommodityIdentityError(
                f"GC provider identity drift: {symbol}"
            )
        contract_key = (
            f"QORE:FUTURES_CONTRACT:{raw['canonical_product']}:"
            f"{int(raw['contract_year']):04d}-{int(raw['contract_month']):02d}:COMEX"
        )
        records.append(
            {
                "provider": provider.get("provider"),
                "provider_symbol": symbol,
                "provider_symbol_id": provider.get("provider_symbol_id"),
                "asset_world": "METALS_FUTURES",
                "identity_kind": "DATED_FUTURES_CONTRACT_DESCRIPTOR",
                "observation_identity": contract_key,
                "identity_status": "PRODUCT_MONTH_YEAR_VENUE_VERIFIED",
                "effective_from": captured.isoformat(timespec="microseconds"),
                "known_at": known.isoformat(timespec="microseconds"),
                "historical_pre_freeze_mapping_authorized": False,
                "dated_contract_identity_verified": True,
                "front_contract_verified": False,
                "roll_semantics_verified": False,
                "continuous_series_verified": False,
                "relational_claims_authorized": False,
                "execution_authority": False,
            }
        )

    records.sort(
        key=lambda item: (
            str(item["asset_world"]),
            str(item["provider_symbol"]),
        )
    )
    provider_ids = [
        (row["provider"], row["provider_symbol_id"]) for row in records
    ]
    if len(provider_ids) != len(set(provider_ids)):
        raise SharedBCommodityIdentityError(
            "commodity provider identity collision"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "CURRENT_COMMODITY_OBSERVATION_IDENTITY_PACK_COMPLETE",
        "provider_schedule_captured_at": captured.isoformat(
            timespec="microseconds"
        ),
        "known_at": known.isoformat(timespec="microseconds"),
        "records": records,
        "record_count": len(records),
        "metal_reference_count": 11,
        "energy_reference_count": 3,
        "dated_gc_contract_count": 5,
        "historical_pre_freeze_mapping_authorized": False,
        "energy_tradable_product_identity_verified_count": 0,
        "gc_front_contract_verified_count": 0,
        "gc_roll_semantics_verified_count": 0,
        "gc_continuous_series_verified_count": 0,
        "sensor_admission_authorized": False,
        "relational_claims_authorized": False,
        "historical_market_data_read": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
    }
    payload["pack_fingerprint_sha256"] = _fingerprint(payload)
    return payload
