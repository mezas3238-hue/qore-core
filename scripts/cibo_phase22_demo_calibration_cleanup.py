"""Fail-closed cleanup for Phase22 cTrader DEMO calibration objects.

Only positions/orders carrying the exact QORE:CIBO-CAL: label prefix are
eligible. The cTrader client itself rejects LIVE/ambiguous accounts. This
script never touches FundedNext, VPS, unlabeled orders, or unrelated positions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_demo_calibration_contract import (
    CALIBRATION_LABEL_PREFIX,
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
            f"Phase22 calibration cleanup request failed: {name}: {result.error}"
        )
    return result.value


def _label(value: object) -> str | None:
    trade_data = getattr(value, "tradeData", None)
    label = getattr(trade_data, "label", None) if trade_data is not None else None
    if isinstance(label, str) and label:
        return label
    direct = getattr(value, "label", None)
    return direct if isinstance(direct, str) and direct else None


def _hash_id(value: int) -> str:
    return "sha256:" + hashlib.sha256(str(value).encode()).hexdigest()


def _snapshot(
    client: SpotwareCTraderOpenApiClient,
    *,
    message_id: str,
) -> tuple[tuple[object, ...], tuple[object, ...]]:
    payload = _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        message_id,
    )
    positions = tuple(
        item
        for item in tuple(getattr(payload, "position", ()))
        if (_label(item) or "").startswith(CALIBRATION_LABEL_PREFIX)
    )
    orders = tuple(
        item
        for item in tuple(getattr(payload, "order", ()))
        if (_label(item) or "").startswith(CALIBRATION_LABEL_PREFIX)
    )
    return positions, orders


def cleanup() -> dict[str, object]:
    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    cancelled: list[str] = []
    closed: list[str] = []
    try:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise CiboCapitalManagementError(
                f"Phase22 cleanup DEMO authentication failed: {connected.error}"
            )
        binding = discover_free_account_binding(client)
        if binding.configuration.endpoint.host != "demo.ctraderapi.com":
            raise CiboCapitalManagementError("Phase22 cleanup endpoint is not DEMO")

        positions, orders = _snapshot(
            client,
            message_id="phase22-cal-cleanup-initial",
        )

        for order in orders:
            order_id = getattr(order, "orderId", None)
            if type(order_id) is not int or order_id <= 0:
                raise CiboCapitalManagementError(
                    "Phase22 cleanup calibration order id invalid"
                )
            _request(
                client,
                "ProtoOACancelOrderReq",
                {
                    "ctidTraderAccountId": client.account_id,
                    "orderId": order_id,
                },
                f"phase22-cal-cleanup-cancel:{order_id}",
            )
            cancelled.append(_hash_id(order_id))

        # Reconcile after cancellation because a MARKET order may have filled
        # while cancellation was being attempted.
        positions, _orders_after_cancel = _snapshot(
            client,
            message_id="phase22-cal-cleanup-after-cancel",
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
                    "Phase22 cleanup calibration position identity/volume invalid"
                )
            _request(
                client,
                "ProtoOAClosePositionReq",
                {
                    "ctidTraderAccountId": client.account_id,
                    "positionId": position_id,
                    "volume": volume,
                },
                f"phase22-cal-cleanup-close:{position_id}",
            )
            closed.append(_hash_id(position_id))

        time.sleep(1.0)
        remaining_positions, remaining_orders = _snapshot(
            client,
            message_id="phase22-cal-cleanup-terminal",
        )
        if remaining_positions or remaining_orders:
            raise CiboCapitalManagementError(
                "Phase22 calibration cleanup left labeled broker state"
            )

        return {
            "schema": "qore.cibo.phase22.demo-calibration-cleanup.v1",
            "status": "CLEAN",
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "endpoint_host": "demo.ctraderapi.com",
            "initial_labeled_positions": len(positions),
            "initial_labeled_orders": len(orders),
            "cancelled_order_refs_sha256": cancelled,
            "closed_position_refs_sha256": closed,
            "remaining_labeled_positions": 0,
            "remaining_labeled_orders": 0,
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
    payload = cleanup()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
