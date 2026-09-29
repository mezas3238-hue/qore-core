from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


def _load_runner() -> ModuleType:
    path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "shared_gen2_ctrader_temporal_metadata.py"
    )
    spec = importlib.util.spec_from_file_location(
        "shared_gen2_ctrader_temporal_metadata",
        path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _native(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "symbolId": 10012,
        "scheduleTimeZone": "UTC",
        "tradingMode": 0,
        "schedule": (
            SimpleNamespace(startSecond=100, endSecond=200),
            SimpleNamespace(startSecond=10, endSecond=90),
        ),
        "holiday": (
            SimpleNamespace(
                holidayId=7,
                name="Holiday",
                description="Test holiday",
                scheduleTimeZone="UTC",
                holidayDate=20_000,
                isRecurring=False,
                startSecond=None,
                endSecond=None,
            ),
        ),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _light_native(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "symbolId": 10012,
        "symbolName": "US2000",
        "enabled": True,
        "baseAssetId": 501,
        "quoteAssetId": 502,
        "symbolCategoryId": 77,
        "description": "US Small Cap 2000 provider description",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _registry_row() -> dict[str, object]:
    return {
        "instrument_key": "CTRADER_DEMO:US2000:10012",
        "provider": "CTRADER_DEMO",
        "provider_symbol": "US2000",
        "provider_symbol_id": 10012,
    }


def test_provider_light_symbol_parser_preserves_descriptors_without_inference() -> None:
    module = _load_runner()

    row = module._parse_light_symbol_metadata(
        native=_light_native(),
        registry_row=_registry_row(),
    )

    assert row == {
        "provider_native_symbol_name": "US2000",
        "provider_base_asset_id": 501,
        "provider_quote_asset_id": 502,
        "provider_symbol_category_id": 77,
        "provider_description": "US Small Cap 2000 provider description",
    }


def test_provider_light_symbol_name_drift_fails_closed() -> None:
    module = _load_runner()

    with pytest.raises(
        module.Gen2ProviderScheduleError,
        match="name drift",
    ):
        module._parse_light_symbol_metadata(
            native=_light_native(symbolName="DIFFERENT"),
            registry_row=_registry_row(),
        )


def test_provider_schedule_parser_preserves_exact_identity_and_canonical_order() -> None:
    module = _load_runner()

    row = module._parse_symbol_metadata(
        native=_native(),
        registry_row=_registry_row(),
    )

    assert row["provider_symbol_id"] == 10012
    assert row["schedule_timezone"] == "UTC"
    assert row["schedule_intervals"] == [
        {"start_second": 10, "end_second": 90},
        {"start_second": 100, "end_second": 200},
    ]
    assert row["metadata_status"] == "COMPLETE_PROVIDER_SCHEDULE"
    assert row["holidays"][0]["holiday_id"] == 7


def test_provider_schedule_parser_allows_explicit_no_schedule_metadata() -> None:
    module = _load_runner()

    row = module._parse_symbol_metadata(
        native=_native(
            scheduleTimeZone=None,
            schedule=(),
            holiday=(),
        ),
        registry_row=_registry_row(),
    )

    assert row["metadata_status"] == "NO_PROVIDER_SCHEDULE_METADATA"


def test_provider_schedule_identity_drift_fails_closed() -> None:
    module = _load_runner()

    with pytest.raises(
        module.Gen2ProviderScheduleError,
        match="identity drift",
    ):
        module._parse_symbol_metadata(
            native=_native(symbolId=99999),
            registry_row=_registry_row(),
        )


def test_provider_schedule_invalid_interval_fails_closed() -> None:
    module = _load_runner()

    with pytest.raises(
        module.Gen2ProviderScheduleError,
        match="must advance",
    ):
        module._parse_symbol_metadata(
            native=_native(
                schedule=(
                    SimpleNamespace(startSecond=200, endSecond=100),
                )
            ),
            registry_row=_registry_row(),
        )


def test_provider_schedule_never_performs_canonical_calendar_mapping() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "shared_gen2_ctrader_temporal_metadata.py"
    ).read_text(encoding="utf-8")

    assert '"canonical_calendar_mapping_performed": False' in source
    assert '"provider_availability_is_canonical_market_hours": False' in source
    assert '"target_or_outcome_read": False' in source
    assert '"provider_native_identity_metadata_is_not_canonical_identity": True' in source
