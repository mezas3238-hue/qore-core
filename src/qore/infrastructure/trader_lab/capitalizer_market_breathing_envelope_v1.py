"""Market-specific breathing envelope audit for QORE Capitalizer Stop Intelligence.

Uses the development-only context thresholds from Breathing Context V2 to identify coherent
OB-break cases (0 or 1 degraded pre-entry factors) and degraded cases (2 or 3 factors).

For coherent development cases that actually overshot the validated M1 Order Block and later
reached the unchanged target in-session, this lab measures P50/P75/P90 breathing depth.

Each development-derived envelope is then carried unchanged into the already-consumed
2021-09-17..2026-09-17 window. The audit reports both:
- recovery coverage: coherent target-recovery paths that fit strictly inside the envelope;
- failure survival: coherent no-target paths that also fit strictly inside the envelope.

That second number is essential: a wider stop is not credited merely for keeping a losing
trade alive.

Research only. No envelope is frozen as an executable stop, no entry is changed, and no
holdout outcome selects a quantile.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_stop_breathing_context_v2 import (
    BASE_FEATURES,
    COMPOSITE_CORE_FEATURES,
    NEGATIVE_PATH,
    POSITIVE_PATH,
    CapitalizerBreathingThresholdAudit,
    _add_derived_pretrade_features,
    _degraded_count,
    _enrich_pre_entry_paths,
    _evaluable_overshoots,
    _merge_window,
    _quantile,
    _threshold_audit,
)

__all__ = ["NEGATIVE_PATH", "POSITIVE_PATH"]

IDENTITY = "QORE_CAPITALIZER_MARKET_BREATHING_ENVELOPE_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_BREATHING_ENVELOPE_MATRIX_V1"
QUANTILES: tuple[tuple[str, Decimal], ...] = (
    ("P50", Decimal("0.50")),
    ("P75", Decimal("0.75")),
    ("P90", Decimal("0.90")),
)
FX_SYMBOLS = frozenset(
    {
        "AUDJPY",
        "AUDUSD",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "USDCAD",
        "USDJPY",
    }
)


@dataclass(frozen=True, slots=True)
class CapitalizerBreathingEnvelopeAudit:
    quantile: str
    development_threshold_r: str
    development_threshold_absolute: str
    absolute_unit: str
    development_threshold_provider_increments: str
    development_recovery_cases: int
    development_recovery_coverage_r: str
    consumed_holdout_recovery_cases: int
    consumed_holdout_failure_cases: int
    consumed_holdout_recovery_coverage_r: str
    consumed_holdout_failure_survival_rate_r: str
    consumed_holdout_target_rate_inside_r_envelope: str
    consumed_holdout_recovery_coverage_absolute: str
    consumed_holdout_failure_survival_rate_absolute: str
    consumed_holdout_target_rate_inside_absolute_envelope: str
    development_only_threshold: bool = True
    consumed_holdout_selected_threshold: bool = False
    executable_buffer_frozen: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerMarketBreathingEnvelopeReport:
    identity: str
    symbol: str
    session: str
    composite_core_features: tuple[str, ...]
    development_total_trades: int
    consumed_holdout_total_trades: int
    development_evaluable_overshoots: int
    consumed_holdout_evaluable_overshoots: int
    development_coherent_overshoots: int
    development_degraded_overshoots: int
    consumed_holdout_coherent_overshoots: int
    consumed_holdout_degraded_overshoots: int
    development_coherent_recovery_cases: int
    consumed_holdout_coherent_recovery_cases: int
    consumed_holdout_coherent_failure_cases: int
    development_coherent_target_rate: str
    development_degraded_target_rate: str
    consumed_holdout_coherent_target_rate: str
    consumed_holdout_degraded_target_rate: str
    composite_direction_transported: bool
    envelopes: tuple[CapitalizerBreathingEnvelopeAudit, ...]
    coherent_definition: str = "DEGRADED_FACTOR_COUNT_0_OR_1"
    degraded_definition: str = "DEGRADED_FACTOR_COUNT_2_OR_3"
    development_selects_context_thresholds: bool = True
    consumed_holdout_selects_context_thresholds: bool = False
    quantile_grid_predeclared: bool = True
    quantile_selected_for_execution: bool = False
    entry_changed: bool = False
    target_changed: bool = False
    stop_changed_in_live_runtime: bool = False
    buffer_candidate_frozen: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _decimal(row: dict[str, Any], key: str) -> Decimal:
    value = row.get(key)
    if value is None:
        raise ValueError(f"breathing envelope row missing {key}")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError(f"{key} must be finite")
    return result


def _rate(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal("0")
    return Decimal(numerator) / Decimal(denominator)


def _is_positive(row: dict[str, Any]) -> bool:
    return str(row["ob_penetration_path_classification"]) == POSITIVE_PATH


def _context_audits(
    development_rows: list[dict[str, Any]],
    development_overshoots: list[dict[str, Any]],
    holdout_overshoots: list[dict[str, Any]],
) -> tuple[CapitalizerBreathingThresholdAudit, ...]:
    return tuple(
        audit
        for feature in BASE_FEATURES
        if (
            audit := _threshold_audit(
                feature=feature,
                development_all=development_rows,
                development_overshoots=development_overshoots,
                holdout_overshoots=holdout_overshoots,
            )
        )
        is not None
    )


def _split_composite(
    rows: list[dict[str, Any]],
    audits: tuple[CapitalizerBreathingThresholdAudit, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    audit_index = {audit.feature: audit for audit in audits}
    coherent: list[dict[str, Any]] = []
    degraded: list[dict[str, Any]] = []
    for row in rows:
        count = _degraded_count(row, audit_index)
        if count is None:
            continue
        row["breathing_degraded_factor_count"] = count
        row["breathing_context_state"] = (
            "COHERENT_BREATHING_CANDIDATE"
            if count <= 1
            else "ENTRY_CONTEXT_DEGRADATION_CANDIDATE"
        )
        if count <= 1:
            coherent.append(row)
        else:
            degraded.append(row)
    if not coherent or not degraded:
        raise ValueError("breathing envelope requires coherent and degraded samples")
    return coherent, degraded


def _value_key(symbol: str) -> tuple[str, str]:
    if symbol in FX_SYMBOLS:
        return "max_ob_overshoot_pips", "PIPS"
    return "max_ob_overshoot_beyond_distal_price", "PRICE_DISTANCE"


def _strict_inside(row: dict[str, Any], key: str, threshold: Decimal) -> bool:
    return _decimal(row, key) < threshold


def _envelope(
    *,
    symbol: str,
    quantile_name: str,
    fraction: Decimal,
    development_recovered: list[dict[str, Any]],
    holdout_recovered: list[dict[str, Any]],
    holdout_failed: list[dict[str, Any]],
) -> CapitalizerBreathingEnvelopeAudit:
    absolute_key, absolute_unit = _value_key(symbol)
    dev_r = [_decimal(row, "max_ob_overshoot_r") for row in development_recovered]
    dev_absolute = [_decimal(row, absolute_key) for row in development_recovered]
    dev_increments = [
        _decimal(row, "max_ob_overshoot_provider_increments")
        for row in development_recovered
    ]
    threshold_r = _quantile(dev_r, fraction)
    threshold_absolute = _quantile(dev_absolute, fraction)
    threshold_increments = _quantile(dev_increments, fraction)
    if (
        threshold_r is None
        or threshold_absolute is None
        or threshold_increments is None
        or threshold_r <= 0
        or threshold_absolute <= 0
        or threshold_increments <= 0
    ):
        raise ValueError("breathing envelope requires positive development thresholds")

    dev_fit_r = sum(
        _strict_inside(row, "max_ob_overshoot_r", threshold_r)
        for row in development_recovered
    )
    hold_recovery_fit_r = sum(
        _strict_inside(row, "max_ob_overshoot_r", threshold_r)
        for row in holdout_recovered
    )
    hold_failure_fit_r = sum(
        _strict_inside(row, "max_ob_overshoot_r", threshold_r)
        for row in holdout_failed
    )
    hold_recovery_fit_abs = sum(
        _strict_inside(row, absolute_key, threshold_absolute)
        for row in holdout_recovered
    )
    hold_failure_fit_abs = sum(
        _strict_inside(row, absolute_key, threshold_absolute)
        for row in holdout_failed
    )

    return CapitalizerBreathingEnvelopeAudit(
        quantile=quantile_name,
        development_threshold_r=str(threshold_r),
        development_threshold_absolute=str(threshold_absolute),
        absolute_unit=absolute_unit,
        development_threshold_provider_increments=str(threshold_increments),
        development_recovery_cases=len(development_recovered),
        development_recovery_coverage_r=str(
            _rate(dev_fit_r, len(development_recovered))
        ),
        consumed_holdout_recovery_cases=len(holdout_recovered),
        consumed_holdout_failure_cases=len(holdout_failed),
        consumed_holdout_recovery_coverage_r=str(
            _rate(hold_recovery_fit_r, len(holdout_recovered))
        ),
        consumed_holdout_failure_survival_rate_r=str(
            _rate(hold_failure_fit_r, len(holdout_failed))
        ),
        consumed_holdout_target_rate_inside_r_envelope=str(
            _rate(
                hold_recovery_fit_r,
                hold_recovery_fit_r + hold_failure_fit_r,
            )
        ),
        consumed_holdout_recovery_coverage_absolute=str(
            _rate(hold_recovery_fit_abs, len(holdout_recovered))
        ),
        consumed_holdout_failure_survival_rate_absolute=str(
            _rate(hold_failure_fit_abs, len(holdout_failed))
        ),
        consumed_holdout_target_rate_inside_absolute_envelope=str(
            _rate(
                hold_recovery_fit_abs,
                hold_recovery_fit_abs + hold_failure_fit_abs,
            )
        ),
    )


def build_market_report(
    development_penetration_root: Path,
    development_forensic_root: Path,
    holdout_penetration_root: Path,
    holdout_forensic_root: Path,
    m1_root: Path,
) -> CapitalizerMarketBreathingEnvelopeReport:
    dev_report, dev_rows = _merge_window(
        development_penetration_root,
        development_forensic_root,
    )
    hold_report, hold_rows = _merge_window(
        holdout_penetration_root,
        holdout_forensic_root,
    )
    symbol = str(dev_report["symbol"])
    session = str(dev_report["session"])
    if symbol != str(hold_report["symbol"]) or session != str(hold_report["session"]):
        raise ValueError("breathing envelope window identity mismatch")

    _enrich_pre_entry_paths((dev_rows, hold_rows), m1_root)
    _add_derived_pretrade_features(dev_rows)
    _add_derived_pretrade_features(hold_rows)
    dev_over = _evaluable_overshoots(dev_rows)
    hold_over = _evaluable_overshoots(hold_rows)

    audits = _context_audits(dev_rows, dev_over, hold_over)
    for feature in COMPOSITE_CORE_FEATURES:
        if feature not in {audit.feature for audit in audits}:
            raise ValueError(f"composite core feature unavailable: {feature}")

    dev_coherent, dev_degraded = _split_composite(dev_over, audits)
    hold_coherent, hold_degraded = _split_composite(hold_over, audits)
    dev_recovered = [row for row in dev_coherent if _is_positive(row)]
    hold_recovered = [row for row in hold_coherent if _is_positive(row)]
    hold_failed = [
        row
        for row in hold_coherent
        if str(row["ob_penetration_path_classification"]) == NEGATIVE_PATH
    ]
    if min(len(dev_recovered), len(hold_recovered), len(hold_failed)) <= 0:
        raise ValueError("breathing envelope lacks coherent outcome density")

    envelopes = tuple(
        _envelope(
            symbol=symbol,
            quantile_name=name,
            fraction=fraction,
            development_recovered=dev_recovered,
            holdout_recovered=hold_recovered,
            holdout_failed=hold_failed,
        )
        for name, fraction in QUANTILES
    )

    dev_coherent_rate = _rate(
        sum(_is_positive(row) for row in dev_coherent),
        len(dev_coherent),
    )
    dev_degraded_rate = _rate(
        sum(_is_positive(row) for row in dev_degraded),
        len(dev_degraded),
    )
    hold_coherent_rate = _rate(
        sum(_is_positive(row) for row in hold_coherent),
        len(hold_coherent),
    )
    hold_degraded_rate = _rate(
        sum(_is_positive(row) for row in hold_degraded),
        len(hold_degraded),
    )

    return CapitalizerMarketBreathingEnvelopeReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session,
        composite_core_features=COMPOSITE_CORE_FEATURES,
        development_total_trades=len(dev_rows),
        consumed_holdout_total_trades=len(hold_rows),
        development_evaluable_overshoots=len(dev_over),
        consumed_holdout_evaluable_overshoots=len(hold_over),
        development_coherent_overshoots=len(dev_coherent),
        development_degraded_overshoots=len(dev_degraded),
        consumed_holdout_coherent_overshoots=len(hold_coherent),
        consumed_holdout_degraded_overshoots=len(hold_degraded),
        development_coherent_recovery_cases=len(dev_recovered),
        consumed_holdout_coherent_recovery_cases=len(hold_recovered),
        consumed_holdout_coherent_failure_cases=len(hold_failed),
        development_coherent_target_rate=str(dev_coherent_rate),
        development_degraded_target_rate=str(dev_degraded_rate),
        consumed_holdout_coherent_target_rate=str(hold_coherent_rate),
        consumed_holdout_degraded_target_rate=str(hold_degraded_rate),
        composite_direction_transported=(
            dev_coherent_rate > dev_degraded_rate
            and hold_coherent_rate > hold_degraded_rate
        ),
        envelopes=envelopes,
    )


def write_market_report(
    report: CapitalizerMarketBreathingEnvelopeReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        f"capitalizer-{report.symbol.lower()}-market-breathing-envelope-v1.json"
    )
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-market-breathing-envelope-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"breathing envelope matrix requires 9 reports, got {len(paths)}")
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
        raise ValueError("breathing envelope universe mismatch")
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "development_total_trades": sum(
            int(report["development_total_trades"]) for report in reports
        ),
        "consumed_holdout_total_trades": sum(
            int(report["consumed_holdout_total_trades"]) for report in reports
        ),
        "composite_direction_transported_markets": [
            report["symbol"]
            for report in sorted(reports, key=lambda item: str(item["symbol"]))
            if bool(report["composite_direction_transported"])
        ],
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "quantile_grid": [name for name, _ in QUANTILES],
        "development_selects_context_thresholds": True,
        "consumed_holdout_selects_context_thresholds": False,
        "quantile_selected_for_execution": False,
        "entry_changed": False,
        "target_changed": False,
        "stop_changed_in_live_runtime": False,
        "buffer_candidate_frozen": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-breathing-envelope-v1.json"
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
                    "composite_transport": report.composite_direction_transported,
                    "envelopes": [
                        {
                            "quantile": item.quantile,
                            "threshold_r": item.development_threshold_r,
                            "threshold_absolute": item.development_threshold_absolute,
                            "absolute_unit": item.absolute_unit,
                            "hold_recovery_coverage_r": (
                                item.consumed_holdout_recovery_coverage_r
                            ),
                            "hold_failure_survival_r": (
                                item.consumed_holdout_failure_survival_rate_r
                            ),
                        }
                        for item in report.envelopes
                    ],
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
