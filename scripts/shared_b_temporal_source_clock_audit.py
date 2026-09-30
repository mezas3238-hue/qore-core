"""Audit source-clock integrity on sealed Architect-B cross-asset evidence."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_cross_asset_source_replay import (
    SHARED_B_CROSS_ASSET_RAW_IDENTITY,
    verify_historical_quote_shard,
)

IDENTITY = "SHARED_B_TEMPORAL_SOURCE_CLOCK_INTEGRITY_001"


class SharedBTemporalClockAuditError(ValueError):
    """Sealed source clock evidence failed closed."""


def _load(path: Path) -> dict[str, Any]:
    payload=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload,dict):
        raise SharedBTemporalClockAuditError(f"{path} must contain an object")
    return cast(dict[str,Any],payload)


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value,str):
        raise SharedBTemporalClockAuditError(f"{field} missing")
    try:
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise SharedBTemporalClockAuditError(
            f"{field} must be ISO timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SharedBTemporalClockAuditError(
            f"{field} must be timezone-aware"
        )
    return parsed.astimezone(UTC)


def _sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",",":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _audit_shard(
    *,
    path: Path,
    record: dict[str, object],
) -> dict[str, object]:
    verified=verify_historical_quote_shard(
        path=path,
        expected=record,
    )
    try:
        raw=gzip.decompress(path.read_bytes()).decode("utf-8")
    except (OSError,UnicodeDecodeError) as exc:
        raise SharedBTemporalClockAuditError(
            f"cannot decode sealed shard: {path}"
        ) from exc
    lines=[line for line in raw.splitlines() if line]
    if not lines:
        raise SharedBTemporalClockAuditError("sealed shard empty")
    try:
        header_envelope=json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise SharedBTemporalClockAuditError(
            "sealed shard header JSON invalid"
        ) from exc
    if (
        not isinstance(header_envelope,dict)
        or set(header_envelope)!={"header"}
        or not isinstance(header_envelope["header"],dict)
    ):
        raise SharedBTemporalClockAuditError(
            "sealed shard header envelope invalid"
        )
    header=cast(dict[str,object],header_envelope["header"])
    retrieved_at=_aware(
        header.get("retrieved_at"),
        field="retrieved_at",
    )
    record_retrieved_at=_aware(
        record.get("retrieved_at"),
        field="manifest.retrieved_at",
    )
    if retrieved_at != record_retrieved_at:
        raise SharedBTemporalClockAuditError(
            "raw header/manifest retrieval clock drift"
        )

    tick_count=0
    strict_past_count=0
    equal_clock_count=0
    max_retrieval_lag_ms=0
    min_retrieval_lag_ms: int | None=None
    first_provider_event_at: datetime | None=None
    last_provider_event_at: datetime | None=None
    previous: datetime | None=None

    for line in lines[1:]:
        try:
            envelope=json.loads(line)
        except json.JSONDecodeError as exc:
            raise SharedBTemporalClockAuditError(
                "sealed tick JSON invalid"
            ) from exc
        if (
            not isinstance(envelope,dict)
            or set(envelope)!={"tick"}
            or not isinstance(envelope["tick"],dict)
        ):
            raise SharedBTemporalClockAuditError(
                "sealed tick envelope invalid"
            )
        tick=cast(dict[str,object],envelope["tick"])
        provider_event_at=_aware(
            tick.get("provider_event_at"),
            field="provider_event_at",
        )
        if provider_event_at > retrieved_at:
            raise SharedBTemporalClockAuditError(
                "provider event postdates retrieval"
            )
        if previous is not None and provider_event_at < previous:
            raise SharedBTemporalClockAuditError(
                "provider events out of order"
            )
        previous=provider_event_at
        lag_ms=int(
            (retrieved_at-provider_event_at).total_seconds()*1000
        )
        if lag_ms < 0:
            raise SharedBTemporalClockAuditError(
                "negative retrieval lag"
            )
        max_retrieval_lag_ms=max(max_retrieval_lag_ms,lag_ms)
        min_retrieval_lag_ms=(
            lag_ms
            if min_retrieval_lag_ms is None
            else min(min_retrieval_lag_ms,lag_ms)
        )
        if lag_ms == 0:
            equal_clock_count+=1
        else:
            strict_past_count+=1
        first_provider_event_at=(
            provider_event_at
            if first_provider_event_at is None
            else min(first_provider_event_at,provider_event_at)
        )
        last_provider_event_at=(
            provider_event_at
            if last_provider_event_at is None
            else max(last_provider_event_at,provider_event_at)
        )
        tick_count+=1

    if tick_count != verified.tick_count:
        raise SharedBTemporalClockAuditError(
            "verified/raw tick count drift"
        )
    return {
        "quote_side":verified.quote_side,
        "window_index":verified.window_index,
        "page_index":verified.page_index,
        "retrieved_at":retrieved_at.isoformat(timespec="microseconds"),
        "tick_count":tick_count,
        "strict_past_provider_event_count":strict_past_count,
        "equal_provider_retrieval_clock_count":equal_clock_count,
        "min_retrieval_lag_ms":min_retrieval_lag_ms,
        "max_retrieval_lag_ms":max_retrieval_lag_ms,
        "first_provider_event_at":(
            None
            if first_provider_event_at is None
            else first_provider_event_at.isoformat(timespec="microseconds")
        ),
        "last_provider_event_at":(
            None
            if last_provider_event_at is None
            else last_provider_event_at.isoformat(timespec="microseconds")
        ),
        "content_sha256":verified.content_sha256,
        "provenance_sha256":verified.provenance_sha256,
        "relative_path":verified.relative_path,
    }


def run(
    *,
    raw_root: Path,
    raw_manifest_path: Path,
    output_path: Path,
) -> dict[str, object]:
    manifest=_load(raw_manifest_path)
    if manifest.get("identity") != SHARED_B_CROSS_ASSET_RAW_IDENTITY:
        raise SharedBTemporalClockAuditError(
            "unexpected raw evidence identity"
        )
    if manifest.get("partition") != "r8_source_only":
        raise SharedBTemporalClockAuditError(
            "unexpected raw evidence partition"
        )
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
        if manifest.get(key) is not False:
            raise SharedBTemporalClockAuditError(
                f"upstream governance violation: {key}"
            )

    candidates=manifest.get("candidate_reports")
    if not isinstance(candidates,list):
        raise SharedBTemporalClockAuditError(
            "candidate reports missing"
        )

    sensor_reports: list[dict[str,object]]=[]
    global_tick_count=0
    global_shard_count=0
    global_strict_past_count=0
    global_equal_clock_count=0
    for candidate_any in candidates:
        if not isinstance(candidate_any,dict):
            raise SharedBTemporalClockAuditError(
                "candidate report invalid"
            )
        candidate=cast(dict[str,object],candidate_any)
        symbol=candidate.get("provider_symbol")
        symbol_id=candidate.get("provider_symbol_id")
        records=candidate.get("records")
        data_root=candidate.get("data_root")
        if (
            not isinstance(symbol,str)
            or not symbol
            or type(symbol_id) is not int
            or symbol_id <= 0
        ):
            raise SharedBTemporalClockAuditError(
                "candidate provider identity invalid"
            )
        if records is None:
            records=[]
        if not isinstance(records,list):
            raise SharedBTemporalClockAuditError(
                "candidate raw records invalid"
            )

        shard_reports: list[dict[str,object]]=[]
        if records:
            if not isinstance(data_root,str) or not data_root:
                raise SharedBTemporalClockAuditError(
                    "candidate raw data_root missing"
                )
            for record_any in records:
                if not isinstance(record_any,dict):
                    raise SharedBTemporalClockAuditError(
                        "raw record invalid"
                    )
                record=cast(dict[str,object],record_any)
                relative=record.get("relative_path")
                if not isinstance(relative,str) or not relative:
                    raise SharedBTemporalClockAuditError(
                        "raw relative_path missing"
                    )
                row=_audit_shard(
                    path=raw_root/data_root/relative,
                    record=record,
                )
                shard_reports.append(row)
                global_shard_count+=1
                global_tick_count+=int(cast(int,row["tick_count"]))
                global_strict_past_count+=int(
                    cast(int,row["strict_past_provider_event_count"])
                )
                global_equal_clock_count+=int(
                    cast(int,row["equal_provider_retrieval_clock_count"])
                )

        sensor_tick_count=sum(
            int(cast(int,row["tick_count"]))
            for row in shard_reports
        )
        sensor_reports.append({
            "provider_symbol":symbol,
            "provider_symbol_id":symbol_id,
            "technical_error":candidate.get("technical_error"),
            "sealed_shard_count":len(shard_reports),
            "tick_count":sensor_tick_count,
            "provider_event_after_retrieval_count":0,
            "shards":shard_reports,
        })

    if global_shard_count <= 0 or global_tick_count <= 0:
        raise SharedBTemporalClockAuditError(
            "temporal clock audit requires non-empty real evidence"
        )
    if global_strict_past_count+global_equal_clock_count != global_tick_count:
        raise SharedBTemporalClockAuditError(
            "clock partition count mismatch"
        )

    payload: dict[str,object]={
        "identity":IDENTITY,
        "status":"SEALED_SOURCE_CLOCK_INTEGRITY_PASS",
        "source_identity":manifest["identity"],
        "source_manifest_sha256":manifest.get("source_manifest_sha256"),
        "provider_catalog_sha256":manifest.get("provider_catalog_sha256"),
        "sensor_count":len(sensor_reports),
        "sealed_shard_count":global_shard_count,
        "tick_count":global_tick_count,
        "provider_event_after_retrieval_count":0,
        "strict_past_provider_event_count":global_strict_past_count,
        "equal_provider_retrieval_clock_count":global_equal_clock_count,
        "provider_event_retrieval_clock_separation_pass":True,
        "future_provider_event_rejected":True,
        "raw_shard_monotonicity_pass":True,
        "historical_retrieval_proves_past_point_in_time_availability":False,
        "historical_retrieval_can_reset_market_freshness":False,
        "causal_historical_use_authorized":False,
        "canonical_market_hours_resolved":False,
        "relational_comparability_authorized":False,
        "sensor_reports":sensor_reports,
        "target_or_outcome_read":False,
        "r6_r5_read":False,
        "fresh_holdout_opened":False,
        "broker_mutation":False,
        "productive_authority":False,
    }
    payload["audit_fingerprint_sha256"]=_sha(payload)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(
        json.dumps(payload,sort_keys=True,indent=2)+"\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--raw-root",type=Path,required=True)
    parser.add_argument("--raw-manifest",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    payload=run(
        raw_root=args.raw_root,
        raw_manifest_path=args.raw_manifest,
        output_path=args.output,
    )
    print(json.dumps({
        "status":payload["status"],
        "sensor_count":payload["sensor_count"],
        "sealed_shard_count":payload["sealed_shard_count"],
        "tick_count":payload["tick_count"],
        "provider_event_after_retrieval_count":payload[
            "provider_event_after_retrieval_count"
        ],
    },sort_keys=True))


if __name__=="__main__":
    main()
