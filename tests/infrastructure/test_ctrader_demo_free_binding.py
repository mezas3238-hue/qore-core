from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from qore.infrastructure.ctrader_demo_free_binding import (
    CTraderDemoFreeBindingError,
    discover_free_account_binding,
)
from qore.kernel.result import Success

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


class FakeClient:
    def __init__(self, *, ambiguous_nas: bool = False) -> None:
        self._ready = True
        names = ["XAUUSD", "EURUSD", "GBPUSD", "GBPJPY", "AUDJPY", "US100"]
        if ambiguous_nas:
            names.append("USTEC")
        self.light = tuple(
            SimpleNamespace(symbolId=index + 1, symbolName=name, enabled=True)
            for index, name in enumerate(names)
        )
        self.details = tuple(
            SimpleNamespace(
                symbolId=item.symbolId,
                digits=2 if item.symbolName in {"XAUUSD", "US100", "USTEC"} else 5,
                minVolume=100,
                maxVolume=100_000_000,
                stepVolume=100,
                lotSize=(
                    10_000
                    if item.symbolName == "XAUUSD"
                    else 100
                    if item.symbolName in {"US100", "USTEC"}
                    else 10_000_000
                ),
            )
            for item in self.light
        )

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def account_id(self) -> int:
        return 424242

    def connect_and_authenticate(self):
        self._ready = True
        return Success(None)

    def request(self, message_name, fields, *, client_msg_id, timeout_seconds):
        del fields, client_msg_id, timeout_seconds
        if message_name == "ProtoOATraderReq":
            return Success(
                SimpleNamespace(
                    ctidTraderAccountId=424242,
                    trader=SimpleNamespace(balance=10_000_000, moneyDigits=2),
                )
            )
        if message_name == "ProtoOASymbolsListReq":
            return Success(SimpleNamespace(symbol=self.light))
        if message_name == "ProtoOASymbolByIdReq":
            return Success(SimpleNamespace(symbol=self.details))
        raise AssertionError(message_name)


def test_discovers_all_active_symbols_and_actual_demo_balance() -> None:
    binding = discover_free_account_binding(FakeClient(), bound_at=NOW)

    assert binding.balance == Decimal("100000.00")
    assert binding.account.account_ref == "424242"
    assert len(binding.contracts) == 6
    assert len(binding.configuration.symbol_mappings) == 6
    assert binding.contract("EURUSD").lot_size_units == Decimal("100000.00")
    assert binding.contract("XAUUSD").lot_size_units == Decimal("100.00")
    assert binding.contract("NAS100").symbol_name == "US100"
    assert binding.contract("NAS100").lot_size_units == Decimal("1.00")


def test_ambiguous_nas_alias_fails_closed() -> None:
    with pytest.raises(CTraderDemoFreeBindingError, match="ambiguous"):
        discover_free_account_binding(FakeClient(ambiguous_nas=True), bound_at=NOW)
