"""Reasoning-sovereignty conflict forensics for VT31 NAS100.

Consumed evidence only. No trading rule is changed.

The current density architecture may route a SECONDARY/SCOUT trade after the
core reasoning engine has emitted WAIT or ABSTAIN. This module reconstructs the
core decision and joins it to the trade that was actually authorized, so we can
measure which exact contradiction/uncertainty codes are associated with losing
streaks.

Post-outcome data is diagnostic only. Runtime causality is restricted to the
reasoning state observed before the fallback authorization.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_r5_loss_sequence_root_cause_forensics_v1 as lossfx
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.r5.reasoning_sovereignty_conflict_forensics.v1"
MARKET = "NAS100"
PROFILE_NAME = "ALLOC_G_CORE_FAMILY_050"

CONSUMED_BLOCKS = {
    "Y1_WEAK_2022-07-18_2023-07-18": (
        date(2022, 7, 18),
        date(2023, 7, 18),
    ),
    "Y2_RECOVERY_2023-07-18_2024-07-18": (
        date(2023, 7, 18),
        date(2024, 7, 18),
    ),
}


def _capture_state(
    state: dict[str, object],
    *,
    authorization_reason: str,
) -> dict[str, object]:
    return {
        "core_action": state.get("action"),
        "authorization_reason": authorization_reason,
        "reasoning_contradictions": list(
            cast(list[str], state.get("reasoning_contradictions", []))
        ),
        "reasoning_uncertainty": list(
            cast(list[str], state.get("reasoning_uncertainty", []))
        ),
        "reasoning_support": list(
            cast(list[str], state.get("reasoning_support", []))
        ),
        "decision_at": state.get("decision_at"),
        "decision_minute_ny": state.get("decision_minute_ny"),
        "entry_family": state.get("entry_evidence_family"),
        "h1_state": state.get("h1_state"),
        "h4_state": state.get("h4_state"),
        "premarket_state": state.get("premarket_state"),
        "cash_open_state": state.get("cash_open_state"),
        "reference_volatility_state": state.get(
            "reference_volatility_state"
        ),
        "current_path_vs_previous": state.get(
            "current_path_vs_previous"
        ),
        "risk_ref": state.get("risk_ref"),
        "reference_reclaim_age_minutes": state.get(
            "reference_reclaim_age_minutes"
        ),
        "confirmation_latency_minutes": state.get(
            "confirmation_latency_minutes"
        ),
        "last_structure_event_family": state.get(
            "last_structure_event_family"
        ),
    }


def _core_decisions(
    by_day: dict[date, tuple[object, ...]],
    context_by_day: dict[
        date,
        tuple[Decimal | None, Decimal | None, tuple[object, ...]],
    ],
    *,
    evidence: str,
) -> dict[date, dict[str, object]]:
    policy = Vt31R22ExecutionPolicy()
    result: dict[date, dict[str, object]] = {}

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(
            day_bars,
            (9, 0, 0),
            (10, 0, 0),
        )
        session = specialist._slice(
            day_bars,
            (10, 0, 0),
            (11, 0, 0),
        )
        if len(reference) != 60 or len(session) != 60:
            continue

        prefix = list(reference)
        previous_path_range, prior_ref_median, prior_bars = (
            context_by_day[local_day]
        )
        saw_wait = False

        for bar in session:
            prefix.append(bar)
            closed_at = cast(Any, getattr(bar, "closed_at"))
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=closed_at,
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                if saw_wait and evaluation.both_sides_swept:
                    result[local_day] = {
                        "core_action": "INVALIDATED_AFTER_WAIT",
                        "authorization_reason": (
                            "CORE_INVALIDATED_AFTER_WAIT"
                        ),
                        "reasoning_contradictions": [],
                        "reasoning_uncertainty": [],
                        "reasoning_support": [],
                        "decision_at": closed_at.isoformat(),
                    }
                    break
                continue

            executable, _ = make_executable_setup(
                evaluation.setup,
                policy,
            )
            if executable is None:
                result[local_day] = {
                    "core_action": "NON_EXECUTABLE",
                    "authorization_reason": (
                        "CORE_SOURCE_NOT_SINGLE_ROUTE_EXECUTABLE"
                    ),
                    "reasoning_contradictions": [],
                    "reasoning_uncertainty": [],
                    "reasoning_support": [],
                    "decision_at": closed_at.isoformat(),
                }
                break

            session_prefix = tuple(
                item
                for item in prefix
                if (10, 0, 0)
                <= _wall(getattr(item, "opened_at"))
                < (11, 0, 0)
            )
            state = specialist._state_snapshot(
                day_bars,
                previous_path_range,
                prior_ref_median,
                prior_bars,
                session_prefix,
                evaluation.setup,
                executable,
                closed_at,
            )
            action = str(state["action"])
            if action == "WAIT":
                saw_wait = True
                if (
                    specialist.baseline._local_minute(bar)
                    >= corrective.WAIT_RELEASE_MINUTE
                ):
                    result[local_day] = _capture_state(
                        state,
                        authorization_reason="CORE_PERSISTENT_WAIT_625",
                    )
                    break
                continue
            if action == "ABSTAIN":
                result[local_day] = _capture_state(
                    state,
                    authorization_reason="CORE_CAUSAL_ABSTAIN",
                )
                break
            if action == "EXECUTE":
                result[local_day] = _capture_state(
                    state,
                    authorization_reason="CORE_EXECUTE",
                )
                break
            raise ValueError(action)

    return result


def _is_loss(row: dict[str, object]) -> bool:
    return Decimal(cast(str, row["capital_weighted_net_r"])) < 0


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {
            "sample": 0,
            "losses": 0,
            "loss_rate": "0",
            "total_r": "0",
            "mean_r": "0",
            "severe_streak_loss_count": 0,
            "severe_streak_loss_share": "0",
            "path_counts": {},
        }

    values = [
        Decimal(cast(str, row["capital_weighted_net_r"]))
        for row in rows
    ]
    losses = [row for row in rows if _is_loss(row)]
    severe = [
        row
        for row in losses
        if bool(row.get("severe_loss_streak"))
    ]
    return {
        "sample": len(rows),
        "losses": len(losses),
        "loss_rate": format(
            Decimal(len(losses)) / Decimal(len(rows)),
            "f",
        ),
        "total_r": format(sum(values, Decimal(0)), "f"),
        "mean_r": format(
            sum(values, Decimal(0)) / Decimal(len(rows)),
            "f",
        ),
        "severe_streak_loss_count": len(severe),
        "severe_streak_loss_share": format(
            Decimal(len(severe)) / Decimal(len(losses)),
            "f",
        )
        if losses
        else "0",
        "path_counts": dict(
            Counter(
                str(row.get("loss_path_class"))
                for row in losses
            )
        ),
    }


def _group_codes(
    rows: list[dict[str, object]],
    field: str,
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        values = cast(list[str], row.get(field, []))
        if not values:
            grouped["NONE"].append(row)
            continue
        for value in values:
            grouped[value].append(row)
    return {
        key: _stats(items)
        for key, items in sorted(grouped.items())
    }


def _group_exact_signature(
    rows: list[dict[str, object]],
    field: str,
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        values = sorted(cast(list[str], row.get(field, [])))
        key = "NONE" if not values else " + ".join(values)
        grouped[key].append(row)
    return {
        key: _stats(items)
        for key, items in sorted(grouped.items())
    }


def _analyze_joined(rows: list[dict[str, object]]) -> dict[str, object]:
    by_action: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_reason: dict[str, list[dict[str, object]]] = defaultdict(list)
    override_rows: list[dict[str, object]] = []

    for row in rows:
        action = str(row.get("core_action"))
        reason = str(row.get("core_authorization_reason"))
        by_action[action].append(row)
        by_reason[reason].append(row)
        if action in {"ABSTAIN", "WAIT", "NON_EXECUTABLE"}:
            override_rows.append(row)

    return {
        "trade_count": len(rows),
        "by_core_action": {
            key: _stats(items)
            for key, items in sorted(by_action.items())
        },
        "by_authorization_reason": {
            key: _stats(items)
            for key, items in sorted(by_reason.items())
        },
        "override_conflict": {
            "sample": len(override_rows),
            "share_of_first_trades": format(
                Decimal(len(override_rows)) / Decimal(len(rows)),
                "f",
            )
            if rows
            else "0",
            **_stats(override_rows),
        },
        "contradiction_codes": _group_codes(
            rows,
            "core_reasoning_contradictions",
        ),
        "contradiction_signatures": _group_exact_signature(
            rows,
            "core_reasoning_contradictions",
        ),
        "uncertainty_codes": _group_codes(
            rows,
            "core_reasoning_uncertainty",
        ),
        "uncertainty_signatures": _group_exact_signature(
            rows,
            "core_reasoning_uncertainty",
        ),
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("reasoning conflict forensics requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    first_rows, first_diag = corrective._first_rows(
        by_day,
        context_by_day,
        evidence=evidence,
        alt_partial_r=None,
        secondary_route_policy="ORIGINAL",
    )
    rearm_rows, rearm_diag = corrective._rearm_rows(
        by_day,
        context_by_day,
        first_rows,
        evidence=evidence,
        rearm_partial_r=None,
    )
    nominal = sorted(
        [*first_rows, *rearm_rows],
        key=lambda row: cast(str, row["signal_at"]),
    )
    alloc_g = [
        lossfx._decorate(row)
        for row in allocation._apply_profile(
            nominal,
            profile=allocation.PROFILES[PROFILE_NAME],
        )
    ]
    marked, _ = lossfx._mark_streaks(alloc_g)
    marked_by_signal = {
        str(row["signal_at"]): row
        for row in marked
    }

    decisions = _core_decisions(
        by_day,
        context_by_day,
        evidence=evidence,
    )
    first_joined: list[dict[str, object]] = []
    for row in first_rows:
        signal = str(row["signal_at"])
        marked_row = marked_by_signal.get(signal)
        if marked_row is None:
            continue
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        decision = decisions.get(local_day, {})
        joined = dict(marked_row)
        joined["core_action"] = decision.get("core_action", "UNKNOWN")
        joined["core_authorization_reason"] = decision.get(
            "authorization_reason",
            row.get("authorization_reason"),
        )
        joined["core_reasoning_contradictions"] = decision.get(
            "reasoning_contradictions",
            [],
        )
        joined["core_reasoning_uncertainty"] = decision.get(
            "reasoning_uncertainty",
            [],
        )
        joined["core_reasoning_support"] = decision.get(
            "reasoning_support",
            [],
        )
        first_joined.append(joined)

    consumed_blocks: dict[str, object] = {}
    if partition == "consumed_holdout":
        for name, (start, end) in CONSUMED_BLOCKS.items():
            selected = [
                row
                for row in first_joined
                if start
                <= date.fromisoformat(cast(str, row["local_date"]))
                < end
            ]
            consumed_blocks[name] = {
                "start": start.isoformat(),
                "end_exclusive": end.isoformat(),
                **_analyze_joined(selected),
            }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "allocation_profile": PROFILE_NAME,
        "first_trade_analysis": _analyze_joined(first_joined),
        "consumed_blocks": consumed_blocks,
        "diagnostics": {
            "first": first_diag,
            "rearm": rearm_diag,
        },
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "diagnostic_only": True,
            "reasoning_state_captured_pre_fallback": True,
            "post_outcome_fields_diagnostic_only": True,
            "trade_authorization_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "allocation_profile_changed": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "uses_calendar_time_at_runtime": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "first_trade_analysis": payload["first_trade_analysis"],
                "consumed_blocks": payload["consumed_blocks"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
