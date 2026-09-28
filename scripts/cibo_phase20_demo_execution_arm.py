"""Fail-closed read-only arm for the CIBO Phase20D cTrader DEMO collector.

The arm authenticates the exact DEMO account, proves a clean initial broker
state, discovers the six CIBO contracts, and writes only local runtime binding
metadata. It never submits, amends, cancels, or closes broker orders/positions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.ctrader_demo_free_binding import (  # type: ignore[import-untyped]
    binding_fingerprint,
    discover_free_account_binding,
)
from qore.infrastructure.ctrader_open_api_client import (  # type: ignore[import-untyped]
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

_REQUIRED_SYMBOLS = (
    "AUDJPY",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "XAUUSD",
)
_SOURCE_CONTRACT_SIZE_UNITS = {
    "AUDJPY": Decimal("100000"),
    "EURUSD": Decimal("100000"),
    "GBPJPY": Decimal("100000"),
    "GBPUSD": Decimal("100000"),
    "NAS100": Decimal("10"),
    "XAUUSD": Decimal("100"),
}
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise RuntimeError(f"missing required environment input: {name}")


def _credentials() -> CTraderOpenApiCredentials:
    return CTraderOpenApiCredentials(
        client_id=_required_env(
            "QORE_CTRADER_CLIENT_ID",
            "QORE_CTRADER_DEMO_CLIENT_ID",
        ),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET",
            "QORE_CTRADER_DEMO_CLIENT_SECRET",
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN",
            "QORE_CTRADER_DEMO_ACCESS_TOKEN",
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN",
            "QORE_CTRADER_DEMO_REFRESH_TOKEN",
        ),
        ctid_trader_account_id=int(
            _required_env(
                "QORE_CTRADER_DEMO_ACCOUNT_ID",
                "QORE_CTRADER_ACCOUNT_ID",
            )
        ),
    )


def _git_sha() -> str:
    value = _required_env("GITHUB_SHA").strip()
    if _SHA1_RE.fullmatch(value) is None:
        raise RuntimeError("GITHUB_SHA must be lowercase 40-hex")
    return value


def _request(client: SpotwareCTraderOpenApiClient, name: str) -> object:
    result = client.request(
        name,
        {"ctidTraderAccountId": client.account_id},
        client_msg_id=f"qore-cibo-phase20-arm:{name}",
        timeout_seconds=10.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(f"cTrader DEMO arm read failed: {name}")
    return result.value


def _assert_clean_initial_broker_state(
    client: SpotwareCTraderOpenApiClient,
) -> None:
    reconciled = _request(client, "ProtoOAReconcileReq")
    positions = tuple(getattr(reconciled, "position", ()))
    orders = tuple(getattr(reconciled, "order", ()))
    if positions or orders:
        raise RuntimeError(
            "CIBO Phase20D initial DEMO arm requires zero open positions "
            "and zero pending orders"
        )


def _binding_payload(binding: object) -> dict[str, object]:
    contracts = getattr(binding, "contracts")
    by_symbol = {item.qore_symbol: item for item in contracts}
    if tuple(sorted(by_symbol)) != _REQUIRED_SYMBOLS:
        raise RuntimeError("CIBO Phase20D DEMO binding symbol-set drift")

    rows: list[dict[str, object]] = []
    for qore_symbol in _REQUIRED_SYMBOLS:
        item = by_symbol[qore_symbol]
        source_contract = _SOURCE_CONTRACT_SIZE_UNITS[qore_symbol]
        if source_contract <= 0:
            raise RuntimeError("source contract size must be positive")
        rows.append(
            {
                "qore_symbol": qore_symbol,
                "provider_symbol": item.symbol_name,
                "symbol_id": item.symbol_id,
                "digits": item.digits,
                "source_contract_size_units": format(source_contract, "f"),
                "ctrader_lot_size_units": format(
                    item.lot_size_units,
                    "f",
                ),
                "min_volume_units": item.min_volume_units,
                "max_volume_units": item.max_volume_units,
                "step_volume_units": item.step_volume_units,
            }
        )
    return {
        "schema": "qore.cibo.phase20d.ctrader_demo_runtime_binding.v1",
        "contracts": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    args = parser.parse_args()

    armed_at = datetime.now(UTC)
    client = SpotwareCTraderOpenApiClient(credentials=_credentials())
    try:
        binding = discover_free_account_binding(client, bound_at=armed_at)
        _assert_clean_initial_broker_state(client)
        runtime_binding = _binding_payload(binding)

        args.binding_output.parent.mkdir(parents=True, exist_ok=True)
        args.binding_output.write_text(
            json.dumps(runtime_binding, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        report = {
            "schema": "qore.cibo.phase20d.demo_execution_arm.v1",
            "status": "ARMED_NOT_ACTIVATED",
            "git_sha": _git_sha(),
            "armed_at": armed_at.isoformat(),
            "environment": "demo",
            "account_ref_sha256_exposed": False,
            "binding_fingerprint": binding_fingerprint(binding),
            "required_qore_symbols": list(_REQUIRED_SYMBOLS),
            "initial_open_positions": 0,
            "initial_pending_orders": 0,
            "broker_mutation_performed": False,
            "execution_authorized": False,
            "activation_gate": (
                "CIBO_PHASE20D_DEMO_EXECUTION_AUTHORIZED"
            ),
            "phase20d_population_started": False,
            "governance": {
                "fundednext_touched": False,
                "vps_touched": False,
                "live_authorized": False,
                "real_capital_authorized": False,
                "merge_authorized": False,
            },
        }
        args.report_output.parent.mkdir(parents=True, exist_ok=True)
        args.report_output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, sort_keys=True))
    finally:
        client.close()


if __name__ == "__main__":
    main()
