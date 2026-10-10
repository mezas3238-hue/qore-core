"""Post-hoc MAX3 censoring analysis on the frozen nine-market V49 ledgers.

This module is deliberately outcome-aware ONLY AFTER replay completion: excluded
trade R values are *counterfactual independent simulations*, not fills. No
admission, ranking, risk, or trading decision imports this auditor.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    IDENTITY as V49_REPORT_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _portfolio_select,
)

IDENTITY = "QORE_SCALPER_A2_MAX3_COUNTERFACTUAL_OUTCOME_AUDIT_V1"
SESSIONS = frozenset(("ASIA", "LONDON", "NEW_YORK"))
Disposition = Literal["CHRONOLOGICAL_SELECTED", "EXCLUDED_COUNTERFACTUAL"]


def _trade_key(item: V49EconomicTrade) -> tuple[str, ...]:
    """Conservative unique simulated entry key; never silently dedupe fills."""
    return (
        item.symbol,
        item.session,
        item.operating_date,
        item.entry_at,
        item.entry_price,
        item.trigger_family,
        item.h1_state_basis,
    )


def _summary(trades: tuple[V49EconomicTrade, ...]) -> dict[str, Any]:
    values = tuple(Decimal(item.realized_gross_r) for item in trades)
    wins = tuple(value for value in values if value > 0)
    losses = tuple(value for value in values if value < 0)
    gp = sum(wins, Decimal(0))
    gl = -sum(losses, Decimal(0))
    return {
        "count": len(values),
        "wins": len(wins),
        "losses": len(losses),
        "flats": len(values) - len(wins) - len(losses),
        "total_gross_r": str(sum(values, Decimal(0))),
        "mean_gross_r": (
            str(sum(values, Decimal(0)) / len(values)) if values else None
        ),
        "gross_winning_r": str(gp),
        "gross_losing_r_magnitude": str(gl),
        "profit_factor": (str(gp / gl) if gl else None),
        "mean_winning_r": str(gp / len(wins)) if wins else None,
        "mean_losing_r": str(-gl / len(losses)) if losses else None,
        "median_planned_reward_r": (
            str(sorted(Decimal(item.planned_reward_r) for item in trades)[len(trades) // 2])
            if trades else None
        ),
        "stop_exits": sum(item.exit_reason == "STOP" for item in trades),
        "target_exits": sum(item.exit_reason == "TARGET" for item in trades),
        "session_exits": sum(item.exit_reason == "SESSION_EXIT" for item in trades),
        "same_bar_stop_target_ambiguity": sum(
            item.same_bar_stop_target_ambiguity for item in trades
        ),
    }


def _bucketed(trades: tuple[V49EconomicTrade, ...]) -> dict[str, Any]:
    dimensions: dict[str, dict[str, list[V49EconomicTrade]]] = {
        "session": defaultdict(list),
        "market": defaultdict(list),
        "trigger_family": defaultdict(list),
        "session_and_trigger": defaultdict(list),
    }
    for item in trades:
        dimensions["session"][item.session].append(item)
        dimensions["market"][item.symbol].append(item)
        dimensions["trigger_family"][item.trigger_family].append(item)
        dimensions["session_and_trigger"][
            f"{item.session}|{item.trigger_family}"
        ].append(item)
    return {
        label: {
            key: _summary(tuple(group))
            for key, group in sorted(rows.items())
        }
        for label, rows in dimensions.items()
    }


def _load_market_ledgers(
    root: Path, *, expected_markets: int
) -> tuple[V49EconomicTrade, ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-development-economics-trades.jsonl"))
    reports = sorted(root.rglob("capitalizer-*-v49-development-economics.json"))
    if expected_markets != 9 or len(paths) != expected_markets or len(reports) != 9:
        raise ValueError("MAX3 nine-market control requires exactly nine ledgers/reports")
    report_by_symbol: dict[str, dict[str, Any]] = {}
    for path in reports:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("V49 market report must be a JSON object")
        symbol = str(value.get("symbol", ""))
        if (
            not symbol
            or symbol in report_by_symbol
            or path.name != f"capitalizer-{symbol.lower()}-v49-development-economics.json"
            or value.get("identity") != V49_REPORT_IDENTITY
            or value.get("trader_certified") is not False
            or value.get("live_authorized") is not False
        ):
            raise ValueError("V49 report identity or safety contract mismatch")
        report_by_symbol[symbol] = value

    observed: dict[str, list[V49EconomicTrade]] = {}
    all_keys: set[tuple[str, ...]] = set()
    for path in paths:
        found = tuple(
            symbol
            for symbol in report_by_symbol
            if path.name == f"capitalizer-{symbol.lower()}-v49-development-economics-trades.jsonl"
        )
        if len(found) != 1:
            raise ValueError("V49 economic ledger filename/market mismatch")
        symbol = found[0]
        rows: list[V49EconomicTrade] = []
        with path.open(encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError(f"invalid V49 trade row at {path}:{lineno}")
                trade = V49EconomicTrade(**raw)
                if trade.symbol != symbol or trade.session not in SESSIONS:
                    raise ValueError("trade market/session mismatch")
                key = _trade_key(trade)
                if key in all_keys:
                    raise ValueError("duplicate or ambiguous V49 economic trade source")
                all_keys.add(key)
                rows.append(trade)
        if (
            symbol in observed
            or len(rows) != report_by_symbol[symbol].get("replayed_trades")
            or len(rows) + report_by_symbol[symbol].get("rejected_no_session_m1", -1)
            != report_by_symbol[symbol].get("candidate_opportunities")
            or any(row.session != report_by_symbol[symbol].get("session") for row in rows)
        ):
            raise ValueError("V49 economic trade/report census mismatch")
        observed[symbol] = rows
    if set(observed) != set(report_by_symbol):
        raise ValueError("nine-market reports and trades disagree")
    return tuple(row for symbol in sorted(observed) for row in observed[symbol])


def build_max3_counterfactual_report(
    control_root: Path,
    *,
    expected_markets: int = 9,
) -> dict[str, Any]:
    """Compare observed source-simulated R in chronological MAX3 vs censored cases.

    MAX3 is never relaxed or applied after seeing outcomes. An independent
    simulated outcome of an excluded opportunity is not a live fill nor an
    implementable ex-ante strategy.
    """

    rows = _load_market_ledgers(control_root, expected_markets=expected_markets)
    selected = tuple(item for _, item in _portfolio_select(rows))
    selected_keys = {_trade_key(item) for item in selected}
    if len(selected_keys) != len(selected):
        raise ValueError("MAX3 produced repeated source keys")
    excluded = tuple(item for item in rows if _trade_key(item) not in selected_keys)
    if len(selected) + len(excluded) != len(rows):
        raise ValueError("MAX3 accounting lost economic source trades")

    grouped: Counter[tuple[str, str]] = Counter()
    for item in selected:
        grouped[(item.session, item.operating_date)] += 1
    if any(value > 3 for value in grouped.values()):
        raise ValueError("MAX3 violated a session-date execution ceiling")
    return {
        "identity": IDENTITY,
        "source_simulated_economic_rows": len(rows),
        "max3_selected": len(selected),
        "max3_excluded_simulated_counterfactuals": len(excluded),
        "selected": _summary(selected),
        "excluded_counterfactual": _summary(excluded),
        "selected_by": _bucketed(selected),
        "excluded_counterfactual_by": _bucketed(excluded),
        "source_family_totals": dict(sorted(Counter(
            item.trigger_family for item in rows
        ).items())),
        "source_trades_already_simulated_prior_to_max3": True,
        "censored_outcomes_known_only_ex_post": True,
        "excluded_outcomes_are_not_executed_fills": True,
        "no_outcome_aware_reranking": True,
        "no_change_to_max3_or_strategy": True,
        "can_infer_ex_ante_policy_improvement": False,
        "provider_costs_bid_ask_commission_modeled": False,
        "trader_certified": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("control_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_max3_counterfactual_report(args.control_root)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "scalper-a2-v49-max3-counterfactual.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "identity": report["identity"],
        "source_simulated_economic_rows": report["source_simulated_economic_rows"],
        "max3_selected": report["max3_selected"],
        "max3_excluded_simulated_counterfactuals": (
            report["max3_excluded_simulated_counterfactuals"]
        ),
        "selected": report["selected"],
        "excluded_counterfactual": report["excluded_counterfactual"],
        "trader_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
