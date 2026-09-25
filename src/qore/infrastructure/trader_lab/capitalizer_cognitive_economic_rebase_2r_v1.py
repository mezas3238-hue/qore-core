"""Economic/cognitive rebase of the frozen 948-trade Capitalizer universe to true 2R.

Target Sensitivity V2 established that the original 2R identity is the only V1
target-grid point whose payout accounting was valid. Source microstructure facts
remain causal because selection, entries and stops are unchanged across the target
grid. Dynamic portfolio/Journey state does *not* remain invariant because changing
the target changes exit timestamps and realized PnL known before later candidates.

This lab therefore:
- consumes the fully source-bound Cognitive Evidence Binding V2;
- consumes corrected Target Sensitivity V2 outcomes;
- freezes the 948 MAX3 trades at true 2R;
- reuses source/microstructure evidence only;
- recomputes active exposure, factor state, day/session Journey and slot state from
  the 2R lifecycle;
- attaches current-trade outcomes only for post-state diagnostics.

No cognitive rule, entry, stop, target, MAX3 or runtime policy is promoted here.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v1 as binding_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target_sensitivity_2y_v1 as target_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target_sensitivity_2y_v2 as target_v2,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_ECONOMIC_REBASE_2R_V1"
SOURCE_BINDING_RUN_ID = 36065651404
SOURCE_BINDING_SHA = "1d910f5c3550ac481c28390671a86ceb011597e3"
SOURCE_TARGET_V2_RUN_ID = 36077843102
SOURCE_TARGET_V2_SHA = "a47de3b491b4468527c945d6eff3afbbaec82d4e"
TARGET_R = Decimal("2.00")

EXPECTED_TRADES = 948
EXPECTED_STOPS = 275
EXPECTED_WINS = 483
EXPECTED_LOSSES = 465
EXPECTED_PF = Decimal("1.466020472120789368123727041")
EXPECTED_TOTAL_R = Decimal("153.9927998412621697329314877")
EXPECTED_DD_R = Decimal("12.93584837435268644582248142")
EXPECTED_LS = 7


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _join_key(row: dict[str, Any] | target_v1.TargetOutcome) -> tuple[str, str]:
    if isinstance(row, target_v1.TargetOutcome):
        return row.symbol, row.entry_at
    return str(row["symbol"]), str(row["entry_at"])


def _load_binding(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    report_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2-rows.jsonl")
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("2R rebase requires exactly one Binding V2 artifact")

    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != binding_v2.IDENTITY:
        raise ValueError("2R rebase received unexpected Binding V2 identity")
    coverage = report.get("binding_coverage")
    if not isinstance(coverage, dict):
        raise ValueError("Binding V2 coverage missing")
    if int(coverage.get("source_microstructure", -1)) != EXPECTED_TRADES:
        raise ValueError("2R rebase requires all source microstructure bound")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("2R rebase rejects future evidence")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("Binding V2 row must be an object")
            if raw.get("source_microstructure_bound") is not True:
                raise ValueError("2R rebase requires source-bound rows")
            rows.append(raw)
    if len(rows) != EXPECTED_TRADES:
        raise ValueError(f"2R rebase expected {EXPECTED_TRADES} binding rows")
    return report, tuple(rows)


def _load_2r_outcomes(root: Path) -> tuple[target_v1.TargetOutcome, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-max-recovery-target-sensitivity-2y-v2-outcomes.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"2R rebase requires 9 V2 outcome ledgers, got {len(paths)}")

    raw: list[target_v1.TargetOutcome] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                outcome = target_v1.TargetOutcome(**json.loads(line))
                if Decimal(outcome.target_r) == TARGET_R:
                    raw.append(outcome)

    if len(raw) != target_v2.EXPECTED_FINAL_RAW:
        raise ValueError("2R rebase raw trade count mismatch")
    selected = target_v1._max3(tuple(raw))
    if len(selected) != EXPECTED_TRADES:
        raise ValueError("2R rebase MAX3 trade count mismatch")
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                _aware(item.entry_at, field="entry_at"),
                item.symbol,
            ),
        )
    )


def _outcome_dict(item: target_v1.TargetOutcome) -> dict[str, Any]:
    return {
        "symbol": item.symbol,
        "session": item.session,
        "operating_date": item.operating_date,
        "side": item.side,
        "h1_open": item.h1_open,
        "h1_deadline": item.h1_deadline,
        "entry_at": item.entry_at,
        "entry_price": item.entry_price,
        "stop_price": item.stop_price,
        "target_r": item.target_r,
        "target_price": item.target_price,
        "exit_at": item.exit_at,
        "realized_gross_r": item.realized_gross_r,
        "exit_reason": item.exit_reason,
        "same_minute_stop_target_ambiguity": (
            item.same_minute_stop_target_ambiguity
        ),
        "provenance": item.provenance,
    }


def _dynamic_context(
    current: dict[str, Any],
    control: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    entry_at = _aware(current["entry_at"], field="entry_at")
    operating_date = str(current["operating_date"])
    session = str(current["session"])

    prior_entered = tuple(
        row
        for row in control
        if str(row["operating_date"]) == operating_date
        and _aware(row["entry_at"], field="entry_at") < entry_at
    )
    active = tuple(
        row
        for row in prior_entered
        if _aware(row["exit_at"], field="exit_at") > entry_at
    )
    closed = tuple(
        row
        for row in prior_entered
        if _aware(row["exit_at"], field="exit_at") <= entry_at
    )
    prior_same_session = sum(
        str(row["session"]) == session for row in prior_entered
    )
    shared, same, opposing = binding_v1._factor_relation(current, active)
    prior_realized = sum(
        (Decimal(str(row["realized_gross_r"])) for row in closed),
        Decimal("0"),
    )

    return {
        "baseline_active_positions": len(active),
        "baseline_shared_factors": list(shared),
        "baseline_same_direction_factors": list(same),
        "baseline_opposing_direction_factors": list(opposing),
        "prior_closed_trades_today": len(closed),
        "prior_realized_r_today": str(prior_realized),
        "completed_prior_sessions": list(
            binding_v1._completed_prior_sessions(session)
        ),
        "prior_same_session_selected": prior_same_session,
        "session_slots_remaining_before": max(
            0,
            MAX_EXECUTIONS_PER_SESSION - prior_same_session,
        ),
    }


def _rebase_rows(
    binding_rows: tuple[dict[str, Any], ...],
    outcomes: tuple[target_v1.TargetOutcome, ...],
) -> tuple[dict[str, Any], ...]:
    binding_by_key = {_join_key(row): row for row in binding_rows}
    if len(binding_by_key) != len(binding_rows):
        raise ValueError("Binding V2 join identity must be unique")

    control = tuple(_outcome_dict(item) for item in outcomes)
    if {_join_key(row) for row in control} != set(binding_by_key):
        raise ValueError("2R outcome identity differs from source binding identity")

    rows: list[dict[str, Any]] = []
    for current in control:
        binding = binding_by_key[_join_key(current)]
        context = _dynamic_context(current, control)
        rows.append(
            {
                "symbol": current["symbol"],
                "session": current["session"],
                "operating_date": current["operating_date"],
                "side": current["side"],
                "h1_open": current["h1_open"],
                "h1_deadline": current["h1_deadline"],
                "entry_at": current["entry_at"],
                "provenance": current["provenance"],
                "target_r": current["target_r"],
                "source_microstructure_match_found": bool(
                    binding["source_microstructure_match_found"]
                ),
                "source_microstructure_bound": bool(
                    binding["source_microstructure_bound"]
                ),
                "source_timestamps_causal": bool(
                    binding["source_timestamps_causal"]
                ),
                "evidence_provenance_complete": bool(
                    binding["evidence_provenance_complete"]
                ),
                "source_microstructure_family": binding.get(
                    "source_microstructure_family"
                ),
                "microstructure_observations": list(
                    binding["microstructure_observations"]
                ),
                "baseline_portfolio_exposure_bound": True,
                "baseline_active_positions": context[
                    "baseline_active_positions"
                ],
                "baseline_shared_factors": context["baseline_shared_factors"],
                "baseline_same_direction_factors": context[
                    "baseline_same_direction_factors"
                ],
                "baseline_opposing_direction_factors": context[
                    "baseline_opposing_direction_factors"
                ],
                "day_session_journey_bound": True,
                "prior_closed_trades_today": context[
                    "prior_closed_trades_today"
                ],
                "prior_realized_r_today": context["prior_realized_r_today"],
                "completed_prior_sessions": context[
                    "completed_prior_sessions"
                ],
                "prior_same_session_selected": context[
                    "prior_same_session_selected"
                ],
                "session_slots_remaining_before": context[
                    "session_slots_remaining_before"
                ],
                "baseline_slot_state_bound": True,
                "current_outcome_visible_to_cognitive_state": False,
                "current_outcome_attached_for_post_audit": True,
                "post_audit_exit_at": current["exit_at"],
                "post_audit_realized_gross_r": current["realized_gross_r"],
                "post_audit_exit_reason": current["exit_reason"],
                "post_audit_same_minute_stop_target_ambiguity": current[
                    "same_minute_stop_target_ambiguity"
                ],
            }
        )
    return tuple(rows)


def _metrics_by_bucket(
    outcomes: tuple[target_v1.TargetOutcome, ...],
    *,
    field: str,
) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[target_v1.TargetOutcome]] = defaultdict(list)
    for item in outcomes:
        buckets[str(getattr(item, field))].append(item)
    return {
        key: target_v1._metrics(tuple(value))
        for key, value in sorted(buckets.items())
    }


def build_report(
    binding_root: Path,
    target_v2_root: Path,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    binding_report, binding_rows = _load_binding(binding_root)
    outcomes = _load_2r_outcomes(target_v2_root)
    rows = _rebase_rows(binding_rows, outcomes)
    metrics = target_v1._metrics(outcomes)

    if int(metrics["trades"]) != EXPECTED_TRADES:
        raise ValueError("2R rebase trade control mismatch")
    if int(metrics["stop_exits"]) != EXPECTED_STOPS:
        raise ValueError("2R rebase stop control mismatch")
    if int(metrics["wins"]) != EXPECTED_WINS:
        raise ValueError("2R rebase win control mismatch")
    if int(metrics["losses"]) != EXPECTED_LOSSES:
        raise ValueError("2R rebase loss control mismatch")
    if Decimal(str(metrics["profit_factor"])) != EXPECTED_PF:
        raise ValueError("2R rebase PF control mismatch")
    if Decimal(str(metrics["total_r"])) != EXPECTED_TOTAL_R:
        raise ValueError("2R rebase total-R control mismatch")
    if Decimal(str(metrics["max_drawdown_r"])) != EXPECTED_DD_R:
        raise ValueError("2R rebase DD control mismatch")
    if int(metrics["max_losing_streak"]) != EXPECTED_LS:
        raise ValueError("2R rebase losing-streak control mismatch")

    old_by_key = {_join_key(row): row for row in binding_rows}
    dynamic_changed = 0
    active_changed = 0
    factor_changed = 0
    closed_changed = 0
    realized_changed = 0
    slot_changed = 0
    source_changed = 0

    for row in rows:
        old = old_by_key[_join_key(row)]
        active_delta = int(row["baseline_active_positions"]) != int(
            old["baseline_active_positions"]
        )
        factor_delta = any(
            tuple(row[key]) != tuple(old[key])
            for key in (
                "baseline_shared_factors",
                "baseline_same_direction_factors",
                "baseline_opposing_direction_factors",
            )
        )
        closed_delta = int(row["prior_closed_trades_today"]) != int(
            old["prior_closed_trades_today"]
        )
        realized_delta = Decimal(str(row["prior_realized_r_today"])) != Decimal(
            str(old["prior_realized_r_today"])
        )
        slot_delta = (
            int(row["prior_same_session_selected"])
            != int(old["prior_same_session_selected"])
            or int(row["session_slots_remaining_before"])
            != int(old["session_slots_remaining_before"])
        )
        source_delta = (
            tuple(row["microstructure_observations"])
            != tuple(old["microstructure_observations"])
            or row["source_microstructure_family"]
            != old.get("source_microstructure_family")
        )

        active_changed += int(active_delta)
        factor_changed += int(factor_delta)
        closed_changed += int(closed_delta)
        realized_changed += int(realized_delta)
        slot_changed += int(slot_delta)
        source_changed += int(source_delta)
        dynamic_changed += int(
            active_delta or factor_delta or closed_delta or realized_delta
        )

    provenance = Counter(item.provenance for item in outcomes)
    report = {
        "identity": IDENTITY,
        "source_binding_run_id": SOURCE_BINDING_RUN_ID,
        "source_binding_sha": SOURCE_BINDING_SHA,
        "source_target_v2_run_id": SOURCE_TARGET_V2_RUN_ID,
        "source_target_v2_sha": SOURCE_TARGET_V2_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": str(TARGET_R),
        "control_trades": len(outcomes),
        "control_metrics": metrics,
        "source_provenance_counts": dict(sorted(provenance.items())),
        "source_microstructure_reused": True,
        "source_microstructure_rows": sum(
            bool(row["source_microstructure_bound"]) for row in rows
        ),
        "portfolio_journey_recomputed_from_2r_lifecycle": True,
        "old_1r_dynamic_state_reused": False,
        "dynamic_state_delta_vs_binding_v2": {
            "trades_with_any_dynamic_change": dynamic_changed,
            "active_position_count_changed": active_changed,
            "factor_state_changed": factor_changed,
            "prior_closed_trade_count_changed": closed_changed,
            "prior_realized_r_changed": realized_changed,
            "slot_state_changed": slot_changed,
            "source_microstructure_changed": source_changed,
        },
        "simultaneous_candidates_are_not_prior_active_exposure": True,
        "by_market": _metrics_by_bucket(outcomes, field="symbol"),
        "by_session": _metrics_by_bucket(outcomes, field="session"),
        "binding_v2_source_control_reproduced": (
            int(binding_report["control_trades"]) == len(outcomes)
        ),
        "current_outcome_visible_to_cognitive_state": False,
        "current_outcome_attached_for_post_audit": True,
        "target_v1_non2r_economics_superseded": True,
        "selection_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed_from_original_2r": False,
        "max3_changed": False,
        "cognitive_rule_selected": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "RERUN_STOP_RISK_JOURNEY_AND_OPPORTUNITY_COMPETITION_ON_TRUE_2R"
        ),
    }
    return report, rows


def write_report(
    report: dict[str, Any],
    rows: tuple[dict[str, Any], ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cognitive-economic-rebase-2r-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("binding_root", type=Path)
    parser.add_argument("target_v2_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, rows = build_report(args.binding_root, args.target_v2_root)
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
