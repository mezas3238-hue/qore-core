from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.ctrader_demo_free_position_service import DemoPosition
from qore.infrastructure.ctrader_demo_mt5_management_adapter import (
    CTraderDemoMt5ManagementAdapter,
)
from qore.infrastructure.ctrader_demo_trade_registry import (
    CTraderDemoTradeRegistry,
    DemoTradeRegistryEntry,
)


NOW = datetime(2026, 9, 24, 15, 0, tzinfo=UTC)


class FakePositions:
    def __init__(self):
        self.amended = []
        self.closed = []

    def positions(self):
        return (
            DemoPosition(
                position_id=101,
                trader_id=TraderLineage.R38_EURUSD,
                qore_symbol="EURUSD",
                provider_symbol="EURUSD",
                side="long",
                volume_units=Decimal("10000"),
                entry_price=Decimal("1.1000"),
                stop_loss=Decimal("1.0950"),
                take_profit=Decimal("1.1100"),
                opened_at=NOW,
                comment="demo",
            ),
        )

    def deals(self, **kwargs):
        return ()

    def amend_protection(self, **kwargs):
        self.amended.append(kwargs)

    def close_position(self, **kwargs):
        self.closed.append(kwargs)

    def order_status(self, *, order_id):
        return 1

    def cancel_order(self, *, order_id):
        return None


class FakeMt5:
    def symbol_info(self, symbol):
        return SimpleNamespace(
            trade_tick_size=0.00001,
            volume_step=0.01,
            filling_mode=2,
            trade_exemode=2,
        )

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(
            bid=1.1000,
            ask=1.1001,
            time_msc=int(NOW.timestamp() * 1000),
        )

    def copy_rates_from_pos(self, *args, **kwargs):
        return ()

    def copy_rates_range(self, *args, **kwargs):
        return ()


def _adapter(tmp_path):
    registry = CTraderDemoTradeRegistry(tmp_path / "registry.json")
    registry.register(
        DemoTradeRegistryEntry(
            trader="R38_EURUSD",
            signal_fingerprint="a" * 64,
            request_id="request-1",
            client_order_id="qore-client-1",
            provider_order_ref="12345",
            qore_symbol="EURUSD",
            requested_volume="0.10",
            requested_stop_risk="25",
            submitted_at=NOW.isoformat(),
            expires_at=(NOW + timedelta(hours=1)).isoformat(),
            position_id=101,
        )
    )
    binding = tmp_path / "binding.json"
    binding.write_text(
        '{"contracts":[{"qore_symbol":"EURUSD","source_contract_size_units":"100000"}]}',
        encoding="utf-8",
    )
    positions = FakePositions()
    adapter = CTraderDemoMt5ManagementAdapter(
        mt5_market_api=FakeMt5(),
        positions=positions,
        registry=registry,
        binding_path=binding,
    )
    return adapter, positions


def test_adapter_translates_sltp_to_ctrader_demo(tmp_path):
    adapter, positions = _adapter(tmp_path)
    synthetic = adapter.positions_get(symbol="EURUSD")
    assert len(synthetic) == 1
    assert Decimal(str(synthetic[0].volume)) == Decimal("0.1")

    request = {
        "action": adapter.TRADE_ACTION_SLTP,
        "position": 101,
        "sl": 1.0960,
        "tp": 1.1120,
    }
    assert adapter.order_check(request).retcode == 0
    assert adapter.order_send(request).retcode == adapter.TRADE_RETCODE_DONE
    assert positions.amended[0]["position_id"] == 101


def test_adapter_translates_partial_close_without_mt5_mutation(tmp_path):
    adapter, positions = _adapter(tmp_path)
    request = {
        "action": adapter.TRADE_ACTION_DEAL,
        "position": 101,
        "volume": 0.05,
    }
    assert adapter.order_check(request).retcode == 0
    result = adapter.order_send(request)
    assert result.retcode == adapter.TRADE_RETCODE_DONE_PARTIAL
    assert positions.closed == [
        {"position_id": 101, "volume_units": Decimal("5000.00")}
    ]
