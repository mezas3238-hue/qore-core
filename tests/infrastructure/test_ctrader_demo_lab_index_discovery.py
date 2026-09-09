from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from qore.infrastructure.ctrader_demo_lab_index_discovery import (
    CTraderDemoIndexDiscovery,
    CTraderDemoIndexSymbolTarget,
    resolve_index_light_symbols,
)
from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabProbeError,
    CTraderDemoLabSymbolEvidence,
)


def _light(symbol_id: int, name: str, *, enabled: bool = True) -> object:
    return SimpleNamespace(
        symbolId=symbol_id,
        symbolName=name,
        enabled=enabled,
    )


def _symbol(symbol_id: int, name: str) -> CTraderDemoLabSymbolEvidence:
    return CTraderDemoLabSymbolEvidence(
        symbol_id=symbol_id,
        symbol_name=name,
        digits=2,
        min_volume_units=100,
        max_volume_units=100_000,
        step_volume_units=100,
    )


def test_resolve_index_light_symbols_requires_exact_unique_aliases() -> None:
    resolved = resolve_index_light_symbols(
        (
            _light(101, "SPX500"),
            _light(202, "US30"),
            _light(303, "USTEC"),
            _light(404, "EURUSD"),
        )
    )

    assert resolved == (
        ("SP500", 101, "SPX500"),
        ("US30", 202, "US30"),
        ("NAS100", 303, "USTEC"),
    )


def test_resolve_index_light_symbols_ignores_disabled_alias() -> None:
    resolved = resolve_index_light_symbols(
        (
            _light(100, "SP500", enabled=False),
            _light(101, "US500"),
            _light(202, "DJ30"),
            _light(303, "NAS100"),
        )
    )

    assert resolved[0] == ("SP500", 101, "US500")


def test_resolve_index_light_symbols_rejects_ambiguous_target() -> None:
    with pytest.raises(
        CTraderDemoLabProbeError,
        match="SP500 requires exactly one enabled alias match",
    ):
        resolve_index_light_symbols(
            (
                _light(101, "SP500"),
                _light(102, "US500"),
                _light(202, "US30"),
                _light(303, "NAS100"),
            )
        )


def test_resolve_index_light_symbols_rejects_missing_target() -> None:
    with pytest.raises(
        CTraderDemoLabProbeError,
        match="NAS100 requires exactly one enabled alias match",
    ):
        resolve_index_light_symbols(
            (
                _light(101, "SP500"),
                _light(202, "US30"),
            )
        )


def test_discovery_payload_does_not_claim_economic_identity_certification() -> None:
    discovery = CTraderDemoIndexDiscovery(
        account_fingerprint="a" * 64,
        checked_at=datetime(2026, 9, 9, 5, 0, tzinfo=UTC),
        targets=(
            CTraderDemoIndexSymbolTarget("SP500", _symbol(101, "US500")),
            CTraderDemoIndexSymbolTarget("US30", _symbol(202, "US30")),
            CTraderDemoIndexSymbolTarget("NAS100", _symbol(303, "USTEC")),
        ),
    )

    payload = discovery.sanitized_payload()
    targets = payload["targets"]
    assert isinstance(targets, list)
    assert all(item["economic_identity_certified"] is False for item in targets)
    assert payload["read_only"] is True
    assert payload["account_is_live"] is False
