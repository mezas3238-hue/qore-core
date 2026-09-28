"""Read-only cTrader DEMO execution-economics calibration probe.

The probe reads provider-native contracts, precise commission metadata, current
spot spread and broker expected-margin responses. It never sends, amends or
cancels an order. Historical execution economics are not claimed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.ctrader_demo_free_binding import (
    discover_free_account_binding,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiMessageClientBoundary,
)
from qore.kernel.result import Failure

_PRICE_SCALE = Decimal("100000")
_VOLUME_UNIT = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class CTraderExpectedMarginQuote:
    native_volume_cents: int
    buy_margin_usd: Decimal
    sell_margin_usd: Decimal

    def __post_init__(self) -> None:
        if (
            not isinstance(self.native_volume_cents, int)
            or isinstance(self.native_volume_cents, bool)
            or self.native_volume_cents <= 0
        ):
            raise CiboCapitalManagementError(
                "expected-margin volume must be positive int"
            )
        for name in ("buy_margin_usd", "sell_margin_usd"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite positive Decimal"
                )


@dataclass(frozen=True, slots=True)
class CTraderNativeCommissionTerms:
    precise_rate_raw: int | None
    commission_type: int | None
    precise_minimum_raw: int | None
    minimum_type: int | None
    minimum_asset: str | None

    @property
    def complete(self) -> bool:
        return (
            self.precise_rate_raw is not None
            and self.commission_type is not None
            and self.precise_minimum_raw is not None
            and self.minimum_type is not None
            and self.minimum_asset is not None
        )


@dataclass(frozen=True, slots=True)
class CTraderProviderEconomicsSymbolEvidence:
    qore_symbol: str
    provider_symbol: str
    symbol_id: int
    observed_at: datetime
    digits: int
    bid: Decimal
    ask: Decimal
    min_volume_cents: int
    max_volume_cents: int
    step_volume_cents: int
    lot_size_cents: int
    commission: CTraderNativeCommissionTerms
    expected_margin: tuple[CTraderExpectedMarginQuote, ...]
    margin_native_ready: bool
    spread_native_ready: bool
    slippage_empirically_calibrated: bool = False
    historical_exact_claimed: bool = False

    def __post_init__(self) -> None:
        if not self.qore_symbol or not self.provider_symbol:
            raise CiboCapitalManagementError(
                "provider economics symbol identity required"
            )
        if self.symbol_id <= 0:
            raise CiboCapitalManagementError("symbol id must be positive")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "provider economics observed_at must be timezone-aware"
            )
        if self.bid <= 0 or self.ask < self.bid:
            raise CiboCapitalManagementError("provider economics spot invalid")
        if any(
            value <= 0
            for value in (
                self.min_volume_cents,
                self.max_volume_cents,
                self.step_volume_cents,
                self.lot_size_cents,
            )
        ):
            raise CiboCapitalManagementError(
                "provider economics volume terms must be positive"
            )
        if type(self.margin_native_ready) is not bool:
            raise CiboCapitalManagementError(
                "margin_native_ready must be bool"
            )
        if type(self.spread_native_ready) is not bool:
            raise CiboCapitalManagementError(
                "spread_native_ready must be bool"
            )
        if self.slippage_empirically_calibrated or self.historical_exact_claimed:
            raise CiboCapitalManagementError(
                "read-only provider probe cannot claim slippage/history"
            )

    @property
    def commission_native_ready(self) -> bool:
        return self.commission.complete

    @property
    def provider_terms_ready(self) -> bool:
        return (
            self.margin_native_ready
            and self.spread_native_ready
            and self.commission_native_ready
        )


@dataclass(frozen=True, slots=True)
class CTraderProviderEconomicsProbe:
    account_ref: str
    observed_at: datetime
    symbols: tuple[CTraderProviderEconomicsSymbolEvidence, ...]
    broker_mutation_performed: bool = False
    historical_exact_claimed: bool = False
    holdout_outcomes_used: bool = False
    target_aware: bool = False

    def __post_init__(self) -> None:
        if not self.account_ref or not self.symbols:
            raise CiboCapitalManagementError(
                "provider economics probe account/symbols required"
            )
        if (
            self.broker_mutation_performed
            or self.historical_exact_claimed
            or self.holdout_outcomes_used
            or self.target_aware
        ):
            raise CiboCapitalManagementError(
                "provider economics probe governance violation"
            )
        codes = tuple(item.qore_symbol for item in self.symbols)
        if len(codes) != len(set(codes)):
            raise CiboCapitalManagementError(
                "provider economics symbols must be unique"
            )

    @property
    def provider_terms_ready(self) -> bool:
        return all(item.provider_terms_ready for item in self.symbols)


def collect_ctrader_demo_provider_economics(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    observed_at: datetime | None = None,
) -> CTraderProviderEconomicsProbe:
    """Collect provider-native calibration inputs without broker mutation."""

    observed = observed_at or datetime.now(UTC)
    binding = discover_free_account_binding(client, bound_at=observed)
    account_id = client.account_id
    ids = [item.symbol_id for item in binding.contracts]
    details_res = _request(
        client,
        "ProtoOASymbolByIdReq",
        {"ctidTraderAccountId": account_id, "symbolId": ids},
        "qore-cibo-provider-economics-symbols",
    )
    details = tuple(getattr(details_res, "symbol", ()))
    by_id = {int(item.symbolId): item for item in details}

    _request(
        client,
        "ProtoOASubscribeSpotsReq",
        {"ctidTraderAccountId": account_id, "symbolId": ids},
        "qore-cibo-provider-economics-spots",
    )
    spots = _collect_spots(client, ids)

    rows: list[CTraderProviderEconomicsSymbolEvidence] = []
    for contract in binding.contracts:
        detail = by_id.get(contract.symbol_id)
        if detail is None:
            raise CiboCapitalManagementError(
                f"missing native symbol detail for {contract.qore_symbol}"
            )
        lot_size_cents = int(contract.lot_size_units / _VOLUME_UNIT)
        margin_res = _request(
            client,
            "ProtoOAExpectedMarginReq",
            {
                "ctidTraderAccountId": account_id,
                "symbolId": contract.symbol_id,
                "volume": [
                    contract.min_volume_units,
                    lot_size_cents,
                ],
            },
            f"qore-cibo-expected-margin-{contract.qore_symbol.lower()}",
        )
        money_digits = getattr(margin_res, "moneyDigits", None)
        if type(money_digits) is not int or money_digits < 0:
            raise CiboCapitalManagementError(
                f"invalid ExpectedMargin moneyDigits for {contract.qore_symbol}"
            )
        scale = Decimal(1).scaleb(-money_digits)
        margin_quotes = tuple(
            sorted(
                (
                    CTraderExpectedMarginQuote(
                        native_volume_cents=_positive_int(
                            getattr(item, "volume", None),
                            "ExpectedMargin.volume",
                        ),
                        buy_margin_usd=Decimal(
                            _positive_int(
                                getattr(item, "buyMargin", None),
                                "ExpectedMargin.buyMargin",
                            )
                        )
                        * scale,
                        sell_margin_usd=Decimal(
                            _positive_int(
                                getattr(item, "sellMargin", None),
                                "ExpectedMargin.sellMargin",
                            )
                        )
                        * scale,
                    )
                    for item in getattr(margin_res, "margin", ())
                ),
                key=lambda item: item.native_volume_cents,
            )
        )
        requested = {contract.min_volume_units, lot_size_cents}
        margin_ready = {
            item.native_volume_cents for item in margin_quotes
        } == requested

        bid_raw, ask_raw, spot_at = spots[contract.symbol_id]
        bid = Decimal(bid_raw) / _PRICE_SCALE
        ask = Decimal(ask_raw) / _PRICE_SCALE
        commission = CTraderNativeCommissionTerms(
            precise_rate_raw=_optional_present_int(
                detail,
                "preciseTradingCommissionRate",
            ),
            commission_type=_optional_present_int(
                detail,
                "commissionType",
            ),
            precise_minimum_raw=_optional_present_int(
                detail,
                "preciseMinCommission",
            ),
            minimum_type=_optional_present_int(
                detail,
                "minCommissionType",
            ),
            minimum_asset=_optional_present_str(
                detail,
                "minCommissionAsset",
            ),
        )
        rows.append(
            CTraderProviderEconomicsSymbolEvidence(
                qore_symbol=contract.qore_symbol,
                provider_symbol=contract.symbol_name,
                symbol_id=contract.symbol_id,
                observed_at=spot_at,
                digits=contract.digits,
                bid=bid,
                ask=ask,
                min_volume_cents=contract.min_volume_units,
                max_volume_cents=contract.max_volume_units,
                step_volume_cents=contract.step_volume_units,
                lot_size_cents=lot_size_cents,
                commission=commission,
                expected_margin=margin_quotes,
                margin_native_ready=margin_ready,
                spread_native_ready=ask >= bid > 0,
            )
        )

    return CTraderProviderEconomicsProbe(
        account_ref=binding.account.account_ref,
        observed_at=observed,
        symbols=tuple(sorted(rows, key=lambda item: item.qore_symbol)),
    )


def _collect_spots(
    client: CTraderOpenApiMessageClientBoundary,
    symbol_ids: list[int],
) -> dict[int, tuple[int, int, datetime]]:
    wanted = set(symbol_ids)
    partial: dict[int, tuple[int | None, int | None, datetime]] = {}
    deadline = datetime.now(UTC).timestamp() + 10.0
    while set(partial) != wanted or any(
        bid is None or ask is None for bid, ask, _ in partial.values()
    ):
        remaining = deadline - datetime.now(UTC).timestamp()
        if remaining <= 0:
            raise CiboCapitalManagementError(
                "provider economics spot collection timed out"
            )
        event = client.wait_for_event(
            "ProtoOASpotEvent",
            timeout_seconds=min(1.0, remaining),
        )
        if isinstance(event, Failure):
            continue
        item = event.value
        symbol_id = getattr(item, "symbolId", None)
        if symbol_id not in wanted:
            continue
        previous = partial.get(
            symbol_id,
            (None, None, datetime.now(UTC)),
        )
        bid_raw = getattr(item, "bid", 0)
        ask_raw = getattr(item, "ask", 0)
        bid = bid_raw if type(bid_raw) is int and bid_raw > 0 else previous[0]
        ask = ask_raw if type(ask_raw) is int and ask_raw > 0 else previous[1]
        timestamp = getattr(item, "timestamp", 0)
        seen_at = (
            datetime.fromtimestamp(timestamp / 1000, tz=UTC)
            if type(timestamp) is int and timestamp > 0
            else datetime.now(UTC)
        )
        partial[int(symbol_id)] = (bid, ask, seen_at)
    return {
        symbol_id: (int(bid), int(ask), seen_at)
        for symbol_id, (bid, ask, seen_at) in partial.items()
        if bid is not None and ask is not None
    }


def _request(
    client: CTraderOpenApiMessageClientBoundary,
    name: str,
    fields: dict[str, object],
    message_id: str,
) -> object:
    result = client.request(
        name,
        fields,
        client_msg_id=message_id,
        timeout_seconds=10.0,
    )
    if isinstance(result, Failure):
        raise CiboCapitalManagementError(str(result.error))
    return result.value


def _field_present(message: object, name: str) -> bool:
    has_field = getattr(message, "HasField", None)
    if callable(has_field):
        try:
            return bool(has_field(name))
        except (ValueError, KeyError):
            pass
    list_fields = getattr(message, "ListFields", None)
    if callable(list_fields):
        try:
            return any(
                getattr(descriptor, "name", None) == name
                for descriptor, _ in list_fields()
            )
        except (TypeError, ValueError):
            return False
    return False


def _optional_present_int(message: object, name: str) -> int | None:
    if not _field_present(message, name):
        return None
    value = getattr(message, name, None)
    return value if type(value) is int else None


def _optional_present_str(message: object, name: str) -> str | None:
    if not _field_present(message, name):
        return None
    value = getattr(message, name, None)
    return value if isinstance(value, str) and value else None


def _positive_int(value: Any, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise CiboCapitalManagementError(f"{name} must be positive int")
    return value
