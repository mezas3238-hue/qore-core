"""Read-only containment audit for the burned T11 V1 execution claim.

Run 36945327912 was cancelled after broker mutation may have begun.  This audit
does not place, amend, cancel, or close anything.  It reconciles the cTrader
DEMO account and proves whether any open position/order still carries the exact
label suffix of that claimed run.

Raw provider order/position identifiers are not emitted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_arch2_t11_execution_claim import (
    RUN_ATTEMPT,
    RUN_ID,
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

_LABEL_PREFIX = "CIBOA2T11:"


def claimed_run_suffix() -> str:
    return f"{RUN_ID}-{RUN_ATTEMPT}"[-6:]


def label_belongs_to_claimed_run(label: object) -> bool:
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
            f"T11 containment audit provider request failed: {result.error}"
        )
    return result.value


def _hashed_identity(kind: str, value: object) -> str:
    if type(value) is not int or value <= 0:
        raise CiboCapitalManagementError(
            f"T11 containment audit invalid {kind} identity"
        )
    return "sha256:" + hashlib.sha256(
        f"{kind}|{value}".encode("utf-8")
    ).hexdigest()


def build_report() -> dict[str, Any]:
    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    try:
        binding = discover_free_account_binding(client)
        response = _request(
            client,
            "ProtoOAReconcileReq",
            {"ctidTraderAccountId": client.account_id},
            "cibo-arch2-t11-v1-containment-audit",
        )

        positions: list[dict[str, str]] = []
        for item in tuple(getattr(response, "position", ())):
            trade_data = getattr(item, "tradeData", None)
            label = getattr(trade_data, "label", None)
            if not label_belongs_to_claimed_run(label):
                continue
            positions.append(
                {
                    "label": str(label),
                    "position_ref_sha256": _hashed_identity(
                        "position",
                        getattr(item, "positionId", None),
                    ),
                }
            )

        orders: list[dict[str, str]] = []
        for item in tuple(getattr(response, "order", ())):
            trade_data = getattr(item, "tradeData", None)
            label = getattr(trade_data, "label", None)
            if not label_belongs_to_claimed_run(label):
                continue
            orders.append(
                {
                    "label": str(label),
                    "order_ref_sha256": _hashed_identity(
                        "order",
                        getattr(item, "orderId", None),
                    ),
                }
            )

        clean = not positions and not orders
        return {
            "schema": "qore.cibo.arch2.t11-v1-containment-audit.v1",
            "claimed_run_id": RUN_ID,
            "claimed_run_attempt": RUN_ATTEMPT,
            "claimed_run_suffix": claimed_run_suffix(),
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "account_fingerprint_sha256": hashlib.sha256(
                binding.account.account_ref.encode("utf-8")
            ).hexdigest(),
            "open_claimed_run_position_count": len(positions),
            "open_claimed_run_order_count": len(orders),
            "open_positions": positions,
            "open_orders": orders,
            "containment_clean": clean,
            "broker_mutation_performed": False,
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

    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "containment_clean": report["containment_clean"],
                "open_positions": report["open_claimed_run_position_count"],
                "open_orders": report["open_claimed_run_order_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
