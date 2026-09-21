"""Temporal breathing-context falsification for QORE Capitalizer Stop Intelligence.

This laboratory explains Order-Block overshoot using facts available no later than entry.
Development (2016-09-17..2021-09-17) is allowed to generate threshold hypotheses.
The already-consumed 2021-09-17..2026-09-17 window may only falsify those thresholds.

The outcome under study is deliberately narrow:
- OB_OVERSHOOT_THEN_TARGET: the M1 path exceeded the distal validated OB extreme and
  later reached the unchanged target in the same session.
- OB_BREAK_NO_TARGET: the M1 path exceeded the distal OB extreme and the unchanged
  target did not arrive in-session.

Same-bar target/overshoot ambiguity is excluded from threshold selection. OB-held trades are
reported in the penetration dossier but are not used to learn "breathing after OB break".

No result freezes a stop buffer or promotes an economic rule.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)

IDENTITY = "QORE_CAPITALIZER_STOP_BREATHING_CONTEXT_V2"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_STOP_BREATHING_CONTEXT_MATRIX_V2"
PENETRATION_IDENTITY = "QORE_CAPITALIZER_OB_PENETRATION_INTELLIGENCE_V1"
FORENSIC_IDENTITY = "QORE_CAPITALIZER_M1_LOSS_CAUSAL_FORENSICS_V1"
POSITIVE_PATH = "OB_OVERSHOOT_THEN_TARGET"
NEGATIVE_PATH = "OB_BREAK_NO_TARGET"
AMBIGUOUS_PATH = "OB_OVERSHOOT_TARGET_SAME_BAR_AMBIGUOUS"
MIN_SIDE_OVERSHOOTS = 30
DEV_MIN_GAP = Decimal("0.08")
HOLD_MIN_GAP = Decimal("0.05")
CATEGORICAL_MAX_DELTA = Decimal("0.10")

BASE_FEATURES = (
    "setup_age_minutes",
    "retest_delay_minutes",
    "planned_reward_r",
    "fvg_width_r",
    "order_block_width_r",
    "ob_fvg_overlap_r",
    "distance_ob_to_mss_r",
    "displacement_body_ratio",
    "displacement_range_vs_prior20",
    "displacement_body_vs_prior20",
    "displacement_range_r",
    "displacement_body_r",
    "session_elapsed_minutes",
    "session_remaining_minutes",
    "order_block_candle_count",
    "pre_entry_peak_extension_r",
    "pre_entry_peak_extension_speed_r_per_minute",
    "pre_entry_mean_bar_range_r",
    "pre_entry_mean_bar_body_r",
    "prior20_median_range_r",
    "order_block_width_vs_prior20_range",
    "fvg_width_vs_prior20_range",
    "distance_ob_to_mss_vs_prior20_range",
)
CATEGORICAL_FEATURES = (
    "side",
    "retest_phase",
    "source_event_signature",
    "ny_entry_hour",
    "order_block_candle_count_state",
)


@dataclass(slots=True)
class _PreEntryPathState:
    row: dict[str, Any]
    start_at: datetime
    entry_at: datetime
    side: str
    ob_low: Decimal
    ob_high: Decimal
    risk: Decimal
    bars: int = 0
    peak_extension: Decimal = Decimal("0")
    peak_close_extension: Decimal = Decimal("0")
    peak_at: datetime | None = None
    range_sum: Decimal = Decimal("0")
    body_sum: Decimal = Decimal("0")
    ranges: list[Decimal] | None = None
    bodies: list[Decimal] | None = None

    def __post_init__(self) -> None:
        self.ranges = []
        self.bodies = []

    @property
    def proximal(self) -> Decimal:
        return self.ob_high if self.side == "LONG" else self.ob_low


@dataclass(frozen=True, slots=True)
class CapitalizerBreathingThresholdAudit:
    feature: str
    threshold_quantile: str
    threshold: str
    development_lower_overshoots: int
    development_upper_overshoots: int
    development_lower_target_rate: str
    development_upper_target_rate: str
    development_gap_upper_minus_lower: str
    development_direction: str
    consumed_holdout_lower_overshoots: int
    consumed_holdout_upper_overshoots: int
    consumed_holdout_lower_target_rate: str
    consumed_holdout_upper_target_rate: str
    consumed_holdout_gap_upper_minus_lower: str
    consumed_holdout_direction: str
    direction_transported: bool
    context_clue_transported: bool
    threshold_selected_on_development_only: bool = True
    consumed_holdout_used_for_threshold_selection: bool = False
    buffer_frozen: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerBreathingCategorySlice:
    feature: str
    state: str
    development_overshoots: int
    development_target_rate: str
    consumed_holdout_overshoots: int
    consumed_holdout_target_rate: str
    absolute_rate_delta: str
    temporally_stable_slice: bool
    buffer_frozen: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerStopBreathingContextReport:
    identity: str
    symbol: str
    session: str
    development_trades: int
    consumed_holdout_trades: int
    development_evaluable_overshoots: int
    consumed_holdout_evaluable_overshoots: int
    development_breathing_success_rate: str
    consumed_holdout_breathing_success_rate: str
    threshold_audits: tuple[CapitalizerBreathingThresholdAudit, ...]
    categorical_slices: tuple[CapitalizerBreathingCategorySlice, ...]
    transported_context_clues: tuple[str, ...]
    pre_entry_path_features_present: bool = True
    first_retest_entry_contract_constant: bool = True
    fresh_repeat_discriminator_available: bool = False
    pre_entry_reclaim_discriminator_available: bool = False
    post_entry_reclaim_used_for_initial_stop: bool = False
    historical_spread_at_entry_available: bool = False
    historical_broker_tick_size_available: bool = False
    development_outcome_used_for_hypothesis_generation: bool = True
    consumed_holdout_used_for_threshold_selection: bool = False
    buffer_candidate_frozen: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _aware(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("breathing-context timestamps must be timezone-aware")
    return result


def _decimal(row: dict[str, Any], key: str) -> Decimal:
    value = row.get(key)
    if value is None:
        raise ValueError(f"breathing-context row missing {key}")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError(f"{key} must be finite")
    return result


def _optional_decimal(row: dict[str, Any], key: str) -> Decimal | None:
    value = row.get(key)
    if value is None:
        return None
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError(f"{key} must be finite")
    return result


def _one_json(root: Path, pattern: str, identity: str) -> dict[str, Any]:
    paths = sorted(root.rglob(pattern))
    if len(paths) != 1:
        raise ValueError(f"expected one {pattern}, got {len(paths)}")
    raw = json.loads(paths[0].read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("identity") != identity:
        raise ValueError(f"unexpected identity for {pattern}")
    return raw


def _jsonl(root: Path, pattern: str) -> list[dict[str, Any]]:
    paths = sorted(root.rglob(pattern))
    if len(paths) != 1:
        raise ValueError(f"expected one {pattern}, got {len(paths)}")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("breathing-context ledger row must be object")
            rows.append(raw)
    if not rows:
        raise ValueError("breathing-context ledger cannot be empty")
    return rows


def _trade_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row["higher_setup_signal_at"]),
        str(row["entry_at"]),
        str(row["side"]),
    )


def _source_signature(row: dict[str, Any]) -> str:
    labels = row.get("source_event_labels")
    if not isinstance(labels, list) or not labels:
        return "NO_SOURCE_EVENT_LABEL"
    if not all(isinstance(item, str) and item for item in labels):
        raise ValueError("source_event_labels must contain strings")
    return "+".join(sorted(labels))


def _merge_window(
    penetration_root: Path,
    forensic_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    pen_report = _one_json(
        penetration_root,
        "capitalizer-*-ob-penetration-intelligence-v1.json",
        PENETRATION_IDENTITY,
    )
    pen_rows = _jsonl(
        penetration_root,
        "capitalizer-*-ob-penetration-intelligence-v1-trades.jsonl",
    )
    forensic_report = _one_json(
        forensic_root,
        "capitalizer-*-m1-loss-causal-forensics-v1.json",
        FORENSIC_IDENTITY,
    )
    forensic_rows = _jsonl(
        forensic_root,
        "capitalizer-*-m1-loss-causal-forensics-v1-ledger.jsonl",
    )
    if pen_report["symbol"] != forensic_report["symbol"]:
        raise ValueError("penetration/forensic symbol mismatch")
    if pen_report["session"] != forensic_report["session"]:
        raise ValueError("penetration/forensic session mismatch")
    forensic_index = {_trade_key(row): row for row in forensic_rows}
    if len(forensic_index) != len(forensic_rows):
        raise ValueError("duplicate forensic trade key")
    merged: list[dict[str, Any]] = []
    for pen in pen_rows:
        source = forensic_index.get(_trade_key(pen))
        if source is None:
            raise ValueError("penetration trade missing forensic match")
        row = dict(pen)
        for key, value in source.items():
            if key not in row:
                row[key] = value
        row["source_event_signature"] = _source_signature(source)
        delay = int(source["retest_delay_minutes"])
        row["retest_phase"] = "IMMEDIATE_RETEST" if delay == 0 else "LATER_RETEST"
        row["ny_entry_hour"] = int(
            _aware(str(source["entry_at"])).astimezone(
                ZoneInfo("America/New_York")
            ).hour
        )
        row["order_block_candle_count_state"] = str(
            int(source["order_block_candle_count"])
        )
        merged.append(row)
    if len(merged) != len(pen_rows):
        raise ValueError("breathing-context merge lost penetration rows")
    return pen_report, merged


def _extension(state: _PreEntryPathState, bar: CapitalizerM1Bar) -> Decimal:
    if state.side == "LONG":
        return max(Decimal("0"), bar.high - state.ob_high)
    return max(Decimal("0"), state.ob_low - bar.low)


def _close_extension(state: _PreEntryPathState, bar: CapitalizerM1Bar) -> Decimal:
    if state.side == "LONG":
        return max(Decimal("0"), bar.close - state.ob_high)
    return max(Decimal("0"), state.ob_low - bar.close)


def _enrich_pre_entry_paths(
    windows: tuple[list[dict[str, Any]], ...],
    m1_root: Path,
) -> None:
    starts: dict[datetime, list[_PreEntryPathState]] = defaultdict(list)
    all_states: list[_PreEntryPathState] = []
    for rows in windows:
        for row in rows:
            start_at = _aware(str(row["m1_fvg_confirmed_at"]))
            entry_at = _aware(str(row["entry_at"]))
            if start_at > entry_at:
                raise ValueError("FVG confirmation cannot follow entry")
            entry = _decimal(row, "entry_price")
            stop = _decimal(row, "stop_price")
            risk = abs(entry - stop)
            if risk <= 0:
                raise ValueError("pre-entry path requires positive baseline risk")
            state = _PreEntryPathState(
                row=row,
                start_at=start_at,
                entry_at=entry_at,
                side=str(row["side"]),
                ob_low=_decimal(row, "m1_order_block_low"),
                ob_high=_decimal(row, "m1_order_block_high"),
                risk=risk,
            )
            starts[start_at].append(state)
            all_states.append(state)

    active: list[_PreEntryPathState] = []
    pending_starts = set(starts)
    for bar in iter_cibo_m1(m1_root):
        at = bar.opened_at
        if at in starts:
            active.extend(starts[at])
            pending_starts.discard(at)
        if not active:
            if not pending_starts and all(state.entry_at <= at for state in all_states):
                break
            continue

        retained: list[_PreEntryPathState] = []
        for state in active:
            if at >= state.entry_at:
                continue
            ext = _extension(state, bar)
            close_ext = _close_extension(state, bar)
            state.bars += 1
            state.range_sum += bar.range
            state.body_sum += bar.body
            assert state.ranges is not None
            assert state.bodies is not None
            state.ranges.append(bar.range)
            state.bodies.append(bar.body)
            if ext > state.peak_extension:
                state.peak_extension = ext
                state.peak_at = bar.closed_at
            state.peak_close_extension = max(state.peak_close_extension, close_ext)
            retained.append(state)
        active = retained

    if pending_starts:
        raise ValueError("native M1 clone missed FVG-confirmation starts")

    for state in all_states:
        elapsed_to_peak = Decimal("1")
        if state.peak_at is not None:
            seconds = Decimal(str((state.peak_at - state.start_at).total_seconds()))
            elapsed_to_peak = max(Decimal("1"), seconds / Decimal("60"))
        row = state.row
        row["pre_entry_expansion_bars"] = state.bars
        row["pre_entry_peak_extension_r"] = str(state.peak_extension / state.risk)
        row["pre_entry_peak_close_extension_r"] = str(
            state.peak_close_extension / state.risk
        )
        row["pre_entry_peak_extension_speed_r_per_minute"] = str(
            (state.peak_extension / state.risk) / elapsed_to_peak
        )
        row["pre_entry_mean_bar_range_r"] = (
            "0"
            if state.bars == 0
            else str((state.range_sum / Decimal(state.bars)) / state.risk)
        )
        row["pre_entry_mean_bar_body_r"] = (
            "0"
            if state.bars == 0
            else str((state.body_sum / Decimal(state.bars)) / state.risk)
        )
        row["pre_entry_median_bar_range_r"] = (
            "0"
            if not state.ranges
            else str(median(state.ranges) / state.risk)
        )
        row["pre_entry_median_bar_body_r"] = (
            "0"
            if not state.bodies
            else str(median(state.bodies) / state.risk)
        )


def _add_derived_pretrade_features(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        displacement_range_r = _optional_decimal(row, "displacement_range_r")
        range_ratio = _optional_decimal(row, "displacement_range_vs_prior20")
        if (
            displacement_range_r is not None
            and range_ratio is not None
            and range_ratio > 0
        ):
            prior20_range_r = displacement_range_r / range_ratio
            row["prior20_median_range_r"] = str(prior20_range_r)
            if prior20_range_r > 0:
                row["order_block_width_vs_prior20_range"] = str(
                    _decimal(row, "order_block_width_r") / prior20_range_r
                )
                row["fvg_width_vs_prior20_range"] = str(
                    _decimal(row, "fvg_width_r") / prior20_range_r
                )
                row["distance_ob_to_mss_vs_prior20_range"] = str(
                    _decimal(row, "distance_ob_to_mss_r") / prior20_range_r
                )
        else:
            row["prior20_median_range_r"] = None
            row["order_block_width_vs_prior20_range"] = None
            row["fvg_width_vs_prior20_range"] = None
            row["distance_ob_to_mss_vs_prior20_range"] = None


def _evaluable_overshoots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if str(row["ob_penetration_path_classification"])
        in {POSITIVE_PATH, NEGATIVE_PATH}
    ]


def _is_positive(row: dict[str, Any]) -> bool:
    return str(row["ob_penetration_path_classification"]) == POSITIVE_PATH


def _rate(rows: list[dict[str, Any]]) -> Decimal:
    if not rows:
        return Decimal("0")
    return Decimal(sum(_is_positive(row) for row in rows)) / Decimal(len(rows))


def _quantile(values: list[Decimal], fraction: Decimal) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = int(
        (Decimal(len(ordered) - 1) * fraction).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    return ordered[index]


def _feature_values(rows: list[dict[str, Any]], feature: str) -> list[Decimal]:
    result: list[Decimal] = []
    for row in rows:
        value = _optional_decimal(row, feature)
        if value is not None:
            result.append(value)
    return result


def _direction(gap: Decimal) -> str:
    if gap > 0:
        return "HIGHER_FEATURE_MORE_BREATHING"
    if gap < 0:
        return "LOWER_FEATURE_MORE_BREATHING"
    return "NO_SEPARATION"


def _partition(
    rows: list[dict[str, Any]],
    feature: str,
    threshold: Decimal,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lower: list[dict[str, Any]] = []
    upper: list[dict[str, Any]] = []
    for row in rows:
        value = _optional_decimal(row, feature)
        if value is None:
            continue
        (lower if value < threshold else upper).append(row)
    return lower, upper


def _threshold_audit(
    *,
    feature: str,
    development_all: list[dict[str, Any]],
    development_overshoots: list[dict[str, Any]],
    holdout_overshoots: list[dict[str, Any]],
) -> CapitalizerBreathingThresholdAudit | None:
    values = _feature_values(development_all, feature)
    if len(values) < 100:
        return None
    candidates: list[
        tuple[Decimal, Decimal, str, list[dict[str, Any]], list[dict[str, Any]]]
    ] = []
    for label, fraction in (
        ("Q25", Decimal("0.25")),
        ("Q50", Decimal("0.50")),
        ("Q75", Decimal("0.75")),
    ):
        threshold = _quantile(values, fraction)
        if threshold is None:
            continue
        lower, upper = _partition(development_overshoots, feature, threshold)
        if min(len(lower), len(upper)) < MIN_SIDE_OVERSHOOTS:
            continue
        gap = _rate(upper) - _rate(lower)
        candidates.append((abs(gap), threshold, label, lower, upper))
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            -item[0],
            abs(Decimal(item[2][1:]) / Decimal("100") - Decimal("0.5")),
            item[2],
        )
    )
    _, threshold, label, dev_lower, dev_upper = candidates[0]
    hold_lower, hold_upper = _partition(holdout_overshoots, feature, threshold)
    dev_low_rate = _rate(dev_lower)
    dev_up_rate = _rate(dev_upper)
    hold_low_rate = _rate(hold_lower)
    hold_up_rate = _rate(hold_upper)
    dev_gap = dev_up_rate - dev_low_rate
    hold_gap = hold_up_rate - hold_low_rate
    dev_direction = _direction(dev_gap)
    hold_direction = _direction(hold_gap)
    transported = (
        dev_direction == hold_direction
        and dev_direction != "NO_SEPARATION"
        and min(len(hold_lower), len(hold_upper)) >= MIN_SIDE_OVERSHOOTS
    )
    clue = (
        transported
        and abs(dev_gap) >= DEV_MIN_GAP
        and abs(hold_gap) >= HOLD_MIN_GAP
    )
    return CapitalizerBreathingThresholdAudit(
        feature=feature,
        threshold_quantile=label,
        threshold=str(threshold),
        development_lower_overshoots=len(dev_lower),
        development_upper_overshoots=len(dev_upper),
        development_lower_target_rate=str(dev_low_rate),
        development_upper_target_rate=str(dev_up_rate),
        development_gap_upper_minus_lower=str(dev_gap),
        development_direction=dev_direction,
        consumed_holdout_lower_overshoots=len(hold_lower),
        consumed_holdout_upper_overshoots=len(hold_upper),
        consumed_holdout_lower_target_rate=str(hold_low_rate),
        consumed_holdout_upper_target_rate=str(hold_up_rate),
        consumed_holdout_gap_upper_minus_lower=str(hold_gap),
        consumed_holdout_direction=hold_direction,
        direction_transported=transported,
        context_clue_transported=clue,
    )


def _category_value(row: dict[str, Any], feature: str) -> str:
    return str(row[feature])


def _categorical_slices(
    *,
    development_overshoots: list[dict[str, Any]],
    holdout_overshoots: list[dict[str, Any]],
) -> tuple[CapitalizerBreathingCategorySlice, ...]:
    results: list[CapitalizerBreathingCategorySlice] = []
    for feature in CATEGORICAL_FEATURES:
        dev_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        hold_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in development_overshoots:
            dev_groups[_category_value(row, feature)].append(row)
        for row in holdout_overshoots:
            hold_groups[_category_value(row, feature)].append(row)
        for state in sorted(dev_groups.keys() & hold_groups.keys()):
            dev = dev_groups[state]
            hold = hold_groups[state]
            if min(len(dev), len(hold)) < MIN_SIDE_OVERSHOOTS:
                continue
            dev_rate = _rate(dev)
            hold_rate = _rate(hold)
            delta = abs(dev_rate - hold_rate)
            results.append(
                CapitalizerBreathingCategorySlice(
                    feature=feature,
                    state=state,
                    development_overshoots=len(dev),
                    development_target_rate=str(dev_rate),
                    consumed_holdout_overshoots=len(hold),
                    consumed_holdout_target_rate=str(hold_rate),
                    absolute_rate_delta=str(delta),
                    temporally_stable_slice=delta <= CATEGORICAL_MAX_DELTA,
                )
            )
    return tuple(
        sorted(
            results,
            key=lambda item: (
                item.feature,
                not item.temporally_stable_slice,
                item.state,
            ),
        )
    )


def build_market_report(
    development_penetration_root: Path,
    development_forensic_root: Path,
    holdout_penetration_root: Path,
    holdout_forensic_root: Path,
    m1_root: Path,
) -> CapitalizerStopBreathingContextReport:
    dev_report, dev_rows = _merge_window(
        development_penetration_root,
        development_forensic_root,
    )
    hold_report, hold_rows = _merge_window(
        holdout_penetration_root,
        holdout_forensic_root,
    )
    if dev_report["symbol"] != hold_report["symbol"]:
        raise ValueError("development/holdout symbol mismatch")
    if dev_report["session"] != hold_report["session"]:
        raise ValueError("development/holdout session mismatch")

    _enrich_pre_entry_paths((dev_rows, hold_rows), m1_root)
    _add_derived_pretrade_features(dev_rows)
    _add_derived_pretrade_features(hold_rows)

    dev_over = _evaluable_overshoots(dev_rows)
    hold_over = _evaluable_overshoots(hold_rows)
    if not dev_over or not hold_over:
        raise ValueError("breathing-context audit requires evaluable overshoots")

    audits = tuple(
        audit
        for feature in BASE_FEATURES
        if (
            audit := _threshold_audit(
                feature=feature,
                development_all=dev_rows,
                development_overshoots=dev_over,
                holdout_overshoots=hold_over,
            )
        )
        is not None
    )
    category_slices = _categorical_slices(
        development_overshoots=dev_over,
        holdout_overshoots=hold_over,
    )
    clues = tuple(
        audit.feature
        for audit in audits
        if audit.context_clue_transported
    )

    return CapitalizerStopBreathingContextReport(
        identity=IDENTITY,
        symbol=str(dev_report["symbol"]),
        session=str(dev_report["session"]),
        development_trades=len(dev_rows),
        consumed_holdout_trades=len(hold_rows),
        development_evaluable_overshoots=len(dev_over),
        consumed_holdout_evaluable_overshoots=len(hold_over),
        development_breathing_success_rate=str(_rate(dev_over)),
        consumed_holdout_breathing_success_rate=str(_rate(hold_over)),
        threshold_audits=audits,
        categorical_slices=category_slices,
        transported_context_clues=clues,
    )


def write_market_report(
    report: CapitalizerStopBreathingContextReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        f"capitalizer-{report.symbol.lower()}-stop-breathing-context-v2.json"
    )
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-stop-breathing-context-v2.json"))
    if len(paths) != 9:
        raise ValueError(f"breathing-context matrix requires 9 reports, got {len(paths)}")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    expected = {
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
    if {str(report["symbol"]) for report in reports} != expected:
        raise ValueError("breathing-context universe mismatch")
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "development_trades": sum(int(r["development_trades"]) for r in reports),
        "consumed_holdout_trades": sum(int(r["consumed_holdout_trades"]) for r in reports),
        "development_evaluable_overshoots": sum(
            int(r["development_evaluable_overshoots"]) for r in reports
        ),
        "consumed_holdout_evaluable_overshoots": sum(
            int(r["consumed_holdout_evaluable_overshoots"]) for r in reports
        ),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "markets_with_transported_context_clues": [
            {
                "symbol": report["symbol"],
                "clues": report["transported_context_clues"],
            }
            for report in sorted(reports, key=lambda item: str(item["symbol"]))
            if report["transported_context_clues"]
        ],
        "first_retest_entry_contract_constant": True,
        "fresh_repeat_discriminator_available": False,
        "pre_entry_reclaim_discriminator_available": False,
        "post_entry_reclaim_used_for_initial_stop": False,
        "historical_spread_at_entry_available": False,
        "historical_broker_tick_size_available": False,
        "development_outcome_used_for_hypothesis_generation": True,
        "consumed_holdout_used_for_threshold_selection": False,
        "buffer_candidate_frozen": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-stop-breathing-context-v2.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("development_penetration_root", type=Path)
    market.add_argument("development_forensic_root", type=Path)
    market.add_argument("holdout_penetration_root", type=Path)
    market.add_argument("holdout_forensic_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report = build_market_report(
            args.development_penetration_root,
            args.development_forensic_root,
            args.holdout_penetration_root,
            args.holdout_forensic_root,
            args.m1_root,
        )
        write_market_report(report, args.output)
        print(
            json.dumps(
                {
                    "identity": report.identity,
                    "symbol": report.symbol,
                    "development_overshoots": report.development_evaluable_overshoots,
                    "holdout_overshoots": report.consumed_holdout_evaluable_overshoots,
                    "transported_context_clues": report.transported_context_clues,
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
