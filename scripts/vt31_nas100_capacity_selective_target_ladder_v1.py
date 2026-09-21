"""Capacity-selective structural target ladder for VT31_NAS100.

Development-only economic falsification.

Starts from the strongest causal ladder:
- 50% bank at frozen reference equilibrium;
- remaining exposure reaches DOL1 or original terminal;
- runner is permitted only when causal capacity evidence supports deeper
  delivery.

If DOL1 is reached:
- no runner state: bank the remaining 50% at DOL1;
- runner state: bank 25% at DOL1 and run 25% toward DOL2 with PS2 structural
  protection.

Runner selectors under test:
- DEEP: Target Decision Engine V2 DEEP state known at entry;
- DEEP_ACCEPT: DEEP + DOL1 touch bar closes beyond DOL1;
- COMPRESSED_ACCEPT: compressed reference volatility + DOL1 bar closes beyond.

DOL1 acceptance is decided at the close of the DOL1 touch M1; runner becomes
effective from the next M1. Future extension is never a runtime input.

No stop widening, no trade admission change, no Silver Bullet change.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_post_dol1_structural_runner_protection_v1 as runner
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual
import vt31_nas100_structural_target_ladder_frontier_v1 as ladder
import vt31_nas100_target_decision_engine_frontier_v2 as target_v2

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.capacity_selective_target_ladder.v1"
MARKET = "NAS100"
EQ_FRACTION = Decimal("0.50")
DOL1_RUNNER_BANK_FRACTION = Decimal("0.25")
RUNNER_FRACTION = Decimal("0.25")
EXTRA_EQ_FRICTION_R = Decimal("0.005")
EXTRA_RUNNER_FRICTION_R = Decimal("0.01")
RUNNER_EXTENSION_REF = Decimal("0.25")

VARIANTS = (
    "EQ50_DOL1_FULL",
    "EQ50_DEEP_RUN25",
    "EQ50_DEEP_ACCEPT_RUN25",
    "EQ50_COMPRESSED_ACCEPT_RUN25",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _opt_d(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _dt(value: object) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _forward(*, side: str, entry: Decimal, level: Decimal) -> bool:
    return level > entry if side == "long" else level < entry


def _dol1_accepts(
    bar: object,
    *,
    side: str,
    target: Decimal,
) -> bool:
    close = _d(getattr(bar, "close"))
    if side == "long":
        return close >= target
    return close <= target


def _runner_selected(
    row: dict[str, object],
    *,
    variant: str,
    dol1_bar: object,
    side: str,
    target: Decimal,
) -> bool:
    if variant == "EQ50_DOL1_FULL":
        return False

    state, _ = target_v2._destination_state(row)
    accepts = _dol1_accepts(
        dol1_bar,
        side=side,
        target=target,
    )
    if variant == "EQ50_DEEP_RUN25":
        return state == "DEEP"
    if variant == "EQ50_DEEP_ACCEPT_RUN25":
        return state == "DEEP" and accepts
    if variant == "EQ50_COMPRESSED_ACCEPT_RUN25":
        return (
            row.get("reference_volatility_state") == "compressed"
            and accepts
        )
    raise ValueError(variant)


def _apply(
    rows: list[dict[str, object]],
    *,
    by_day: dict[date, tuple[object, ...]],
    variant: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    eq_applied = 0
    dol1_reached = 0
    runner_selected = 0
    runner_protected = 0
    censored = 0

    for row in rows:
        updated = dict(row)
        entry = _opt_d(row.get("entry"))
        initial_stop = _opt_d(row.get("initial_stop"))
        structural_target = _opt_d(row.get("structural_target"))
        requested_risk = _opt_d(row.get("requested_risk_r"))
        original_gross = _opt_d(row.get("r_multiple"))
        filled_at_raw = row.get("filled_at")
        terminal_at_raw = row.get("exit_at")

        if (
            entry is None
            or initial_stop is None
            or structural_target is None
            or requested_risk is None
            or original_gross is None
            or filled_at_raw is None
            or terminal_at_raw is None
        ):
            censored += 1
            adjusted.append(updated)
            continue

        risk = abs(entry - initial_stop)
        if risk <= 0:
            censored += 1
            adjusted.append(updated)
            continue

        local_day = date.fromisoformat(str(row["local_date"]))
        day_bars = by_day.get(local_day)
        if not day_bars:
            censored += 1
            adjusted.append(updated)
            continue

        reference = tuple(
            bar
            for bar in day_bars
            if (9, 0, 0) <= _wall(getattr(bar, "opened_at")) < (10, 0, 0)
        )
        if len(reference) != 60:
            censored += 1
            adjusted.append(updated)
            continue

        ref_high = max(_d(getattr(bar, "high")) for bar in reference)
        ref_low = min(_d(getattr(bar, "low")) for bar in reference)
        ref_width = ref_high - ref_low
        equilibrium = (ref_high + ref_low) / Decimal("2")
        side = str(row["side"])
        if (
            ref_width <= 0
            or not _forward(side=side, entry=entry, level=equilibrium)
        ):
            adjusted.append(updated)
            continue

        filled_at = _dt(filled_at_raw)
        terminal_at = _dt(terminal_at_raw)
        fill_index = next(
            (
                index
                for index, bar in enumerate(day_bars)
                if cast(datetime, getattr(bar, "closed_at")) == filled_at
            ),
            None,
        )
        if fill_index is None:
            censored += 1
            adjusted.append(updated)
            continue

        eq_index = ladder._first_touch_index(
            day_bars,
            start_index=fill_index,
            terminal_at=terminal_at,
            side=side,
            level=equilibrium,
        )
        if eq_index is None:
            adjusted.append(updated)
            continue

        eq_closed = cast(datetime, getattr(day_bars[eq_index], "closed_at"))
        if eq_closed >= terminal_at:
            adjusted.append(updated)
            continue

        eq_applied += 1
        eq_r = abs(equilibrium - entry) / risk

        dol1_index = ladder._first_touch_index(
            day_bars,
            start_index=eq_index + 1,
            terminal_at=terminal_at,
            side=side,
            level=structural_target,
        )
        if dol1_index is None:
            gross = (
                EQ_FRACTION * eq_r
                + (Decimal("1") - EQ_FRACTION) * original_gross
            )
            net = requested_risk * (
                gross
                - engine.FRICTION
                - EXTRA_EQ_FRICTION_R
            )
            updated["capacity_ladder_status"] = "EQ_ONLY_ORIGINAL_REMAINDER"
            updated["r_multiple"] = format(gross, "f")
            updated["capital_weighted_net_r"] = format(net, "f")
            updated["exit_reason"] = "eq-bank-plus-original-remainder"
            status_counts["EQ_ONLY_ORIGINAL_REMAINDER"] += 1
            adjusted.append(updated)
            continue

        dol1_reached += 1
        dol1_bar = day_bars[dol1_index]
        dol1_closed = cast(datetime, getattr(dol1_bar, "closed_at"))
        dol1_r = abs(structural_target - entry) / risk

        selected = _runner_selected(
            updated,
            variant=variant,
            dol1_bar=dol1_bar,
            side=side,
            target=structural_target,
        )
        if not selected:
            gross = EQ_FRACTION * eq_r + Decimal("0.50") * dol1_r
            net = requested_risk * (
                gross
                - engine.FRICTION
                - EXTRA_EQ_FRICTION_R
            )
            updated["capacity_ladder_status"] = "EQ50_DOL1_FULL_REMAINDER"
            updated["r_multiple"] = format(gross, "f")
            updated["capital_weighted_net_r"] = format(net, "f")
            updated["exit_reason"] = "eq50-dol1-full-remainder"
            status_counts["EQ50_DOL1_FULL_REMAINDER"] += 1
            adjusted.append(updated)
            continue

        runner_selected += 1
        direction = Decimal(1) if side == "long" else Decimal(-1)
        runner_target = (
            structural_target
            + direction * ref_width * RUNNER_EXTENSION_REF
        )
        runner_r, runner_status, runner_diag = runner._runner_outcome(
            day_bars,
            target_exit_at=dol1_closed,
            side=side,
            entry=entry,
            initial_stop=initial_stop,
            runner_target=runner_target,
            risk=risk,
            required_confirmations=2,
        )

        gross = (
            EQ_FRACTION * eq_r
            + DOL1_RUNNER_BANK_FRACTION * dol1_r
            + RUNNER_FRACTION * runner_r
        )
        net = requested_risk * (
            gross
            - engine.FRICTION
            - EXTRA_EQ_FRICTION_R
            - EXTRA_RUNNER_FRICTION_R
        )
        updated["capacity_ladder_status"] = "EQ50_DOL125_RUN25"
        updated["runner_terminal_r"] = format(runner_r, "f")
        updated["runner_terminal_status"] = runner_status
        updated["runner_structural_protection_armed"] = bool(
            runner_diag.get("structural_protection_armed")
        )
        updated["r_multiple"] = format(gross, "f")
        updated["capital_weighted_net_r"] = format(net, "f")
        updated["exit_reason"] = "capacity-selective-target-ladder"

        if updated["runner_structural_protection_armed"]:
            runner_protected += 1
        status_counts[f"RUNNER_{runner_status}"] += 1
        adjusted.append(updated)

    return adjusted, {
        "equilibrium_bank_applied_count": eq_applied,
        "dol1_reached_after_eq_count": dol1_reached,
        "runner_selected_count": runner_selected,
        "runner_structural_protection_armed_count": runner_protected,
        "status_counts": dict(sorted(status_counts.items())),
        "censored_geometry_count": censored,
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence, diagnostics, source_stats = alt._current_rows(path)
    (
        series,
        account,
        fingerprint,
        checked,
        evidence_sha,
        provider,
    ) = load_market_evidence(path)
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("capacity selective target ladder requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    variants: dict[str, object] = {}
    for name in VARIANTS:
        adjusted, diag = _apply(
            rows,
            by_day=by_day,
            variant=name,
        )
        metrics = residual._metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=f"CAPACITY_TARGET_LADDER:{name}:{partition}",
        )
        annual = (
            annuals._annual_blocks(
                adjusted,
                start=date(2022, 7, 18),
                years=2,
            )
            if partition == "consumed_holdout"
            else []
        )
        objectives = {
            "density_300_350": 300 <= len(adjusted) <= 350,
            "pf_ge_1_50": (
                metrics["profit_factor"] is not None
                and _d(metrics["profit_factor"]) >= Decimal("1.50")
            ),
            "dd_le_6": _d(metrics["max_drawdown_r"]) <= Decimal("6"),
            "mc_positive_ge_0_90": (
                _d(mc["positive_terminal_probability"])
                >= Decimal("0.90")
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
            "trade_count": len(adjusted),
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "ladder_diagnostics": diag,
            "objectives": objectives,
            "passes_economic_objectives": all(objectives.values()),
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "variants": variants,
        "source_stats": source_stats,
        "diagnostics": diagnostics,
        "evidence": {
            **evidence,
            "account_fingerprint": account,
            "evidence_fingerprint": fingerprint,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "development_frontier_only": True,
            "eq50_structural_bank": True,
            "runner_requires_capacity_selector": True,
            "dol1_acceptance_known_at_closed_m1": True,
            "runner_effective_next_m1": True,
            "future_extension_runtime_input": False,
            "runner_ps2_closed_m1_only": True,
            "stop_can_only_improve_or_hold": True,
            "stop_widened": False,
            "trade_admission_changed": False,
            "entry_changed": False,
            "silver_bullet_changed": False,
            "opens_new_holdout": False,
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
