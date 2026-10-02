"""Run post-V14 source-only historical availability for frozen cross-asset sensors."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import monotonic, sleep
from typing import Any, cast

from qore.infrastructure.core_stack_v2.active_perception_post_v13_sensor_availability import (
    HistoricalWindowCoverage,
    classify_historical_peer_coverage,
)
from qore.infrastructure.core_stack_v2.active_perception_post_v14_cross_asset_availability import (
    FROZEN_CROSS_ASSET_CANDIDATES,
    POST_V14_CROSS_ASSET_AUDIT_IDENTITY,
    validate_candidates_against_catalog,
)
from qore.infrastructure.core_stack_v2.active_perception_v12_coverage_pilot import (
    select_v12_temporal_coverage_pilot,
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
from qore.kernel.result import Failure

EXPECTED_MANIFEST_IDENTITY = (
    "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_ACQUISITION_MANIFEST_001"
)
REQUEST_INTERVAL_SECONDS = 0.21


class PostV14CrossAssetAuditError(RuntimeError):
    """The post-V14 source-only availability audit failed closed."""


@dataclass(frozen=True, slots=True)
class _SideProbe:
    count: int
    page_count: int
    first_at: datetime | None
    last_at: datetime | None
    technical_error: bool


class _RateLimiter:
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
    raise PostV14CrossAssetAuditError(f"missing required environment input: {name}")


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat(timespec="microseconds")


def _load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise PostV14CrossAssetAuditError(f"{path} must contain a JSON object")
    return cast(dict[str, Any], raw)


def _probe_side(
    *,
    reader: CTraderHistoricalTickReader,
    limiter: _RateLimiter,
    identity: CTraderHistoricalSensorIdentity,
    from_at: datetime,
    to_at: datetime,
    quote_type: CTraderQuoteType,
    symbol_ordinal: int,
    manifest_index: int,
) -> _SideProbe:
    count = 0
    page_count = 0
    first_at: datetime | None = None
    last_at: datetime | None = None
    request_ordinal = 0
    for segment in split_historical_request_windows(from_at=from_at, to_at=to_at):
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
                    "wp05-post-v14-cross-asset-"
                    f"{symbol_ordinal}-{manifest_index}-"
                    f"{quote_type.name.lower()}-{request_ordinal}"
                ),
            )
            if isinstance(result, Failure):
                return _SideProbe(
                    count=count,
                    page_count=page_count,
                    first_at=first_at,
                    last_at=last_at,
                    technical_error=True,
                )
            page = result.value
            page_count += 1
            count += len(page.ticks)
            if page.ticks:
                observed_first = page.ticks[0].observed_at
                observed_last = page.ticks[-1].observed_at
                if first_at is None or observed_first < first_at:
                    first_at = observed_first
                if last_at is None or observed_last > last_at:
                    last_at = observed_last
            next_to_at = page.next_older_to_at
            request_ordinal += 1
            if next_to_at is None:
                break
            if next_to_at <= segment.from_at or next_to_at >= page_to_at:
                raise PostV14CrossAssetAuditError(
                    "historical pagination made no legal backward progress"
                )
            page_to_at = next_to_at
    return _SideProbe(
        count=count,
        page_count=page_count,
        first_at=first_at,
        last_at=last_at,
        technical_error=False,
    )


def run(
    *,
    manifest_path: Path,
    catalog_path: Path,
    output_path: Path,
    expected_manifest_sha256: str,
    expected_catalog_sha256: str,
) -> dict[str, object]:
    manifest = _load_json(manifest_path)
    catalog = _load_json(catalog_path)

    if manifest.get("identity") != EXPECTED_MANIFEST_IDENTITY:
        raise PostV14CrossAssetAuditError("unexpected source-manifest identity")
    if manifest.get("partition") != "r8":
        raise PostV14CrossAssetAuditError("audit is restricted to R8 source windows")
    if manifest.get("manifest_sha256") != expected_manifest_sha256:
        raise PostV14CrossAssetAuditError("source-manifest digest mismatch")
    if catalog.get("provider_catalog_sha256") != expected_catalog_sha256:
        raise PostV14CrossAssetAuditError("provider-catalog digest mismatch")
    rows = catalog.get("enabled_symbols")
    if not isinstance(rows, list):
        raise PostV14CrossAssetAuditError("provider catalog omitted enabled symbols")
    validate_candidates_against_catalog(cast(list[dict[str, object]], rows))

    selected_windows = select_v12_temporal_coverage_pilot(manifest["windows"])

    credentials = CTraderOpenApiCredentials(
        client_id=_required_env("QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET", "QORE_CTRADER_DEMO_CLIENT_SECRET"
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN", "QORE_CTRADER_DEMO_ACCESS_TOKEN"
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN", "QORE_CTRADER_DEMO_REFRESH_TOKEN"
        ),
        ctid_trader_account_id=int(
            _required_env("QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID")
        ),
    )
    native_client = SpotwareCTraderOpenApiClient(
        credentials=credentials,
        required_permission_scope=CTraderOpenApiPermissionScope.TRADE,
    )
    read_only_client = CTraderHistoricalReadOnlyMessageClient(native_client)
    limiter = _RateLimiter()

    try:
        ready = read_only_client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise PostV14CrossAssetAuditError("cTrader DEMO authentication failed")

        reports: list[dict[str, object]] = []
        for ordinal, candidate in enumerate(FROZEN_CROSS_ASSET_CANDIDATES):
            identity_result = resolve_ctrader_historical_sensor_identity(
                client=read_only_client,
                provider_symbol=candidate.provider_symbol,
                timeout_seconds=10.0,
            )
            if isinstance(identity_result, Failure):
                reports.append(
                    {
                        "semantic_role": candidate.semantic_role,
                        "provider_symbol": candidate.provider_symbol,
                        "provider_symbol_id": candidate.provider_symbol_id,
                        "coverage_status": "technical_error",
                        "windows": [],
                    }
                )
                continue
            identity = identity_result.value
            if identity.symbol_id != candidate.provider_symbol_id:
                raise PostV14CrossAssetAuditError(
                    f"provider symbol id drift for {candidate.provider_symbol}"
                )
            reader = CTraderHistoricalTickReader(
                client=read_only_client,
                timeout_seconds=20.0,
            )
            coverage_rows: list[HistoricalWindowCoverage] = []
            window_reports: list[dict[str, object]] = []
            technical_error = False

            for window in selected_windows:
                bid = _probe_side(
                    reader=reader,
                    limiter=limiter,
                    identity=identity,
                    from_at=window.from_at,
                    to_at=window.to_at,
                    quote_type=CTraderQuoteType.BID,
                    symbol_ordinal=ordinal,
                    manifest_index=window.manifest_index,
                )
                ask = _probe_side(
                    reader=reader,
                    limiter=limiter,
                    identity=identity,
                    from_at=window.from_at,
                    to_at=window.to_at,
                    quote_type=CTraderQuoteType.ASK,
                    symbol_ordinal=ordinal,
                    manifest_index=window.manifest_index,
                )
                technical_error = technical_error or bid.technical_error or ask.technical_error
                coverage_rows.append(
                    HistoricalWindowCoverage(
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
                        "bid_count": bid.count,
                        "ask_count": ask.count,
                        "bid_page_count": bid.page_count,
                        "ask_page_count": ask.page_count,
                        "bid_first_at": _iso(bid.first_at),
                        "bid_last_at": _iso(bid.last_at),
                        "ask_first_at": _iso(ask.first_at),
                        "ask_last_at": _iso(ask.last_at),
                        "technical_error": bid.technical_error or ask.technical_error,
                    }
                )

            status = (
                "technical_error"
                if technical_error
                else classify_historical_peer_coverage(tuple(coverage_rows)).value
            )
            reports.append(
                {
                    "semantic_role": candidate.semantic_role,
                    "provider_symbol": candidate.provider_symbol,
                    "provider_symbol_id": candidate.provider_symbol_id,
                    "provider_digits": identity.digits,
                    "coverage_status": status,
                    "bid_tick_count": sum(item.bid_count for item in coverage_rows),
                    "ask_tick_count": sum(item.ask_count for item in coverage_rows),
                    "windows": window_reports,
                }
            )

        report: dict[str, object] = {
            "identity": POST_V14_CROSS_ASSET_AUDIT_IDENTITY,
            "partition": "r8_source_only",
            "provider_catalog_sha256": expected_catalog_sha256,
            "source_manifest_sha256": expected_manifest_sha256,
            "selection_basis": "FROZEN_MARKET_SEMANTICS_NOT_PERFORMANCE",
            "selected_manifest_indices": [
                item.manifest_index for item in selected_windows
            ],
            "candidate_reports": reports,
            "target_or_outcome_read": False,
            "r6_r5_read": False,
            "fresh_holdout_opened": False,
            "scientific_v15_opened": False,
            "shared_methodology_authority": False,
            "shared_sizing_authority": False,
            "shared_risk_authority": False,
            "shared_order_authority": False,
            "shared_execution_authority": False,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return report
    finally:
        read_only_client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-catalog-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(
        manifest_path=args.manifest,
        catalog_path=args.catalog,
        output_path=args.output,
        expected_manifest_sha256=args.expected_manifest_sha256,
        expected_catalog_sha256=args.expected_catalog_sha256,
    )
    print(
        json.dumps(
            {
                "identity": report["identity"],
                "candidate_reports": report["candidate_reports"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
