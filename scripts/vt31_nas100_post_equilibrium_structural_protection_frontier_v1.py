"""Post-equilibrium structural protection frontier for VT31_NAS100.

Development-only economic falsification.

Root-cause target:
Structural Target Ladder V1 localized the remaining weakness to trades that
reach the frozen reference equilibrium but fail to continue to DOL1. The best
ladder was near the consumed MC gate, but 40/69 EQ-touch trades in consumed
never staged DOL1 afterward.

This frontier does NOT change entry, initial stop, DOL1, or Silver Bullet.
After equilibrium is touched on a strictly earlier closed M1:
- bank the declared EQ fraction;
- protect ONLY the remaining position with a causal M1 protective swing;
- PS1 or PS2 is confirmed by left/middle/right CLOSED M1 anatomy;
- protection becomes actionable only from the next M1;
- stop can only improve or hold, never widen;
- if DOL1 is reached first, stage the declared DOL1 fraction and leave the
  declared runner toward DOL2 using the existing post-DOL1 PS2 logic;
- same-M1 stop/target ambiguity is STOP FIRST;
- no future labels are runtime inputs.

This tests whether the remaining MC gap is caused by giving back too much
after a valid structural milestone (EQ) when continuation to DOL1 fails.
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
import vt31_nas100_post_dol1_structural_runner_protection_v1 as post_dol1
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.post_equilibrium_structural_protection_frontier.v1"
MARKET = "NAS100"
EXTRA_EQ_FRICTION_R = Decimal("0.005")
EXTRA_RUNNER_FRICTION_R = Decimal("0.01")

VARIANTS = {
    "BASE": None,
    "EQ50_PS1_DOL125_RUN25_DOL2_PS2": (
        Decimal("0.50"),
        Decimal("0.25"),
        Decimal("0.25"),
        1,
    ),
    "EQ50_PS2_DOL125_RUN25_DOL2_PS2": (
        Decimal("0.50"),
        Decimal("0.25"),
        Decimal("0.25"),
        2,
    ),
    "EQ40_PS1_DOL140_RUN20_DOL2_PS2": (
        Decimal("0.40"),
        Decimal("0.40"),
        Decimal("0.20"),
        1,
    ),
    "EQ40_PS2_DOL140_RUN20_DOL2_PS2": (
        Decimal("0.40"),
        Decimal("0.40"),
        Decimal("0.20"),
        2,
    ),
}


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


def _touches_target(bar: object, *, side: str, level: Decimal) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= level
    return _d(getattr(bar, "low")) <= level


def _touches_stop(bar: object, *, side: str, level: Decimal) -> bool:
    if side == "long":
        return _d(getattr(bar, "low")) <= level
    return _d(getattr(bar, "high")) >= level


def _improves_stop(
    *,
    side: str,
    current_stop: Decimal,
    candidate: Decimal,
    target: Decimal,
) -> bool:
    if side == "long":
        return current_stop < candidate < target
    return target < candidate < current_stop


def _protective_swing_level(
    bars: tuple[object, ...],
    *,
    right_index: int,
    side: str,
) -> Decimal | None:
    if right_index < 2:
        return None
    left = bars[right_index - 2]
    middle = bars[right_index - 1]
    right = bars[right_index]
    if side == "long":
        level = _d(getattr(middle, "low"))
        if (
            level < _d(getattr(left, "low"))
            and level < _d(getattr(right, "low"))
        ):
            return level
        return None
    level = _d(getattr(middle, "high"))
    if (
        level > _d(getattr(left, "high"))
        and level > _d(getattr(right, "high"))
    ):
        return level
    return None


def _stop_r(
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
    stop: Decimal,
) -> Decimal:
    if side == "long":
        return (stop - entry) / risk
    return (entry - stop) / risk


def _close_r(
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
    close: Decimal,
) -> Decimal:
    if side == "long":
        return (close - entry) / risk
    return (entry - close) / risk


def _eq_remainder_to_dol1(
    day_bars: tuple[object, ...],
    *,
    eq_index: int,
    side: str,
    entry: Decimal,
    initial_stop: Decimal,
    dol1: Decimal,
    risk: Decimal,
    required_confirmations: int,
) -> tuple[str, Decimal, datetime | None, dict[str, object]]:
    current_stop = initial_stop
    confirmations = 0
    armed = False
    improvements: list[str] = []

    path = day_bars[eq_index:]
    for index in range(1, len(path)):
        bar = path[index]
        opened = cast(datetime, getattr(bar, "opened_at"))
        if _wall(opened) >= (16, 0, 0):
            break

        stop_hit = _touches_stop(bar, side=side, level=current_stop)
        target_hit = _touches_target(bar, side=side, level=dol1)

        if stop_hit and target_hit:
            return (
                "SAME_BAR_STOP_FIRST",
                _stop_r(
                    side=side,
                    entry=entry,
                    risk=risk,
                    stop=current_stop,
                ),
                None,
                {
                    "protective_confirmations_seen": confirmations,
                    "structural_protection_armed": armed,
                    "stop_improvements": improvements,
                },
            )
        if stop_hit:
            return (
                "PROTECTIVE_SWING_STOP" if armed else "METHODOLOGICAL_STOP",
                _stop_r(
                    side=side,
                    entry=entry,
                    risk=risk,
                    stop=current_stop,
                ),
                None,
                {
                    "protective_confirmations_seen": confirmations,
                    "structural_protection_armed": armed,
                    "stop_improvements": improvements,
                },
            )
        if target_hit:
            return (
                "DOL1_REACHED",
                abs(dol1 - entry) / risk,
                cast(datetime, getattr(bar, "closed_at")),
                {
                    "protective_confirmations_seen": confirmations,
                    "structural_protection_armed": armed,
                    "stop_improvements": improvements,
                },
            )

        if not armed:
            candidate = _protective_swing_level(
                path,
                right_index=index,
                side=side,
            )
            if (
                candidate is not None
                and _improves_stop(
                    side=side,
                    current_stop=current_stop,
                    candidate=candidate,
                    target=dol1,
                )
            ):
                confirmations += 1
                if confirmations >= required_confirmations:
                    current_stop = candidate
                    armed = True
                    improvements.append(format(candidate, "f"))

    final_close = _d(getattr(path[-1], "close"))
    return (
        "16:00_LIFECYCLE",
        _close_r(
            side=side,
            entry=entry,
            risk=risk,
            close=final_close,
        ),
        None,
        {
            "protective_confirmations_seen": confirmations,
            "structural_protection_armed": armed,
            "stop_improvements": improvements,
        },
    )


def _apply(
    rows: list[dict[str, object]],
    *,
    by_day: dict[date, tuple[object, ...]],
    eq_fraction: Decimal,
    dol1_fraction: Decimal,
    runner_fraction: Decimal,
    eq_ps_confirmations: int,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    eq_statuses: Counter[str] = Counter()
    runner_statuses: Counter[str] = Counter()
    eq_applied = 0
    eq_protected = 0
    dol1_staged = 0
    runner_applied = 0
    runner_protected = 0
    censored = 0

    for row in rows:
        updated = dict(row)
        entry = _opt_d(row.get("entry"))
        initial_stop = _opt_d(row.get("initial_stop"))
        dol1 = _opt_d(row.get("structural_target"))
        requested_risk = _opt_d(row.get("requested_risk_r"))
        filled_at_raw = row.get("filled_at")

        if (
            entry is None
            or initial_stop is None
            or dol1 is None
            or requested_risk is None
            or filled_at_raw is None
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

        eq_index = next(
            (
                index
                for index in range(fill_index, len(day_bars))
                if _wall(getattr(day_bars[index], "opened_at")) < (16, 0, 0)
                and _touches_target(
                    day_bars[index],
                    side=side,
                    level=equilibrium,
                )
            ),
            None,
        )
        if eq_index is None:
            adjusted.append(updated)
            continue

        eq_r = abs(equilibrium - entry) / risk
        eq_applied += 1

        status, remainder_r, dol1_at, eq_diag = _eq_remainder_to_dol1(
            day_bars,
            eq_index=eq_index,
            side=side,
            entry=entry,
            initial_stop=initial_stop,
            dol1=dol1,
            risk=risk,
            required_confirmations=eq_ps_confirmations,
        )
        eq_statuses[status] += 1
        if bool(eq_diag.get("structural_protection_armed")):
            eq_protected += 1

        if status != "DOL1_REACHED" or dol1_at is None:
            gross = (
                eq_fraction * eq_r
                + (Decimal("1") - eq_fraction) * remainder_r
            )
            net = requested_risk * (
                gross
                - engine.FRICTION
                - EXTRA_EQ_FRICTION_R
            )
            updated["post_eq_status"] = status
            updated["post_eq_structural_protection_armed"] = bool(
                eq_diag.get("structural_protection_armed")
            )
            updated["r_multiple"] = format(gross, "f")
            updated["capital_weighted_net_r"] = format(net, "f")
            updated["exit_reason"] = "eq-bank-post-eq-structural-protection"
            adjusted.append(updated)
            continue

        dol1_staged += 1
        direction = Decimal(1) if side == "long" else Decimal(-1)
        runner_target = dol1 + direction * ref_width * Decimal("0.25")
        runner_r, runner_status, runner_diag = post_dol1._runner_outcome(
            day_bars,
            target_exit_at=dol1_at,
            side=side,
            entry=entry,
            initial_stop=initial_stop,
            runner_target=runner_target,
            risk=risk,
            required_confirmations=2,
        )
        runner_statuses[runner_status] += 1
        runner_applied += 1
        if bool(runner_diag.get("structural_protection_armed")):
            runner_protected += 1

        dol1_r = abs(dol1 - entry) / risk
        gross = (
            eq_fraction * eq_r
            + dol1_fraction * dol1_r
            + runner_fraction * runner_r
        )
        net = requested_risk * (
            gross
            - engine.FRICTION
            - EXTRA_EQ_FRICTION_R
            - EXTRA_RUNNER_FRICTION_R
        )

        updated["post_eq_status"] = "DOL1_REACHED"
        updated["post_eq_structural_protection_armed"] = bool(
            eq_diag.get("structural_protection_armed")
        )
        updated["runner_terminal_status"] = runner_status
        updated["runner_structural_protection_armed"] = bool(
            runner_diag.get("structural_protection_armed")
        )
        updated["r_multiple"] = format(gross, "f")
        updated["capital_weighted_net_r"] = format(net, "f")
        updated["exit_reason"] = "eq-protected-dol1-runner-ladder"
        adjusted.append(updated)

    return adjusted, {
        "equilibrium_bank_applied_count": eq_applied,
        "post_eq_structural_protection_armed_count": eq_protected,
        "post_eq_status_counts": dict(sorted(eq_statuses.items())),
        "dol1_staged_count": dol1_staged,
        "runner_applied_count": runner_applied,
        "runner_structural_protection_armed_count": runner_protected,
        "runner_status_counts": dict(sorted(runner_statuses.items())),
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
        raise ValueError("post-equilibrium structural protection requires NAS100")

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
    for name, spec in VARIANTS.items():
        if spec is None:
            adjusted = [dict(row) for row in rows]
            diag = {
                "equilibrium_bank_applied_count": 0,
                "post_eq_structural_protection_armed_count": 0,
                "post_eq_status_counts": {},
                "dol1_staged_count": 0,
                "runner_applied_count": 0,
                "runner_structural_protection_armed_count": 0,
                "runner_status_counts": {},
                "censored_geometry_count": 0,
            }
        else:
            eq_fraction, dol1_fraction, run_fraction, confirmations = spec
            adjusted, diag = _apply(
                rows,
                by_day=by_day,
                eq_fraction=eq_fraction,
                dol1_fraction=dol1_fraction,
                runner_fraction=run_fraction,
                eq_ps_confirmations=confirmations,
            )

        metrics = residual._metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=f"POST_EQ_STRUCTURAL_PROTECT:{name}:{partition}",
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
            "trade_count": len(adjusted),
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "protection_diagnostics": diag,
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
            "equilibrium_known_before_trade": True,
            "post_eq_protection_closed_m1_only": True,
            "post_eq_protection_effective_next_m1": True,
            "stop_can_only_improve_or_hold": True,
            "stop_widened": False,
            "dol1_structural_target_retained": True,
            "runner_only_after_dol1": True,
            "future_journey_runtime_input": False,
            "same_bar_stop_first": True,
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
