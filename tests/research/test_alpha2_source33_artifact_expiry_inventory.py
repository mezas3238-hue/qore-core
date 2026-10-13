"""Synthetic fake GitHub API artifact listings, ZERO original M5 data read."""
from datetime import UTC, datetime, timedelta

import pytest

from qore.research.alpha2_source33_artifact_expiry_inventory import (
    ATLAS_PREFIX,
    ATLAS_RUN,
    HEADS,
    NEW21,
    NEW21_PREFIX,
    NEW21_RUN,
    ORIGINAL12,
    SIGNED33_PREFIX,
    SOURCE33_RUN,
    audit,
)

T=datetime(2026,10,12,tzinfo=UTC)
DIGEST="sha256:"+"a"*64


def artifact(rid,name,aid,days=65):
    return {
        "id":aid,"name":name,"size_in_bytes":1000,
        "digest":DIGEST,"expired":False,
        "created_at":(T-timedelta(days=25)).isoformat().replace("+00:00","Z"),
        "expires_at":(T+timedelta(days=days)).isoformat().replace("+00:00","Z"),
    }


def fixtures(*,atlas_days=65,new_days=90):
    atl=[
        artifact(ATLAS_RUN,ATLAS_PREFIX+s+"-"+HEADS[ATLAS_RUN],100+i,atlas_days)
        for i,s in enumerate(ORIGINAL12)
    ]
    atl.append(artifact(ATLAS_RUN,ATLAS_PREFIX+"aggregate-"+HEADS[ATLAS_RUN],
                        113,atlas_days))
    new=[
        artifact(NEW21_RUN,NEW21_PREFIX+s+"-"+HEADS[NEW21_RUN],200+i,new_days)
        for i,s in enumerate(NEW21)
    ]
    signed=[
        artifact(SOURCE33_RUN,SIGNED33_PREFIX+HEADS[SOURCE33_RUN],400,new_days),
    ]
    listings={
        rid:{"total_count":len(rows),"artifacts":rows}
        for rid,rows in ((ATLAS_RUN,atl),(NEW21_RUN,new),(SOURCE33_RUN,signed))
    }
    runs={
        rid:{"id":rid,"head_sha":sha,"status":"completed","conclusion":"success"}
        for rid,sha in HEADS.items()
    }
    return listings,runs


def test_exact_33_source_artifacts_and_original_atlas_aggregate():
    listing,runs=fixtures()
    d=audit(listing,runs,now=T)
    assert d["original_m5_source_markets_verified"]==33
    assert len(d["per_original_market_artifact_ids_digests_expiry"])==33
    assert d["status"]=="P0_ARCHIVE_VAULT_LICENSE_AND_RESTORE_BEFORE_EXPIRY"
    assert d["total_compressed_original33_m5_bytes"]==33000
    assert d["minimum_days_until_expiry"]==65
    assert d["cohorts"]["ATLAS_ORIGINAL12"]["archive_bytes"]==12000
    assert d["cohorts"]["ICMARKETS_NEW21"]["archive_bytes"]==21000
    assert d["authorized_private_durable_vault_backup_verified"] is False
    assert d["trade_orders_sent"]==0


def test_critical_expiry_30_day_gate():
    listings,runs=fixtures(atlas_days=20)
    report=audit(listings,runs,now=T)
    assert report["status"]=="P0_CRITICAL_SOURCE_EXPIRY"


def test_no_backfilling_of_missing_market_or_misnamed_provider():
    listings,runs=fixtures()
    listings[NEW21_RUN]["artifacts"].pop()
    listings[NEW21_RUN]["total_count"]-=1
    with pytest.raises(ValueError,match="NEW21"):
        audit(listings,runs,now=T)


def test_artifact_expired_or_digest_absent_blocks():
    listings,runs=fixtures()
    listings[ATLAS_RUN]["artifacts"][0]["expired"]=True
    with pytest.raises(ValueError,match="MISSING_SHA_OR_EXPIRED"):
        audit(listings,runs,now=T)
    listings,runs=fixtures()
    listings[ATLAS_RUN]["artifacts"][0]["digest"]="sha256:not-64"
    with pytest.raises(ValueError,match="MISSING_SHA_OR_EXPIRED"):
        audit(listings,runs,now=T)


def test_wrong_signed_github_run_code_head_blocks():
    listings,runs=fixtures()
    runs[ATLAS_RUN]["head_sha"]="deadbeef"
    with pytest.raises(ValueError,match="HEAD_OR_SUCCESS"):
        audit(listings,runs,now=T)


def test_censored_or_truncated_api_page_does_not_claim_source_complete():
    listings,runs=fixtures()
    listings[NEW21_RUN]["total_count"]=100
    with pytest.raises(ValueError,match="LIST_INCOMPLETE"):
        audit(listings,runs,now=T)


def test_duplicate_github_artifact_name_and_id_block():
    listings,runs=fixtures()
    listings[ATLAS_RUN]["artifacts"][1]["id"]=100
    with pytest.raises(ValueError,match="MISSING_SHA_OR_EXPIRED"):
        audit(listings,runs,now=T)
    listings,runs=fixtures()
    listings[ATLAS_RUN]["artifacts"][1]["name"]=listings[ATLAS_RUN][
        "artifacts"][0]["name"]
    with pytest.raises(ValueError,match="DUPLICATE"):
        audit(listings,runs,now=T)
