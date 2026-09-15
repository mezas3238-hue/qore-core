"""Full forensic ledger for the consumed ICT Turtle Soup R2 Forex holdout."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.ict_turtle_soup_r2_all_session import (
    LiquiditySide,
    Side,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r2_forex_holdout import (
    EVAL_CLOSE,
    EVAL_OPEN,
    EXPECTED_SYMBOLS,
    MIN_PROJECTED_R,
    NY,
    Trade,
    _cisd_threshold,
    _event_end_index,
    _find_confirmation,
    _json_trade,
    _load_evidence,
    _session_bucket,
    _target_pool,
    build_pools,
    first_sweeps,
    replay_symbol,
)

FORENSIC_IDENTITY = "ICT_TURTLE_SOUP_R2_FOREX_FULL_LEDGER_FORENSICS_001"
PARENT_REPORT_SHA256 = (
    "b70ae358fb9c895f281a8c1505b7b7257b4ff26a5ed6dcba2bcd41d71c5c6613"
)
PARENT_TRADES_SHA256 = (
    "cfa3c635b5657af1d3de5b5dd1bbcd3a97b2bd84a44501f641bf706a5f94a01c"
)
EXPECTED_FUNNEL = {
    "ambiguous-multi-pool-sweep": 6933,
    "event-data-gap": 334,
    "ignored-position-open": 3286,
    "insufficient-projected-r": 6350,
    "invalid-geometry": 3,
    "no-causal-entry": 42,
    "no-cisd": 3940,
    "no-opposing-series": 799,
    "no-opposing-target": 32,
    "no-reclaim": 959,
    "swept-pool-events": 27840,
    "swept-pools": 38047,
    "trade": 5162,
}
NON_EXECUTION_REASONS = {
    key
    for key in EXPECTED_FUNNEL
    if key not in {"swept-pool-events", "swept-pools", "trade"}
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_exact(root: Path, name: str) -> Path:
    matches = sorted(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, found {len(matches)}")
    return matches[0]


def _quarter(moment: Any) -> str:
    local = moment.astimezone(NY)
    quarter = ((local.month - 1) // 3) + 1
    return f"{local.year}-Q{quarter}"


def _pool_payload(pool: Any) -> dict[str, Any]:
    return {
        "pool_id": pool.pool_id,
        "family": pool.family,
        "side": pool.side.value,
        "level": str(pool.level),
        "known_at": pool.known_at.astimezone(UTC).isoformat(),
    }


def _base_event(symbol: str, sweep_at: Any, pools: list[Any]) -> dict[str, Any]:
    local = sweep_at.astimezone(NY)
    return {
        "symbol": symbol,
        "sweep_at": sweep_at.astimezone(UTC).isoformat(),
        "sweep_at_ny": local.isoformat(),
        "ny_hour": local.hour,
        "session_bucket": _session_bucket(sweep_at),
        "year": local.year,
        "quarter": _quarter(sweep_at),
        "swept_pool_count": len(pools),
        "swept_pools": [_pool_payload(pool) for pool in pools],
    }


def _trade_outcome(trade: Trade) -> str:
    if trade.primary_net_r > 0:
        return "winner"
    if trade.primary_net_r < 0:
        return "loser"
    return "flat"


def _classify_nontrade(
    *,
    evidence: Any,
    pools: Any,
    first: Any,
    group_ids: Any,
    by_id: Any,
    index_by_time: Any,
    sweep_at: Any,
    next_available: Any,
) -> dict[str, Any]:
    selected = [by_id[pool_id] for pool_id in group_ids]
    event = _base_event(evidence.symbol, sweep_at, selected)
    event["executed"] = False
    event["outcome"] = "not-executed"

    if len(group_ids) != 1:
        event["terminal_reason"] = "ambiguous-multi-pool-sweep"
        return event

    pool = selected[0]
    side = Side.LONG if pool.side is LiquiditySide.SELL_SIDE else Side.SHORT
    event["side"] = side.value
    event["swept_pool_id"] = pool.pool_id
    event["swept_family"] = pool.family

    if sweep_at < next_available:
        event["terminal_reason"] = "ignored-position-open"
        event["position_available_at"] = next_available.astimezone(UTC).isoformat()
        return event

    bars = evidence.bars
    sweep_index = index_by_time[sweep_at]
    end_index = _event_end_index(bars, sweep_index)
    threshold = _cisd_threshold(
        bars,
        sweep_index=sweep_index,
        pool=pool,
        side=side,
    )
    if threshold is None:
        event["terminal_reason"] = "no-opposing-series"
        return event
    event["cisd_threshold"] = str(threshold)

    reclaim_index, cisd_index, data_gap = _find_confirmation(
        bars,
        sweep_index=sweep_index,
        end_index=end_index,
        pool=pool,
        side=side,
        threshold=threshold,
    )
    if reclaim_index is not None:
        event["reclaim_at"] = bars[reclaim_index].closed_at.astimezone(UTC).isoformat()
    if data_gap:
        event["terminal_reason"] = "event-data-gap"
        return event
    if reclaim_index is None:
        event["terminal_reason"] = "no-reclaim"
        return event
    if cisd_index is None:
        event["terminal_reason"] = "no-cisd"
        return event

    event["cisd_at"] = bars[cisd_index].closed_at.astimezone(UTC).isoformat()
    entry_index = cisd_index + 1
    if (
        entry_index >= end_index
        or bars[cisd_index].closed_at != bars[entry_index].opened_at
    ):
        event["terminal_reason"] = "no-causal-entry"
        return event

    tick = Decimal(1).scaleb(-evidence.digits)
    entry_bar = bars[entry_index]
    entry = entry_bar.open
    adverse = bars[sweep_index : cisd_index + 1]
    if side is Side.LONG:
        stop = min(bar.low for bar in adverse) - tick
    else:
        stop = max(bar.high for bar in adverse) + tick

    event["candidate_entry_at"] = entry_bar.opened_at.astimezone(UTC).isoformat()
    event["candidate_entry"] = str(entry)
    event["candidate_stop"] = str(stop)

    target = _target_pool(
        pools,
        first,
        swept=pool,
        side=side,
        entry=entry,
        entry_at=entry_bar.opened_at,
    )
    if target is None:
        event["terminal_reason"] = "no-opposing-target"
        return event

    event["candidate_target_pool"] = _pool_payload(target)
    event["candidate_target"] = str(target.level)
    risk = entry - stop if side is Side.LONG else stop - entry
    reward = target.level - entry if side is Side.LONG else entry - target.level
    event["candidate_risk"] = str(risk)
    event["candidate_reward"] = str(reward)
    if risk <= 0 or reward <= 0:
        event["terminal_reason"] = "invalid-geometry"
        return event

    projected_r = reward / risk
    event["projected_r"] = str(projected_r)
    if projected_r < MIN_PROJECTED_R:
        event["terminal_reason"] = "insufficient-projected-r"
        return event

    raise AssertionError(
        f"event {evidence.symbol} {sweep_at.isoformat()} should have executed"
    )


def _executed_event(trade: Trade) -> dict[str, Any]:
    payload = _json_trade(trade)
    payload.update(
        {
            "executed": True,
            "outcome": _trade_outcome(trade),
            "terminal_reason": "trade",
            "session_bucket": _session_bucket(trade.entry_at),
            "ny_hour": trade.entry_at.astimezone(NY).hour,
            "year": trade.entry_at.astimezone(NY).year,
            "quarter": _quarter(trade.entry_at),
        }
    )
    return payload


def _increment(
    counter: dict[str, Counter[str]], dimension: str, value: Any
) -> None:
    counter[dimension][str(value)] += 1


def _summaries(events: list[dict[str, Any]]) -> dict[str, Any]:
    dimensions: dict[str, Counter[str]] = defaultdict(Counter)
    for event in events:
        _increment(dimensions, "outcome", event["outcome"])
        _increment(dimensions, "terminal_reason", event["terminal_reason"])
        _increment(dimensions, "symbol", event["symbol"])
        _increment(dimensions, "session_bucket", event["session_bucket"])
        _increment(dimensions, "ny_hour", event["ny_hour"])
        _increment(dimensions, "year", event["year"])
        _increment(dimensions, "quarter", event["quarter"])
        side = event.get("side")
        if side is not None:
            _increment(dimensions, "side", side)
        swept_family = event.get("swept_family")
        if swept_family is not None:
            _increment(dimensions, "swept_family", swept_family)
        target_family = event.get("target_family")
        if target_family is not None:
            _increment(dimensions, "target_family", target_family)
        exit_reason = event.get("exit_reason")
        if exit_reason is not None:
            _increment(dimensions, "exit_reason", exit_reason)
    return {
        key: dict(sorted(value.items()))
        for key, value in sorted(dimensions.items())
    }


def _outcome_by_symbol(events: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Counter[str]] = defaultdict(Counter)
    for event in events:
        result[event["symbol"]][event["outcome"]] += 1
    return {
        symbol: dict(sorted(counts.items()))
        for symbol, counts in sorted(result.items())
    }


def _reason_by_symbol(non_executed: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Counter[str]] = defaultdict(Counter)
    for event in non_executed:
        result[event["symbol"]][event["terminal_reason"]] += 1
    return {
        symbol: dict(sorted(counts.items()))
        for symbol, counts in sorted(result.items())
    }


def _load_parent(
    parent_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report_path = _find_exact(parent_root, "report.json")
    trades_path = _find_exact(parent_root, "trades.json")
    if _sha256(report_path) != PARENT_REPORT_SHA256:
        raise ValueError("parent report digest mismatch")
    if _sha256(trades_path) != PARENT_TRADES_SHA256:
        raise ValueError("parent trades digest mismatch")
    return (
        json.loads(report_path.read_text()),
        json.loads(trades_path.read_text()),
    )


def run(source_root: Path, parent_root: Path, output: Path) -> dict[str, Any]:
    parent_report, parent_trades = _load_parent(parent_root)
    if parent_report["trade_count"] != EXPECTED_FUNNEL["trade"]:
        raise ValueError("parent trade count drift")
    if parent_report["funnel"] != EXPECTED_FUNNEL:
        raise ValueError("parent funnel drift")

    files = sorted(source_root.rglob("market-evidence.json"))
    evidence_items = [_load_evidence(path) for path in files]
    symbols = {item.symbol for item in evidence_items}
    if symbols != EXPECTED_SYMBOLS:
        raise ValueError(f"retained symbol set mismatch: {sorted(symbols)}")

    generated_trades: list[Trade] = []
    generated_funnel: Counter[str] = Counter()
    events: list[dict[str, Any]] = []

    for evidence in sorted(evidence_items, key=lambda item: item.symbol):
        symbol_trades, symbol_funnel, _metadata = replay_symbol(evidence)
        generated_trades.extend(symbol_trades)
        generated_funnel.update(symbol_funnel)
        trade_by_sweep = {trade.sweep_at: trade for trade in symbol_trades}
        if len(trade_by_sweep) != len(symbol_trades):
            raise ValueError(f"duplicate executed sweep timestamp for {evidence.symbol}")

        pools = build_pools(evidence)
        by_id = {pool.pool_id: pool for pool in pools}
        first, groups = first_sweeps(evidence.bars, pools)
        index_by_time = {
            bar.opened_at: index for index, bar in enumerate(evidence.bars)
        }
        next_available = EVAL_OPEN

        for sweep_at in sorted(groups):
            if not EVAL_OPEN <= sweep_at < EVAL_CLOSE:
                continue
            group_ids = groups[sweep_at]
            trade = trade_by_sweep.get(sweep_at)
            if len(group_ids) != 1:
                if trade is not None:
                    raise AssertionError("ambiguous sweep cannot execute")
                event = _classify_nontrade(
                    evidence=evidence,
                    pools=pools,
                    first=first,
                    group_ids=group_ids,
                    by_id=by_id,
                    index_by_time=index_by_time,
                    sweep_at=sweep_at,
                    next_available=next_available,
                )
                events.append(event)
                continue

            if sweep_at < next_available:
                if trade is not None:
                    raise AssertionError("position-open event cannot execute")
                event = _classify_nontrade(
                    evidence=evidence,
                    pools=pools,
                    first=first,
                    group_ids=group_ids,
                    by_id=by_id,
                    index_by_time=index_by_time,
                    sweep_at=sweep_at,
                    next_available=next_available,
                )
                events.append(event)
                continue

            if trade is not None:
                event = _executed_event(trade)
                events.append(event)
                next_available = max(next_available, trade.exit_at)
                continue

            event = _classify_nontrade(
                evidence=evidence,
                pools=pools,
                first=first,
                group_ids=group_ids,
                by_id=by_id,
                index_by_time=index_by_time,
                sweep_at=sweep_at,
                next_available=next_available,
            )
            events.append(event)

    generated_trades.sort(key=lambda trade: (trade.entry_at, trade.symbol))
    generated_trade_payload = [_json_trade(trade) for trade in generated_trades]
    if generated_trade_payload != parent_trades:
        raise ValueError("generated executed trade ledger differs from parent artifact")
    if dict(generated_funnel) != EXPECTED_FUNNEL:
        raise ValueError(
            "generated funnel mismatch: "
            f"{dict(sorted(generated_funnel.items()))}"
        )

    events.sort(key=lambda event: (event["sweep_at"], event["symbol"]))
    for index, event in enumerate(events, start=1):
        event["event_id"] = f"ICTTSR2-FX-{index:05d}"

    winners = [event for event in events if event["outcome"] == "winner"]
    losers = [event for event in events if event["outcome"] == "loser"]
    flats = [event for event in events if event["outcome"] == "flat"]
    non_executed = [
        event for event in events if event["outcome"] == "not-executed"
    ]

    reason_counts = Counter(
        event["terminal_reason"] for event in non_executed
    )
    expected_non_execution = {
        key: EXPECTED_FUNNEL[key] for key in sorted(NON_EXECUTION_REASONS)
    }
    if dict(sorted(reason_counts.items())) != expected_non_execution:
        raise ValueError("non-execution reason ledger mismatch")
    if len(events) != EXPECTED_FUNNEL["swept-pool-events"]:
        raise ValueError("event ledger count mismatch")
    if len(winners) != 1486 or len(losers) != 3676 or flats:
        raise ValueError("executed outcome reconciliation failed")
    if len(non_executed) != 22678:
        raise ValueError("non-executed ledger count mismatch")

    output.mkdir(parents=True, exist_ok=True)
    payloads = {
        "event-ledger.json": events,
        "winners.json": winners,
        "losers.json": losers,
        "flats.json": flats,
        "non-executed.json": non_executed,
    }
    for name, payload in payloads.items():
        (output / name).write_text(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )

    report = {
        "schema": "qore.ict_turtle_soup_r2_forex_full_ledger_forensics.v1",
        "identity": FORENSIC_IDENTITY,
        "parent_holdout_run": 35030690033,
        "parent_holdout_head": "3cb3d789eb73aa346affad7a80fe5214942ca992",
        "parent_holdout_artifact": 10420839755,
        "parent_structural_forensics_run": 35031070205,
        "consumed_evidence_only": True,
        "fresh_oos_accessed": False,
        "rule_change_authorized": False,
        "event_count": len(events),
        "swept_pool_count": EXPECTED_FUNNEL["swept-pools"],
        "executed_trade_count": len(winners) + len(losers) + len(flats),
        "winner_count": len(winners),
        "loser_count": len(losers),
        "flat_count": len(flats),
        "non_executed_count": len(non_executed),
        "non_execution_rate": str(
            Decimal(len(non_executed)) / Decimal(len(events))
        ),
        "execution_rate": str(
            Decimal(len(winners) + len(losers) + len(flats))
            / Decimal(len(events))
        ),
        "parent_funnel": EXPECTED_FUNNEL,
        "non_execution_reasons": dict(sorted(reason_counts.items())),
        "all_event_dimensions": _summaries(events),
        "executed_outcome_by_symbol": _outcome_by_symbol(
            winners + losers + flats
        ),
        "non_execution_reason_by_symbol": _reason_by_symbol(non_executed),
        "governance": {
            "candidate_selection_authorized": False,
            "filter_selection_authorized": False,
            "counterfactual_pnl_on_abstentions": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    report_path = output / "full-ledger-report.json"
    report_path.write_text(
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return report


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: python -m "
            "qore.infrastructure.trader_lab.ict_turtle_soup_r2_forex_full_ledger "
            "<retained-market-evidence-root> "
            "<parent-holdout-artifact-root> <output>"
        )
    report = run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    print(
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
