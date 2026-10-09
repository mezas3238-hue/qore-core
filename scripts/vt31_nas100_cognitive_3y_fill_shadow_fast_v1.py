#!/usr/bin/env python3
"""Fast Trader Lab research-only fill-time shadow on immutable owner 3Y NAS100.

The specialist's original frozen entry remains executable and untouched.
Retrospective source fill is used for *labelling the opportunity T only*;
all features consumed by the revalidator are strictly closed_at <= T.
The result never applies cancellations, new sizing, or future/terminal labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.traders.vt31_nas100_fill_time_causal_sensor import (
    build_prospective_fill_observation,
)
from qore.infrastructure.traders.vt31_nas100_post_entry_cognitive_runtime import (
    revalidate_prospective_fill,
)

SCHEMA = "qore.vt31.nas100.3y_causal_fill_time_shadow.v1"
BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"


def _verified_evidence_sha(path: Path) -> str:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "base_id": BASE_ID,
        "market": "NAS100",
        "base_start_at": "2023-10-01T00:00:00+00:00",
        "base_end_exclusive": "2026-10-01T00:00:00+00:00",
        "coverage_sufficient": True,
        "consumed_for_development_after_first_inspection": True,
    }
    for key, value in expected.items():
        if evidence.get(key) != value:
            raise ValueError(f"unexpected owner-consumed 3Y evidence: {key}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ordered(c: Counter[str]) -> dict[str, int]:
    return dict(sorted(c.items()))


def audit(path: Path) -> dict[str, object]:
    digest = _verified_evidence_sha(path)
    by_action: Counter[str] = Counter()
    by_blocker: Counter[str] = Counter()
    by_disposition: Counter[str] = Counter()
    by_economics: Counter[str] = Counter()
    by_pre_fill_delay: Counter[str] = Counter()
    by_session: Counter[str] = Counter()
    source_families: Counter[str] = Counter()
    full_current_cognition_count = 0
    total_setups = 0
    actual_fill_opportunities = 0
    structural_terminal_count = 0
    zero_call_terminal_count = 0
    zero_call_rejected = 0
    revalidator_rejects = 0
    different_comp008_verdicts = 0
    diagnostics: list[dict[str, object]] = []
    original_sim = specialist._simulate_selected_plan
    original_mc = specialist._monte_carlo

    def observer(
        day_bars: tuple[Any, ...],
        selected: Any,
        state: dict[str, object],
    ) -> dict[str, object]:
        nonlocal total_setups, actual_fill_opportunities
        nonlocal structural_terminal_count, zero_call_terminal_count
        nonlocal zero_call_rejected, revalidator_rejects
        nonlocal full_current_cognition_count, different_comp008_verdicts
        total_setups += 1
        source_families[str(selected.selected_family.value)] += 1
        fill_index = specialist.v2b._fill_index(day_bars, selected)
        result: dict[str, object] | None = None
        if fill_index is not None:
            actual_fill_opportunities += 1
            fill_bar = day_bars[fill_index]
            t = cast(datetime, fill_bar.opened_at)
            entry = cognition_lab._reconstruct_situation(
                state=state,
                selected=selected,
                source=selected.source_setup,
                observation_at=selected.decision_at,
            )
            frozen = cognition_lab._reconstruct_reasoning(state)
            previous_raw = state.get("previous_admitted_path_range")
            previous_range = (
                None if previous_raw is None else Decimal(str(previous_raw))
            )
            observation = build_prospective_fill_observation(
                entry_situation=entry,
                source=selected.source_setup,
                selected_family=str(selected.selected_family.value),
                day_bars=cast(tuple[Any, ...], day_bars),
                prospective_fill_open_at=t,
                previous_admitted_path_range=previous_range,
            )
            if datetime.fromisoformat(observation.as_of) != t:
                raise AssertionError("prospective fill causal timestamp drift")
            primary = revalidate_prospective_fill(
                entry_situation=entry,
                entry_reasoning=frozen,
                observation=observation,
                prospective_fill_open_at=t,
                apply_comp008_admission=False,
            )
            stricter = revalidate_prospective_fill(
                entry_situation=entry,
                entry_reasoning=frozen,
                observation=observation,
                prospective_fill_open_at=t,
                apply_comp008_admission=True,
            )
            if primary.entry_situation_fingerprint != frozen.situation_fingerprint:
                raise AssertionError("entry reasoning was not frozen at signal")
            full_current_cognition_count += 1
            decision = primary.candidate_fill_accepted
            if not decision:
                revalidator_rejects += 1
            if decision != stricter.candidate_fill_accepted:
                different_comp008_verdicts += 1
            by_action[primary.current_reasoning_action] += 1
            by_action[
                "accept" if decision else "reject"
            ] += 1
            by_action[
                "comp008_accept" if stricter.candidate_fill_accepted
                else "comp008_reject"
            ] += 1
            for block in primary.entry_mandatory_blockers:
                by_blocker[block] += 1
            by_session["NY_AM_SILVER_BULLET"] += 1
            delay = int((t - selected.decision_at).total_seconds() // 60)
            if delay < 0:
                raise AssertionError("fill before frozen decision")
            by_pre_fill_delay["same-m1-open" if delay == 0 else "later-open"] += 1
            result = {
                "signal_at": selected.decision_at.isoformat(),
                "prospective_fill_open_at": t.isoformat(),
                "pre_fill_delay_m1": delay,
                "selected_family": selected.selected_family.value,
                "side": selected.side.value,
                "source_entry_reasoning_action": frozen.action,
                "source_entry_fingerprint": frozen.situation_fingerprint,
                "revalidated_situation_fingerprint": (
                    primary.current_situation_fingerprint
                ),
                "revalidated_reasoning_action": primary.current_reasoning_action,
                "entry_mandatory_blockers": list(
                    primary.entry_mandatory_blockers
                ),
                "post_entry_only_blockers": list(
                    primary.post_entry_only_blockers
                ),
                "candidate_fill_accepted": decision,
                "comp008_shadow_fill_accepted": (
                    stricter.candidate_fill_accepted
                ),
                "as_of_closed_m1_timestamp": observation.as_of,
                "updated_entry_evidence_freshness": (
                    observation.entry_evidence_freshness
                ),
                "updated_double_sided_sweep": (
                    observation.double_sided_before_decision
                ),
                "read_only": True,
            }

        # Only AFTER scoring the fill-time thesis do we inspect outcomes.
        structural = specialist._simulate_structural_boundary_only(
            day_bars, selected,
        )
        by_disposition[str(structural["status"])] += 1
        if result is not None:
            result["structural_status"] = structural["status"]
            if structural["status"] == "terminal":
                structural_terminal_count += 1
                exit_at = datetime.fromisoformat(str(structural["exit_at"]))
                call_count = sum(
                    bar.closed_at < exit_at
                    for bar in day_bars[fill_index + 1:]  # type: ignore[operator]
                    if specialist.baseline._local_minute(bar) <
                    specialist.LIFECYCLE_MINUTE
                )
                zero = call_count == 0
                if zero:
                    zero_call_terminal_count += 1
                    if result["candidate_fill_accepted"] is False:
                        zero_call_rejected += 1
                result["has_zero_preterminal_post_entry_m1"] = zero
                result["causal_post_fill_m1_count"] = call_count
                r = Decimal(str(structural["r_multiple"]))
                outcome_class = "winner" if r > 0 else "nonwinner"
                result["structural_r_multiple"] = format(r, "f")
                result["structural_outcome_class"] = outcome_class
                by_economics["terminal_" + outcome_class] += 1
                if result["candidate_fill_accepted"] is False:
                    by_economics["shadow_reject_" + outcome_class] += 1
                else:
                    by_economics["shadow_preserve_" + outcome_class] += 1
            diagnostics.append(result)
        return structural

    try:
        specialist._simulate_selected_plan = observer
        specialist._monte_carlo = lambda _: {
            "status": "NOT_RUN_SHADOW_ONLY",
            "paths": 0,
            "positive_terminal_probability": "0",
            "p95_max_drawdown_r": "0",
        }
        control = specialist.replay(path)
    finally:
        specialist._simulate_selected_plan = original_sim
        specialist._monte_carlo = original_mc

    if total_setups != sum(by_disposition.values()):
        raise AssertionError("all frozen control setups must be preserved")
    if int(control["trade_count"]) != by_disposition["terminal"]:
        raise AssertionError("structural terminal control drift")
    if structural_terminal_count != by_disposition["terminal"]:
        raise AssertionError("every terminal needs prospective fill revalidation")
    if actual_fill_opportunities != len(diagnostics):
        raise AssertionError("all filled outcomes require one prospective evaluation")
    return {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "source_sha256": digest,
        "selected_executable_setups": total_setups,
        "realized_fill_opportunities": actual_fill_opportunities,
        "structural_terminal_trade_count": structural_terminal_count,
        "zero_call_structural_terminal_count": zero_call_terminal_count,
        "zero_call_would_reject_count": zero_call_rejected,
        "full_causal_entry_revalidations": full_current_cognition_count,
        "candidate_shadow_rejections": revalidator_rejects,
        "comp008_different_candidate_verdict_count": different_comp008_verdicts,
        "structural_dispositions": _ordered(by_disposition),
        "source_entry_families": _ordered(source_families),
        "fill_shadow_action_counts": _ordered(by_action),
        "entry_blocker_counts": _ordered(by_blocker),
        "retrospective_structural_outcome_attribution": _ordered(by_economics),
        "signal_to_fill_open_delay": _ordered(by_pre_fill_delay),
        "session_models_seen": _ordered(by_session),
        "per_fill_ledger": diagnostics,
        "governance": {
            "research_shadow_only": True,
            "single_owner_consumed_3y_base": True,
            "runtime_action_altered": False,
            "fill_cancel_authority": False,
            "source_trade_selection_unchanged": True,
            "structural_controls_unchanged": True,
            "terminal_outcomes_not_seen_by_cognition": True,
            "retrospective_fill_index_only_labels_opportunity": True,
            "fill_bar_OHLC_excluded_from_revalidation": True,
            "fresh_holdout_opened": False,
            "session_ny_only": True,
            "london_methodology_not_assumed": True,
            "position_sizing_used": False,
            "leverage_used": False,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("evidence", type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    payload = audit(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(
        {key: value for key, value in payload.items() if key != "per_fill_ledger"},
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
