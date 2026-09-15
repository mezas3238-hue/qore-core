"""Preregistered Turtle Soup persistence candidate P1 replay."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from statistics import median

from turtle_soup_r5_economics import (
    FOLDS,
    Trade,
    censored_trade,
    closed_trade,
    concentration,
    directional,
    entry_session,
    excursions,
    fold_name,
    metrics,
)
from turtle_soup_r5_replay_core import MARKETS, OOS_START, Evaluation, Fill, Market, run_census

IDENTITY = "turtle-soup-persistence-candidate-p1"
POLICY = "P1_CONFIRM_NEXT_OPEN_2R_H3"
MIN_RISK_BPS = Decimal("4")
TARGET_R = Decimal("2")
HORIZON = 3


def serialize(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat(timespec="microseconds")
    if isinstance(value, Counter):
        return dict(value)
    raise TypeError(f"cannot serialize {type(value)!r}")


def digest(value: object) -> str:
    raw = json.dumps(
        value,
        default=serialize,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode()
    return sha256(raw).hexdigest()


def favorable_close(result: Evaluation, source_close: Decimal) -> bool:
    if result.fill is None:
        raise ValueError("fill required")
    threshold = max(result.fill.trigger, result.fill.entry) if result.fill.side == "long" else min(
        result.fill.trigger, result.fill.entry
    )
    return source_close > threshold if result.fill.side == "long" else source_close < threshold


def favorable_next_open(result: Evaluation, next_open: Decimal) -> bool:
    if result.fill is None:
        raise ValueError("fill required")
    return next_open > result.fill.trigger if result.fill.side == "long" else next_open < result.fill.trigger


def valid_stop_side(side: str, entry: Decimal, stop: Decimal) -> bool:
    return entry > stop if side == "long" else entry < stop


def candidate_fill(result: Evaluation, session_open: datetime, entry: Decimal) -> Fill:
    if result.fill is None:
        raise ValueError("fill required")
    return Fill(
        side=result.fill.side,
        entry=entry,
        trigger=result.fill.trigger,
        stop=result.fill.stop,
        fill_at=session_open,
        source_session=session_open,
        resolution="D1_OPEN:P1",
    )


def replay_candidate(market: Market, fill: Fill, source_index: int) -> Trade:
    risk = abs(fill.entry - fill.stop)
    if risk <= 0:
        raise AssertionError("P1 risk must be positive")
    target = fill.entry + TARGET_R * risk if fill.side == "long" else fill.entry - TARGET_R * risk
    mfe = Decimal(0)
    mae = Decimal(0)

    for offset in range(HORIZON):
        index = source_index + offset
        if index >= len(market.d1):
            return censored_trade(
                market.symbol, fill, POLICY, "insufficient-data", mfe, mae, offset
            )
        session = market.d1[index]
        if session.opened_at >= OOS_START:
            return censored_trade(
                market.symbol, fill, POLICY, "fresh-oos-embargo", mfe, mae, offset
            )
        path = market.m15_session(session)
        if path is None:
            return censored_trade(
                market.symbol, fill, POLICY, "data-resolution-limitation", mfe, mae, offset
            )

        for bar in path:
            if fill.side == "long":
                if bar.open <= fill.stop:
                    move = directional(fill.side, fill.entry, bar.open)
                    mae = max(mae, -move / risk if move < 0 else Decimal(0))
                    return closed_trade(
                        market.symbol,
                        fill,
                        POLICY,
                        bar.open,
                        bar.opened_at,
                        "gap-stop",
                        mfe,
                        mae,
                        offset + 1,
                    )
                if bar.open >= target:
                    mfe = max(mfe, TARGET_R)
                    return closed_trade(
                        market.symbol,
                        fill,
                        POLICY,
                        target,
                        bar.opened_at,
                        "target",
                        mfe,
                        mae,
                        offset + 1,
                    )
                stop_hit = bar.low <= fill.stop
                target_hit = bar.high >= target
            else:
                if bar.open >= fill.stop:
                    move = directional(fill.side, fill.entry, bar.open)
                    mae = max(mae, -move / risk if move < 0 else Decimal(0))
                    return closed_trade(
                        market.symbol,
                        fill,
                        POLICY,
                        bar.open,
                        bar.opened_at,
                        "gap-stop",
                        mfe,
                        mae,
                        offset + 1,
                    )
                if bar.open <= target:
                    mfe = max(mfe, TARGET_R)
                    return closed_trade(
                        market.symbol,
                        fill,
                        POLICY,
                        target,
                        bar.opened_at,
                        "target",
                        mfe,
                        mae,
                        offset + 1,
                    )
                stop_hit = bar.high >= fill.stop
                target_hit = bar.low <= target

            if stop_hit:
                mae = max(mae, Decimal(1))
                return closed_trade(
                    market.symbol,
                    fill,
                    POLICY,
                    fill.stop,
                    bar.opened_at,
                    "stop-first" if target_hit else "stop",
                    mfe,
                    mae,
                    offset + 1,
                )
            if target_hit:
                mfe = max(mfe, TARGET_R)
                return closed_trade(
                    market.symbol,
                    fill,
                    POLICY,
                    target,
                    bar.opened_at,
                    "target",
                    mfe,
                    mae,
                    offset + 1,
                )
            mfe, mae = excursions(fill.side, fill.entry, risk, bar, mfe, mae)

        if offset == HORIZON - 1:
            return closed_trade(
                market.symbol,
                fill,
                POLICY,
                session.close,
                session.closed_at,
                "time-exit",
                mfe,
                mae,
                HORIZON,
            )

    raise AssertionError("unresolved P1 replay")


def select_candidate(
    market: Market,
    result: Evaluation,
    source_index: int,
) -> tuple[str, Trade | None, Decimal | None]:
    if result.fill is None or result.context is None:
        raise ValueError("deterministic source fill required")

    probe_price, _, _, _, _ = entry_session(result.fill, result.context)
    if probe_price is not None:
        return "probe-stopped-source-session", None, None

    source_session = market.d1[source_index]
    if not favorable_close(result, source_session.close):
        return "persistence-close-fail", None, None

    entry_index = source_index + 1
    if entry_index >= len(market.d1):
        return "next-session-unavailable", None, None
    next_session = market.d1[entry_index]
    if next_session.opened_at >= OOS_START:
        return "next-session-oos-embargo", None, None
    if market.m15_session(next_session) is None:
        return "next-session-m15-unavailable", None, None
    if not favorable_next_open(result, next_session.open):
        return "overnight-reclaim-fail", None, None
    if not valid_stop_side(result.fill.side, next_session.open, result.fill.stop):
        return "invalid-structural-stop-side", None, None

    risk = abs(next_session.open - result.fill.stop)
    risk_bps = risk / next_session.open * Decimal(10000)
    if risk_bps < MIN_RISK_BPS:
        return "risk-bps-below-4", None, risk_bps

    fill = candidate_fill(result, next_session.opened_at, next_session.open)
    return "trade", replay_candidate(market, fill, entry_index), risk_bps


def gate_report(trades: list[Trade]) -> dict[str, object]:
    forward = [trade for trade in trades if fold_name(trade) is not None]
    primary = metrics(forward)
    gross = metrics(forward, "gross_r")
    stress = metrics(forward, "net_2bp_r")
    folds = {
        name: metrics([trade for trade in trades if fold_name(trade) == name])
        for name, _, _ in FOLDS
    }
    positive_folds = sum(
        isinstance(item["total_r"], Decimal) and item["total_r"] > 0
        for item in folds.values()
    )
    leave_one_out = {
        market: metrics([trade for trade in forward if trade.market != market])["total_r"]
        for market in MARKETS
    }
    concentrated = concentration(forward)
    market_forward = {
        market: metrics([trade for trade in forward if trade.market == market]) for market in MARKETS
    }
    side_forward = {
        side: metrics([trade for trade in forward if trade.side == side]) for side in ("long", "short")
    }
    positive_markets = sum(
        isinstance(item["total_r"], Decimal) and item["total_r"] > 0
        for item in market_forward.values()
    )
    both_sides_positive = all(
        isinstance(item["total_r"], Decimal) and item["total_r"] > 0
        for item in side_forward.values()
    )

    gate = {
        "forward_closed_trades_gte_30": primary["closed"] >= 30,
        "forward_expectancy_gt_0": isinstance(primary["mean_r"], Decimal) and primary["mean_r"] > 0,
        "forward_profit_factor_gt_1": isinstance(primary["profit_factor"], Decimal)
        and primary["profit_factor"] > 1,
        "positive_folds_gte_4_of_6": positive_folds >= 4,
        "stress_expectancy_gte_0": isinstance(stress["mean_r"], Decimal) and stress["mean_r"] >= 0,
        "leave_one_market_out_all_positive": all(
            isinstance(value, Decimal) and value > 0 for value in leave_one_out.values()
        ),
        "positive_gain_concentration_lte_50pct": bool(concentrated["pass"]),
        "both_sides_forward_total_positive": both_sides_positive,
        "positive_markets_gte_5_of_7": positive_markets >= 5,
        "causal_integrity_fail_closed": True,
    }
    return {
        "all_development": metrics(trades),
        "walk_forward": primary,
        "walk_forward_gross_before_cost": gross,
        "walk_forward_stress_2bp": stress,
        "positive_folds": positive_folds,
        "folds": folds,
        "leave_one_market_out_total_r": leave_one_out,
        "concentration": concentrated,
        "market_forward": market_forward,
        "side_forward": side_forward,
        "positive_markets": positive_markets,
        "advancement_gate": gate,
        "passes_advancement_gate": all(gate.values()),
        "exit_reasons": Counter(trade.exit_reason for trade in trades),
    }


def build_report(root: Path, software_sha: str) -> tuple[dict[str, object], list[Trade]]:
    markets = {symbol: Market(root, symbol) for symbol in MARKETS}
    evaluations, fills = run_census(markets, True)
    if len(fills) != 290:
        raise AssertionError(f"R5 source fill census drifted: {len(fills)}")
    unresolved_base = Counter(item.status for item in evaluations if item.status.startswith("tick-"))
    if unresolved_base:
        raise AssertionError(f"R5 causal base drifted: {unresolved_base}")

    selection: Counter[str] = Counter()
    trades: list[Trade] = []
    accepted_risk_bps: list[Decimal] = []
    rejected_risk_bps: list[Decimal] = []
    for evaluation, market, source_index in fills:
        status, trade, risk_bps = select_candidate(market, evaluation, source_index)
        selection[status] += 1
        if status == "trade":
            if trade is None or risk_bps is None:
                raise AssertionError("trade selection lost payload")
            trades.append(trade)
            accepted_risk_bps.append(risk_bps)
        elif status == "risk-bps-below-4" and risk_bps is not None:
            rejected_risk_bps.append(risk_bps)

    policy = gate_report(trades)
    passed = bool(policy["passes_advancement_gate"])
    verdict = "P1_DEVELOPMENT_GATE_PASS" if passed else "P1_PERSISTENCE_CANDIDATE_REJECTED"
    report: dict[str, object] = {
        "schema": "qore.trader_lab.turtle_soup.persistence_candidate_p1.v1",
        "research_identity": IDENTITY,
        "canonical_trader_code": "CODE_UNASSIGNED",
        "software_sha": software_sha,
        "source_fill_census": len(fills),
        "selection_census": selection,
        "candidate_trade_count": len(trades),
        "accepted_risk_bps_median": median(accepted_risk_bps) if accepted_risk_bps else None,
        "rejected_sub4_risk_bps_median": median(rejected_risk_bps) if rejected_risk_bps else None,
        "frozen_contract": {
            "virtual_probe": True,
            "persistence_close_beyond_trigger_and_original_fill": True,
            "entry": "next_provider_d1_open",
            "minimum_risk_bps": MIN_RISK_BPS,
            "target_r": TARGET_R,
            "horizon_d1_sessions": HORIZON,
            "same_m15_stop_target_policy": "STOP_FIRST_CONSERVATIVE",
            "trailing": False,
            "break_even": False,
            "reentry": False,
            "partial_exit": False,
        },
        "policy": policy,
        "fresh_oos_consumed": False,
        "fresh_oos_authorized": False,
        "candidate_freeze": None,
        "final_verdict": verdict,
    }
    report["report_digest_sha256"] = digest(report)
    return report, trades


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--software-sha", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--trades", type=Path, required=True)
    args = parser.parse_args()

    report, trades = build_report(args.input_root, args.software_sha)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, default=serialize, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    args.trades.write_text(
        json.dumps([asdict(trade) for trade in trades], default=serialize, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "final_verdict": report["final_verdict"],
                "candidate_trade_count": report["candidate_trade_count"],
                "selection_census": report["selection_census"],
                "report_digest_sha256": report["report_digest_sha256"],
            },
            default=serialize,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
