from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.fundednext_mt5 import FundedNextMt5OrderPlan
from qore.infrastructure.fundednext_mt5_transport import (
    MetaTrader5FundedNextTransport,
)
from qore.infrastructure.fundednext_operational import resolve_account_provider_symbol
from qore.infrastructure.order_intent import OrderSide, OrderType

mt5 = importlib.import_module("MetaTrader5")

RETAINED_SYMBOLS = ("AUDJPY", "GBPUSD", "GBPJPY")
EXPECTED_SERVER = "FundedNext-Server"


def _git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    sha = result.stdout.strip().lower()
    if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha):
        raise RuntimeError("git_head_is_not_full_sha")
    return sha


def _fail(reason: str, *, details: dict[str, Any] | None = None) -> int:
    payload = {
        "schema": "qore.fundednext.mt5-shadow-order-check.v1",
        "probe": "fundednext_mt5_shadow_order_check",
        "mode": "SHADOW_ORDER_CHECK_NO_SEND",
        "ok": False,
        "reason": reason,
        "details": details or {},
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "safety": {"order_check_called": True, "order_send_called": False},
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 2


def _plan_for_symbol(
    transport: MetaTrader5FundedNextTransport,
    *,
    qore_symbol: str,
    provider_symbol: str,
    sequence: int,
) -> FundedNextMt5OrderPlan:
    spec = transport.symbol_info(provider_symbol)
    if spec is None:
        raise RuntimeError(f"symbol_info_unavailable:{provider_symbol}")
    minimum_points = max(
        spec.minimum_stop_distance_points,
        spec.freeze_level_points,
        Decimal("10"),
    )
    distance = (minimum_points + Decimal("50")) * spec.point
    entry = spec.ask
    volume = spec.minimum_volume
    return FundedNextMt5OrderPlan(
        client_order_id=f"qore-shadow-{sequence:02d}-{qore_symbol.lower()}",
        qore_symbol=qore_symbol,
        provider_symbol=provider_symbol,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        volume=volume,
        effective_entry=entry,
        limit_price=None,
        stop_loss=entry - distance,
        take_profit=entry + distance,
        margin_required=volume * spec.margin_per_volume,
        planned_at=datetime.now(UTC),
    )


def main() -> int:
    git_sha = _git_sha()
    if not mt5.initialize():
        return _fail("mt5_initialize_failed", details={"last_error": mt5.last_error()})
    try:
        account = mt5.account_info()
        if account is None:
            return _fail("account_info_unavailable", details={"last_error": mt5.last_error()})
        server = str(account.server)
        if server != EXPECTED_SERVER:
            return _fail(
                "server_mismatch",
                details={"expected_server": EXPECTED_SERVER, "actual_server": server},
            )
        symbols = mt5.symbols_get()
        if symbols is None:
            return _fail("symbols_unavailable", details={"last_error": mt5.last_error()})
        available = tuple(str(item.name) for item in symbols if getattr(item, "name", ""))
        transport = MetaTrader5FundedNextTransport(
            api=mt5,
            qore_account_ref="fundednext-stellar-instant-production",
            expected_login=int(account.login),
            expected_server=EXPECTED_SERVER,
        )
        checks: list[dict[str, object]] = []
        for sequence, qore_symbol in enumerate(RETAINED_SYMBOLS, start=1):
            provider_symbol = resolve_account_provider_symbol(qore_symbol, available)
            plan = _plan_for_symbol(
                transport,
                qore_symbol=qore_symbol,
                provider_symbol=provider_symbol,
                sequence=sequence,
            )
            evidence = transport.check_order(plan)
            checks.append(
                {
                    "qore_symbol": qore_symbol,
                    "provider_symbol": provider_symbol,
                    "volume": str(plan.volume),
                    "retcode": evidence.retcode,
                    "comment": evidence.comment,
                    "ok": evidence.ok,
                    "checked_at": evidence.checked_at.isoformat(),
                }
            )
        identity_material = (
            f"{server}|{account.company}|{account.currency}|{int(account.leverage)}"
        )
        fingerprint = hashlib.sha256(identity_material.encode("utf-8")).hexdigest()
        ok = all(bool(item["ok"]) for item in checks)
        payload = {
            "schema": "qore.fundednext.mt5-shadow-order-check.v1",
            "probe": "fundednext_mt5_shadow_order_check",
            "mode": "SHADOW_ORDER_CHECK_NO_SEND",
            "ok": ok,
            "git_sha": git_sha,
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "account": {
                "server": server,
                "company": str(account.company),
                "currency": str(account.currency),
                "leverage": int(account.leverage),
                "identity_fingerprint": fingerprint,
            },
            "checks": checks,
            "safety": {
                "order_check_called": True,
                "order_send_called": False,
                "provider_mutation_requested": False,
            },
        }
        out_dir = Path("artifacts")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "fundednext_mt5_shadow_probe.json"
        out_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        print(f"ARTIFACT={out_path.resolve()}")
        return 0 if ok else 2
    except Exception as exc:
        return _fail(
            "probe_exception",
            details={"type": type(exc).__name__, "message": str(exc)},
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())
