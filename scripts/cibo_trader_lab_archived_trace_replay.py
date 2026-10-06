#!/usr/bin/env python3
"""Archived decision-trace replay for CIBO Maximum Capability Trader Lab.

Replays only causal decision-time surfaces retained in an archived trace.
It does not regenerate trader methodology, does not use realized outcomes for
decision logic, and does not claim certification/fresh OOS.

Primary uses:
- measure RECOVERY/MPC opportunity-capture improvement;
- measure real open-position portfolio competition;
- estimate causal continuation value from frozen entry expectation + remaining
  capital horizon;
- identify shadow RELEASE proposals that remain blocked until executable causal
  mark-to-market evidence exists.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any


ZERO = Decimal(0)
ONE = Decimal(1)


def dec(value: object, default: Decimal = ZERO) -> Decimal:
    if value is None:
        return default
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("archived trace numeric value must be finite")
    return result


def dt(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError("archived trace timestamp must be string")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("archived trace timestamp must be timezone-aware")
    return result


def ratio(num: int | Decimal, den: int | Decimal) -> Decimal:
    den_d = Decimal(den)
    num_d = Decimal(num)
    if den_d <= 0:
        return ONE if num_d == 0 else ZERO
    return max(ZERO, min(ONE, num_d / den_d))


def continuation_value(position: dict[str, Any], observed_at: datetime) -> tuple[Decimal, Decimal]:
    entry_at = dt(position.get("capital_deployed_at") or position.get("entry_at"))
    exit_at = dt(position.get("capital_released_at") or position.get("exit_at"))
    if entry_at is None or exit_at is None or observed_at >= exit_at:
        return ZERO, ZERO
    entry_ev = dec(position.get("expected_net_value_usd"))
    entry_minutes = dec(position.get("expected_capital_minutes"))
    if entry_minutes <= 0:
        return ZERO, ZERO
    remaining = Decimal(str((exit_at - observed_at).total_seconds())) / Decimal(60)
    fraction = min(ONE, max(ZERO, remaining / entry_minutes))
    value = entry_ev * fraction
    utility_per_minute = ZERO if remaining <= 0 else value / remaining
    return value, utility_per_minute


def active_positions(rows: list[dict[str, Any]], observed_at: datetime, exclude: str) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        if not row.get("selected"):
            continue
        if row.get("signal_fingerprint") == exclude:
            continue
        start = dt(row.get("capital_deployed_at") or row.get("entry_at"))
        end = dt(row.get("capital_released_at") or row.get("exit_at"))
        if start is None or end is None:
            continue
        if start < observed_at < end:
            out.append(row)
    return out


def _compact_raw_trace(payload: dict[str, Any], *, group: str) -> dict[str, Any]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        raise ValueError("raw decision trace requires opportunities")
    rows = []
    for row in opportunities:
        ce2i = row.get("ce2i") or {}
        receipts = ce2i.get("runtime_receipts") or []
        posture = None
        t14 = []
        for receipt in receipts:
            if not isinstance(receipt, dict):
                continue
            if receipt.get("engine_name") == "select_ce2i_tools_for_regime":
                output = receipt.get("output_payload") or {}
                posture = output.get("posture") or posture
            if (
                receipt.get("tool_code") == "T14"
                or receipt.get("engine_name") == "dynamic_derisk"
            ):
                t14.append(
                    {
                        "tool_code": receipt.get("tool_code"),
                        "engine_name": receipt.get("engine_name"),
                        "decision_changed": receipt.get("decision_changed"),
                        "economic_effect_observable": receipt.get(
                            "economic_effect_observable"
                        ),
                        "output_payload": receipt.get("output_payload"),
                    }
                )
        allocation = row.get("allocation") or {}
        qore_risk = row.get("qore_risk") or {}
        settlement = row.get("settlement") or {}
        expectation = row.get("expectation") or {}
        context = row.get("context_quality") or {}
        market_state = row.get("market_predecision_state") or {}
        trader = row.get("trader_opportunity") or {}
        cma = row.get("cma") or {}
        rows.append(
            {
                "signal_fingerprint": row.get("signal_fingerprint"),
                "trader_id": row.get("trader_id"),
                "qore_symbol": row.get("qore_symbol"),
                "decision_epoch_id": row.get("decision_epoch_id"),
                "market_decision_at": row.get("market_decision_at"),
                "expected_net_value_usd": expectation.get(
                    "expected_net_value_usd"
                ),
                "expected_capital_minutes": expectation.get(
                    "expected_capital_minutes"
                ),
                "context_disposition": context.get("disposition"),
                "context_rules": context.get("matched_rule_ids") or [],
                "allocator_disposition": allocation.get(
                    "allocator_disposition"
                ),
                "selected": bool(
                    allocation.get("selected_by_cibo_policy")
                ),
                "regime_posture": posture
                or (market_state.get("regime") or {}).get("posture"),
                "hard_risk_headroom_usd": market_state.get(
                    "hard_risk_headroom_usd"
                ),
                "margin_headroom_usd": market_state.get(
                    "margin_headroom_usd"
                ),
                "requested_stop_risk_usd": cma.get(
                    "requested_stop_risk_usd"
                ),
                "candidate_stop_risk_usd": cma.get(
                    "candidate_stop_risk_usd"
                ),
                "candidate_margin_usd": cma.get("candidate_margin_usd"),
                "qore_risk_status": qore_risk.get("status"),
                "authorized_stop_risk_usd": qore_risk.get(
                    "authorized_stop_risk_usd"
                ),
                "authorized_margin_usd": qore_risk.get(
                    "authorized_margin_usd"
                ),
                "capital_deployed_at": settlement.get(
                    "capital_deployed_at"
                ),
                "capital_released_at": settlement.get(
                    "capital_released_at"
                ),
                "entry_at": (row.get("evaluation_outcome") or {}).get(
                    "entry_at"
                ),
                "exit_at": (row.get("evaluation_outcome") or {}).get(
                    "exit_at"
                ),
                "intended_entry": trader.get("intended_entry"),
                "stop_loss": trader.get("stop_loss"),
                "take_profit": trader.get("take_profit"),
                "provider_cost_proxy_usd": (
                    row.get("provider_economics_and_execution") or {}
                ).get("decision_provider_cost_proxy_usd"),
                "t14_receipts": t14,
            }
        )
    return {
        "schema": "qore.cibo.archived-trace-compact.v1",
        "source_trace_sha256": payload.get("trace_sha256"),
        "group": group,
        "rows": rows,
    }


def group_replay(payload: dict[str, Any], *, group: str) -> dict[str, Any]:
    if "rows" not in payload and "opportunities" in payload:
        payload = _compact_raw_trace(payload, group=group)
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("archived trace payload requires rows")

    positive_allowed = []
    selected_positive = []
    recovery_misses = []
    portfolio_competitions = 0
    portfolio_fit_without_release = 0
    portfolio_capacity_constrained = 0
    portfolio_release_capacity_sufficient = 0
    portfolio_nonpositive_replacement = 0
    portfolio_release_proposals = 0
    portfolio_positive_replacements = 0
    portfolio_shadow_incremental_utility = ZERO
    proposed_release_risk = ZERO
    proposed_release_margin = ZERO
    mark_blocked_release_proposals = 0
    continuation_positions_seen = 0
    continuation_positions_identified = 0

    by_epoch: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_epoch[str(row.get("decision_epoch_id", ""))].append(row)

    for row in rows:
        ev = dec(row.get("expected_net_value_usd"))
        if ev <= 0 or row.get("context_disposition") != "ALLOW":
            continue
        positive_allowed.append(row)
        if row.get("selected"):
            selected_positive.append(row)

        if (
            not row.get("selected")
            and row.get("allocator_disposition") == "PRESERVE_CAPACITY"
            and row.get("regime_posture") == "RECOVERY"
        ):
            recovery_misses.append(row)

        observed_at = dt(row.get("market_decision_at"))
        if observed_at is None:
            continue
        active = active_positions(rows, observed_at, str(row.get("signal_fingerprint", "")))
        if not active:
            continue
        portfolio_competitions += 1
        continuation_positions_seen += len(active)
        continuation_positions_identified += sum(
            dt(
                position.get("capital_released_at")
                or position.get("exit_at")
            )
            is not None
            and dec(position.get("expected_capital_minutes")) > 0
            for position in active
        )

        candidate_risk = dec(
            row.get("candidate_stop_risk_usd"),
            dec(row.get("requested_stop_risk_usd")),
        )
        candidate_margin = dec(row.get("candidate_margin_usd"))
        headroom_risk = dec(row.get("hard_risk_headroom_usd"))
        headroom_margin = dec(row.get("margin_headroom_usd"))
        need_risk = max(ZERO, candidate_risk - headroom_risk)
        need_margin = max(ZERO, candidate_margin - headroom_margin)

        if need_risk <= 0 and need_margin <= 0:
            portfolio_fit_without_release += 1
            continue

        portfolio_capacity_constrained += 1
        release_candidates = []
        for position in active:
            continuation, utility_per_minute = continuation_value(position, observed_at)
            risk = dec(position.get("authorized_stop_risk_usd"))
            margin = dec(position.get("authorized_margin_usd"))
            release_candidates.append(
                (
                    utility_per_minute,
                    continuation,
                    str(position.get("signal_fingerprint", "")),
                    risk,
                    margin,
                )
            )
        release_candidates.sort(key=lambda item: (item[0], item[1], item[2]))

        released_risk = ZERO
        released_margin = ZERO
        displaced = ZERO
        for _, continuation, _, risk, margin in release_candidates:
            if released_risk >= need_risk and released_margin >= need_margin:
                break
            released_risk += risk
            released_margin += margin
            displaced += max(ZERO, continuation)

        enough = released_risk >= need_risk and released_margin >= need_margin
        if enough:
            portfolio_release_capacity_sufficient += 1
        incremental = ev - displaced
        if enough and incremental > 0:
            portfolio_positive_replacements += 1
            portfolio_release_proposals += 1
            portfolio_shadow_incremental_utility += incremental
            proposed_release_risk += released_risk
            proposed_release_margin += released_margin
            # Archived #107 trace has no causal current mark per open position.
            mark_blocked_release_proposals += 1
        elif enough:
            portfolio_nonpositive_replacement += 1

    allowed_count = len(positive_allowed)
    selected_count = len(selected_positive)
    recovery_count = len(recovery_misses)
    allowed_ev = sum((dec(x.get("expected_net_value_usd")) for x in positive_allowed), ZERO)
    selected_ev = sum((dec(x.get("expected_net_value_usd")) for x in selected_positive), ZERO)
    recovery_ev = sum((dec(x.get("expected_net_value_usd")) for x in recovery_misses), ZERO)

    baseline_count_eff = ratio(selected_count, allowed_count)
    baseline_value_eff = ratio(selected_ev, allowed_ev)
    recovery_count_ceiling = ratio(selected_count + recovery_count, allowed_count)
    recovery_value_ceiling = ratio(selected_ev + recovery_ev, allowed_ev)

    t14_changed = 0
    t14_effective = 0
    for row in rows:
        for receipt in row.get("t14_receipts") or []:
            if receipt.get("decision_changed"):
                t14_changed += 1
            if receipt.get("economic_effect_observable"):
                t14_effective += 1

    return {
        "group": payload.get("group"),
        "source_trace_sha256": payload.get("source_trace_sha256"),
        "opportunity_count": len(rows),
        "positive_context_allowed_count": allowed_count,
        "baseline_selected_positive_count": selected_count,
        "baseline_count_efficiency": format(baseline_count_eff, "f"),
        "baseline_value_efficiency": format(baseline_value_eff, "f"),
        "recovery_preserve_miss_count": recovery_count,
        "recovery_preserve_miss_expected_value_usd": format(recovery_ev, "f"),
        "recovery_probe_count_ceiling": format(recovery_count_ceiling, "f"),
        "recovery_probe_value_ceiling": format(recovery_value_ceiling, "f"),
        "recovery_count_efficiency_delta": format(
            recovery_count_ceiling - baseline_count_eff, "f"
        ),
        "recovery_value_efficiency_delta": format(
            recovery_value_ceiling - baseline_value_eff, "f"
        ),
        "portfolio_open_position_competition_count": portfolio_competitions,
        "portfolio_fit_without_release_count": portfolio_fit_without_release,
        "portfolio_capacity_constrained_count": portfolio_capacity_constrained,
        "portfolio_release_capacity_sufficient_count": (
            portfolio_release_capacity_sufficient
        ),
        "portfolio_nonpositive_replacement_count": (
            portfolio_nonpositive_replacement
        ),
        "portfolio_positive_replacement_count": portfolio_positive_replacements,
        "portfolio_shadow_release_proposal_count": portfolio_release_proposals,
        "portfolio_shadow_incremental_utility_usd": format(
            portfolio_shadow_incremental_utility, "f"
        ),
        "portfolio_proposed_release_stop_risk_usd": format(
            proposed_release_risk, "f"
        ),
        "portfolio_proposed_release_margin_usd": format(
            proposed_release_margin, "f"
        ),
        "portfolio_mark_blocked_release_proposals": mark_blocked_release_proposals,
        "continuation_positions_seen": continuation_positions_seen,
        "continuation_positions_identified": continuation_positions_identified,
        "continuation_coverage": format(
            ratio(continuation_positions_identified, continuation_positions_seen), "f"
        ),
        "t14_decision_changed_receipts": t14_changed,
        "t14_economic_effect_receipts": t14_effective,
        "outcome_used_for_decision": False,
        "certification_claimed": False,
        "fresh_oos_claimed": False,
        "productive_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    groups = [
        group_replay(
            json.loads(path.read_text(encoding="utf-8")),
            group=f"GROUP_{index}",
        )
        for index, path in enumerate(args.input, start=1)
    ]
    aggregate = {
        "schema": "qore.cibo.trader-lab.archived-trace-replay.v1",
        "validation_mode": "NON_CERTIFYING_ARCHIVED_CAUSAL_TRACE_REPLAY",
        "group_count": len(groups),
        "groups": groups,
        "aggregate": {
            "opportunity_count": sum(x["opportunity_count"] for x in groups),
            "recovery_preserve_miss_count": sum(
                x["recovery_preserve_miss_count"] for x in groups
            ),
            "recovery_preserve_miss_expected_value_usd": format(
                sum(
                    (
                        dec(x["recovery_preserve_miss_expected_value_usd"])
                        for x in groups
                    ),
                    ZERO,
                ),
                "f",
            ),
            "portfolio_open_position_competition_count": sum(
                x["portfolio_open_position_competition_count"] for x in groups
            ),
            "portfolio_fit_without_release_count": sum(
                x["portfolio_fit_without_release_count"] for x in groups
            ),
            "portfolio_capacity_constrained_count": sum(
                x["portfolio_capacity_constrained_count"] for x in groups
            ),
            "portfolio_release_capacity_sufficient_count": sum(
                x["portfolio_release_capacity_sufficient_count"] for x in groups
            ),
            "portfolio_nonpositive_replacement_count": sum(
                x["portfolio_nonpositive_replacement_count"] for x in groups
            ),
            "portfolio_positive_replacement_count": sum(
                x["portfolio_positive_replacement_count"] for x in groups
            ),
            "portfolio_shadow_incremental_utility_usd": format(
                sum(
                    (
                        dec(x["portfolio_shadow_incremental_utility_usd"])
                        for x in groups
                    ),
                    ZERO,
                ),
                "f",
            ),
            "portfolio_mark_blocked_release_proposals": sum(
                x["portfolio_mark_blocked_release_proposals"] for x in groups
            ),
        },
        "outcome_used_for_decision": False,
        "certification_claimed": False,
        "fresh_oos_claimed": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(aggregate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(aggregate, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
