"""Bounded DEMO-only cleanup for orphan Architect-2 T11 exposure.

The cancelled initial T11 provider experiment and its technically replaced run
are both scientifically inadmissible. This utility may mutate the broker only
to neutralize positions/orders carrying the exact CIBOA2T11 label suffixes for
those two known runs.

It must not touch:
- any non-T11 position/order;
- any unknown T11 run suffix;
- FundedNext, LIVE, VPS or real capital;
- Phase22 V2 or the canonical CIBO ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
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

AUTHORIZATION_TOKEN = "CIBO_ARCH2_T11_ORPHAN_CONTAINMENT_CLEANUP_AUTHORIZED"
_LABEL_PREFIX = "CIBOA2T11:"
_EXPECTED_ACCOUNT_FINGERPRINT_SHA256 = (
    "70d38b13a2afb1ada12883a486ddb39aa0626e4c262b69ee44410bb6531d6086"
)


def run_suffix(run_id: int, run_attempt: int) -> str:
    if run_id <= 0 or run_attempt <= 0:
        raise CiboCapitalManagementError("T11 cleanup run identity invalid")
    return f"{run_id}-{run_attempt}"[-6:]


INITIAL_SUFFIX = run_suffix(INITIAL_RUN_ID, INITIAL_RUN_ATTEMPT)
REPLACEMENT_SUFFIX = run_suffix(CANONICAL_RUN_ID, CANONICAL_RUN_ATTEMPT)
AUTHORIZED_SUFFIXES = (INITIAL_SUFFIX, REPLACEMENT_SUFFIX)


def authorized_t11_label(label: object) -> bool:
    if not isinstance(label, str) or not label.startswith(_LABEL_PREFIX):
        return False
    return any(f":{suffix}:" in label for suffix in AUTHORIZED_SUFFIXES)


def any_t11_label(label: object) -> bool:
    return isinstance(label, str) and label.startswith(_LABEL_PREFIX)


def _authorization() -> None:
    if os.environ.get("QORE_CIBO_ARCH2_T11_CONTAINMENT_AUTHORIZATION") != (
        AUTHORIZATION_TOKEN
    ):
        raise CiboCapitalManagementError(
            "T11 containment cleanup authorization token missing"
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
            f"T11 containment cleanup provider request failed: {name}: {result.error}"
        )
    return result.value


def _hash_identity(kind: str, value: object) -> str:
    if type(value) is not int or value <= 0:
        raise CiboCapitalManagementError(
            f"T11 containment cleanup invalid {kind} identity"
        )
    return "sha256:" + hashlib.sha256(f"{kind}|{value}".encode()).hexdigest()


def _snapshot(client: SpotwareCTraderOpenApiClient, *, message_id: str) -> object:
    return _request(
        client,
        "ProtoOAReconcileReq",
        {"ctidTraderAccountId": client.account_id},
        message_id,
    )


def _label(item: object) -> object:
    return getattr(getattr(item, "tradeData", None), "label", None)


def _matching_positions(response: object) -> tuple[object, ...]:
    return tuple(
        item
        for item in tuple(getattr(response, "position", ()))
        if authorized_t11_label(_label(item))
    )


def _matching_orders(response: object) -> tuple[object, ...]:
    return tuple(
        item
        for item in tuple(getattr(response, "order", ()))
        if authorized_t11_label(_label(item))
    )


def _unknown_t11_labels(response: object) -> tuple[str, ...]:
    labels = {
        str(label)
        for item in (
            *tuple(getattr(response, "position", ())),
            *tuple(getattr(response, "order", ())),
        )
        if any_t11_label(label := _label(item))
        and not authorized_t11_label(label)
    }
    return tuple(sorted(labels))


def build_cleanup_report() -> dict[str, Any]:
    _authorization()
    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    try:
        binding = discover_free_account_binding(client)
        account_fingerprint = hashlib.sha256(
            binding.account.account_ref.encode()
        ).hexdigest()
        if account_fingerprint != _EXPECTED_ACCOUNT_FINGERPRINT_SHA256:
            raise CiboCapitalManagementError(
                "T11 containment cleanup DEMO account drift"
            )

        before = _snapshot(client, message_id="t11-containment-before")
        unknown_before = _unknown_t11_labels(before)
        if unknown_before:
            raise CiboCapitalManagementError(
                "T11 containment cleanup found unknown T11 run labels"
            )

        positions = _matching_positions(before)
        orders = _matching_orders(before)

        cancelled_orders: list[dict[str, str]] = []
        for order in orders:
            order_id = getattr(order, "orderId", None)
            _request(
                client,
                "ProtoOACancelOrderReq",
                {
                    "ctidTraderAccountId": client.account_id,
                    "orderId": order_id,
                },
                f"t11-containment-cancel:{order_id}",
            )
            cancelled_orders.append(
                {
                    "label": str(_label(order)),
                    "order_ref_sha256": _hash_identity("order", order_id),
                }
            )

        closed_positions: list[dict[str, str]] = []
        for position in positions:
            trade_data = getattr(position, "tradeData", None)
            position_id = getattr(position, "positionId", None)
            volume = getattr(trade_data, "volume", None)
            if (
                type(position_id) is not int
                or position_id <= 0
                or type(volume) is not int
                or volume <= 0
            ):
                raise CiboCapitalManagementError(
                    "T11 containment cleanup position geometry invalid"
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
            closed_positions.append(
                {
                    "label": str(_label(position)),
                    "position_ref_sha256": _hash_identity(
                        "position",
                        position_id,
                    ),
                }
            )

        terminal: object | None = None
        for attempt in range(30):
            terminal = _snapshot(
                client,
                message_id=f"t11-containment-terminal:{attempt}",
            )
            if (
                not _matching_positions(terminal)
                and not _matching_orders(terminal)
            ):
                break
            time.sleep(0.25)
        if terminal is None:
            raise CiboCapitalManagementError(
                "T11 containment cleanup terminal snapshot missing"
            )

        remaining_positions = _matching_positions(terminal)
        remaining_orders = _matching_orders(terminal)
        unknown_after = _unknown_t11_labels(terminal)
        clean = (
            not remaining_positions
            and not remaining_orders
            and not unknown_after
        )

        return {
            "schema": "qore.cibo.arch2.t11-orphan-containment-cleanup.v1",
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "account_fingerprint_sha256": account_fingerprint,
            "authorized_run_ids": [INITIAL_RUN_ID, CANONICAL_RUN_ID],
            "authorized_suffixes": list(AUTHORIZED_SUFFIXES),
            "before_position_count": len(positions),
            "before_order_count": len(orders),
            "closed_position_count": len(closed_positions),
            "cancelled_order_count": len(cancelled_orders),
            "closed_positions": closed_positions,
            "cancelled_orders": cancelled_orders,
            "remaining_position_count": len(remaining_positions),
            "remaining_order_count": len(remaining_orders),
            "unknown_t11_labels": list(unknown_after),
            "containment_clean": clean,
            "broker_mutation_performed": bool(positions or orders),
            "mutation_scope": (
                "CTRADER_DEMO_KNOWN_T11_ORPHAN_LABELS_ONLY"
            ),
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
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = build_cleanup_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "containment_clean": report["containment_clean"],
                "closed_positions": report["closed_position_count"],
                "cancelled_orders": report["cancelled_order_count"],
                "remaining_positions": report["remaining_position_count"],
                "remaining_orders": report["remaining_order_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
