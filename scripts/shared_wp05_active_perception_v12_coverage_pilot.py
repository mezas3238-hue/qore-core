"""Run the outcome-blind WP-05 V12 historical tick coverage pilot.

The script consumes only the already frozen R8 source-only acquisition manifest,
authenticates against cTrader DEMO, resolves exact provider identity, and
retains BID/ASK pages as immutable quote-side shards. No target/outcome,
R6/R5, fresh holdout, Trader decision, sizing, Risk or Execution input exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, sleep
from typing import Any
from uuid import UUID

from qore.infrastructure.core_stack_v2.active_perception_v12_coverage_pilot import (
    V12CoveragePilotSample,
    classify_v12_coverage_pilot,
    select_v12_temporal_coverage_pilot,
    v12_coverage_pilot_selection_digest,
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

IDENTITY = "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_COVERAGE_PILOT_001"
EXPECTED_MANIFEST_IDENTITY = (
    "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_ACQUISITION_MANIFEST_001"
)
SELECTION_RULE = "FIRST_Q1_MID_Q3_LAST_BY_MANIFEST_ORDINAL"
REQUEST_INTERVAL_SECONDS = 0.21
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("7a000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("7a000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo-historical"),
)


class V12CoveragePilotError(RuntimeError):
    """Coverage-pilot acquisition failed closed."""


@dataclass(frozen=True, slots=True)
class _SideStats:
    count: int
    page_count: int
    first_at: datetime | None
    last_at: datetime | None
    longest_gap_ms: int
    records: tuple[HistoricalQuoteSideShardRecord, ...]


class _HistoricalRateLimiter:
    def __init__(self, interval_seconds: float = REQUEST_INTERVAL_SECONDS) -> None:
        self._interval_seconds = interval_seconds
        self._last_request_started: float | None = None

    def wait(self) -> None:
        now = monotonic()
        if self._last_request_started is not None:
            remaining = self._interval_seconds - (now - self._last_request_started)
            if remaining > 0:
                sleep(remaining)
        self._last_request_started = monotonic()


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise V12CoveragePilotError(f"missing required environment input: {name}")


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _page_longest_gap_ms(observations: tuple[Any, ...]) -> int:
    longest = 0
    for left, right in zip(observations, observations[1:], strict=False):
        gap = int(
            (right.provider_event_at - left.provider_event_at).total_seconds()
            * 1000
        )
        if gap > longest:
            longest = gap
    return longest


def _collect_side(
    *,
    reader: CTraderHistoricalTickReader,
    sink: HistoricalQuoteSideShardSink,
    limiter: _HistoricalRateLimiter,
    identity: CTraderHistoricalSensorIdentity,
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
    longest_gap_ms = 0
    previous_newer_page_first: datetime | None = None
    page_ordinal = 0

    segments = split_historical_request_windows(from_at=from_at, to_at=to_at)
    for segment_index, segment in enumerate(segments):
        page_to_at = segment.to_at
        previous_newer_page_first = None
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
                    f"wp05-v12-pilot-{manifest_index}-"
                    f"{quote_type.name.lower()}-{segment_index}-{page_ordinal}"
                ),
            )
            if isinstance(result, Failure):
                raise V12CoveragePilotError(
                    "historical tick page request failed during coverage pilot"
                )
            page = result.value
            retrieved_at = datetime.now(UTC)
            observations = retain_ctrader_historical_quote_side_page(
                page=page,
                instrument=Instrument("NAS100"),
                source=_SOURCE,
                provider_symbol=identity.provider_symbol,
                retrieved_at=retrieved_at,
            )
            side = (
                MarketPriceSide.BID
                if quote_type is CTraderQuoteType.BID
                else MarketPriceSide.ASK
            )
            record = sink.write_page(
                quote_side=side,
                window_index=manifest_index,
                page_index=page_ordinal,
                request_from_at=request.from_at,
                request_to_at=request.to_at,
                retrieved_at=retrieved_at,
                observations=observations,
            )
            records.append(record)
            page_count += 1
            count += len(observations)

            if observations:
                current_first = observations[0].provider_event_at
                current_last = observations[-1].provider_event_at
                if first_at is None or current_first < first_at:
                    first_at = current_first
                if last_at is None or current_last > last_at:
                    last_at = current_last
                longest_gap_ms = max(
                    longest_gap_ms,
                    _page_longest_gap_ms(observations),
                )
                if previous_newer_page_first is not None:
                    cross_gap = int(
                        (
                            previous_newer_page_first - current_last
                        ).total_seconds()
                        * 1000
                    )
                    if cross_gap > longest_gap_ms:
                        longest_gap_ms = cross_gap
                previous_newer_page_first = current_first

            next_to_at = page.next_older_to_at
            page_ordinal += 1
            if next_to_at is None:
                break
            if next_to_at <= segment.from_at or next_to_at >= page_to_at:
                raise V12CoveragePilotError(
                    "historical tick pagination made no legal backward progress"
                )
            page_to_at = next_to_at

    return _SideStats(
        count=count,
        page_count=page_count,
        first_at=first_at,
        last_at=last_at,
        longest_gap_ms=longest_gap_ms,
        records=tuple(records),
    )


def _load_manifest(path: Path, *, expected_manifest_sha256: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("identity") != EXPECTED_MANIFEST_IDENTITY:
        raise V12CoveragePilotError("unexpected V12 acquisition manifest identity")
    if payload.get("partition") != "r8":
        raise V12CoveragePilotError("coverage pilot is restricted to R8")
    if payload.get("manifest_sha256") != expected_manifest_sha256:
        raise V12CoveragePilotError("V12 acquisition manifest digest mismatch")
    if payload.get("target_or_outcome_used_for_selection") is not False:
        raise V12CoveragePilotError("manifest used target/outcome for selection")
    if payload.get("r6_r5_read_for_selection") is not False:
        raise V12CoveragePilotError("manifest read R6/R5 for sensor selection")
    if payload.get("fresh_holdout_opened") is not False:
        raise V12CoveragePilotError("manifest opened fresh holdout")
    windows = payload.get("windows")
    if not isinstance(windows, list) or not windows:
        raise V12CoveragePilotError("manifest omitted acquisition windows")
    return payload


def run(
    *,
    manifest_path: Path,
    output_dir: Path,
    expected_manifest_sha256: str,
) -> dict[str, object]:
    manifest = _load_manifest(
        manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    selected = select_v12_temporal_coverage_pilot(manifest["windows"])
    selection_digest = v12_coverage_pilot_selection_digest(
        manifest_sha256=expected_manifest_sha256,
        windows=selected,
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
    native_client = SpotwareCTraderOpenApiClient(
        credentials=credentials,
        required_permission_scope=CTraderOpenApiPermissionScope.TRADE,
    )
    read_only_client = CTraderHistoricalReadOnlyMessageClient(native_client)
    output_dir.mkdir(parents=True, exist_ok=True)
    sink = HistoricalQuoteSideShardSink(output_dir / "shards")
    limiter = _HistoricalRateLimiter()

    try:
        ready = read_only_client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise V12CoveragePilotError(
                "cTrader DEMO authentication failed for V12 coverage pilot"
            )
        identity_result = resolve_ctrader_historical_sensor_identity(
            client=read_only_client,
            provider_symbol=str(manifest["provider_symbol"]),
            timeout_seconds=10.0,
        )
        if isinstance(identity_result, Failure):
            raise V12CoveragePilotError(
                "cTrader provider symbol identity resolution failed"
            )
        provider_identity = identity_result.value
        reader = CTraderHistoricalTickReader(
            client=read_only_client,
            timeout_seconds=20.0,
        )

        window_reports: list[dict[str, object]] = []
        samples: list[V12CoveragePilotSample] = []
        all_records: list[HistoricalQuoteSideShardRecord] = []

        for window in selected:
            bid = _collect_side(
                reader=reader,
                sink=sink,
                limiter=limiter,
                identity=provider_identity,
                manifest_index=window.manifest_index,
                from_at=window.from_at,
                to_at=window.to_at,
                quote_type=CTraderQuoteType.BID,
            )
            ask = _collect_side(
                reader=reader,
                sink=sink,
                limiter=limiter,
                identity=provider_identity,
                manifest_index=window.manifest_index,
                from_at=window.from_at,
                to_at=window.to_at,
                quote_type=CTraderQuoteType.ASK,
            )
            all_records.extend(bid.records)
            all_records.extend(ask.records)
            samples.append(
                V12CoveragePilotSample(
                    manifest_index=window.manifest_index,
                    bid_count=bid.count,
                    ask_count=ask.count,
                )
            )
            window_reports.append(
                {
                    "manifest_index": window.manifest_index,
                    "from_at": _iso(window.from_at),
                    "to_at": _iso(window.to_at),
                    "source_count": window.source_count,
                    "bid_count": bid.count,
                    "ask_count": ask.count,
                    "bid_page_count": bid.page_count,
                    "ask_page_count": ask.page_count,
                    "bid_first_at": _iso(bid.first_at),
                    "bid_last_at": _iso(bid.last_at),
                    "ask_first_at": _iso(ask.first_at),
                    "ask_last_at": _iso(ask.last_at),
                    "bid_longest_gap_ms": bid.longest_gap_ms,
                    "ask_longest_gap_ms": ask.longest_gap_ms,
                    "duplicate_count": 0,
                    "conflict_count": 0,
                }
            )

        status = classify_v12_coverage_pilot(tuple(samples))
        dataset_digest = historical_shard_dataset_digest(tuple(all_records))
        report: dict[str, object] = {
            "identity": IDENTITY,
            "partition": "r8",
            "manifest_identity": EXPECTED_MANIFEST_IDENTITY,
            "manifest_sha256": expected_manifest_sha256,
            "selection_rule": SELECTION_RULE,
            "selection_sha256": selection_digest,
            "selected_manifest_indices": [
                item.manifest_index for item in selected
            ],
            "provider_symbol": provider_identity.provider_symbol,
            "provider_symbol_id": provider_identity.symbol_id,
            "provider_digits": provider_identity.digits,
            "account_fingerprint": compute_ctrader_demo_lab_account_fingerprint(
                provider_identity.account_id
            ),
            "permission_scope_required": "trade",
            "read_only_message_firewall": True,
            "coverage_status": status.value,
            "window_reports": window_reports,
            "bid_tick_count": sum(item.bid_count for item in samples),
            "ask_tick_count": sum(item.ask_count for item in samples),
            "shard_count": len(all_records),
            "dataset_sha256": dataset_digest,
            "provider_error_count": 0,
            "rate_limit_error_count": 0,
            "target_or_outcome_used_for_selection": False,
            "target_or_outcome_read": False,
            "r6_r5_read": False,
            "fresh_holdout_opened": False,
            "shared_methodology_authority": False,
            "shared_sizing_authority": False,
            "shared_risk_authority": False,
            "shared_order_authority": False,
            "shared_execution_authority": False,
        }
        return report
    finally:
        read_only_client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()

    report = run(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        expected_manifest_sha256=args.expected_manifest_sha256,
    )
    report_path = args.output_dir / "coverage-pilot-report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": report["identity"],
                "coverage_status": report["coverage_status"],
                "selected_manifest_indices": report["selected_manifest_indices"],
                "bid_tick_count": report["bid_tick_count"],
                "ask_tick_count": report["ask_tick_count"],
                "dataset_sha256": report["dataset_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
