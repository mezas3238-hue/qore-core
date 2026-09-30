from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    CTraderDemoAccountType,
    collect_ctrader_demo_account_capability,
)
from qore.kernel.result import Success

T0 = datetime(2026, 9, 30, 18, 0, tzinfo=UTC)


class _Proto:
    def __init__(self, *, present: set[str] | None = None, **values: object) -> None:
        self._present = present or set(values)
        for name, value in values.items():
            setattr(self, name, value)

    def HasField(self, name: str) -> bool:
        return name in self._present


class _Client:
    is_ready = True
    account_id = 12345

    def __init__(self, *, trader: object) -> None:
        self.trader = trader
        self.calls: list[str] = []

    def connect_and_authenticate(self):
        raise AssertionError("ready client must not reconnect")

    def request(
        self,
        message_name: str,
        fields: dict[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ):
        assert fields["ctidTraderAccountId"] == self.account_id
        assert client_msg_id
        assert timeout_seconds == 10.0
        self.calls.append(message_name)
        if message_name == "ProtoOATraderReq":
            return Success(
                SimpleNamespace(
                    ctidTraderAccountId=self.account_id,
                    trader=self.trader,
                )
            )
        if message_name == "ProtoOASymbolsListReq":
            return Success(
                SimpleNamespace(
                    ctidTraderAccountId=self.account_id,
                    symbol=(
                        _Proto(
                            symbolId=20,
                            symbolName="US100",
                            enabled=True,
                            symbolCategoryId=2,
                            description="US Tech index",
                        ),
                        _Proto(
                            symbolId=10,
                            symbolName="EURUSD",
                            enabled=True,
                            symbolCategoryId=1,
                            description="Euro US Dollar",
                        ),
                    ),
                )
            )
        raise AssertionError(message_name)

    def wait_for_event(self, *args, **kwargs):
        raise AssertionError("capability observation uses no event stream")

    def close(self) -> None:
        return None


def test_account_capability_observes_hedged_mode_without_certifying_t16() -> None:
    client = _Client(
        trader=_Proto(
            present={"accountType"},
            accountType=0,
        )
    )

    result = collect_ctrader_demo_account_capability(
        client,
        observed_at=T0,
    )

    assert result.account_ref == "12345"
    assert result.account_type is CTraderDemoAccountType.HEDGED
    assert result.account_type_field_present is True
    assert result.same_symbol_opposite_positions_supported is True
    assert result.t16_hedge_instrument_certified is False
    assert result.t17_option_structure_certified is False
    assert result.productive_authority is False
    assert result.enabled_symbol_count == 2
    assert tuple(item.symbol_id for item in result.symbols) == (10, 20)
    assert result.catalog_sha256.startswith("sha256:")
    assert result.fingerprint().startswith("sha256:")
    assert client.calls == ["ProtoOATraderReq", "ProtoOASymbolsListReq"]


def test_missing_account_type_stays_unknown_and_never_infers_hedging() -> None:
    client = _Client(
        trader=_Proto(
            present=set(),
            accountType=0,
        )
    )

    result = collect_ctrader_demo_account_capability(
        client,
        observed_at=T0,
    )

    assert result.account_type is CTraderDemoAccountType.UNKNOWN
    assert result.account_type_field_present is False
    assert result.same_symbol_opposite_positions_supported is None
    assert result.t16_hedge_instrument_certified is False
    assert result.t17_option_structure_certified is False


def test_catalog_fingerprint_is_deterministic() -> None:
    left = collect_ctrader_demo_account_capability(
        _Client(trader=_Proto(present={"accountType"}, accountType=1)),
        observed_at=T0,
    )
    right = collect_ctrader_demo_account_capability(
        _Client(trader=_Proto(present={"accountType"}, accountType=1)),
        observed_at=T0,
    )

    assert left.account_type is CTraderDemoAccountType.NETTED
    assert left.same_symbol_opposite_positions_supported is False
    assert left.catalog_sha256 == right.catalog_sha256
    assert left.fingerprint() == right.fingerprint()
