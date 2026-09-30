from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.shared_b_commodity_observation_identity import (
    SharedBCommodityIdentityError,
    build_commodity_observation_identity_pack,
)


def _fixtures() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    symbols: list[dict[str, object]]=[]
    metals: list[dict[str, object]]=[]
    metal_pairs=[
        ("XAGAUD","XAG","AUD"),("XAGEUR","XAG","EUR"),
        ("XAGUSD","XAG","USD"),("XAUAUD","XAU","AUD"),
        ("XAUCHF","XAU","CHF"),("XAUEUR","XAU","EUR"),
        ("XAUGBP","XAU","GBP"),("XAUJPY","XAU","JPY"),
        ("XAUUSD","XAU","USD"),("XPDUSD","XPD","USD"),
        ("XPTUSD","XPT","USD"),
    ]
    next_id=1
    for symbol,base,quote in metal_pairs:
        symbols.append({
            "provider":"CTRADER_DEMO",
            "provider_symbol":symbol,
            "provider_symbol_id":next_id,
            "provider_description":symbol,
            "provider_base_asset_name":base,
            "provider_quote_asset_name":quote,
        })
        metals.append({
            "provider":"CTRADER_DEMO",
            "provider_symbol":symbol,
            "provider_symbol_id":next_id,
            "provider_description":symbol,
            "metal_code":base,
            "quote_currency_code":quote,
            "components_verified":True,
            "provider_neutral_reference_key":f"QORE:METAL_REFERENCE:{base}/{quote}",
        })
        next_id+=1

    energy_records=[]
    for symbol,base,reference,status in (
        ("XBRUSD","XBR","BRENT_CRUDE_OIL_BENCHMARK_FAMILY",
         "SUPPORTED_BY_PROVIDER_DESCRIPTION_AND_EXTERNAL_AUTHORITY"),
        ("XNGUSD","XNG","GENERIC_NATURAL_GAS","GENERIC_REFERENCE_ONLY"),
        ("XTIUSD","XTI","WTI_LIGHT_SWEET_CRUDE_OIL",
         "SUPPORTED_BY_PROVIDER_DESCRIPTION_AND_EXTERNAL_AUTHORITY"),
    ):
        description=f"desc-{symbol}"
        symbols.append({
            "provider":"CTRADER_DEMO",
            "provider_symbol":symbol,
            "provider_symbol_id":next_id,
            "provider_description":description,
            "provider_base_asset_name":base,
            "provider_quote_asset_name":"USD",
        })
        energy_records.append({
            "provider_symbol":symbol,
            "provider_description":description,
            "provider_base_asset_name":base,
            "provider_quote_asset_name":"USD",
            "reference_identity":reference,
            "reference_identity_status":status,
        })
        next_id+=1

    gc_records=[]
    for symbol,month,year in (
        ("GCG26",2,2026),("GCJ26",4,2026),("GCM25",6,2025),
        ("GCM26",6,2026),("GCQ26",8,2026),
    ):
        description=f"Gold Futures {symbol}"
        symbols.append({
            "provider":"CTRADER_DEMO",
            "provider_symbol":symbol,
            "provider_symbol_id":next_id,
            "provider_description":description,
            "provider_base_asset_name":symbol,
            "provider_quote_asset_name":"USD",
        })
        gc_records.append({
            "provider_symbol":symbol,
            "provider_description":description,
            "canonical_product":"COMEX_GOLD_FUTURES_100_TROY_OZ",
            "venue":"COMEX",
            "economic_underlying":"GOLD",
            "contract_month":month,
            "contract_year":year,
            "contract_identity_verified":True,
        })
        next_id+=1

    provider={
        "identity":"QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001",
        "captured_at":"2026-09-30T07:00:00+00:00",
        "symbols":symbols,
    }
    metal_evidence={
        "identity":"QORE_SHARED_GW2_METALS_ISO4217_REFERENCE_EVIDENCE_001",
        "reference_evidence":metals,
    }
    energy_evidence={
        "identity":"QORE_SHARED_GW2_ENERGY_REFERENCE_BINDING_001",
        "records":energy_records,
    }
    gc_evidence={
        "identity":"QORE_SHARED_GW2_GC_FUTURES_CONTRACT_BINDING_001",
        "records":gc_records,
    }
    return provider,metal_evidence,energy_evidence,gc_evidence


def test_commodity_pack_preserves_reference_contract_boundaries() -> None:
    provider,metals,energy,gc=_fixtures()
    payload=build_commodity_observation_identity_pack(
        provider_schedule=provider,
        metals_evidence=metals,
        energy_evidence=energy,
        gc_contract_evidence=gc,
        known_at=datetime(2026,9,30,18,0,tzinfo=UTC),
    )

    assert payload["record_count"] == 19
    assert payload["metal_reference_count"] == 11
    assert payload["energy_reference_count"] == 3
    assert payload["dated_gc_contract_count"] == 5
    assert payload["historical_pre_freeze_mapping_authorized"] is False
    assert payload["energy_tradable_product_identity_verified_count"] == 0
    assert payload["gc_front_contract_verified_count"] == 0
    assert payload["gc_roll_semantics_verified_count"] == 0
    assert payload["gc_continuous_series_verified_count"] == 0
    assert payload["sensor_admission_authorized"] is False
    assert payload["relational_claims_authorized"] is False
    assert payload["target_or_outcome_read"] is False
    assert payload["fresh_holdout_opened"] is False
    assert payload["productive_authority"] is False
    assert len(payload["pack_fingerprint_sha256"]) == 64

    rows=payload["records"]
    assert isinstance(rows,list)
    metal=[x for x in rows if x["asset_world"]=="METALS"]
    energy_rows=[x for x in rows if x["asset_world"]=="ENERGY"]
    futures=[x for x in rows if x["asset_world"]=="METALS_FUTURES"]
    assert len(metal)==11
    assert len(energy_rows)==3
    assert len(futures)==5
    assert all(x["identity_kind"]=="REFERENCE_OBJECT" for x in metal+energy_rows)
    assert all(
        x["identity_kind"]=="DATED_FUTURES_CONTRACT_DESCRIPTOR"
        and x["dated_contract_identity_verified"] is True
        and x["front_contract_verified"] is False
        and x["continuous_series_verified"] is False
        for x in futures
    )


def test_commodity_pack_rejects_provider_component_drift() -> None:
    provider,metals,energy,gc=_fixtures()
    drift=deepcopy(provider)
    symbols=drift["symbols"]
    assert isinstance(symbols,list)
    symbols[0]["provider_quote_asset_name"]="XXX"

    with pytest.raises(
        SharedBCommodityIdentityError,
        match="metal provider components drift",
    ):
        build_commodity_observation_identity_pack(
            provider_schedule=drift,
            metals_evidence=metals,
            energy_evidence=energy,
            gc_contract_evidence=gc,
            known_at=datetime(2026,9,30,18,0,tzinfo=UTC),
        )


def test_commodity_pack_rejects_unverified_gc_contract() -> None:
    provider,metals,energy,gc=_fixtures()
    broken=deepcopy(gc)
    records=broken["records"]
    assert isinstance(records,list)
    records[0]["contract_identity_verified"]=False

    with pytest.raises(
        SharedBCommodityIdentityError,
        match="GC dated contract evidence incomplete",
    ):
        build_commodity_observation_identity_pack(
            provider_schedule=provider,
            metals_evidence=metals,
            energy_evidence=energy,
            gc_contract_evidence=broken,
            known_at=datetime(2026,9,30,18,0,tzinfo=UTC),
        )


def test_commodity_pack_rejects_mapping_known_before_provider_capture() -> None:
    provider,metals,energy,gc=_fixtures()
    with pytest.raises(
        SharedBCommodityIdentityError,
        match="cannot predate provider capture",
    ):
        build_commodity_observation_identity_pack(
            provider_schedule=provider,
            metals_evidence=metals,
            energy_evidence=energy,
            gc_contract_evidence=gc,
            known_at=datetime(2026,9,30,6,59,tzinfo=UTC),
        )
