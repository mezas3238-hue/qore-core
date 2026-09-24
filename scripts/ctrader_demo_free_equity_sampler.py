from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.ctrader_demo_free_binding import discover_free_account_binding
from qore.infrastructure.ctrader_demo_free_position_service import (
    CTraderDemoFreePositionService,
)
from qore.infrastructure.ctrader_demo_free_sink import credentials_from_environment
from qore.infrastructure.ctrader_demo_trade_registry import CTraderDemoTradeRegistry
from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient

ROOT = Path(r"C:\QORE_CTRADER_DEMO_FREE")
FREE_DIR = ROOT / "var" / "ctrader_demo_free"
BINDING_PATH = FREE_DIR / "binding.json"
STATE_PATH = FREE_DIR / "equity-drawdown.json"
ERROR_PATH = ROOT / "artifacts" / "ctrader_demo_equity_sampler_errors.log"
INTERVAL_SECONDS = 5


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(
                payload,
                stream,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _load_state(
    *,
    allocations: dict[str, Decimal],
    portfolio_base: Decimal,
    started_at: datetime,
) -> dict[str, object]:
    if STATE_PATH.exists():
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if raw.get("schema") == "qore.ctrader-demo.equity-drawdown.v1":
            return raw
    return {
        "schema": "qore.ctrader-demo.equity-drawdown.v1",
        "started_at": started_at.isoformat(),
        "last_deal_poll_at": started_at.isoformat(),
        "processed_deal_ids": [],
        "portfolio": {
            "base_capital": format(portfolio_base, "f"),
            "current_equity": format(portfolio_base, "f"),
            "peak_equity": format(portfolio_base, "f"),
            "max_drawdown": "0",
            "max_drawdown_pct": "0",
            "max_open_positions": 0,
        },
        "traders": {
            trader: {
                "base_capital": format(capital, "f"),
                "realized_pnl": "0",
                "unrealized_pnl": "0",
                "current_equity": format(capital, "f"),
                "peak_equity": format(capital, "f"),
                "max_drawdown": "0",
                "max_drawdown_pct": "0",
                "max_open_positions": 0,
            }
            for trader, capital in allocations.items()
        },
        "position_excursions": {},
        "observed_at": started_at.isoformat(),
    }


def _deal_windows(start: datetime, end: datetime):
    cursor = start
    while cursor < end:
        right = min(end, cursor + timedelta(days=1))
        yield cursor, right
        cursor = right


def _sample(
    *,
    service: CTraderDemoFreePositionService,
    registry: CTraderDemoTradeRegistry,
    state: dict[str, object],
    allocations: dict[str, Decimal],
) -> dict[str, object]:
    now = datetime.now(UTC)
    account = service.account_snapshot(observed_at=now)
    positions = service.positions()
    unrealized_by_position = service.unrealized_by_position()

    traders = state["traders"]
    assert isinstance(traders, dict)
    processed = {int(item) for item in state.get("processed_deal_ids", [])}
    poll_from = datetime.fromisoformat(str(state["last_deal_poll_at"]))
    poll_from = min(poll_from, now) - timedelta(seconds=30)

    for left, right in _deal_windows(poll_from, now):
        if right <= left:
            continue
        for deal in service.deals(
            opened_at=left,
            closed_at=right,
            max_rows=1000,
        ):
            if deal.deal_id in processed:
                continue
            entry = registry.by_position(deal.position_id)
            if entry is None:
                # Position binding may lag a fresh market fill by one sample.
                continue
            row = traders.get(entry.trader)
            if not isinstance(row, dict):
                continue
            contribution = (
                deal.net_profit
                if deal.net_profit is not None
                else deal.commission
            )
            realized = Decimal(str(row["realized_pnl"])) + contribution
            row["realized_pnl"] = format(realized, "f")
            processed.add(deal.deal_id)

    position_excursions = state.setdefault("position_excursions", {})
    assert isinstance(position_excursions, dict)
    current_unrealized = {name: Decimal("0") for name in allocations}
    for position in positions:
        value = unrealized_by_position.get(position.position_id, Decimal("0"))
        current_unrealized[position.trader_id.value] = (
            current_unrealized.get(position.trader_id.value, Decimal("0")) + value
        )
        key = str(position.position_id)
        legs = registry.entries_by_position(position.position_id)
        requested_stop_risk = sum(
            (
                Decimal(leg.requested_stop_risk)
                for leg in legs
                if Decimal(leg.requested_stop_risk) > 0
            ),
            Decimal("0"),
        )
        previous = position_excursions.get(key)
        if isinstance(previous, dict):
            minimum = min(Decimal(str(previous["min_unrealized_pnl"])), value)
            maximum = max(Decimal(str(previous["max_unrealized_pnl"])), value)
            samples = int(previous.get("samples", 0)) + 1
        else:
            minimum = value
            maximum = value
            samples = 1
        position_excursions[key] = {
            "position_id": position.position_id,
            "trader": position.trader_id.value,
            "symbol": position.qore_symbol,
            "opened_at": position.opened_at.isoformat(),
            "requested_stop_risk": format(requested_stop_risk, "f"),
            "min_unrealized_pnl": format(minimum, "f"),
            "max_unrealized_pnl": format(maximum, "f"),
            "samples": samples,
            "last_observed_at": now.isoformat(),
        }

    for trader, base in allocations.items():
        row = traders[trader]
        assert isinstance(row, dict)
        realized = Decimal(str(row["realized_pnl"]))
        unrealized = current_unrealized.get(trader, Decimal("0"))
        equity = base + realized + unrealized
        peak = max(Decimal(str(row["peak_equity"])), equity)
        drawdown = peak - equity
        max_dd = max(Decimal(str(row["max_drawdown"])), drawdown)
        open_count = sum(
            1 for item in positions if item.trader_id.value == trader
        )
        row.update(
            {
                "base_capital": format(base, "f"),
                "unrealized_pnl": format(unrealized, "f"),
                "current_equity": format(equity, "f"),
                "peak_equity": format(peak, "f"),
                "max_drawdown": format(max_dd, "f"),
                "max_drawdown_pct": format(
                    (max_dd / base) * Decimal("100"), ".8f"
                )
                if base > 0
                else "0",
                "open_positions": open_count,
                "max_open_positions": max(
                    int(row.get("max_open_positions", 0)),
                    open_count,
                ),
            }
        )

    portfolio = state["portfolio"]
    assert isinstance(portfolio, dict)
    portfolio_base = Decimal(str(portfolio["base_capital"]))
    portfolio_peak = max(
        Decimal(str(portfolio["peak_equity"])),
        account.equity,
    )
    portfolio_dd = portfolio_peak - account.equity
    portfolio_max_dd = max(
        Decimal(str(portfolio["max_drawdown"])),
        portfolio_dd,
    )
    portfolio.update(
        {
            "current_equity": format(account.equity, "f"),
            "peak_equity": format(portfolio_peak, "f"),
            "max_drawdown": format(portfolio_max_dd, "f"),
            "max_drawdown_pct": format(
                (portfolio_max_dd / portfolio_base) * Decimal("100"), ".8f"
            )
            if portfolio_base > 0
            else "0",
            "balance": format(account.balance, "f"),
            "unrealized_pnl": format(account.net_unrealized_pnl, "f"),
            "open_positions": len(positions),
            "max_open_positions": max(
                int(portfolio.get("max_open_positions", 0)),
                len(positions),
            ),
        }
    )
    state["processed_deal_ids"] = sorted(processed)
    state["last_deal_poll_at"] = now.isoformat()
    state["observed_at"] = now.isoformat()
    return state


def main() -> None:
    credentials = credentials_from_environment()
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        binding = discover_free_account_binding(client)
        service = CTraderDemoFreePositionService(
            client=client,
            configuration=binding.configuration,
        )
        registry = CTraderDemoTradeRegistry(FREE_DIR / "trade-registry.json")
        binding_raw = json.loads(BINDING_PATH.read_text(encoding="utf-8"))
        allocations = {
            str(key): Decimal(str(value))
            for key, value in binding_raw["allocations"].items()
        }
        started_at = datetime.fromisoformat(binding_raw["bound_at"]).astimezone(UTC)
        portfolio_base = Decimal(str(binding_raw["balance"]))
        state = _load_state(
            allocations=allocations,
            portfolio_base=portfolio_base,
            started_at=started_at,
        )
        while True:
            started = time.monotonic()
            try:
                state = _sample(
                    service=service,
                    registry=registry,
                    state=state,
                    allocations=allocations,
                )
                _atomic_json(STATE_PATH, state)
            except Exception as error:
                ERROR_PATH.parent.mkdir(parents=True, exist_ok=True)
                with ERROR_PATH.open("a", encoding="utf-8") as stream:
                    stream.write(
                        f"{datetime.now(UTC).isoformat()} "
                        f"{type(error).__name__}: {error}\n"
                    )
            elapsed = time.monotonic() - started
            time.sleep(max(0.5, INTERVAL_SECONDS - elapsed))
    finally:
        client.close()


if __name__ == "__main__":
    main()
