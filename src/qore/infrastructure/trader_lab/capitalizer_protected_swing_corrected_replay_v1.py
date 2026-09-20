"""Protected-swing corrected replay proxy for QORE Capitalizer.

Purpose
-------
Measure the delta caused by replacing the original R0 stop proxy
(SOURCE_M5_DIRECTIONAL_EXTREME) with a causally reconstructed protected-swing
anchor while keeping the original entry and structural target unchanged.

Important evidence boundary
---------------------------
The frozen source-faithful trader requires M1 execution confirmation. The
consumed research corpus is native M5 only. Therefore this module reconstructs
an M5 protected-swing *surrogate* using the same TTrades CISD/protected-swing
mechanics already encoded in QORE:

- immediately preceding opposing candle series;
- close through the opening price of the first causal candle;
- protected swing extracted only after that structural CISD confirmation.

This is useful for falsifying the old one-bar stop proxy, but it is NOT a claim
that M5 replaces the required M1 execution layer.

No arbitrary stop padding is introduced. The corrected proxy uses the protected
swing itself, which is explicitly documented as the default invalidation in the
reviewed TTrades stop-loss lesson. Other source examples that say "beyond" are
kept as execution variants, not silently converted into a universal numeric
buffer.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
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
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import detect_cisd
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_source_structural_extraction_v2 import (
    protected_swing_from_cisd,
)

IDENTITY = "QORE_CAPITALIZER_PROTECTED_SWING_CORRECTED_REPLAY_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_PROTECTED_SWING_CORRECTION_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerStopCorrectionTransition:
    baseline_exit: str
    corrected_exit: str
    trades: int


@dataclass(frozen=True, slots=True)
class CapitalizerProtectedSwingCorrectionMarketReport:
    identity: str
    symbol: str
    session: str
    total_replay_trades: int
    protected_swing_surrogate_matched_trades: int
    protected_swing_surrogate_coverage: str
    baseline_all_metrics: CapitalizerR0Metrics
    baseline_matched_metrics: CapitalizerR0Metrics
    corrected_matched_metrics: CapitalizerR0Metrics
    median_corrected_stop_width_vs_baseline: str
    median_causal_series_bars: str
    transitions: tuple[CapitalizerStopCorrectionTransition, ...]
    baseline_stop_probe: str = "SOURCE_M5_DIRECTIONAL_EXTREME"
    corrected_stop_probe: str = "M5_CAUSAL_CISD_PROTECTED_SWING_SURROGATE"
    source_default_stop_semantics: str = "PROTECTED_SWING_WICK_INVALIDATION"
    entry_changed: bool = False
    target_changed: bool = False
    arbitrary_numeric_buffer_added: bool = False
    m1_evidence_required: bool = True
    m1_evidence_present: bool = False
    source_faithful_replay_complete: bool = False
    important_level_proxy_used: bool = True
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    geometry_proxy_only: bool = True
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    fresh_holdout_claimed: bool = False
    trader_certified: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerProtectedSwingCorrectionMatrix:
    identity: str
    markets: tuple[CapitalizerProtectedSwingCorrectionMarketReport, ...]
    complete_nine_market_universe: bool
    markets_pf_improved_on_matched_sample: tuple[str, ...]
    markets_dd_reduced_on_matched_sample: tuple[str, ...]
    markets_losing_streak_reduced_on_matched_sample: tuple[str, ...]
    all_markets_pf_improved: bool
    all_markets_dd_reduced: bool
    all_markets_losing_streak_reduced: bool
    m1_evidence_required: bool = True
    m1_evidence_present: bool = False
    source_faithful_replay_complete: bool = False
    geometry_proxy_only: bool = True
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False


@dataclass(frozen=True, slots=True)
class _ReplayOutcome:
    realized_r: Decimal
    exit_reason: str
    bars_held: int
    same_bar_ambiguity: bool


def _source_bar(bar: CapitalizerM5Bar) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
    )


def _direction(side: CapitalizerSide) -> CapitalizerSourceDirection:
    return (
        CapitalizerSourceDirection.BULLISH
        if side is CapitalizerSide.LONG
        else CapitalizerSourceDirection.BEARISH
    )


def _opposing_close(bar: CapitalizerM5Bar, side: CapitalizerSide) -> bool:
    if side is CapitalizerSide.LONG:
        return bar.close < bar.open
    return bar.close > bar.open


def _causal_series_before_confirmation(
    bars: tuple[CapitalizerM5Bar, ...],
    *,
    confirmation_index: int,
    side: CapitalizerSide,
) -> tuple[CapitalizerM5Bar, ...]:
    if confirmation_index <= 0:
        return ()
    index = confirmation_index - 1
    selected: list[CapitalizerM5Bar] = []
    newer_open = bars[confirmation_index].opened_at
    while index >= 0:
        bar = bars[index]
        if newer_open - bar.opened_at != BAR_DURATION:
            break
        if not _opposing_close(bar, side):
            break
        selected.append(bar)
        newer_open = bar.opened_at
        index -= 1
    selected.reverse()
    return tuple(selected)


def _protected_swing_surrogate(
    bars: tuple[CapitalizerM5Bar, ...],
    *,
    confirmation_index: int,
    side: CapitalizerSide,
) -> tuple[Decimal, int] | None:
    causal = _causal_series_before_confirmation(
        bars,
        confirmation_index=confirmation_index,
        side=side,
    )
    if not causal:
        return None

    confirmation = bars[confirmation_index]
    cisd = detect_cisd(
        causal_series=tuple(_source_bar(item) for item in causal),
        confirmation_bar=_source_bar(confirmation),
        direction=_direction(side),
        important_level_reached=True,
        higher_timeframe_closure=None,
    )
    if not cisd.structural_confirmed:
        return None

    protected = protected_swing_from_cisd(
        cisd=cisd,
        causal_series=tuple(_source_bar(item) for item in causal),
        confirmation_bar=_source_bar(confirmation),
        origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
    )
    return protected.swing_price, len(causal)


def _load_trade_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-three-session-replay-cell-v1-trades.jsonl"))
    if len(paths) != 1:
        raise ValueError(
            f"protected-swing correction requires one replay ledger, got {len(paths)}"
        )
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row: Any = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("replay trade row must be an object")
            if row.get("outcome_used_for_selection") is not False:
                raise ValueError("correction replay requires non-outcome-selected source ledger")
            rows.append(row)
    if not rows:
        raise ValueError("protected-swing correction requires replay trades")
    return tuple(rows)


def _lifecycle(
    bars: tuple[CapitalizerM5Bar, ...],
    *,
    entry_index: int,
    side: CapitalizerSide,
    entry_price: Decimal,
    stop_price: Decimal,
    target_price: Decimal,
) -> _ReplayOutcome:
    session = capitalizer_session_at(bars[entry_index].opened_at)
    if session is None:
        raise ValueError("correction replay entry must belong to Capitalizer session")
    risk = abs(entry_price - stop_price)
    if risk <= 0:
        raise ValueError("correction replay risk must be positive")

    last_close = entry_price
    bars_held = 0
    for index in range(entry_index, len(bars)):
        bar = bars[index]
        if index > entry_index:
            previous = bars[index - 1]
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
            return _ReplayOutcome(
                realized_r=Decimal("-1"),
                exit_reason="STOP",
                bars_held=bars_held,
                same_bar_ambiguity=target_hit,
            )
        if target_hit:
            return _ReplayOutcome(
                realized_r=abs(target_price - entry_price) / risk,
                exit_reason="TARGET",
                bars_held=bars_held,
                same_bar_ambiguity=False,
            )

    if bars_held <= 0:
        raise ValueError("correction replay must observe at least one lifecycle bar")
    delta = (
        last_close - entry_price
        if side is CapitalizerSide.LONG
        else entry_price - last_close
    )
    return _ReplayOutcome(
        realized_r=delta / risk,
        exit_reason="SESSION_EXIT",
        bars_held=bars_held,
        same_bar_ambiguity=False,
    )


def _metrics(
    outcomes: tuple[_ReplayOutcome, ...],
    *,
    planned_rewards: tuple[Decimal, ...],
) -> CapitalizerR0Metrics:
    if not outcomes or len(outcomes) != len(planned_rewards):
        raise ValueError("correction metrics require aligned non-empty outcomes")
    returns = tuple(item.realized_r for item in outcomes)
    gross_profit = sum((value for value in returns if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in returns if value < 0), Decimal("0"))
    total = sum(returns, Decimal("0"))

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

    return CapitalizerR0Metrics(
        trades=len(outcomes),
        wins=sum(value > 0 for value in returns),
        losses=sum(value < 0 for value in returns),
        flats=sum(value == 0 for value in returns),
        total_gross_r=str(total),
        mean_gross_r=str(total / Decimal(len(outcomes))),
        gross_profit_r=str(gross_profit),
        gross_loss_r=str(gross_loss),
        profit_factor=(
            None if gross_loss == 0 else str(gross_profit / gross_loss)
        ),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        median_planned_reward_r=str(median(planned_rewards)),
        median_bars_held=str(median(item.bars_held for item in outcomes)),
        stop_exits=sum(item.exit_reason == "STOP" for item in outcomes),
        target_exits=sum(item.exit_reason == "TARGET" for item in outcomes),
        session_exits=sum(item.exit_reason == "SESSION_EXIT" for item in outcomes),
        ambiguous_stop_first_exits=sum(item.same_bar_ambiguity for item in outcomes),
    )


def _row_outcome(row: dict[str, Any]) -> _ReplayOutcome:
    return _ReplayOutcome(
        realized_r=Decimal(str(row["realized_gross_r"])),
        exit_reason=str(row["exit_reason"]),
        bars_held=int(row["bars_held"]),
        same_bar_ambiguity=bool(row["same_bar_stop_target_ambiguity"]),
    )


def build_market_report(
    *,
    replay_root: Path,
    m5_root: Path,
) -> CapitalizerProtectedSwingCorrectionMarketReport:
    rows = _load_trade_rows(replay_root)
    symbols = {str(row["symbol"]) for row in rows}
    sessions = {str(row["session"]) for row in rows}
    if len(symbols) != 1 or len(sessions) != 1:
        raise ValueError("one correction report requires one market/session")
    symbol = next(iter(symbols))
    session = CapitalizerSession(next(iter(sessions)))
    if symbol not in allowed_markets(session):
        raise ValueError("correction replay market/session drift")

    bars = tuple(iter_atlas_m5(m5_root))
    if not bars or bars[0].symbol != symbol:
        raise ValueError("M5 artifact must match replay symbol")
    by_open = {bar.opened_at: index for index, bar in enumerate(bars)}

    baseline_all = tuple(_row_outcome(row) for row in rows)
    baseline_all_rewards = tuple(
        Decimal(str(row["planned_reward_r"])) for row in rows
    )

    baseline_matched: list[_ReplayOutcome] = []
    corrected: list[_ReplayOutcome] = []
    baseline_matched_rewards: list[Decimal] = []
    corrected_rewards: list[Decimal] = []
    width_ratios: list[Decimal] = []
    causal_lengths: list[int] = []
    transitions: Counter[tuple[str, str]] = Counter()

    for row in rows:
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        source_opened_at = signal_at - BAR_DURATION
        confirmation_index = by_open.get(source_opened_at)
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        entry_index = by_open.get(entry_at)
        if confirmation_index is None or entry_index is None:
            raise ValueError("replay timestamps must map to exact M5 artifact bars")

        side = CapitalizerSide(str(row["side"]))
        surrogate = _protected_swing_surrogate(
            bars,
            confirmation_index=confirmation_index,
            side=side,
        )
        if surrogate is None:
            continue
        protected_price, causal_bars = surrogate

        entry = Decimal(str(row["entry_price"]))
        original_stop = Decimal(str(row["stop_price"]))
        target = Decimal(str(row["target_price"]))
        if side is CapitalizerSide.LONG:
            if protected_price >= entry:
                continue
        else:
            if protected_price <= entry:
                continue

        baseline_outcome = _lifecycle(
            bars,
            entry_index=entry_index,
            side=side,
            entry_price=entry,
            stop_price=original_stop,
            target_price=target,
        )
        corrected_outcome = _lifecycle(
            bars,
            entry_index=entry_index,
            side=side,
            entry_price=entry,
            stop_price=protected_price,
            target_price=target,
        )

        baseline_risk = abs(entry - original_stop)
        corrected_risk = abs(entry - protected_price)
        if baseline_risk <= 0 or corrected_risk <= 0:
            raise ValueError("matched correction trade requires positive stop geometry")

        baseline_matched.append(baseline_outcome)
        corrected.append(corrected_outcome)
        baseline_matched_rewards.append(abs(target - entry) / baseline_risk)
        corrected_rewards.append(abs(target - entry) / corrected_risk)
        width_ratios.append(corrected_risk / baseline_risk)
        causal_lengths.append(causal_bars)
        transitions[(baseline_outcome.exit_reason, corrected_outcome.exit_reason)] += 1

    if not corrected:
        raise ValueError("no replay trades produced a causal protected-swing surrogate")

    return CapitalizerProtectedSwingCorrectionMarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        total_replay_trades=len(rows),
        protected_swing_surrogate_matched_trades=len(corrected),
        protected_swing_surrogate_coverage=str(
            Decimal(len(corrected)) / Decimal(len(rows))
        ),
        baseline_all_metrics=_metrics(
            baseline_all,
            planned_rewards=baseline_all_rewards,
        ),
        baseline_matched_metrics=_metrics(
            tuple(baseline_matched),
            planned_rewards=tuple(baseline_matched_rewards),
        ),
        corrected_matched_metrics=_metrics(
            tuple(corrected),
            planned_rewards=tuple(corrected_rewards),
        ),
        median_corrected_stop_width_vs_baseline=str(median(width_ratios)),
        median_causal_series_bars=str(median(causal_lengths)),
        transitions=tuple(
            CapitalizerStopCorrectionTransition(
                baseline_exit=baseline,
                corrected_exit=corrected_exit,
                trades=count,
            )
            for (baseline, corrected_exit), count in sorted(transitions.items())
        ),
    )


def write_market_report(
    report: CapitalizerProtectedSwingCorrectionMarketReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        f"capitalizer-{report.symbol.lower()}-protected-swing-corrected-replay-v1.json"
    )
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_market_reports(
    root: Path,
) -> tuple[CapitalizerProtectedSwingCorrectionMarketReport, ...]:
    paths = sorted(root.rglob("capitalizer-*-protected-swing-corrected-replay-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"correction matrix requires 9 reports, got {len(paths)}")

    result: list[CapitalizerProtectedSwingCorrectionMarketReport] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        result.append(
            CapitalizerProtectedSwingCorrectionMarketReport(
                **{
                    **raw,
                    "baseline_all_metrics": CapitalizerR0Metrics(
                        **raw["baseline_all_metrics"]
                    ),
                    "baseline_matched_metrics": CapitalizerR0Metrics(
                        **raw["baseline_matched_metrics"]
                    ),
                    "corrected_matched_metrics": CapitalizerR0Metrics(
                        **raw["corrected_matched_metrics"]
                    ),
                    "transitions": tuple(
                        CapitalizerStopCorrectionTransition(**item)
                        for item in raw["transitions"]
                    ),
                }
            )
        )
    return tuple(sorted(result, key=lambda item: item.symbol))


def build_matrix_from_reports(
    reports: tuple[CapitalizerProtectedSwingCorrectionMarketReport, ...],
) -> CapitalizerProtectedSwingCorrectionMatrix:
    expected = {
        symbol
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    }
    if {report.symbol for report in reports} != expected:
        raise ValueError("protected-swing correction universe mismatch")

    pf_improved = tuple(
        report.symbol
        for report in reports
        if report.baseline_matched_metrics.profit_factor is not None
        and report.corrected_matched_metrics.profit_factor is not None
        and Decimal(report.corrected_matched_metrics.profit_factor)
        > Decimal(report.baseline_matched_metrics.profit_factor)
    )
    dd_reduced = tuple(
        report.symbol
        for report in reports
        if Decimal(report.corrected_matched_metrics.max_drawdown_r)
        < Decimal(report.baseline_matched_metrics.max_drawdown_r)
    )
    streak_reduced = tuple(
        report.symbol
        for report in reports
        if report.corrected_matched_metrics.max_losing_streak
        < report.baseline_matched_metrics.max_losing_streak
    )

    return CapitalizerProtectedSwingCorrectionMatrix(
        identity=MATRIX_IDENTITY,
        markets=reports,
        complete_nine_market_universe=True,
        markets_pf_improved_on_matched_sample=pf_improved,
        markets_dd_reduced_on_matched_sample=dd_reduced,
        markets_losing_streak_reduced_on_matched_sample=streak_reduced,
        all_markets_pf_improved=len(pf_improved) == 9,
        all_markets_dd_reduced=len(dd_reduced) == 9,
        all_markets_losing_streak_reduced=len(streak_reduced) == 9,
    )


def build_matrix(root: Path) -> CapitalizerProtectedSwingCorrectionMatrix:
    return build_matrix_from_reports(_load_market_reports(root))


def write_matrix(
    report: CapitalizerProtectedSwingCorrectionMatrix,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "capitalizer-nine-market-protected-swing-correction-v1.json"
    json_path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# QORE Capitalizer — Protected-Swing Corrected Replay V1",
        "",
        "- M5 protected-swing surrogate only; native M1 remains required.",
        "- Same entry and same structural target on matched trades.",
        "- No arbitrary numeric stop buffer.",
        "",
        (
            "| Market | Coverage | Baseline matched PF/DD | Corrected PF/DD | "
            "Width x | Baseline LS | Corrected LS |"
        ),
        "|---|---:|---|---|---:|---:|---:|",
    ]
    for market in report.markets:
        base = market.baseline_matched_metrics
        corrected = market.corrected_matched_metrics
        lines.append(
            f"| {market.symbol} | "
            f"{Decimal(market.protected_swing_surrogate_coverage) * 100:.2f}% | "
            f"{base.profit_factor} / {base.max_drawdown_r}R | "
            f"{corrected.profit_factor} / {corrected.max_drawdown_r}R | "
            f"{market.median_corrected_stop_width_vs_baseline} | "
            f"{base.max_losing_streak} | {corrected.max_losing_streak} |"
        )
    lines.extend(
        [
            "",
            (
                "- PF improved: "
                + (", ".join(report.markets_pf_improved_on_matched_sample) or "NONE")
            ),
            (
                "- DD reduced: "
                + (", ".join(report.markets_dd_reduced_on_matched_sample) or "NONE")
            ),
            (
                "- Losing streak reduced: "
                + (
                    ", ".join(report.markets_losing_streak_reduced_on_matched_sample)
                    or "NONE"
                )
            ),
        ]
    )
    (output / "capitalizer-nine-market-protected-swing-correction-v1.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer protected-swing corrected replay proxy"
    )
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
                    "coverage": market_report.protected_swing_surrogate_coverage,
                    "baseline_matched": asdict(market_report.baseline_matched_metrics),
                    "corrected_matched": asdict(market_report.corrected_matched_metrics),
                    "width_x": market_report.median_corrected_stop_width_vs_baseline,
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
                "all_markets_pf_improved": matrix_report.all_markets_pf_improved,
                "all_markets_dd_reduced": matrix_report.all_markets_dd_reduced,
                "all_markets_losing_streak_reduced": (
                    matrix_report.all_markets_losing_streak_reduced
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
