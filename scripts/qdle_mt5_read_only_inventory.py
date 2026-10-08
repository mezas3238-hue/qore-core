#!/usr/bin/env python3
"""Offline-safe MT5 FundedNext instrument discovery (read-only, zero orders).

Emits provider's actual candidate symbols for all 6 QORE Core asset names,
plus MT5 per-symbol lot grid and tick economics. It DOES NOT infer a unique
NAS100/NDX100 mapping or broker commissions and never changes a chart/symbol.
Account login is validated but NOT written to the report.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

QORE_ASSETS = ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "NAS100", "XAUUSD")


def _decimal(v: object, name: str) -> str:
    try:
        value = Decimal(str(v))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"invalid broker {name}") from exc
    if not value.is_finite() or value < 0:
        raise ValueError(f"nonfinite or negative broker {name}")
    return format(value, "f")


def _candidates(label: str, name: str) -> bool:
    x = name.upper()
    if label == "NAS100":
        return "NAS100" in x or "NDX100" in x
    return label in x


def discover(mt5: object, expected_login: str) -> dict:
    account = mt5.account_info()
    if account is None or str(account.login) != expected_login:
        raise ValueError("FundedNext account login mismatch")
    if account.currency != "USD":
        raise ValueError("non-USD MT5 account needs explicit currency model")
    infos = mt5.symbols_get()
    if infos is None:
        raise ValueError("MT5 returned no instrument catalog")
    catalog: dict[str, list[dict]] = {asset: [] for asset in QORE_ASSETS}
    for info in infos:
        symbol_name = str(info.name)
        labels = [asset for asset in QORE_ASSETS if _candidates(asset, symbol_name)]
        if not labels:
            continue
        item = {
            "mt5_exact_symbol": symbol_name,
            "volume_min": _decimal(info.volume_min, "volume_min"),
            "volume_max": _decimal(info.volume_max, "volume_max"),
            "volume_step": _decimal(info.volume_step, "volume_step"),
            "volume_limit": _decimal(info.volume_limit, "volume_limit"),
            "contract_size": _decimal(info.trade_contract_size, "contract_size"),
            "tick_size": _decimal(info.trade_tick_size, "tick_size"),
            "tick_value": _decimal(info.trade_tick_value, "tick_value"),
            "tick_value_profit": _decimal(info.trade_tick_value_profit, "tick_value_profit"),
            "tick_value_loss": _decimal(info.trade_tick_value_loss, "tick_value_loss"),
            "profit_currency": str(info.currency_profit),
            "trade_mode": int(info.trade_mode),
            "visible": bool(info.visible),
            "fee_usd_per_lot": None,
            "fee_proof": "REQUIRES_ACCOUNT_SPECIFIC_VERIFICATION",
        }
        for label in labels:
            catalog[label].append(item)
    return {
        "schema": "qore.qdle.mt5-read-only-inventory.v1",
        "source": "OBSERVED_CONNECTED_MT5_ACCOUNT",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "account_login_recorded": False,
        "account_currency": account.currency,
        "server": str(account.server),
        "symbols": {a: sorted(items, key=lambda z: z["mt5_exact_symbol"])
                    for a, items in catalog.items()},
        "missing_or_unresolved": [a for a, items in catalog.items() if len(items) != 1],
        "replay_certified": False,
        "executed_orders": 0,
        "note": "Candidates are not mapping decisions; verify symbol and fees before LIVE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    login = os.environ.get("QDLE_MT5_ACCOUNT_ID", "")
    if not login:
        parser.error("QDLE_MT5_ACCOUNT_ID required, do not write login into result")
    try:
        import MetaTrader5 as mt5
    except ImportError:
        parser.error("MetaTrader5 package required on attached Windows VPS")
    if not mt5.initialize():
        parser.error("MT5 disconnected")
    try:
        report = discover(mt5, login)
    finally:
        mt5.shutdown()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True),
                           encoding="utf-8")
    print(json.dumps({"report": str(args.output),
                      "unresolved_symbols": report["missing_or_unresolved"],
                      "read_only": True}, sort_keys=True))
    return 0 if not report["missing_or_unresolved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
