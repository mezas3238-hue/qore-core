"""Acquire one source-only WP-05 V14 peer-microstructure R8 shard."""

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

from qore.infrastructure.core_stack_v2.active_perception_v14_peer_acquisition import (
    FROZEN_SHARD_COUNT,
    V14_PEER_ACQUISITION_IDENTITY,
    V14PeerFamily,
    peer_spec,
    plan_v14_peer_shard,
    v14_peer_assignment_digest,
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
    adapter_id=AdapterId(UUID("7c000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("7c000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo-historical"),
)


class V14PeerAcquisitionError(RuntimeError):
    """V14 source-only peer acquisition failed closed."""


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
    raise V14PeerAcquisitionError(f"missing required environment input: {name}")


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(UTC).isoformat(
        timespec="microseconds"
    )


def _load_manifest(path: Path, expected_sha256: str) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise V14PeerAcquisitionError("manifest must be a JSON object")
    payload = cast(dict[str, Any], raw)
    if payload.get("identity") != EXPECTED_MANIFEST_IDENTITY:
        raise V14PeerAcquisitionError("unexpected source manifest identity")
    if payload.get("partition") != "r8":
        raise V14PeerAcquisitionError("V14 acquisition restricted to R8")
    if payload.get("manifest_sha256") != expected_sha256:
        raise V14PeerAcquisitionError("source manifest digest mismatch")
    if payload.get("target_or_outcome_used_for_selection") is not False:
        raise V14PeerAcquisitionError("source manifest used target/outcome")
    if payload.get("r6_r5_read_for_selection") is not False:
        raise V14PeerAcquisitionError("source manifest read R6/R5")
    if payload.get("fresh_holdout_opened") is not False:
        raise V14PeerAcquisitionError("source manifest opened fresh holdout")
    if not isinstance(payload.get("windows"), list) or not payload["windows"]:
        raise V14PeerAcquisitionError("source manifest omitted windows")
    return payload


def _parse_window(value: object, index: int) -> _ManifestWindow:
    if not isinstance(value, list) or len(value) != 3:
        raise V14PeerAcquisitionError("manifest window must have three fields")
    from_raw, to_raw, source_count = value
    if not isinstance(from_raw, str) or not isinstance(to_raw, str):
        raise V14PeerAcquisitionError("manifest timestamps must be strings")
    if type(source_count) is not int or source_count <= 0:
        raise V14PeerAcquisitionError("manifest source_count invalid")
    try:
        from_at = datetime.fromisoformat(from_raw)
        to_at = datetime.fromisoformat(to_raw)
    except ValueError as error:
        raise V14PeerAcquisitionError("manifest timestamp invalid") from error
    if (
        from_at.tzinfo is None
        or from_at.utcoffset() is None
        or to_at.tzinfo is None
        or to_at.utcoffset() is None
        or to_at <= from_at
    ):
        raise V14PeerAcquisitionError("manifest chronology invalid")
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
    peer: V14PeerFamily,
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
                    f"wp05-v14-{peer.value.lower()}-{window.manifest_index}-"
                    f"{quote_type.name.lower()}-{page_ordinal}"
                ),
            )
            if isinstance(result, Failure):
                raise V14PeerAcquisitionError(
                    "historical peer tick request failed: "
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
                if first_at is None or observations[0].provider_event_at < first_at:
                    first_at = observations[0].provider_event_at
                if last_at is None or observations[-1].provider_event_at > last_at:
                    last_at = observations[-1].provider_event_at

            next_to_at = page.next_older_to_at
            page_ordinal += 1
            if next_to_at is None:
                break
            if next_to_at <= segment.from_at or next_to_at >= page_to_at:
                raise V14PeerAcquisitionError(
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
    expected_manifest_sha256: str,
    peer: V14PeerFamily,
    shard_index: int,
    shard_count: int,
) -> dict[str, object]:
    manifest = _load_manifest(manifest_path, expected_manifest_sha256)
    raw_windows = cast(list[object], manifest["windows"])
    plan = plan_v14_peer_shard(
        peer=peer,
        total_windows=len(raw_windows),
        shard_index=shard_index,
        shard_count=shard_count,
    )
    windows = tuple(
        _parse_window(raw_windows[index], index) for index in plan.manifest_indices
    )
    spec = peer_spec(peer)

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
            raise V14PeerAcquisitionError("cTrader DEMO authentication failed")
        identity_result = resolve_ctrader_historical_sensor_identity(
            client=client,
            provider_symbol=spec.provider_symbol,
            timeout_seconds=10.0,
        )
        if isinstance(identity_result, Failure):
            raise V14PeerAcquisitionError("V14 provider symbol resolution failed")
        identity = identity_result.value
        if identity.symbol_id != spec.provider_symbol_id or identity.digits != spec.digits:
            raise V14PeerAcquisitionError("V14 frozen provider identity drift")

        reader = CTraderHistoricalTickReader(client=client, timeout_seconds=20.0)
        instrument = Instrument(spec.canonical_instrument)
        all_records: list[HistoricalQuoteSideShardRecord] = []
        window_reports: list[dict[str, object]] = []
        bid_ticks = 0
        ask_ticks = 0
        bid_pages = 0
        ask_pages = 0
        empty_bid = 0
        empty_ask = 0

        for window in windows:
            bid = _collect_side(
                reader=reader,
                sink=sink,
                limiter=limiter,
                identity=identity,
                instrument=instrument,
                window=window,
                quote_type=CTraderQuoteType.BID,
                peer=peer,
            )
            ask = _collect_side(
                reader=reader,
                sink=sink,
                limiter=limiter,
                identity=identity,
                instrument=instrument,
                window=window,
                quote_type=CTraderQuoteType.ASK,
                peer=peer,
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
            "identity": V14_PEER_ACQUISITION_IDENTITY,
            "partition": "r8_source_only",
            "manifest_sha256": expected_manifest_sha256,
            "peer_family": peer.value,
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
            "assignment_sha256": v14_peer_assignment_digest(
                plan=plan,
                manifest_sha256=expected_manifest_sha256,
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
            "scientific_v14_outcomes_opened": False,
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
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--peer", choices=[item.value for item in V14PeerFamily], required=True)
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, default=FROZEN_SHARD_COUNT)
    args = parser.parse_args()
    peer = V14PeerFamily(args.peer)
    report = run(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        expected_manifest_sha256=args.expected_manifest_sha256,
        peer=peer,
        shard_index=args.shard_index,
        shard_count=args.shard_count,
    )
    destination = args.output_dir / f"{peer.value.lower()}-shard-{args.shard_index:02d}-report.json"
    destination.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "peer_family": report["peer_family"],
                "shard_index": report["shard_index"],
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
