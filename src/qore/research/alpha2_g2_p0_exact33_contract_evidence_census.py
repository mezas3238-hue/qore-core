"""Fail-closed source-only 33-contract evidence census from six GitHub metadata runs.

No broker or raw quote access, no PnL, no account contract equality, no orders.
See G2 P0 exact33 offline contract evidence census prereg dated 2026-10-12.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from qore.research.alpha2_g2_29_real_bidask_reuse import SOURCE_29
from qore.research.alpha2_intermarket import MARKETS
from qore.research.alpha2_source33_artifact_expiry_inventory import (
    NEW21,
    ORIGINAL12,
)

IDENTITY = "QORE_ALPHA2_G2_P0_EXACT33_SIX_ORIGINAL_RUN_META_CENSUS_V1"
G0_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
EXCLUDED = frozenset({"NAS100", "SP500", "NZDUSD", "XAGUSD"})
RUNS = {
    "DEMO_EXACT29_SOURCE": (
        38298399112, "33068c720fedb3d358a2f73e7323508abd8365f6",
        11769446263, "6de061c63d570e2c004fd4192b3771395fd33ba68199df620447046baf081472",
        "alpha2-g2-forward-exact29-demo-firstseen-NOT-NET-",
    ),
    "DEMO_EXACT29_INDEPENDENT_QA": (
        38298920851, "a80702b40e2242f7da05d392137cc76ce7124b8b",
        11770276257, "0787fa156e5a4d5b885d27ff8aee8ce831618ae5fd1cee16eb742294ba2a6bb6",
        "alpha2-g2-29-independent-forward-source-QA-",
    ),
    "DEMO_NZDUSD_SOURCE": (
        38296610948, "ca32ad2311c5c6b4a9312073ca0b4c7b53109a75",
        11767978684, "f3e0e8e52f459e8c2ec136a84b4346dd81f130787fe0430b0ed4bc7b9c4e9039",
        "alpha2-g2-nzdusd-first-receipt-DEMO-NOT-NET-",
    ),
    "DEMO_NZDUSD_INDEPENDENT_QA": (
        38297614422, "2c39e6e5c4047f2c30ffdcf84c271ead07aa8167",
        11768424790, "b6ed9e8ae23fd17be7c9fcfd93c386f6309303154631177e8d924cefd829f0cf",
        "alpha2-g2-nzdusd-independent-firstseen-QA-",
    ),
    "DEMO_USTEC_CATALOG_SOURCE": (
        38284304699, "716996e0f893af0aeb2b990ac11d644cf62a5c5f",
        11762018327, "7f927792e575c5cccb9932c55a8db6733430c34629681701c6acd98491ac5c2e",
        "qore-native-G1-NAS100-USTEC-source-alias-catalog-only-",
    ),
    "DEMO_USTEC_INDEPENDENT_QA": (
        38301861733, "b163b37f5681abfae5cfb6a0a38890c7db14506b",
        11771250981, "ed60441604a5878d5aca7bcb4c710aba7f229d2a54b384c423fc3490ab071a0f",
        "alpha2-g2-original850-ustec-independent-catalog-QA-",
    ),
}
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _required_roster() -> None:
    if (
        len(MARKETS) != 33 or len(set(MARKETS)) != 33
        or set(ORIGINAL12) | set(NEW21) != set(MARKETS)
        or set(ORIGINAL12) & set(NEW21)
        or len(ORIGINAL12) != 12 or len(NEW21) != 21
        or set(SOURCE_29) != set(MARKETS) - EXCLUDED
        or len(SOURCE_29) != 29
    ):
        raise ValueError("G2_EXACT33_FROZEN_ROSTER_AND_SOURCE29_MISMATCH")


def _verify_one(name: str, run: Any, artifacts: Any) -> dict:
    rid, head, artifact_id, sha, prefix = RUNS[name]
    if (
        type(run) is not dict
        or type(run.get("id")) is not int or run["id"] != rid
        or run.get("head_sha") != head
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or type(run.get("run_attempt")) is not int
        or run["run_attempt"] != 1
    ):
        raise ValueError("G2_EXACT33_ORIGINAL_RUN_ID_HEAD_OR_SUCCESS_MISMATCH")
    if (
        type(artifacts) is not dict
        or type(artifacts.get("total_count")) is not int
        or artifacts["total_count"] != 1
        or type(artifacts.get("artifacts")) is not list
        or len(artifacts["artifacts"]) != 1
    ):
        raise ValueError("G2_EXACT33_GITHUB_ARTIFACT_LIST_NOT_SINGLE_COMPLETE")
    a = artifacts["artifacts"][0]
    if type(a) is not dict:
        raise ValueError("G2_EXACT33_ARTIFACT_INVALID")
    digest = "sha256:" + sha
    if (
        type(a.get("id")) is not int or a["id"] != artifact_id
        or a.get("name") != prefix + head
        or a.get("digest") != digest
        or re.fullmatch(r"sha256:[0-9a-f]{64}", str(a.get("digest"))) is None
        or HEX40.fullmatch(head) is None
        or a.get("expired") is not False
        or type(a.get("size_in_bytes")) is not int
        or a["size_in_bytes"] <= 0
    ):
        raise ValueError("G2_EXACT33_ARTIFACT_SHA_ID_NAME_EXPIRED_OR_BYTES_DRIFT")
    return {
        "run_id": rid, "exact_code_head": head,
        "artifact_id": artifact_id, "original_github_zip_sha256": digest,
        "original_github_artifact_bytes": a["size_in_bytes"],
        "artifact_expired_at_audit": False,
        "github_run_completed_success": True,
        "run_attempt": 1,
        "original_zip_prices_or_bytes_read_in_this_audit": False,
    }


def source_only_census(metadata: Any) -> dict:
    """Truthfully separate GitHub metadata SHA witness and economic identity."""
    _required_roster()
    if type(metadata) is not dict or set(metadata) != set(RUNS):
        raise ValueError("G2_EXACT33_SIX_RUNS_REQUIRED_NO_SUBSTITUTION")
    witnesses = {}
    for key in RUNS:
        entry = metadata[key]
        if type(entry) is not dict or set(entry) != {"run", "artifacts"}:
            raise ValueError("G2_EXACT33_RUN_ENTRY_SCHEMA_INVALID")
        witnesses[key] = _verify_one(key, entry["run"], entry["artifacts"])

    matrix = []
    for symbol in MARKETS:
        if symbol in SOURCE_29:
            evidence = "29_EXACT_DEMO_60S_SOURCE_SHA_WITNESS_ONLY"
            keys = ["DEMO_EXACT29_SOURCE", "DEMO_EXACT29_INDEPENDENT_QA"]
            provider = symbol
        elif symbol == "NZDUSD":
            evidence = "SEPARATE_DEMO_45S_SOURCE_SHA_WITNESS_ONLY"
            keys = ["DEMO_NZDUSD_SOURCE", "DEMO_NZDUSD_INDEPENDENT_QA"]
            provider = symbol
        elif symbol == "NAS100":
            evidence = "USTEC_CATALOG_ALIAS_METADATA_SHA_ONLY_NOT_EQUIVALENT"
            keys = ["DEMO_USTEC_CATALOG_SOURCE", "DEMO_USTEC_INDEPENDENT_QA"]
            provider = "USTEC"
        elif symbol == "SP500":
            evidence = "US500_REPORTED_HISTORICAL_ALIAS_NOT_CONTRACT_QA"
            keys = []
            provider = "US500"
        elif symbol == "XAGUSD":
            evidence = "HISTORICAL_SHORT_WINDOWS_REPORTED_NO_PROSPECTIVE_EXACT_QA"
            keys = []
            provider = symbol
        else:
            raise ValueError("G2_EXACT33_CANONICAL_UNKNOWN")
        matrix.append({
            "canonical_G0_symbol": symbol,
            "original_M5_cohort": (
                "ATLAS_ORIGINAL12" if symbol in ORIGINAL12 else "ICMARKETS_NEW21"
            ),
            "reported_provider_symbol_not_contract_equivalence": provider,
            "quote_or_catalog_source_evidence_class": evidence,
            "github_api_metadata_sha_witness_names": keys,
            "historical_atlas_account_contract_equivalence_proven": False,
            "broker_symbol_id_historical_validity_verified": False,
            "trade_value_per_point_in_deposit_currency_verified": False,
            "broker_fee_swap_financing_schedule_PIT_verified": False,
            "broker_historical_bidask_entry_and_exit_available_at_proven": False,
            "NEWS_PIT_verified": False,
            "broker_execution_contract_eligible": False,
            "NET_economic_edge_proven": False,
            "UTC001_certified": False,
        })

    if (
        len(matrix) != 33
        or len({row["canonical_G0_symbol"] for row in matrix}) != 33
        or sum(row["original_M5_cohort"] == "ATLAS_ORIGINAL12" for row in matrix) != 12
        or sum(row["original_M5_cohort"] == "ICMARKETS_NEW21" for row in matrix) != 21
        or sum(row["quote_or_catalog_source_evidence_class"] ==
               "29_EXACT_DEMO_60S_SOURCE_SHA_WITNESS_ONLY" for row in matrix) != 29
        or any(row["broker_execution_contract_eligible"] for row in matrix)
    ):
        raise ValueError("G2_EXACT33_CENSUS_COHORT_OR_ADMISSION_DRIFT")

    return {
        "identity": IDENTITY,
        "status": "G2_EXACT33_GITHUB_SOURCE_METADATA_VERIFIED_CONTRACTS_0_OF_33_BLOCKED",
        "original_G0_source33_manifest_sha256_reference_only": G0_SHA,
        "source_metadata_witnesses": witnesses,
        "rows": matrix,
        "exact_G0_symbols": 33,
        "original12": 12,
        "new21": 21,
        "simultaneous_demo_60s_quote_symbols": 29,
        "independent_separate_demo_45s_quote_symbols": 1,
        "alias_hints_not_equivalence": {"NAS100": "USTEC", "SP500": "US500"},
        "contract_eligible_count": 0,
        "SOURCE_ARCHIVED_PERMANENTLY": False,
        "historical_broker_equivalence_certified": False,
        "economic_NET_computed": False,
        "UTC001_certified": False,
        "original_quote_bytes_read": False,
        "broker_API_requests_made": 0,
        "broker_orders_submitted": 0,
        "new_strategy_parameter_search": False,
        "research_status": "W1_W2_W3_GROSS_NO_SUPPORT_FROZEN",
        "caution": (
            "Six GitHub run/artifact metadata witnesses only: source QA outcomes "
            "were performed previously and cannot establish historic account "
            "contract or fills. SP500/XAGUSD source claims are reported background "
            "and not independently reauthenticated by these six runs."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("github_metadata_dir", type=Path)
    p.add_argument("output_dir", type=Path)
    args = p.parse_args()
    data = {}
    for name, (rid, _, _, _, _) in RUNS.items():
        data[name] = {
            "run": json.loads(
                (args.github_metadata_dir / f"run-{rid}.json").read_text(
                    encoding="utf-8"
                )
            ),
            "artifacts": json.loads(
                (args.github_metadata_dir / f"artifacts-run-{rid}.json").read_text(
                    encoding="utf-8"
                )
            ),
        }
    result = source_only_census(data)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "alpha2-g2-p0-exact33-source-contract-matrix.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": result["status"],
        "original_symbols": result["exact_G0_symbols"],
        "six_original_runs": len(result["source_metadata_witnesses"]),
        "simultaneous_short_pilot": result["simultaneous_demo_60s_quote_symbols"],
        "contract_eligible": result["contract_eligible_count"],
        "broker_orders": result["broker_orders_submitted"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
