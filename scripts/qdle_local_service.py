#!/usr/bin/env python3
"""Start QDLE as a standalone, loopback-only VPS worker.

Requires installed MetaTrader5 and a connected account. A separate trusted
QORE treasury publisher MUST push fresh bank/cushion/risk events; otherwise the
service intentionally cannot reserve any volume. This program NEVER sends
orders, logs credentials, or derives QORE reserves from the broker balance.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from qore.infrastructure.qore_dynamic_lot_engine import QDLE, QDLEError
from qore.infrastructure.qdle_local_api import serve_loopback
from qore.infrastructure.qdle_mt5_read_only import MT5ReadOnlyCalculator


def main() -> int:
    required = ("QDLE_TRADER_TOKEN", "QDLE_TREASURY_TOKEN",
                "QDLE_PROVIDER_TOKEN", "QDLE_MT5_ACCOUNT_ID", "QDLE_SQLITE_PATH")
    if any(not os.environ.get(name) for name in required):
        print("QDLE FAIL CLOSED: missing local-only authority configuration",
              file=sys.stderr)
        return 2
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("QDLE FAIL CLOSED: MetaTrader5 Python package not installed",
              file=sys.stderr)
        return 2
    if not mt5.initialize():
        print("QDLE FAIL CLOSED: connected MT5 terminal not available",
              file=sys.stderr)
        return 2
    try:
        account = mt5.account_info()
        account_id = os.environ["QDLE_MT5_ACCOUNT_ID"]
        if account is None or str(account.login) != account_id or account.currency != "USD":
            raise QDLEError("live terminal differs from configured funded account")
        db_file = Path(os.environ["QDLE_SQLITE_PATH"]).resolve()
        db_file.parent.mkdir(parents=True, exist_ok=True)
        engine = QDLE(db_file, MT5ReadOnlyCalculator(mt5, account_id),
                      enforce_finance_approval=True)
        # Intentionally starts NOT READY until a fresh independently funded QORE
        # ACCOUNT event AND verified MT5 SYMBOL events have arrived.
        serve_loopback(
            engine, trader_token=os.environ["QDLE_TRADER_TOKEN"],
            treasury_token=os.environ["QDLE_TREASURY_TOKEN"],
            provider_token=os.environ["QDLE_PROVIDER_TOKEN"],
            port=int(os.environ.get("QDLE_PORT", "18761")),
        )
    except (QDLEError, OSError, ValueError) as exc:
        print(f"QDLE FAIL CLOSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
