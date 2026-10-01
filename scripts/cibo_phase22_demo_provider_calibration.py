"""Top up the predeclared Phase22 provider calibration cohort on cTrader DEMO.

The runner executes only the missing number of minimum-volume MARKET entries
needed to reach eight valid causal-quote observations per required symbol.
Every created position is immediately closed by exact position id. The cTrader
client itself rejects LIVE/ambiguous accounts before any request can mutate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ctrader_demo_empirical_slippage import (
    CTraderEmpiricalSlippageObservation,
    _account_entry_deal,
    _deal_observation,
    _market_entry_order,
)
from qore.infrastructure.cibo_phase22_demo_calibration_contract import (
    CALIBRATION_AUTHORIZATION_TOKEN,
    CALIBRATION_LABEL_PREFIX,
    MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL,
    PHASE22_DEMO_CALIBRATION_GOVERNANCE,
    REQUIRED_SYMBOLS,
)
from qore.infrastructure.ctrader_demo_free_binding import (
    CTraderDemoFreeBinding,
    CTraderDemoNativeContract,
    discover_free_account_binding,
)
from qore.infrastructure.ctrader_demo_free_sink import (
    credentials_from_environment,
)
from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

_MARKET = 1
_BUY = 1
_SELL = 2


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
            f"Phase22 DEMO calibration request failed: {name}: {result.error}"
        )
    return result.value


def _authorization() -> None:
    if os.environ.get("QORE_CIBO_PHASE22_DEMO_CALIBRATION_AUTHORIZATION") != (
        CALIBRATION_AUTHORIZATION_TOKEN
    ):
        raise CiboCapitalManagementError(
            "Phase22 DEMO calibration Owner authorization token missing"
        )


def _label(symbol: str, ordinal: int, run_key: str) -> str:
    return f"{CALIBRATION_LABEL_PREFIX}{symbol}:{run_key[-8:]}:{ordinal:02d}"


def _order_label(order: object | None) -> str | None:
    if order is None:
        return None
    trade_data = getattr(order, "tradeData", None)
    value = getattr(trade_data, "label", None) if trade_data is not None else None
    if isinstance(value, str) and value:
        return value
    value = getattr(order, "label", None)
    return value if isinstance(value, str) and value else None


def _history(
    client: SpotwareCTraderOpenApiClient,
    binding: CTraderDemoFreeBinding,
    *,
    observed_at: datetime,
) -> tuple[
    dict[str, tuple[CTraderEmpiricalSlippageObservation, ...]],
    dict[str, int],
]:
    account_id = client.account_id
    start = observed_at - timedelta(days=365)
    deals_res = _request(
        client,
        "ProtoOADealListReq",
        {
            "ctidTraderAccountId": account_id,
            "fromTimestamp": int(start.timestamp() * 1000),
            "toTimestamp": int(observed_at.timestamp() * 1000),
            "maxRows": 5000,
        },
        "qore-phase22-cal-deals",
    )
    orders_res = _request(
        client,
        "ProtoOAOrderListReq",
        {
            "ctidTraderAccountId": account_id,
            "fromTimestamp": int(start.timestamp() * 1000),
            "toTimestamp": int(observed_at.timestamp() * 1000),
        },
        "qore-phase22-cal-orders",
    )
    if bool(getattr(deals_res, "hasMore", False)) or bool(
        getattr(orders_res, "hasMore", False)
    ):
        raise CiboCapitalManagementError(
            "Phase22 calibration history is truncated"
        )

    contracts = {item.symbol_id: item for item in binding.contracts}
    orders = {
        int(item.orderId): item
        for item in tuple(getattr(orders_res, "order", ()))
        if type(getattr(item, "orderId", None)) is int
        and int(item.orderId) > 0
    }
    observations: dict[str, list[CTraderEmpiricalSlippageObservation]] = (
        defaultdict(list)
    )
    invalid: dict[str, int] = defaultdict(int)
    for deal in tuple(getattr(deals_res, "deal", ())):
        if not _account_entry_deal(deal, contracts):
            continue
        order = orders.get(int(deal.orderId))
        if not _market_entry_order(order):
            continue
        label = _order_label(order)
        if label is None or not label.startswith(CALIBRATION_LABEL_PREFIX):
            continue
        contract = contracts[int(deal.symbolId)]
        try:
            observation = _deal_observation(
                client=client,
                account_id=account_id,
                contract=contract,
                deal=deal,
            )
        except CiboCapitalManagementError:
            invalid[contract.qore_symbol] += 1
            continue
        observations[contract.qore_symbol].append(observation)
    frozen = {
        symbol: tuple(
            sorted(rows, key=lambda item: (item.execution_at, item.order_ref))
        )
        for symbol, rows in observations.items()
    }
    return frozen, dict(invalid)


def _causal_quote(
    client: SpotwareCTraderOpenApiClient,
    contract: CTraderDemoNativeContract,
) -> dict[str, object]:
    subscribed = client.request(
        "ProtoOASubscribeSpotsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "subscribeToSpotTimestamp": True,
            "symbolId": [contract.symbol_id],
        },
        client_msg_id=f"phase22-cal-spots:{contract.symbol_id}",
        timeout_seconds=10.0,
    )
    if isinstance(subscribed, Failure) and (
        "ALREADY_SUBSCRIBED" not in str(subscribed.error)
    ):
        raise CiboCapitalManagementError(
            "Phase22 calibration spot subscription failed: "
            + str(subscribed.error)
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
            predicate=lambda item: getattr(item, "symbolId", None)
            == contract.symbol_id,
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
            "Phase22 calibration causal bid/ask snapshot incomplete"
        )
    observed_at = max(bid_at, ask_at)
    return {
        "symbol_id": contract.symbol_id,
        "observed_at": observed_at.isoformat(),
        "bid_relative": bid,
        "ask_relative": ask,
        "bid_observed_at": bid_at.isoformat(),
        "ask_observed_at": ask_at.isoformat(),
        "stream_delta_reconciled": True,
    }


def _single_deal(
    response: object,
    *,
    order_id: int,
) -> object | None:
    direct = getattr(response, "deal", None)
    if (
        direct is not None
        and type(getattr(direct, "dealId", None)) is int
    ):
        direct_order_id = getattr(direct, "orderId", order_id)
        if direct_order_id == order_id:
            return cast(object, direct)
    raw = getattr(response, "deal", ())
    try:
        rows = tuple(raw)
    except TypeError:
        rows = ()
    candidates = tuple(
        item
        for item in rows
        if getattr(item, "orderId", order_id) == order_id
        and type(getattr(item, "dealId", None)) is int
        and item.dealId > 0
    )
    if not candidates:
        return None
    return cast(
        object,
        min(
            candidates,
            key=lambda item: (
                getattr(item, "executionTimestamp", 0),
                getattr(item, "dealId", 0),
            ),
        ),
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
    matches = []
    for item in tuple(getattr(reconciled, "position", ())):
        trade_data = getattr(item, "tradeData", None)
        observed_label = (
            getattr(trade_data, "label", None)
            if trade_data is not None
            else None
        )
        if observed_label == label:
            matches.append(item)
    if len(matches) > 1:
        raise CiboCapitalManagementError(
            "Phase22 calibration label maps to multiple positions"
        )
    return matches[0] if matches else None


def _wait_entry_fill(
    client: SpotwareCTraderOpenApiClient,
    opened: object,
    *,
    order_id: int,
    label: str,
) -> tuple[object, int]:
    """Wait for the exact submitted order; never resubmit on async acceptance."""
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
                f"phase22-cal-order-details:{order_id}:{attempt}",
            )
        )
        deal = _single_deal(response, order_id=order_id)
        position = _position_for_label(
            client,
            label,
            message_id=f"phase22-cal-position:{order_id}:{attempt}",
        )
        position_id = (
            getattr(position, "positionId", None)
            if position is not None
            else None
        )
        if (
            deal is not None
            and type(position_id) is int
            and position_id > 0
        ):
            return deal, position_id
        time.sleep(0.25)
    raise CiboCapitalManagementError(
        "Phase22 calibration accepted order did not reconcile to fill/position"
    )


def _neutralize_label(
    client: SpotwareCTraderOpenApiClient,
    label: str,
) -> None:
    """Best-effort containment for exactly one calibration label."""
    reconciled = _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        f"phase22-cal-neutralize:{label}",
    )
    orders = tuple(
        item
        for item in tuple(getattr(reconciled, "order", ()))
        if (
            getattr(getattr(item, "tradeData", None), "label", None)
            == label
        )
    )
    for order in orders:
        order_id = getattr(order, "orderId", None)
        if type(order_id) is not int or order_id <= 0:
            continue
        # An accepted MARKET order can fill while cancellation is racing.
        # Failure here does not authorize a resubmit; we reconcile positions next.
        result = client.request(
            "ProtoOACancelOrderReq",
            {
                "ctidTraderAccountId": client.account_id,
                "orderId": order_id,
            },
            client_msg_id=f"phase22-cal-neutralize-cancel:{order_id}",
            timeout_seconds=10.0,
        )
        del result

    reconciled = _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        f"phase22-cal-neutralize-positions:{label}",
    )
    positions = tuple(
        item
        for item in tuple(getattr(reconciled, "position", ()))
        if (
            getattr(getattr(item, "tradeData", None), "label", None)
            == label
        )
    )
    for position in positions:
        position_id = getattr(position, "positionId", None)
        trade_data = getattr(position, "tradeData", None)
        volume = (
            getattr(trade_data, "volume", None)
            if trade_data is not None
            else None
        )
        if (
            type(position_id) is not int
            or position_id <= 0
            or type(volume) is not int
            or volume <= 0
        ):
            raise CiboCapitalManagementError(
                "Phase22 calibration containment position invalid"
            )
        _request(
            client,
            "ProtoOAClosePositionReq",
            {
                "ctidTraderAccountId": client.account_id,
                "positionId": position_id,
                "volume": volume,
            },
            f"phase22-cal-neutralize-close:{position_id}",
        )

    time.sleep(0.25)
    terminal = _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        f"phase22-cal-neutralize-terminal:{label}",
    )
    remaining_positions = tuple(
        item
        for item in tuple(getattr(terminal, "position", ()))
        if (
            getattr(getattr(item, "tradeData", None), "label", None)
            == label
        )
    )
    remaining_orders = tuple(
        item
        for item in tuple(getattr(terminal, "order", ()))
        if (
            getattr(getattr(item, "tradeData", None), "label", None)
            == label
        )
    )
    if remaining_positions or remaining_orders:
        raise CiboCapitalManagementError(
            "Phase22 calibration label remains active after containment"
        )


def _one_round_trip(
    client: SpotwareCTraderOpenApiClient,
    contract: CTraderDemoNativeContract,
    *,
    ordinal: int,
    run_key: str,
) -> dict[str, object]:
    side = _BUY if ordinal % 2 else _SELL
    label = _label(contract.qore_symbol, ordinal, run_key)
    quote = _causal_quote(client, contract)
    client_order_id = (
        f"qore-p22-cal-{run_key[-12:]}-{contract.qore_symbol}-{ordinal:02d}"
    )
    order_id: int | None = None
    position_id: int | None = None
    try:
        opened = _request(
            client,
            "ProtoOANewOrderReq",
            {
                "ctidTraderAccountId": client.account_id,
                "clientOrderId": client_order_id,
                "orderType": _MARKET,
                "symbolId": contract.symbol_id,
                "tradeSide": side,
                "volume": contract.min_volume_units,
                "label": label,
                "comment": "qore-phase22-provider-calibration",
            },
            client_order_id,
        )
        order = getattr(opened, "order", None)
        raw_order_id = (
            getattr(order, "orderId", None)
            if order is not None
            else None
        )
        if type(raw_order_id) is not int or raw_order_id <= 0:
            raise CiboCapitalManagementError(
                "Phase22 calibration submit returned no canonical order id"
            )
        order_id = raw_order_id
        deal, position_id = _wait_entry_fill(
            client,
            opened,
            order_id=order_id,
            label=label,
        )
        deal_id = getattr(deal, "dealId", None)
        fill_price = getattr(deal, "executionPrice", None)
        fill_at_ms = getattr(deal, "executionTimestamp", None)
        if (
            type(deal_id) is not int
            or deal_id <= 0
            or not isinstance(fill_price, float)
            or fill_price <= 0
            or type(fill_at_ms) is not int
            or fill_at_ms <= 0
        ):
            raise CiboCapitalManagementError(
                "Phase22 calibration reconciled deal is incomplete"
            )

        position = _position_for_label(
            client,
            label,
            message_id=f"phase22-cal-preclose:{position_id}",
        )
        trade_data = (
            getattr(position, "tradeData", None)
            if position is not None
            else None
        )
        volume = (
            getattr(trade_data, "volume", None)
            if trade_data is not None
            else None
        )
        if type(volume) is not int or volume <= 0:
            raise CiboCapitalManagementError(
                "Phase22 calibration created position volume missing"
            )
        _request(
            client,
            "ProtoOAClosePositionReq",
            {
                "ctidTraderAccountId": client.account_id,
                "positionId": position_id,
                "volume": volume,
            },
            f"close:{client_order_id}",
        )
        _neutralize_label(client, label)

        return {
            "qore_symbol": contract.qore_symbol,
            "provider_symbol": contract.symbol_name,
            "symbol_id": contract.symbol_id,
            "minimum_volume_units": contract.min_volume_units,
            "side": "BUY" if side == _BUY else "SELL",
            "label": label,
            "causal_quote": quote,
            "entry_order_ref_sha256": "sha256:"
            + hashlib.sha256(str(order_id).encode()).hexdigest(),
            "entry_deal_ref_sha256": "sha256:"
            + hashlib.sha256(str(deal_id).encode()).hexdigest(),
            "position_ref_sha256": "sha256:"
            + hashlib.sha256(str(position_id).encode()).hexdigest(),
            "entry_fill_price": str(fill_price),
            "entry_fill_at": datetime.fromtimestamp(
                fill_at_ms / 1000,
                tz=UTC,
            ).isoformat(),
            "position_closed": True,
            "async_fill_reconciled": True,
        }
    finally:
        # Exact-label neutralization is safe even when the normal close already
        # completed. It prevents a failed parsing/poll step from leaving a DEMO
        # calibration mutation unresolved.
        _neutralize_label(client, label)


def _jsonable_observation(
    observation: CTraderEmpiricalSlippageObservation,
) -> dict[str, object]:
    row = asdict(observation)
    for name in ("execution_at", "quote_at"):
        row[name] = getattr(observation, name).isoformat()
    for name in (
        "quote_price",
        "fill_price",
        "signed_slippage_price",
        "signed_slippage_bps",
        "adverse_slippage_bps",
    ):
        row[name] = format(getattr(observation, name), "f")
    if observation.commission_usd is not None:
        row["commission_usd"] = format(observation.commission_usd, "f")
    return row


def run() -> dict[str, object]:
    _authorization()
    governance = PHASE22_DEMO_CALIBRATION_GOVERNANCE
    if governance.live_allowed or governance.real_capital_allowed:
        raise CiboCapitalManagementError(
            "Phase22 calibration governance unexpectedly widened"
        )

    run_key = os.environ.get("GITHUB_RUN_ID", "") + "-" + os.environ.get(
        "GITHUB_RUN_ATTEMPT", "1"
    )
    if not run_key.strip("-"):
        raise CiboCapitalManagementError(
            "Phase22 calibration requires GitHub run identity"
        )
    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    created: list[dict[str, object]] = []
    try:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise CiboCapitalManagementError(
                f"Phase22 DEMO authentication failed: {connected.error}"
            )
        binding = discover_free_account_binding(client)
        by_symbol = {item.qore_symbol: item for item in binding.contracts}
        if tuple(sorted(by_symbol)) != REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "Phase22 calibration provider symbol surface drift"
            )

        before, before_invalid = _history(
            client,
            binding,
            observed_at=datetime.now(UTC),
        )
        before_counts = {
            symbol: len({item.order_ref for item in before.get(symbol, ())})
            for symbol in REQUIRED_SYMBOLS
        }

        for symbol in REQUIRED_SYMBOLS:
            deficit = max(
                0,
                MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL
                - before_counts[symbol],
            )
            for offset in range(deficit):
                ordinal = before_counts[symbol] + offset + 1
                created.append(
                    _one_round_trip(
                        client,
                        by_symbol[symbol],
                        ordinal=ordinal,
                        run_key=run_key,
                    )
                )
                time.sleep(0.35)

        after, after_invalid = _history(
            client,
            binding,
            observed_at=datetime.now(UTC),
        )
        after_counts = {
            symbol: len({item.order_ref for item in after.get(symbol, ())})
            for symbol in REQUIRED_SYMBOLS
        }
        ready = all(
            count >= MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL
            for count in after_counts.values()
        )
        if not ready:
            raise CiboCapitalManagementError(
                "Phase22 calibration minimum causal population not reached"
            )
        if any(after_invalid.get(symbol, 0) for symbol in REQUIRED_SYMBOLS):
            raise CiboCapitalManagementError(
                "Phase22 calibration cohort contains causal quote gaps"
            )

        observations = [
            _jsonable_observation(item)
            for symbol in REQUIRED_SYMBOLS
            for item in after.get(symbol, ())
        ]
        return {
            "schema": "qore.cibo.phase22.demo-provider-calibration.v1",
            "status": "READY",
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "endpoint_host": "demo.ctraderapi.com",
            "account_fingerprint_sha256": hashlib.sha256(
                f"ctrader-demo:{binding.account.account_ref}".encode()
            ).hexdigest(),
            "required_symbols": list(REQUIRED_SYMBOLS),
            "minimum_distinct_entry_orders_per_symbol": (
                MINIMUM_DISTINCT_ENTRY_ORDERS_PER_SYMBOL
            ),
            "before_valid_distinct_orders": before_counts,
            "after_valid_distinct_orders": after_counts,
            "before_invalid_causal_observations": before_invalid,
            "after_invalid_causal_observations": after_invalid,
            "created_round_trips": created,
            "created_round_trip_count": len(created),
            "observations": observations,
            "observation_count": len(observations),
            "empirical_slippage_calibrated": True,
            "execution_model_ready": True,
            "broker_mutation_performed": bool(created),
            "minimum_volume_only": True,
            "created_positions_closed": all(
                row["position_closed"] is True for row in created
            ),
            "historical_provider_economics_claimed": False,
            "historical_holdout_execution_claimed": False,
            "holdout_outcomes_used": False,
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
                "after_valid_distinct_orders": report[
                    "after_valid_distinct_orders"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
