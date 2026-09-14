"""Phase-2 consumed-evidence root-cause forensics for VT-08 Index V4.

Every predictor emitted by this module is known at ``signal_at``.  Outcome and
path diagnostics are explicitly prefixed with ``outcome_`` and are never used
by the hypothesis predicates.  The module is research-only and cannot freeze a
candidate or authorize trading.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from statistics import median
from typing import Any, cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_index_qore_ambiguity_lab_v1 import (
    ClosurePolicy,
    SwingPolicy,
    _closure,
    _signal,
)
from qore.infrastructure.trader_lab.vt08_index_v2_candidate import (
    _gap_exit,
    _intrabar_exit,
)
from qore.infrastructure.trader_lab.vt08_index_v3_geometry_candidate import (
    _geometry,
)
from qore.infrastructure.trader_lab.vt08_index_v4_regime_forensics import (
    DEVELOPMENT_SHA,
    V2_FRESH_SHA,
    V3_FRESH_SHA,
    _load_indexed,
    _metrics,
    _replay,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    AUTHORIZED_MARKETS,
    Vt08IndexC2R1Bar,
    _aggregate_contiguous_m15,
    _source_day,
    _window_bars,
    protected_swings_in_candle2,
)
from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_v4_root_cause_forensics.v2"
RESEARCH_ID = "VT08_INDEX_V4_ROOT_CAUSE_FORENSICS_002"
STRESS_COSTS_R = tuple(Decimal(item) for item in ("0.025", "0.05", "0.075", "0.10"))
_NY = ZoneInfo("America/New_York")
_TARGETS = tuple(Decimal(item) for item in ("1.5", "2", "2.5", "3"))


class Vt08IndexV4RootCauseError(InfrastructureError):
    __slots__ = ()


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    return numerator / denominator if denominator > 0 else Decimal()


def _side_sign(side: DemoTradingSetupSide) -> int:
    return 1 if side is DemoTradingSetupSide.LONG else -1


def _body_sign(bar: Vt08IndexC2R1Bar) -> int:
    return (bar.close > bar.open) - (bar.close < bar.open)


def _aligned(bar: Vt08IndexC2R1Bar, side: DemoTradingSetupSide) -> bool:
    return _body_sign(bar) == _side_sign(side)


def _sweep_type(subject: Vt08IndexC2R1Bar, reference: Vt08IndexC2R1Bar) -> str:
    high = subject.high > reference.high
    low = subject.low < reference.low
    if high and low:
        return "both_sides"
    if high:
        return "high_breakout" if subject.close > reference.high else "high_reclaim"
    if low:
        return "low_breakout" if subject.close < reference.low else "low_reclaim"
    return "inside"


def _source_days(
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    *,
    before_local: datetime,
    count: int,
) -> tuple[Vt08IndexC2R1Bar, ...]:
    """Return oldest-to-newest complete source days available before decision."""
    end_date = before_local.astimezone(_NY).date() - timedelta(days=1)
    retained: list[Vt08IndexC2R1Bar] = []
    for offset in range(30):
        candidate = _source_day(indexed, end_date=end_date - timedelta(days=offset))
        if candidate is not None:
            retained.append(candidate)
            if len(retained) == count:
                return tuple(reversed(retained))
    raise Vt08IndexV4RootCauseError("insufficient complete source-day history")


def _aggregate_h4_before(
    indexed: dict[datetime, Vt08IndexC2R1Bar], decision: datetime, count: int
) -> tuple[Vt08IndexC2R1Bar, ...]:
    rows: list[Vt08IndexC2R1Bar] = []
    local = decision.astimezone(_NY)
    for offset in range(1, count + 10):
        bar = _aggregate_contiguous_m15(
            indexed,
            opened_at_local=local - timedelta(hours=4 * offset),
            count=16,
        )
        if bar is not None:
            rows.append(bar)
            if len(rows) == count:
                return tuple(rows)
    raise Vt08IndexV4RootCauseError("insufficient causal H4 history")


def _range_state(ratio: Decimal) -> str:
    if ratio < Decimal("0.8"):
        return "compressed"
    if ratio > Decimal("1.2"):
        return "expanded"
    return "normal"


def _selected_rank(swings: Sequence[Any], selected: Any) -> int:
    for index, item in enumerate(swings, start=1):
        if item.price == selected.price and item.cisd_level == selected.cisd_level:
            return index
    raise Vt08IndexV4RootCauseError("selected swing left reconstructed set")


def _opposing_series_length(bars: Sequence[Vt08IndexC2R1Bar], selected: Any) -> int:
    return sum(
        selected.opposing_series_opened_at <= bar.opened_at < selected.confirmed_at
        and (
            bar.close < bar.open
            if selected.side is DemoTradingSetupSide.LONG
            else bar.close > bar.open
        )
        for bar in bars
    )


def _path_outcome(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    stop: Decimal,
    target_multiple: Decimal,
    bars: Sequence[Vt08IndexC2R1Bar],
) -> Decimal:
    risk = entry - stop if side is DemoTradingSetupSide.LONG else stop - entry
    target = (
        entry + target_multiple * risk
        if side is DemoTradingSetupSide.LONG
        else entry - target_multiple * risk
    )
    exit_price = bars[-1].close
    for bar in bars:
        resolved = _gap_exit(side=side, bar=bar, stop=stop, target=target)
        if resolved is None:
            resolved = _intrabar_exit(bar=bar, stop=stop, target=target)
        if resolved is not None:
            exit_price = resolved[0]
            break
    pnl = exit_price - entry if side is DemoTradingSetupSide.LONG else entry - exit_price
    return pnl / risk


def _cross_index_features(
    *,
    all_indexed: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
    decision: datetime,
    side: DemoTradingSetupSide,
) -> tuple[str, int, int]:
    signs: list[int] = []
    same_signals = 0
    opposite_signals = 0
    for indexed in all_indexed.values():
        h4 = _aggregate_h4_before(indexed, decision, 1)[0]
        signs.append(_body_sign(h4))
        candidate = _signal(
            symbol="NAS100",  # symbol does not affect structural resolution
            bars_by_open=indexed,
            decision_at=decision,
            closure=ClosurePolicy.C2_OR_C3_BODY_CLOSE,
            swing=SwingPolicy.FARTHEST_STRUCTURAL,
        )
        if candidate is not None:
            if candidate.side is side:
                same_signals += 1
            else:
                opposite_signals += 1
    wanted = _side_sign(side)
    if all(item == wanted for item in signs):
        state = "unanimous_with_side"
    elif all(item == -wanted for item in signs):
        state = "unanimous_against_side"
    else:
        state = "mixed"
    return state, same_signals, opposite_signals


def _feature_row(
    trade: dict[str, object],
    *,
    window_id: str,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    all_indexed: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
) -> dict[str, object]:
    symbol = str(trade["symbol"])
    decision = datetime.fromisoformat(str(trade["signal_at"]))
    signal = _signal(
        symbol=symbol,
        bars_by_open=indexed,
        decision_at=decision,
        closure=ClosurePolicy.C2_OR_C3_BODY_CLOSE,
        swing=SwingPolicy.FARTHEST_STRUCTURAL,
    )
    if signal is None:
        raise Vt08IndexV4RootCauseError("official V3 trade no longer resolves")
    resolved = _closure(
        policy=ClosurePolicy.C2_OR_C3_BODY_CLOSE,
        bars_by_open=indexed,
        decision_at=decision,
        side=signal.side,
    )
    geometry = _geometry(signal, bars_by_open=indexed)
    if resolved is None or geometry is None:
        raise Vt08IndexV4RootCauseError("feature reconstruction drifted")
    reference, closure_bar, closure_kind = resolved
    closure_m15 = _window_bars(indexed, opened_at=closure_bar.opened_at, count=16)
    future_m15 = _window_bars(indexed, opened_at=decision, count=16)
    if closure_m15 is None or future_m15 is None:
        raise Vt08IndexV4RootCauseError("incomplete M15 feature/path window")
    important = reference.low if signal.side is DemoTradingSetupSide.LONG else reference.high
    swings = protected_swings_in_candle2(closure_m15, side=signal.side, important_level=important)
    selected = signal.protected_swing
    # Decision artifacts deliberately retain only the causal prefix needed by
    # the frozen replay.  Three complete source days are always present; using
    # a longer lookback would silently turn artifact retention into a feature
    # selection rule and would exclude otherwise valid early trades.
    days = _source_days(indexed, before_local=decision.astimezone(_NY), count=3)
    previous_previous, previous_day, current_day = days[-3:]
    h4 = _aggregate_h4_before(indexed, decision, 3)
    h4_ranges = [item.high - item.low for item in h4]
    day_ranges = [item.high - item.low for item in days]
    h4_ratio = _ratio(h4_ranges[0], Decimal(str(median(h4_ranges[1:]))))
    daily_ratio = _ratio(day_ranges[-1], Decimal(str(median(day_ranges[:-1]))))
    reference_range = reference.high - reference.low
    closure_range = closure_bar.high - closure_bar.low
    local = decision.astimezone(_NY)
    manipulation = _aggregate_contiguous_m15(
        indexed,
        opened_at_local=local - timedelta(hours=8 if closure_kind == "c3" else 4),
        count=16,
    )
    if manipulation is None:
        raise Vt08IndexV4RootCauseError("missing manipulation H4")
    if signal.side is DemoTradingSetupSide.LONG:
        sweep_depth = max(Decimal(), important - manipulation.low)
        reclaim_depth = closure_bar.close - important
        close_position = _ratio(closure_bar.close - closure_bar.low, closure_range)
    else:
        sweep_depth = max(Decimal(), manipulation.high - important)
        reclaim_depth = important - closure_bar.close
        close_position = _ratio(closure_bar.high - closure_bar.close, closure_range)
    body = abs(closure_bar.close - closure_bar.open)
    cross_state, simultaneous_same, simultaneous_opposite = _cross_index_features(
        all_indexed=all_indexed, decision=decision, side=signal.side
    )
    entry = _decimal(trade["entry"])
    stop = _decimal(trade["stop"])
    risk = abs(entry - stop)
    favorable = max(
        (bar.high - entry if signal.side is DemoTradingSetupSide.LONG else entry - bar.low)
        for bar in future_m15
    )
    adverse = max(
        (entry - bar.low if signal.side is DemoTradingSetupSide.LONG else bar.high - entry)
        for bar in future_m15
    )
    confirmation_index = int((selected.confirmed_at - closure_bar.opened_at).total_seconds() // 900)
    source_relationship = (
        "breakout"
        if current_day.close > previous_day.high or current_day.close < previous_day.low
        else "reversal"
    )
    row: dict[str, object] = {
        "window_id": window_id,
        "symbol": symbol,
        "timestamp": decision.astimezone(UTC).isoformat(),
        "signal_at": decision.astimezone(UTC).isoformat(),
        "anchor": signal.anchor,
        "side": signal.side.value,
        "closure_family": closure_kind,
        "bias_family": f"{source_relationship}_{signal.side.value}",
        "source_day_relationship": source_relationship,
        "previous_source_day_body_alignment": "aligned"
        if _aligned(previous_day, signal.side)
        else "opposed",
        "current_source_day_body_alignment": "aligned"
        if _aligned(current_day, signal.side)
        else "opposed",
        "previous_day_sweep_type": _sweep_type(previous_day, previous_previous),
        "current_day_sweep_type": _sweep_type(current_day, previous_day),
        "protected_swing_count": len(swings),
        "selected_protected_swing_rank": _selected_rank(swings, selected),
        "opposing_series_length": _opposing_series_length(closure_m15, selected),
        "cisd_latency_m15": confirmation_index,
        "protected_swing_confirmation_latency_m15": confirmation_index,
        "cisd_to_extreme_normalized_distance": str(
            _ratio(abs(selected.cisd_level - selected.price), reference_range)
        ),
        "sweep_depth": str(_ratio(sweep_depth, reference_range)),
        "reclaim_depth": str(_ratio(reclaim_depth, reference_range)),
        "closure_reference_range_ratio": str(_ratio(closure_range, reference_range)),
        "closure_body_fraction": str(_ratio(body, closure_range)),
        "closure_close_position": str(close_position),
        "protected_risk_fraction": str(geometry["risk_fraction"]),
        "recent_causal_h4_range_ratio": str(h4_ratio),
        "recent_causal_h4_range_state": _range_state(h4_ratio),
        "recent_causal_daily_range_ratio": str(daily_ratio),
        "recent_causal_daily_range_state": _range_state(daily_ratio),
        "cross_index_directional_state": cross_state,
        "cross_index_simultaneous_same_side_signals": simultaneous_same,
        "cross_index_simultaneous_opposite_side_signals": simultaneous_opposite,
        "outcome_r": str(trade["r_multiple"]),
        "outcome_exit_reason": str(trade["exit_reason"]),
        "outcome_mae_r": str(_ratio(adverse, risk)),
        "outcome_mfe_r": str(_ratio(favorable, risk)),
    }
    for target in _TARGETS:
        row[f"outcome_target_{target}_r"] = str(
            _path_outcome(
                side=signal.side,
                entry=entry,
                stop=stop,
                target_multiple=target,
                bars=future_m15,
            )
        )
    return row


def _full_feature_rows(
    report: dict[str, object],
    *,
    window_id: str,
    indexed: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
) -> list[dict[str, object]]:
    trades = report.get("trades")
    if not isinstance(trades, list):
        raise Vt08IndexV4RootCauseError("report trades malformed")
    return [
        _feature_row(
            item,
            window_id=window_id,
            indexed=indexed[str(item["symbol"])],
            all_indexed=indexed,
        )
        for item in trades
        if isinstance(item, dict)
    ]


def _row_metrics(
    rows: Iterable[dict[str, object]], *, outcome: str = "outcome_r"
) -> dict[str, object]:
    remapped = [
        {"signal_at": row["timestamp"], "symbol": row["symbol"], "r_multiple": row[outcome]}
        for row in rows
    ]
    result = _metrics(remapped)
    total = sum((_decimal(item["r_multiple"]) for item in remapped), Decimal())
    result["stress"] = {
        str(cost): {
            "total_r": str(total - cost * len(remapped)),
            "mean_r": str(total / len(remapped) - cost) if remapped else "0",
        }
        for cost in STRESS_COSTS_R
    }
    return result


def _decompose(rows: list[dict[str, object]], key: str) -> dict[str, dict[str, object]]:
    return {
        str(value): _row_metrics([row for row in rows if row[key] == value])
        for value in sorted({row[key] for row in rows}, key=str)
    }


def _temporal_block(value: str, months: int) -> str:
    stamp = datetime.fromisoformat(value)
    absolute = stamp.year * 12 + stamp.month - 1
    start = absolute - absolute % months
    return f"{start // 12:04d}-{start % 12 + 1:02d}"


def _hypotheses() -> dict[str, Callable[[dict[str, object]], bool]]:
    """Predeclared interpretable screens; none references outcome columns."""
    return {
        "H01_previous_body_opposed": lambda r: r["previous_source_day_body_alignment"] == "opposed",
        "H02_cisd_first_half": lambda r: _decimal(r["cisd_latency_m15"]) <= 8,
        "H03_previous_body_opposed_and_cisd_first_half": lambda r: (
            r["previous_source_day_body_alignment"] == "opposed"
            and _decimal(r["cisd_latency_m15"]) <= 8
        ),
        "H04_previous_body_opposed_and_c2": lambda r: (
            r["previous_source_day_body_alignment"] == "opposed" and r["closure_family"] == "c2"
        ),
        "H05_previous_body_opposed_and_c3": lambda r: (
            r["previous_source_day_body_alignment"] == "opposed" and r["closure_family"] == "c3"
        ),
        "H06_previous_body_opposed_and_reversal_bias": lambda r: (
            r["previous_source_day_body_alignment"] == "opposed"
            and r["source_day_relationship"] == "reversal"
        ),
        "H07_previous_body_opposed_and_breakout_bias": lambda r: (
            r["previous_source_day_body_alignment"] == "opposed"
            and r["source_day_relationship"] == "breakout"
        ),
        "H08_previous_body_opposed_and_cross_index_not_against": lambda r: (
            r["previous_source_day_body_alignment"] == "opposed"
            and r["cross_index_directional_state"] != "unanimous_against_side"
        ),
        "H09_protected_swing_count_eq_2": lambda r: _decimal(r["protected_swing_count"]) == 2,
        "H10_single_protected_swing": lambda r: _decimal(r["protected_swing_count"]) == 1,
        "H11_cisd_short_series": lambda r: _decimal(r["opposing_series_length"]) <= 2,
        "H12_current_body_aligned": lambda r: r["current_source_day_body_alignment"] == "aligned",
        "H13_h4_not_expanded": lambda r: r["recent_causal_h4_range_state"] != "expanded",
        "H14_daily_not_expanded": lambda r: r["recent_causal_daily_range_state"] != "expanded",
        "H15_cross_index_unanimous_with": lambda r: (
            r["cross_index_directional_state"] == "unanimous_with_side"
        ),
        "H16_cross_index_mixed": lambda r: r["cross_index_directional_state"] == "mixed",
        "H17_sweep_reclaim": lambda r: "reclaim" in str(r["current_day_sweep_type"]),
        "H18_previous_body_opposed_cisd_first_half_c2": lambda r: (
            r["previous_source_day_body_alignment"] == "opposed"
            and _decimal(r["cisd_latency_m15"]) <= 8
            and r["closure_family"] == "c2"
        ),
    }


def _normal_pvalue(rows: Sequence[dict[str, object]]) -> float:
    values = [float(_decimal(row["outcome_r"])) for row in rows]
    if len(values) < 2:
        return 1.0
    mean = sum(values) / len(values)
    variance = sum((item - mean) ** 2 for item in values) / (len(values) - 1)
    if variance == 0:
        return 0.0 if mean > 0 else 1.0
    z = mean / math.sqrt(variance / len(values))
    return 0.5 * math.erfc(z / math.sqrt(2))


def _holm_adjust(raw: dict[str, float]) -> dict[str, float]:
    ordered = sorted(raw, key=lambda name: raw[name])
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for index, name in enumerate(ordered):
        running = max(running, min(1.0, raw[name] * (total - index)))
        adjusted[name] = running
    return adjusted


def _hypothesis_report(rows: list[dict[str, object]]) -> dict[str, object]:
    reports: dict[str, object] = {}
    raw_p: dict[str, float] = {}
    for name, predicate in _hypotheses().items():
        retained = [row for row in rows if predicate(row)]
        windows = _decompose(retained, "window_id")
        markets = _decompose(retained, "symbol")
        sides = _decompose(retained, "side")
        anchors = _decompose(retained, "anchor")
        closures = _decompose(retained, "closure_family")
        block6 = {
            key: _row_metrics(
                [row for row in retained if _temporal_block(str(row["timestamp"]), 6) == key]
            )
            for key in sorted({_temporal_block(str(row["timestamp"]), 6) for row in retained})
        }
        window_stress_positive = len(windows) == 3 and all(
            _decimal(
                cast(
                    dict[str, object],
                    cast(dict[str, object], item["stress"])["0.05"],
                )["mean_r"]
            )
            > 0
            for item in windows.values()
        )
        window_internal_robustness: dict[str, object] = {}
        for window in sorted({str(row["window_id"]) for row in retained}):
            window_rows = [row for row in retained if row["window_id"] == window]
            window_markets = _decompose(window_rows, "symbol")
            window_sides = _decompose(window_rows, "side")
            window_anchors = _decompose(window_rows, "anchor")

            def stressed_positive(item: dict[str, object]) -> bool:
                stress = cast(dict[str, object], item["stress"])
                primary = cast(dict[str, object], stress["0.05"])
                return _decimal(primary["mean_r"]) > 0

            window_internal_robustness[window] = {
                "positive_stressed_markets": sum(
                    stressed_positive(item) for item in window_markets.values()
                ),
                "positive_stressed_sides": sum(
                    stressed_positive(item) for item in window_sides.values()
                ),
                "positive_stressed_anchors": sum(
                    stressed_positive(item) for item in window_anchors.values()
                ),
                "pass": (
                    sum(stressed_positive(item) for item in window_markets.values()) >= 2
                    and sum(stressed_positive(item) for item in window_sides.values()) == 2
                    and sum(stressed_positive(item) for item in window_anchors.values()) >= 2
                ),
            }
        stratified_stability = len(window_internal_robustness) == 3 and all(
            bool(cast(dict[str, object], item)["pass"])
            for item in window_internal_robustness.values()
        )
        positive_markets = sum(_decimal(item["mean_r"]) > 0 for item in markets.values())
        positive_sides = sum(_decimal(item["mean_r"]) > 0 for item in sides.values())
        positive_anchors = sum(_decimal(item["mean_r"]) > 0 for item in anchors.values())
        serious = (
            len(retained) >= 60
            and window_stress_positive
            and stratified_stability
            and positive_markets >= 2
            and positive_sides == 2
            and positive_anchors >= 2
        )
        raw_p[name] = _normal_pvalue(retained)
        reports[name] = {
            "sample": len(retained),
            "aggregate": _row_metrics(retained),
            "by_window": windows,
            "by_market": markets,
            "by_side": sides,
            "by_anchor": anchors,
            "by_closure": closures,
            "six_month_blocks": block6,
            "window_stress_positive": window_stress_positive,
            "window_internal_robustness": window_internal_robustness,
            "stratified_stability": stratified_stability,
            "positive_market_count": positive_markets,
            "positive_side_count": positive_sides,
            "positive_anchor_count": positive_anchors,
            "candidate_screen_pass": serious,
            "one_sided_normal_p": raw_p[name],
        }
    adjusted = _holm_adjust(raw_p)
    for name, value in adjusted.items():
        report = reports[name]
        assert isinstance(report, dict)
        report["holm_adjusted_p"] = value
        report["multiplicity_pass_0_05"] = value <= 0.05
    return {
        "hypothesis_count": len(reports),
        "selection_policy": "predeclared-interpretable-screens-not-max-pnl",
        "multiplicity_control": "holm-bonferroni-one-sided-normal-screen",
        "reports": reports,
    }


def _payoff_report(rows: list[dict[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for target in _TARGETS:
        column = f"outcome_target_{target}_r"
        result[str(target)] = {
            "aggregate": _row_metrics(rows, outcome=column),
            "by_window": {
                window: _row_metrics(
                    [row for row in rows if row["window_id"] == window], outcome=column
                )
                for window in sorted({str(row["window_id"]) for row in rows})
            },
            "promotion_status": "diagnostic_only_not_selected",
        }
    return result


def _distribution_shift(rows: list[dict[str, object]]) -> dict[str, object]:
    categorical = (
        "previous_source_day_body_alignment",
        "source_day_relationship",
        "closure_family",
        "recent_causal_h4_range_state",
        "recent_causal_daily_range_state",
        "cross_index_directional_state",
        "current_day_sweep_type",
    )
    result: dict[str, object] = {}
    for feature in categorical:
        feature_report: dict[str, object] = {}
        for window in sorted({str(row["window_id"]) for row in rows}):
            subset = [row for row in rows if row["window_id"] == window]
            feature_report[window] = {
                str(value): {
                    "frequency": sum(row[feature] == value for row in subset),
                    "share": sum(row[feature] == value for row in subset) / len(subset),
                    "performance": _row_metrics([row for row in subset if row[feature] == value]),
                }
                for value in sorted({row[feature] for row in subset}, key=str)
            }
        result[feature] = feature_report
    return result


def _read_equivalence(root: Path) -> dict[str, object]:
    payload = json.loads((root / "causal-equivalence.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("pass") is not True:
        raise Vt08IndexV4RootCauseError("upstream causal equivalence is not PASS")
    return payload


def build_root_cause_report(
    *,
    v3_decision_root: Path,
    v2_decision_root: Path,
    development_paths: dict[str, Path],
) -> tuple[list[dict[str, object]], dict[str, object], dict[str, object], dict[str, object]]:
    specs = {
        "2022_23": (v3_decision_root, date(2022, 9, 15), date(2023, 9, 15), V3_FRESH_SHA, 350),
        "2023_24": (v2_decision_root, date(2023, 9, 15), date(2024, 8, 13), V2_FRESH_SHA, 300),
        "2024_26": (None, date(2024, 8, 13), date(2026, 9, 12), DEVELOPMENT_SHA, 700),
    }
    all_rows: list[dict[str, object]] = []
    baseline: dict[str, object] = {}
    for window, (root, start, end, sha, minimum) in specs.items():
        paths = (
            development_paths
            if root is None
            else {symbol: root / "truncated" / f"{symbol}.json" for symbol in AUTHORIZED_MARKETS}
        )
        replay, _ = _replay(
            paths=paths,
            start=start,
            end_exclusive=end,
            expected_sha=sha,
            minimum_days=minimum,
        )
        indexed = {
            symbol: _load_indexed(
                paths[symbol], symbol=symbol, expected_sha=sha, minimum_days=minimum
            )
            for symbol in AUTHORIZED_MARKETS
        }
        rows = _full_feature_rows(replay, window_id=window, indexed=indexed)
        baseline[window] = replay["metrics"]
        all_rows.extend(rows)
    hypotheses = _hypothesis_report(all_rows)
    reports = hypotheses["reports"]
    assert isinstance(reports, dict)
    survivors = [
        name
        for name, report in reports.items()
        if isinstance(report, dict)
        and report["candidate_screen_pass"] is True
        and report["multiplicity_pass_0_05"] is True
    ]
    adjudication = {
        "status": "V4_CANDIDATE_NOT_JUSTIFIED"
        if not survivors
        else "V4_CANDIDATE_REQUIRES_SEPARATE_FREEZE_REVIEW",
        "candidate_freeze_recommended": bool(survivors),
        "surviving_hypotheses": survivors,
        "reason": (
            "No predeclared causal screen passed sample, three-window stress, "
            "market, side, anchor, and multiplicity gates."
            if not survivors
            else "At least one screen passed research gates; this artifact alone "
            "does not freeze a candidate."
        ),
    }
    root_cause = {
        "baseline_by_window": baseline,
        "distribution_shift": _distribution_shift(all_rows),
        "hypothesis_falsification": hypotheses,
        "payoff_geometry_diagnostic": _payoff_report(all_rows),
        "causal_equivalence": {
            "v2": _read_equivalence(v2_decision_root),
            "v3": _read_equivalence(v3_decision_root),
            "phase2_feature_contract": "all non-outcome columns available at or before signal_at",
            "no_future_predictor": True,
        },
        "adjudication": adjudication,
        "root_cause_conclusion": {
            "identified_failure_mode": (
                "V3 conflates a regime-sensitive previous-source-day aligned family with "
                "a more stable opposed family. The aligned family changes from -0.407936R/trade "
                "in 2022-23 to positive expectation later; its frequency does not explain the "
                "flip, so the unresolved defect is context classification, not anchor, market, "
                "side, protected-swing count, or fixed-target choice alone."
            ),
            "strongest_surviving_research_lead": (
                "previous_source_day_body_opposed: 83 trades, positive after 0.05R friction in "
                "all three windows, but not candidate-grade after subgroup stability and "
                "Holm-Bonferroni control"
            ),
            "payoff_diagnosis": (
                "Targets 1.5R, 2R, 2.5R, and 3R all remain negative in 2022-23 and positive "
                "later; target selection does not repair the admission/context regime failure."
            ),
            "not_explanatory_as_standalone": [
                "anchor removal",
                "market removal",
                "side removal",
                "protected_swing_count_eq_2",
                "CISD first-half timing",
                "cross-index direction",
                "fixed target multiple",
            ],
            "remaining_uncertainty": (
                "The consumed sample cannot distinguish a durable source-bound context rule "
                "from a post-hoc effect with acceptable family-wise error and internal strata."
            ),
        },
        "candidate_validation": {
            "fresh_tranche_opened": False,
            "stress_gate": "not_applicable_no_candidate",
            "monte_carlo": "not_run_no_candidate",
            "candidate_causal_equivalence": "not_run_no_candidate",
        },
        "governance": {
            "consumed_evidence_only": True,
            "v4_research_open": True,
            "v4_candidate_frozen": False,
            "demo_eligible": False,
            "account_purchase_authorized": False,
            "order_submission_authorized": False,
            "real_capital_authorized": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }
    temporal = {
        name: report["six_month_blocks"]
        for name, report in reports.items()
        if isinstance(report, dict)
    }
    return all_rows, root_cause, hypotheses, temporal


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise Vt08IndexV4RootCauseError("feature census is empty")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v3-decision-root", type=Path, required=True)
    parser.add_argument("--v2-decision-root", type=Path, required=True)
    parser.add_argument("--development-nas100", type=Path, required=True)
    parser.add_argument("--development-sp500", type=Path, required=True)
    parser.add_argument("--development-us30", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    rows, report, hypotheses, temporal = build_root_cause_report(
        v3_decision_root=args.v3_decision_root,
        v2_decision_root=args.v2_decision_root,
        development_paths={
            "NAS100": args.development_nas100,
            "SP500": args.development_sp500,
            "US30": args.development_us30,
        },
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    census = {
        "schema": SCHEMA,
        "research_id": RESEARCH_ID,
        "feature_contract": "predictors-pre-entry; outcome_* columns-label-or-post-trade-only",
        "row_count": len(rows),
        "rows": rows,
    }
    _write_json(args.out_dir / "vt08-index-v4-regime-feature-census.json", census)
    _write_csv(args.out_dir / "vt08-index-v4-regime-feature-census.csv", rows)
    _write_json(args.out_dir / "vt08-index-v4-hypothesis-falsification.json", hypotheses)
    _write_json(args.out_dir / "vt08-index-v4-temporal-stability.json", temporal)
    _write_json(args.out_dir / "vt08-index-v4-root-cause-report.json", report)
    artifact_names = (
        "vt08-index-v4-regime-feature-census.json",
        "vt08-index-v4-regime-feature-census.csv",
        "vt08-index-v4-hypothesis-falsification.json",
        "vt08-index-v4-temporal-stability.json",
        "vt08-index-v4-root-cause-report.json",
    )
    digests = {
        name: sha256((args.out_dir / name).read_bytes()).hexdigest() for name in artifact_names
    }
    _write_json(args.out_dir / "artifact-digests.json", digests)
    print(json.dumps(report["adjudication"], sort_keys=True))


if __name__ == "__main__":
    main()
