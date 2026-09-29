"""Freeze cTrader provider schedule/holiday metadata for all GEN-1 sensors."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.ctrader_demo_lab_probe import (
    compute_ctrader_demo_lab_account_fingerprint,
)
from qore.infrastructure.ctrader_metadata_read_only import (
    CTraderMetadataReadOnlyMessageClient,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiPermissionScope,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
EXPECTED_REGISTRY_IDENTITY = "QORE_SHARED_GLOBAL_SENSOR_REGISTRY_001"


class Gen2ProviderScheduleError(RuntimeError):
    """The source-only provider schedule census failed closed."""


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise Gen2ProviderScheduleError(
        f"missing required environment input: {name}"
    )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise Gen2ProviderScheduleError("captured_at must be timezone-aware")
    return value


def _sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_registry(
    path: Path,
    *,
    expected_fingerprint: str,
) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise Gen2ProviderScheduleError(
            "global sensor registry must be JSON object"
        )
    payload = cast(dict[str, Any], raw)
    if payload.get("identity") != EXPECTED_REGISTRY_IDENTITY:
        raise Gen2ProviderScheduleError(
            "unexpected global sensor registry identity"
        )
    if payload.get("sensor_registry_fingerprint_sha256") != expected_fingerprint:
        raise Gen2ProviderScheduleError(
            "global sensor registry fingerprint drift"
        )
    rows = payload.get("sensors")
    if not isinstance(rows, list) or not rows:
        raise Gen2ProviderScheduleError("global sensor registry is empty")
    if payload.get("sensor_count") != len(rows):
        raise Gen2ProviderScheduleError(
            "global sensor registry count drift"
        )
    if any(row.get("disposition") != "DISCOVERED" for row in rows):
        raise Gen2ProviderScheduleError(
            "GEN-2 source census requires discovery-only registry"
        )
    return payload


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or type(value) is not int:
        raise Gen2ProviderScheduleError("provider metadata int field drift")
    return value


def _positive_int(value: object, *, field_name: str) -> int:
    parsed = _optional_int(value)
    if parsed is None or parsed <= 0:
        raise Gen2ProviderScheduleError(
            f"{field_name} must be positive int"
        )
    return parsed


def _optional_text(value: object, *, field_name: str) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise Gen2ProviderScheduleError(
            f"{field_name} must be string or empty"
        )
    return value


def _parse_provider_asset(native: object) -> dict[str, object]:
    return {
        "asset_id": _positive_int(
            getattr(native, "assetId", None),
            field_name="provider asset id",
        ),
        "name": _optional_text(
            getattr(native, "name", None),
            field_name="provider asset name",
        ),
        "display_name": _optional_text(
            getattr(native, "displayName", None),
            field_name="provider asset display name",
        ),
        "digits": _optional_int(getattr(native, "digits", None)),
    }


def _parse_provider_asset_class(native: object) -> dict[str, object]:
    return {
        "asset_class_id": _positive_int(
            getattr(native, "id", None),
            field_name="provider asset-class id",
        ),
        "name": _optional_text(
            getattr(native, "name", None),
            field_name="provider asset-class name",
        ),
    }


def _parse_provider_symbol_category(native: object) -> dict[str, object]:
    return {
        "symbol_category_id": _positive_int(
            getattr(native, "id", None),
            field_name="provider symbol-category id",
        ),
        "asset_class_id": _positive_int(
            getattr(native, "assetClassId", None),
            field_name="provider symbol-category asset-class id",
        ),
        "name": _optional_text(
            getattr(native, "name", None),
            field_name="provider symbol-category name",
        ),
    }


def _request_metadata_catalog(
    *,
    client: CTraderMetadataReadOnlyMessageClient,
    message_name: str,
    response_field: str,
    client_msg_id: str,
) -> tuple[object, ...]:
    result = client.request(
        message_name,
        {"ctidTraderAccountId": client.account_id},
        client_msg_id=client_msg_id,
        timeout_seconds=20.0,
    )
    if isinstance(result, Failure):
        raise Gen2ProviderScheduleError(
            f"cTrader provider metadata request failed: {message_name}"
        )
    if getattr(result.value, "ctidTraderAccountId", None) != client.account_id:
        raise Gen2ProviderScheduleError(
            f"provider metadata account identity drift: {message_name}"
        )
    rows = tuple(getattr(result.value, response_field, ()))
    if not rows:
        raise Gen2ProviderScheduleError(
            f"provider metadata response empty: {message_name}"
        )
    return rows


def _parse_light_symbol_metadata(
    *,
    native: object,
    registry_row: dict[str, object],
) -> dict[str, object]:
    """Preserve provider-native identity descriptors without canonical inference."""

    symbol_id = getattr(native, "symbolId", None)
    expected_id = registry_row.get("provider_symbol_id")
    if type(symbol_id) is not int or symbol_id != expected_id:
        raise Gen2ProviderScheduleError(
            "provider light-symbol identity drift"
        )
    symbol_name = getattr(native, "symbolName", None)
    expected_symbol = registry_row.get("provider_symbol")
    if not isinstance(symbol_name, str) or not symbol_name:
        raise Gen2ProviderScheduleError(
            "provider light-symbol name missing"
        )
    if symbol_name != expected_symbol:
        raise Gen2ProviderScheduleError(
            "provider light-symbol name drift"
        )
    if getattr(native, "enabled", None) is not True:
        raise Gen2ProviderScheduleError(
            "provider light-symbol unexpectedly disabled"
        )

    description = getattr(native, "description", None)
    if description == "":
        description = None
    if description is not None and not isinstance(description, str):
        raise Gen2ProviderScheduleError(
            "provider light-symbol description drift"
        )

    return {
        "provider_native_symbol_name": symbol_name,
        "provider_base_asset_id": _optional_int(
            getattr(native, "baseAssetId", None)
        ),
        "provider_quote_asset_id": _optional_int(
            getattr(native, "quoteAssetId", None)
        ),
        "provider_symbol_category_id": _optional_int(
            getattr(native, "symbolCategoryId", None)
        ),
        "provider_description": description,
    }


def _parse_symbol_metadata(
    *,
    native: object,
    registry_row: dict[str, object],
) -> dict[str, object]:
    symbol_id = getattr(native, "symbolId", None)
    expected_id = registry_row.get("provider_symbol_id")
    if type(symbol_id) is not int or symbol_id != expected_id:
        raise Gen2ProviderScheduleError(
            "provider symbol identity drift in schedule metadata"
        )

    schedule_timezone = getattr(native, "scheduleTimeZone", None)
    if schedule_timezone == "":
        schedule_timezone = None
    if schedule_timezone is not None and not isinstance(schedule_timezone, str):
        raise Gen2ProviderScheduleError(
            "provider schedule timezone field drift"
        )

    intervals: list[dict[str, int]] = []
    for interval in tuple(getattr(native, "schedule", ())):
        start = _optional_int(getattr(interval, "startSecond", None))
        end = _optional_int(getattr(interval, "endSecond", None))
        if start is None or end is None:
            raise Gen2ProviderScheduleError(
                "provider schedule interval missing boundary"
            )
        if not 0 <= start <= 604_800 or not 0 <= end <= 604_800:
            raise Gen2ProviderScheduleError(
                "provider schedule interval outside weekly range"
            )
        if end <= start:
            raise Gen2ProviderScheduleError(
                "provider weekly schedule interval must advance"
            )
        intervals.append(
            {
                "start_second": start,
                "end_second": end,
            }
        )
    intervals.sort(
        key=lambda item: (item["start_second"], item["end_second"])
    )

    holidays: list[dict[str, object]] = []
    for holiday in tuple(getattr(native, "holiday", ())):
        holiday_id = _optional_int(getattr(holiday, "holidayId", None))
        holiday_date = _optional_int(getattr(holiday, "holidayDate", None))
        if holiday_id is None or holiday_date is None:
            raise Gen2ProviderScheduleError(
                "provider holiday identity/date missing"
            )
        holiday_timezone = getattr(holiday, "scheduleTimeZone", None)
        if not isinstance(holiday_timezone, str) or not holiday_timezone:
            raise Gen2ProviderScheduleError(
                "provider holiday timezone missing"
            )
        name = getattr(holiday, "name", None)
        if not isinstance(name, str) or not name:
            raise Gen2ProviderScheduleError(
                "provider holiday name missing"
            )
        is_recurring = getattr(holiday, "isRecurring", None)
        if type(is_recurring) is not bool:
            raise Gen2ProviderScheduleError(
                "provider holiday recurrence flag drift"
            )
        holidays.append(
            {
                "holiday_id": holiday_id,
                "name": name,
                "description": getattr(holiday, "description", "") or "",
                "schedule_timezone": holiday_timezone,
                "holiday_date_days_since_epoch": holiday_date,
                "is_recurring": is_recurring,
                "start_second": _optional_int(
                    getattr(holiday, "startSecond", None)
                ),
                "end_second": _optional_int(
                    getattr(holiday, "endSecond", None)
                ),
            }
        )
    holidays.sort(
        key=lambda item: (
            int(item["holiday_date_days_since_epoch"]),
            int(item["holiday_id"]),
            str(item["name"]),
        )
    )

    if intervals and schedule_timezone:
        metadata_status = "COMPLETE_PROVIDER_SCHEDULE"
    elif intervals or schedule_timezone or holidays:
        metadata_status = "PARTIAL_PROVIDER_SCHEDULE"
    else:
        metadata_status = "NO_PROVIDER_SCHEDULE_METADATA"

    return {
        "instrument_key": registry_row["instrument_key"],
        "provider": registry_row["provider"],
        "provider_symbol": registry_row["provider_symbol"],
        "provider_symbol_id": expected_id,
        "schedule_timezone": schedule_timezone,
        "trading_mode": _optional_int(
            getattr(native, "tradingMode", None)
        ),
        "schedule_intervals": intervals,
        "holidays": holidays,
        "metadata_status": metadata_status,
    }


def run(
    *,
    registry_path: Path,
    output_path: Path,
    expected_registry_fingerprint: str,
    captured_at: datetime,
    source_run_id: int,
    source_artifact_id: int,
    source_git_sha: str,
) -> dict[str, object]:
    registry = _load_registry(
        registry_path,
        expected_fingerprint=expected_registry_fingerprint,
    )
    rows = cast(list[dict[str, object]], registry["sensors"])
    by_id = {
        cast(int, row["provider_symbol_id"]): row
        for row in rows
    }
    if len(by_id) != len(rows):
        raise Gen2ProviderScheduleError(
            "duplicate provider symbol id in GEN-1 registry"
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
    read_only_client = CTraderMetadataReadOnlyMessageClient(native_client)

    parsed: list[dict[str, object]] = []
    try:
        ready = read_only_client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise Gen2ProviderScheduleError(
                "cTrader DEMO authentication failed"
            )
        assets = tuple(
            sorted(
                (
                    _parse_provider_asset(item)
                    for item in _request_metadata_catalog(
                        client=read_only_client,
                        message_name="ProtoOAAssetListReq",
                        response_field="asset",
                        client_msg_id="shared-gen2-provider-assets",
                    )
                ),
                key=lambda item: int(item["asset_id"]),
            )
        )
        asset_classes = tuple(
            sorted(
                (
                    _parse_provider_asset_class(item)
                    for item in _request_metadata_catalog(
                        client=read_only_client,
                        message_name="ProtoOAAssetClassListReq",
                        response_field="assetClass",
                        client_msg_id="shared-gen2-provider-asset-classes",
                    )
                ),
                key=lambda item: int(item["asset_class_id"]),
            )
        )
        symbol_categories = tuple(
            sorted(
                (
                    _parse_provider_symbol_category(item)
                    for item in _request_metadata_catalog(
                        client=read_only_client,
                        message_name="ProtoOASymbolCategoryListReq",
                        response_field="symbolCategory",
                        client_msg_id="shared-gen2-provider-symbol-categories",
                    )
                ),
                key=lambda item: int(item["symbol_category_id"]),
            )
        )
        asset_by_id = {int(item["asset_id"]): item for item in assets}
        asset_class_by_id = {
            int(item["asset_class_id"]): item
            for item in asset_classes
        }
        category_by_id = {
            int(item["symbol_category_id"]): item
            for item in symbol_categories
        }
        if len(asset_by_id) != len(assets):
            raise Gen2ProviderScheduleError(
                "duplicate provider asset identity"
            )
        if len(asset_class_by_id) != len(asset_classes):
            raise Gen2ProviderScheduleError(
                "duplicate provider asset-class identity"
            )
        if len(category_by_id) != len(symbol_categories):
            raise Gen2ProviderScheduleError(
                "duplicate provider symbol-category identity"
            )

        ids = tuple(sorted(by_id))
        listed = read_only_client.request(
            "ProtoOASymbolsListReq",
            {
                "ctidTraderAccountId": read_only_client.account_id,
                "includeArchivedSymbols": False,
            },
            client_msg_id="shared-gen2-provider-light-symbols",
            timeout_seconds=20.0,
        )
        if isinstance(listed, Failure):
            raise Gen2ProviderScheduleError(
                "cTrader provider light-symbol metadata request failed"
            )
        if (
            getattr(listed.value, "ctidTraderAccountId", None)
            != read_only_client.account_id
        ):
            raise Gen2ProviderScheduleError(
                "provider light-symbol account identity drift"
            )
        light_symbols = tuple(getattr(listed.value, "symbol", ()))
        light_by_id: dict[int, dict[str, object]] = {}
        for native in light_symbols:
            symbol_id = getattr(native, "symbolId", None)
            if symbol_id not in by_id:
                continue
            if type(symbol_id) is not int:
                raise Gen2ProviderScheduleError(
                    "provider light-symbol id drift"
                )
            if symbol_id in light_by_id:
                raise Gen2ProviderScheduleError(
                    "duplicate provider light-symbol identity"
                )
            light_by_id[symbol_id] = _parse_light_symbol_metadata(
                native=native,
                registry_row=by_id[symbol_id],
            )
        if set(light_by_id) != set(ids):
            raise Gen2ProviderScheduleError(
                "provider light-symbol coverage drift"
            )
        for symbol_id, item in light_by_id.items():
            base_id = cast(int | None, item["provider_base_asset_id"])
            quote_id = cast(int | None, item["provider_quote_asset_id"])
            category_id = cast(
                int | None,
                item["provider_symbol_category_id"],
            )
            if base_id is None or base_id not in asset_by_id:
                raise Gen2ProviderScheduleError(
                    "provider base-asset coverage drift"
                )
            if quote_id is None or quote_id not in asset_by_id:
                raise Gen2ProviderScheduleError(
                    "provider quote-asset coverage drift"
                )
            if category_id is None or category_id not in category_by_id:
                raise Gen2ProviderScheduleError(
                    "provider symbol-category coverage drift"
                )
            category = category_by_id[category_id]
            asset_class_id = int(category["asset_class_id"])
            if asset_class_id not in asset_class_by_id:
                raise Gen2ProviderScheduleError(
                    "provider asset-class coverage drift"
                )
            item.update(
                {
                    "provider_base_asset_name": (
                        asset_by_id[base_id]["name"]
                    ),
                    "provider_base_asset_display_name": (
                        asset_by_id[base_id]["display_name"]
                    ),
                    "provider_quote_asset_name": (
                        asset_by_id[quote_id]["name"]
                    ),
                    "provider_quote_asset_display_name": (
                        asset_by_id[quote_id]["display_name"]
                    ),
                    "provider_symbol_category_name": category["name"],
                    "provider_asset_class_id": asset_class_id,
                    "provider_asset_class_name": (
                        asset_class_by_id[asset_class_id]["name"]
                    ),
                }
            )

        for batch_index in range(0, len(ids), 50):
            batch = ids[batch_index : batch_index + 50]
            result = read_only_client.request(
                "ProtoOASymbolByIdReq",
                {
                    "ctidTraderAccountId": read_only_client.account_id,
                    "symbolId": list(batch),
                },
                client_msg_id=(
                    "shared-gen2-provider-schedule-"
                    f"{batch_index // 50}"
                ),
                timeout_seconds=20.0,
            )
            if isinstance(result, Failure):
                raise Gen2ProviderScheduleError(
                    "cTrader provider schedule metadata request failed"
                )
            if (
                getattr(result.value, "ctidTraderAccountId", None)
                != read_only_client.account_id
            ):
                raise Gen2ProviderScheduleError(
                    "provider schedule account identity drift"
                )
            native_symbols = tuple(getattr(result.value, "symbol", ()))
            returned = {
                getattr(item, "symbolId", None)
                for item in native_symbols
            }
            if returned != set(batch):
                raise Gen2ProviderScheduleError(
                    "provider schedule batch identity coverage drift"
                )
            for native in native_symbols:
                symbol_id = getattr(native, "symbolId", None)
                if type(symbol_id) is not int:
                    raise Gen2ProviderScheduleError(
                        "provider symbol id missing from full metadata"
                    )
                full_metadata = _parse_symbol_metadata(
                    native=native,
                    registry_row=by_id[symbol_id],
                )
                full_metadata.update(light_by_id[symbol_id])
                parsed.append(full_metadata)
    finally:
        read_only_client.close()

    parsed.sort(key=lambda item: str(item["instrument_key"]))
    if len(parsed) != len(rows):
        raise Gen2ProviderScheduleError(
            "provider schedule catalogue count drift"
        )
    descriptor_payload = {
        "assets": assets,
        "asset_classes": asset_classes,
        "symbol_categories": symbol_categories,
        "symbols": [
            {
                key: item.get(key)
                for key in (
                    "instrument_key",
                    "provider_symbol_id",
                    "provider_native_symbol_name",
                    "provider_base_asset_id",
                    "provider_base_asset_name",
                    "provider_base_asset_display_name",
                    "provider_quote_asset_id",
                    "provider_quote_asset_name",
                    "provider_quote_asset_display_name",
                    "provider_symbol_category_id",
                    "provider_symbol_category_name",
                    "provider_asset_class_id",
                    "provider_asset_class_name",
                    "provider_description",
                )
            }
            for item in parsed
        ],
    }
    descriptor_fingerprint = _sha256(descriptor_payload)
    payload_for_hash = {
        "identity": IDENTITY,
        "source_registry_fingerprint": expected_registry_fingerprint,
        "captured_at": _aware(captured_at).isoformat(timespec="microseconds"),
        "provider_assets": assets,
        "provider_asset_classes": asset_classes,
        "provider_symbol_categories": symbol_categories,
        "provider_identity_descriptor_fingerprint_sha256": (
            descriptor_fingerprint
        ),
        "symbols": parsed,
    }
    schedule_fingerprint = _sha256(payload_for_hash)
    status_counts: dict[str, int] = {}
    for item in parsed:
        status = cast(str, item["metadata_status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    report: dict[str, object] = {
        **payload_for_hash,
        "status": "provider_schedule_metadata_frozen",
        "source_registry_run_id": source_run_id,
        "source_registry_artifact_id": source_artifact_id,
        "source_registry_git_sha": source_git_sha,
        "sensor_count": len(parsed),
        "provider_schedule_catalog_fingerprint_sha256": schedule_fingerprint,
        "metadata_status_counts": dict(sorted(status_counts.items())),
        "provider_native_identity_metadata_captured": True,
        "provider_native_identity_metadata_is_not_canonical_identity": True,
        "provider_native_identity_metadata_coverage_count": len(light_by_id),
        "provider_asset_count": len(assets),
        "provider_asset_class_count": len(asset_classes),
        "provider_symbol_category_count": len(symbol_categories),
        "provider_identity_descriptor_fingerprint_sha256": (
            descriptor_fingerprint
        ),
        "account_fingerprint": (
            compute_ctrader_demo_lab_account_fingerprint(
                read_only_client.account_id
            )
        ),
        "canonical_calendar_mapping_performed": False,
        "provider_availability_is_canonical_market_hours": False,
        "market_history_read": False,
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


def _parse_aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return _aware(parsed)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-registry-fingerprint", required=True)
    parser.add_argument("--captured-at", type=_parse_aware, required=True)
    parser.add_argument("--source-run-id", type=int, required=True)
    parser.add_argument("--source-artifact-id", type=int, required=True)
    parser.add_argument("--source-git-sha", required=True)
    args = parser.parse_args()

    report = run(
        registry_path=args.registry,
        output_path=args.output,
        expected_registry_fingerprint=args.expected_registry_fingerprint,
        captured_at=args.captured_at,
        source_run_id=args.source_run_id,
        source_artifact_id=args.source_artifact_id,
        source_git_sha=args.source_git_sha,
    )
    print(
        json.dumps(
            {
                "identity": report["identity"],
                "sensor_count": report["sensor_count"],
                "metadata_status_counts": report["metadata_status_counts"],
                "provider_native_identity_metadata_coverage_count": report[
                    "provider_native_identity_metadata_coverage_count"
                ],
                "provider_schedule_catalog_fingerprint_sha256": report[
                    "provider_schedule_catalog_fingerprint_sha256"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
