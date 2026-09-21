"""Consumed-5Y replay of the conservative Market Stop Intelligence candidate.

Candidate contract (research only):
- Original native-M1 entries and original target remain unchanged.
- Development-only Breathing Context V2 thresholds classify pre-entry context.
- 0-1 degraded factors => coherent setup eligible for breathing.
- 2-3 degraded factors => ENTRY_CONTEXT_DEGRADED -> NO_TRADE.
- unavailable context => fail-closed NO_TRADE.
- coherent setup stop = validated M1 OB distal extreme + market-specific P50 absolute
  breathing envelope learned from development recovery paths only.
- same-minute stop/target precedence is STOP first.
- all open trades exit at the unchanged session boundary.

The 2021-09-17..2026-09-17 window is already consumed. This replay is forensic
characterization, not a fresh holdout, not certification and not live authorization.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_market_stop_intelligence_5y_replay_v1 import (
    CapitalizerStopReplayMetrics,
    _ReplayState,
    _aware,
    _finalize_session_exit,
    _iter_relevant_m1,
    _metrics,
    _session_bounds,
)
from qore.infrastructure.trader_lab.capitalizer_stop_breathing_context_v2 import (
    IDENTITY as CONTEXT_IDENTITY,
    CapitalizerBreathingThresholdAudit,
    _add_derived_pretrade_features,
    _degraded_count,
    _enrich_pre_entry_paths,
    _merge_window,
)

IDENTITY = "QORE_CAPITALIZER_STOP_INTELLIGENCE_P50_5Y_REPLAY_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_STOP_INTELLIGENCE_P50_5Y_MATRIX_V1"
ENVELOPE_IDENTITY = "QORE_CAPITALIZER_MARKET_BREATHING_ENVELOPE_V1"
CANDIDATE_IDENTITY = "QORE_CAPITALIZER_STOP_INTELLIGENCE_CONSERVATIVE_P50_V1"
SOURCE_WINDOW = "2021-09-17_TO_2026-09-17_CONSUMED"
EXPECTED_SYMBOLS = {
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "USDCAD",
    "USDJPY",
    "XAUUSD",
}
FX_SYMBOLS = {
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
}


@dataclass(frozen=True, slots=True)
class CapitalizerP50ReplayMarketReport:
    identity: str
    candidate_identity: str
    symbol: str
    session: str
    source_trade_count: int
    coherent_candidate_trades: int
    context_degraded_rejected: int
    context_unavailable_rejected: int
    stop_geometry_rejected: int
    p50_buffer_absolute: str
    p50_buffer_unit: str
    p50_buffer_provider_increments_reference: str
    baseline_all_metrics: CapitalizerStopReplayMetrics
    baseline_matched_metrics: CapitalizerStopReplayMetrics
    candidate_metrics: CapitalizerStopReplayMetrics
    median_candidate_stop_width_vs_baseline: str
    candidate_stop_narrower: int
    candidate_stop_wider: int
    candidate_stop_equal: int
    transition_counts: tuple[tuple[str, int], ...]
    profit_factor_delta_vs_matched: str | None
    drawdown_reduction_r_vs_matched: str
    losing_streak_reduction_vs_matched: int
    candidate_dd_le_6r: bool
    quantile: str = "P50"
    quantile_selection_reason: str = "CONSERVATIVE_MEDIAN_DEVELOPMENT_RECOVERY_BREATHING"
    context_thresholds_development_only: bool = True
    envelope_development_only: bool = True
    consumed_holdout_used_for_threshold_selection: bool = False
    consumed_holdout_used_for_quantile_selection: bool = False
    entry_changed: bool = False
    target_changed: bool = False
    methodology_changed: bool = False
    same_minute_precedence: str = "STOP_FIRST_FAIL_CLOSED"
    post_entry_stop_widening_allowed: bool = False
    qore_risk_sizing_simulated: bool = False
    spread_slippage_latency_applied: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _one_json(root: Path, pattern: str) -> dict[str, Any]:
    paths = sorted(root.rglob(pattern))
    if len(paths) != 1:
        raise ValueError(f"expected one {pattern}, got {len(paths)}")
    raw = json.loads(paths[0].read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{pattern} must contain an object")
    return raw


def _load_context(root: Path, symbol: str) -> tuple[CapitalizerBreathingThresholdAudit, ...]:
    raw = _one_json(root, "capitalizer-*-stop-breathing-context-v2.json")
    if raw.get("identity") != CONTEXT_IDENTITY:
        raise ValueError("unexpected breathing-context identity")
    if raw.get("symbol") != symbol:
        raise ValueError("breathing-context symbol mismatch")
    if raw.get("consumed_holdout_used_for_threshold_selection") is not False:
        raise ValueError("candidate rejects holdout-selected context thresholds")
    if raw.get("buffer_candidate_frozen") is not False:
        raise ValueError("candidate expects research-only context report")
    audits_raw = raw.get("threshold_audits")
    if not isinstance(audits_raw, list):
        raise ValueError("threshold_audits must be a list")
    audits = tuple(CapitalizerBreathingThresholdAudit(**item) for item in audits_raw)
    return audits


def _load_p50_envelope(root: Path, symbol: str) -> dict[str, Any]:
    raw = _one_json(root, "capitalizer-*-market-breathing-envelope-v1.json")
    if raw.get("identity") != ENVELOPE_IDENTITY:
        raise ValueError("unexpected breathing-envelope identity")
    if raw.get("symbol") != symbol:
        raise ValueError("breathing-envelope symbol mismatch")
    if raw.get("consumed_holdout_selects_context_thresholds") is not False:
        raise ValueError("candidate rejects holdout-selected envelope context")
    if raw.get("quantile_selected_for_execution") is not False:
        raise ValueError("source envelope must remain research-only")
    envelopes = raw.get("envelopes")
    if not isinstance(envelopes, list):
        raise ValueError("envelopes must be a list")
    matches = [item for item in envelopes if item.get("quantile") == "P50"]
    if len(matches) != 1:
        raise ValueError("candidate requires exactly one P50 envelope")
    item = matches[0]
    if item.get("development_only_threshold") is not True:
        raise ValueError("P50 threshold must be development-only")
    if item.get("consumed_holdout_selected_threshold") is not False:
        raise ValueError("P50 threshold cannot be selected on holdout")
    return item


def _pip_size(symbol: str) -> Decimal | None:
    if symbol not in FX_SYMBOLS:
        return None
    return Decimal("0.01") if symbol.endswith("JPY") else Decimal("0.0001")


def _ceil_to_increment(value: Decimal, increment: Decimal) -> Decimal:
    if value <= 0 or increment <= 0:
        raise ValueError("buffer and provider increment must be positive")
    steps = (value / increment).to_integral_value(rounding=ROUND_CEILING)
    return steps * increment


def _buffer_price(
    *,
    symbol: str,
    row: dict[str, Any],
    envelope: dict[str, Any],
) -> Decimal:
    absolute = Decimal(str(envelope["development_threshold_absolute"]))
    unit = str(envelope["absolute_unit"])
    if unit == "PIPS":
        pip = _pip_size(symbol)
        if pip is None:
            raise ValueError("PIPS envelope applied to non-FX market")
        raw = absolute * pip
    elif unit == "PRICE_DISTANCE":
        raw = absolute
    else:
        raise ValueError(f"unsupported envelope unit: {unit}")
    increment = Decimal(str(row["provider_quote_increment"]))
    return _ceil_to_increment(raw, increment)


def _candidate_stop(
    *,
    symbol: str,
    row: dict[str, Any],
    envelope: dict[str, Any],
) -> tuple[Decimal, Decimal] | None:
    buffer = _buffer_price(symbol=symbol, row=row, envelope=envelope)
    entry = Decimal(str(row["entry_price"]))
    target = Decimal(str(row["target_price"]))
    side = str(row["side"])
    if side == "LONG":
        stop = Decimal(str(row["m1_order_block_low"])) - buffer
        return (stop, buffer) if stop < entry < target else None
    if side == "SHORT":
        stop = Decimal(str(row["m1_order_block_high"])) + buffer
        return (stop, buffer) if target < entry < stop else None
    raise ValueError(f"unsupported side: {side}")


def _replay_candidate(
    *,
    rows: list[dict[str, Any]],
    m1_root: Path,
    symbol: str,
    audits: tuple[CapitalizerBreathingThresholdAudit, ...],
    envelope: dict[str, Any],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    audit_index = {audit.feature: audit for audit in audits}
    accepted: list[dict[str, Any]] = []
    rejections: Counter[str] = Counter()
    states: list[_ReplayState] = []
    starts: dict[Any, list[int]] = defaultdict(list)
    intervals: list[tuple[Any, Any]] = []

    for source in rows:
        degraded = _degraded_count(source, audit_index)
        if degraded is None:
            rejections["CONTEXT_UNAVAILABLE"] += 1
            continue
        if degraded >= 2:
            rejections["ENTRY_CONTEXT_DEGRADED"] += 1
            continue
        stop_buffer = _candidate_stop(symbol=symbol, row=source, envelope=envelope)
        if stop_buffer is None:
            rejections["STOP_GEOMETRY_UNACCEPTABLE"] += 1
            continue
        stop, buffer = stop_buffer
        row = dict(source)
        entry_at = _aware(str(row["entry_at"]))
        _, session_end = _session_bounds(entry_at, str(row["session"]))
        entry = Decimal(str(row["entry_price"]))
        target = Decimal(str(row["target_price"]))
        baseline_stop = Decimal(str(row["stop_price"]))
        baseline_risk = abs(entry - baseline_stop)
        candidate_risk = abs(entry - stop)
        if baseline_risk <= 0 or candidate_risk <= 0:
            raise ValueError("candidate replay requires positive risk")
        row["baseline_stop_price"] = str(baseline_stop)
        row["candidate_stop_price"] = str(stop)
        row["candidate_buffer_price"] = str(buffer)
        row["candidate_stop_width_vs_baseline"] = str(candidate_risk / baseline_risk)
        row["candidate_planned_reward_r"] = str(abs(target - entry) / candidate_risk)
        row["breathing_degraded_factor_count"] = degraded
        row["breathing_context_state"] = "COHERENT_BREATHING_CANDIDATE"
        row["candidate_identity"] = CANDIDATE_IDENTITY
        row["quantile"] = "P50"
        row["outcome_used_for_selection"] = False

        accepted_index = len(accepted)
        accepted.append(row)
        state = _ReplayState(
            row_index=accepted_index,
            entry_at=entry_at,
            session_end=session_end,
            side=str(row["side"]),
            entry=entry,
            stop=stop,
            target=target,
        )
        state_index = len(states)
        states.append(state)
        starts[entry_at].append(state_index)
        intervals.append(_session_bounds(entry_at, str(row["session"])))

    if not accepted:
        raise ValueError("P50 candidate replay accepted no trades")

    active: set[int] = set()
    last_bar_close = None
    for bar, new_interval in _iter_relevant_m1(m1_root, intervals):
        if new_interval and active:
            for state_index in tuple(active):
                _finalize_session_exit(
                    states[state_index],
                    last_bar_close or bar.opened_at,
                )
            active.clear()

        for state_index in starts.get(bar.opened_at, ()):
            active.add(state_index)

        completed: list[int] = []
        for state_index in tuple(active):
            state = states[state_index]
            state.held += 1
            state.last_close = bar.close
            stop_hit = (
                bar.low <= state.stop
                if state.side == "LONG"
                else bar.high >= state.stop
            )
            target_hit = (
                bar.high >= state.target
                if state.side == "LONG"
                else bar.low <= state.target
            )
            risk = abs(state.entry - state.stop)

            if stop_hit:
                state.realized_r = Decimal("-1")
                state.exit_reason = "STOP"
                state.exit_at = bar.closed_at
                state.ambiguity = target_hit
                completed.append(state_index)
            elif target_hit:
                state.realized_r = abs(state.target - state.entry) / risk
                state.exit_reason = "TARGET"
                state.exit_at = bar.closed_at
                completed.append(state_index)

            if state_index not in completed and bar.closed_at >= state.session_end:
                _finalize_session_exit(state, bar.closed_at)
                completed.append(state_index)

        for state_index in completed:
            active.discard(state_index)
        last_bar_close = bar.closed_at

    if active:
        if last_bar_close is None:
            raise ValueError("no native-M1 bars reached P50 candidate trades")
        for state_index in tuple(active):
            _finalize_session_exit(states[state_index], last_bar_close)

    for state in states:
        if state.realized_r is None or state.exit_reason is None or state.exit_at is None:
            raise ValueError("P50 candidate replay left unresolved trade")
        row = accepted[state.row_index]
        row["structural_realized_gross_r"] = str(state.realized_r)
        row["structural_exit_reason"] = state.exit_reason
        row["structural_exit_at"] = state.exit_at.isoformat()
        row["structural_m1_bars_held"] = state.held
        row["structural_same_minute_stop_target_ambiguity"] = state.ambiguity

    return accepted, rejections


def build_market_report(
    holdout_penetration_root: Path,
    holdout_forensic_root: Path,
    context_root: Path,
    envelope_root: Path,
    m1_root: Path,
) -> tuple[CapitalizerP50ReplayMarketReport, list[dict[str, Any]]]:
    pen_report, rows = _merge_window(
        holdout_penetration_root,
        holdout_forensic_root,
    )
    symbol = str(pen_report["symbol"])
    session = str(pen_report["session"])
    audits = _load_context(context_root, symbol)
    envelope = _load_p50_envelope(envelope_root, symbol)

    _enrich_pre_entry_paths((rows,), m1_root)
    _add_derived_pretrade_features(rows)
    candidate_rows, rejections = _replay_candidate(
        rows=rows,
        m1_root=m1_root,
        symbol=symbol,
        audits=audits,
        envelope=envelope,
    )

    matched_keys = {
        (
            str(row["higher_setup_signal_at"]),
            str(row["entry_at"]),
            str(row["side"]),
        )
        for row in candidate_rows
    }
    baseline_matched = [
        row
        for row in rows
        if (
            str(row["higher_setup_signal_at"]),
            str(row["entry_at"]),
            str(row["side"]),
        )
        in matched_keys
    ]
    baseline_all_metrics = _metrics(rows, "realized_gross_r")
    baseline_matched_metrics = _metrics(baseline_matched, "realized_gross_r")
    candidate_metrics = _metrics(candidate_rows, "structural_realized_gross_r")

    ratios = [
        Decimal(str(row["candidate_stop_width_vs_baseline"]))
        for row in candidate_rows
    ]
    transitions = Counter(
        (str(row["exit_reason"]), str(row["structural_exit_reason"]))
        for row in candidate_rows
    )
    baseline_pf = baseline_matched_metrics.profit_factor
    candidate_pf = candidate_metrics.profit_factor
    pf_delta = (
        None
        if baseline_pf is None or candidate_pf is None
        else str(Decimal(candidate_pf) - Decimal(baseline_pf))
    )

    return (
        CapitalizerP50ReplayMarketReport(
            identity=IDENTITY,
            candidate_identity=CANDIDATE_IDENTITY,
            symbol=symbol,
            session=session,
            source_trade_count=len(rows),
            coherent_candidate_trades=len(candidate_rows),
            context_degraded_rejected=rejections["ENTRY_CONTEXT_DEGRADED"],
            context_unavailable_rejected=rejections["CONTEXT_UNAVAILABLE"],
            stop_geometry_rejected=rejections["STOP_GEOMETRY_UNACCEPTABLE"],
            p50_buffer_absolute=str(envelope["development_threshold_absolute"]),
            p50_buffer_unit=str(envelope["absolute_unit"]),
            p50_buffer_provider_increments_reference=str(
                envelope["development_threshold_provider_increments"]
            ),
            baseline_all_metrics=baseline_all_metrics,
            baseline_matched_metrics=baseline_matched_metrics,
            candidate_metrics=candidate_metrics,
            median_candidate_stop_width_vs_baseline=str(median(ratios)),
            candidate_stop_narrower=sum(value < 1 for value in ratios),
            candidate_stop_wider=sum(value > 1 for value in ratios),
            candidate_stop_equal=sum(value == 1 for value in ratios),
            transition_counts=tuple(
                (f"{before}->{after}", count)
                for (before, after), count in sorted(transitions.items())
            ),
            profit_factor_delta_vs_matched=pf_delta,
            drawdown_reduction_r_vs_matched=str(
                Decimal(baseline_matched_metrics.max_drawdown_r)
                - Decimal(candidate_metrics.max_drawdown_r)
            ),
            losing_streak_reduction_vs_matched=(
                baseline_matched_metrics.max_losing_streak
                - candidate_metrics.max_losing_streak
            ),
            candidate_dd_le_6r=(
                Decimal(candidate_metrics.max_drawdown_r) <= Decimal("6")
            ),
        ),
        candidate_rows,
    )


def write_market(
    report: CapitalizerP50ReplayMarketReport,
    rows: list[dict[str, Any]],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-stop-intelligence-p50-5y-replay-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def build_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-stop-intelligence-p50-5y-replay-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"P50 matrix requires 9 reports, got {len(paths)}")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if {str(report["symbol"]) for report in reports} != EXPECTED_SYMBOLS:
        raise ValueError("P50 replay universe mismatch")
    reports = sorted(reports, key=lambda item: str(item["symbol"]))

    def d(report: dict[str, Any], key: str, field: str) -> Decimal:
        return Decimal(str(report[key][field]))

    baseline_gp = sum(
        (d(report, "baseline_matched_metrics", "gross_profit_r") for report in reports),
        Decimal("0"),
    )
    baseline_gl = sum(
        (d(report, "baseline_matched_metrics", "gross_loss_r") for report in reports),
        Decimal("0"),
    )
    candidate_gp = sum(
        (d(report, "candidate_metrics", "gross_profit_r") for report in reports),
        Decimal("0"),
    )
    candidate_gl = sum(
        (d(report, "candidate_metrics", "gross_loss_r") for report in reports),
        Decimal("0"),
    )
    return {
        "identity": MATRIX_IDENTITY,
        "candidate_identity": CANDIDATE_IDENTITY,
        "market_count": 9,
        "source_window": SOURCE_WINDOW,
        "source_trade_count": sum(int(report["source_trade_count"]) for report in reports),
        "coherent_candidate_trades": sum(
            int(report["coherent_candidate_trades"]) for report in reports
        ),
        "context_degraded_rejected": sum(
            int(report["context_degraded_rejected"]) for report in reports
        ),
        "context_unavailable_rejected": sum(
            int(report["context_unavailable_rejected"]) for report in reports
        ),
        "stop_geometry_rejected": sum(
            int(report["stop_geometry_rejected"]) for report in reports
        ),
        "baseline_matched_pooled_profit_factor": (
            None if baseline_gl == 0 else str(baseline_gp / baseline_gl)
        ),
        "candidate_pooled_profit_factor": (
            None if candidate_gl == 0 else str(candidate_gp / candidate_gl)
        ),
        "baseline_matched_total_r": str(
            sum(
                (d(report, "baseline_matched_metrics", "total_r") for report in reports),
                Decimal("0"),
            )
        ),
        "candidate_total_r": str(
            sum(
                (d(report, "candidate_metrics", "total_r") for report in reports),
                Decimal("0"),
            )
        ),
        "markets_pf_improved": [
            report["symbol"]
            for report in reports
            if report["profit_factor_delta_vs_matched"] is not None
            and Decimal(str(report["profit_factor_delta_vs_matched"])) > 0
        ],
        "markets_dd_reduced": [
            report["symbol"]
            for report in reports
            if Decimal(str(report["drawdown_reduction_r_vs_matched"])) > 0
        ],
        "markets_losing_streak_reduced": [
            report["symbol"]
            for report in reports
            if int(report["losing_streak_reduction_vs_matched"]) > 0
        ],
        "markets_candidate_dd_le_6r": [
            report["symbol"]
            for report in reports
            if bool(report["candidate_dd_le_6r"])
        ],
        "markets": reports,
        "quantile": "P50",
        "quantile_selection_reason": "CONSERVATIVE_MEDIAN_DEVELOPMENT_RECOVERY_BREATHING",
        "context_thresholds_development_only": True,
        "envelope_development_only": True,
        "consumed_holdout_used_for_threshold_selection": False,
        "consumed_holdout_used_for_quantile_selection": False,
        "entry_changed": False,
        "target_changed": False,
        "methodology_changed": False,
        "post_entry_stop_widening_allowed": False,
        "qore_risk_sizing_simulated": False,
        "spread_slippage_latency_applied": False,
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-stop-intelligence-p50-5y-matrix-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("holdout_penetration_root", type=Path)
    market.add_argument("holdout_forensic_root", type=Path)
    market.add_argument("context_root", type=Path)
    market.add_argument("envelope_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report, rows = build_market_report(
            args.holdout_penetration_root,
            args.holdout_forensic_root,
            args.context_root,
            args.envelope_root,
            args.m1_root,
        )
        write_market(report, rows, args.output)
        print(
            json.dumps(
                {
                    "identity": report.identity,
                    "symbol": report.symbol,
                    "candidate_trades": report.coherent_candidate_trades,
                    "candidate_pf": report.candidate_metrics.profit_factor,
                    "candidate_dd": report.candidate_metrics.max_drawdown_r,
                    "candidate_ls": report.candidate_metrics.max_losing_streak,
                },
                sort_keys=True,
            )
        )
        return

    matrix_report = build_matrix(args.input_root)
    write_matrix(matrix_report, args.output)
    print(json.dumps(matrix_report, sort_keys=True))


if __name__ == "__main__":
    main()
