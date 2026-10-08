#!/usr/bin/env python3
"""Publish FundedNext MT5 + authenticated QORE economic events to QDLE.

The signed sovereign event is the ONLY source for available bank/cushion and
provider MLL headroom. The terminal is the ONLY source for actual broker
balance/equity/free margin/positions. This process cannot issue orders.
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

from qore.infrastructure.qdle_mt5_read_only import read_mt5_account_with_qore_treasury
from qore.infrastructure.qdle_signed_treasury import verify_treasury_hmac_event
from qore.infrastructure.qore_dynamic_lot_engine import QDLEError


def forward_account(mt5, *, signed_event: dict, hmac_key: bytes,
                    account_id: str, token: str, base_url: str,
                    now: datetime) -> int:
    receipt = verify_treasury_hmac_event(
        signed_event, hmac_key, now=now, expected_account_id=account_id)
    broker = read_mt5_account_with_qore_treasury(
        mt5, account_id=account_id, sequence=receipt.sequence,
        qore_unreserved_risk_usd=receipt.qore_unreserved_risk_usd,
        qore_trading_capital_usd=receipt.qore_trading_capital_usd,
        sovereign_free_source_usd=receipt.sovereign_free_source_usd,
        cushion_free_source_usd=receipt.cushion_free_source_usd,
        covered_fill_tickets=receipt.covered_fill_tickets,
        provider_loss_floor_usd=receipt.active_provider_mll_floor_usd,
        as_of=now,
    )
    # Never pretend that a strategy's gross revenue is funded cash.
    # Provider stop-out/DD headroom is computed by sovereign QORE Risk; QDLE
    # rejects any signed headroom greater than the broker equity above MLL.
    headroom = max(Decimal(0), broker.equity - receipt.active_provider_mll_floor_usd)
    if broker.equity < receipt.active_provider_mll_floor_usd:
        raise QDLEError("FundedNext provider MLL/stop-out floor already breached")
    if receipt.qore_unreserved_risk_usd > headroom:
        raise QDLEError("QORE risk allocation exceeds remaining provider loss buffer")
    if receipt.qore_trading_capital_usd > broker.equity:
        raise QDLEError("QORE trading capital exceeds MT5 broker equity")
    if (receipt.sovereign_free_source_usd + receipt.cushion_free_source_usd
            > receipt.qore_trading_capital_usd):
        raise QDLEError("QORE cash lanes exceed funded proprietary capital")
    if receipt.qore_unreserved_risk_usd > receipt.qore_trading_capital_usd:
        raise QDLEError("QORE risk headroom exceeds proprietary capital")
    data = json.dumps(asdict(broker), default=str).encode()
    request = urllib.request.Request(
        base_url.rstrip("/") + "/v1/account-event", data=data,
        headers={"Content-Type": "application/json", "X-QDLE-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        if response.status != 200:
            raise QDLEError("QDLE rejected signed treasury/MT5 account event")
    return receipt.sequence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--treasury-envelope", type=Path, required=True)
    parser.add_argument("--interval-seconds", type=float, default=1)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.interval_seconds < .5:
        parser.error("poll at >=0.5s")
    account_id = os.environ.get("QDLE_MT5_ACCOUNT_ID", "")
    token = os.environ.get("QDLE_TREASURY_TOKEN", "")
    key_hex = os.environ.get("QDLE_TREASURY_HMAC_KEY_HEX", "")
    if not account_id or len(token) < 24 or len(key_hex) < 64:
        parser.error("account, unique treasury API token and HMAC key required")
    try:
        hmac_key = bytes.fromhex(key_hex)
        import MetaTrader5 as mt5
    except (ImportError, ValueError):
        parser.error("MetaTrader5 and valid key required")
    if not mt5.initialize():
        parser.error("no active MT5 terminal")
    previous = 0
    try:
        while True:
            envelope = json.loads(args.treasury_envelope.read_text(encoding="utf-8"))
            latest = int(envelope["payload"]["sequence"])
            if latest > previous:
                previous = forward_account(
                    mt5, signed_event=envelope, hmac_key=hmac_key,
                    account_id=account_id, token=token,
                    base_url="http://127.0.0.1:" + os.environ.get("QDLE_PORT", "18761"),
                    now=datetime.now(timezone.utc))
            if args.once:
                break
            time.sleep(args.interval_seconds)
    except (OSError, QDLEError, KeyError, ValueError) as exc:
        parser.error(f"QDLE signed account event FAIL CLOSED: {exc}")
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
