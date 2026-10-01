"""Bounded T16 cTrader DEMO execution calibration for US30/US500.

Exactly one BUY and one SELL minimum-volume round trip are allowed for each
pre-registered hedge instrument.  Every position is closed by exact position
id and then neutralized by its unique label.  This runner is DEMO-only and does
not consume Phase22 V2 outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_t16_preregistered_hedge_universe import (
    T16_ACCOUNT_FINGERPRINT_SHA256,
    T16_PROVIDER_CATALOG_SHA256,
)
from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    collect_ctrader_demo_account_capability,
)
from qore.infrastructure.ctrader_demo_free_sink import (
    credentials_from_environment,
)
from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

_AUTHORIZATION_TOKEN = "CIBO_ARCH2_T16_DEMO_EXECUTION_AUTHORIZED"
_LABEL_PREFIX = "QORE:CIBO-T16:"
_MARKET = 1
_BUY = 1
_SELL = 2
_PRICE_SCALE = Decimal("100000")
_REQUIRED_HEDGES = ("US30", "US500")


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
            f"T16 DEMO execution request failed: {name}: {result.error}"
        )
    return result.value


def _authorization() -> None:
    if os.environ.get("QORE_CIBO_ARCH2_T16_DEMO_AUTHORIZATION") != (
        _AUTHORIZATION_TOKEN
    ):
        raise CiboCapitalManagementError(
            "T16 DEMO execution Owner authorization token missing"
        )


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


def _commission_usd(deal: object) -> Decimal | None:
    if not _field_present(deal, "commission"):
        return None
    raw = getattr(deal, "commission", None)
    digits = getattr(deal, "moneyDigits", None)
    if type(raw) is not int or type(digits) is not int or digits < 0:
        return None
    return abs(Decimal(raw).scaleb(-digits))


def _spread_bps(quote: dict[str, object]) -> Decimal:
    bid = Decimal(str(quote["bid"]))
    ask = Decimal(str(quote["ask"]))
    midpoint = (bid + ask) / Decimal(2)
    return (ask - bid) / midpoint * Decimal("10000")


def _signed_slippage_bps(
    *,
    side: int,
    quote: dict[str, object],
    fill_price: Decimal,
) -> Decimal:
    reference = (
        Decimal(str(quote["ask"]))
        if side == _BUY
        else Decimal(str(quote["bid"]))
    )
    signed = fill_price - reference if side == _BUY else reference - fill_price
    return signed / reference * Decimal("10000")


def _causal_quote(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    message_key: str,
) -> dict[str, object]:
    subscribed = client.request(
        "ProtoOASubscribeSpotsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "subscribeToSpotTimestamp": True,
            "symbolId": [symbol_id],
        },
        client_msg_id=f"t16-spots:{message_key}",
        timeout_seconds=10.0,
    )
    if isinstance(subscribed, Failure) and (
        "ALREADY_SUBSCRIBED" not in str(subscribed.error)
    ):
        raise CiboCapitalManagementError(
            "T16 DEMO spot subscription failed: " + str(subscribed.error)
        )
    bid: int | None = None
    ask: int | None = None
    bid_at: datetime | None = None
    ask_at: datetime | None = None
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline and (bid is None or ask is None):
        event = client.wait_for_event(
            "ProtoOASpotEvent",
            timeout_seconds=max(
                0.1,
                min(2.0, deadline - time.monotonic()),
            ),
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
        raise CiboCapitalManagementError("T16 DEMO causal quote incomplete")
    return {
        "bid": format(Decimal(bid) / _PRICE_SCALE, "f"),
        "ask": format(Decimal(ask) / _PRICE_SCALE, "f"),
        "observed_at": max(bid_at, ask_at).isoformat(),
    }


def _single_deal(response: object, *, order_id: int) -> object | None:
    direct = getattr(response, "deal", None)
    if direct is not None and type(getattr(direct, "dealId", None)) is int:
        if getattr(direct, "orderId", order_id) == order_id:
            return cast(object, direct)
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
    return (
        cast(
            object,
            min(
                matches,
                key=lambda item: (
                    getattr(item, "executionTimestamp", 0),
                    getattr(item, "dealId", 0),
                ),
            ),
        )
        if matches
        else None
    )


def _position_for_label(
    client: SpotwareCTraderOpenApiClient,
    label: str,
    *,
    message_id: str,
) -> object | None:
    reconciled = _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        message_id,
    )
    matches = tuple(
        item
        for item in tuple(getattr(reconciled, "position", ()))
        if getattr(getattr(item, "tradeData", None), "label", None) == label
    )
    if len(matches) > 1:
        raise CiboCapitalManagementError(
            "T16 DEMO label maps to multiple positions"
        )
    return matches[0] if matches else None


def _wait_entry_fill(
    client: SpotwareCTraderOpenApiClient,
    opened: object,
    *,
    order_id: int,
    label: str,
) -> tuple[object, int]:
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
                f"t16-order:{order_id}:{attempt}",
            )
        )
        deal = _single_deal(response, order_id=order_id)
        position = _position_for_label(
            client,
            label,
            message_id=f"t16-position:{order_id}:{attempt}",
        )
        position_id = (
            getattr(position, "positionId", None)
            if position is not None
            else None
        )
        if deal is not None and type(position_id) is int and position_id > 0:
            return deal, position_id
        time.sleep(0.25)
    raise CiboCapitalManagementError(
        "T16 DEMO accepted order did not reconcile to fill/position"
    )


def _neutralize_label(
    client: SpotwareCTraderOpenApiClient,
    label: str,
) -> None:
    reconciled = _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        f"t16-neutralize:{label}",
    )
    for order in tuple(getattr(reconciled, "order", ())):
        if getattr(getattr(order, "tradeData", None), "label", None) != label:
            continue
        order_id = getattr(order, "orderId", None)
        if type(order_id) is int and order_id > 0:
            client.request(
                "ProtoOACancelOrderReq",
                {
                    "ctidTraderAccountId": client.account_id,
                    "orderId": order_id,
                },
                client_msg_id=f"t16-cancel:{order_id}",
                timeout_seconds=10.0,
            )
    reconciled = _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        f"t16-neutralize-pos:{label}",
    )
    for position in tuple(getattr(reconciled, "position", ())):
        trade = getattr(position, "tradeData", None)
        if getattr(trade, "label", None) != label:
            continue
        position_id = getattr(position, "positionId", None)
        volume = getattr(trade, "volume", None)
        if (
            type(position_id) is not int
            or position_id <= 0
            or type(volume) is not int
            or volume <= 0
        ):
            raise CiboCapitalManagementError(
                "T16 DEMO containment position invalid"
            )
        _request(
            client,
            "ProtoOAClosePositionReq",
            {
                "ctidTraderAccountId": client.account_id,
                "positionId": position_id,
                "volume": volume,
            },
            f"t16-neutralize-close:{position_id}",
        )
    time.sleep(0.25)
    terminal = _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        f"t16-neutralize-terminal:{label}",
    )
    if any(
        getattr(getattr(item, "tradeData", None), "label", None) == label
        for item in tuple(getattr(terminal, "position", ()))
    ):
        raise CiboCapitalManagementError(
            "T16 DEMO position remains after containment"
        )


def _position_deals(
    client: SpotwareCTraderOpenApiClient,
    *,
    position_id: int,
    symbol_id: int,
    started_at: datetime,
) -> tuple[object, ...]:
    for attempt in range(20):
        observed = datetime.now(UTC)
        response = _request(
            client,
            "ProtoOADealListReq",
            {
                "ctidTraderAccountId": client.account_id,
                "fromTimestamp": int(
                    (started_at - timedelta(minutes=1)).timestamp() * 1000
                ),
                "toTimestamp": int(observed.timestamp() * 1000),
                "maxRows": 1000,
            },
            f"t16-deals:{position_id}:{attempt}",
        )
        rows = tuple(
            sorted(
                (
                    item
                    for item in tuple(getattr(response, "deal", ()))
                    if getattr(item, "positionId", None) == position_id
                    and getattr(item, "symbolId", None) == symbol_id
                    and type(getattr(item, "dealId", None)) is int
                ),
                key=lambda item: (
                    getattr(item, "executionTimestamp", 0),
                    getattr(item, "dealId", 0),
                ),
            )
        )
        if len(rows) >= 2:
            return rows
        time.sleep(0.25)
    raise CiboCapitalManagementError(
        "T16 DEMO round trip did not reconcile two provider deals"
    )


def _zero_commission_contract(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
) -> int:
    response = _request(
        client,
        "ProtoOASymbolByIdReq",
        {
            "ctidTraderAccountId": client.account_id,
            "symbolId": [symbol_id],
        },
        f"t16-detail:{symbol_id}",
    )
    rows = tuple(getattr(response, "symbol", ()))
    if len(rows) != 1:
        raise CiboCapitalManagementError("T16 DEMO symbol detail missing")
    detail = rows[0]
    minimum = getattr(detail, "minVolume", None)
    rate = getattr(detail, "preciseTradingCommissionRate", None)
    min_commission = getattr(detail, "preciseMinCommission", None)
    if type(minimum) is not int or minimum <= 0:
        raise CiboCapitalManagementError("T16 DEMO minimum volume invalid")
    if rate not in {0, None} or min_commission not in {0, None}:
        raise CiboCapitalManagementError(
            "T16 DEMO V1 requires zero-commission preregistered index contracts"
        )
    return minimum


def _round_trip(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol: str,
    symbol_id: int,
    minimum_volume: int,
    side: int,
    run_key: str,
) -> dict[str, object]:
    side_name = "BUY" if side == _BUY else "SELL"
    label = f"{_LABEL_PREFIX}{symbol}:{side_name}:{run_key[-8:]}"
    client_order_id = f"qore-t16-{run_key[-10:]}-{symbol}-{side_name.lower()}"
    started_at = datetime.now(UTC)
    entry_quote = _causal_quote(
        client,
        symbol_id=symbol_id,
        message_key=f"{symbol}:{side_name}:entry",
    )
    try:
        opened = _request(
            client,
            "ProtoOANewOrderReq",
            {
                "ctidTraderAccountId": client.account_id,
                "clientOrderId": client_order_id,
                "orderType": _MARKET,
                "symbolId": symbol_id,
                "tradeSide": side,
                "volume": minimum_volume,
                "label": label,
                "comment": "qore-cibo-arch2-t16-calibration",
            },
            client_order_id,
        )
        order = getattr(opened, "order", None)
        order_id = getattr(order, "orderId", None) if order is not None else None
        if type(order_id) is not int or order_id <= 0:
            raise CiboCapitalManagementError(
                "T16 DEMO entry returned no canonical order id"
            )
        entry_deal, position_id = _wait_entry_fill(
            client,
            opened,
            order_id=order_id,
            label=label,
        )
        close_quote = _causal_quote(
            client,
            symbol_id=symbol_id,
            message_key=f"{symbol}:{side_name}:close",
        )
        position = _position_for_label(
            client,
            label,
            message_id=f"t16-preclose:{position_id}",
        )
        trade = getattr(position, "tradeData", None) if position is not None else None
        volume = getattr(trade, "volume", None) if trade is not None else None
        if type(volume) is not int or volume <= 0:
            raise CiboCapitalManagementError(
                "T16 DEMO created position volume missing"
            )
        _request(
            client,
            "ProtoOAClosePositionReq",
            {
                "ctidTraderAccountId": client.account_id,
                "positionId": position_id,
                "volume": volume,
            },
            f"t16-close:{position_id}",
        )
        _neutralize_label(client, label)
        deals = _position_deals(
            client,
            position_id=position_id,
            symbol_id=symbol_id,
            started_at=started_at,
        )
        entry = deals[0]
        close = deals[-1]
        if getattr(entry, "dealId", None) != getattr(entry_deal, "dealId", None):
            raise CiboCapitalManagementError("T16 DEMO entry deal lineage drift")
        entry_native = cast(Any, entry)
        close_native = cast(Any, close)
        entry_fill = Decimal(str(entry_native.executionPrice))
        close_fill = Decimal(str(close_native.executionPrice))
        close_side = close_native.tradeSide
        if close_side not in {_BUY, _SELL} or close_side == side:
            raise CiboCapitalManagementError("T16 DEMO close side invalid")
        commissions = (_commission_usd(entry), _commission_usd(close))
        if any(value not in {None, Decimal(0)} for value in commissions):
            raise CiboCapitalManagementError(
                "T16 DEMO observed non-zero commission outside V1 cost contract"
            )
        entry_slippage = _signed_slippage_bps(
            side=side,
            quote=entry_quote,
            fill_price=entry_fill,
        )
        close_slippage = _signed_slippage_bps(
            side=int(close_side),
            quote=close_quote,
            fill_price=close_fill,
        )
        entry_spread = _spread_bps(entry_quote)
        close_spread = _spread_bps(close_quote)
        cost_bound = (
            entry_spread / Decimal(2)
            + close_spread / Decimal(2)
            + max(Decimal(0), entry_slippage)
            + max(Decimal(0), close_slippage)
        )
        return {
            "symbol": symbol,
            "provider_symbol": symbol,
            "side": side_name,
            "minimum_volume_cents": minimum_volume,
            "entry_quote": entry_quote,
            "close_quote": close_quote,
            "entry_fill_price": format(entry_fill, "f"),
            "close_fill_price": format(close_fill, "f"),
            "entry_signed_slippage_bps": format(entry_slippage, "f"),
            "close_signed_slippage_bps": format(close_slippage, "f"),
            "entry_quoted_spread_bps": format(entry_spread, "f"),
            "close_quoted_spread_bps": format(close_spread, "f"),
            "round_trip_cost_bound_bps": format(cost_bound, "f"),
            "entry_commission_usd": (
                None if commissions[0] is None else format(commissions[0], "f")
            ),
            "close_commission_usd": (
                None if commissions[1] is None else format(commissions[1], "f")
            ),
            "entry_order_ref_sha256": "sha256:"
            + hashlib.sha256(str(order_id).encode()).hexdigest(),
            "position_ref_sha256": "sha256:"
            + hashlib.sha256(str(position_id).encode()).hexdigest(),
            "entry_deal_ref_sha256": "sha256:"
            + hashlib.sha256(str(entry_native.dealId).encode()).hexdigest(),
            "close_deal_ref_sha256": "sha256:"
            + hashlib.sha256(str(close_native.dealId).encode()).hexdigest(),
            "position_closed": True,
            "execution_supported": True,
        }
    finally:
        _neutralize_label(client, label)


def run() -> dict[str, object]:
    _authorization()
    run_key = os.environ.get("GITHUB_RUN_ID", "") + "-" + os.environ.get(
        "GITHUB_RUN_ATTEMPT",
        "1",
    )
    if not run_key.strip("-"):
        raise CiboCapitalManagementError("T16 DEMO execution requires GitHub run id")

    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    try:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise CiboCapitalManagementError(
                f"T16 DEMO authentication failed: {connected.error}"
            )
        capability = collect_ctrader_demo_account_capability(client)
        account_fingerprint = hashlib.sha256(
            capability.account_ref.encode("utf-8")
        ).hexdigest()
        if account_fingerprint != T16_ACCOUNT_FINGERPRINT_SHA256:
            raise CiboCapitalManagementError("T16 DEMO account fingerprint drift")
        if capability.catalog_sha256 != T16_PROVIDER_CATALOG_SHA256:
            raise CiboCapitalManagementError("T16 DEMO provider catalog drift")
        by_name = {
            item.symbol_name: item
            for item in capability.symbols
            if item.enabled
        }
        if not set(_REQUIRED_HEDGES).issubset(by_name):
            raise CiboCapitalManagementError(
                "T16 DEMO preregistered hedge symbols unavailable"
            )
        rows: list[dict[str, object]] = []
        for symbol in _REQUIRED_HEDGES:
            item = by_name[symbol]
            minimum = _zero_commission_contract(
                client,
                symbol_id=item.symbol_id,
            )
            for side in (_BUY, _SELL):
                rows.append(
                    _round_trip(
                        client,
                        symbol=symbol,
                        symbol_id=item.symbol_id,
                        minimum_volume=minimum,
                        side=side,
                        run_key=run_key,
                    )
                )
                time.sleep(0.35)
        by_symbol: dict[str, list[Decimal]] = {
            symbol: [] for symbol in _REQUIRED_HEDGES
        }
        for row in rows:
            by_symbol[str(row["symbol"])].append(
                Decimal(str(row["round_trip_cost_bound_bps"]))
            )
        summaries = {
            symbol: {
                "round_trip_count": len(costs),
                "max_round_trip_cost_bound_bps": format(max(costs), "f"),
                "mean_round_trip_cost_bound_bps": format(
                    sum(costs, Decimal(0)) / Decimal(len(costs)),
                    "f",
                ),
                "buy_and_sell_covered": len(costs) == 2,
                "execution_supported": len(costs) == 2,
            }
            for symbol, costs in by_symbol.items()
        }
        return {
            "schema": "qore.cibo.arch2.t16.demo-execution-calibration.v1",
            "status": "READY",
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "endpoint_host": "demo.ctraderapi.com",
            "account_fingerprint_sha256": account_fingerprint,
            "provider_catalog_sha256": capability.catalog_sha256,
            "required_hedges": list(_REQUIRED_HEDGES),
            "round_trips": rows,
            "summaries": summaries,
            "minimum_volume_only": True,
            "both_sides_covered": True,
            "created_round_trip_count": len(rows),
            "created_positions_closed": all(
                row["position_closed"] is True for row in rows
            ),
            "realized_slippage_coverage_complete": True,
            "realized_execution_coverage_complete": True,
            "full_hedge_cost_model_ready": True,
            "holdout_outcomes_used": False,
            "holdout_market_data_read": False,
            "historical_provider_economics_claimed": False,
            "fundednext_touched": False,
            "vps_touched": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "productive_authority": False,
            "git_sha": os.environ.get("GITHUB_SHA", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        }
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
                "created_round_trip_count": report["created_round_trip_count"],
                "summaries": report["summaries"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
