"""ALLOC_G adapter for the existing VT31 CAUTIOUS Drag risk profiles.

Consumed development evidence only.

Base identity:
- ALLOC_G_CORE_FAMILY_050
- SHIELD_060
- SECONDARY Breaker +1R closed-M1 checkpoint with +0.25R lock

This adapter reuses the existing CAUTIOUS Drag context classifier, drag flags,
risk classes and predeclared profiles. It does not reuse that lab's old OCO
opportunity universe. The current ALLOC_G admission, entry, stop, target,
rearm and lifecycle remain unchanged; only capital is multiplied after the
trade has already been causally authorized.
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
from zoneinfo import ZoneInfo

import vt31_nas100_alloc_g_breaker_journey_management_frontier_v1 as breaker
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_cautious_drag_risk_protection_v1 as drag
import vt31_nas100_high_density_management_intelligence_v1 as management
import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as shield
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.alloc_g_cautious_drag_adapter_frontier.v1"
MARKET = "NAS100"
BASE_PROFILE = "ALLOC_G_CORE_FAMILY_050"
BASE_SHIELD = Decimal("0.60")
BREAKER_LOCK_R = Decimal("0.25")
NY = ZoneInfo("America/New_York")

VARIANTS = {
    "BASE_BREAKER_LOCK025": None,
    "DRAG_CONSERVATIVE": "CONSERVATIVE",
    "DRAG_BALANCED": "BALANCED",
    "DRAG_DENSITY_CAPITAL": "DENSITY_CAPITAL",
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _decision_minute_ny(row: dict[str, object]) -> int:
    value = datetime.fromisoformat(cast(str, row["signal_at"]))
    local = value.astimezone(NY)
    return local.hour * 60 + local.minute


def _classify(row: dict[str, object]) -> tuple[str, str, tuple[str, ...]]:
    state = {
        "reference_volatility_state": row.get("reference_volatility_state"),
        "current_path_vs_previous": row.get("current_path_vs_previous"),
        "last_structure_event_family": row.get("last_structure_event_family"),
        "reference_reclaim_age_minutes": row.get(
            "reference_reclaim_age_minutes"
        ),
        "decision_minute_ny": _decision_minute_ny(row),
    }
    context = management._context_state(state)
    flags = drag._drag_flags(
        state,
        context=context,
        side=str(row.get("side")),
        family=str(row.get("entry_family")),
    )
    risk_class = drag._risk_class(context, len(flags))
    return context, risk_class, flags


def _apply_drag_profile(
    rows: list[dict[str, object]],
    *,
    profile_name: str | None,
) -> list[dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    for row in rows:
        updated = dict(row)
        context, risk_class, flags = _classify(updated)
        multiplier = (
            Decimal("1.00")
            if profile_name is None
            else drag.PROFILES[profile_name][risk_class]
        )
        updated["drag_profile"] = profile_name or "BASE"
        updated["drag_context"] = context
        updated["drag_risk_class"] = risk_class
        updated["drag_flags"] = list(flags)
        updated["drag_multiplier"] = format(multiplier, "f")
        updated["requested_risk_r"] = format(
            _d(updated["requested_risk_r"]) * multiplier,
            "f",
        )
        updated["capital_weighted_net_r"] = format(
            _d(updated["capital_weighted_net_r"]) * multiplier,
            "f",
        )
        adjusted.append(updated)
    return adjusted


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("ALLOC_G CAUTIOUS Drag adapter requires NAS100")

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

    managed, management_diag = breaker._apply_management(
        nominal,
        by_day,
        scope="ALL",
        lock_r=BREAKER_LOCK_R,
    )
    alloc_g = allocation._apply_profile(
        managed,
        profile=allocation.PROFILES[BASE_PROFILE],
    )
    base_rows = shield._apply_shield(
        alloc_g,
        multiplier=BASE_SHIELD,
    )

    variants: dict[str, object] = {}
    for name, profile_name in VARIANTS.items():
        rows = _apply_drag_profile(
            base_rows,
            profile_name=profile_name,
        )
        metrics = shield._metrics(rows)
        mc = engine._monte_carlo(
            rows,
            variant=f"ALLOC_G_DRAG:{name}:{partition}",
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

        contexts = Counter(str(row["drag_context"]) for row in rows)
        classes = Counter(str(row["drag_risk_class"]) for row in rows)
        flags = Counter(
            flag
            for row in rows
            for flag in cast(list[str], row["drag_flags"])
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
            "profile_name": profile_name,
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "drag_context_counts": dict(sorted(contexts.items())),
            "drag_risk_class_counts": dict(sorted(classes.items())),
            "drag_flag_counts": dict(sorted(flags.items())),
            "objectives": objectives,
            "passes_economic_objectives": all(objectives.values()),
        }

    status_counts = cast(
        dict[str, int],
        management_diag["status_counts"],
    )
    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "base_profile": BASE_PROFILE,
        "base_state_shield": "SHIELD_060",
        "breaker_management": {
            "checkpoint_r": "1.00",
            "lock_r": format(BREAKER_LOCK_R, "f"),
            "eligible_count": status_counts.get("management-eligible", 0),
            "applied_count": status_counts.get(
                "management-protective-exit", 0
            ),
        },
        "reused_drag_profiles": {
            name: {
                key: format(value, "f")
                for key, value in values.items()
            }
            for name, values in drag.PROFILES.items()
        },
        "variants": variants,
        "diagnostics": {
            "first": first_diag,
            "rearm": rearm_diag,
            "breaker_management": management_diag,
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
            "existing_cautious_drag_classifier_reused": True,
            "existing_cautious_drag_profiles_reused": True,
            "risk_only_adapter": True,
            "trade_count_changed": False,
            "trade_admission_changed": False,
            "silver_bullet_changed": False,
            "entry_changed": False,
            "initial_stop_changed_at_entry": False,
            "structural_target_changed": False,
            "rearm_changed": False,
            "fvg_management_changed": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_future_bars_for_drag_classification": False,
            "uses_fold_identity_at_runtime": False,
            "uses_calendar_date_at_runtime": False,
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
