"""Edge-only early no-progress frontier for VT31 NAS100.

Revalidates the pre-existing VT31 scratch hypothesis on the equal-risk OCO
population:
- after N fully closed post-fill M1 bars;
- maximum favorable excursion remains < +0.25R;
- checkpoint close is <= -0.25R;
- exit at the next M1 open if it has not already opened through original
  stop/target.

No admission, sizing, target, leverage, volume or future outcome is used.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_cognitive_structural_protection_frontier_v1 as ps
import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    assess_full_cognitive_position,
)

SCHEMA = "qore.vt31.nas100.edge_only_early_no_progress.v1"
MARKET = "NAS100"
MFE_LIMIT_R = Decimal("0.25")
ADVERSE_CLOSE_R = Decimal("-0.25")
VARIANTS = {
    "BASELINE": None,
    "SCRATCH_5M": 5,
    "SCRATCH_8M": 8,
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _level_touched_at_open(
    *,
    side: str,
    opened: Decimal,
    stop: Decimal,
    target: Decimal,
) -> bool:
    if side == "long":
        return opened <= stop or opened >= target
    return opened >= stop or opened <= target


def _apply_scratch(
    *,
    day_bars: tuple[object, ...],
    setup: object,
    baseline: dict[str, object],
    checkpoint_bars: int,
) -> tuple[dict[str, object], str]:
    updated = dict(baseline)
    if baseline["status"] != "terminal":
        return updated, "baseline-non-terminal"

    side = str(getattr(getattr(setup, "side"), "value"))
    entry = _d(getattr(setup, "entry_price"))
    stop = _d(getattr(setup, "stop_price"))
    target = _d(getattr(setup, "target_price"))
    risk = abs(entry - stop)
    if risk <= 0:
        return updated, "invalid-risk"

    filled_at = datetime.fromisoformat(cast(str, baseline["filled_at"]))
    original_exit_at = datetime.fromisoformat(cast(str, baseline["exit_at"]))

    observed: list[object] = []
    checkpoint_bar: object | None = None
    for bar in day_bars:
        opened_at = cast(datetime, getattr(bar, "opened_at"))
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        if opened_at < filled_at:
            continue
        if closed_at >= original_exit_at:
            break
        observed.append(bar)
        if len(observed) == checkpoint_bars:
            checkpoint_bar = bar
            break

    if checkpoint_bar is None:
        return updated, "checkpoint-not-reached"

    max_favorable = Decimal(0)
    for bar in observed:
        favorable, _ = specialist.baseline._favorable_adverse(
            bar,
            side,
            entry,
            risk,
        )
        max_favorable = max(max_favorable, favorable)

    checkpoint_close = _d(getattr(checkpoint_bar, "close"))
    close_r = (
        (checkpoint_close - entry) / risk
        if side == "long"
        else (entry - checkpoint_close) / risk
    )
    updated["scratch_checkpoint_mfe_r"] = format(max_favorable, "f")
    updated["scratch_checkpoint_close_r"] = format(close_r, "f")

    if not (
        max_favorable < MFE_LIMIT_R
        and close_r <= ADVERSE_CLOSE_R
    ):
        return updated, "condition-not-met"

    checkpoint_at = cast(datetime, getattr(checkpoint_bar, "closed_at"))
    next_bar = next(
        (
            bar
            for bar in day_bars
            if cast(datetime, getattr(bar, "opened_at")) == checkpoint_at
        ),
        None,
    )
    if next_bar is None:
        return updated, "next-m1-missing"

    next_opened_at = cast(datetime, getattr(next_bar, "opened_at"))
    if next_opened_at >= original_exit_at:
        return updated, "baseline-exit-precedes-next-open"

    opened = _d(getattr(next_bar, "open"))
    if _level_touched_at_open(
        side=side,
        opened=opened,
        stop=stop,
        target=target,
    ):
        return updated, "next-open-through-original-level"

    exit_r = (
        (opened - entry) / risk
        if side == "long"
        else (entry - opened) / risk
    )
    updated["r_multiple"] = format(exit_r, "f")
    updated["exit_at"] = next_opened_at.astimezone(UTC).isoformat()
    updated["exit_reason"] = "early-no-progress-scratch-next-m1-open"
    updated["scratch_applied"] = True
    return updated, "scratch-applied"


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("early no-progress requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = oco.Vt31R22ExecutionPolicy()
    trades: dict[str, list[dict[str, object]]] = {
        variant: [] for variant in VARIANTS
    }
    statuses: dict[str, Counter[str]] = {
        variant: Counter() for variant in VARIANTS
    }

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            continue
        timeline = oco._timeline(
            day_bars,
            evidence_fingerprint=evidence,
        )
        if timeline is None:
            continue
        selected, _ = oco._select_oco(day_bars, timeline, policy)
        if selected is None:
            continue

        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        ) = context_by_day[local_day]
        observation_at = selected.decision_at
        session_prefix = tuple(
            bar
            for bar in session
            if cast(datetime, getattr(bar, "closed_at")) <= observation_at
        )
        state = specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            session_prefix,
            timeline.source,
            selected,
            observation_at,
        )
        situation = cognition_lab._reconstruct_situation(
            state=state,
            selected=selected,
            source=timeline.source,
            observation_at=observation_at,
        )
        reasoning = cognition_lab._reconstruct_reasoning(state)
        cognition = assess_full_cognitive_position(
            situation=situation,
            reasoning=reasoning,
            entry_tier="CORE",
            dol1_acceptance_observed=None,
        )

        baseline = specialist.baseline._simulate(day_bars, selected)
        trade_id = ps._trade_id(local_day=local_day, selected=selected)

        for variant, checkpoint in VARIANTS.items():
            if checkpoint is None:
                outcome = dict(baseline)
                status = str(baseline["status"])
            else:
                outcome, status = _apply_scratch(
                    day_bars=day_bars,
                    setup=selected,
                    baseline=baseline,
                    checkpoint_bars=checkpoint,
                )
            statuses[variant][status] += 1
            if outcome["status"] != "terminal":
                continue
            row = dict(outcome)
            row["trade_id"] = trade_id
            row["entry_family"] = selected.selected_family.value
            row["destination_state"] = cognition.destination_state
            row["management_context"] = cognition.management_context.value
            row["support_score"] = cognition.support_score
            row["caution_score"] = cognition.caution_score
            row["last_structure_event_family"] = state[
                "last_structure_event_family"
            ]
            row["path_not_compressed"] = (
                "REASONING_CONTRADICTION:"
                "SITUATION:CURRENT_PATH_NOT_COMPRESSED"
                in cognition.signal_codes
            )
            row["reference_volatility_state"] = state[
                "reference_volatility_state"
            ]
            trades[variant].append(row)

    baseline_rows = trades["BASELINE"]
    variants: dict[str, object] = {}
    for variant, rows in trades.items():
        variants[variant] = {
            "terminal_count": len(rows),
            "scratch_applied_count": sum(
                row.get("scratch_applied") is True for row in rows
            ),
            "normalized_metrics": ps._normalized_metrics(rows),
            "monte_carlo": specialist._monte_carlo(rows),
            "winner_preservation_vs_baseline": ps._winner_preservation(
                baseline_rows,
                rows,
            ),
            "status_counts": dict(sorted(statuses[variant].items())),
            "exit_reasons": dict(
                sorted(
                    Counter(
                        str(row["exit_reason"]) for row in rows
                    ).items()
                )
            ),
        }

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "scratch_contract": {
            "mfe_limit_r": format(MFE_LIMIT_R, "f"),
            "adverse_close_r": format(ADVERSE_CLOSE_R, "f"),
            "checkpoints_m1": [5, 8],
            "exit_timing": "next-m1-open",
        },
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "variants": variants,
        "trade_rows": trades,
        "governance": {
            "consumed_evidence_only": True,
            "preexisting_hypothesis_revalidation": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "target_changed": False,
            "checkpoint_closed_m1_only": True,
            "exit_next_m1_open": True,
            "future_outcome_runtime_input": False,
            "future_journey_runtime_input": False,
            "normalized_equal_r_economics": True,
            "capital_weighted_net_r_used": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "partial_exit_required": False,
            "absolute_volume_used": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"variants": payload["variants"]}, sort_keys=True))


if __name__ == "__main__":
    main()
