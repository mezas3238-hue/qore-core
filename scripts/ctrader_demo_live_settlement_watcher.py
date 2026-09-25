#!/usr/bin/env python3
"""Independent read-only cTrader DEMO settlement watcher."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.ctrader_demo_free_binding import discover_free_account_binding
from qore.infrastructure.ctrader_demo_free_position_service import CTraderDemoFreePositionService
from qore.infrastructure.ctrader_demo_free_sink import credentials_from_environment
from qore.infrastructure.ctrader_demo_live_behavior_lab import (
    CTraderDemoLiveBehaviorLedger,
    settlement_observation_payload,
)
from qore.infrastructure.ctrader_demo_trade_registry import CTraderDemoTradeRegistry
from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient

SCHEMA = "qore.ctrader-demo.live-settlement-watcher.v1"


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _load_state(path: Path, *, initial_cursor: datetime) -> tuple[datetime, set[int]]:
    if not path.exists():
        return initial_cursor, set()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("schema") != SCHEMA:
            raise ValueError("settlement watcher state schema drift")
        cursor = datetime.fromisoformat(str(raw["cursor_at"]))
        if cursor.tzinfo is None or cursor.utcoffset() is None:
            raise ValueError("settlement watcher cursor must be timezone-aware")
        seen = {
            int(value)
            for value in raw.get("seen_deal_ids", [])
            if str(value).isdigit() and int(value) > 0
        }
        return cursor.astimezone(UTC), seen
    except (OSError, ValueError, json.JSONDecodeError, TypeError):
        return initial_cursor, set()


def _store_state(path: Path, *, cursor: datetime, seen: set[int]) -> None:
    _atomic_json(
        path,
        {
            "schema": SCHEMA,
            "cursor_at": cursor.astimezone(UTC).isoformat(),
            "seen_deal_ids": sorted(seen),
        },
    )


def _run_session(root: Path, *, interval_seconds: float) -> None:
    raw_binding = json.loads(
        (root / "var" / "ctrader_demo_free" / "binding.json").read_text(encoding="utf-8")
    )
    bound_at = datetime.fromisoformat(str(raw_binding["bound_at"])).astimezone(UTC)
    source_sizes = {
        str(row["qore_symbol"]): Decimal(str(row["source_contract_size_units"]))
        for row in raw_binding["contracts"]
    }
    state_path = (
        root
        / "var"
        / "ctrader_demo_live_behavior_lab"
        / "settlement-watcher-state.json"
    )
    ledger = CTraderDemoLiveBehaviorLedger(
        root
        / "artifacts"
        / "ctrader_demo_live_behavior_lab"
        / "settlement-events.normalized.jsonl"
    )
    cursor, seen = _load_state(
        state_path,
        initial_cursor=bound_at - timedelta(minutes=1),
    )

    credentials = credentials_from_environment()
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        binding = discover_free_account_binding(client)
        positions = CTraderDemoFreePositionService(
            client=client,
            configuration=binding.configuration,
        )
        registry = CTraderDemoTradeRegistry(
            root / "var" / "ctrader_demo_free" / "trade-registry.json"
        )

        ledger.record_raw(
            {
                "event": "CTRADER_DEMO_SETTLEMENT_WATCHER_STARTED",
                "observed_at": datetime.now(UTC).isoformat(),
                "poll_interval_seconds": interval_seconds,
            },
            source="settlement",
        )

        while True:
            now = datetime.now(UTC)
            window_start = max(
                bound_at - timedelta(minutes=1),
                cursor - timedelta(minutes=15),
            )
            deals = positions.deals(
                opened_at=window_start,
                closed_at=now,
                max_rows=1000,
            )
            open_ids = {item.position_id for item in positions.positions()}

            for deal in deals:
                if not deal.is_closing or deal.deal_id in seen:
                    continue
                reg = registry.by_position(deal.position_id)
                if reg is None:
                    continue
                source_size = source_sizes.get(reg.qore_symbol)
                if source_size is None or source_size <= 0:
                    continue
                if (
                    deal.gross_profit is None
                    or deal.swap is None
                    or deal.pnl_conversion_fee is None
                    or deal.net_profit is None
                ):
                    continue
                payload = settlement_observation_payload(
                    trader=reg.trader,
                    symbol=reg.qore_symbol,
                    signal_fingerprint=reg.signal_fingerprint,
                    position_id=deal.position_id,
                    deal_id=deal.deal_id,
                    order_id=deal.order_id,
                    side=deal.side,
                    execution_price=deal.execution_price,
                    filled_units=deal.filled_units,
                    source_volume=deal.filled_units / source_size,
                    net_profit=deal.net_profit,
                    gross_profit=deal.gross_profit,
                    commission=deal.commission,
                    swap=deal.swap,
                    pnl_conversion_fee=deal.pnl_conversion_fee,
                    balance_after=deal.balance_after,
                    executed_at=deal.executed_at,
                    position_open_after=deal.position_id in open_ids,
                )
                ledger.record_raw(
                    payload,
                    source="settlement",
                    observed_at=deal.executed_at,
                )
                seen.add(deal.deal_id)

            cursor = now
            _store_state(state_path, cursor=cursor, seen=seen)
            time.sleep(interval_seconds)
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--interval-seconds", type=float, default=30.0)
    args = parser.parse_args()
    if args.interval_seconds < 10:
        raise SystemExit("settlement watcher interval must be >= 10 seconds")

    root = args.root.resolve()
    ledger = CTraderDemoLiveBehaviorLedger(
        root
        / "artifacts"
        / "ctrader_demo_live_behavior_lab"
        / "settlement-events.normalized.jsonl"
    )
    while True:
        try:
            _run_session(root, interval_seconds=args.interval_seconds)
        except KeyboardInterrupt:
            return 0
        except Exception as error:
            ledger.record_raw(
                {
                    "event": "CTRADER_DEMO_SETTLEMENT_WATCHER_ERROR",
                    "reason": type(error).__name__,
                    "message": str(error),
                    "observed_at": datetime.now(UTC).isoformat(),
                },
                source="settlement",
            )
            time.sleep(10)


if __name__ == "__main__":
    raise SystemExit(main())
