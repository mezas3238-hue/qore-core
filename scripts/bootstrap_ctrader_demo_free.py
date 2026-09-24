from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.ctrader_demo_allocation_only import (
    equal_active_trader_allocations,
)
from qore.infrastructure.ctrader_demo_free_binding import (
    binding_fingerprint,
    discover_free_account_binding,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)

ROOT = Path(r"C:\QORE_CTRADER_DEMO_FREE")
STATE = ROOT / "var" / "ctrader_demo_free"
ARTIFACT = STATE / "binding.json"
FAILURE = STATE / "binding_failed.json"

# Frozen QORE strategy contract semantics.  These are strategy units, not
# broker/account observations, so bootstrap never consults MT5 or FundedNext.
SOURCE_CONTRACTS: dict[str, tuple[str, Decimal]] = {
    "XAUUSD": ("XAUUSD", Decimal("100")),
    "EURUSD": ("EURUSD", Decimal("100000")),
    "GBPUSD": ("GBPUSD", Decimal("100000")),
    "GBPJPY": ("GBPJPY", Decimal("100000")),
    "AUDJPY": ("AUDJPY", Decimal("100000")),
    "NAS100": ("NDX100", Decimal("10")),
}


def required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"missing required environment input: {name}")
    return value


def source_contract_sizes() -> dict[str, tuple[str, Decimal]]:
    return dict(SOURCE_CONTRACTS)


def main() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    account_id = int(required_env("QORE_CTRADER_DEMO_ACCOUNT_ID"))
    credentials = CTraderOpenApiCredentials(
        client_id=required_env("QORE_CTRADER_CLIENT_ID"),
        client_secret=required_env("QORE_CTRADER_CLIENT_SECRET"),
        access_token=required_env("QORE_CTRADER_ACCESS_TOKEN"),
        refresh_token=required_env("QORE_CTRADER_REFRESH_TOKEN"),
        ctid_trader_account_id=account_id,
    )
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        binding = discover_free_account_binding(client)
        if binding.account.account_ref != str(account_id):
            raise RuntimeError("authenticated DEMO account mismatch")
        source = source_contract_sizes()
        contract_rows: list[dict[str, object]] = []
        for contract in binding.contracts:
            source_symbol, source_size = source[contract.qore_symbol]
            contract_rows.append(
                {
                    "qore_symbol": contract.qore_symbol,
                    "source_symbol": source_symbol,
                    "ctrader_symbol": contract.symbol_name,
                    "digits": contract.digits,
                    "source_contract_size_units": format(source_size, "f"),
                    "lot_size_units": format(contract.lot_size_units, "f"),
                    "source_to_ctrader_lot_ratio": format(
                        source_size / contract.lot_size_units, "f"
                    ),
                    "min_volume_cents": contract.min_volume_units,
                    "max_volume_cents": contract.max_volume_units,
                    "step_volume_cents": contract.step_volume_units,
                }
            )
        book = equal_active_trader_allocations(binding.balance)
        account_hash = hashlib.sha256(str(account_id).encode("utf-8")).hexdigest()
        payload = {
            "schema": "qore.ctrader-demo.free-account-binding.v1",
            "environment": "DEMO",
            "provider": "ctrader",
            "endpoint": "demo.ctraderapi.com:5035",
            "account_fingerprint": account_hash,
            "binding_fingerprint": binding_fingerprint(binding),
            "balance": format(binding.balance, "f"),
            "money_digits": binding.money_digits,
            "risk_role": "CAPITAL_ALLOCATOR_ONLY",
            "cibo_role": "SIZING_AND_POSITION_INTELLIGENCE_SOVEREIGN",
            "cross_trader_risk_reduction": False,
            "contracts": contract_rows,
            "allocations": {
                trader.value: format(capital, "f") for trader, capital in book.allocations.items()
            },
            "bound_at": binding.bound_at.astimezone(UTC).isoformat(),
        }
        ARTIFACT.write_text(
            json.dumps(payload, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        FAILURE.unlink(missing_ok=True)
        print("CTRADER_DEMO_FREE_BINDING_OK")
        print(f"balance={payload['balance']}")
        print(f"traders={len(payload['allocations'])}")
        print(f"symbols={len(contract_rows)}")
        return 0
    except Exception as error:
        failure = {
            "schema": "qore.ctrader-demo.free-account-binding-failure.v1",
            "failed_closed": True,
            "reason": str(error),
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        FAILURE.write_text(
            json.dumps(failure, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"CTRADER_DEMO_FREE_BINDING_FAILED: {error}")
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
