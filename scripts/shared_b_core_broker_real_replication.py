"""Real read-only Core/Broker observational replication for Architect B."""

from __future__ import annotations

import argparse
import gzip
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Any, cast

from qore.infrastructure.core_stack_v2.active_perception_post_v14_sensor_catalog import (
    freeze_enabled_provider_catalog,
    provider_catalog_sha256,
)
from qore.infrastructure.core_stack_v2.contracts import MarketEvent, freeze_facts
from qore.infrastructure.core_stack_v2.runtime import CoreStackV2Runtime
from qore.infrastructure.core_stack_v2.shared_b_core_broker_observability import (
    SharedBObservedSystemKind,
    SharedBObservedSystemState,
    SharedBSystemAssessment,
    SharedBSystemObservation,
    assess_system_observation,
)
from qore.infrastructure.ctrader_demo_lab_probe import (
    compute_ctrader_demo_lab_account_fingerprint,
)
from qore.infrastructure.ctrader_historical_tick_collector import (
    CTraderHistoricalReadOnlyMessageClient,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiPermissionScope,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

IDENTITY = "SHARED_B_CORE_BROKER_REAL_REPLICATION_001"


class SharedBCoreBrokerReplicationError(RuntimeError):
    """Real read-only Core/Broker replication failed closed."""


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise SharedBCoreBrokerReplicationError(
        f"missing required environment input: {name}"
    )


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SharedBCoreBrokerReplicationError(
            f"{path} must contain an object"
        )
    return cast(dict[str, Any], payload)


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise SharedBCoreBrokerReplicationError(f"{field} missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SharedBCoreBrokerReplicationError(
            f"{field} must be ISO timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SharedBCoreBrokerReplicationError(
            f"{field} must be timezone-aware"
        )
    return parsed.astimezone(UTC)


def _first_real_tick(
    *,
    raw_root: Path,
    raw_manifest: dict[str, Any],
) -> tuple[str, int, datetime, datetime]:
    candidates = raw_manifest.get("candidate_reports")
    if not isinstance(candidates, list):
        raise SharedBCoreBrokerReplicationError(
            "raw candidate reports missing"
        )
    for candidate_any in candidates:
        if not isinstance(candidate_any, dict):
            continue
        candidate = cast(dict[str, object], candidate_any)
        symbol = candidate.get("provider_symbol")
        symbol_id = candidate.get("provider_symbol_id")
        data_root = candidate.get("data_root")
        records = candidate.get("records")
        if (
            not isinstance(symbol, str)
            or type(symbol_id) is not int
            or not isinstance(data_root, str)
            or not isinstance(records, list)
        ):
            continue
        for record_any in records:
            if not isinstance(record_any, dict):
                continue
            record = cast(dict[str, object], record_any)
            count = record.get("tick_count")
            relative = record.get("relative_path")
            if type(count) is not int or count <= 0:
                continue
            if not isinstance(relative, str) or not relative:
                continue
            path = raw_root / data_root / relative
            try:
                text = gzip.decompress(path.read_bytes()).decode("utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise SharedBCoreBrokerReplicationError(
                    f"raw shard unreadable: {path}"
                ) from exc
            lines = [line for line in text.splitlines() if line]
            if len(lines) < 2:
                raise SharedBCoreBrokerReplicationError(
                    "positive raw shard omitted tick"
                )
            try:
                envelope = json.loads(lines[1])
            except json.JSONDecodeError as exc:
                raise SharedBCoreBrokerReplicationError(
                    "raw tick invalid JSON"
                ) from exc
            if not isinstance(envelope, dict) or set(envelope) != {"tick"}:
                raise SharedBCoreBrokerReplicationError(
                    "raw tick envelope invalid"
                )
            tick = envelope["tick"]
            if not isinstance(tick, dict):
                raise SharedBCoreBrokerReplicationError("raw tick invalid")
            provider_event_at = _aware(
                tick.get("provider_event_at"),
                field="provider_event_at",
            )
            retrieved_at = _aware(
                record.get("retrieved_at"),
                field="retrieved_at",
            )
            if provider_event_at > retrieved_at:
                raise SharedBCoreBrokerReplicationError(
                    "provider event postdates retrieval"
                )
            return symbol, symbol_id, provider_event_at, retrieved_at
    raise SharedBCoreBrokerReplicationError(
        "no sealed real cross-asset tick available"
    )


def _system_payload(
    assessment: SharedBSystemAssessment,
) -> dict[str, object]:
    item = assessment
    return {
        "system_id": item.system_id,
        "system_kind": item.system_kind.value,
        "state": item.state.value,
        "latency_ms": item.latency_ms,
        "data_integrity_bps": item.data_integrity_bps,
        "freshness_age_ms": item.freshness_age_ms,
        "error_count": item.error_count,
        "new_market_inference_allowed": item.new_market_inference_allowed,
        "relation_support_allowed": item.relation_support_allowed,
        "reason_codes": list(item.reason_codes),
        "fingerprint_sha256": item.fingerprint(),
        "mutation_authority": item.mutation_authority,
        "restart_authority": item.restart_authority,
        "order_authority": item.order_authority,
        "risk_authority": item.risk_authority,
        "sizing_authority": item.sizing_authority,
        "capital_authority": item.capital_authority,
    }


def run(
    *,
    raw_root: Path,
    raw_manifest_path: Path,
    expected_catalog_sha256: str,
    output_path: Path,
) -> dict[str, object]:
    raw_manifest = _load(raw_manifest_path)
    if raw_manifest.get("target_or_outcome_read") is not False:
        raise SharedBCoreBrokerReplicationError(
            "raw source evidence used target/outcome"
        )
    if raw_manifest.get("fresh_holdout_opened") is not False:
        raise SharedBCoreBrokerReplicationError(
            "raw source evidence opened holdout"
        )

    symbol, symbol_id, event_at, retrieved_at = _first_real_tick(
        raw_root=raw_root,
        raw_manifest=raw_manifest,
    )

    event = MarketEvent(
        event_id=f"shared-b-real-{symbol}-{symbol_id}",
        market=symbol,
        event_type="SEALED_PROVIDER_TICK",
        source_at=event_at,
        observed_at=retrieved_at,
        sequence=1,
        complete=True,
        timeframe_seconds=None,
        facts=freeze_facts(
            {
                "market_state": "HISTORICAL_SOURCE_OBSERVED",
                "provider_symbol": symbol,
                "structure_state": "RAW_TICK_EVIDENCE",
            }
        ),
    )
    runtime = CoreStackV2Runtime()
    core_started = monotonic()
    core_result = runtime.ingest(event, generated_at=retrieved_at)
    core_latency_ms = max(0, round((monotonic() - core_started) * 1000))
    checkpoint = runtime.checkpoint(symbol)
    rebuilt = CoreStackV2Runtime.from_checkpoint(checkpoint).rebuild(
        market=symbol,
        generated_at=retrieved_at,
    )
    deterministic_core = (
        rebuilt.fingerprint() == core_result.snapshot.fingerprint()
    )
    if not deterministic_core:
        raise SharedBCoreBrokerReplicationError(
            "Core runtime replay fingerprint drift"
        )

    credentials = CTraderOpenApiCredentials(
        client_id=_required_env(
            "QORE_CTRADER_CLIENT_ID",
            "QORE_CTRADER_DEMO_CLIENT_ID",
        ),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET",
            "QORE_CTRADER_DEMO_CLIENT_SECRET",
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN",
            "QORE_CTRADER_DEMO_ACCESS_TOKEN",
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN",
            "QORE_CTRADER_DEMO_REFRESH_TOKEN",
        ),
        ctid_trader_account_id=int(
            _required_env(
                "QORE_CTRADER_DEMO_ACCOUNT_ID",
                "QORE_CTRADER_ACCOUNT_ID",
            )
        ),
    )
    native = SpotwareCTraderOpenApiClient(
        credentials=credentials,
        required_permission_scope=CTraderOpenApiPermissionScope.TRADE,
    )
    client = CTraderHistoricalReadOnlyMessageClient(native)

    try:
        auth_started = monotonic()
        ready = client.connect_and_authenticate()
        auth_latency_ms = max(0, round((monotonic() - auth_started) * 1000))
        if isinstance(ready, Failure):
            raise SharedBCoreBrokerReplicationError(
                "cTrader DEMO read-only authentication failed"
            )

        request_started = monotonic()
        listed = client.request(
            "ProtoOASymbolsListReq",
            {
                "ctidTraderAccountId": client.account_id,
                "includeArchivedSymbols": False,
            },
            client_msg_id="shared-b-core-broker-real-replication",
            timeout_seconds=20.0,
        )
        provider_latency_ms = max(
            0,
            round((monotonic() - request_started) * 1000),
        )
        if isinstance(listed, Failure):
            raise SharedBCoreBrokerReplicationError(
                "cTrader DEMO symbol catalogue request failed"
            )
        native_symbols = getattr(listed.value, "symbol", None)
        if native_symbols is None:
            raise SharedBCoreBrokerReplicationError(
                "cTrader DEMO symbol catalogue missing"
            )
        rows: list[tuple[int, str, bool]] = []
        for item in native_symbols:
            if getattr(item, "enabled", None) is not True:
                continue
            item_id = getattr(item, "symbolId", None)
            item_name = getattr(item, "symbolName", None)
            if type(item_id) is not int or not isinstance(item_name, str):
                raise SharedBCoreBrokerReplicationError(
                    "provider symbol identity invalid"
                )
            rows.append((item_id, item_name, True))
        entries = freeze_enabled_provider_catalog(tuple(rows))
        current_catalog_sha256 = provider_catalog_sha256(entries)
        catalog_matches_frozen = (
            current_catalog_sha256 == expected_catalog_sha256
        )
        integrity_bps = 10_000 if catalog_matches_frozen else 0
        account_fingerprint = (
            compute_ctrader_demo_lab_account_fingerprint(client.account_id)
        )

        observed_at = datetime.now(UTC)
        thresholds = {
            "latency_degraded_threshold_ms": 5_000,
            "integrity_degraded_threshold_bps": 10_000,
            "freshness_degraded_threshold_ms": 60_000,
        }
        provider_assessment = assess_system_observation(
            SharedBSystemObservation(
                system_id="CTRADER_DEMO_PROVIDER",
                system_kind=SharedBObservedSystemKind.PROVIDER,
                observed_at=observed_at,
                evidence_cutoff_at=observed_at,
                availability_known=True,
                available=True,
                latency_ms=provider_latency_ms,
                data_integrity_bps=integrity_bps,
                freshness_age_ms=0,
                error_count=0,
                provenance_refs=(
                    f"provider-catalog:{current_catalog_sha256}",
                ),
            ),
            **thresholds,
        )
        broker_assessment = assess_system_observation(
            SharedBSystemObservation(
                system_id="CTRADER_DEMO_ACCOUNT",
                system_kind=SharedBObservedSystemKind.BROKER,
                observed_at=observed_at,
                evidence_cutoff_at=observed_at,
                availability_known=True,
                available=True,
                latency_ms=auth_latency_ms,
                data_integrity_bps=10_000,
                freshness_age_ms=0,
                error_count=0,
                provenance_refs=(
                    f"account-fingerprint:{account_fingerprint}",
                ),
            ),
            **thresholds,
        )
        core_assessment = assess_system_observation(
            SharedBSystemObservation(
                system_id="QORE_CORE_STACK_V2_RUNTIME",
                system_kind=SharedBObservedSystemKind.CORE_COMPONENT,
                observed_at=observed_at,
                evidence_cutoff_at=observed_at,
                availability_known=True,
                available=True,
                latency_ms=core_latency_ms,
                data_integrity_bps=10_000,
                freshness_age_ms=0,
                error_count=0,
                provenance_refs=(
                    f"core-checkpoint:{checkpoint.fingerprint()}",
                    f"source-event:{event.fingerprint()}",
                ),
            ),
            **thresholds,
        )
    finally:
        client.close()

    assessments = (
        provider_assessment,
        broker_assessment,
        core_assessment,
    )
    if any(
        item.state is SharedBObservedSystemState.UNKNOWN
        for item in assessments
    ):
        raise SharedBCoreBrokerReplicationError(
            "real observed system unexpectedly remained UNKNOWN"
        )

    report: dict[str, object] = {
        "identity": IDENTITY,
        "status": "REAL_READ_ONLY_CORE_BROKER_REPLICATION_PASS",
        "source_provider_symbol": symbol,
        "source_provider_symbol_id": symbol_id,
        "source_provider_event_at": event_at.isoformat(
            timespec="microseconds"
        ),
        "source_retrieved_at": retrieved_at.isoformat(
            timespec="microseconds"
        ),
        "core_runtime_executed": True,
        "core_runtime_deterministic_rebuild": deterministic_core,
        "core_snapshot_fingerprint_sha256": (
            core_result.snapshot.fingerprint()
        ),
        "core_checkpoint_fingerprint_sha256": checkpoint.fingerprint(),
        "current_provider_catalog_sha256": current_catalog_sha256,
        "expected_provider_catalog_sha256": expected_catalog_sha256,
        "provider_catalog_matches_frozen": catalog_matches_frozen,
        "enabled_symbol_count": len(entries),
        "account_fingerprint": account_fingerprint,
        "system_assessments": [
            _system_payload(item)
            for item in assessments
        ],
        "read_only_message_firewall": True,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "restart_authority": False,
        "order_authority": False,
        "risk_authority": False,
        "sizing_authority": False,
        "capital_authority": False,
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
    parser.add_argument("--expected-catalog-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(
        raw_root=args.raw_root,
        raw_manifest_path=args.raw_manifest,
        expected_catalog_sha256=args.expected_catalog_sha256,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "provider_catalog_matches_frozen": report[
                    "provider_catalog_matches_frozen"
                ],
                "enabled_symbol_count": report["enabled_symbol_count"],
                "states": [
                    item["state"]
                    for item in cast(
                        list[dict[str, object]],
                        report["system_assessments"],
                    )
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
