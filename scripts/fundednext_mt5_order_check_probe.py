"""Broker-native MT5 order_check probe for the retained FundedNext Forex universe.

This probe never calls order_send and does not fabricate a VT-08 signal. It
verifies the canonical payload shape for every direction that the certified live
portfolio is allowed to use, including certified EURUSD R38 long and short.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import MetaTrader5 as mt5

from qore.infrastructure.fundednext_live_guard import CERTIFIED_LIVE_DIRECTIONS
from qore.infrastructure.fundednext_stellar_instant import PILOT_SYMBOL_MAP
from qore.infrastructure.fundednext_live_mt5 import MetaTrader5FundedNextLiveTransport
from qore.infrastructure.fundednext_mt5 import FundedNextMt5OrderPlan
from qore.infrastructure.order_intent import OrderSide, OrderType

_MARKETS = ("AUDJPY", "GBPUSD", "GBPJPY", "EURUSD", "XAUUSD", "NAS100")
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
            provider_symbol = PILOT_SYMBOL_MAP.get(symbol, symbol)
            spec = transport.symbol_info(provider_symbol)
            if spec is None:
                raise SystemExit(
                    f"symbol unavailable: {symbol}:{provider_symbol}"
                )
            volume = spec.minimum_volume
            base_distance = max(
                spec.point * Decimal("100"),
                spec.tick_size * Decimal("20"),
                spec.point * spec.minimum_stop_distance_points,
            )
            spread_distance = abs(spec.ask - spec.bid)
            distance = spread_distance + base_distance
            for side_text in sorted(CERTIFIED_LIVE_DIRECTIONS[symbol]):
                side = OrderSide.BUY if side_text == "long" else OrderSide.SELL
                entry = spec.ask if side is OrderSide.BUY else spec.bid
                stop = entry - distance if side is OrderSide.BUY else entry + distance
                target = (
                    entry + distance * Decimal("2")
                    if side is OrderSide.BUY
                    else entry - distance * Decimal("2")
                )
                plan = FundedNextMt5OrderPlan(
                    client_order_id=f"qore-shadow-{symbol.lower()}-{side_text}-probe",
                    qore_symbol=symbol,
                    provider_symbol=provider_symbol,
                    side=side,
                    order_type=OrderType.MARKET,
                    volume=volume,
                    effective_entry=entry,
                    limit_price=None,
                    stop_loss=stop,
                    take_profit=target,
                    margin_required=volume * spec.margin_per_volume,
                    planned_at=datetime.now(UTC),
                )
                result = transport.check_order(plan)
                check_key = f"{symbol}:{side_text}"
                checks[check_key] = {
                    "broker_valid": result.broker_valid,
                    "retcode": result.retcode,
                    "reason": result.reason,
                    "volume": str(volume),
                    "tick_size": str(spec.tick_size),
                    "tick_value": str(spec.tick_value),
                    "provider_symbol": provider_symbol,
                    "filling_mode_source": "fresh SymbolInfo",
                }
                if not result.broker_valid:
                    raise SystemExit(f"order_check failed for {check_key}: {result.reason}")
        payload = {
            "schema": "qore.fundednext.mt5-order-check-probe.v2",
            "mode": "BROKER_ORDER_CHECK_NO_SEND",
            "ok": True,
            "git_sha": _git_sha(root),
            "account_identity_fingerprint": _fingerprint(account),
            "server": str(account.server),
            "checked_at": datetime.now(UTC).isoformat(),
            "directions": {
                symbol: sorted(CERTIFIED_LIVE_DIRECTIONS[symbol]) for symbol in _MARKETS
            },
            "checks": checks,
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
