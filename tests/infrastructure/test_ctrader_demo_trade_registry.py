import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.ctrader_demo_trade_registry import (
    CTraderDemoTradeRegistry,
    DemoTradeRegistryEntry,
)


NOW = datetime(2026, 9, 24, 15, 0, tzinfo=UTC)


def _entry(
    *,
    position_id: int | None = None,
) -> DemoTradeRegistryEntry:
    return DemoTradeRegistryEntry(
        trader="R38_EURUSD",
        signal_fingerprint="a" * 64,
        request_id="request-1",
        client_order_id="qore-client-1",
        provider_order_ref="12345",
        qore_symbol="EURUSD",
        requested_volume="0.10",
        requested_stop_risk="25.00",
        submitted_at=NOW.isoformat(),
        expires_at=(NOW + timedelta(hours=1)).isoformat(),
        position_id=position_id,
        capital_provenance=(
            ("ORIGINAL_BASE_CAPITAL", "base:signal", "25.00"),
        ),
    )


def test_registry_round_trip_and_position_binding(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    registry = CTraderDemoTradeRegistry(path)
    registry.register(_entry())

    reloaded = CTraderDemoTradeRegistry(path)
    assert reloaded.latest_for_trader("R38_EURUSD") == _entry()
    assert reloaded.by_position(99) is None

    bound = reloaded.bind_position("qore-client-1", 99)
    assert bound.position_id == 99
    assert CTraderDemoTradeRegistry(path).by_position(99) == bound


def test_registry_rejects_identity_conflict(tmp_path: Path) -> None:
    registry = CTraderDemoTradeRegistry(tmp_path / "registry.json")
    registry.register(_entry())
    conflicting = replace(
        _entry(),
        signal_fingerprint="b" * 64,
    )
    with pytest.raises(RuntimeError, match="identity conflict"):
        registry.register(conflicting)


def test_registry_allows_multiple_cibo_legs_on_one_netted_position(
    tmp_path: Path,
) -> None:
    path = tmp_path / "registry.json"
    registry = CTraderDemoTradeRegistry(path)
    first = _entry(position_id=99)
    second = DemoTradeRegistryEntry(
        trader="R38_EURUSD",
        signal_fingerprint="b" * 64,
        request_id="request-2",
        client_order_id="qore-client-2",
        provider_order_ref="12346",
        qore_symbol="EURUSD",
        requested_volume="0.20",
        requested_stop_risk="40.00",
        submitted_at=(NOW + timedelta(seconds=5)).isoformat(),
        expires_at=(NOW + timedelta(hours=1)).isoformat(),
        position_id=99,
    )
    registry.register(first)
    registry.register(second)

    legs = registry.entries_by_position(99)

    assert legs == (first, second)
    assert registry.by_position(99) == first



def test_registry_loads_legacy_entry_without_provenance(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy-registry.json"
    payload = {
        "schema": "qore.ctrader-demo.trade-registry.v1",
        "entries": [
            {
                "trader": "R38_EURUSD",
                "signal_fingerprint": "a" * 64,
                "request_id": "request-legacy",
                "client_order_id": "qore-legacy",
                "provider_order_ref": "legacy-ref",
                "qore_symbol": "EURUSD",
                "requested_volume": "0.10",
                "requested_stop_risk": "25.00",
                "submitted_at": NOW.isoformat(),
                "expires_at": (NOW + timedelta(hours=1)).isoformat(),
                "position_id": None,
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = CTraderDemoTradeRegistry(path).entries()

    assert len(loaded) == 1
    assert loaded[0].capital_provenance == ()
