"""Broker-native MT5 order_check probe for the retained FundedNext Forex universe.

This probe never calls order_send and does not fabricate a VT-08 signal. It only
verifies that the current broker accepts the canonical payload shape, filling
mode, volume step, margin calculation and SL/TP geometry that the live gateway
would use after a genuine upstream authorization.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import MetaTrader5 as mt5

from qore.infrastructure.fundednext_live_mt5 import MetaTrader5FundedNextLiveTransport
from qore.infrastructure.fundednext_mt5 import FundedNextMt5OrderPlan
from qore.infrastructure.order_intent import OrderSide, OrderType

_MARKETS = ("AUDJPY", "GBPUSD", "GBPJPY")
_SERVER = "FundedNext-Server"
_ACCOUNT_REF = "fundednext-stellar-instant-live"


def _git_sha(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _fingerprint(account: object) -> str:
    value = "|".join(
        (
            str(getattr(account, "login")),
            str(getattr(account, "server")),
            str(getattr(account, "company")),
            str(getattr(account, "currency")),
        )
    )
    return hashlib.sha256(value.encode()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    terminal_path = __import__("os").environ.get("QORE_MT5_TERMINAL_PATH")
    initialized = mt5.initialize(path=terminal_path) if terminal_path else mt5.initialize()
    if not initialized:
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None or str(account.server) != _SERVER:
            raise SystemExit("FundedNext account/server binding failed")
        transport = MetaTrader5FundedNextLiveTransport(
            api=mt5,
            qore_account_ref=_ACCOUNT_REF,
            expected_login=int(account.login),
            expected_server=_SERVER,
        )
        checks: dict[str, object] = {}
        for symbol in _MARKETS:
            spec = transport.symbol_info(symbol)
            if spec is None:
                raise SystemExit(f"symbol unavailable: {symbol}")
            volume = spec.minimum_volume
            distance = max(spec.point * Decimal("100"), spec.tick_size * Decimal("20"))
            entry = spec.ask
            plan = FundedNextMt5OrderPlan(
                client_order_id=f"qore-shadow-{symbol.lower()}-probe",
                qore_symbol=symbol,
                provider_symbol=symbol,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                volume=volume,
                effective_entry=entry,
                limit_price=None,
                stop_loss=entry - distance,
                take_profit=entry + distance * Decimal("2"),
                margin_required=volume * spec.margin_per_volume,
                planned_at=datetime.now(UTC),
            )
            result = transport.check_order(plan)
            checks[symbol] = {
                "broker_valid": result.broker_valid,
                "retcode": result.retcode,
                "reason": result.reason,
                "volume": str(volume),
                "tick_size": str(spec.tick_size),
                "tick_value": str(spec.tick_value),
                "filling_mode_source": "fresh SymbolInfo",
            }
            if not result.broker_valid:
                raise SystemExit(f"order_check failed for {symbol}: {result.reason}")
        payload = {
            "schema": "qore.fundednext.mt5-order-check-probe.v1",
            "mode": "BROKER_ORDER_CHECK_NO_SEND",
            "ok": True,
            "git_sha": _git_sha(root),
            "account_identity_fingerprint": _fingerprint(account),
            "server": str(account.server),
            "checked_at": datetime.now(UTC).isoformat(),
            "symbols": checks,
            "order_send_called": False,
        }
        out = root / "artifacts" / "fundednext_mt5_order_check_probe.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        digest = hashlib.sha256(out.read_bytes()).hexdigest()
        print("QORE MT5 ORDER_CHECK PROBE PASSED")
        print(out)
        print(f"SHA256={digest}")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
