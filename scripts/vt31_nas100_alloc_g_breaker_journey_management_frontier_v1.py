"""ALLOC_G family-specific journey management frontier for VT31_NAS100.

Consumed development evidence only.

This frontier preserves Silver Bullet, trade admission, entry, initial stop,
structural target, rearm, ALLOC_G capital routing, and SHIELD_060. It tests a
single missing capability identified by existing Core evidence: selective
post-fill protection for SECONDARY Breaker positions after a fully closed M1
has earned +1R. FVG and REARM positions are never modified here.

The decision uses only bars closed by the checkpoint. Protection becomes
active on the next M1. Future Journey labels and terminal PnL are research
labels only and are never consulted by the management decision.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_causal_hybrid_density_v2 as hybrid
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_ny_journey_bifurcation_forensics_v1 as journey
import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as shield
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.alloc_g_breaker_journey_management_frontier.v1"
MARKET = "NAS100"
BASE_PROFILE = "ALLOC_G_CORE_FAMILY_050"
CHECKPOINT_R = Decimal("1.00")
SHIELD_MULTIPLIER = Decimal("0.60")

VARIANTS: dict[str, tuple[str, Decimal] | None] = {
    "BASELINE_SHIELD060": None,
    "BREAKER_ALL_BE100": ("ALL", Decimal("0.00")),
    "BREAKER_ALL_LOCK025_100": ("ALL", Decimal("0.25")),
    "BREAKER_OVERLAP_LT025_BE100": ("OVERLAP_LT025", Decimal("0.00")),
    "BREAKER_OVERLAP_LT025_LOCK025_100": (
        "OVERLAP_LT025",
        Decimal("0.25"),
    ),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _touches_stop(bar: object, side: str, level: Decimal) -> bool:
    low = _d(getattr(bar, "low"))
    high = _d(getattr(bar, "high"))
    return low <= level if side == "long" else high >= level


def _touches_target(bar: object, side: str, level: Decimal) -> bool:
    low = _d(getattr(bar, "low"))
    high = _d(getattr(bar, "high"))
    return high >= level if side == "long" else low <= level


def _protective_fill_r(
    bar: object,
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
    protective_level: Decimal,
    lock_r: Decimal,
) -> Decimal:
    """Model a next-M1 protective stop without granting a better gap fill."""
    opened = _d(getattr(bar, "open"))
    if side == "long" and opened < protective_level:
        return (opened - entry) / risk
    if side == "short" and opened > protective_level:
        return (entry - opened) / risk
    return lock_r


def _checkpoint(
    bars: tuple[object, ...],
    row: dict[str, object],
) -> tuple[int, dict[str, Decimal | str]] | None:
    side = str(row["side"])
    entry = _d(row["entry"])
    stop = _d(row["initial_stop"])
    target = _d(row["structural_target"])
    risk = abs(entry - stop)
    if risk <= 0:
        return None

    filled_at = datetime.fromisoformat(cast(str, row["filled_at"]))
    original_exit_at = datetime.fromisoformat(cast(str, row["exit_at"]))
    observed: list[object] = []

    for index, bar in enumerate(bars):
        opened_at = cast(datetime, getattr(bar, "opened_at"))
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        if opened_at < filled_at:
            continue
        if closed_at >= original_exit_at:
            break
        if _touches_stop(bar, side, stop):
            return None

        observed.append(bar)
        close_r = journey._favorable_close_r(
            bar,
            side=side,
            entry=entry,
            risk=risk,
        )
        if close_r < CHECKPOINT_R:
            continue

        overlap = journey._overlap_rate(tuple(observed))
        efficiency = journey._path_efficiency(
            tuple(observed),
            side=side,
            entry=entry,
        )
        body_ratio = journey._directional_body_ratio(
            tuple(observed),
            side=side,
        )
        checkpoint_close = _d(getattr(bar, "close"))
        remaining_r = (
            max(Decimal(0), target - checkpoint_close) / risk
            if side == "long"
            else max(Decimal(0), checkpoint_close - target) / risk
        )
        return index, {
            "overlap_rate": overlap,
            "path_efficiency": efficiency,
            "directional_body_ratio": body_ratio,
            "remaining_to_target_r": remaining_r,
            "checkpoint_at": closed_at.isoformat(),
        }
    return None


def _eligible(scope: str, features: dict[str, Decimal | str]) -> bool:
    if scope == "ALL":
        return True
    if scope == "OVERLAP_LT025":
        return cast(Decimal, features["overlap_rate"]) < Decimal("0.25")
    raise ValueError(f"unsupported journey management scope={scope}")


def _apply_management(
    rows: list[dict[str, object]],
    by_day: dict[date, tuple[object, ...]],
    *,
    scope: str,
    lock_r: Decimal,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    counts: Counter[str] = Counter()

    for row in rows:
        updated = dict(row)
        updated["journey_management_scope"] = scope
        updated["journey_management_checkpoint_r"] = format(
            CHECKPOINT_R, "f"
        )
        updated["journey_management_lock_r"] = format(lock_r, "f")
        updated["journey_management_eligible"] = False
        updated["journey_management_applied"] = False
        updated["journey_management_ambiguous"] = False

        if not (
            str(row.get("tier")) == "SECONDARY"
            and str(row.get("entry_family")) == "breaker"
        ):
            counts["unchanged-non-secondary-breaker"] += 1
            adjusted.append(updated)
            continue

        local_day = date.fromisoformat(cast(str, row["local_date"]))
        bars = by_day.get(local_day)
        if not bars:
            counts["missing-day-bars"] += 1
            adjusted.append(updated)
            continue

        checkpoint = _checkpoint(bars, row)
        if checkpoint is None:
            counts["checkpoint-not-earned-before-baseline-exit"] += 1
            adjusted.append(updated)
            continue

        checkpoint_index, features = checkpoint
        for key, value in features.items():
            updated[f"journey_{key}"] = (
                format(value, "f") if isinstance(value, Decimal) else value
            )

        if not _eligible(scope, features):
            counts["checkpoint-earned-scope-not-eligible"] += 1
            adjusted.append(updated)
            continue

        counts["management-eligible"] += 1
        updated["journey_management_eligible"] = True

        side = str(row["side"])
        entry = _d(row["entry"])
        initial_stop = _d(row["initial_stop"])
        structural_target = _d(row["structural_target"])
        risk = abs(entry - initial_stop)
        original_exit_at = datetime.fromisoformat(cast(str, row["exit_at"]))
        protective_level = (
            entry + risk * lock_r
            if side == "long"
            else entry - risk * lock_r
        )
        checkpoint_at = datetime.fromisoformat(
            cast(str, features["checkpoint_at"])
        )

        applied = False
        for bar in bars[checkpoint_index + 1 :]:
            opened_at = cast(datetime, getattr(bar, "opened_at"))
            closed_at = cast(datetime, getattr(bar, "closed_at"))
            if opened_at < checkpoint_at:
                continue
            if closed_at > original_exit_at:
                break

            protect_hit = _touches_stop(bar, side, protective_level)
            if not protect_hit:
                continue

            if _touches_target(bar, side, structural_target):
                counts["ambiguous-protect-vs-target-same-m1"] += 1
                updated["journey_management_ambiguous"] = True
                break

            managed_r = _protective_fill_r(
                bar,
                side=side,
                entry=entry,
                risk=risk,
                protective_level=protective_level,
                lock_r=lock_r,
            )
            requested_risk = _d(row["requested_risk_r"])
            updated["r_multiple"] = format(managed_r, "f")
            updated["capital_weighted_net_r"] = format(
                requested_risk * (managed_r - hybrid.FRICTION),
                "f",
            )
            updated["exit_at"] = closed_at.isoformat()
            updated["exit_reason"] = (
                "secondary-breaker-journey-breakeven"
                if lock_r == 0
                else "secondary-breaker-journey-lock"
            )
            updated["journey_management_applied"] = True
            updated["journey_protective_level"] = format(
                protective_level, "f"
            )
            counts["management-protective-exit"] += 1
            applied = True
            break

        if not applied and not updated["journey_management_ambiguous"]:
            counts["management-eligible-baseline-exit-preserved"] += 1
        adjusted.append(updated)

    adjusted.sort(key=lambda row: cast(str, row["signal_at"]))
    return adjusted, {"status_counts": dict(sorted(counts.items()))}


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("breaker journey management frontier requires NAS100")

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

    variants: dict[str, object] = {}
    for name, spec in VARIANTS.items():
        if spec is None:
            managed = [dict(row) for row in nominal]
            management_diag = {"status_counts": {"baseline": len(managed)}}
        else:
            scope, lock_r = spec
            managed, management_diag = _apply_management(
                nominal,
                by_day,
                scope=scope,
                lock_r=lock_r,
            )

        alloc_g = allocation._apply_profile(
            managed,
            profile=allocation.PROFILES[BASE_PROFILE],
        )
        rows = shield._apply_shield(
            alloc_g,
            multiplier=SHIELD_MULTIPLIER,
        )
        metrics = shield._metrics(rows)
        mc = engine._monte_carlo(
            rows,
            variant=f"BREAKER_JOURNEY:{name}:{partition}",
        )
        annual = (
            shield._annual_blocks(
                rows, start=date(2022, 7, 18), years=2
            )
            if partition == "consumed_holdout"
            else []
        )
        status_counts = cast(
            dict[str, int], management_diag["status_counts"]
        )
        ambiguity_count = status_counts.get(
            "ambiguous-protect-vs-target-same-m1", 0
        )
        applied_count = status_counts.get("management-protective-exit", 0)
        eligible_count = status_counts.get("management-eligible", 0)

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
            "management_eligible_count": eligible_count,
            "management_applied_count": applied_count,
            "management_ambiguity_count": ambiguity_count,
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "management_diagnostics": management_diag,
            "objectives": objectives,
            "passes_economic_objectives": all(objectives.values()),
            "tick_resolution_required": ambiguity_count > 0,
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "base_profile": BASE_PROFILE,
        "shield": "SHIELD_060",
        "checkpoint_r": format(CHECKPOINT_R, "f"),
        "variants": variants,
        "diagnostics": {"first": first_diag, "rearm": rearm_diag},
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "silver_bullet_changed": False,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_stop_changed_at_entry": False,
            "structural_target_changed": False,
            "rearm_changed": False,
            "fvg_management_changed": False,
            "core_management_changed": False,
            "journey_decision_uses_closed_m1_only": True,
            "protection_activates_next_m1": True,
            "uses_future_journey_label_at_runtime": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "uses_calendar_date_at_runtime": False,
            "same_m1_protect_target_is_ambiguity": True,
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
                "base_profile": payload["base_profile"],
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
