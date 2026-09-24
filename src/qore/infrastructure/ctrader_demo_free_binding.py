"""Authenticated binding for the unrestricted QORE cTrader DEMO account."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoOperationalLimits,
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
    ctrader_demo_secret_requirements,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiMessageClientBoundary,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import ExecutionInstrument
from qore.infrastructure.transport import ExternalTransportTimeout
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure

_NATIVE_VOLUME_UNIT = Decimal("0.01")
_ALIASES: dict[str, tuple[str, ...]] = {
    "XAUUSD": ("XAUUSD", "GOLD"),
    "EURUSD": ("EURUSD",),
    "GBPUSD": ("GBPUSD",),
    "GBPJPY": ("GBPJPY",),
    "AUDJPY": ("AUDJPY",),
    "NAS100": ("NAS100", "US100", "USTEC", "NDX100"),
}


class CTraderDemoFreeBindingError(InfrastructureError):
    __slots__ = ()


def _norm(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _positive_int(value: object, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise CTraderDemoFreeBindingError(f"{name} must be a positive int")
    return value


@dataclass(frozen=True, slots=True)
class CTraderDemoNativeContract:
    qore_symbol: str
    symbol_id: int
    symbol_name: str
    digits: int
    min_volume_units: int
    max_volume_units: int
    step_volume_units: int
    lot_size_units: Decimal

    def __post_init__(self) -> None:
        if self.qore_symbol not in _ALIASES:
            raise CTraderDemoFreeBindingError("unsupported QORE DEMO symbol")
        _positive_int(self.symbol_id, "symbol_id")
        if not self.symbol_name:
            raise CTraderDemoFreeBindingError("symbol_name is required")
        if type(self.digits) is not int or self.digits < 0:
            raise CTraderDemoFreeBindingError("digits must be non-negative int")
        for name, value in (
            ("min_volume_units", self.min_volume_units),
            ("max_volume_units", self.max_volume_units),
            ("step_volume_units", self.step_volume_units),
        ):
            _positive_int(value, name)
        if self.min_volume_units > self.max_volume_units:
            raise CTraderDemoFreeBindingError("cTrader volume bounds are inverted")
        if (
            not isinstance(self.lot_size_units, Decimal)
            or not self.lot_size_units.is_finite()
            or self.lot_size_units <= 0
        ):
            raise CTraderDemoFreeBindingError("lot_size_units must be positive")


@dataclass(frozen=True, slots=True)
class CTraderDemoFreeBinding:
    account: MarketTestAccountIdentity
    balance: Decimal
    money_digits: int
    contracts: tuple[CTraderDemoNativeContract, ...]
    configuration: CTraderDemoRuntimeConfiguration
    bound_at: datetime

    def __post_init__(self) -> None:
        if self.account.environment is not MarketRuntimeEnvironment.DEMO:
            raise CTraderDemoFreeBindingError("binding must remain DEMO-only")
        if not self.balance.is_finite() or self.balance <= 0:
            raise CTraderDemoFreeBindingError("DEMO balance must be positive")
        if type(self.money_digits) is not int or self.money_digits < 0:
            raise CTraderDemoFreeBindingError("money_digits must be non-negative")
        if len(self.contracts) != len(_ALIASES):
            raise CTraderDemoFreeBindingError("all active Trader symbols must bind")
        if self.configuration.account != self.account:
            raise CTraderDemoFreeBindingError("configuration account mismatch")
        if self.bound_at.tzinfo is None or self.bound_at.utcoffset() is None:
            raise CTraderDemoFreeBindingError("bound_at must be timezone-aware")

    def contract(self, qore_symbol: str) -> CTraderDemoNativeContract:
        for item in self.contracts:
            if item.qore_symbol == qore_symbol:
                return item
        raise CTraderDemoFreeBindingError(f"missing cTrader contract for {qore_symbol}")


def _select_light_symbol(
    qore_symbol: str,
    symbols: tuple[object, ...],
) -> object:
    aliases = tuple(_norm(item) for item in _ALIASES[qore_symbol])
    exact = [
        item
        for item in symbols
        if _norm(str(getattr(item, "symbolName", ""))) == _norm(qore_symbol)
    ]
    if len(exact) == 1:
        return exact[0]
    matches = [item for item in symbols if _norm(str(getattr(item, "symbolName", ""))) in aliases]
    if len(matches) != 1:
        raise CTraderDemoFreeBindingError(
            f"cTrader DEMO symbol binding is ambiguous or absent for {qore_symbol}"
        )
    return matches[0]


def _request(
    client: CTraderOpenApiMessageClientBoundary,
    name: str,
    fields: dict[str, object],
    msg_id: str,
) -> object:
    result = client.request(
        name,
        fields,
        client_msg_id=msg_id,
        timeout_seconds=10.0,
    )
    if isinstance(result, Failure):
        raise CTraderDemoFreeBindingError(str(result.error))
    return result.value


def discover_free_account_binding(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    bound_at: datetime | None = None,
) -> CTraderDemoFreeBinding:
    if not client.is_ready:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise CTraderDemoFreeBindingError(str(connected.error))
    account_id = _positive_int(client.account_id, "cTrader DEMO account id")
    trader_res = _request(
        client,
        "ProtoOATraderReq",
        {"ctidTraderAccountId": account_id},
        "qore-free-demo-trader",
    )
    if getattr(trader_res, "ctidTraderAccountId", None) != account_id:
        raise CTraderDemoFreeBindingError("trader response account mismatch")
    trader = getattr(trader_res, "trader", None)
    if trader is None:
        raise CTraderDemoFreeBindingError("trader response missing account")
    balance_raw = _positive_int(getattr(trader, "balance", None), "balance")
    money_digits = getattr(trader, "moneyDigits", 0)
    if type(money_digits) is not int or money_digits < 0:
        raise CTraderDemoFreeBindingError("invalid moneyDigits")
    balance = Decimal(balance_raw).scaleb(-money_digits)

    listed = _request(
        client,
        "ProtoOASymbolsListReq",
        {
            "ctidTraderAccountId": account_id,
            "includeArchivedSymbols": False,
        },
        "qore-free-demo-symbol-list",
    )
    native_light = getattr(listed, "symbol", None)
    if native_light is None:
        raise CTraderDemoFreeBindingError("cTrader symbol list missing")
    light_symbols = tuple(native_light)
    selected = {
        qore_symbol: _select_light_symbol(qore_symbol, light_symbols) for qore_symbol in _ALIASES
    }
    symbol_ids = [
        _positive_int(getattr(item, "symbolId", None), "symbolId") for item in selected.values()
    ]
    details = _request(
        client,
        "ProtoOASymbolByIdReq",
        {"ctidTraderAccountId": account_id, "symbolId": symbol_ids},
        "qore-free-demo-symbol-details",
    )
    native_details = getattr(details, "symbol", None)
    if native_details is None:
        raise CTraderDemoFreeBindingError("cTrader symbol details missing")
    by_id = {
        _positive_int(getattr(item, "symbolId", None), "detail symbolId"): item
        for item in native_details
    }

    contracts: list[CTraderDemoNativeContract] = []
    mappings: list[CTraderSymbolMapping] = []
    for qore_symbol, light in selected.items():
        symbol_id = _positive_int(getattr(light, "symbolId", None), "symbolId")
        if getattr(light, "enabled", None) is not True:
            raise CTraderDemoFreeBindingError(f"{qore_symbol} is disabled on cTrader DEMO")
        native = by_id.get(symbol_id)
        if native is None:
            raise CTraderDemoFreeBindingError(f"missing details for {qore_symbol}")
        min_volume = _positive_int(getattr(native, "minVolume", None), "minVolume")
        max_volume = _positive_int(getattr(native, "maxVolume", None), "maxVolume")
        step_volume = _positive_int(getattr(native, "stepVolume", None), "stepVolume")
        lot_size_cents = _positive_int(getattr(native, "lotSize", None), "lotSize")
        digits = getattr(native, "digits", None)
        if type(digits) is not int or digits < 0:
            raise CTraderDemoFreeBindingError("invalid symbol digits")
        symbol_name = str(getattr(light, "symbolName", ""))
        contract = CTraderDemoNativeContract(
            qore_symbol=qore_symbol,
            symbol_id=symbol_id,
            symbol_name=symbol_name,
            digits=digits,
            min_volume_units=min_volume,
            max_volume_units=max_volume,
            step_volume_units=step_volume,
            lot_size_units=Decimal(lot_size_cents) * _NATIVE_VOLUME_UNIT,
        )
        contracts.append(contract)
        mappings.append(
            CTraderSymbolMapping(
                instrument=ExecutionInstrument(qore_symbol),
                symbol_id=symbol_id,
                symbol_name=symbol_name,
                digits=digits,
                volume_step=_NATIVE_VOLUME_UNIT,
                min_volume_units=min_volume,
                max_volume_units=max_volume,
                step_volume_units=step_volume,
            )
        )

    account = MarketTestAccountIdentity(
        provider_key="ctrader-demo",
        account_ref=str(account_id),
        environment=MarketRuntimeEnvironment.DEMO,
    )
    configuration = CTraderDemoRuntimeConfiguration(
        provider_key="ctrader-demo",
        environment=MarketRuntimeEnvironment.DEMO,
        endpoint=ProviderEndpoint(host="demo.ctraderapi.com", port=5035),
        account=account,
        symbol_mappings=tuple(sorted(mappings, key=lambda item: item.instrument.value)),
        capabilities=(
            CTraderDemoCapability.ACCOUNT,
            CTraderDemoCapability.CANDLES,
            CTraderDemoCapability.ORDERS,
        ),
        rest_timeout=ExternalTransportTimeout(milliseconds=3000),
        limits=CTraderDemoOperationalLimits(order_requests_per_second=1),
        secret_requirements=ctrader_demo_secret_requirements(),
    )
    observed = bound_at or datetime.now(UTC)
    return CTraderDemoFreeBinding(
        account=account,
        balance=balance,
        money_digits=money_digits,
        contracts=tuple(sorted(contracts, key=lambda item: item.qore_symbol)),
        configuration=configuration,
        bound_at=observed,
    )


def binding_fingerprint(binding: CTraderDemoFreeBinding) -> str:
    material = "|".join(
        [
            "ctrader-demo-free-binding-v1",
            format(binding.balance, "f"),
            *(
                f"{item.qore_symbol}:{item.symbol_id}:{item.symbol_name}:"
                f"{item.digits}:{item.min_volume_units}:{item.max_volume_units}:"
                f"{item.step_volume_units}:{format(item.lot_size_units, 'f')}"
                for item in binding.contracts
            ),
        ]
    )
    return uuid5(NAMESPACE_URL, material).hex
