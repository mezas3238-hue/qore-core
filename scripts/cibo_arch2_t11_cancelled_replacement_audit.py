"""Read-only audit for cancelled T11 replacement-run provider exposure.

The first cancelled V1 run has already been neutralized separately. This audit
checks only the later cancelled replacement lineage:
- 36946792349 / attempt 1, which reached broker mutation;
- 36947685956 / attempt 1, which was cancelled before a terminal artifact.

No broker mutation is permitted here. Raw provider ids are hashed before output.
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

SECONDARY_CANCELLED_RUN_ID = 36947685956
SECONDARY_CANCELLED_RUN_ATTEMPT = 1
_LABEL_PREFIX = "CIBOA2T11:"


def _suffix(run_id: int, attempt: int) -> str:
    return f"{run_id}-{attempt}"[-6:]


AUDITED_RUNS = (
    (CANONICAL_RUN_ID, CANONICAL_RUN_ATTEMPT),
    (SECONDARY_CANCELLED_RUN_ID, SECONDARY_CANCELLED_RUN_ATTEMPT),
)
AUDITED_SUFFIXES = tuple(_suffix(run_id, attempt) for run_id, attempt in AUDITED_RUNS)


def label_run_suffix(label: object) -> str | None:
    if not isinstance(label, str) or not label.startswith(_LABEL_PREFIX):
        return None
    matches = tuple(suffix for suffix in AUDITED_SUFFIXES if f":{suffix}:" in label)
    if len(matches) > 1:
        raise CiboCapitalManagementError(
            "T11 cancelled replacement label matches multiple run suffixes"
        )
    return matches[0] if matches else None


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
            f"T11 replacement containment audit failed: {name}: {result.error}"
        )
    return result.value


def _hash(kind: str, value: object) -> str:
    if type(value) is not int or value <= 0:
        raise CiboCapitalManagementError(
            f"T11 replacement containment invalid {kind} identity"
        )
    return "sha256:" + hashlib.sha256(f"{kind}|{value}".encode()).hexdigest()


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
            "cibo-arch2-t11-cancelled-replacement-audit",
        )

        position_rows: dict[str, list[dict[str, str]]] = {
            suffix: [] for suffix in AUDITED_SUFFIXES
        }
        order_rows: dict[str, list[dict[str, str]]] = {
            suffix: [] for suffix in AUDITED_SUFFIXES
        }

        for item in tuple(getattr(response, "position", ())):
            trade_data = getattr(item, "tradeData", None)
            label = getattr(trade_data, "label", None)
            suffix = label_run_suffix(label)
            if suffix is None:
                continue
            position_rows[suffix].append(
                {
                    "label": str(label),
                    "position_ref_sha256": _hash(
                        "position",
                        getattr(item, "positionId", None),
                    ),
                }
            )

        for item in tuple(getattr(response, "order", ())):
            trade_data = getattr(item, "tradeData", None)
            label = getattr(trade_data, "label", None)
            suffix = label_run_suffix(label)
            if suffix is None:
                continue
            order_rows[suffix].append(
                {
                    "label": str(label),
                    "order_ref_sha256": _hash(
                        "order",
                        getattr(item, "orderId", None),
                    ),
                }
            )

        run_rows = {
            suffix: {
                "position_count": len(position_rows[suffix]),
                "order_count": len(order_rows[suffix]),
                "positions": position_rows[suffix],
                "orders": order_rows[suffix],
            }
            for suffix in AUDITED_SUFFIXES
        }
        total_positions = sum(len(rows) for rows in position_rows.values())
        total_orders = sum(len(rows) for rows in order_rows.values())
        return {
            "schema": "qore.cibo.arch2.t11-cancelled-replacement-audit.v1",
            "audited_runs": [
                {
                    "run_id": run_id,
                    "run_attempt": attempt,
                    "run_suffix": _suffix(run_id, attempt),
                }
                for run_id, attempt in AUDITED_RUNS
            ],
            "provider_key": "ctrader-demo",
            "environment": "demo",
            "account_fingerprint_sha256": hashlib.sha256(
                binding.account.account_ref.encode()
            ).hexdigest(),
            "run_surfaces": run_rows,
            "open_position_count": total_positions,
            "open_order_count": total_orders,
            "containment_clean": total_positions == 0 and total_orders == 0,
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
                "open_positions": report["open_position_count"],
                "open_orders": report["open_order_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
