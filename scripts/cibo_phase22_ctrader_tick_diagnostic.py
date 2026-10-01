"""Read-only cTrader historical-tick diagnostic for Phase22 provider evidence."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from qore.infrastructure.cibo_phase22_demo_calibration_contract import (
    CALIBRATION_LABEL_PREFIX,
    REQUIRED_SYMBOLS,
)
from qore.infrastructure.ctrader_demo_free_binding import (
    discover_free_account_binding,
)
from qore.infrastructure.ctrader_demo_free_sink import (
    credentials_from_environment,
)
from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

_BID = 1
_ASK = 2
_LOOKBACKS_MS = (300_000, 900_000, 3_600_000)


def _label(order: object | None) -> str | None:
    if order is None:
        return None
    trade_data = getattr(order, "tradeData", None)
    value = getattr(trade_data, "label", None) if trade_data is not None else None
    if isinstance(value, str) and value:
        return value
    value = getattr(order, "label", None)
    return value if isinstance(value, str) and value else None


def _request(
    client: SpotwareCTraderOpenApiClient,
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
        raise RuntimeError(f"{name}:{type(result.error).__name__}:{result.error}")
    return result.value


def build_report() -> dict[str, object]:
    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    try:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise RuntimeError(
                f"DEMO authentication failed: {type(connected.error).__name__}"
            )
        binding = discover_free_account_binding(client)
        contracts = {item.symbol_id: item for item in binding.contracts}
        by_symbol = {item.qore_symbol: item for item in binding.contracts}
        if tuple(sorted(by_symbol)) != REQUIRED_SYMBOLS:
            raise RuntimeError("provider symbol surface drift")

        observed = datetime.now(UTC)
        start = observed - timedelta(days=365)
        deals = _request(
            client,
            "ProtoOADealListReq",
            {
                "ctidTraderAccountId": client.account_id,
                "fromTimestamp": int(start.timestamp() * 1000),
                "toTimestamp": int(observed.timestamp() * 1000),
                "maxRows": 5000,
            },
            "phase22-tick-diag-deals",
        )
        orders = _request(
            client,
            "ProtoOAOrderListReq",
            {
                "ctidTraderAccountId": client.account_id,
                "fromTimestamp": int(start.timestamp() * 1000),
                "toTimestamp": int(observed.timestamp() * 1000),
            },
            "phase22-tick-diag-orders",
        )
        orders_by_id = {
            int(item.orderId): item
            for item in tuple(getattr(orders, "order", ()))
            if type(getattr(item, "orderId", None)) is int
            and item.orderId > 0
        }

        latest: dict[str, object] = {}
        for deal in tuple(getattr(deals, "deal", ())):
            symbol_id = getattr(deal, "symbolId", None)
            order_id = getattr(deal, "orderId", None)
            execution_ms = getattr(deal, "executionTimestamp", None)
            if (
                type(symbol_id) is not int
                or symbol_id not in contracts
                or type(order_id) is not int
                or type(execution_ms) is not int
                or execution_ms <= 0
            ):
                continue
            order = orders_by_id.get(order_id)
            label = _label(order)
            if label is None or not label.startswith(CALIBRATION_LABEL_PREFIX):
                continue
            symbol = contracts[symbol_id].qore_symbol
            current = latest.get(symbol)
            if current is None or int(current.executionTimestamp) < execution_ms:
                latest[symbol] = deal

        rows: list[dict[str, object]] = []
        for symbol in REQUIRED_SYMBOLS:
            deal = latest.get(symbol)
            if deal is None:
                rows.append(
                    {
                        "qore_symbol": symbol,
                        "status": "NO_CALIBRATION_DEAL",
                        "probes": [],
                    }
                )
                continue
            contract = by_symbol[symbol]
            execution_ms = int(deal.executionTimestamp)
            trade_side = int(deal.tradeSide)
            probes: list[dict[str, object]] = []
            for quote_name, quote_type in (("BID", _BID), ("ASK", _ASK)):
                for lookback_ms in _LOOKBACKS_MS:
                    time.sleep(0.25)
                    result = client.request(
                        "ProtoOAGetTickDataReq",
                        {
                            "ctidTraderAccountId": client.account_id,
                            "symbolId": contract.symbol_id,
                            "type": quote_type,
                            "fromTimestamp": max(0, execution_ms - lookback_ms),
                            "toTimestamp": execution_ms,
                        },
                        client_msg_id=(
                            f"phase22-tick-diag-{contract.symbol_id}-"
                            f"{quote_type}-{lookback_ms}"
                        ),
                        timeout_seconds=10.0,
                    )
                    if isinstance(result, Failure):
                        probes.append(
                            {
                                "quote_type": quote_name,
                                "lookback_ms": lookback_ms,
                                "status": "ERROR",
                                "error_type": type(result.error).__name__,
                                "error": str(result.error),
                            }
                        )
                        continue
                    response = result.value
                    ticks = tuple(getattr(response, "tickData", ()))
                    first = ticks[0] if ticks else None
                    probes.append(
                        {
                            "quote_type": quote_name,
                            "lookback_ms": lookback_ms,
                            "status": "OK",
                            "account_matches": (
                                getattr(
                                    response,
                                    "ctidTraderAccountId",
                                    client.account_id,
                                )
                                == client.account_id
                            ),
                            "has_more": bool(getattr(response, "hasMore", False)),
                            "tick_count": len(ticks),
                            "first_timestamp": (
                                getattr(first, "timestamp", None)
                                if first is not None
                                else None
                            ),
                            "first_tick": (
                                getattr(first, "tick", None)
                                if first is not None
                                else None
                            ),
                        }
                    )
            rows.append(
                {
                    "qore_symbol": symbol,
                    "provider_symbol": contract.symbol_name,
                    "execution_timestamp_ms": execution_ms,
                    "trade_side": trade_side,
                    "status": "PROBED",
                    "probes": probes,
                }
            )

        return {
            "schema": "qore.cibo.phase22.ctrader-tick-diagnostic.v1",
            "status": "COMPLETE",
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "endpoint_host": "demo.ctraderapi.com",
            "required_symbols": list(REQUIRED_SYMBOLS),
            "calibration_symbols_found": sorted(latest),
            "rows": rows,
            "broker_mutation_performed": False,
            "holdout_outcomes_used": False,
            "fundednext_touched": False,
            "vps_touched": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "productive_authority": False,
        }
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
