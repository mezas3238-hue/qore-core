"""Acquire one source-only WP-05 V15 cross-asset R8 shard."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, sleep
from typing import cast
from uuid import UUID

from qore.infrastructure.core_stack_v2.active_perception_v15_cross_asset_acquisition import (
    EXPECTED_MANIFEST_SHA256,
    V15_CROSS_ASSET_ACQUISITION_IDENTITY,
    V15CrossAssetFamily,
    cross_asset_spec,
    plan_v15_cross_asset_shard,
    v15_assignment_digest,
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
    adapter_id=AdapterId(UUID("7d000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("7d000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo-historical"),
)


class V15CrossAssetAcquisitionError(RuntimeError):
    """V15 source-only cross-asset acquisition failed closed."""


@dataclass(frozen=True, slots=True)
class _ManifestWindow:
    manifest_index: int
    from_at: datetime
    to_at: datetime
    source_count: int


@dataclass(frozen=True, slots=True)
class _SideStats:
    count: int
    page_count: int
    first_at: datetime | None
    last_at: datetime | None
    records: tuple[HistoricalQuoteSideShardRecord, ...]


class _RateLimiter:
    def __init__(self) -> None:
        self._last_request_started: float | None = None

    def wait(self) -> None:
        now = monotonic()
        if self._last_request_started is not None:
            remaining = REQUEST_INTERVAL_SECONDS - (now - self._last_request_started)
            if remaining > 0:
                sleep(remaining)
        self._last_request_started = monotonic()


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise V15CrossAssetAcquisitionError(
        f"missing required environment input: {name}"
    )


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(UTC).isoformat(
        timespec="microseconds"
    )


def _load_manifest(path: Path) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise V15CrossAssetAcquisitionError("manifest must be a JSON object")
    if raw.get("identity") != EXPECTED_MANIFEST_IDENTITY:
        raise V15CrossAssetAcquisitionError("unexpected source manifest identity")
    if raw.get("partition") != "r8":
        raise V15CrossAssetAcquisitionError("V15 acquisition restricted to R8")
    if raw.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256:
        raise V15CrossAssetAcquisitionError("source manifest digest mismatch")
    if raw.get("target_or_outcome_used_for_selection") is not False:
        raise V15CrossAssetAcquisitionError("source manifest used target/outcome")
    if raw.get("r6_r5_read_for_selection") is not False:
        raise V15CrossAssetAcquisitionError("source manifest read R6/R5")
    if raw.get("fresh_holdout_opened") is not False:
        raise V15CrossAssetAcquisitionError("source manifest opened holdout")
    windows = raw.get("windows")
    if not isinstance(windows, list) or len(windows) != 2948:
        raise V15CrossAssetAcquisitionError(
            "V15 requires exact 2948-window manifest"
        )
    return cast(dict[str, object], raw)


def _parse_window(value: object, index: int) -> _ManifestWindow:
    if not isinstance(value, list) or len(value) != 3:
        raise V15CrossAssetAcquisitionError(
            "manifest window must have three fields"
        )
    from_raw, to_raw, source_count = value
    if not isinstance(from_raw, str) or not isinstance(to_raw, str):
        raise V15CrossAssetAcquisitionError(
            "manifest timestamps must be strings"
        )
    if type(source_count) is not int or source_count <= 0:
        raise V15CrossAssetAcquisitionError("manifest source_count invalid")
    try:
        from_at = datetime.fromisoformat(from_raw)
        to_at = datetime.fromisoformat(to_raw)
    except ValueError as exc:
        raise V15CrossAssetAcquisitionError(
            "manifest timestamp invalid"
        ) from exc
    if (
        from_at.tzinfo is None
        or from_at.utcoffset() is None
        or to_at.tzinfo is None
        or to_at.utcoffset() is None
        or to_at <= from_at
    ):
        raise V15CrossAssetAcquisitionError("manifest chronology invalid")
    return _ManifestWindow(index, from_at, to_at, source_count)


def _collect_side(
    *,
    reader: CTraderHistoricalTickReader,
    sink: HistoricalQuoteSideShardSink,
    limiter: _RateLimiter,
    identity: CTraderHistoricalSensorIdentity,
    instrument: Instrument,
    window: _ManifestWindow,
    quote_type: CTraderQuoteType,
    family: V15CrossAssetFamily,
) -> _SideStats:
    records: list[HistoricalQuoteSideShardRecord] = []
    count = 0
    page_count = 0
    first_at: datetime | None = None
    last_at: datetime | None = None
    page_ordinal = 0

    for segment in split_historical_request_windows(
        from_at=window.from_at,
        to_at=window.to_at,
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
                    f"wp05-v15-{family.value.lower()}-"
                    f"{window.manifest_index}-"
                    f"{quote_type.name.lower()}-{page_ordinal}"
                ),
            )
            if isinstance(result, Failure):
                raise V15CrossAssetAcquisitionError(
                    "historical cross-asset request failed: "
                    f"{result.error}"
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
                    window_index=window.manifest_index,
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
                raise V15CrossAssetAcquisitionError(
                    "historical pagination made no legal backward progress"
                )
            page_to_at = next_to_at

    return _SideStats(
        count=count,
        page_count=page_count,
        first_at=first_at,
        last_at=last_at,
        records=tuple(records),
    )


def run(
    *,
    manifest_path: Path,
    output_dir: Path,
    family: V15CrossAssetFamily,
    shard_index: int,
) -> dict[str, object]:
    manifest = _load_manifest(manifest_path)
    raw_windows = cast(list[object], manifest["windows"])
    plan = plan_v15_cross_asset_shard(
        family=family,
        total_windows=len(raw_windows),
        shard_index=shard_index,
    )
    windows = tuple(
        _parse_window(raw_windows[index], index)
        for index in plan.manifest_indices
    )
    spec = cross_asset_spec(family)

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
    output_dir.mkdir(parents=True, exist_ok=True)
    sink = HistoricalQuoteSideShardSink(output_dir / "data")
    limiter = _RateLimiter()

    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise V15CrossAssetAcquisitionError(
                "cTrader DEMO authentication failed"
            )
        identity_result = resolve_ctrader_historical_sensor_identity(
            client=client,
            provider_symbol=spec.provider_symbol,
            timeout_seconds=10.0,
        )
        if isinstance(identity_result, Failure):
            raise V15CrossAssetAcquisitionError(
                "V15 provider symbol resolution failed"
            )
        identity = identity_result.value
        if identity.symbol_id != spec.provider_symbol_id:
            raise V15CrossAssetAcquisitionError(
                "V15 frozen provider symbol id drift"
            )

        reader = CTraderHistoricalTickReader(
            client=client,
            timeout_seconds=20.0,
        )
        instrument = Instrument(spec.canonical_instrument)
        all_records: list[HistoricalQuoteSideShardRecord] = []
        window_reports: list[dict[str, object]] = []
        bid_ticks = ask_ticks = bid_pages = ask_pages = 0
        empty_bid = empty_ask = 0

        for window in windows:
            bid = _collect_side(
                reader=reader,
                sink=sink,
                limiter=limiter,
                identity=identity,
                instrument=instrument,
                window=window,
                quote_type=CTraderQuoteType.BID,
                family=family,
            )
            ask = _collect_side(
                reader=reader,
                sink=sink,
                limiter=limiter,
                identity=identity,
                instrument=instrument,
                window=window,
                quote_type=CTraderQuoteType.ASK,
                family=family,
            )
            all_records.extend(bid.records)
            all_records.extend(ask.records)
            bid_ticks += bid.count
            ask_ticks += ask.count
            bid_pages += bid.page_count
            ask_pages += ask.page_count
            empty_bid += int(bid.count == 0)
            empty_ask += int(ask.count == 0)
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
                }
            )

        return {
            "identity": V15_CROSS_ASSET_ACQUISITION_IDENTITY,
            "partition": "r8_source_only",
            "manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "family": family.value,
            "semantic_role": spec.semantic_role,
            "canonical_instrument": spec.canonical_instrument,
            "provider_symbol": identity.provider_symbol,
            "provider_symbol_id": identity.symbol_id,
            "provider_digits": identity.digits,
            "account_fingerprint": compute_ctrader_demo_lab_account_fingerprint(
                identity.account_id
            ),
            "shard_index": plan.shard_index,
            "shard_count": plan.shard_count,
            "total_manifest_windows": plan.total_windows,
            "assignment_rule": "MANIFEST_INDEX_MOD_16",
            "assignment_sha256": v15_assignment_digest(
                plan=plan,
                manifest_sha256=EXPECTED_MANIFEST_SHA256,
            ),
            "attempted_manifest_indices": list(plan.manifest_indices),
            "assigned_window_count": len(plan.manifest_indices),
            "read_only_message_firewall": True,
            "bid_tick_count": bid_ticks,
            "ask_tick_count": ask_ticks,
            "bid_page_count": bid_pages,
            "ask_page_count": ask_pages,
            "provider_page_count": bid_pages + ask_pages,
            "empty_bid_window_count": empty_bid,
            "empty_ask_window_count": empty_ask,
            "immutable_page_shard_count": len(all_records),
            "shard_dataset_sha256": historical_shard_dataset_digest(
                tuple(all_records)
            ),
            "window_reports": window_reports,
            "target_or_outcome_read": False,
            "r6_r5_read": False,
            "fresh_holdout_opened": False,
            "scientific_v15_outcomes_opened": False,
            "shared_methodology_authority": False,
            "shared_sizing_authority": False,
            "shared_risk_authority": False,
            "shared_order_authority": False,
            "shared_execution_authority": False,
        }
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--family",
        choices=[item.value for item in V15CrossAssetFamily],
        required=True,
    )
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    family = V15CrossAssetFamily(args.family)
    report = run(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        family=family,
        shard_index=args.shard_index,
    )
    destination = (
        args.output_dir
        / f"{family.value.lower()}-shard-{args.shard_index:02d}-report.json"
    )
    destination.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "family": report["family"],
                "shard_index": report["shard_index"],
                "provider_digits": report["provider_digits"],
                "bid_tick_count": report["bid_tick_count"],
                "ask_tick_count": report["ask_tick_count"],
                "empty_bid_window_count": report["empty_bid_window_count"],
                "empty_ask_window_count": report["empty_ask_window_count"],
                "shard_dataset_sha256": report["shard_dataset_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
