"""Read-only global containment audit for all Architect-2 T11 DEMO labels.

This audit is intentionally broader than the V1 audit. It verifies that no
open cTrader DEMO order or position remains under the CIBOA2T11 namespace
before a new explicitly versioned research cycle may begin.

It emits only hashed provider identities and performs zero broker mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_arch2_t11_execution_claim import (
    CANONICAL_RUN_ATTEMPT,
    CANONICAL_RUN_ID,
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

_LABEL_PREFIX = "CIBOA2T11:"


def _suffix(run_id: int, attempt: int) -> str:
    return f"{run_id}-{attempt}"[-6:]


INITIAL_SUFFIX = _suffix(INITIAL_RUN_ID, INITIAL_RUN_ATTEMPT)
CANONICAL_SUFFIX = _suffix(CANONICAL_RUN_ID, CANONICAL_RUN_ATTEMPT)


def t11_label(label: object) -> bool:
    return isinstance(label, str) and label.startswith(_LABEL_PREFIX)


def classify_label(label: str) -> str:
    if f":{INITIAL_SUFFIX}:" in label:
        return "INITIAL_CANCELLED_RUN"
    if f":{CANONICAL_SUFFIX}:" in label:
        return "CONTAMINATED_REPLACEMENT_RUN"
    return "OTHER_T11_LABEL"


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
            f"T11 global containment audit request failed: {result.error}"
        )
    return result.value


def _hashed(kind: str, value: object) -> str:
    if type(value) is not int or value <= 0:
        raise CiboCapitalManagementError(
            f"T11 global containment invalid {kind} identity"
        )
    return "sha256:" + hashlib.sha256(
        f"{kind}|{value}".encode()
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
            "cibo-arch2-t11-global-containment-audit",
        )

        positions: list[dict[str, str]] = []
        for item in tuple(getattr(response, "position", ())):
            trade_data = getattr(item, "tradeData", None)
            label = getattr(trade_data, "label", None)
            if not t11_label(label):
                continue
            assert isinstance(label, str)
            positions.append(
                {
                    "label": label,
                    "lineage": classify_label(label),
                    "position_ref_sha256": _hashed(
                        "position",
                        getattr(item, "positionId", None),
                    ),
                }
            )

        orders: list[dict[str, str]] = []
        for item in tuple(getattr(response, "order", ())):
            trade_data = getattr(item, "tradeData", None)
            label = getattr(trade_data, "label", None)
            if not t11_label(label):
                continue
            assert isinstance(label, str)
            orders.append(
                {
                    "label": label,
                    "lineage": classify_label(label),
                    "order_ref_sha256": _hashed(
                        "order",
                        getattr(item, "orderId", None),
                    ),
                }
            )

        clean = not positions and not orders
        return {
            "schema": "qore.cibo.arch2.t11-global-containment-audit.v1",
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "account_fingerprint_sha256": hashlib.sha256(
                binding.account.account_ref.encode()
            ).hexdigest(),
            "initial_run_id": INITIAL_RUN_ID,
            "initial_run_suffix": INITIAL_SUFFIX,
            "contaminated_replacement_run_id": CANONICAL_RUN_ID,
            "contaminated_replacement_suffix": CANONICAL_SUFFIX,
            "open_t11_position_count": len(positions),
            "open_t11_order_count": len(orders),
            "open_positions": positions,
            "open_orders": orders,
            "containment_clean": clean,
            "new_versioned_cycle_allowed": clean,
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
                "open_positions": report["open_t11_position_count"],
                "open_orders": report["open_t11_order_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
