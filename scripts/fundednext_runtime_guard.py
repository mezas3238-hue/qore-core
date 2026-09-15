from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

mt5 = importlib.import_module("MetaTrader5")

EXPECTED_SERVER = "FundedNext-Server"
RETAINED_SYMBOLS = ("AUDJPY", "GBPUSD", "GBPJPY")


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


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _snapshot(git_sha: str) -> dict[str, Any]:
    terminal = mt5.terminal_info()
    if terminal is None or not bool(terminal.connected):
        raise RuntimeError("mt5_terminal_disconnected")
    account = mt5.account_info()
    if account is None:
        raise RuntimeError("mt5_account_info_unavailable")
    server = str(account.server)
    if server != EXPECTED_SERVER:
        raise RuntimeError(f"mt5_server_mismatch:{server}")
    available_raw = mt5.symbols_get()
    if available_raw is None:
        raise RuntimeError("mt5_symbol_catalog_unavailable")
    available = {str(item.name) for item in available_raw if getattr(item, "name", "")}
    missing = [symbol for symbol in RETAINED_SYMBOLS if symbol not in available]
    if missing:
        raise RuntimeError(f"retained_symbols_missing:{','.join(missing)}")
    positions = mt5.positions_get()
    orders = mt5.orders_get()
    if positions is None or orders is None:
        raise RuntimeError("mt5_reconciliation_unavailable")
    return {
        "schema": "qore.fundednext.runtime-guard.v1",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "git_sha": git_sha,
        "connected": True,
        "server": server,
        "balance": float(account.balance),
        "equity": float(account.equity),
        "margin": float(account.margin),
        "margin_free": float(account.margin_free),
        "trade_allowed": bool(account.trade_allowed),
        "trade_expert": bool(account.trade_expert),
        "retained_symbols": list(RETAINED_SYMBOLS),
        "open_positions_count": len(positions),
        "pending_orders_count": len(orders),
        "safety": {
            "order_send_called": False,
            "order_check_called": False,
            "provider_mutation_requested": False,
        },
    }


def run(*, state_dir: Path, interval_seconds: float, once: bool) -> int:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    git_sha = _git_sha()
    state_dir.mkdir(parents=True, exist_ok=True)
    output = state_dir / "guard.json"
    while True:
        if not mt5.initialize():
            raise RuntimeError(f"mt5_initialize_failed:{mt5.last_error()}")
        try:
            payload = _snapshot(git_sha)
            _atomic_write(output, payload)
        finally:
            mt5.shutdown()
        if once:
            return 0
        time.sleep(interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--interval-seconds", type=float, default=10.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    try:
        return run(
            state_dir=args.state_dir,
            interval_seconds=args.interval_seconds,
            once=args.once,
        )
    except Exception as exc:
        payload = {
            "schema": "qore.fundednext.runtime-guard.v1",
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "connected": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "safety": {
                "order_send_called": False,
                "provider_mutation_requested": False,
            },
        }
        args.state_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(args.state_dir / "guard.json", payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
