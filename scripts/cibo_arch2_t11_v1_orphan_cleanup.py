"""Bounded cleanup for orphaned positions from the cancelled T11 V1 run.

This command may mutate only cTrader DEMO positions/orders whose label belongs
exactly to INITIAL_RUN_ID / INITIAL_RUN_ATTEMPT from the immutable T11 execution
lineage.  It cannot touch the canonical replacement run or any other QORE
position.

The command reconciles before and after mutation and fails closed unless the
cancelled-run surface is fully neutralized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_arch2_t11_execution_claim import (
    INITIAL_RUN_ATTEMPT,
    INITIAL_RUN_ID,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
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

AUTHORIZATION_TOKEN = "CIBO_ARCH2_T11_V1_ORPHAN_CLEANUP_AUTHORIZED"
EXPECTED_ACCOUNT_FINGERPRINT_SHA256 = (
    "70d38b13a2afb1ada12883a486ddb39aa0626e4c262b69ee44410bb6531d6086"
)
_LABEL_PREFIX = "CIBOA2T11:"


def claimed_run_suffix() -> str:
    return f"{INITIAL_RUN_ID}-{INITIAL_RUN_ATTEMPT}"[-6:]


def label_belongs_to_cancelled_run(label: object) -> bool:
    return (
        isinstance(label, str)
        and label.startswith(_LABEL_PREFIX)
        and f":{claimed_run_suffix()}:" in label
    )


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
            f"T11 V1 cleanup provider request failed: {name}: {result.error}"
        )
    return result.value


def _hash(kind: str, value: int) -> str:
    return "sha256:" + hashlib.sha256(
        f"{kind}|{value}".encode("utf-8")
    ).hexdigest()


def _surface(response: object) -> tuple[list[object], list[object]]:
    positions = []
    for item in tuple(getattr(response, "position", ())):
        label = getattr(getattr(item, "tradeData", None), "label", None)
        if label_belongs_to_cancelled_run(label):
            positions.append(item)

    orders = []
    for item in tuple(getattr(response, "order", ())):
        label = getattr(getattr(item, "tradeData", None), "label", None)
        if label_belongs_to_cancelled_run(label):
            orders.append(item)
    return positions, orders


def run_cleanup() -> dict[str, Any]:
    if os.environ.get("QORE_CIBO_ARCH2_T11_V1_CLEANUP_AUTHORIZATION") != (
        AUTHORIZATION_TOKEN
    ):
        raise CiboCapitalManagementError(
            "T11 V1 cleanup authorization token missing"
        )

    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    try:
        binding = discover_free_account_binding(client)
        account_fingerprint = hashlib.sha256(
            binding.account.account_ref.encode("utf-8")
        ).hexdigest()
        if account_fingerprint != EXPECTED_ACCOUNT_FINGERPRINT_SHA256:
            raise CiboCapitalManagementError(
                "T11 V1 cleanup DEMO account fingerprint drift"
            )

        before = _request(
            client,
            "ProtoOAReconcileReq",
            {"ctidTraderAccountId": client.account_id},
            "t11-v1-cleanup-before",
        )
        positions, orders = _surface(before)

        cancelled_orders: list[str] = []
        for item in orders:
            order_id = getattr(item, "orderId", None)
            if type(order_id) is not int or order_id <= 0:
                raise CiboCapitalManagementError(
                    "T11 V1 cleanup target order identity invalid"
                )
            _request(
                client,
                "ProtoOACancelOrderReq",
                {
                    "ctidTraderAccountId": client.account_id,
                    "orderId": order_id,
                },
                f"t11-v1-cancel:{order_id}",
            )
            cancelled_orders.append(_hash("order", order_id))

        closed_positions: list[str] = []
        for item in positions:
            position_id = getattr(item, "positionId", None)
            trade_data = getattr(item, "tradeData", None)
            volume = getattr(trade_data, "volume", None)
            label = getattr(trade_data, "label", None)
            if (
                type(position_id) is not int
                or position_id <= 0
                or type(volume) is not int
                or volume <= 0
                or not label_belongs_to_cancelled_run(label)
            ):
                raise CiboCapitalManagementError(
                    "T11 V1 cleanup target position identity invalid"
                )
            _request(
                client,
                "ProtoOAClosePositionReq",
                {
                    "ctidTraderAccountId": client.account_id,
                    "positionId": position_id,
                    "volume": volume,
                },
                f"t11-v1-close:{position_id}",
            )
            closed_positions.append(_hash("position", position_id))

        after = _request(
            client,
            "ProtoOAReconcileReq",
            {"ctidTraderAccountId": client.account_id},
            "t11-v1-cleanup-after",
        )
        remaining_positions, remaining_orders = _surface(after)
        clean = not remaining_positions and not remaining_orders
        if not clean:
            raise CiboCapitalManagementError(
                "T11 V1 cleanup did not fully neutralize cancelled-run surface"
            )

        return {
            "schema": "qore.cibo.arch2.t11-v1-orphan-cleanup.v1",
            "initial_run_id": INITIAL_RUN_ID,
            "initial_run_attempt": INITIAL_RUN_ATTEMPT,
            "initial_run_suffix": claimed_run_suffix(),
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "account_fingerprint_sha256": account_fingerprint,
            "before_position_count": len(positions),
            "before_order_count": len(orders),
            "closed_position_refs_sha256": closed_positions,
            "cancelled_order_refs_sha256": cancelled_orders,
            "after_position_count": 0,
            "after_order_count": 0,
            "containment_clean": True,
            "mutation_scope": "INITIAL_T11_CANCELLED_RUN_LABELS_ONLY",
            "canonical_replacement_touched": False,
            "phase22_v2_consumed": False,
            "fundednext_touched": False,
            "vps_touched": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "canonical_ledger_modified": False,
            "productive_authority": False,
        }
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_cleanup()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "before_positions": report["before_position_count"],
                "before_orders": report["before_order_count"],
                "containment_clean": report["containment_clean"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
