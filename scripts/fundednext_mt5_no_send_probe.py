from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.fundednext_stellar_instant import PILOT_SYMBOL_MAP

mt5 = importlib.import_module("MetaTrader5")

RETAINED_SYMBOLS = ("AUDJPY", "GBPUSD", "GBPJPY", "EURUSD", "XAUUSD", "NAS100")
EXPECTED_SERVER = "FundedNext-Server"


def _fail(reason: str, *, details: dict[str, Any] | None = None) -> int:
    payload = {
        "probe": "fundednext_mt5_no_send",
        "mode": "NO_SEND",
        "ok": False,
        "reason": reason,
        "details": details or {},
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 2


def _git_sha(root: Path) -> str:
    value = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(value) != 40:
        raise RuntimeError("git_sha_unavailable")
    return value


def _account_fingerprint(account: Any) -> str:
    material = "|".join(
        (
            str(account.login),
            str(account.server),
            str(account.company),
            str(account.currency),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _symbol_snapshot(symbol: str) -> dict[str, Any]:
    provider_symbol = PILOT_SYMBOL_MAP.get(symbol, symbol)
    info = mt5.symbol_info(provider_symbol)
    if info is None:
        raise RuntimeError(
            f"symbol_info_unavailable:{symbol}:{provider_symbol}"
        )

    if not info.visible and not mt5.symbol_select(provider_symbol, True):
        raise RuntimeError(
            f"symbol_select_failed:{symbol}:{provider_symbol}"
        )

    tick = mt5.symbol_info_tick(provider_symbol)
    if tick is None:
        raise RuntimeError(
            f"symbol_tick_unavailable:{symbol}:{provider_symbol}"
        )

    return {
        "symbol": symbol,
        "provider_symbol": provider_symbol,
        "visible": bool(info.visible),
        "digits": int(info.digits),
        "point": float(info.point),
        "tick_size": float(info.trade_tick_size),
        "tick_value": float(info.trade_tick_value),
        "contract_size": float(info.trade_contract_size),
        "volume_min": float(info.volume_min),
        "volume_max": float(info.volume_max),
        "volume_step": float(info.volume_step),
        "stops_level": int(info.trade_stops_level),
        "freeze_level": int(info.trade_freeze_level),
        "filling_mode": int(info.filling_mode),
        "trade_mode": int(info.trade_mode),
        "bid": float(tick.bid),
        "ask": float(tick.ask),
        "spread_points": (float(tick.ask) - float(tick.bid)) / float(info.point)
        if info.point
        else None,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
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

        positions = mt5.positions_get()
        if positions is None:
            return _fail("positions_unavailable", details={"last_error": mt5.last_error()})

        orders = mt5.orders_get()
        if orders is None:
            return _fail("orders_unavailable", details={"last_error": mt5.last_error()})

        symbols = [_symbol_snapshot(symbol) for symbol in RETAINED_SYMBOLS]
        account_identity_fingerprint = _account_fingerprint(account)

        payload = {
            "probe": "fundednext_mt5_no_send",
            "mode": "NO_SEND",
            "ok": True,
            "git_sha": _git_sha(root),
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "account": {
                "server": server,
                "company": str(account.company),
                "currency": str(account.currency),
                "leverage": int(account.leverage),
                "balance": float(account.balance),
                "equity": float(account.equity),
                "margin": float(account.margin),
                "margin_free": float(account.margin_free),
                "trade_allowed": bool(account.trade_allowed),
                "trade_expert": bool(account.trade_expert),
                "identity_fingerprint": account_identity_fingerprint,
            },
            "startup_reconciliation": {
                "open_positions_count": len(positions),
                "pending_orders_count": len(orders),
                "clean": len(positions) == 0 and len(orders) == 0,
            },
            "retained_symbols": symbols,
            "safety": {
                "order_send_called": False,
                "order_submission_authorized": False,
                "real_capital_authorized": False,
            },
        }

        out_dir = root / "artifacts"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "fundednext_mt5_no_send_probe.json"
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        print(f"ARTIFACT={out_path.resolve()}")
        return 0
    except Exception as exc:  # fail closed for live account inspection
        return _fail(
            "probe_exception",
            details={"type": type(exc).__name__, "message": str(exc)},
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())
