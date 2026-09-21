"""FundedNext MT5 feed-transport latency probe.

This diagnostic intentionally separates:
- new-tick transport latency (broker timestamp -> first local observation), from
- market tick inter-arrival time, and from
- the hard <=2s executable quote-age gate enforced immediately before LIVE send.

It never sends or checks an order.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.fundednext_mt5_clock import (
    normalise_fundednext_server_epoch,
)
from qore.infrastructure.fundednext_stellar_instant import PILOT_SYMBOL_MAP

MARKETS = ("AUDJPY", "GBPUSD", "GBPJPY", "EURUSD", "XAUUSD", "NAS100")
MAX_TRANSPORT_LATENCY_SECONDS = 2.0


def _tick_at(tick: Any) -> datetime:
    raw_msc = int(getattr(tick, "time_msc", 0) or 0)
    if raw_msc > 0:
        raw_seconds, millis = divmod(raw_msc, 1000)
        return normalise_fundednext_server_epoch(raw_seconds).replace(
            microsecond=millis * 1000
        )
    raw_seconds = int(getattr(tick, "time", 0) or 0)
    if raw_seconds <= 0:
        raise RuntimeError("broker tick timestamp unavailable")
    return normalise_fundednext_server_epoch(raw_seconds)


def run_probe(*, root: Path, timeout_seconds: float, poll_seconds: float) -> dict[str, object]:
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None or account is None:
            raise SystemExit("MT5 terminal/account unavailable")

        baseline: dict[str, int] = {}
        for qore_symbol in MARKETS:
            provider_symbol = PILOT_SYMBOL_MAP.get(qore_symbol, qore_symbol)
            tick = mt5.symbol_info_tick(provider_symbol)
            if tick is None:
                raise SystemExit(f"tick unavailable:{qore_symbol}:{provider_symbol}")
            baseline[qore_symbol] = int(getattr(tick, "time_msc", 0) or 0)

        found: dict[str, dict[str, object]] = {}
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline and len(found) < len(MARKETS):
            for qore_symbol in MARKETS:
                if qore_symbol in found:
                    continue
                provider_symbol = PILOT_SYMBOL_MAP.get(qore_symbol, qore_symbol)
                started = time.perf_counter()
                tick = mt5.symbol_info_tick(provider_symbol)
                api_ms = (time.perf_counter() - started) * 1000.0
                if tick is None:
                    continue
                raw_msc = int(getattr(tick, "time_msc", 0) or 0)
                if raw_msc <= 0 or raw_msc == baseline[qore_symbol]:
                    continue
                observed_at = datetime.now(UTC)
                tick_at = _tick_at(tick)
                latency = (observed_at - tick_at).total_seconds()
                found[qore_symbol] = {
                    "provider_symbol": provider_symbol,
                    "tick_at": tick_at.isoformat(),
                    "observed_at": observed_at.isoformat(),
                    "transport_latency_seconds": latency,
                    "api_call_ms": api_ms,
                    "within_transport_sla": (
                        -0.5 <= latency <= MAX_TRANSPORT_LATENCY_SECONDS
                    ),
                }
            if len(found) < len(MARKETS):
                time.sleep(poll_seconds)

        results: dict[str, object] = {}
        all_observed = True
        all_within = True
        for qore_symbol in MARKETS:
            item = found.get(qore_symbol)
            if item is None:
                all_observed = False
                results[qore_symbol] = {
                    "status": "NO_NEW_TICK_OBSERVED",
                    "interpretation": "inconclusive-not-late",
                }
                continue
            if not bool(item["within_transport_sla"]):
                all_within = False
            results[qore_symbol] = {"status": "OBSERVED", **item}

        payload = {
            "schema": "qore.fundednext.feed-transport-latency.v1",
            "mode": "NO_SEND_DIAGNOSTIC",
            "git_sha": __import__("subprocess").check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                text=True,
            ).strip(),
            "terminal_connected": bool(terminal.connected),
            "account_server": str(account.server),
            "timeout_seconds": timeout_seconds,
            "poll_seconds": poll_seconds,
            "transport_sla_seconds": MAX_TRANSPORT_LATENCY_SECONDS,
            "all_markets_observed_new_tick": all_observed,
            "all_observed_ticks_within_transport_sla": all_within,
            "results": results,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        out = root / "artifacts" / "fundednext_feed_transport_latency.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload
    finally:
        mt5.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--poll-seconds", type=float, default=0.05)
    args = parser.parse_args()
    payload = run_probe(
        root=args.root.resolve(),
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
