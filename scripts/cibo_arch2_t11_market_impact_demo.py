"""Bounded cTrader DEMO micro-bundle experiment for Architect-2 T11.

The frozen experiment compares aggregate 1x versus 2x exposure while every
child order remains provider minimum volume. For the 2x level both child
positions are opened before either is closed.

The admitted economic metric is provider-settled all-in loss in the DEMO
account deposit currency. The runner requires the account deposit asset to be
USD and binds the final account balance to the final closing-deal settlement.
No synthetic tick value or historical provider term is created.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
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
    T11_NONLINEAR_INPUT_FREEZE,
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
_MARKET = 1
_BUY = 1
_SELL = 2

# Same source-contract surface used by the frozen Phase20 DEMO execution arm.
_SOURCE_CONTRACT_SIZE_UNITS = {
    "AUDJPY": Decimal("100000"),
    "EURUSD": Decimal("100000"),
    "GBPJPY": Decimal("100000"),
    "GBPUSD": Decimal("100000"),
    "NAS100": Decimal("10"),
    "XAUUSD": Decimal("100"),
}

# Provider-native identities already observed before the T11 experiment freeze.
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
    *,
    timeout_seconds: float = 15.0,
) -> object:
    result = client.request(
        name,
        fields,
        client_msg_id=message_id,
        timeout_seconds=timeout_seconds,
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


def _hash_ref(kind: str, value: int) -> str:
    return "sha256:" + hashlib.sha256(
        f"{kind}|{value}".encode()
    ).hexdigest()


def _trader(
    client: SpotwareCTraderOpenApiClient,
    message_id: str,
) -> object:
    response = _request(
        client,
        "ProtoOATraderReq",
        {"ctidTraderAccountId": client.account_id},
        message_id,
    )
    trader = getattr(response, "trader", None)
    if trader is None:
        raise CiboCapitalManagementError("T11 DEMO trader entity missing")
    return trader


def _money_digits(message: object, fallback: int = 0) -> int:
    value = (
        getattr(message, "moneyDigits", fallback)
        if _field_present(message, "moneyDigits")
        else fallback
    )
    if type(value) is not int or value < 0:
        raise CiboCapitalManagementError("T11 DEMO moneyDigits invalid")
    return value


def _balance_usd(trader: object) -> Decimal:
    raw = getattr(trader, "balance", None)
    if type(raw) is not int:
        raise CiboCapitalManagementError("T11 DEMO account balance invalid")
    return Decimal(raw).scaleb(-_money_digits(trader))


def _close_balance_usd(detail: object, *, fallback_digits: int) -> Decimal:
    raw = getattr(detail, "balance", None)
    if type(raw) is not int:
        raise CiboCapitalManagementError(
            "T11 closing settlement balance invalid"
        )
    return Decimal(raw).scaleb(-_money_digits(detail, fallback_digits))


def _assert_usd_deposit_asset(
    client: SpotwareCTraderOpenApiClient,
    trader: object,
) -> None:
    asset_id = getattr(trader, "depositAssetId", None)
    if type(asset_id) is not int or asset_id <= 0:
        raise CiboCapitalManagementError(
            "T11 DEMO deposit asset id invalid"
        )
    response = _request(
        client,
        "ProtoOAAssetListReq",
        {"ctidTraderAccountId": client.account_id},
        "t11-asset-list",
    )
    matches = tuple(
        asset
        for asset in tuple(getattr(response, "asset", ()))
        if getattr(asset, "assetId", None) == asset_id
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "T11 DEMO deposit asset could not be resolved"
        )
    if str(getattr(matches[0], "name", "")).upper() != "USD":
        raise CiboCapitalManagementError(
            "T11 market-impact V1 requires USD DEMO deposit asset"
        )


def _reconcile(
    client: SpotwareCTraderOpenApiClient,
    message_id: str,
) -> object:
    return _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        message_id,
    )


def _assert_clean_state(
    client: SpotwareCTraderOpenApiClient,
    message_id: str,
) -> None:
    response = _reconcile(client, message_id)
    if tuple(getattr(response, "position", ())) or tuple(
        getattr(response, "order", ())
    ):
        raise CiboCapitalManagementError(
            "T11 DEMO experiment requires zero open positions/orders"
        )


def _position_for_label(
    client: SpotwareCTraderOpenApiClient,
    *,
    label: str,
    message_id: str,
) -> object | None:
    response = _reconcile(client, message_id)
    matches = tuple(
        item
        for item in tuple(getattr(response, "position", ()))
        if getattr(getattr(item, "tradeData", None), "label", None) == label
    )
    if len(matches) > 1:
        raise CiboCapitalManagementError(
            "T11 label maps to multiple positions"
        )
    return matches[0] if matches else None


def _single_deal(response: object, *, order_id: int) -> object | None:
    direct = getattr(response, "deal", None)
    if (
        direct is not None
        and type(getattr(direct, "dealId", None)) is int
        and getattr(direct, "orderId", order_id) == order_id
    ):
        return cast(object, direct)
    try:
        rows = tuple(getattr(response, "deal", ()))
    except TypeError:
        rows = ()
    matches = tuple(
        item
        for item in rows
        if getattr(item, "orderId", order_id) == order_id
        and type(getattr(item, "dealId", None)) is int
        and getattr(item, "dealId", 0) > 0
    )
    return matches[0] if len(matches) == 1 else None


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
                f"t11-order:{order_id}:{attempt}",
            )
        )
        deal = _single_deal(response, order_id=order_id)
        position = _position_for_label(
            client,
            label=label,
            message_id=f"t11-position:{order_id}:{attempt}",
        )
        position_id = getattr(position, "positionId", None) if position else None
        trade = getattr(position, "tradeData", None) if position else None
        volume = getattr(trade, "volume", None) if trade else None
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
        "T11 child entry did not reconcile to fill/position"
    )


def _position_deals(
    client: SpotwareCTraderOpenApiClient,
    *,
    position_id: int,
    symbol_id: int,
    started_at: datetime,
) -> tuple[object, ...]:
    for attempt in range(25):
        response = _request(
            client,
            "ProtoOADealListReq",
            {
                "ctidTraderAccountId": client.account_id,
                "fromTimestamp": int(
                    (started_at - timedelta(minutes=1)).timestamp() * 1000
                ),
                "toTimestamp": int(datetime.now(UTC).timestamp() * 1000),
                "maxRows": 1000,
            },
            f"t11-deals:{position_id}:{attempt}",
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
        closing = tuple(
            row
            for row in rows
            if getattr(row, "closePositionDetail", None) is not None
        )
        if rows and closing:
            return rows
        time.sleep(0.25)
    raise CiboCapitalManagementError(
        "T11 round trip did not reconcile closing settlement"
    )


def _neutralize_label(
    client: SpotwareCTraderOpenApiClient,
    *,
    label: str,
) -> None:
    response = _reconcile(client, f"t11-neutralize:{label}")
    for order in tuple(getattr(response, "order", ())):
        trade = getattr(order, "tradeData", None)
        if getattr(trade, "label", None) != label:
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

    response = _reconcile(client, f"t11-neutralize-pos:{label}")
    for position in tuple(getattr(response, "position", ())):
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
                "T11 containment position invalid"
            )
        _request(
            client,
            "ProtoOAClosePositionReq",
            {
                "ctidTraderAccountId": client.account_id,
                "positionId": position_id,
                "volume": volume,
            },
            f"t11-containment-close:{position_id}",
        )
    time.sleep(0.2)


def _open_child(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    native_volume: int,
    side_code: int,
    label: str,
    child_id: str,
) -> dict[str, object]:
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
    order_id = getattr(order, "orderId", None) if order else None
    if type(order_id) is not int or order_id <= 0:
        raise CiboCapitalManagementError(
            "T11 child entry returned no order id"
        )
    entry_deal, position_id, position_volume = _wait_entry(
        client,
        opened,
        order_id=order_id,
        label=label,
    )
    if position_volume != native_volume:
        raise CiboCapitalManagementError(
            "T11 child position volume drift"
        )
    return {
        "label": label,
        "order_id": order_id,
        "position_id": position_id,
        "entry_deal_id": int(getattr(entry_deal, "dealId")),
        "position_volume": position_volume,
    }


def _close_child(
    client: SpotwareCTraderOpenApiClient,
    *,
    child: dict[str, object],
    symbol_id: int,
    started_at: datetime,
    fallback_money_digits: int,
) -> dict[str, object]:
    position_id = cast(int, child["position_id"])
    volume = cast(int, child["position_volume"])
    _request(
        client,
        "ProtoOAClosePositionReq",
        {
            "ctidTraderAccountId": client.account_id,
            "positionId": position_id,
            "volume": volume,
        },
        f"t11-close:{position_id}",
    )
    label = cast(str, child["label"])
    _neutralize_label(client, label=label)
    deals = _position_deals(
        client,
        position_id=position_id,
        symbol_id=symbol_id,
        started_at=started_at,
    )
    close_deal = tuple(
        row
        for row in deals
        if getattr(row, "closePositionDetail", None) is not None
    )[-1]
    detail = getattr(close_deal, "closePositionDetail")
    settlement_balance = _close_balance_usd(
        detail,
        fallback_digits=fallback_money_digits,
    )
    return {
        "label_sha256": "sha256:"
        + hashlib.sha256(label.encode()).hexdigest(),
        "order_ref_sha256": _hash_ref(
            "order", cast(int, child["order_id"])
        ),
        "position_ref_sha256": _hash_ref("position", position_id),
        "entry_deal_ref_sha256": _hash_ref(
            "deal", cast(int, child["entry_deal_id"])
        ),
        "close_deal_ref_sha256": _hash_ref(
            "deal", int(getattr(close_deal, "dealId"))
        ),
        "settlement_balance_usd": settlement_balance,
    }


def _validate_contract_binding(binding: CTraderDemoFreeBinding) -> None:
    by_symbol = {item.qore_symbol: item for item in binding.contracts}
    if tuple(sorted(by_symbol)) != REQUIRED_SYMBOLS:
        raise CiboCapitalManagementError(
            "T11 provider symbol surface drift"
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
                f"T11 frozen provider contract drift: {symbol}"
            )


def source_minimum_volume(
    *,
    qore_symbol: str,
    min_native_volume: int,
) -> Decimal:
    source_contract = _SOURCE_CONTRACT_SIZE_UNITS.get(qore_symbol)
    if source_contract is None:
        raise CiboCapitalManagementError(
            "T11 source contract identity missing"
        )
    underlying = Decimal(min_native_volume) * _NATIVE_VOLUME_UNIT
    result = underlying / source_contract
    if result <= 0:
        raise CiboCapitalManagementError(
            "T11 source minimum volume invalid"
        )
    return result


def pair_plan(pair_index: int) -> tuple[str, tuple[int, int]]:
    if pair_index <= 0:
        raise CiboCapitalManagementError(
            "T11 pair index must be positive"
        )
    side = "long" if pair_index % 2 else "short"
    levels = (1, 2) if pair_index % 2 else (2, 1)
    return side, levels


def _bundle(
    client: SpotwareCTraderOpenApiClient,
    *,
    qore_symbol: str,
    provider_symbol: str,
    symbol_id: int,
    native_volume: int,
    child_count: int,
    side: str,
    phase: str,
    pair_index: int,
    fold_index: int,
    run_key: str,
) -> tuple[T11MarketImpactEpisode, dict[str, object]]:
    if child_count not in {1, 2}:
        raise CiboCapitalManagementError(
            "T11 child count must be 1 or 2"
        )
    _assert_clean_state(
        client,
        f"t11-clean-pre:{qore_symbol}:{phase}:{pair_index}:{child_count}",
    )
    trader_before = _trader(
        client,
        f"t11-trader-pre:{qore_symbol}:{phase}:{pair_index}:{child_count}",
    )
    fallback_digits = _money_digits(trader_before)
    balance_before = _balance_usd(trader_before)
    started_at = datetime.now(UTC)
    side_code = _BUY if side == "long" else _SELL
    opened: list[dict[str, object]] = []
    try:
        for child_index in range(1, child_count + 1):
            label = (
                f"{_LABEL_PREFIX}{qore_symbol}:{run_key[-6:]}:"
                f"{phase[0]}{pair_index:02d}:L{child_count}:C{child_index}"
            )
            child_id = (
                f"qore-t11-{run_key[-10:]}-{qore_symbol.lower()}-"
                f"{phase[0].lower()}{pair_index:02d}-"
                f"l{child_count}-c{child_index}"
            )[-50:]
            opened.append(
                _open_child(
                    client,
                    symbol_id=symbol_id,
                    native_volume=native_volume,
                    side_code=side_code,
                    label=label,
                    child_id=child_id,
                )
            )

        # Critical 2x invariant: all children are open before any close begins.
        if child_count == 2:
            response = _reconcile(
                client,
                f"t11-aggregate-check:{qore_symbol}:{phase}:{pair_index}",
            )
            active = tuple(
                item
                for item in tuple(getattr(response, "position", ()))
                if str(
                    getattr(getattr(item, "tradeData", None), "label", "")
                ).startswith(_LABEL_PREFIX)
            )
            if len(active) != 2:
                raise CiboCapitalManagementError(
                    "T11 2x level failed simultaneous aggregate exposure invariant"
                )

        settlements = [
            _close_child(
                client,
                child=child,
                symbol_id=symbol_id,
                started_at=started_at,
                fallback_money_digits=fallback_digits,
            )
            for child in opened
        ]
        _assert_clean_state(
            client,
            f"t11-clean-post:{qore_symbol}:{phase}:{pair_index}:{child_count}",
        )
        trader_after = _trader(
            client,
            f"t11-trader-post:{qore_symbol}:{phase}:{pair_index}:{child_count}",
        )
        balance_after = _balance_usd(trader_after)
        final_settlement_balance = cast(
            Decimal, settlements[-1]["settlement_balance_usd"]
        )
        if balance_after != final_settlement_balance:
            raise CiboCapitalManagementError(
                "T11 final balance does not bind to final closing settlement"
            )
        net_pnl = balance_after - balance_before
        adverse_cost = max(Decimal(0), -net_pnl)
        minimum_volume = source_minimum_volume(
            qore_symbol=qore_symbol,
            min_native_volume=native_volume,
        )
        observed_at = datetime.now(UTC)
        if observed_at <= FROZEN_AT:
            raise CiboCapitalManagementError(
                "T11 market-impact observation predates freeze"
            )
        pair_id = f"{qore_symbol}-{phase}-{pair_index:02d}"
        episode = T11MarketImpactEpisode(
            evidence_id=(
                "t11-impact:"
                + hashlib.sha256(
                    (
                        f"{run_key}|{pair_id}|{child_count}|"
                        f"{observed_at.isoformat()}|{adverse_cost}"
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
            adverse_slippage_cost_total_usd=adverse_cost,
            observed_at=observed_at,
            provider_bound=True,
            every_child_order_minimum_volume=True,
            holdout_outcomes_used=False,
            target_aware=False,
            productive_authority=False,
        )
        raw = {
            "episode": _jsonable(asdict(episode)),
            "provider_symbol": provider_symbol,
            "balance_before_usd": format(balance_before, "f"),
            "balance_after_usd": format(balance_after, "f"),
            "net_realized_pnl_usd": format(net_pnl, "f"),
            "adverse_realized_cost_usd": format(adverse_cost, "f"),
            "children": _jsonable(settlements),
            "all_children_open_before_first_close": True,
        }
        return episode, raw
    except Exception:
        for child in opened:
            try:
                _neutralize_label(
                    client,
                    label=cast(str, child["label"]),
                )
            except Exception:
                pass
        raise


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
    return cast(dict[str, object], _jsonable(asdict(value)))


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
                "T11 market-impact requires HEDGED DEMO account"
            )
        trader = _trader(client, "t11-initial-trader")
        _assert_usd_deposit_asset(client, trader)
        _assert_clean_state(client, "t11-initial-clean-state")

        binding = discover_free_account_binding(client)
        _validate_contract_binding(binding)
        by_symbol = {item.qore_symbol: item for item in binding.contracts}
        episodes: list[T11MarketImpactEpisode] = []
        raw_rows: list[dict[str, object]] = []

        for symbol in REQUIRED_SYMBOLS:
            contract = by_symbol[symbol]
            for phase, pair_count in (
                (
                    "CALIBRATION",
                    MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL,
                ),
                (
                    "VALIDATION",
                    MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL,
                ),
            ):
                for pair_index in range(1, pair_count + 1):
                    side, level_order = pair_plan(pair_index)
                    fold_index = 0 if phase == "CALIBRATION" else pair_index
                    for child_count in level_order:
                        episode, raw = _bundle(
                            client,
                            qore_symbol=symbol,
                            provider_symbol=contract.symbol_name,
                            symbol_id=contract.symbol_id,
                            native_volume=contract.min_volume_units,
                            child_count=child_count,
                            side=side,
                            phase=phase,
                            pair_index=pair_index,
                            fold_index=fold_index,
                            run_key=run_key,
                        )
                        episodes.append(episode)
                        raw_rows.append(raw)
                        time.sleep(0.25)

        evaluation = evaluate_t11_market_impact(tuple(episodes))
        _assert_clean_state(client, "t11-terminal-clean-state")
        report: dict[str, object] = {
            "schema": "qore.cibo.arch2.t11.market-impact-demo.v2",
            "status": (
                "MARKET_IMPACT_MODEL_READY"
                if evaluation.market_impact_model_ready
                else "MARKET_IMPACT_MODEL_FALSIFIED_OR_NOT_READY"
            ),
            "protocol_sha256": T11_NONLINEAR_INPUT_FREEZE.fingerprint(),
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "deposit_asset": "USD",
            "account_fingerprint_sha256": account_fingerprint,
            "episode_count": len(episodes),
            "child_entry_count": sum(item.child_count for item in episodes),
            "minimum_volume_child_orders_only": True,
            "two_x_children_open_before_close": True,
            "balanced_long_short_pairs": True,
            "alternating_level_order": True,
            "metric": "ADVERSE_REALIZED_ALL_IN_SETTLEMENT_COST_USD",
            "calibration_pairs_per_symbol": (
                MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL
            ),
            "validation_pairs_per_symbol": (
                MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL
            ),
            "raw_rows": raw_rows,
            "evaluation": _evaluation_payload(evaluation),
            "all_created_positions_closed": True,
            "broker_mutation_performed": True,
            "mutation_scope": (
                "CTRADER_DEMO_MINIMUM_VOLUME_CHILD_ROUND_TRIPS_ONLY"
            ),
            "holdout_outcomes_used": False,
            "phase22_v2_consumed": False,
            "historical_provider_economics_claimed": False,
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
                "T11 frozen episode-count drift"
            )
        if report["child_entry_count"] != 216:
            raise CiboCapitalManagementError(
                "T11 frozen child-count drift"
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
