from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.ctrader_demo_free_binding import discover_free_account_binding
from qore.infrastructure.ctrader_demo_free_position_service import CTraderDemoFreePositionService
from qore.infrastructure.ctrader_demo_free_sink import credentials_from_environment
from qore.infrastructure.ctrader_demo_trade_registry import CTraderDemoTradeRegistry
from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.kernel.result import Failure

ROOT = Path(r"C:\QORE_CTRADER_DEMO_FREE")
STATE_DIR = ROOT / "var" / "ctrader_demo_free"
REPORT_PATH = STATE_DIR / "performance.json"
TEXT_PATH = ROOT / "artifacts" / "ctrader_demo_free_performance.txt"
EVENTS_PATH = STATE_DIR / "events.jsonl"


def money(raw: Any, digits: Any) -> Decimal:
    d = int(digits or 0)
    return Decimal(int(raw or 0)).scaleb(-d)


def request(client: Any, name: str, fields: dict[str, object], msg_id: str) -> object:
    result = client.request(name, fields, client_msg_id=msg_id, timeout_seconds=15.0)
    if isinstance(result, Failure):
        raise RuntimeError(str(result.error))
    return result.value


def windows(start: datetime, end: datetime):
    cursor = start
    while cursor < end:
        nxt = min(end, cursor + timedelta(days=1))
        yield cursor, nxt
        cursor = nxt


def label_trader(label: Any) -> str | None:
    if not isinstance(label, str) or not label.startswith("QORE:"):
        return None
    raw = label.split(":", 1)[1]
    try:
        return TraderLineage(raw).value
    except ValueError:
        return None


def event_counts() -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    if not EVENTS_PATH.exists():
        return {}
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") != "CTRADER_DEMO_FREE_SUBMIT":
            continue
        trader = str(row.get("trader", ""))
        if not trader:
            continue
        out[trader]["signal_requests"] += 1
        state = str(row.get("state", "UNKNOWN"))
        out[trader][state.lower()] += 1
    return {k: dict(v) for k, v in out.items()}


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def drawdown(rows: list[tuple[datetime, Decimal]]) -> Decimal:
    cumulative = Decimal("0")
    peak = Decimal("0")
    worst = Decimal("0")
    for _, pnl in sorted(rows):
        cumulative += pnl
        peak = max(peak, cumulative)
        worst = max(worst, peak - cumulative)
    return worst


def main() -> None:
    credentials = credentials_from_environment()
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        binding = discover_free_account_binding(client)
        position_service = CTraderDemoFreePositionService(
            client=client,
            configuration=binding.configuration,
        )
        registry = CTraderDemoTradeRegistry(STATE_DIR / "trade-registry.json")
        account = position_service.account_snapshot()
        open_positions = position_service.positions()
        open_ids = {item.position_id for item in open_positions}

        binding_raw = json.loads((STATE_DIR / "binding.json").read_text(encoding="utf-8"))
        started = datetime.fromisoformat(binding_raw["bound_at"]).astimezone(UTC)
        now = datetime.now(UTC)
        allocations = {
            str(k): Decimal(str(v)) for k, v in binding_raw.get("allocations", {}).items()
        }
        equity_state: dict[str, object] = {}
        equity_path = STATE_DIR / "equity-drawdown.json"
        if equity_path.exists():
            try:
                raw_equity = json.loads(equity_path.read_text(encoding="utf-8"))
                if raw_equity.get("schema") == "qore.ctrader-demo.equity-drawdown.v1":
                    equity_state = raw_equity
            except (OSError, ValueError, json.JSONDecodeError):
                equity_state = {}
        excursions = equity_state.get("position_excursions", {})
        if not isinstance(excursions, dict):
            excursions = {}
        sampled_traders = equity_state.get("traders", {})
        if not isinstance(sampled_traders, dict):
            sampled_traders = {}
        sampled_portfolio = equity_state.get("portfolio", {})
        if not isinstance(sampled_portfolio, dict):
            sampled_portfolio = {}

        orders: dict[int, object] = {}
        for left, right in windows(started - timedelta(minutes=1), now):
            response = request(
                client,
                "ProtoOAOrderListReq",
                {
                    "ctidTraderAccountId": credentials.ctid_trader_account_id,
                    "fromTimestamp": int(left.timestamp() * 1000),
                    "toTimestamp": int(right.timestamp() * 1000),
                },
                f"qore-demo-report-orders-{int(left.timestamp())}",
            )
            for item in tuple(getattr(response, "order", ())):
                orders[int(getattr(item, "orderId"))] = item

        order_trader: dict[int, str] = {}
        position_trader: dict[int, str] = {}
        submitted_orders: dict[str, set[int]] = defaultdict(set)
        for oid, order in orders.items():
            trade = getattr(order, "tradeData", None)
            trader = label_trader(getattr(trade, "label", None) if trade is not None else None)
            if trader is None:
                continue
            order_trader[oid] = trader
            pid = int(getattr(order, "positionId", 0) or 0)
            if pid > 0:
                position_trader[pid] = trader
            if not bool(getattr(order, "closingOrder", False)):
                submitted_orders[trader].add(oid)

        deals: dict[int, object] = {}
        for left, right in windows(started - timedelta(minutes=1), now):
            response = request(
                client,
                "ProtoOADealListReq",
                {
                    "ctidTraderAccountId": credentials.ctid_trader_account_id,
                    "fromTimestamp": int(left.timestamp() * 1000),
                    "toTimestamp": int(right.timestamp() * 1000),
                    "maxRows": 1000,
                },
                f"qore-demo-report-deals-{int(left.timestamp())}",
            )
            for item in tuple(getattr(response, "deal", ())):
                deals[int(getattr(item, "dealId"))] = item

        per_position: dict[int, dict[str, object]] = {}
        for deal in deals.values():
            pid = int(getattr(deal, "positionId", 0) or 0)
            oid = int(getattr(deal, "orderId", 0) or 0)
            trader = order_trader.get(oid) or position_trader.get(pid)
            if trader is None or pid <= 0:
                continue
            position_trader.setdefault(pid, trader)
            rec = per_position.setdefault(
                pid,
                {
                    "trader": trader,
                    "pnl": Decimal("0"),
                    "first_at": None,
                    "last_at": None,
                    "has_close": False,
                    "deal_count": 0,
                },
            )
            ts_raw = int(getattr(deal, "executionTimestamp", 0) or 0)
            ts = datetime.fromtimestamp(ts_raw / 1000, tz=UTC) if ts_raw > 0 else now
            rec["first_at"] = ts if rec["first_at"] is None else min(rec["first_at"], ts)
            rec["last_at"] = ts if rec["last_at"] is None else max(rec["last_at"], ts)
            rec["deal_count"] = int(rec["deal_count"]) + 1

            close = None
            has_field = getattr(deal, "HasField", None)
            if callable(has_field):
                try:
                    if has_field("closePositionDetail"):
                        close = getattr(deal, "closePositionDetail", None)
                except ValueError:
                    close = None
            if close is not None:
                d = getattr(close, "moneyDigits", getattr(deal, "moneyDigits", 0))
                contribution = (
                    money(getattr(close, "grossProfit", 0), d)
                    + money(getattr(close, "swap", 0), d)
                    + money(getattr(close, "commission", 0), d)
                    + money(getattr(close, "pnlConversionFee", 0), d)
                )
                rec["has_close"] = True
            else:
                contribution = money(
                    getattr(deal, "commission", 0),
                    getattr(deal, "moneyDigits", 0),
                )
            rec["pnl"] = Decimal(rec["pnl"]) + contribution

        current_open_by_trader: dict[str, int] = defaultdict(int)
        for pos in open_positions:
            current_open_by_trader[pos.trader_id.value] += 1
            position_trader[pos.position_id] = pos.trader_id.value

        event_stats = event_counts()
        trader_rows: dict[str, dict[str, object]] = {}
        all_closed: list[tuple[datetime, Decimal]] = []
        all_r_rows: list[tuple[datetime, Decimal]] = []
        all_pnls: list[Decimal] = []
        all_durations: list[Decimal] = []
        total_realized = Decimal("0")
        total_gross_profit = Decimal("0")
        total_gross_loss = Decimal("0")

        # Binding allocations are the source of truth for the seven active
        # cTrader DEMO traders. Do not report dormant TraderLineage members.
        for name in allocations:
            positions = [
                (pid, rec) for pid, rec in per_position.items() if rec["trader"] == name
            ]
            closed_items = [
                (pid, rec)
                for pid, rec in positions
                if bool(rec["has_close"]) and pid not in open_ids
            ]
            closed = [rec for _, rec in closed_items]
            closed_rows = [
                (rec["last_at"], Decimal(rec["pnl"]))
                for rec in closed
                if isinstance(rec["last_at"], datetime)
            ]
            pnls = [Decimal(rec["pnl"]) for rec in closed]
            durations = [
                Decimal(
                    str(
                        max(
                            0.0,
                            (rec["last_at"] - rec["first_at"]).total_seconds(),
                        )
                    )
                )
                for rec in closed
                if isinstance(rec["first_at"], datetime)
                and isinstance(rec["last_at"], datetime)
            ]
            r_rows: list[tuple[datetime, Decimal]] = []
            mae_usd_values: list[Decimal] = []
            mfe_usd_values: list[Decimal] = []
            mae_r_values: list[Decimal] = []
            mfe_r_values: list[Decimal] = []
            for pid, rec in closed_items:
                last_at = rec["last_at"]
                risk = sum(
                    (
                        Decimal(leg.requested_stop_risk)
                        for leg in registry.entries_by_position(pid)
                        if leg.trader == name
                        and Decimal(leg.requested_stop_risk) > 0
                    ),
                    Decimal("0"),
                )
                if isinstance(last_at, datetime) and risk > 0:
                    r_rows.append((last_at, Decimal(rec["pnl"]) / risk))
                excursion = excursions.get(str(pid))
                if isinstance(excursion, dict):
                    minimum = Decimal(
                        str(excursion.get("min_unrealized_pnl", "0"))
                    )
                    maximum = Decimal(
                        str(excursion.get("max_unrealized_pnl", "0"))
                    )
                    mae = max(Decimal("0"), -minimum)
                    mfe = max(Decimal("0"), maximum)
                    mae_usd_values.append(mae)
                    mfe_usd_values.append(mfe)
                    if risk > 0:
                        mae_r_values.append(mae / risk)
                        mfe_r_values.append(mfe / risk)
            r_values = [value for _, value in r_rows]
            realized = sum(pnls, Decimal("0"))
            total_realized += realized
            all_closed.extend(closed_rows)
            all_r_rows.extend(r_rows)
            all_pnls.extend(pnls)
            all_durations.extend(durations)
            gp = sum((p for p in pnls if p > 0), Decimal("0"))
            gl = -sum((p for p in pnls if p < 0), Decimal("0"))
            total_gross_profit += gp
            total_gross_loss += gl
            closed_trade_dd = drawdown(closed_rows)
            dd_r = drawdown(r_rows)
            sampled = sampled_traders.get(name)
            sampled_dd = (
                Decimal(str(sampled.get("max_drawdown", "0")))
                if isinstance(sampled, dict)
                else Decimal("0")
            )
            dd = max(closed_trade_dd, sampled_dd)
            allocation = allocations.get(name, Decimal("0"))
            pf = None if gl == 0 else gp / gl
            events = event_stats.get(name, {})
            trader_rows[name] = {
                "assigned_capital": format(allocation, "f"),
                "signal_requests": int(events.get("signal_requests", 0)),
                "submitted_requests": int(events.get("submitted", 0)),
                "broker_orders": len(submitted_orders.get(name, set())),
                "filled_positions": len(positions),
                "closed_trades": len(closed),
                "open_positions": int(current_open_by_trader.get(name, 0)),
                "wins": sum(1 for p in pnls if p > 0),
                "losses": sum(1 for p in pnls if p < 0),
                "breakeven": sum(1 for p in pnls if p == 0),
                "net_profit": format(realized, "f"),
                "gross_profit": format(gp, "f"),
                "gross_loss": format(gl, "f"),
                "profit_factor": None if pf is None else format(pf, ".8f"),
                "win_rate": None if not pnls else format(
                    Decimal(sum(1 for p in pnls if p > 0)) / Decimal(len(pnls)), ".6f"
                ),
                "average_closed_trade": None if not pnls else format(
                    realized / Decimal(len(pnls)), "f"
                ),
                "expectancy": None if not pnls else format(
                    realized / Decimal(len(pnls)), "f"
                ),
                "largest_win": None if not pnls else format(max(pnls), "f"),
                "largest_loss": None if not pnls else format(min(pnls), "f"),
                "average_duration_seconds": None if not durations else format(
                    sum(durations, Decimal("0")) / Decimal(len(durations)), "f"
                ),
                "total_r": None if not r_values else format(
                    sum(r_values, Decimal("0")), ".8f"
                ),
                "average_r": None if not r_values else format(
                    sum(r_values, Decimal("0")) / Decimal(len(r_values)), ".8f"
                ),
                "max_drawdown_r": None if not r_values else format(dd_r, ".8f"),
                "closed_trade_max_drawdown": format(closed_trade_dd, "f"),
                "max_drawdown": format(dd, "f"),
                "max_drawdown_pct_allocated": None if allocation <= 0 else format(
                    (dd / allocation) * Decimal("100"), ".6f"
                ),
                "average_mae_usd": None if not mae_usd_values else format(
                    sum(mae_usd_values, Decimal("0"))
                    / Decimal(len(mae_usd_values)),
                    "f",
                ),
                "average_mfe_usd": None if not mfe_usd_values else format(
                    sum(mfe_usd_values, Decimal("0"))
                    / Decimal(len(mfe_usd_values)),
                    "f",
                ),
                "largest_mae_usd": None if not mae_usd_values else format(
                    max(mae_usd_values), "f"
                ),
                "largest_mfe_usd": None if not mfe_usd_values else format(
                    max(mfe_usd_values), "f"
                ),
                "average_mae_r": None if not mae_r_values else format(
                    sum(mae_r_values, Decimal("0")) / Decimal(len(mae_r_values)),
                    ".8f",
                ),
                "average_mfe_r": None if not mfe_r_values else format(
                    sum(mfe_r_values, Decimal("0")) / Decimal(len(mfe_r_values)),
                    ".8f",
                ),
            }

        portfolio_dd = drawdown(all_closed)
        portfolio_dd_r = drawdown(all_r_rows)
        portfolio_pf = (
            None
            if total_gross_loss == 0
            else total_gross_profit / total_gross_loss
        )
        portfolio_wins = sum(1 for pnl in all_pnls if pnl > 0)
        payload = {
            "schema": "qore.ctrader-demo.performance.v1",
            "account_observation_started_at": started.isoformat(),
            "observed_at": now.isoformat(),
            "account": {
                "balance": format(account.balance, "f"),
                "equity": format(account.equity, "f"),
                "net_unrealized_pnl": format(account.net_unrealized_pnl, "f"),
                "open_positions": len(open_positions),
            },
            "portfolio": {
                "realized_net_profit": format(total_realized, "f"),
                "gross_profit": format(total_gross_profit, "f"),
                "gross_loss": format(total_gross_loss, "f"),
                "profit_factor": (
                    None if portfolio_pf is None else format(portfolio_pf, ".8f")
                ),
                "closed_trades": sum(
                    int(row["closed_trades"]) for row in trader_rows.values()
                ),
                "open_positions": len(open_positions),
                "win_rate": None if not all_pnls else format(
                    Decimal(portfolio_wins) / Decimal(len(all_pnls)), ".6f"
                ),
                "expectancy": None if not all_pnls else format(
                    total_realized / Decimal(len(all_pnls)), "f"
                ),
                "average_duration_seconds": None if not all_durations else format(
                    sum(all_durations, Decimal("0")) / Decimal(len(all_durations)),
                    "f",
                ),
                "total_r": None if not all_r_rows else format(
                    sum((value for _, value in all_r_rows), Decimal("0")),
                    ".8f",
                ),
                "average_r": None if not all_r_rows else format(
                    sum((value for _, value in all_r_rows), Decimal("0"))
                    / Decimal(len(all_r_rows)),
                    ".8f",
                ),
                "max_drawdown": format(portfolio_dd, "f"),
                "max_drawdown_r": (
                    None if not all_r_rows else format(portfolio_dd_r, ".8f")
                ),
            },
            "traders": trader_rows,
        }
        atomic_json(REPORT_PATH, payload)

        lines = [
            "QORE cTrader DEMO FREE",
            f"Observed: {now.isoformat()}",
            f"Balance: {account.balance}  Equity: {account.equity}  Unrealized: {account.net_unrealized_pnl}",
            f"Portfolio realized: {total_realized}  Closed: {payload['portfolio']['closed_trades']}  DD: {portfolio_dd}",
            "",
        ]
        for name, row in trader_rows.items():
            lines.append(
                f"{name}: signals={row['signal_requests']} orders={row['broker_orders']} "
                f"closed={row['closed_trades']} open={row['open_positions']} "
                f"net={row['net_profit']} PF={row['profit_factor']} DD={row['max_drawdown']}"
            )
        TEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
        TEXT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("CTRADER_DEMO_PERFORMANCE_REPORT_OK")
    finally:
        client.close()


if __name__ == "__main__":
    main()
