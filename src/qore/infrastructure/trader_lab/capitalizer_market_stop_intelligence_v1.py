"""Per-market Stop Intelligence dossiers for QORE Capitalizer.

This laboratory consolidates three already-governed research layers for each of the
nine Capitalizer markets:

1. STOP causal forensics (when/where/context before STOP),
2. structural breathing probes (same entry/target, wider causal M5 extremes),
3. protected-swing corrected replay proxy (same entry/target, causal CISD swing).

The output is a *market dossier*, not a promoted stop rule. It preserves the frozen
source hierarchy:

    ICT original primary -> TTrades secondary refinement -> QORE operationalization

Native M1 remains required for the final TTrades H1->M15->M1 scalp execution route.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_ict_ttrades_dual_source_fidelity_audit_v1 import (
    FROZEN_DUAL_SOURCE_FIDELITY_AUDIT,
)

IDENTITY = "QORE_CAPITALIZER_MARKET_STOP_INTELLIGENCE_LAB_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_STOP_INTELLIGENCE_MATRIX_V1"

CAUSE_IDENTITY = "QORE_CAPITALIZER_STOP_LOSS_CAUSAL_FORENSICS_V1"
BREATHING_IDENTITY = "QORE_CAPITALIZER_STRUCTURAL_STOP_BREATHING_PROBE_V1"
CORRECTION_IDENTITY = "QORE_CAPITALIZER_PROTECTED_SWING_CORRECTED_REPLAY_V1"

CAUSE_DIMENSIONS = (
    "WEEKDAY",
    "NY_HOUR",
    "SESSION_ELAPSED_HOUR",
    "SIDE",
    "EVENT_SIGNATURE",
    "EVENT_FAMILY",
    "PLANNED_REWARD_BAND",
    "RELATIVE_STOP_WIDTH_QUARTILE",
    "REPEAT_STATE",
    "RECLAIM_STATE",
    "H1_SOURCE_AGE",
    "H1_EPISODE_MULTIPLICITY",
    "H1_BOUNDARY_MULTIPLICITY",
    "SOURCE_TIMING",
    "CISD_TIMING",
    "REPEAT_X_RECLAIM",
    "RISK_X_ELAPSED",
    "RISK_X_REPEAT",
    "EVENT_X_REPEAT",
)

MARKET_SPECIFIC_SIGNAL_KEYS = (
    ("REPEAT_STATE", "REPEAT"),
    ("RECLAIM_STATE", "RECLAIM_MIXED"),
    ("SESSION_ELAPSED_HOUR", "H2"),
    ("SESSION_ELAPSED_HOUR", "H3"),
    ("RELATIVE_STOP_WIDTH_QUARTILE", "Q1_TIGHTEST"),
    ("PLANNED_REWARD_BAND", "2_TO_LT_3R"),
    ("PLANNED_REWARD_BAND", "GE_3R"),
    ("H1_EPISODE_MULTIPLICITY", "MULTI_EPISODE"),
    ("H1_BOUNDARY_MULTIPLICITY", "MULTI_SOURCE_BOUNDARY"),
)


@dataclass(frozen=True, slots=True)
class CapitalizerStopPressureSignal:
    dimension: str
    key: str
    trades: int
    stops: int
    stop_rate: str
    relative_lift: str


@dataclass(frozen=True, slots=True)
class CapitalizerMarketStopIntelligenceDossier:
    identity: str
    symbol: str
    session: str

    # Source contract / fidelity boundary.
    ict_original_primary: bool
    ttrades_secondary_refinement: bool
    qore_operationalization_explicit: bool
    structural_stop_anchor_dual_source_compatible: bool
    exact_stop_expression_universal: bool
    native_m1_required: bool
    native_m1_present: bool
    full_source_faithful_stop_replay_complete: bool

    # Baseline STOP burden.
    replay_trades: int
    stop_exits: int
    baseline_stop_rate: str

    # Full causal context.
    causal_cohorts: tuple[dict[str, Any], ...]
    elevated_stop_pressure_signals: tuple[CapitalizerStopPressureSignal, ...]
    reduced_stop_pressure_signals: tuple[CapitalizerStopPressureSignal, ...]
    recurring_signal_flags: tuple[str, ...]

    # Post-STOP behavior / premature-stop evidence.
    post_stop_recovery: dict[str, Any]
    later_target_reached_after_stop_rate: str
    later_target_reached_with_le_0_5r_extra_count: int
    later_target_reached_with_le_0_5r_extra_rate: str

    # Structural breathing sensitivity.
    breathing_modes: tuple[dict[str, Any], ...]
    lowest_dd_breathing_probe: str
    lowest_dd_breathing_probe_dd_r: str
    lowest_dd_breathing_probe_pf: str | None
    lowest_dd_probe_reaches_owner_6r: bool

    # Protected-swing correction.
    protected_swing_surrogate_coverage: str
    protected_swing_baseline_matched_metrics: dict[str, Any]
    protected_swing_corrected_matched_metrics: dict[str, Any]
    protected_swing_median_width_vs_baseline: str
    protected_swing_transitions: tuple[dict[str, Any], ...]
    protected_swing_pf_delta: str | None
    protected_swing_dd_reduction_r: str
    protected_swing_losing_streak_reduction: int
    protected_swing_reaches_owner_6r: bool

    # Research conclusion, not rule promotion.
    stop_geometry_material: bool
    entry_context_still_material: bool
    next_required_evidence: tuple[str, ...]
    rule_promotion_allowed: bool = False
    stop_rule_frozen: bool = False
    economic_candidate: bool = False
    fresh_holdout_claimed: bool = False
    trader_certified: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerNineMarketStopIntelligenceMatrix:
    identity: str
    markets: tuple[CapitalizerMarketStopIntelligenceDossier, ...]
    complete_nine_market_universe: bool
    recurring_signal_market_counts: tuple[tuple[str, int], ...]
    markets_where_stop_geometry_material: tuple[str, ...]
    markets_where_entry_context_still_material: tuple[str, ...]
    markets_reaching_owner_6r_on_any_stop_probe: tuple[str, ...]
    native_m1_required: bool = True
    native_m1_present: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False


def _read_single_json(root: Path, pattern: str) -> dict[str, Any]:
    paths = sorted(root.rglob(pattern))
    if len(paths) != 1:
        raise ValueError(f"expected exactly one {pattern}, got {len(paths)}")
    raw: Any = json.loads(paths[0].read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{pattern} must contain one JSON object")
    return raw


def _decimal(value: Any) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("stop-intelligence numeric value must be finite")
    return result


def _cohort_signal(raw: dict[str, Any]) -> CapitalizerStopPressureSignal:
    return CapitalizerStopPressureSignal(
        dimension=str(raw["dimension"]),
        key=str(raw["key"]),
        trades=int(raw["trades"]),
        stops=int(raw["stops"]),
        stop_rate=str(raw["stop_rate"]),
        relative_lift=str(raw["relative_lift"]),
    )


def _find_cohort(
    cohorts: tuple[dict[str, Any], ...],
    *,
    dimension: str,
    key: str,
) -> dict[str, Any] | None:
    matches = tuple(
        row
        for row in cohorts
        if str(row.get("dimension")) == dimension and str(row.get("key")) == key
    )
    if len(matches) > 1:
        raise ValueError(f"duplicate cohort {dimension}:{key}")
    return None if not matches else matches[0]


def _validate_cause_payload(raw: dict[str, Any]) -> None:
    if raw.get("identity") != CAUSE_IDENTITY:
        raise ValueError("unexpected stop-cause artifact identity")
    dimensions = {str(row.get("dimension")) for row in raw.get("cohorts", ())}
    missing = set(CAUSE_DIMENSIONS) - dimensions
    if missing:
        raise ValueError(f"stop-cause artifact missing dimensions: {sorted(missing)}")
    if raw.get("source_strategy_status") != "WAIT_M1_EVIDENCE":
        raise ValueError("stop-cause artifact must remain WAIT_M1_EVIDENCE")
    if raw.get("rule_promotion_allowed") is not False:
        raise ValueError("stop-cause artifact cannot promote rules")


def _validate_breathing_payload(raw: dict[str, Any]) -> None:
    if raw.get("identity") != BREATHING_IDENTITY:
        raise ValueError("unexpected breathing artifact identity")
    modes = raw.get("modes")
    if not isinstance(modes, list) or len(modes) != 3:
        raise ValueError("breathing artifact must contain exactly three modes")
    if raw.get("diagnostic_only") is not True:
        raise ValueError("breathing artifact must remain diagnostic")
    if raw.get("stop_widening_authorized") is not False:
        raise ValueError("breathing artifact cannot authorize widening")


def _validate_correction_payload(raw: dict[str, Any]) -> None:
    if raw.get("identity") != CORRECTION_IDENTITY:
        raise ValueError("unexpected protected-swing correction identity")
    if raw.get("m1_evidence_present") is not False:
        raise ValueError("protected-swing correction must remain M1 fail-closed")
    if raw.get("source_faithful_replay_complete") is not False:
        raise ValueError("protected-swing surrogate cannot claim full source replay")
    if raw.get("rule_promotion_allowed") is not False:
        raise ValueError("protected-swing surrogate cannot promote rules")


def build_market_dossier_from_payloads(
    *,
    cause: dict[str, Any],
    breathing: dict[str, Any],
    correction: dict[str, Any],
) -> CapitalizerMarketStopIntelligenceDossier:
    _validate_cause_payload(cause)
    _validate_breathing_payload(breathing)
    _validate_correction_payload(correction)

    symbols = {str(cause["symbol"]), str(breathing["symbol"]), str(correction["symbol"])}
    sessions = {
        str(cause["session"]),
        str(breathing["session"]),
        str(correction["session"]),
    }
    if len(symbols) != 1 or len(sessions) != 1:
        raise ValueError("stop-intelligence inputs must describe one market/session")

    symbol = next(iter(symbols))
    session = CapitalizerSession(next(iter(sessions)))
    if symbol not in allowed_markets(session):
        raise ValueError("stop-intelligence market/session drift")

    raw_cohorts = cause.get("cohorts")
    if not isinstance(raw_cohorts, list):
        raise ValueError("stop-cause cohorts must be a list")
    cohorts = tuple(dict(item) for item in raw_cohorts if isinstance(item, dict))
    if len(cohorts) != len(raw_cohorts):
        raise ValueError("every stop-cause cohort must be an object")

    total_trades = int(cause["trades"])
    min_sample = max(50, total_trades // 100)
    eligible = tuple(row for row in cohorts if int(row["trades"]) >= min_sample)

    elevated = tuple(
        _cohort_signal(row)
        for row in sorted(
            (row for row in eligible if _decimal(row["relative_lift"]) >= Decimal("1.05")),
            key=lambda row: (
                -_decimal(row["relative_lift"]),
                str(row["dimension"]),
                str(row["key"]),
            ),
        )[:20]
    )
    reduced = tuple(
        _cohort_signal(row)
        for row in sorted(
            (row for row in eligible if _decimal(row["relative_lift"]) <= Decimal("0.95")),
            key=lambda row: (
                _decimal(row["relative_lift"]),
                str(row["dimension"]),
                str(row["key"]),
            ),
        )[:20]
    )

    recurring_flags: list[str] = []
    for dimension, key in MARKET_SPECIFIC_SIGNAL_KEYS:
        row = _find_cohort(cohorts, dimension=dimension, key=key)
        if (
            row is not None
            and int(row["trades"]) >= min_sample
            and _decimal(row["relative_lift"]) >= Decimal("1.05")
        ):
            recurring_flags.append(f"{dimension}:{key}")

    recovery = cause.get("post_stop_recovery")
    if not isinstance(recovery, dict):
        raise ValueError("stop-cause report requires post_stop_recovery")
    stops = int(recovery["stops"])
    recovered_le_05 = int(recovery["recovered_le_0_5r"])
    recovered_le_05_rate = Decimal(recovered_le_05) / Decimal(stops)

    raw_modes = breathing.get("modes")
    assert isinstance(raw_modes, list)
    modes = tuple(dict(item) for item in raw_modes if isinstance(item, dict))
    best_mode = min(modes, key=lambda item: _decimal(item["max_drawdown_r"]))
    best_dd = _decimal(best_mode["max_drawdown_r"])

    base_ps = correction.get("baseline_matched_metrics")
    corrected_ps = correction.get("corrected_matched_metrics")
    transitions = correction.get("transitions")
    if (
        not isinstance(base_ps, dict)
        or not isinstance(corrected_ps, dict)
        or not isinstance(transitions, list)
    ):
        raise ValueError("protected-swing correction payload is incomplete")

    base_pf_raw = base_ps.get("profit_factor")
    corrected_pf_raw = corrected_ps.get("profit_factor")
    pf_delta: str | None = None
    if base_pf_raw is not None and corrected_pf_raw is not None:
        pf_delta = str(_decimal(corrected_pf_raw) - _decimal(base_pf_raw))

    dd_reduction = _decimal(base_ps["max_drawdown_r"]) - _decimal(
        corrected_ps["max_drawdown_r"]
    )
    streak_reduction = int(base_ps["max_losing_streak"]) - int(
        corrected_ps["max_losing_streak"]
    )

    stop_geometry_material = (
        dd_reduction > 0
        and pf_delta is not None
        and _decimal(pf_delta) > 0
    )
    corrected_dd = _decimal(corrected_ps["max_drawdown_r"])
    entry_context_still_material = (
        corrected_dd > Decimal("6")
        or bool(recurring_flags)
    )

    dual = FROZEN_DUAL_SOURCE_FIDELITY_AUDIT
    return CapitalizerMarketStopIntelligenceDossier(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        ict_original_primary=dual.ict_is_original_primary_source,
        ttrades_secondary_refinement=not dual.ttrades_may_override_ict,
        qore_operationalization_explicit=not dual.qore_may_masquerade_as_author,
        structural_stop_anchor_dual_source_compatible=(
            dual.current_stop_anchor_structurally_compatible
        ),
        exact_stop_expression_universal=(
            dual.current_exact_stop_expression_universally_dual_source_faithful
        ),
        native_m1_required=dual.native_m1_required_for_final_fidelity,
        native_m1_present=dual.native_m1_present,
        full_source_faithful_stop_replay_complete=dual.replay_may_claim_full_source_fidelity,
        replay_trades=total_trades,
        stop_exits=int(cause["stops"]),
        baseline_stop_rate=str(cause["baseline_stop_rate"]),
        causal_cohorts=cohorts,
        elevated_stop_pressure_signals=elevated,
        reduced_stop_pressure_signals=reduced,
        recurring_signal_flags=tuple(recurring_flags),
        post_stop_recovery=dict(recovery),
        later_target_reached_after_stop_rate=str(recovery["later_target_reached_rate"]),
        later_target_reached_with_le_0_5r_extra_count=recovered_le_05,
        later_target_reached_with_le_0_5r_extra_rate=str(recovered_le_05_rate),
        breathing_modes=modes,
        lowest_dd_breathing_probe=str(best_mode["mode"]),
        lowest_dd_breathing_probe_dd_r=str(best_mode["max_drawdown_r"]),
        lowest_dd_breathing_probe_pf=(
            None
            if best_mode.get("profit_factor") is None
            else str(best_mode["profit_factor"])
        ),
        lowest_dd_probe_reaches_owner_6r=best_dd <= Decimal("6"),
        protected_swing_surrogate_coverage=str(
            correction["protected_swing_surrogate_coverage"]
        ),
        protected_swing_baseline_matched_metrics=dict(base_ps),
        protected_swing_corrected_matched_metrics=dict(corrected_ps),
        protected_swing_median_width_vs_baseline=str(
            correction["median_corrected_stop_width_vs_baseline"]
        ),
        protected_swing_transitions=tuple(
            dict(item) for item in transitions if isinstance(item, dict)
        ),
        protected_swing_pf_delta=pf_delta,
        protected_swing_dd_reduction_r=str(dd_reduction),
        protected_swing_losing_streak_reduction=streak_reduction,
        protected_swing_reaches_owner_6r=corrected_dd <= Decimal("6"),
        stop_geometry_material=stop_geometry_material,
        entry_context_still_material=entry_context_still_material,
        next_required_evidence=(
            "NATIVE_M1_OR_FINER_EXECUTION_EVIDENCE",
            "ICT_INVALIDATION_PLUS_TTRADES_M1_PROTECTED_SWING",
            "ROUTE_SPECIFIC_EXACT_STOP_EXPRESSION",
            "MARKET_SPECIFIC_STOP_FALSEIFICATION",
            "SPREAD_SLIPPAGE_LATENCY_AFTER_STOP_FREEZE",
        ),
    )


def build_market_dossier(
    *,
    cause_root: Path,
    breathing_root: Path,
    correction_root: Path,
) -> CapitalizerMarketStopIntelligenceDossier:
    cause = _read_single_json(
        cause_root,
        "capitalizer-*-stop-loss-causal-forensics-v1.json",
    )
    breathing = _read_single_json(
        breathing_root,
        "capitalizer-*-structural-stop-breathing-v1.json",
    )
    correction = _read_single_json(
        correction_root,
        "capitalizer-*-protected-swing-corrected-replay-v1.json",
    )
    return build_market_dossier_from_payloads(
        cause=cause,
        breathing=breathing,
        correction=correction,
    )


def write_market_dossier(
    report: CapitalizerMarketStopIntelligenceDossier,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-stop-intelligence-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    base = report.protected_swing_baseline_matched_metrics
    corrected = report.protected_swing_corrected_matched_metrics
    lines = [
        f"# {report.symbol} — QORE Capitalizer Stop Intelligence V1",
        "",
        f"- Session: {report.session}",
        f"- Replay trades: {report.replay_trades}",
        f"- STOP exits: {report.stop_exits}",
        f"- Baseline STOP rate: {Decimal(report.baseline_stop_rate) * 100:.2f}%",
        "- Authority: ICT original -> TTrades refinement -> QORE operationalization.",
        "- Final M1 source-faithful stop replay: NOT COMPLETE.",
        "",
        "## Protected-swing correction",
        "",
        f"- M5 surrogate coverage: {Decimal(report.protected_swing_surrogate_coverage) * 100:.2f}%",
        f"- PF: {base['profit_factor']} -> {corrected['profit_factor']}",
        f"- DD: {base['max_drawdown_r']}R -> {corrected['max_drawdown_r']}R",
        (
            f"- Losing streak: {base['max_losing_streak']} -> "
            f"{corrected['max_losing_streak']}"
        ),
        f"- Median stop width vs baseline: {report.protected_swing_median_width_vs_baseline}x",
        "",
        "## Highest STOP-pressure cohorts",
        "",
        "| Dimension | State | Trades | STOP rate | Lift |",
        "|---|---|---:|---:|---:|",
    ]
    for item in report.elevated_stop_pressure_signals[:12]:
        lines.append(
            f"| {item.dimension} | {item.key} | {item.trades} | "
            f"{Decimal(item.stop_rate) * 100:.2f}% | {Decimal(item.relative_lift):.3f}x |"
        )

    lines.extend(
        [
            "",
            "## Post-STOP recovery",
            "",
            (
                "- Original target later reached in-session: "
                f"{Decimal(report.later_target_reached_after_stop_rate) * 100:.2f}%"
            ),
            (
                "- Later target with <=0.5R extra excursion: "
                f"{Decimal(report.later_target_reached_with_le_0_5r_extra_rate) * 100:.2f}%"
            ),
            "",
            "## Structural breathing diagnostic",
            "",
            (
                f"- Lowest-DD probe: {report.lowest_dd_breathing_probe} — "
                f"PF {report.lowest_dd_breathing_probe_pf}, "
                f"DD {report.lowest_dd_breathing_probe_dd_r}R"
            ),
            f"- Reaches Owner <=6R: {report.lowest_dd_probe_reaches_owner_6r}",
            "",
            "## Governance",
            "",
            f"- Stop geometry material: {report.stop_geometry_material}",
            f"- Entry/context still material: {report.entry_context_still_material}",
            "- No rule promotion.",
            "- No stop freeze.",
            "- No certification.",
        ]
    )
    (output / f"{stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_dossiers(root: Path) -> tuple[CapitalizerMarketStopIntelligenceDossier, ...]:
    paths = sorted(root.rglob("capitalizer-*-stop-intelligence-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"nine-market stop intelligence requires 9 dossiers, got {len(paths)}")

    dossiers: list[CapitalizerMarketStopIntelligenceDossier] = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("identity") != IDENTITY:
            raise ValueError("unexpected stop-intelligence dossier identity")
        dossiers.append(
            CapitalizerMarketStopIntelligenceDossier(
                **{
                    **raw,
                    "causal_cohorts": tuple(raw["causal_cohorts"]),
                    "elevated_stop_pressure_signals": tuple(
                        CapitalizerStopPressureSignal(**item)
                        for item in raw["elevated_stop_pressure_signals"]
                    ),
                    "reduced_stop_pressure_signals": tuple(
                        CapitalizerStopPressureSignal(**item)
                        for item in raw["reduced_stop_pressure_signals"]
                    ),
                    "recurring_signal_flags": tuple(raw["recurring_signal_flags"]),
                    "breathing_modes": tuple(raw["breathing_modes"]),
                    "protected_swing_transitions": tuple(
                        raw["protected_swing_transitions"]
                    ),
                    "next_required_evidence": tuple(raw["next_required_evidence"]),
                }
            )
        )
    return tuple(sorted(dossiers, key=lambda item: item.symbol))


def build_matrix_from_dossiers(
    dossiers: tuple[CapitalizerMarketStopIntelligenceDossier, ...],
) -> CapitalizerNineMarketStopIntelligenceMatrix:
    expected = {
        symbol
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    }
    if {item.symbol for item in dossiers} != expected:
        raise ValueError("stop-intelligence nine-market universe mismatch")

    counter: Counter[str] = Counter()
    for market in dossiers:
        counter.update(market.recurring_signal_flags)

    reaches = tuple(
        market.symbol
        for market in dossiers
        if market.lowest_dd_probe_reaches_owner_6r
        or market.protected_swing_reaches_owner_6r
    )
    return CapitalizerNineMarketStopIntelligenceMatrix(
        identity=MATRIX_IDENTITY,
        markets=dossiers,
        complete_nine_market_universe=True,
        recurring_signal_market_counts=tuple(
            sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        ),
        markets_where_stop_geometry_material=tuple(
            item.symbol for item in dossiers if item.stop_geometry_material
        ),
        markets_where_entry_context_still_material=tuple(
            item.symbol for item in dossiers if item.entry_context_still_material
        ),
        markets_reaching_owner_6r_on_any_stop_probe=reaches,
    )


def build_matrix(root: Path) -> CapitalizerNineMarketStopIntelligenceMatrix:
    return build_matrix_from_dossiers(_load_dossiers(root))


def write_matrix(
    report: CapitalizerNineMarketStopIntelligenceMatrix,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-nine-market-stop-intelligence-matrix-v1.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# QORE Capitalizer — Nine-Market Stop Intelligence Matrix V1",
        "",
        "- ICT original primary; TTrades secondary refinement; QORE operationalization.",
        "- No market stop rule is promoted or frozen by this matrix.",
        "",
        (
            "| Market | STOP rate | Top flags | Best breathing DD | "
            "PS coverage | PS PF | PS DD |"
        ),
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for market in report.markets:
        corrected = market.protected_swing_corrected_matched_metrics
        lines.append(
            f"| {market.symbol} | {Decimal(market.baseline_stop_rate) * 100:.2f}% | "
            f"{', '.join(market.recurring_signal_flags[:4]) or 'NONE'} | "
            f"{market.lowest_dd_breathing_probe_dd_r}R | "
            f"{Decimal(market.protected_swing_surrogate_coverage) * 100:.2f}% | "
            f"{corrected['profit_factor']} | {corrected['max_drawdown_r']}R |"
        )

    lines.extend(["", "## Cross-market recurring STOP-pressure signals", ""])
    lines.extend(
        f"- {signal}: {count}/9 markets"
        for signal, count in report.recurring_signal_market_counts
    )
    lines.extend(
        [
            "",
            (
                "- Stop geometry material: "
                f"{len(report.markets_where_stop_geometry_material)}/9"
            ),
            (
                "- Entry/context still material: "
                f"{len(report.markets_where_entry_context_still_material)}/9"
            ),
            (
                "- Any stop probe at <=6R: "
                f"{', '.join(report.markets_reaching_owner_6r_on_any_stop_probe) or 'NONE'}"
            ),
        ]
    )
    (output / "capitalizer-nine-market-stop-intelligence-matrix-v1.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer per-market Stop Intelligence")
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("cause_root", type=Path)
    market.add_argument("breathing_root", type=Path)
    market.add_argument("correction_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report = build_market_dossier(
            cause_root=args.cause_root,
            breathing_root=args.breathing_root,
            correction_root=args.correction_root,
        )
        write_market_dossier(report, args.output)
        print(
            json.dumps(
                {
                    "symbol": report.symbol,
                    "stop_rate": report.baseline_stop_rate,
                    "flags": list(report.recurring_signal_flags),
                    "best_breathing_dd_r": report.lowest_dd_breathing_probe_dd_r,
                    "protected_swing_dd_r": report.protected_swing_corrected_matched_metrics[
                        "max_drawdown_r"
                    ],
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
                "stop_geometry_material": list(
                    matrix_report.markets_where_stop_geometry_material
                ),
                "entry_context_still_material": list(
                    matrix_report.markets_where_entry_context_still_material
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
