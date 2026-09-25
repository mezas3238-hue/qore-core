"""VT08 Index shadow falsification for Shared stop-vs-target discrimination.

Phase-1 only. This lab does NOT change stops, targets, sizing, entries, trade
count, market selection, or economics. It asks whether Shared can causally
separate possible terminal-stop paths from possible target-reaching paths
before the canonical VT08 outcome is known.

Realized outcome is read only after classification to score the shadow
hypothesis. All runtime classifications use bars closed by the assessment time.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median

import vt08_index_shared_full_stack_no_sizing_v3 as v3

from qore.infrastructure.core_stack_v2.path_intelligence import (
    PositionPathObservation,
    assess_position_path,
)
from qore.infrastructure.core_stack_v2.stop_target_discrimination import (
    StopTargetHypothesis,
    assess_stop_target_path,
)

SCHEMA = "qore.shared.vt08_index.stop_target_discrimination.v6"
IDENTITY = "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6"
ZERO = Decimal("0")
TARGET_R = Decimal("2.5")


def _clip(value: int) -> int:
    return max(0, min(10_000, int(value)))


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _signed_r(signal: object, price: Decimal) -> Decimal:
    risk = abs(_d(signal.entry) - _d(signal.stop))
    if risk <= ZERO:
        return ZERO
    if str(signal.side.value).lower() == "long":
        return (price - _d(signal.entry)) / risk
    return (_d(signal.entry) - price) / risk


def _path_observation(
    *,
    signal: object,
    bar: object,
    latest: object,
    environment: object,
    trajectory: object,
    max_mfe: Decimal,
    max_mae: Decimal,
) -> PositionPathObservation:
    risk = abs(_d(signal.entry) - _d(signal.stop))
    side = str(signal.side.value).lower()
    close_r = _signed_r(signal, _d(bar.close))
    body_r = (
        (_d(bar.close) - _d(bar.open)) / risk
        if side == "long"
        else (_d(bar.open) - _d(bar.close)) / risk
    )
    progress_bps = _clip(
        int(max(ZERO, max_mfe) / TARGET_R * Decimal(10_000))
    )
    return PositionPathObservation(
        as_of=bar.closed_at.astimezone(UTC),
        data_integrity_bps=latest.data_integrity_bps,
        journey_progress_bps=progress_bps,
        close_support_bps=_clip(int(Decimal(5_000) + close_r * Decimal(2_500))),
        directional_efficiency_bps=latest.momentum_bps,
        favorable_excursion_bps=progress_bps,
        adverse_excursion_bps=_clip(
            int(max(ZERO, max_mae) * Decimal(10_000))
        ),
        favorable_body_bps=_clip(
            int(max(ZERO, body_r) * Decimal(10_000))
        ),
        adverse_body_bps=_clip(
            int(max(ZERO, -body_r) * Decimal(10_000))
        ),
        market_support_bps=environment.market_support_bps,
        environment_adverse_bps=environment.adverse_environment_bps,
        recovery_evidence_bps=_clip(
            (
                trajectory.recovery_velocity_bps
                + environment.recovery_velocity_bps
            )
            // 2
        ),
    )


def _shadow_trade(
    item: object,
    *,
    bars_by_symbol: dict[str, Sequence[object]],
    closed_by_symbol: dict[str, tuple[datetime, ...]],
) -> dict[str, object]:
    signal = item.opportunity.signal
    symbol = str(signal.symbol)
    side = str(signal.side.value).lower()
    risk = abs(_d(signal.entry) - _d(signal.stop))
    terminal_r = _d(item.outcome.r_multiple)
    actual = "LOSS" if terminal_r < ZERO else "WIN" if terminal_r > ZERO else "FLAT"

    entry = v3._entry_assessment(
        item,
        bars_by_symbol=bars_by_symbol,
        closed_by_symbol=closed_by_symbol,
        closed_memory=(),
    )
    entry_shadow = assess_stop_target_path(
        entry["environment"],
        entry["trajectory"],
        entry["geometry"],
        entry["futures"],
    )

    all_bars = bars_by_symbol[symbol]
    closed = closed_by_symbol[symbol]
    start = bisect.bisect_right(closed, signal.signal_at.astimezone(UTC))
    end = bisect.bisect_right(closed, item.exited_at.astimezone(UTC))
    observed = tuple(all_bars[start:end])

    path_history: list[PositionPathObservation] = []
    rows: list[dict[str, object]] = [
        {
            "stage": "ENTRY",
            "as_of": signal.signal_at.astimezone(UTC).isoformat(),
            "bar_index": 0,
            "bars_before_canonical_exit": len(observed),
            "hypothesis": entry_shadow.hypothesis.value,
            "agreement_bps": entry_shadow.structural_agreement_bps,
            "terminal_relations": entry_shadow.terminal_relation_count,
            "target_relations": entry_shadow.target_relation_count,
            "recovery_relations": entry_shadow.recovery_relation_count,
        }
    ]

    max_mfe = ZERO
    max_mae = ZERO
    if risk > ZERO:
        for idx, bar in enumerate(observed, start=1):
            if side == "long":
                max_mfe = max(max_mfe, (_d(bar.high) - _d(signal.entry)) / risk)
                max_mae = max(max_mae, (_d(signal.entry) - _d(bar.low)) / risk)
            else:
                max_mfe = max(max_mfe, (_d(signal.entry) - _d(bar.low)) / risk)
                max_mae = max(max_mae, (_d(bar.high) - _d(signal.entry)) / risk)

            as_of = bar.closed_at.astimezone(UTC)
            history = v3._history(
                item,
                bars_by_symbol=bars_by_symbol,
                closed_by_symbol=closed_by_symbol,
                as_of=as_of,
            )
            trajectory = v3._trajectory(history)
            environment = v3._environment(history)
            geometry = v3._geometry(history)
            futures = v3._competing_futures(history)
            latest = history[-1]
            path_history.append(
                _path_observation(
                    signal=signal,
                    bar=bar,
                    latest=latest,
                    environment=environment,
                    trajectory=trajectory,
                    max_mfe=max_mfe,
                    max_mae=max_mae,
                )
            )
            path = assess_position_path(
                tuple(path_history[-min(v3.PATH_WINDOW, len(path_history)):])
            )
            shadow = assess_stop_target_path(
                environment,
                trajectory,
                geometry,
                futures,
                path=path,
            )
            rows.append(
                {
                    "stage": "PATH",
                    "as_of": as_of.isoformat(),
                    "bar_index": idx,
                    "bars_before_canonical_exit": len(observed) - idx,
                    "hypothesis": shadow.hypothesis.value,
                    "agreement_bps": shadow.structural_agreement_bps,
                    "terminal_relations": shadow.terminal_relation_count,
                    "target_relations": shadow.target_relation_count,
                    "recovery_relations": shadow.recovery_relation_count,
                    "path_state": path.state.value,
                }
            )

    decisive = [
        row
        for row in rows
        if row["hypothesis"]
        in {
            StopTargetHypothesis.STOP_LIKELY.value,
            StopTargetHypothesis.TARGET_LIKELY.value,
        }
    ]
    first_decisive = None if not decisive else decisive[0]
    first_stop = next(
        (
            row
            for row in rows
            if row["hypothesis"] == StopTargetHypothesis.STOP_LIKELY.value
        ),
        None,
    )
    first_target = next(
        (
            row
            for row in rows
            if row["hypothesis"] == StopTargetHypothesis.TARGET_LIKELY.value
        ),
        None,
    )

    return {
        "trade_id": item.trade_id,
        "market": symbol,
        "signal_at": signal.signal_at.astimezone(UTC).isoformat(),
        "exited_at": item.exited_at.astimezone(UTC).isoformat(),
        "terminal_r": str(terminal_r),
        "actual": actual,
        "entry_hypothesis": entry_shadow.hypothesis.value,
        "first_decisive": first_decisive,
        "first_stop": first_stop,
        "first_target": first_target,
        "hypothesis_counts": dict(
            sorted(Counter(str(row["hypothesis"]) for row in rows).items())
        ),
        "observations": rows,
    }


def _safe_ratio(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0"
    return str(Decimal(numerator) / Decimal(denominator))


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, object]:
    source_window_id = {
        "five_year": "5Y",
        "recent_two_year": "2Y",
        "r66_consumed_failed_holdout": "R66",
    }[window_id]
    canonical, bars_raw, provenance = v3.v2.r74._load_window(
        roots=roots,
        window_id=source_window_id,
    )
    start_date, end_date, expected = v3.v2.r74._window_contract(source_window_id)
    bars_by_symbol = {
        symbol: tuple(rows)
        for symbol, rows in bars_raw.items()
    }
    opened_by_symbol = {
        symbol: tuple(bar.opened_at.astimezone(UTC) for bar in rows)
        for symbol, rows in bars_by_symbol.items()
    }
    closed_by_symbol = {
        symbol: tuple(bar.closed_at.astimezone(UTC) for bar in rows)
        for symbol, rows in bars_by_symbol.items()
    }
    base, _ = v3.v2.r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars_by_symbol,
    )
    control, _ = v3.v2.r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=v3.v2.r102.POLICY_EXPLICIT_FULL,
    )
    control = v3.v2._unitize(tuple(control))
    if len(control) != expected:
        raise ValueError(f"VT08 Shared stop-target {window_id} density drift")

    rows = tuple(
        _shadow_trade(
            item,
            bars_by_symbol=bars_by_symbol,
            closed_by_symbol=closed_by_symbol,
        )
        for item in control
    )
    baseline = v3.v2.r108._bundle(
        control,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=source_window_id,
        start_date=start_date,
        end_date=end_date,
    )

    losses = [row for row in rows if row["actual"] == "LOSS"]
    winners = [row for row in rows if row["actual"] == "WIN"]
    decisive = [row for row in rows if row["first_decisive"] is not None]
    predicted_stop = [
        row
        for row in decisive
        if row["first_decisive"]["hypothesis"]
        == StopTargetHypothesis.STOP_LIKELY.value
    ]
    predicted_target = [
        row
        for row in decisive
        if row["first_decisive"]["hypothesis"]
        == StopTargetHypothesis.TARGET_LIKELY.value
    ]
    true_stop = [row for row in predicted_stop if row["actual"] == "LOSS"]
    false_stop = [row for row in predicted_stop if row["actual"] == "WIN"]
    true_target = [row for row in predicted_target if row["actual"] == "WIN"]
    false_target = [row for row in predicted_target if row["actual"] == "LOSS"]
    losses_detected = [row for row in losses if row["first_stop"] is not None]
    winners_detected = [row for row in winners if row["first_target"] is not None]
    winner_false_stop_any = [row for row in winners if row["first_stop"] is not None]
    loss_false_target_any = [row for row in losses if row["first_target"] is not None]

    stop_leads = [
        int(row["first_stop"]["bars_before_canonical_exit"])
        for row in losses_detected
    ]
    target_leads = [
        int(row["first_target"]["bars_before_canonical_exit"])
        for row in winners_detected
    ]

    return {
        "window_id": window_id,
        "sample": len(rows),
        "canonical_expected": expected,
        "density_retained_shadow": "1",
        "baseline": baseline,
        "phase_1_contract": {
            "shadow_only": True,
            "stop_mutation_used": False,
            "target_mutation_used": False,
            "trailing_used": False,
            "target_extension_used": False,
            "sizing_used": False,
            "risk_weighting_used": False,
            "signal_suppression_used": False,
            "future_outcome_input_used": False,
            "realized_outcome_used_for_scoring_only": True,
        },
        "discrimination": {
            "losses": len(losses),
            "winners": len(winners),
            "decisive_trades": len(decisive),
            "decisive_coverage": _safe_ratio(len(decisive), len(rows)),
            "predicted_stop": len(predicted_stop),
            "predicted_target": len(predicted_target),
            "stop_true_positive": len(true_stop),
            "stop_false_positive": len(false_stop),
            "stop_precision": _safe_ratio(len(true_stop), len(predicted_stop)),
            "loss_stop_recall": _safe_ratio(len(losses_detected), len(losses)),
            "target_true_positive": len(true_target),
            "target_false_positive": len(false_target),
            "target_precision": _safe_ratio(len(true_target), len(predicted_target)),
            "winner_target_recall": _safe_ratio(len(winners_detected), len(winners)),
            "winner_false_stop_rate_anytime": _safe_ratio(
                len(winner_false_stop_any),
                len(winners),
            ),
            "loss_false_target_rate_anytime": _safe_ratio(
                len(loss_false_target_any),
                len(losses),
            ),
            "median_stop_lead_bars": None if not stop_leads else str(median(stop_leads)),
            "median_target_lead_bars": None if not target_leads else str(median(target_leads)),
        },
        "entry_hypothesis_counts": dict(
            sorted(Counter(str(row["entry_hypothesis"]) for row in rows).items())
        ),
        "rows": list(rows),
        "provenance": provenance,
    }


def run(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "challenge": {
            "source_pr": 604,
            "source_head": v3.VT08_HEAD,
            "shared_is_only_cognitive_engine": True,
            "vt08_role": "METHODOLOGY_VALID_FALSIFICATION_SURFACE_ONLY",
            "vt08_cognition_used_by_shared": False,
            "vt31_cognition_used_by_shared": False,
            "phase": "PHASE_1_NATURAL_DD_DISCRIMINATION",
            "management_actuation_forbidden": True,
            "stop_target_discrimination_required": True,
            "same_opportunity_universe": True,
            "same_initial_position_size": True,
            "sizing_used": False,
        },
        "five_year": _window(roots=roots, window_id="five_year"),
        "recent_two_year": _window(roots=roots, window_id="recent_two_year"),
        "r66_consumed_failed_holdout": _window(
            roots=roots,
            window_id="r66_consumed_failed_holdout",
        ),
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_opened": False,
            "trailing_used": False,
            "target_extension_used": False,
            "sizing_used": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(v3._jsonable(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "five_year": payload["five_year"]["discrimination"],
                "recent_two_year": payload["recent_two_year"]["discrimination"],
                "r66": payload["r66_consumed_failed_holdout"]["discrimination"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
