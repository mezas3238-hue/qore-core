"""Offline reducer for sealed Architect-B cross-asset availability evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_cross_asset_source_replay import (
    FROZEN_PILOT_INDICES,
    SHARED_B_CROSS_ASSET_RAW_IDENTITY,
    SHARED_B_CROSS_ASSET_REPLAY_IDENTITY,
    VerifiedShard,
    classify_verified_window_counts,
    raw_dataset_digest,
    verify_historical_quote_shard,
)


class SharedBCrossAssetReduceError(ValueError):
    """Sealed Architect-B source evidence cannot be reduced safely."""


def _load(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SharedBCrossAssetReduceError("raw manifest must be a JSON object")
    return cast(dict[str, Any], raw)


def _candidate_result(
    *,
    root: Path,
    candidate: dict[str, object],
) -> dict[str, object]:
    symbol = candidate.get("provider_symbol")
    symbol_id = candidate.get("provider_symbol_id")
    role = candidate.get("semantic_role")
    if not isinstance(symbol, str) or not symbol:
        raise SharedBCrossAssetReduceError("provider symbol missing")
    if type(symbol_id) is not int or symbol_id <= 0:
        raise SharedBCrossAssetReduceError("provider symbol id invalid")
    if not isinstance(role, str) or not role:
        raise SharedBCrossAssetReduceError("semantic role missing")

    data_root = candidate.get("data_root")
    records = candidate.get("records")
    technical_error = candidate.get("technical_error")
    if technical_error not in (True, False):
        raise SharedBCrossAssetReduceError("technical_error must be bool")
    if records is None:
        records = []
    if not isinstance(records, list):
        raise SharedBCrossAssetReduceError("candidate records must be a list")
    if records and not isinstance(data_root, str):
        raise SharedBCrossAssetReduceError("candidate data_root missing")

    verified: list[VerifiedShard] = []
    for item in records:
        if not isinstance(item, dict):
            raise SharedBCrossAssetReduceError("raw shard record invalid")
        relative = item.get("relative_path")
        if not isinstance(relative, str) or not relative:
            raise SharedBCrossAssetReduceError("raw shard path invalid")
        verified.append(
            verify_historical_quote_shard(
                path=root / cast(str, data_root) / relative,
                expected=item,
            )
        )

    counts: dict[int, dict[str, int]] = {
        index: {"BID": 0, "ASK": 0}
        for index in FROZEN_PILOT_INDICES
    }
    seen_pages: set[tuple[str, int, int]] = set()
    for shard in verified:
        if shard.window_index not in counts:
            raise SharedBCrossAssetReduceError(
                "raw shard escaped frozen pilot windows"
            )
        key = (shard.quote_side, shard.window_index, shard.page_index)
        if key in seen_pages:
            raise SharedBCrossAssetReduceError(
                "duplicate raw shard page identity"
            )
        seen_pages.add(key)
        counts[shard.window_index][shard.quote_side] += shard.tick_count

    if technical_error:
        coverage_status = "technical_error"
    else:
        for index in FROZEN_PILOT_INDICES:
            for side in ("BID", "ASK"):
                if not any(
                    shard.window_index == index and shard.quote_side == side
                    for shard in verified
                ):
                    raise SharedBCrossAssetReduceError(
                        "successful acquisition omitted a BID/ASK raw page"
                    )
        coverage_status = classify_verified_window_counts(counts).value

    digest = raw_dataset_digest(
        provider_symbol=symbol,
        shards=verified,
    )
    claimed_digest = candidate.get("raw_dataset_sha256")
    if not technical_error and claimed_digest != digest:
        raise SharedBCrossAssetReduceError(
            f"raw dataset digest mismatch for {symbol}"
        )

    return {
        "semantic_role": role,
        "provider_symbol": symbol,
        "provider_symbol_id": symbol_id,
        "provider_digits": candidate.get("provider_digits"),
        "account_fingerprint": candidate.get("account_fingerprint"),
        "coverage_status": coverage_status,
        "raw_dataset_sha256": digest,
        "window_counts": [
            {
                "manifest_index": index,
                "bid_tick_count": counts[index]["BID"],
                "ask_tick_count": counts[index]["ASK"],
            }
            for index in FROZEN_PILOT_INDICES
        ],
    }


def reduce_raw(
    *,
    raw_root: Path,
    raw_manifest_path: Path,
    output_path: Path,
) -> dict[str, object]:
    payload = _load(raw_manifest_path)
    if payload.get("identity") != SHARED_B_CROSS_ASSET_RAW_IDENTITY:
        raise SharedBCrossAssetReduceError("raw evidence identity mismatch")
    if payload.get("partition") != "r8_source_only":
        raise SharedBCrossAssetReduceError("raw evidence partition mismatch")
    if payload.get("selected_manifest_indices") != list(
        FROZEN_PILOT_INDICES
    ):
        raise SharedBCrossAssetReduceError("frozen pilot indices drifted")
    for key in (
        "target_or_outcome_read",
        "r6_r5_read",
        "fresh_holdout_opened",
        "scientific_v15_opened",
        "broker_mutation",
        "shared_methodology_authority",
        "shared_sizing_authority",
        "shared_risk_authority",
        "shared_order_authority",
        "shared_execution_authority",
    ):
        if payload.get(key) is not False:
            raise SharedBCrossAssetReduceError(
                f"source governance violation: {key}"
            )
    if payload.get("read_only_message_firewall") is not True:
        raise SharedBCrossAssetReduceError(
            "read-only provider firewall missing"
        )

    candidates = payload.get("candidate_reports")
    if not isinstance(candidates, list) or len(candidates) != 3:
        raise SharedBCrossAssetReduceError(
            "expected exact three frozen cross-asset candidates"
        )
    reduced = [
        _candidate_result(root=raw_root, candidate=cast(dict[str, object], item))
        for item in candidates
        if isinstance(item, dict)
    ]
    if len(reduced) != len(candidates):
        raise SharedBCrossAssetReduceError("candidate report invalid")

    report: dict[str, object] = {
        "identity": SHARED_B_CROSS_ASSET_REPLAY_IDENTITY,
        "partition": "r8_source_only",
        "source_manifest_sha256": payload.get("source_manifest_sha256"),
        "provider_catalog_sha256": payload.get("provider_catalog_sha256"),
        "selected_manifest_indices": list(FROZEN_PILOT_INDICES),
        "candidate_reports": reduced,
        "replay_requires_provider": False,
        "raw_evidence_verified": True,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "scientific_v15_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--raw-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = reduce_raw(
        raw_root=args.raw_root,
        raw_manifest_path=args.raw_manifest,
        output_path=args.output,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
