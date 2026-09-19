"""Early no-progress scratch frontier for VT31_NAS100.

Consumed development evidence only.

Base identity:
- ALLOC_G_CORE_FAMILY_050
- SHIELD_060
- stable loss-cluster shield 0.60
- SECONDARY Breaker closed +1R checkpoint with +0.25R lock

Missing capability under test:
A trade that has made no meaningful favorable progress after a fixed number of
fully closed post-fill M1 bars, while closing materially adverse, may be
scratched at the next M1 open. This targets DEAD_ON_ARRIVAL without changing
trade admission.

Decision inputs are only closed M1 bars available by the checkpoint. Terminal
PnL and future path labels are never used. If the next M1 opens through the
original stop/target, the baseline outcome is retained rather than inventing
order precedence.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_alloc_g_breaker_journey_management_frontier_v1 as breaker
import vt31_nas100_causal_hybrid_density_v2 as hybrid
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_loss_cluster_risk_shield_frontier_v1 as loss_shield
import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as shield
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.early_no_progress_scratch_frontier.v1"
MARKET = "NAS100"
BASE_PROFILE = "ALLOC_G_CORE_FAMILY_050"
BASE_SHIELD = Decimal("0.60")
LOSS_CLUSTER_SHIELD = Decimal("0.60")
BREAKER_LOCK_R = Decimal("0.25")
MFE_LIMIT_R = Decimal("0.25")
ADVERSE_CLOSE_R = Decimal("-0.25")

VARIANTS: dict[str, int | None] = {
    "BASE": None,
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


def _scratch_row(
    row: dict[str, object],
    bars: tuple[object, ...],
    *,
    checkpoint_bars: int,
) -> tuple[dict[str, object], str]:
    updated = dict(row)
    updated["scratch_checkpoint_bars"] = checkpoint_bars
    updated["scratch_mfe_limit_r"] = format(MFE_LIMIT_R, "f")
    updated["scratch_adverse_close_r"] = format(ADVERSE_CLOSE_R, "f")
    updated["scratch_applied"] = False

    side = str(row["side"])
    entry = _d(row["entry"])
    stop = _d(row["initial_stop"])
    target = _d(row["structural_target"])
    risk = abs(entry - stop)
    if risk <= 0:
        return updated, "invalid-risk"

    filled_at = datetime.fromisoformat(cast(str, row["filled_at"]))
    original_exit_at = datetime.fromisoformat(cast(str, row["exit_at"]))

    observed: list[object] = []
    checkpoint_bar: object | None = None
    for bar in bars:
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
        return updated, "checkpoint-not-reached-before-baseline-exit"

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
    updated["scratch_checkpoint_at"] = cast(
        datetime, getattr(checkpoint_bar, "closed_at")
    ).isoformat()

    if not (
        max_favorable < MFE_LIMIT_R
        and close_r <= ADVERSE_CLOSE_R
    ):
        return updated, "checkpoint-condition-not-met"

    checkpoint_at = cast(datetime, getattr(checkpoint_bar, "closed_at"))
    next_bar: object | None = None
    for bar in bars:
        opened_at = cast(datetime, getattr(bar, "opened_at"))
        if opened_at == checkpoint_at:
            next_bar = bar
            break
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
        updated["scratch_open_level_ambiguity"] = True
        return updated, "next-open-through-stop-or-target"

    exit_r = (
        (opened - entry) / risk
        if side == "long"
        else (entry - opened) / risk
    )
    requested_risk = _d(row["requested_risk_r"])
    updated["r_multiple"] = format(exit_r, "f")
    updated["capital_weighted_net_r"] = format(
        requested_risk * (exit_r - hybrid.FRICTION),
        "f",
    )
    updated["exit_at"] = next_opened_at.isoformat()
    updated["exit_reason"] = "early-no-progress-scratch-next-m1-open"
    updated["scratch_applied"] = True
    updated["scratch_exit_r"] = format(exit_r, "f")
    return updated, "scratch-applied"


def _apply_scratch(
    rows: list[dict[str, object]],
    by_day: dict[date, tuple[object, ...]],
    *,
    checkpoint_bars: int,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    adjusted: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    for row in rows:
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        bars = by_day.get(local_day)
        if not bars:
            counts["missing-day-bars"] += 1
            adjusted.append(dict(row))
            continue
        updated, status = _scratch_row(
            row,
            bars,
            checkpoint_bars=checkpoint_bars,
        )
        counts[status] += 1
        adjusted.append(updated)
    adjusted.sort(key=lambda row: cast(str, row["signal_at"]))
    return adjusted, dict(sorted(counts.items()))


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("early no-progress scratch requires NAS100")

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

    managed, breaker_diag = breaker._apply_management(
        nominal,
        by_day,
        scope="ALL",
        lock_r=BREAKER_LOCK_R,
    )
    alloc_g = allocation._apply_profile(
        managed,
        profile=allocation.PROFILES[BASE_PROFILE],
    )
    state_shielded = shield._apply_shield(
        alloc_g,
        multiplier=BASE_SHIELD,
    )
    base_rows = loss_shield._apply_loss_cluster_shield(
        state_shielded,
        multiplier=LOSS_CLUSTER_SHIELD,
    )

    variants: dict[str, object] = {}
    for name, checkpoint in VARIANTS.items():
        if checkpoint is None:
            rows = [dict(row) for row in base_rows]
            scratch_counts = {"baseline": len(rows)}
        else:
            rows, scratch_counts = _apply_scratch(
                base_rows,
                by_day,
                checkpoint_bars=checkpoint,
            )

        metrics = shield._metrics(rows)
        mc = engine._monte_carlo(
            rows,
            variant=f"EARLY_SCRATCH:{name}:{partition}",
        )
        annual = (
            shield._annual_blocks(
                rows,
                start=date(2022, 7, 18),
                years=2,
            )
            if partition == "consumed_holdout"
            else []
        )
        scratch_applied_count = sum(
            bool(row.get("scratch_applied")) for row in rows
        )

        objectives = {
            "density_300_350": 300 <= len(rows) <= 350,
            "pf_ge_1_50": (
                metrics["profit_factor"] is not None
                and _d(metrics["profit_factor"]) >= Decimal("1.50")
            ),
            "dd_le_6": _d(metrics["max_drawdown_r"]) <= Decimal("6"),
            "mc_positive_ge_0_90": (
                _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
            ),
            "mc_p95_dd_le_15": (
                _d(mc["p95_max_drawdown_r"]) <= Decimal("15")
            ),
        }
        if annual:
            objectives["both_consumed_years_positive"] = all(
                bool(block["positive"]) for block in annual
            )

        variants[name] = {
            "trade_count": len(rows),
            "checkpoint_bars": checkpoint,
            "scratch_applied_count": scratch_applied_count,
            "scratch_status_counts": scratch_counts,
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "objectives": objectives,
            "passes_economic_objectives": all(objectives.values()),
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "base_profile": BASE_PROFILE,
        "base_state_shield": "SHIELD_060",
        "base_loss_cluster_shield": "LOSS_CLUSTER_SHIELD_060",
        "breaker_management": "LOCK025_AFTER_CLOSED_1R",
        "scratch_contract": {
            "mfe_limit_r": format(MFE_LIMIT_R, "f"),
            "adverse_close_r": format(ADVERSE_CLOSE_R, "f"),
            "exit_timing": "next-m1-open",
        },
        "variants": variants,
        "diagnostics": {
            "first": first_diag,
            "rearm": rearm_diag,
            "breaker": breaker_diag,
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
            "new_capability_was_missing_from_core": True,
            "trade_count_changed": False,
            "trade_admission_changed": False,
            "silver_bullet_changed": False,
            "entry_changed": False,
            "initial_stop_changed_at_entry": False,
            "structural_target_changed": False,
            "rearm_changed": False,
            "checkpoint_uses_closed_post_fill_m1_only": True,
            "exit_occurs_next_m1_open": True,
            "future_outcome_used_by_scratch_decision": False,
            "future_journey_label_used_by_scratch_decision": False,
            "uses_fold_identity_at_runtime": False,
            "uses_calendar_date_at_runtime": False,
            "next_open_stop_target_ambiguity_preserves_baseline": True,
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
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
