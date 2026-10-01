"""Bounded cTrader DEMO micro-bundle experiment for Architect-2 T11.

The frozen T11 protocol compares one minimum-volume child order with two
minimum-volume child orders.  This runner collects the post-freeze provider
population without reading Phase22 V2 or any holdout outcome.

Adverse entry slippage is converted to USD from provider-native contract units:

    adverse_price * filled_underlying_units * quote_currency_to_usd

For USD-quoted instruments the conversion is 1.  For AUDJPY/GBPJPY, JPY is
converted with a causal USDJPY spot observed before the bundle.  This is
algebraically equivalent to price_delta / tick_size * tick_value for the
provider contract, but avoids inventing a broker tick-value field that cTrader
Open API does not expose directly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.cibo_arch2_t11_market_impact_evaluator import (
    T11MarketImpactEpisode,
    evaluate_t11_market_impact,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    FROZEN_AT,
    MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL,
    MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL,
    REQUIRED_SYMBOLS,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    CTraderDemoAccountType,
    collect_ctrader_demo_account_capability,
)
from qore.infrastructure.ctrader_demo_free_binding import (
    CTraderDemoFreeBinding,
    discover_free_account_binding,
)
from qore.infrastructure.ctrader_demo_free_sink import (
    credentials_from_environment,
)
from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

AUTHORIZATION_TOKEN = "CIBO_ARCH2_T11_MARKET_IMPACT_DEMO_AUTHORIZED"
EXPECTED_ACCOUNT_FINGERPRINT_SHA256 = (
    "70d38b13a2afb1ada12883a486ddb39aa0626e4c262b69ee44410bb6531d6086"
)
_LABEL_PREFIX = "CIBOA2T11:"
_NATIVE_VOLUME_UNIT = Decimal("0.01")
_PRICE_SCALE = Decimal("100000")
_MARKET = 1
_BUY = 1
_SELL = 2

# Frozen from the successful pre-T11 cTrader DEMO provider-economics artifact
# (run 36810489106, artifact 11139835744).  These facts existed before FROZEN_AT.
_EXPECTED_CONTRACTS = {
    "AUDJPY": ("AUDJPY", 3, 100000, Decimal("100000")),
    "EURUSD": ("EURUSD", 5, 100000, Decimal("100000")),
    "GBPJPY": ("GBPJPY", 3, 100000, Decimal("100000")),
    "GBPUSD": ("GBPUSD", 5, 100000, Decimal("100000")),
    "NAS100": ("USTEC", 2, 10, Decimal("1")),
    "XAUUSD": ("XAUUSD", 2, 100, Decimal("100")),
}


def _request(
    client: SpotwareCTraderOpenApiClient,
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
        raise CiboCapitalManagementError(
            f"T11 market-impact provider request failed: {name}: {result.error}"
        )
    return result.value


def _authorization() -> None:
    if os.environ.get("QORE_CIBO_ARCH2_T11_MARKET_IMPACT_AUTHORIZATION") != (
        AUTHORIZATION_TOKEN
    ):
        raise CiboCapitalManagementError(
            "T11 market-impact DEMO authorization token missing"
        )


def _hash_ref(kind: str, value: int) -> str:
    return "sha256:" + hashlib.sha256(
        f"{kind}|{value}".encode()
    ).hexdigest()


def _quote_snapshot(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    purpose: str,
) -> dict[str, object]:
    subscribed = client.request(
        "ProtoOASubscribeSpotsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "symbolId": [symbol_id],
            "subscribeToSpotTimestamp": True,
        },
        client_msg_id=f"t11-subscribe:{symbol_id}:{purpose}",
        timeout_seconds=10.0,
    )
    if isinstance(subscribed, Failure) and "ALREADY_SUBSCRIBED" not in str(
        subscribed.error
    ):
        raise CiboCapitalManagementError(
            f"T11 market-impact spot subscription failed: {subscribed.error}"
        )

    bid: int | None = None
    ask: int | None = None
    bid_at: datetime | None = None
    ask_at: datetime | None = None
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline and (bid is None or ask is None):
        remaining = max(0.1, min(2.0, deadline - time.monotonic()))
        event = client.wait_for_event(
            "ProtoOASpotEvent",
            timeout_seconds=remaining,
            predicate=lambda item: getattr(item, "symbolId", None) == symbol_id,
        )
        if isinstance(event, Failure):
            continue
        timestamp = getattr(event.value, "timestamp", None)
        observed_at = (
            datetime.fromtimestamp(timestamp / 1000, tz=UTC)
            if type(timestamp) is int and timestamp > 0
            else datetime.now(UTC)
        )
        raw_bid = getattr(event.value, "bid", None)
        raw_ask = getattr(event.value, "ask", None)
        if type(raw_bid) is int and raw_bid > 0:
            bid = raw_bid
            bid_at = observed_at
        if type(raw_ask) is int and raw_ask > 0:
            ask = raw_ask
            ask_at = observed_at

    if (
        bid is None
        or ask is None
        or bid_at is None
        or ask_at is None
        or ask < bid
    ):
        raise CiboCapitalManagementError(
            "T11 market-impact causal bid/ask snapshot incomplete"
        )
    return {
        "bid": Decimal(bid) / _PRICE_SCALE,
        "ask": Decimal(ask) / _PRICE_SCALE,
        "observed_at": max(bid_at, ask_at),
    }


def _usd_jpy_symbol_id(
    client: SpotwareCTraderOpenApiClient,
) -> int:
    response = _request(
        client,
        "ProtoOASymbolsListReq",
        {
            "ctidTraderAccountId": client.account_id,
            "includeArchivedSymbols": False,
        },
        "t11-usdjpy-catalog",
    )
    matches = tuple(
        item
        for item in tuple(getattr(response, "symbol", ()))
        if str(getattr(item, "symbolName", "")).upper() == "USDJPY"
        and getattr(item, "enabled", False) is True
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "T11 market-impact requires exactly one enabled USDJPY converter"
        )
    value = getattr(matches[0], "symbolId", None)
    if type(value) is not int or value <= 0:
        raise CiboCapitalManagementError(
            "T11 market-impact USDJPY converter symbol id invalid"
        )
    return value


def _quote_currency_to_usd(
    client: SpotwareCTraderOpenApiClient,
    *,
    qore_symbol: str,
    usd_jpy_symbol_id: int,
    purpose: str,
) -> tuple[Decimal, dict[str, object] | None]:
    if qore_symbol not in {"AUDJPY", "GBPJPY"}:
        return Decimal(1), None
    conversion = _quote_snapshot(
        client,
        symbol_id=usd_jpy_symbol_id,
        purpose=f"{purpose}:usdjpy",
    )
    midpoint = (
        cast(Decimal, conversion["bid"])
        + cast(Decimal, conversion["ask"])
    ) / Decimal(2)
    if midpoint <= 0:
        raise CiboCapitalManagementError(
            "T11 market-impact USDJPY midpoint invalid"
        )
    return Decimal(1) / midpoint, conversion


def adverse_price_to_usd(
    *,
    side: str,
    bid: Decimal,
    ask: Decimal,
    fill_price: Decimal,
    filled_underlying_units: Decimal,
    quote_currency_to_usd: Decimal,
) -> Decimal:
    """Convert adverse entry slippage to USD without a synthetic tick value."""

    for name, value in (
        ("bid", bid),
        ("ask", ask),
        ("fill_price", fill_price),
        ("filled_underlying_units", filled_underlying_units),
        ("quote_currency_to_usd", quote_currency_to_usd),
    ):
        if (
            not isinstance(value, Decimal)
            or not value.is_finite()
            or value <= 0
        ):
            raise CiboCapitalManagementError(
                f"T11 market-impact {name} must be positive finite Decimal"
            )
    if ask < bid:
        raise CiboCapitalManagementError(
            "T11 market-impact quote is crossed"
        )
    if side == "long":
        adverse_price = max(Decimal(0), fill_price - ask)
    elif side == "short":
        adverse_price = max(Decimal(0), bid - fill_price)
    else:
        raise CiboCapitalManagementError(
            "T11 market-impact side must be long/short"
        )
    return (
        adverse_price
        * filled_underlying_units
        * quote_currency_to_usd
    )


def _position_for_label(
    client: SpotwareCTraderOpenApiClient,
    *,
    label: str,
    message_id: str,
) -> object | None:
    response = _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        message_id,
    )
    matches = tuple(
        item
        for item in tuple(getattr(response, "position", ()))
        if getattr(getattr(item, "tradeData", None), "label", None) == label
    )
    if len(matches) > 1:
        raise CiboCapitalManagementError(
            "T11 market-impact label maps to multiple positions"
        )
    return matches[0] if matches else None


def _single_deal(
    response: object,
    *,
    order_id: int,
) -> object | None:
    direct = getattr(response, "deal", None)
    if (
        direct is not None
        and type(getattr(direct, "dealId", None)) is int
        and getattr(direct, "orderId", order_id) == order_id
    ):
        return direct
    raw = getattr(response, "deal", ())
    try:
        rows = tuple(raw)
    except TypeError:
        rows = ()
    matches = tuple(
        item
        for item in rows
        if getattr(item, "orderId", order_id) == order_id
        and type(getattr(item, "dealId", None)) is int
        and item.dealId > 0
    )
    if not matches:
        return None
    return min(
        matches,
        key=lambda item: (
            getattr(item, "executionTimestamp", 0),
            getattr(item, "dealId", 0),
        ),
    )


def _wait_entry(
    client: SpotwareCTraderOpenApiClient,
    opened: object,
    *,
    order_id: int,
    label: str,
) -> tuple[object, int, int]:
    for attempt in range(25):
        response = (
            opened
            if attempt == 0
            else _request(
                client,
                "ProtoOAOrderDetailsReq",
                {
                    "ctidTraderAccountId": client.account_id,
                    "orderId": order_id,
                },
                f"t11-order-details:{order_id}:{attempt}",
            )
        )
        deal = _single_deal(response, order_id=order_id)
        position = _position_for_label(
            client,
            label=label,
            message_id=f"t11-position:{order_id}:{attempt}",
        )
        position_id = getattr(position, "positionId", None) if position else None
        trade_data = getattr(position, "tradeData", None) if position else None
        volume = getattr(trade_data, "volume", None) if trade_data else None
        if (
            deal is not None
            and type(position_id) is int
            and position_id > 0
            and type(volume) is int
            and volume > 0
        ):
            return deal, position_id, volume
        time.sleep(0.25)
    raise CiboCapitalManagementError(
        "T11 market-impact entry did not reconcile to fill/position"
    )


def _neutralize_label(
    client: SpotwareCTraderOpenApiClient,
    *,
    label: str,
) -> None:
    response = _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        f"t11-neutralize:{label}",
    )

    for order in tuple(getattr(response, "order", ())):
        trade_data = getattr(order, "tradeData", None)
        if getattr(trade_data, "label", None) != label:
            continue
        order_id = getattr(order, "orderId", None)
        if type(order_id) is int and order_id > 0:
            client.request(
                "ProtoOACancelOrderReq",
                {
                    "ctidTraderAccountId": client.account_id,
                    "orderId": order_id,
                },
                client_msg_id=f"t11-cancel:{order_id}",
                timeout_seconds=10.0,
            )

    response = _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        f"t11-neutralize-positions:{label}",
    )
    for position in tuple(getattr(response, "position", ())):
        trade_data = getattr(position, "tradeData", None)
        if getattr(trade_data, "label", None) != label:
            continue
        position_id = getattr(position, "positionId", None)
        volume = getattr(trade_data, "volume", None)
        if (
            type(position_id) is not int
            or position_id <= 0
            or type(volume) is not int
            or volume <= 0
        ):
            raise CiboCapitalManagementError(
                "T11 market-impact containment position invalid"
            )
        _request(
            client,
            "ProtoOAClosePositionReq",
            {
                "ctidTraderAccountId": client.account_id,
                "positionId": position_id,
                "volume": volume,
            },
            f"t11-neutralize-close:{position_id}",
        )

    time.sleep(0.2)
    terminal = _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        f"t11-neutralize-terminal:{label}",
    )
    active_labels = tuple(
        getattr(getattr(item, "tradeData", None), "label", None)
        for item in tuple(getattr(terminal, "position", ()))
    )
    if label in active_labels:
        raise CiboCapitalManagementError(
            "T11 market-impact position remains after containment"
        )


def _submit_child(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    native_volume: int,
    side_code: int,
    label: str,
    child_id: str,
) -> dict[str, object]:
    position_id: int | None = None
    try:
        opened = _request(
            client,
            "ProtoOANewOrderReq",
            {
                "ctidTraderAccountId": client.account_id,
                "clientOrderId": child_id,
                "orderType": _MARKET,
                "symbolId": symbol_id,
                "tradeSide": side_code,
                "volume": native_volume,
                "label": label,
                "comment": "cibo-arch2-t11-market-impact",
            },
            child_id,
        )
        order = getattr(opened, "order", None)
        order_id = getattr(order, "orderId", None) if order is not None else None
        if type(order_id) is not int or order_id <= 0:
            raise CiboCapitalManagementError(
                "T11 market-impact submit returned no order id"
            )
        deal, position_id, position_volume = _wait_entry(
            client,
            opened,
            order_id=order_id,
            label=label,
        )
        deal_id = getattr(deal, "dealId", None)
        fill_price = getattr(deal, "executionPrice", None)
        execution_ms = getattr(deal, "executionTimestamp", None)
        filled_volume = getattr(deal, "filledVolume", None)
        if (
            type(deal_id) is not int
            or deal_id <= 0
            or not isinstance(fill_price, float)
            or fill_price <= 0
            or type(execution_ms) is not int
            or execution_ms <= 0
            or type(filled_volume) is not int
            or filled_volume <= 0
        ):
            raise CiboCapitalManagementError(
                "T11 market-impact reconciled fill incomplete"
            )
        _request(
            client,
            "ProtoOAClosePositionReq",
            {
                "ctidTraderAccountId": client.account_id,
                "positionId": position_id,
                "volume": position_volume,
            },
            f"t11-close:{position_id}",
        )
        _neutralize_label(client, label=label)
        return {
            "order_ref_sha256": _hash_ref("order", order_id),
            "deal_ref_sha256": _hash_ref("deal", deal_id),
            "position_ref_sha256": _hash_ref("position", position_id),
            "fill_price": Decimal(str(fill_price)),
            "filled_underlying_units": (
                Decimal(filled_volume) * _NATIVE_VOLUME_UNIT
            ),
            "executed_at": datetime.fromtimestamp(
                execution_ms / 1000,
                tz=UTC,
            ),
            "position_closed": True,
        }
    finally:
        _neutralize_label(client, label=label)


def _validate_contract_binding(binding: CTraderDemoFreeBinding) -> None:
    by_symbol = {item.qore_symbol: item for item in binding.contracts}
    if tuple(sorted(by_symbol)) != REQUIRED_SYMBOLS:
        raise CiboCapitalManagementError(
            "T11 market-impact provider symbol surface drift"
        )
    for symbol in REQUIRED_SYMBOLS:
        contract = by_symbol[symbol]
        provider_symbol, digits, min_native, lot_size = _EXPECTED_CONTRACTS[symbol]
        if (
            contract.symbol_name != provider_symbol
            or contract.digits != digits
            or contract.min_volume_units != min_native
            or contract.lot_size_units != lot_size
        ):
            raise CiboCapitalManagementError(
                f"T11 market-impact frozen contract drift: {symbol}"
            )


def _source_minimum_volume(
    *,
    min_native_volume: int,
    lot_size_units: Decimal,
) -> Decimal:
    underlying = Decimal(min_native_volume) * _NATIVE_VOLUME_UNIT
    source_volume = underlying / lot_size_units
    if source_volume <= 0:
        raise CiboCapitalManagementError(
            "T11 market-impact source minimum volume invalid"
        )
    return source_volume


def _bundle(
    client: SpotwareCTraderOpenApiClient,
    *,
    qore_symbol: str,
    symbol_id: int,
    native_volume: int,
    lot_size_units: Decimal,
    child_count: int,
    side: str,
    phase: str,
    pair_index: int,
    fold_index: int,
    run_key: str,
    usd_jpy_symbol_id: int,
) -> tuple[T11MarketImpactEpisode, dict[str, object]]:
    if child_count not in {1, 2}:
        raise CiboCapitalManagementError(
            "T11 market-impact child count must be 1 or 2"
        )
    side_code = _BUY if side == "long" else _SELL
    pair_id = f"{qore_symbol}-{phase}-{pair_index:02d}"
    bundle_id = f"{pair_id}-L{child_count}"
    quote = _quote_snapshot(
        client,
        symbol_id=symbol_id,
        purpose=bundle_id,
    )
    conversion, conversion_quote = _quote_currency_to_usd(
        client,
        qore_symbol=qore_symbol,
        usd_jpy_symbol_id=usd_jpy_symbol_id,
        purpose=bundle_id,
    )

    children: list[dict[str, object]] = []
    total_adverse_usd = Decimal(0)
    for child_index in range(1, child_count + 1):
        label = (
            f"{_LABEL_PREFIX}{qore_symbol}:{run_key[-6:]}:"
            f"{phase[0]}{pair_index:02d}:L{child_count}:C{child_index}"
        )
        child_id = (
            f"cibo-a2-t11-{run_key[-10:]}-{qore_symbol.lower()}-"
            f"{phase[0].lower()}{pair_index:02d}-"
            f"l{child_count}-c{child_index}"
        )
        child = _submit_child(
            client,
            symbol_id=symbol_id,
            native_volume=native_volume,
            side_code=side_code,
            label=label,
            child_id=child_id,
        )
        cost = adverse_price_to_usd(
            side=side,
            bid=cast(Decimal, quote["bid"]),
            ask=cast(Decimal, quote["ask"]),
            fill_price=cast(Decimal, child["fill_price"]),
            filled_underlying_units=cast(
                Decimal, child["filled_underlying_units"]
            ),
            quote_currency_to_usd=conversion,
        )
        child["adverse_slippage_cost_usd"] = cost
        children.append(child)
        total_adverse_usd += cost
        time.sleep(0.15)

    minimum_volume = _source_minimum_volume(
        min_native_volume=native_volume,
        lot_size_units=lot_size_units,
    )
    observed_at = max(
        cast(datetime, item["executed_at"])
        for item in children
    )
    if observed_at <= FROZEN_AT:
        raise CiboCapitalManagementError(
            "T11 market-impact execution does not postdate freeze"
        )
    episode = T11MarketImpactEpisode(
        evidence_id=(
            "t11-impact:"
            + hashlib.sha256(
                (
                    f"{run_key}|{bundle_id}|{observed_at.isoformat()}|"
                    f"{total_adverse_usd}"
                ).encode()
            ).hexdigest()
        ),
        qore_symbol=qore_symbol,
        pair_id=pair_id,
        phase=phase,
        fold_index=fold_index,
        side=side,
        child_count=child_count,
        minimum_volume=minimum_volume,
        aggregate_volume=minimum_volume * child_count,
        adverse_slippage_cost_total_usd=total_adverse_usd,
        observed_at=observed_at,
        provider_bound=True,
        every_child_order_minimum_volume=True,
        holdout_outcomes_used=False,
        target_aware=False,
        productive_authority=False,
    )
    raw = {
        "episode": _jsonable(asdict(episode)),
        "provider_quote": _jsonable(quote),
        "quote_currency_to_usd": format(conversion, "f"),
        "conversion_quote": _jsonable(conversion_quote),
        "children": _jsonable(children),
    }
    return episode, raw


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _evaluation_payload(value: object) -> dict[str, object]:
    raw = asdict(value)
    return cast(dict[str, object], _jsonable(raw))


def run() -> dict[str, object]:
    _authorization()
    run_key = os.environ.get("GITHUB_RUN_ID", "") + "-" + os.environ.get(
        "GITHUB_RUN_ATTEMPT", "1"
    )
    if not run_key.strip("-"):
        raise CiboCapitalManagementError(
            "T11 market-impact requires GitHub run identity"
        )

    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    try:
        capability = collect_ctrader_demo_account_capability(client)
        account_fingerprint = hashlib.sha256(
            capability.account_ref.encode()
        ).hexdigest()
        if account_fingerprint != EXPECTED_ACCOUNT_FINGERPRINT_SHA256:
            raise CiboCapitalManagementError(
                "T11 market-impact DEMO account drift"
            )
        if capability.account_type is not CTraderDemoAccountType.HEDGED:
            raise CiboCapitalManagementError(
                "T11 market-impact requires frozen HEDGED DEMO account mode"
            )
        binding = discover_free_account_binding(client)
        _validate_contract_binding(binding)
        usd_jpy_symbol_id = _usd_jpy_symbol_id(client)
        by_symbol = {item.qore_symbol: item for item in binding.contracts}

        episodes: list[T11MarketImpactEpisode] = []
        raw_rows: list[dict[str, object]] = []
        for symbol in REQUIRED_SYMBOLS:
            contract = by_symbol[symbol]

            for pair_index in range(
                1,
                MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL + 1,
            ):
                side = "long" if pair_index % 2 else "short"
                for child_count in (1, 2):
                    episode, raw = _bundle(
                        client,
                        qore_symbol=symbol,
                        symbol_id=contract.symbol_id,
                        native_volume=contract.min_volume_units,
                        lot_size_units=contract.lot_size_units,
                        child_count=child_count,
                        side=side,
                        phase="CALIBRATION",
                        pair_index=pair_index,
                        fold_index=0,
                        run_key=run_key,
                        usd_jpy_symbol_id=usd_jpy_symbol_id,
                    )
                    episodes.append(episode)
                    raw_rows.append(raw)
                    time.sleep(0.25)

            for pair_index in range(
                1,
                MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL + 1,
            ):
                side = "long" if pair_index % 2 else "short"
                for child_count in (1, 2):
                    episode, raw = _bundle(
                        client,
                        qore_symbol=symbol,
                        symbol_id=contract.symbol_id,
                        native_volume=contract.min_volume_units,
                        lot_size_units=contract.lot_size_units,
                        child_count=child_count,
                        side=side,
                        phase="VALIDATION",
                        pair_index=pair_index,
                        fold_index=pair_index,
                        run_key=run_key,
                        usd_jpy_symbol_id=usd_jpy_symbol_id,
                    )
                    episodes.append(episode)
                    raw_rows.append(raw)
                    time.sleep(0.25)

        evaluation = evaluate_t11_market_impact(tuple(episodes))
        report: dict[str, object] = {
            "schema": "qore.cibo.arch2.t11.market-impact-demo.v1",
            "status": (
                "MARKET_IMPACT_MODEL_READY"
                if evaluation.market_impact_model_ready
                else "MARKET_IMPACT_MODEL_FALSIFIED_OR_NOT_READY"
            ),
            "protocol_frozen_at": FROZEN_AT.isoformat(),
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "account_fingerprint_sha256": account_fingerprint,
            "episode_count": len(episodes),
            "child_entry_count": sum(item.child_count for item in episodes),
            "minimum_volume_child_orders_only": True,
            "calibration_pairs_per_symbol": (
                MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL
            ),
            "validation_pairs_per_symbol": (
                MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL
            ),
            "raw_rows": raw_rows,
            "evaluation": _evaluation_payload(evaluation),
            "all_created_positions_closed": True,
            "holdout_outcomes_used": False,
            "phase22_v2_consumed": False,
            "fundednext_touched": False,
            "vps_touched": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "canonical_ledger_modified": False,
            "productive_authority": False,
            "git_sha": os.environ.get("GITHUB_SHA", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        }
        if report["episode_count"] != 144:
            raise CiboCapitalManagementError(
                "T11 market-impact frozen episode-count drift"
            )
        if report["child_entry_count"] != 216:
            raise CiboCapitalManagementError(
                "T11 market-impact frozen child-count drift"
            )
        return report
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "episode_count": report["episode_count"],
                "child_entry_count": report["child_entry_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
