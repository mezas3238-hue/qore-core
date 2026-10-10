"""Read-only, hindsight-only MFE/MAE audit on frozen V49 native-M1 replay.

M1 intrabar order is UNKNOWN. Whole exit-bar high/low are OBSERVED bounds,
not executable profit. Pre-terminal extrema are separated to avoid attributing
a price movement after a STOP/TARGET within that same M1 to an active trade.

Research only: NO entry filter, strategy changes, MT5, or certification.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    IDENTITY as V49_REPORT_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _portfolio_select,
)

IDENTITY = "QORE_SCALPER_A2_V49_NATIVE_M1_MFE_MAE_V1"


def _dt(raw: str) -> datetime:
    value = datetime.fromisoformat(raw)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("MFE/MAE audit requires tz-aware time")
    return value


def _trade_key(t: V49EconomicTrade) -> tuple[str, ...]:
    return (
        t.symbol, t.session, t.operating_date,
        t.entry_at, t.entry_price, t.trigger_family, t.h1_state_basis,
    )


@dataclass(frozen=True, slots=True)
class ExcursionRow:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    exit_at: str
    entry_price: str
    direction: str
    trigger_family: str
    h1_state_basis: str
    exit_reason: str
    realized_gross_r: str
    planned_target_r: str
    stop_width_price: str
    bars_reconciled: int
    mfe_preterminal_r: str
    mae_preterminal_r: str
    mfe_full_exitbar_upper_r: str
    mae_full_exitbar_upper_r: str
    terminal_same_bar_stop_target_ambiguity: bool
    known_intrabar_sequence: bool = False
    executable_capture_claimed: bool = False
    hindsight_only: bool = True

    def __post_init__(self) -> None:
        if self.known_intrabar_sequence or self.executable_capture_claimed:
            raise ValueError("M1 extrema do not establish executable intrabar path")
        if not self.hindsight_only:
            raise ValueError("excursion results must remain ex-post")


def _risk_geometry(t: V49EconomicTrade) -> tuple[Decimal, Decimal, Decimal, int]:
    entry = Decimal(t.entry_price)
    stop = Decimal(t.stop_price)
    target = Decimal(t.target_price)
    if t.direction == "LONG":
        side = 1
        if not stop < entry < target:
            raise ValueError("invalid LONG stop/entry/target geometry")
    elif t.direction == "SHORT":
        side = -1
        if not target < entry < stop:
            raise ValueError("invalid SHORT stop/entry/target geometry")
    else:
        raise ValueError("unsupported trade direction")
    risk = abs(entry - stop)
    if risk <= 0 or abs(
        Decimal(t.planned_reward_r) - abs(target - entry) / risk
    ) > Decimal("0.000000000000000001"):
        raise ValueError("trade planned reward not reconciled to stop")
    if _dt(t.exit_at) <= _dt(t.entry_at):
        raise ValueError("trade exits before its entry")
    return entry, stop, risk, side


@dataclass(slots=True)
class _LiveAccumulator:
    trade: V49EconomicTrade
    entry: Decimal
    risk: Decimal
    side: int
    high_favorable: Decimal = Decimal(0)
    high_adverse: Decimal = Decimal(0)
    pre_favorable: Decimal = Decimal(0)
    pre_adverse: Decimal = Decimal(0)
    held: int = 0
    finished: bool = False

    def absorb(self, bar: CapitalizerM1Bar) -> None:
        t = self.trade
        if bar.opened_at < _dt(t.entry_at) or bar.closed_at > _dt(t.exit_at):
            raise ValueError("M1 bar crosses trade decision/exit boundary")
        if t.symbol != bar.symbol:
            raise ValueError("M1 bar asset mismatch")
        favorable_price = (
            bar.high - self.entry if self.side == 1 else self.entry - bar.low
        )
        adverse_price = (
            self.entry - bar.low if self.side == 1 else bar.high - self.entry
        )
        favorable = max(Decimal(0), favorable_price / self.risk)
        adverse = max(Decimal(0), adverse_price / self.risk)
        self.high_favorable = max(self.high_favorable, favorable)
        self.high_adverse = max(self.high_adverse, adverse)
        self.held += 1
        if bar.closed_at == _dt(t.exit_at):
            self.finished = True
            # Exit bar's full OHLC is an UPPER observational envelope.
            # No preterminal update. Cannot sequence target vs stop intrabar.
        else:
            self.pre_favorable = max(self.pre_favorable, favorable)
            self.pre_adverse = max(self.pre_adverse, adverse)

    def finish(self) -> ExcursionRow:
        t = self.trade
        if not self.finished or self.held != t.m1_bars_held:
            raise ValueError("M1 lifecycle not reconstructed exactly")
        if self.high_favorable < self.pre_favorable or (
            self.high_adverse < self.pre_adverse
        ):
            raise ValueError("excursion envelope narrower than preterminal history")
        if t.exit_reason == "STOP" and self.high_adverse < Decimal(1):
            raise ValueError("STOP exit without M1 stop-touch witness")
        if (
            t.exit_reason == "TARGET"
            and self.high_favorable < Decimal(t.planned_reward_r)
        ):
            raise ValueError("TARGET exit without M1 target-touch witness")
        if t.exit_reason not in ("STOP", "TARGET", "SESSION_EXIT"):
            raise ValueError("unknown replay exit reason")
        return ExcursionRow(
            symbol=t.symbol,
            session=t.session,
            operating_date=t.operating_date,
            entry_at=t.entry_at,
            exit_at=t.exit_at,
            entry_price=t.entry_price,
            direction=t.direction,
            trigger_family=t.trigger_family,
            h1_state_basis=t.h1_state_basis,
            exit_reason=t.exit_reason,
            realized_gross_r=t.realized_gross_r,
            planned_target_r=t.planned_reward_r,
            stop_width_price=str(self.risk),
            bars_reconciled=self.held,
            mfe_preterminal_r=str(self.pre_favorable),
            mae_preterminal_r=str(self.pre_adverse),
            mfe_full_exitbar_upper_r=str(self.high_favorable),
            mae_full_exitbar_upper_r=str(self.high_adverse),
            terminal_same_bar_stop_target_ambiguity=t.same_bar_stop_target_ambiguity,
        )


def observe_market_excursions(
    rows: tuple[V49EconomicTrade, ...],
    bars: Any,
) -> tuple[ExcursionRow, ...]:
    """Streaming bar-by-bar reconstruction; no future M1 bar admitted early."""

    if not rows:
        raise ValueError("market MFE/MAE needs actual simulated trades")
    if len({_trade_key(t) for t in rows}) != len(rows):
        raise ValueError("duplicated trade provenance in market")
    ordered = tuple(sorted(rows, key=lambda t: (_dt(t.entry_at), t.symbol)))
    for item in ordered:
        if item.symbol != ordered[0].symbol or item.session != ordered[0].session:
            raise ValueError("one market/single session required")
    next_index = 0
    active: list[_LiveAccumulator] = []
    finished: list[ExcursionRow] = []
    seen_bars = 0
    last_open: datetime | None = None

    for bar in bars:
        if not DEV_WINDOW_START <= bar.opened_at < DEV_WINDOW_END:
            continue
        if bar.symbol != ordered[0].symbol:
            raise ValueError("market M1 source symbol mismatch")
        if last_open is not None and bar.opened_at <= last_open:
            raise ValueError("M1 price chronology must be strictly increasing")
        last_open = bar.opened_at
        seen_bars += 1
        while next_index < len(ordered) and _dt(
            ordered[next_index].entry_at
        ) <= bar.opened_at:
            trade = ordered[next_index]
            entry, _stop, risk, side = _risk_geometry(trade)
            active.append(_LiveAccumulator(trade, entry, risk, side))
            next_index += 1
        survivors: list[_LiveAccumulator] = []
        for current in active:
            trade = current.trade
            if bar.opened_at >= _dt(trade.exit_at):
                raise ValueError("M1 replay trade missing its terminal bar")
            if (
                bar.opened_at >= _dt(trade.entry_at)
                and bar.closed_at <= _dt(trade.exit_at)
                and capitalizer_session_at(bar.opened_at).value == trade.session
            ):
                current.absorb(bar)
            if current.finished:
                finished.append(current.finish())
            else:
                survivors.append(current)
        active = survivors
    if (
        not seen_bars
        or next_index != len(ordered)
        or active
        or len(finished) != len(ordered)
    ):
        raise ValueError("incomplete M1 source lifecycle / missing trade close")
    return tuple(sorted(finished, key=lambda item: (item.entry_at, item.symbol)))


def _summary(items: tuple[ExcursionRow, ...]) -> dict[str, Any]:
    if not items:
        return {"count": 0}
    realized = tuple(Decimal(item.realized_gross_r) for item in items)
    total = sum(realized, Decimal(0))
    winners = tuple(item for item in items if Decimal(item.realized_gross_r) > 0)
    losers = tuple(item for item in items if Decimal(item.realized_gross_r) < 0)
    def mean_metric(values: tuple[Decimal, ...]) -> str | None:
        return str(sum(values, Decimal(0)) / len(values)) if values else None

    def quantile(values: tuple[Decimal, ...]) -> dict[str, str | None]:
        ordered = sorted(values)
        return {
            "median": str(median(ordered)) if ordered else None,
            "p90": (
                str(ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.9))])
                if ordered else None
            ),
        }

    mfe_pre = tuple(Decimal(item.mfe_preterminal_r) for item in items)
    mae_pre = tuple(Decimal(item.mae_preterminal_r) for item in items)
    mfe_bound = tuple(Decimal(item.mfe_full_exitbar_upper_r) for item in items)
    mae_bound = tuple(Decimal(item.mae_full_exitbar_upper_r) for item in items)
    def count_with_mfe(candidates: tuple[ExcursionRow, ...], r: Decimal) -> int:
        return sum(
            Decimal(item.mfe_preterminal_r) >= r for item in candidates
        )

    return {
        "count": len(items),
        "wins": len(winners),
        "losses": len(losers),
        "flats": len(items) - len(winners) - len(losers),
        "total_gross_r": str(total),
        "mean_realized_r": str(total / len(items)),
        "mean_mfe_preterminal_r": mean_metric(mfe_pre),
        "mean_mae_preterminal_r": mean_metric(mae_pre),
        "mean_mfe_full_exitbar_upper_r": mean_metric(mfe_bound),
        "mean_mae_full_exitbar_upper_r": mean_metric(mae_bound),
        "mfe_preterminal_distribution": quantile(mfe_pre),
        "mae_preterminal_distribution": quantile(mae_pre),
        "mfe_full_exitbar_upper_distribution": quantile(mfe_bound),
        "mae_full_exitbar_upper_distribution": quantile(mae_bound),
        "winners_mean_realized_r": mean_metric(tuple(
            Decimal(item.realized_gross_r) for item in winners
        )),
        "winners_mean_mfe_preterminal_r": mean_metric(tuple(
            Decimal(item.mfe_preterminal_r) for item in winners
        )),
        "losers_mean_realized_r": mean_metric(tuple(
            Decimal(item.realized_gross_r) for item in losers
        )),
        "losers_mean_mfe_preterminal_r": mean_metric(tuple(
            Decimal(item.mfe_preterminal_r) for item in losers
        )),
        "losers_mfe_preterminal_at_least_0_5r": count_with_mfe(
            losers, Decimal("0.5")
        ),
        "losers_mfe_preterminal_at_least_1r": count_with_mfe(
            losers, Decimal(1)
        ),
        "losers_mae_full_exitbar_upper_at_least_1r": sum(
            Decimal(item.mae_full_exitbar_upper_r) >= 1 for item in losers
        ),
        "exitbar_ambiguous_stop_first_count": sum(
            item.terminal_same_bar_stop_target_ambiguity for item in items
        ),
    }


def build_market_excursion_report(
    economic_root: Path,
    raw_m1_root: Path,
) -> tuple[dict[str, Any], tuple[ExcursionRow, ...]]:
    files = sorted(
        economic_root.rglob("capitalizer-*-v49-development-economics-trades.jsonl")
    )
    reports = sorted(
        economic_root.rglob("capitalizer-*-v49-development-economics.json")
    )
    if len(files) != 1 or len(reports) != 1:
        raise ValueError("one V49 frozen control market and report required")
    source_report = json.loads(reports[0].read_text(encoding="utf-8"))
    if (
        source_report.get("identity") != V49_REPORT_IDENTITY
        or source_report.get("trader_certified") is not False
        or source_report.get("live_authorized") is not False
    ):
        raise ValueError("not frozen research-only V49 report")
    rows = tuple(
        V49EconomicTrade(**json.loads(line)) for line in files[0].read_text(
            encoding="utf-8"
        ).splitlines() if line.strip()
    )
    if (
        source_report["replayed_trades"] != len(rows)
        or len(rows) + source_report["rejected_no_session_m1"]
        != source_report["candidate_opportunities"]
        or any(
            trade.symbol != source_report["symbol"]
            or trade.session != source_report["session"]
            for trade in rows
        )
    ):
        raise ValueError("V49 report/census mismatch")
    result = observe_market_excursions(rows, iter_cibo_m1(raw_m1_root))
    groups: dict[str, list[ExcursionRow]] = defaultdict(list)
    for item in result:
        groups[item.exit_reason].append(item)
    return {
        "identity": IDENTITY,
        "symbol": source_report["symbol"],
        "session": source_report["session"],
        "source_simulated_trades": len(rows),
        "reconciled_bars": sum(item.bars_reconciled for item in result),
        "all": _summary(result),
        "exit_reasons": {
            key: _summary(tuple(value)) for key, value in sorted(groups.items())
        },
        "hindsight_only": True,
        "terminal_m1_intrabar_order_unknown": True,
        "no_change_to_admission_or_execution": True,
        "trader_certified": False,
        "live_authorized": False,
    }, result


def aggregate_excursion_reports(root: Path) -> dict[str, Any]:
    market_reports = sorted(root.rglob("scalper-a2-mfe-mae-market.json"))
    paths = sorted(root.rglob("scalper-a2-mfe-mae-trades.jsonl"))
    if len(market_reports) != 9 or len(paths) != 9:
        raise ValueError("nine-market excursion coverage required")
    market_by_symbol: dict[str, dict[str, Any]] = {}
    for path in market_reports:
        r = json.loads(path.read_text(encoding="utf-8"))
        symbol = r.get("symbol")
        if (
            r.get("identity") != IDENTITY
            or symbol in market_by_symbol
            or r.get("trader_certified") is not False
            or r.get("live_authorized") is not False
        ):
            raise ValueError("invalid or duplicate excursion market report")
        market_by_symbol[symbol] = r
    rows: list[ExcursionRow] = []
    for path in paths:
        market_rows = tuple(
            ExcursionRow(**json.loads(line)) for line in path.read_text(
                encoding="utf-8"
            ).splitlines() if line.strip()
        )
        if not market_rows:
            raise ValueError("empty MFE/MAE market ledger")
        symbol = market_rows[0].symbol
        if symbol not in market_by_symbol or any(
            item.symbol != symbol for item in market_rows
        ):
            raise ValueError("excursion market names do not reconcile")
        if market_by_symbol[symbol]["source_simulated_trades"] != len(market_rows):
            raise ValueError("market excursions do not reconcile to V49 control")
        rows.extend(market_rows)
    if len(rows) != 2876 or len(market_by_symbol) != 9:
        raise ValueError("this frozen V49 control must reconcile 2876 trades / 9 markets")
    # Same deterministic rule as original V49; no outcome or MFE is used in selection.
    selected_input: list[V49EconomicTrade] = []
    # Reconstruct minimal V49 economics only to call the unchanged MAX3 selector.
    # Every field not involved in MAX3 remains a placeholder and is NOT used
    # for P&L reconciliation; no economic metrics are computed from these copies.
    for item in rows:
        selected_input.append(V49EconomicTrade(
            symbol=item.symbol, session=item.session,
            operating_date=item.operating_date,
            ordinal_candidate_at=item.entry_at,
            direction=item.direction,
            entry_at=item.entry_at,
            exit_at=item.exit_at,
            entry_price=item.entry_price,
            stop_price=(
                str(Decimal(item.entry_price) - Decimal(item.stop_width_price))
                if item.direction == "LONG" else
                str(Decimal(item.entry_price) + Decimal(item.stop_width_price))
            ),
            target_price=(
                str(Decimal(item.entry_price) + Decimal(item.planned_target_r) *
                    Decimal(item.stop_width_price))
                if item.direction == "LONG" else
                str(Decimal(item.entry_price) - Decimal(item.planned_target_r) *
                    Decimal(item.stop_width_price))
            ),
            planned_reward_r=item.planned_target_r,
            realized_gross_r=item.realized_gross_r,
            exit_reason=item.exit_reason,
            m1_bars_held=item.bars_reconciled,
            trigger_family=item.trigger_family,
            h1_state_basis=item.h1_state_basis,
            same_bar_stop_target_ambiguity=(
                item.terminal_same_bar_stop_target_ambiguity
            ),
        ))
    picked = {_trade_key(item) for _, item in _portfolio_select(tuple(selected_input))}
    if len(picked) != 2020 or len({_trade_key(item) for item in rows}) != len(rows):
        raise ValueError("frozen V49 MAX3 selection identity/denominator mismatch")
    selected = tuple(item for item in rows if _trade_key(item) in picked)
    excluded = tuple(item for item in rows if _trade_key(item) not in picked)
    if len(selected) != 2020 or len(excluded) != 856:
        raise ValueError("MFE/MAE audit MAX3 population mismatch")
    segments: dict[str, dict[str, list[ExcursionRow]]] = {
        "session": defaultdict(list),
        "market": defaultdict(list),
        "trigger_family": defaultdict(list),
        "exit_reason": defaultdict(list),
        "h1_state_basis": defaultdict(list),
    }
    for item in selected:
        segments["session"][item.session].append(item)
        segments["market"][item.symbol].append(item)
        segments["trigger_family"][item.trigger_family].append(item)
        segments["exit_reason"][item.exit_reason].append(item)
        segments["h1_state_basis"][item.h1_state_basis].append(item)
    return {
        "identity": IDENTITY,
        "market_count": 9,
        "source_simulated_trades": len(rows),
        "max3_selected": len(selected),
        "max3_excluded": len(excluded),
        "selected": _summary(selected),
        "excluded_counterfactual": _summary(excluded),
        "selected_by": {
            kind: {k: _summary(tuple(v)) for k, v in sorted(groups.items())}
            for kind, groups in segments.items()
        },
        "reporting_is_post_hoc_only": True,
        "terminal_extrema_are_not_intrabar_executable": True,
        "no_outcome_aware_selection": True,
        "trader_certified": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    market = sub.add_parser("market")
    market.add_argument("economic_root", type=Path)
    market.add_argument("raw_m1_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("market_artifacts", type=Path)
    matrix.add_argument("output", type=Path)
    a = parser.parse_args()
    if a.mode == "market":
        result, items = build_market_excursion_report(a.economic_root, a.raw_m1_root)
        a.output.mkdir(parents=True, exist_ok=True)
        (a.output / "scalper-a2-mfe-mae-market.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with (a.output / "scalper-a2-mfe-mae-trades.jsonl").open(
            "w", encoding="utf-8"
        ) as handle:
            for item in items:
                handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")
        print(json.dumps({
            "identity": IDENTITY,
            "symbol": result["symbol"],
            "source_simulated_trades": result["source_simulated_trades"],
            "all": result["all"],
        }, sort_keys=True))
    else:
        report = aggregate_excursion_reports(a.market_artifacts)
        a.output.mkdir(parents=True, exist_ok=True)
        (a.output / "scalper-a2-mfe-mae-matrix.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps({
            "identity": IDENTITY,
            "max3_selected": report["max3_selected"],
            "max3_excluded": report["max3_excluded"],
            "selected": report["selected"],
            "trader_certified": False,
        }, sort_keys=True))


if __name__ == "__main__":
    main()
