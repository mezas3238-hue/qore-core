"""Synthetic GitHub API metadata only; no broker, quotes, OHLC, or credentials."""
from copy import deepcopy

import pytest

from qore.research.alpha2_g2_p0_exact33_contract_evidence_census import (
    IDENTITY,
    RUNS,
    source_only_census,
)


def fake_runs():
    data = {}
    for name, (rid, head, aid, sha, prefix) in RUNS.items():
        data[name] = {
            "run": {
                "id": rid,
                "head_sha": head,
                "status": "completed",
                "conclusion": "success",
                "run_attempt": 1,
            },
            "artifacts": {
                "total_count": 1,
                "artifacts": [{
                    "id": aid, "name": prefix + head,
                    "digest": "sha256:" + sha,
                    "expired": False, "size_in_bytes": 512,
                }],
            },
        }
    return data


def test_all_33_complete_metadata_census_never_broker_contract_certificate():
    x = source_only_census(fake_runs())
    assert x["identity"] == IDENTITY
    assert x["status"].endswith("CONTRACTS_0_OF_33_BLOCKED")
    assert len(x["source_metadata_witnesses"]) == 6
    assert len(x["rows"]) == 33
    assert x["original12"] == 12 and x["new21"] == 21
    assert x["simultaneous_demo_60s_quote_symbols"] == 29
    assert x["independent_separate_demo_45s_quote_symbols"] == 1
    assert x["contract_eligible_count"] == 0
    assert x["broker_API_requests_made"] == x["broker_orders_submitted"] == 0
    assert x["original_quote_bytes_read"] is False
    assert x["UTC001_certified"] is False
    assert x["economic_NET_computed"] is False
    for row in x["rows"]:
        assert row["broker_execution_contract_eligible"] is False
        assert row["broker_fee_swap_financing_schedule_PIT_verified"] is False
        assert row["historical_atlas_account_contract_equivalence_proven"] is False
        assert row["NET_economic_edge_proven"] is False
        assert row["UTC001_certified"] is False


def test_two_aliases_unproved_even_if_original_run_qa_passes():
    x = source_only_census(fake_runs())
    by_name = {a["canonical_G0_symbol"]: a for a in x["rows"]}
    assert by_name["NAS100"]["reported_provider_symbol_not_contract_equivalence"] == "USTEC"
    assert by_name["SP500"]["reported_provider_symbol_not_contract_equivalence"] == "US500"
    assert by_name["NAS100"]["quote_or_catalog_source_evidence_class"] == (
        "USTEC_CATALOG_ALIAS_METADATA_SHA_ONLY_NOT_EQUIVALENT"
    )
    assert by_name["SP500"]["github_api_metadata_sha_witness_names"] == []
    assert by_name["XAGUSD"]["github_api_metadata_sha_witness_names"] == []
    assert by_name["NZDUSD"]["github_api_metadata_sha_witness_names"] == [
        "DEMO_NZDUSD_SOURCE", "DEMO_NZDUSD_INDEPENDENT_QA"
    ]
    assert by_name["NZDUSD"]["original_M5_cohort"] == "ICMARKETS_NEW21"
    assert by_name["NAS100"]["original_M5_cohort"] == "ATLAS_ORIGINAL12"
    assert by_name["XAGUSD"]["original_M5_cohort"] == "ATLAS_ORIGINAL12"


@pytest.mark.parametrize("spoof", [
    "wrong_run_id", "wrong_head", "failed_run", "replayed_attempt",
    "not_completed", "bool_run_id",
])
def test_failure_of_original_run_evidence_blocks(spoof):
    x = fake_runs()
    r = x["DEMO_EXACT29_SOURCE"]["run"]
    if spoof == "wrong_run_id":
        r["id"] += 1
    elif spoof == "wrong_head":
        r["head_sha"] = "0" * 40
    elif spoof == "failed_run":
        r["conclusion"] = "failure"
    elif spoof == "replayed_attempt":
        r["run_attempt"] = 2
    elif spoof == "not_completed":
        r["status"] = "in_progress"
    else:
        r["id"] = True
    with pytest.raises(ValueError, match="RUN_ID_HEAD_OR_SUCCESS"):
        source_only_census(x)


@pytest.mark.parametrize("spoof", [
    "missing_artifact", "second_artifact", "page_truncation", "wrong_id",
    "wrong_sha", "bad_name", "expired", "empty_size", "boolean_size",
])
def test_artifact_metadata_tampering_blocks_all_33(spoof):
    x = fake_runs()
    a = x["DEMO_USTEC_CATALOG_SOURCE"]["artifacts"]
    row = a["artifacts"][0]
    if spoof == "missing_artifact":
        a["artifacts"] = []
        a["total_count"] = 0
    elif spoof == "second_artifact":
        a["artifacts"].append(deepcopy(row))
        a["total_count"] = 2
    elif spoof == "page_truncation":
        a["total_count"] = 100
    elif spoof == "wrong_id":
        row["id"] += 100
    elif spoof == "wrong_sha":
        row["digest"] = "sha256:" + "f" * 64
    elif spoof == "bad_name":
        row["name"] = "USTEC"
    elif spoof == "expired":
        row["expired"] = True
    elif spoof == "empty_size":
        row["size_in_bytes"] = 0
    else:
        row["size_in_bytes"] = True
    with pytest.raises(ValueError, match="ARTIFACT"):
        source_only_census(x)


def test_partial_six_run_scope_or_surplus_unsupported_run_denied():
    x = fake_runs()
    x.pop("DEMO_NZDUSD_INDEPENDENT_QA")
    with pytest.raises(ValueError, match="SIX_RUNS_REQUIRED"):
        source_only_census(x)
    x = fake_runs()
    x["PROVIDER_ALIAS_WITHOUT_SIGNATURE"] = x["DEMO_NZDUSD_SOURCE"]
    with pytest.raises(ValueError, match="SIX_RUNS_REQUIRED"):
        source_only_census(x)


def test_unexpected_artifact_list_fields_denied():
    x = fake_runs()
    x["DEMO_EXACT29_INDEPENDENT_QA"]["artifacts"]["total_count"] = None
    with pytest.raises(ValueError, match="ARTIFACT"):
        source_only_census(x)
    x = fake_runs()
    x["DEMO_EXACT29_SOURCE"]["artifacts"]["artifacts"] = "not a list"
    with pytest.raises(ValueError, match="ARTIFACT"):
        source_only_census(x)


def test_wrong_entry_schema_denied_before_any_report():
    x = fake_runs()
    x["DEMO_EXACT29_SOURCE"]["net_certified"] = True
    with pytest.raises(ValueError, match="ENTRY_SCHEMA_INVALID"):
        source_only_census(x)
