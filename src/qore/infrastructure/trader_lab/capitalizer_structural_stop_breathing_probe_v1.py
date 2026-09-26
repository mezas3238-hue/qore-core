"""Structural stop-breathing probes for QORE Capitalizer.

This diagnostic asks whether the R0 M5 geometry proxy is materially sensitive to the
amount of *causal structural room* behind the source bar. It does not tune arbitrary
points or ATR multiples. It replays the exact same entry and target with three probes:

- SOURCE_M5_EXTREME: frozen R0 baseline;
- TWO_CLOSED_M5_EXTREME: farther directional extreme across source + prior M5;
- THREE_CLOSED_M5_EXTREME: farther directional extreme across source + prior two M5.

The two/three-bar probes are falsification instruments only. They are NOT ICT/TTrades
source methodology, NOT a replacement for the protected-swing stop, and NOT eligible
for decision-time promotion. Native/finer M1 evidence is still required before the
source-faithful stop contract can be replayed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import (
    BAR_DURATION,
    CapitalizerM5Bar,
    iter_atlas_m5,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)

IDENTITY = "QORE_CAPITALIZER_STRUCTURAL_STOP_BREATHING_PROBE_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_STOP_BREATHING_MATRIX_V1"
MODES = (
    "SOURCE_M5_EXTREME",
    "TWO_CLOSED_M5_EXTREME",
    "THREE_CLOSED_M5_EXTREME",
)


@dataclass(frozen=True, slots=True)
class CapitalizerStopBreathingMetrics:
    mode: str
    trades: int
    wins: int
    losses: int
    flats: int
    total_gross_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    stop_exits: int
    target_exits: int
    session_exits: int
    same_m5_ambiguities: int
    median_stop_width_vs_baseline: str
    unchanged_due_to_history_gap: int


@dataclass(frozen=True, slots=True)
class CapitalizerStopBreathingMarketReport:
    identity: str
    symbol: str
    session: str
    modes: tuple[CapitalizerStopBreathingMetrics, ...]
    owner_dd_ceiling_r: str = "6"
    m1_evidence_required: bool = True
    m1_evidence_present: bool = False
    source_strategy_status: str = "WAIT_M1_EVIDENCE"
    geometry_proxy_only: bool = True
    diagnostic_only: bool = True
    arbitrary_price_padding_used: bool = False
    protected_swing_replaced: bool = False
    rule_promotion_allowed: bool = False
    stop_widening_authorized: bool = False
    economic_candidate: bool = False
    fresh_holdout_claimed: bool = False
    trader_certified: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerNineMarketStopBreathingMatrix:
    identity: str
    markets: tuple[CapitalizerStopBreathingMarketReport, ...]
    complete_nine_market_universe: bool
    modes_improving_pf_all_markets: tuple[str, ...]
    modes_reducing_dd_all_markets: tuple[str, ...]
    markets_reaching_owner_dd_ceiling: tuple[str, ...]
    m1_evidence_required: bool = True
    m1_evidence_present: bool = False
    source_strategy_status: str = "WAIT_M1_EVIDENCE"
    geometry_proxy_only: bool = True
    diagnostic_only: bool = True
    rule_promotion_allowed: bool = False
    stop_widening_authorized: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False


def _load_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-three-session-replay-cell-v1-trades.jsonl"))
    if len(paths) != 1:
        raise ValueError(f"stop breathing requires exactly one replay ledger, got {len(paths)}")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("replay row must be object")
            if row.get("outcome_used_for_selection") is not False:
                raise ValueError("stop-breathing probe requires non-outcome-selected replay")
            rows.append(row)
    if not rows:
        raise ValueError("stop breathing requires trades")
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                datetime.fromisoformat(str(item["entry_at"])),
                str(item["side"]),
            ),
        )
    )


def _bar_index(
    bars: tuple[CapitalizerM5Bar, ...],
) -> dict[datetime, int]:
    return {bar.opened_at: index for index, bar in enumerate(bars)}


def _causal_stop(
    *,
    bars: tuple[CapitalizerM5Bar, ...],
    entry_index: int,
    side: CapitalizerSide,
    baseline_stop: Decimal,
    mode: str,
) -> tuple[Decimal, bool]:
    if mode == "SOURCE_M5_EXTREME":
        return baseline_stop, False
    lookback = 2 if mode == "TWO_CLOSED_M5_EXTREME" else 3
    if mode not in MODES:
        raise ValueError(f"unsupported stop-breathing mode: {mode}")
    start = entry_index - lookback
    if start < 0:
        return baseline_stop, True
    selected = bars[start:entry_index]
    if len(selected) != lookback:
        return baseline_stop, True
    if any(
        selected[index].opened_at - selected[index - 1].opened_at != BAR_DURATION
        for index in range(1, len(selected))
    ):
        return baseline_stop, True

    if side is CapitalizerSide.LONG:
        stop = min(bar.low for bar in selected)
        return min(stop, baseline_stop), False
    stop = max(bar.high for bar in selected)
    return max(stop, baseline_stop), False


def _lifecycle(
    *,
    bars: tuple[CapitalizerM5Bar, ...],
    entry_index: int,
    side: CapitalizerSide,
    entry_price: Decimal,
    stop_price: Decimal,
    target_price: Decimal,
) -> tuple[Decimal, str, bool]:
    session = capitalizer_session_at(bars[entry_index].opened_at)
    if session is None:
        raise ValueError("breathing probe entry must belong to Capitalizer session")
    risk = abs(entry_price - stop_price)
    if risk <= 0:
        raise ValueError("breathing probe risk must be positive")

    last_close = entry_price
    bars_held = 0
    for offset in range(entry_index, len(bars)):
        bar = bars[offset]
        if offset > entry_index:
            previous = bars[offset - 1]
            if bar.opened_at - previous.opened_at != BAR_DURATION:
                break
        if capitalizer_session_at(bar.opened_at) is not session:
            break
        bars_held += 1
        last_close = bar.close

        if side is CapitalizerSide.LONG:
            stop_hit = bar.low <= stop_price
            target_hit = bar.high >= target_price
        else:
            stop_hit = bar.high >= stop_price
            target_hit = bar.low <= target_price

        if stop_hit:
            return Decimal("-1"), "STOP", target_hit
        if target_hit:
            reward = abs(target_price - entry_price)
            return reward / risk, "TARGET", False

    if bars_held <= 0:
        raise ValueError("breathing lifecycle must observe at least one bar")
    delta = (
        last_close - entry_price
        if side is CapitalizerSide.LONG
        else entry_price - last_close
    )
    return delta / risk, "SESSION_EXIT", False


def _metrics(
    *,
    mode: str,
    rows: tuple[dict[str, Any], ...],
    bars: tuple[CapitalizerM5Bar, ...],
    by_open: dict[datetime, int],
) -> CapitalizerStopBreathingMetrics:
    returns: list[Decimal] = []
    widths: list[Decimal] = []
    reasons: list[str] = []
    ambiguities = 0
    history_gaps = 0

    for row in rows:
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        entry_index = by_open.get(entry_at)
        if entry_index is None:
            raise ValueError("replay entry must map to exact M5 open")
        side = CapitalizerSide(str(row["side"]))
        entry = Decimal(str(row["entry_price"]))
        baseline_stop = Decimal(str(row["stop_price"]))
        target = Decimal(str(row["target_price"]))
        baseline_risk = abs(entry - baseline_stop)
        if baseline_risk <= 0:
            raise ValueError("baseline replay risk must be positive")

        stop, gap = _causal_stop(
            bars=bars,
            entry_index=entry_index,
            side=side,
            baseline_stop=baseline_stop,
            mode=mode,
        )
        history_gaps += int(gap)
        risk = abs(entry - stop)
        if risk <= 0:
            raise ValueError("causal breathing stop must remain protective")
        widths.append(risk / baseline_risk)

        realized, reason, ambiguity = _lifecycle(
            bars=bars,
            entry_index=entry_index,
            side=side,
            entry_price=entry,
            stop_price=stop,
            target_price=target,
        )
        returns.append(realized)
        reasons.append(reason)
        ambiguities += int(ambiguity)

    gross_profit = sum((value for value in returns if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in returns if value < 0), Decimal("0"))
    pf = None if gross_loss == 0 else gross_profit / gross_loss

    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in returns:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    return CapitalizerStopBreathingMetrics(
        mode=mode,
        trades=len(returns),
        wins=sum(value > 0 for value in returns),
        losses=sum(value < 0 for value in returns),
        flats=sum(value == 0 for value in returns),
        total_gross_r=str(sum(returns, Decimal("0"))),
        profit_factor=None if pf is None else str(pf),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        stop_exits=sum(reason == "STOP" for reason in reasons),
        target_exits=sum(reason == "TARGET" for reason in reasons),
        session_exits=sum(reason == "SESSION_EXIT" for reason in reasons),
        same_m5_ambiguities=ambiguities,
        median_stop_width_vs_baseline=str(median(widths)),
        unchanged_due_to_history_gap=history_gaps,
    )


def build_market_report(
    *,
    replay_root: Path,
    m5_root: Path,
) -> CapitalizerStopBreathingMarketReport:
    rows = _load_rows(replay_root)
    symbols = {str(row["symbol"]) for row in rows}
    sessions = {str(row["session"]) for row in rows}
    if len(symbols) != 1 or len(sessions) != 1:
        raise ValueError("one breathing report requires one market/session")
    symbol = next(iter(symbols))
    session = CapitalizerSession(next(iter(sessions)))
    if symbol not in allowed_markets(session):
        raise ValueError("stop-breathing market/session drift")

    bars = tuple(iter_atlas_m5(m5_root))
    if not bars or bars[0].symbol != symbol:
        raise ValueError("M5 artifact must match replay symbol")
    by_open = _bar_index(bars)

    metrics = tuple(
        _metrics(mode=mode, rows=rows, bars=bars, by_open=by_open)
        for mode in MODES
    )
    return CapitalizerStopBreathingMarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        modes=metrics,
    )


def write_market_report(
    report: CapitalizerStopBreathingMarketReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-structural-stop-breathing-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_reports(root: Path) -> tuple[CapitalizerStopBreathingMarketReport, ...]:
    paths = sorted(root.rglob("capitalizer-*-structural-stop-breathing-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"stop-breathing matrix requires 9 reports, got {len(paths)}")
    reports: list[CapitalizerStopBreathingMarketReport] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("identity") != IDENTITY:
            raise ValueError("unexpected stop-breathing report identity")
        reports.append(
            CapitalizerStopBreathingMarketReport(
                **{
                    **raw,
                    "modes": tuple(
                        CapitalizerStopBreathingMetrics(**item)
                        for item in raw["modes"]
                    ),
                }
            )
        )
    return tuple(sorted(reports, key=lambda item: item.symbol))


def _mode(
    report: CapitalizerStopBreathingMarketReport,
    mode: str,
) -> CapitalizerStopBreathingMetrics:
    matches = tuple(item for item in report.modes if item.mode == mode)
    if len(matches) != 1:
        raise ValueError("report must contain each breathing mode exactly once")
    return matches[0]


def build_matrix_from_reports(
    reports: tuple[CapitalizerStopBreathingMarketReport, ...],
) -> CapitalizerNineMarketStopBreathingMatrix:
    expected = {
        symbol
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    }
    if {report.symbol for report in reports} != expected:
        raise ValueError("nine-market stop-breathing universe mismatch")

    pf_modes: list[str] = []
    dd_modes: list[str] = []
    for mode in MODES[1:]:
        if all(
            _mode(report, mode).profit_factor is not None
            and _mode(report, "SOURCE_M5_EXTREME").profit_factor is not None
            and Decimal(str(_mode(report, mode).profit_factor))
            > Decimal(str(_mode(report, "SOURCE_M5_EXTREME").profit_factor))
            for report in reports
        ):
            pf_modes.append(mode)
        if all(
            Decimal(_mode(report, mode).max_drawdown_r)
            < Decimal(_mode(report, "SOURCE_M5_EXTREME").max_drawdown_r)
            for report in reports
        ):
            dd_modes.append(mode)

    reaching = tuple(
        f"{report.symbol}:{mode.mode}"
        for report in reports
        for mode in report.modes
        if Decimal(mode.max_drawdown_r) <= Decimal("6")
    )
    return CapitalizerNineMarketStopBreathingMatrix(
        identity=MATRIX_IDENTITY,
        markets=reports,
        complete_nine_market_universe=True,
        modes_improving_pf_all_markets=tuple(pf_modes),
        modes_reducing_dd_all_markets=tuple(dd_modes),
        markets_reaching_owner_dd_ceiling=reaching,
    )


def build_matrix(root: Path) -> CapitalizerNineMarketStopBreathingMatrix:
    return build_matrix_from_reports(_load_reports(root))


def write_matrix(
    report: CapitalizerNineMarketStopBreathingMatrix,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-nine-market-stop-breathing-matrix-v1.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# QORE Capitalizer — Nine-Market Structural Stop Breathing V1",
        "",
        "- M5 geometry falsification only; protected-swing source stop is NOT replaced.",
        "- Native/finer M1 evidence remains required.",
        "- No stop widening is authorized by this artifact.",
        "",
        "| Market | Base PF/DD | 2-M5 PF/DD | 3-M5 PF/DD | 3-M5 width x |",
        "|---|---|---|---|---:|",
    ]
    for market in report.markets:
        base = _mode(market, "SOURCE_M5_EXTREME")
        two = _mode(market, "TWO_CLOSED_M5_EXTREME")
        three = _mode(market, "THREE_CLOSED_M5_EXTREME")
        lines.append(
            f"| {market.symbol} | {base.profit_factor} / {base.max_drawdown_r}R | "
            f"{two.profit_factor} / {two.max_drawdown_r}R | "
            f"{three.profit_factor} / {three.max_drawdown_r}R | "
            f"{three.median_stop_width_vs_baseline} |"
        )
    lines.extend(
        [
            "",
            (
                "- Modes improving PF in all nine markets: "
                f"{', '.join(report.modes_improving_pf_all_markets) or 'NONE'}"
            ),
            (
                "- Modes reducing DD in all nine markets: "
                f"{', '.join(report.modes_reducing_dd_all_markets) or 'NONE'}"
            ),
            (
                "- Market/modes at Owner <=6R DD: "
                f"{', '.join(report.markets_reaching_owner_dd_ceiling) or 'NONE'}"
            ),
        ]
    )
    (output / "capitalizer-nine-market-stop-breathing-matrix-v1.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer structural stop breathing")
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("replay_root", type=Path)
    market.add_argument("m5_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        market_report = build_market_report(
            replay_root=args.replay_root,
            m5_root=args.m5_root,
        )
        write_market_report(market_report, args.output)
        print(
            json.dumps(
                {
                    "symbol": market_report.symbol,
                    "modes": [asdict(item) for item in market_report.modes],
                },
                sort_keys=True,
            )
        )
        return

    matrix_report = build_matrix(args.input_root)
    write_matrix(matrix_report, args.output)
    print(
        json.dumps(
            {
                "identity": matrix_report.identity,
                "markets": len(matrix_report.markets),
                "modes_improving_pf_all_markets": list(
                    matrix_report.modes_improving_pf_all_markets
                ),
                "modes_reducing_dd_all_markets": list(
                    matrix_report.modes_reducing_dd_all_markets
                ),
                "markets_reaching_owner_dd_ceiling": list(
                    matrix_report.markets_reaching_owner_dd_ceiling
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
