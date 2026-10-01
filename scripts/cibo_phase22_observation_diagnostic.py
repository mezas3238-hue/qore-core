"""Read-only diagnostic of the exact empirical-slippage observation path."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ctrader_demo_empirical_slippage import (
    _account_entry_deal,
    _deal_observation,
    _market_entry_order,
)
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


def _label(order: object | None) -> str | None:
    if order is None:
        return None
    trade_data = getattr(order, "tradeData", None)
    value = getattr(trade_data, "label", None) if trade_data is not None else None
    if isinstance(value, str) and value:
        return value
    value = getattr(order, "label", None)
    return value if isinstance(value, str) and value else None


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
        observed = datetime.now(UTC)
        binding = discover_free_account_binding(client, bound_at=observed)
        contracts = {item.symbol_id: item for item in binding.contracts}
        start = observed - timedelta(days=365)
        deals_res = _request(
            client,
            "ProtoOADealListReq",
            {
                "ctidTraderAccountId": client.account_id,
                "fromTimestamp": int(start.timestamp() * 1000),
                "toTimestamp": int(observed.timestamp() * 1000),
                "maxRows": 5000,
            },
            "phase22-observation-diag-deals",
        )
        orders_res = _request(
            client,
            "ProtoOAOrderListReq",
            {
                "ctidTraderAccountId": client.account_id,
                "fromTimestamp": int(start.timestamp() * 1000),
                "toTimestamp": int(observed.timestamp() * 1000),
            },
            "phase22-observation-diag-orders",
        )
        orders = {
            int(item.orderId): item
            for item in tuple(getattr(orders_res, "order", ()))
            if type(getattr(item, "orderId", None)) is int
            and item.orderId > 0
        }

        latest: dict[str, Any] = {}
        for raw in tuple(getattr(deals_res, "deal", ())):
            deal = cast(Any, raw)
            if not _account_entry_deal(deal, contracts):
                continue
            order = orders.get(int(deal.orderId))
            if not _market_entry_order(order):
                continue
            label = _label(order)
            if label is None or not label.startswith(CALIBRATION_LABEL_PREFIX):
                continue
            contract = contracts[int(deal.symbolId)]
            current = latest.get(contract.qore_symbol)
            if (
                current is None
                or int(current.executionTimestamp)
                < int(deal.executionTimestamp)
            ):
                latest[contract.qore_symbol] = deal

        rows: list[dict[str, object]] = []
        for symbol in REQUIRED_SYMBOLS:
            deal = latest.get(symbol)
            if deal is None:
                rows.append(
                    {
                        "qore_symbol": symbol,
                        "status": "NO_DEAL",
                    }
                )
                continue
            contract = next(
                item for item in binding.contracts
                if item.qore_symbol == symbol
            )
            try:
                observation = _deal_observation(
                    client=client,
                    account_id=client.account_id,
                    contract=contract,
                    deal=deal,
                )
            except CiboCapitalManagementError as error:
                rows.append(
                    {
                        "qore_symbol": symbol,
                        "status": "OBSERVATION_ERROR",
                        "error_type": type(error).__name__,
                        "error": str(error),
                        "deal_id_sha256_only": True,
                    }
                )
                continue
            rows.append(
                {
                    "qore_symbol": symbol,
                    "status": "OBSERVATION_OK",
                    "trade_side": observation.trade_side,
                    "quote_at": observation.quote_at.isoformat(),
                    "execution_at": observation.execution_at.isoformat(),
                    "quote_price": format(observation.quote_price, "f"),
                    "fill_price": format(observation.fill_price, "f"),
                    "signed_slippage_bps": format(
                        observation.signed_slippage_bps,
                        "f",
                    ),
                    "quote_age_ms": observation.quote_age_ms,
                    "execution_latency_ms": observation.execution_latency_ms,
                }
            )

        return {
            "schema": "qore.cibo.phase22.observation-diagnostic.v1",
            "status": "COMPLETE",
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "rows": rows,
            "ok_count": sum(
                row["status"] == "OBSERVATION_OK" for row in rows
            ),
            "error_count": sum(
                row["status"] == "OBSERVATION_ERROR" for row in rows
            ),
            "broker_mutation_performed": False,
            "holdout_outcomes_used": False,
            "fundednext_touched": False,
            "vps_touched": False,
            "productive_authority": False,
        }
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
