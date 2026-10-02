"""Bounded cTrader DEMO settlement-cost experiment for Architect-2 T11.

The frozen T11 protocol compares matched micro-bundles made only from provider
minimum-volume child orders:
- level 1: one child;
- level 2: two children.

For every bundle, all children are open before any close begins. The observed cost
is the provider-authoritative realized round-trip settlement cost in the USD
account deposit asset. Calibration and validation populations are disjoint,
long/short sides are balanced, and matched-pair level order alternates to remove
systematic first/second execution bias.

No Phase22 V2 outcome, FundedNext account, VPS, LIVE endpoint, real capital, or
canonical CIBO ledger is touched.
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
_FROZEN_DEPOSIT_ASSET_MARKER = dict(deposit_asset="USD")
EXPECTED_ACCOUNT_FINGERPRINT_SHA256 = (
    "70d38b13a2afb1ada12883a486ddb39aa0626e4c262b69ee44410bb6531d6086"
)
_LABEL_PREFIX = "CIBOA2T11:"
_NATIVE_VOLUME_UNIT = Decimal("0.01")
_MARKET = 1
_BUY = 1
_SELL = 2

# Frozen from provider-economics run 36810489106 / artifact 11139835744,
# which predates the T11 nonlinear protocol freeze.
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


def _native_money(value: object, digits: object, name: str) -> Decimal:
    if type(value) is not int or type(digits) is not int or digits < 0:
        raise CiboCapitalManagementError(
            f"T11 market-impact invalid settlement money field: {name}"
        )
    return Decimal(value).scaleb(-digits)


def realized_settlement_cost_usd(
    *,
    entry_commission_usd: Decimal,
    gross_profit_usd: Decimal,
    swap_usd: Decimal,
    close_commission_usd: Decimal,
    pnl_conversion_fee_usd: Decimal,
) -> Decimal:
    """Return non-negative realized economic cost for one exact round trip."""

    values = (
        entry_commission_usd,
        gross_profit_usd,
        swap_usd,
        close_commission_usd,
        pnl_conversion_fee_usd,
    )
    if any(
        not isinstance(value, Decimal) or not value.is_finite()
        for value in values
    ):
        raise CiboCapitalManagementError(
            "T11 market-impact settlement components must be finite Decimal"
        )
    net = sum(values, Decimal(0))
    return max(Decimal(0), -net)


def _deposit_asset_name(
    client: SpotwareCTraderOpenApiClient,
) -> str:
    trader_response = _request(
        client,
        "ProtoOATraderReq",
        {"ctidTraderAccountId": client.account_id},
        "t11-deposit-asset-trader",
    )
    trader = getattr(trader_response, "trader", None)
    if trader is None:
        raise CiboCapitalManagementError(
            "T11 market-impact trader account response missing"
        )
    asset_id = getattr(trader, "depositAssetId", None)
    if type(asset_id) is not int or asset_id <= 0:
        raise CiboCapitalManagementError(
            "T11 market-impact depositAssetId unavailable"
        )

    asset_response = _request(
        client,
        "ProtoOAAssetListReq",
        {"ctidTraderAccountId": client.account_id},
        "t11-deposit-asset-list",
    )
    matches = tuple(
        item
        for item in tuple(getattr(asset_response, "asset", ()))
        if getattr(item, "assetId", None) == asset_id
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "T11 market-impact deposit asset identity ambiguous"
        )
    name = getattr(matches[0], "name", None)
    if not isinstance(name, str) or not name:
        raise CiboCapitalManagementError(
            "T11 market-impact deposit asset name unavailable"
        )
    if name.upper() != "USD":
        raise CiboCapitalManagementError(
            "T11 market-impact frozen experiment requires USD deposit asset"
        )
    return "USD"


def _hash_ref(kind: str, value: int) -> str:
    return "sha256:" + hashlib.sha256(
        f"{kind}|{value}".encode()
    ).hexdigest()


def _single_deal(response: object, *, order_id: int) -> object | None:
    direct = getattr(response, "deal", None)
    if (
        direct is not None
        and type(getattr(direct, "dealId", None)) is int
        and getattr(direct, "orderId", order_id) == order_id
    ):
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
    if not matches:
        return None
    return cast(
        object,
        min(
            matches,
            key=lambda item: (
                getattr(item, "executionTimestamp", 0),
                getattr(item, "dealId", 0),
            ),
        ),
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


def _closing_deal(
    client: SpotwareCTraderOpenApiClient,
    *,
    position_id: int,
    opened_at: datetime,
) -> object:
    for attempt in range(25):
        response = _request(
            client,
            "ProtoOADealListReq",
            {
                "ctidTraderAccountId": client.account_id,
                "fromTimestamp": int(
                    (opened_at - timedelta(minutes=2)).timestamp() * 1000
                ),
                "toTimestamp": int(datetime.now(UTC).timestamp() * 1000),
                "maxRows": 500,
            },
            f"t11-close-deals:{position_id}:{attempt}",
        )
        matches = tuple(
            deal
            for deal in tuple(getattr(response, "deal", ()))
            if getattr(deal, "positionId", None) == position_id
            and _field_present(deal, "closePositionDetail")
        )
        if matches:
            return max(
                matches,
                key=lambda item: getattr(item, "executionTimestamp", 0),
            )
        time.sleep(0.25)
    raise CiboCapitalManagementError(
        "T11 market-impact close settlement did not reconcile"
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
    if any(
        getattr(getattr(item, "tradeData", None), "label", None) == label
        for item in tuple(getattr(terminal, "position", ()))
    ):
        raise CiboCapitalManagementError(
            "T11 market-impact position remains after containment"
        )


def _settlement_components(
    *,
    entry_deal: object,
    close_deal: object,
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
    entry_digits = getattr(entry_deal, "moneyDigits", None)
    entry_commission = _native_money(
        getattr(entry_deal, "commission", 0),
        entry_digits,
        "entry commission",
    )
    close_detail = getattr(close_deal, "closePositionDetail", None)
    if close_detail is None:
        raise CiboCapitalManagementError(
            "T11 market-impact closePositionDetail missing"
        )
    close_digits = getattr(
        close_detail,
        "moneyDigits",
        getattr(close_deal, "moneyDigits", None),
    )
    return (
        entry_commission,
        _native_money(
            getattr(close_detail, "grossProfit", 0),
            close_digits,
            "gross profit",
        ),
        _native_money(
            getattr(close_detail, "swap", 0),
            close_digits,
            "swap",
        ),
        _native_money(
            getattr(close_detail, "commission", 0),
            close_digits,
            "close commission",
        ),
        _native_money(
            getattr(close_detail, "pnlConversionFee", 0),
            close_digits,
            "pnl conversion fee",
        ),
    )


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


def source_minimum_volume(
    *,
    min_native_volume: int,
    lot_size_units: Decimal,
) -> Decimal:
    source_volume = (
        Decimal(min_native_volume) * _NATIVE_VOLUME_UNIT / lot_size_units
    )
    if source_volume <= 0:
        raise CiboCapitalManagementError(
            "T11 market-impact source minimum volume invalid"
        )
    return source_volume


_source_minimum_volume = source_minimum_volume


def _bundle(
    client: SpotwareCTraderOpenApiClient,
    *,
    qore_symbol: str,
    symbol_id: int,
    native_volume: int,
    lot_size_units: Decimal,
    child_count: int,
    level_order_position: int,
    side: str,
    phase: str,
    pair_index: int,
    fold_index: int,
    run_key: str,
    deposit_asset: str,
) -> tuple[T11MarketImpactEpisode, dict[str, object]]:
    if child_count not in {1, 2} or level_order_position not in {1, 2}:
        raise CiboCapitalManagementError(
            "T11 market-impact frozen bundle geometry invalid"
        )
    if deposit_asset != "USD":
        raise CiboCapitalManagementError(
            "T11 market-impact bundle requires USD deposit asset"
        )
    side_code = _BUY if side == "long" else _SELL
    pair_id = f"{qore_symbol}-{phase}-{pair_index:02d}"
    bundle_id = f"{pair_id}-L{child_count}"

    opened_children: list[dict[str, object]] = []
    labels: list[str] = []
    try:
        # Frozen invariant: all children are open before any close begins.
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
            opened_at = datetime.now(UTC)
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
                    "comment": "cibo-arch2-t11-settlement-impact",
                },
                child_id,
            )
            order = getattr(opened, "order", None)
            order_id = (
                getattr(order, "orderId", None)
                if order is not None
                else None
            )
            if type(order_id) is not int or order_id <= 0:
                raise CiboCapitalManagementError(
                    "T11 market-impact submit returned no order id"
                )
            entry_deal, position_id, position_volume = _wait_entry(
                client,
                opened,
                order_id=order_id,
                label=label,
            )
            entry_deal_id = getattr(entry_deal, "dealId", None)
            if type(entry_deal_id) is not int or entry_deal_id <= 0:
                raise CiboCapitalManagementError(
                    "T11 market-impact entry deal identity invalid"
                )
            opened_children.append(
                {
                    "label": label,
                    "opened_at": opened_at,
                    "order_id": order_id,
                    "entry_deal": entry_deal,
                    "entry_deal_id": entry_deal_id,
                    "position_id": position_id,
                    "position_volume": position_volume,
                }
            )
            labels.append(label)
            time.sleep(0.10)

        if len(opened_children) != child_count:
            raise CiboCapitalManagementError(
                "T11 market-impact child-open accounting drift"
            )

        children: list[dict[str, object]] = []
        total_cost = Decimal(0)
        for child in opened_children:
            position_id = cast(int, child["position_id"])
            position_volume = cast(int, child["position_volume"])
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
            close_deal = _closing_deal(
                client,
                position_id=position_id,
                opened_at=cast(datetime, child["opened_at"]),
            )
            close_deal_id = getattr(close_deal, "dealId", None)
            close_ms = getattr(close_deal, "executionTimestamp", None)
            if (
                type(close_deal_id) is not int
                or close_deal_id <= 0
                or type(close_ms) is not int
                or close_ms <= 0
            ):
                raise CiboCapitalManagementError(
                    "T11 market-impact close deal identity invalid"
                )
            components = _settlement_components(
                entry_deal=child["entry_deal"],
                close_deal=close_deal,
            )
            cost = realized_settlement_cost_usd(
                entry_commission_usd=components[0],
                gross_profit_usd=components[1],
                swap_usd=components[2],
                close_commission_usd=components[3],
                pnl_conversion_fee_usd=components[4],
            )
            total_cost += cost
            children.append(
                {
                    "order_ref_sha256": _hash_ref(
                        "order",
                        cast(int, child["order_id"]),
                    ),
                    "entry_deal_ref_sha256": _hash_ref(
                        "deal",
                        cast(int, child["entry_deal_id"]),
                    ),
                    "close_deal_ref_sha256": _hash_ref(
                        "deal",
                        close_deal_id,
                    ),
                    "position_ref_sha256": _hash_ref(
                        "position",
                        position_id,
                    ),
                    "entry_commission_usd": components[0],
                    "gross_profit_usd": components[1],
                    "swap_usd": components[2],
                    "close_commission_usd": components[3],
                    "pnl_conversion_fee_usd": components[4],
                    "realized_settlement_cost_usd": cost,
                    "settled_at": datetime.fromtimestamp(
                        close_ms / 1000,
                        tz=UTC,
                    ),
                    "position_closed": True,
                }
            )
            time.sleep(0.10)

        for label in labels:
            _neutralize_label(client, label=label)

        observed_at = max(
            cast(datetime, item["settled_at"])
            for item in children
        )
        if observed_at <= FROZEN_AT:
            raise CiboCapitalManagementError(
                "T11 market-impact settlement does not postdate freeze"
            )
        minimum_volume = source_minimum_volume(
            min_native_volume=native_volume,
            lot_size_units=lot_size_units,
        )
        episode = T11MarketImpactEpisode(
            evidence_id=(
                "t11-impact:"
                + hashlib.sha256(
                    (
                        f"{run_key}|{bundle_id}|{observed_at.isoformat()}|"
                        f"{total_cost}|{level_order_position}"
                    ).encode()
                ).hexdigest()
            ),
            qore_symbol=qore_symbol,
            pair_id=pair_id,
            phase=phase,
            fold_index=fold_index,
            side=side,
            child_count=child_count,
            level_order_position=level_order_position,
            minimum_volume=minimum_volume,
            aggregate_volume=minimum_volume * child_count,
            realized_settlement_cost_total_usd=total_cost,
            deposit_asset="USD",
            observed_at=observed_at,
            provider_bound=True,
            every_child_order_minimum_volume=True,
            holdout_outcomes_used=False,
            target_aware=False,
            productive_authority=False,
        )
        return episode, {
            "episode": _jsonable(asdict(episode)),
            "children": _jsonable(children),
            "two_x_children_open_before_close": True,
        }
    finally:
        for label in labels:
            _neutralize_label(client, label=label)

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


def _evaluation_payload(value: Any) -> dict[str, object]:
    return cast(dict[str, object], _jsonable(asdict(value)))


def pair_plan(pair_index: int) -> tuple[str, tuple[int, int]]:
    if pair_index <= 0:
        raise CiboCapitalManagementError(
            "T11 market-impact pair index must be positive"
        )
    side = "long" if pair_index % 2 else "short"
    levels = (1, 2) if pair_index % 2 else (2, 1)
    return side, levels


def _levels_for_pair(pair_index: int) -> tuple[int, int]:
    return pair_plan(pair_index)[1]


def run() -> dict[str, object]:
    _authorization()
    freeze = T11_NONLINEAR_INPUT_FREEZE.market_impact
    if freeze.required_symbols != REQUIRED_SYMBOLS:
        raise CiboCapitalManagementError(
            "T11 market-impact frozen symbol surface drift"
        )
    if (
        not freeze.realized_settlement_cost_required
        or not freeze.deposit_asset_usd_required
        or not freeze.balanced_long_short_pairs_required
        or not freeze.alternating_level_order_required
        or not freeze.each_child_order_minimum_volume_required
    ):
        raise CiboCapitalManagementError(
            "T11 market-impact frozen controls weakened"
        )
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
        deposit_asset = _deposit_asset_name(client)
        binding = discover_free_account_binding(client)
        _validate_contract_binding(binding)
        by_symbol = {item.qore_symbol: item for item in binding.contracts}

        episodes: list[T11MarketImpactEpisode] = []
        raw_rows: list[dict[str, object]] = []
        phases = (
            (
                "CALIBRATION",
                MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL,
            ),
            (
                "VALIDATION",
                MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL,
            ),
        )
        for symbol in REQUIRED_SYMBOLS:
            contract = by_symbol[symbol]
            for phase, pair_count in phases:
                for pair_index in range(1, pair_count + 1):
                    side, levels = pair_plan(pair_index)
                    fold_index = 0 if phase == "CALIBRATION" else pair_index
                    for order_position, child_count in enumerate(
                        levels,
                        start=1,
                    ):
                        episode, raw = _bundle(
                            client,
                            qore_symbol=symbol,
                            symbol_id=contract.symbol_id,
                            native_volume=contract.min_volume_units,
                            lot_size_units=contract.lot_size_units,
                            child_count=child_count,
                            level_order_position=order_position,
                            side=side,
                            phase=phase,
                            pair_index=pair_index,
                            fold_index=fold_index,
                            run_key=run_key,
                            deposit_asset=deposit_asset,
                        )
                        episodes.append(episode)
                        raw_rows.append(raw)
                        time.sleep(0.25)

        evaluation = evaluate_t11_market_impact(tuple(episodes))
        report: dict[str, object] = {
            "schema": "qore.cibo.arch2.t11.market-impact-demo.v2",
            "status": (
                "MARKET_IMPACT_MODEL_READY"
                if evaluation.market_impact_model_ready
                else "MARKET_IMPACT_MODEL_FALSIFIED_OR_NOT_READY"
            ),
            "protocol_frozen_at": FROZEN_AT.isoformat(),
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "account_fingerprint_sha256": account_fingerprint,
            "deposit_asset": "USD",
            "metric": "ADVERSE_REALIZED_ALL_IN_SETTLEMENT_COST_USD",
            "episode_count": len(episodes),
            "child_entry_count": sum(item.child_count for item in episodes),
            "minimum_volume_child_orders_only": True,
            "two_x_children_open_before_close": True,
            "balanced_long_short_pairs": True,
            "alternating_level_order": True,
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
                "metric": report["metric"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
