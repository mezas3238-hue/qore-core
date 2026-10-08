#!/usr/bin/env python3
"""QDLE native MT5 metadata publisher for an authorized FundedNext VPS.

It reads (never trades) broker instrument specifications and sends new events
to the local QDLE provider endpoint. Lot-grid values are NEVER hardcoded.
The account's fee schedule must be explicitly verified and supplied locally.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.qdle_mt5_read_only import VerifiedFee, read_mt5_symbols
from qore.infrastructure.qore_dynamic_lot_engine import QDLEError


def post_provider(endpoint: str, token: str, payload: dict) -> None:
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/v1/symbol-event",
        data=json.dumps(payload, default=str).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-QDLE-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=3) as reply:
        if reply.status != 200:
            raise QDLEError("QDLE provider event not accepted")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aliases", required=True, type=Path)
    parser.add_argument("--verified-fees", required=True, type=Path)
    parser.add_argument("--interval-seconds", type=float, default=2)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.interval_seconds < 0.5:
        parser.error("minimum interval 0.5 seconds")
    token = os.environ.get("QDLE_PROVIDER_TOKEN", "")
    account_id = os.environ.get("QDLE_MT5_ACCOUNT_ID", "")
    if len(token) < 24 or not account_id:
        parser.error("QDLE provider credentials and account binding required")
    aliases = json.loads(args.aliases.read_text(encoding="utf-8"))
    fees = json.loads(args.verified_fees.read_text(encoding="utf-8"))
    if not isinstance(aliases, dict) or not isinstance(fees, dict):
        parser.error("alias and fee maps must be JSON objects")
    required_aliases = {"AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "NAS100", "XAUUSD"}
    if not required_aliases.issubset(aliases):
        parser.error("six QORE assets must be explicitly mapped to MT5 names")
    try:
        import MetaTrader5 as mt5
    except ImportError:
        parser.error("MetaTrader5 package required on Windows VPS")
    if not mt5.initialize():
        parser.error("cannot attach to active MT5 terminal")
    try:
        def fee_quote(symbol, info):
            item = fees.get(symbol)
            if not isinstance(item, dict):
                raise QDLEError("missing verified account-specific fee: " + symbol)
            return VerifiedFee(Decimal(str(item["usd_per_lot"])), item["evidence"])

        while True:
            current = mt5.account_info()
            if current is None or str(current.login) != account_id or current.currency != "USD":
                raise QDLEError("MT5 account changed/disconnected")
            symbols = read_mt5_symbols(mt5, aliases, fee_quote,
                                       as_of=datetime.now(timezone.utc))
            for spec in symbols:
                post_provider("http://127.0.0.1:" + os.environ.get("QDLE_PORT", "18761"),
                              token, asdict(spec))
            if args.once:
                break
            time.sleep(args.interval_seconds)
    except (QDLEError, OSError, ValueError, KeyError) as exc:
        parser.error(f"fail-closed MT5 read-only publisher: {exc}")
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
