"""Acquire sealed raw pages for Architect-B cross-asset availability replay."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, sleep
from typing import Any, cast
from uuid import UUID

from qore.infrastructure.core_stack_v2.active_perception_post_v14_cross_asset_availability import (
    FROZEN_CROSS_ASSET_CANDIDATES,
    validate_candidates_against_catalog,
)
from qore.infrastructure.core_stack_v2.active_perception_v12_coverage_pilot import (
    select_v12_temporal_coverage_pilot,
)
from qore.infrastructure.core_stack_v2.shared_b_cross_asset_source_replay import (
    FROZEN_PILOT_INDICES,
    SHARED_B_CROSS_ASSET_RAW_IDENTITY,
)
from qore.infrastructure.ctrader_demo_lab_probe import (
    compute_ctrader_demo_lab_account_fingerprint,
)
from qore.infrastructure.ctrader_historical_tick_collector import (
    CTraderHistoricalReadOnlyMessageClient,
    CTraderHistoricalSensorIdentity,
    resolve_ctrader_historical_sensor_identity,
    split_historical_request_windows,
)
from qore.infrastructure.ctrader_historical_tick_data import (
    CTraderHistoricalTickReader,
    CTraderHistoricalTickRequest,
    CTraderQuoteType,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiPermissionScope,
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.historical_quote_side_evidence import (
    retain_ctrader_historical_quote_side_page,
)
from qore.infrastructure.historical_quote_side_shards import (
    HistoricalQuoteSideShardRecord,
    HistoricalQuoteSideShardSink,
    historical_shard_dataset_digest,
)
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import MarketPriceSide
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.kernel.result import Failure

EXPECTED_MANIFEST_IDENTITY = (
    "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_ACQUISITION_MANIFEST_001"
)
REQUEST_INTERVAL_SECONDS = 0.21
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("7e000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("7e000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo-historical"),
)


class SharedBCrossAssetAcquireError(RuntimeError):
    """Architect-B source-only cross-asset acquisition failed closed."""


@dataclass(frozen=True, slots=True)
class _SideStats:
    count: int
    page_count: int
    first_at: datetime | None
    last_at: datetime | None
    records: tuple[HistoricalQuoteSideShardRecord, ...]
    technical_error: bool


class _RateLimiter:
    def __init__(self) -> None:
        self._last_request_started: float | None = None

    def wait(self) -> None:
        now = monotonic()
        if self._last_request_started is not None:
            remaining = REQUEST_INTERVAL_SECONDS - (
                now - self._last_request_started
            )
            if remaining > 0:
                sleep(remaining)
        self._last_request_started = monotonic()


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise SharedBCrossAssetAcquireError(
        f"missing required environment input: {name}"
    )


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SharedBCrossAssetAcquireError(
            f"{path} must contain a JSON object"
        )
    return cast(dict[str, Any], raw)


def _record_payload(record: HistoricalQuoteSideShardRecord) -> dict[str, object]:
    return {
        "quote_side": record.quote_side.value,
        "window_index": record.window_index,
        "page_index": record.page_index,
        "request_from_at": _iso(record.request_from_at),
        "request_to_at": _iso(record.request_to_at),
        "retrieved_at": _iso(record.retrieved_at),
        "tick_count": record.tick_count,
        "first_provider_event_at": _iso(record.first_provider_event_at),
        "last_provider_event_at": _iso(record.last_provider_event_at),
        "content_sha256": record.content_sha256,
        "provenance_sha256": record.provenance_sha256,
        "relative_path": record.relative_path,
    }


def _collect_side(
    *,
    reader: CTraderHistoricalTickReader,
    sink: HistoricalQuoteSideShardSink,
    limiter: _RateLimiter,
    identity: CTraderHistoricalSensorIdentity,
    instrument: Instrument,
    manifest_index: int,
    from_at: datetime,
    to_at: datetime,
    quote_type: CTraderQuoteType,
) -> _SideStats:
    records: list[HistoricalQuoteSideShardRecord] = []
    count = 0
    page_count = 0
    first_at: datetime | None = None
    last_at: datetime | None = None
    page_ordinal = 0

    for segment in split_historical_request_windows(
        from_at=from_at,
        to_at=to_at,
    ):
        page_to_at = segment.to_at
        while True:
            limiter.wait()
            request = CTraderHistoricalTickRequest(
                account_id=identity.account_id,
                symbol_id=identity.symbol_id,
                quote_type=quote_type,
                from_at=segment.from_at,
                to_at=page_to_at,
            )
            result = reader.read_page(
                request=request,
                digits=identity.digits,
                client_msg_id=(
                    "shared-b-cross-asset-availability-"
                    f"{identity.symbol_id}-{manifest_index}-"
                    f"{quote_type.name.lower()}-{page_ordinal}"
                ),
            )
            if isinstance(result, Failure):
                return _SideStats(
                    count=count,
                    page_count=page_count,
                    first_at=first_at,
                    last_at=last_at,
                    records=tuple(records),
                    technical_error=True,
                )

            page = result.value
            retrieved_at = datetime.now(UTC)
            observations = retain_ctrader_historical_quote_side_page(
                page=page,
                instrument=instrument,
                source=_SOURCE,
                provider_symbol=identity.provider_symbol,
                retrieved_at=retrieved_at,
            )
            side = (
                MarketPriceSide.BID
                if quote_type is CTraderQuoteType.BID
                else MarketPriceSide.ASK
            )
            records.append(
                sink.write_page(
                    quote_side=side,
                    window_index=manifest_index,
                    page_index=page_ordinal,
                    request_from_at=request.from_at,
                    request_to_at=request.to_at,
                    retrieved_at=retrieved_at,
                    observations=observations,
                )
            )
            count += len(observations)
            page_count += 1
            if observations:
                observed_first = observations[0].provider_event_at
                observed_last = observations[-1].provider_event_at
                if first_at is None or observed_first < first_at:
                    first_at = observed_first
                if last_at is None or observed_last > last_at:
                    last_at = observed_last

            next_to_at = page.next_older_to_at
            page_ordinal += 1
            if next_to_at is None:
                break
            if next_to_at <= segment.from_at or next_to_at >= page_to_at:
                raise SharedBCrossAssetAcquireError(
                    "historical pagination made no legal backward progress"
                )
            page_to_at = next_to_at

    return _SideStats(
        count=count,
        page_count=page_count,
        first_at=first_at,
        last_at=last_at,
        records=tuple(records),
        technical_error=False,
    )


def run(
    *,
    manifest_path: Path,
    catalog_path: Path,
    output_dir: Path,
    expected_manifest_sha256: str,
    expected_catalog_sha256: str,
) -> dict[str, object]:
    manifest = _load_json(manifest_path)
    catalog = _load_json(catalog_path)
    if manifest.get("identity") != EXPECTED_MANIFEST_IDENTITY:
        raise SharedBCrossAssetAcquireError(
            "unexpected source-manifest identity"
        )
    if manifest.get("partition") != "r8":
        raise SharedBCrossAssetAcquireError(
            "B acquisition is restricted to R8 source windows"
        )
    if manifest.get("manifest_sha256") != expected_manifest_sha256:
        raise SharedBCrossAssetAcquireError("source-manifest digest mismatch")
    if catalog.get("provider_catalog_sha256") != expected_catalog_sha256:
        raise SharedBCrossAssetAcquireError("provider-catalog digest mismatch")
    rows = catalog.get("enabled_symbols")
    if not isinstance(rows, list):
        raise SharedBCrossAssetAcquireError(
            "provider catalog omitted enabled symbols"
        )
    validate_candidates_against_catalog(cast(list[dict[str, object]], rows))

    raw_windows = manifest.get("windows")
    if not isinstance(raw_windows, list):
        raise SharedBCrossAssetAcquireError("source manifest omitted windows")
    selected = select_v12_temporal_coverage_pilot(raw_windows)
    if tuple(item.manifest_index for item in selected) != FROZEN_PILOT_INDICES:
        raise SharedBCrossAssetAcquireError("frozen pilot indices drifted")

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
    limiter = _RateLimiter()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise SharedBCrossAssetAcquireError(
                "cTrader DEMO authentication failed"
            )

        candidate_reports: list[dict[str, object]] = []
        for candidate in FROZEN_CROSS_ASSET_CANDIDATES:
            identity_result = resolve_ctrader_historical_sensor_identity(
                client=client,
                provider_symbol=candidate.provider_symbol,
                timeout_seconds=10.0,
            )
            if isinstance(identity_result, Failure):
                candidate_reports.append(
                    {
                        "semantic_role": candidate.semantic_role,
                        "provider_symbol": candidate.provider_symbol,
                        "provider_symbol_id": candidate.provider_symbol_id,
                        "technical_error": True,
                        "records": [],
                        "window_reports": [],
                    }
                )
                continue

            identity = identity_result.value
            if identity.symbol_id != candidate.provider_symbol_id:
                raise SharedBCrossAssetAcquireError(
                    f"provider symbol id drift for {candidate.provider_symbol}"
                )
            data_root = Path(candidate.provider_symbol) / "data"
            sink = HistoricalQuoteSideShardSink(output_dir / data_root)
            reader = CTraderHistoricalTickReader(
                client=client,
                timeout_seconds=20.0,
            )
            instrument = Instrument(candidate.provider_symbol)
            all_records: list[HistoricalQuoteSideShardRecord] = []
            window_reports: list[dict[str, object]] = []
            technical_error = False

            for window in selected:
                bid = _collect_side(
                    reader=reader,
                    sink=sink,
                    limiter=limiter,
                    identity=identity,
                    instrument=instrument,
                    manifest_index=window.manifest_index,
                    from_at=window.from_at,
                    to_at=window.to_at,
                    quote_type=CTraderQuoteType.BID,
                )
                ask = _collect_side(
                    reader=reader,
                    sink=sink,
                    limiter=limiter,
                    identity=identity,
                    instrument=instrument,
                    manifest_index=window.manifest_index,
                    from_at=window.from_at,
                    to_at=window.to_at,
                    quote_type=CTraderQuoteType.ASK,
                )
                technical_error = (
                    technical_error
                    or bid.technical_error
                    or ask.technical_error
                )
                all_records.extend(bid.records)
                all_records.extend(ask.records)
                window_reports.append(
                    {
                        "manifest_index": window.manifest_index,
                        "from_at": _iso(window.from_at),
                        "to_at": _iso(window.to_at),
                        "bid_tick_count": bid.count,
                        "ask_tick_count": ask.count,
                        "bid_page_count": bid.page_count,
                        "ask_page_count": ask.page_count,
                        "bid_first_at": _iso(bid.first_at),
                        "bid_last_at": _iso(bid.last_at),
                        "ask_first_at": _iso(ask.first_at),
                        "ask_last_at": _iso(ask.last_at),
                        "technical_error": (
                            bid.technical_error or ask.technical_error
                        ),
                    }
                )
                if technical_error:
                    break

            candidate_reports.append(
                {
                    "semantic_role": candidate.semantic_role,
                    "provider_symbol": identity.provider_symbol,
                    "provider_symbol_id": identity.symbol_id,
                    "provider_digits": identity.digits,
                    "account_fingerprint": (
                        compute_ctrader_demo_lab_account_fingerprint(
                            identity.account_id
                        )
                    ),
                    "data_root": data_root.as_posix(),
                    "technical_error": technical_error,
                    "raw_dataset_sha256": historical_shard_dataset_digest(
                        tuple(all_records)
                    ),
                    "records": [
                        _record_payload(record)
                        for record in all_records
                    ],
                    "window_reports": window_reports,
                }
            )

        report: dict[str, object] = {
            "identity": SHARED_B_CROSS_ASSET_RAW_IDENTITY,
            "partition": "r8_source_only",
            "source_manifest_sha256": expected_manifest_sha256,
            "provider_catalog_sha256": expected_catalog_sha256,
            "selected_manifest_indices": list(FROZEN_PILOT_INDICES),
            "selection_basis": "FROZEN_MARKET_SEMANTICS_NOT_PERFORMANCE",
            "candidate_reports": candidate_reports,
            "read_only_message_firewall": True,
            "target_or_outcome_read": False,
            "r6_r5_read": False,
            "fresh_holdout_opened": False,
            "scientific_v15_opened": False,
            "broker_mutation": False,
            "shared_methodology_authority": False,
            "shared_sizing_authority": False,
            "shared_risk_authority": False,
            "shared_order_authority": False,
            "shared_execution_authority": False,
        }
        destination = output_dir / "shared-b-cross-asset-raw-manifest.json"
        destination.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return report
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-catalog-sha256", required=True)
    args = parser.parse_args()
    report = run(
        manifest_path=args.manifest,
        catalog_path=args.catalog,
        output_dir=args.output_dir,
        expected_manifest_sha256=args.expected_manifest_sha256,
        expected_catalog_sha256=args.expected_catalog_sha256,
    )
    print(
        json.dumps(
            {
                "identity": report["identity"],
                "selected_manifest_indices": report[
                    "selected_manifest_indices"
                ],
                "candidate_reports": [
                    {
                        "provider_symbol": item.get("provider_symbol"),
                        "technical_error": item.get("technical_error"),
                        "raw_dataset_sha256": item.get(
                            "raw_dataset_sha256"
                        ),
                    }
                    for item in cast(
                        list[dict[str, object]],
                        report["candidate_reports"],
                    )
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
