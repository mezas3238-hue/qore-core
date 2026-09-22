"""Full structural target ladder frontier for VT31_NAS100.

Development-only economic falsification.

This frontier combines the structural findings already established:
1. Frozen 09:00-10:00 reference equilibrium is a meaningful intermediate
   destination reached materially more often than DOL1.
2. DOL1 is often followed by additional expansion.
3. A residual runner is better protected by confirmed M1 protective swings
   than by keeping only the original initial stop.

The ladder is causal:
- bank a declared fraction at equilibrium only when EQ is touched on a closed
  M1 strictly before the original terminal;
- if DOL1 is later reached on a strictly later M1, bank a second fraction;
- leave only the declared residual runner toward DOL2/DOL3;
- runner protection uses PS2: second confirmed M1 protective swing, effective
  on the next M1, never widening the stop;
- if DOL1 is not reached, the non-EQ remainder preserves the original terminal
  outcome;
- same-bar EQ/DOL1 is not credited as staged execution;
- same-bar runner stop/target is fail-closed STOP FIRST.

No future label participates in a runtime decision.
Silver Bullet, trade admission, entry and initial stop are unchanged.
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

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.structural_target_ladder_frontier.v1"
MARKET = "NAS100"
EXTRA_EQ_FRICTION_R = Decimal("0.005")
EXTRA_RUNNER_FRICTION_R = Decimal("0.01")

VARIANTS = {
    "BASE": None,
    "EQ50_DOL140_RUN10_DOL2_PS2": (
        Decimal("0.50"),
        Decimal("0.40"),
        Decimal("0.10"),
        Decimal("0.25"),
    ),
    "EQ50_DOL125_RUN25_DOL2_PS2": (
        Decimal("0.50"),
        Decimal("0.25"),
        Decimal("0.25"),
        Decimal("0.25"),
    ),
    "EQ40_DOL140_RUN20_DOL2_PS2": (
        Decimal("0.40"),
        Decimal("0.40"),
        Decimal("0.20"),
        Decimal("0.25"),
    ),
    "EQ25_DOL150_RUN25_DOL2_PS2": (
        Decimal("0.25"),
        Decimal("0.50"),
        Decimal("0.25"),
        Decimal("0.25"),
    ),
    "EQ50_DOL125_RUN25_DOL3_PS2": (
        Decimal("0.50"),
        Decimal("0.25"),
        Decimal("0.25"),
        Decimal("0.50"),
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


def _touches(bar: object, *, side: str, level: Decimal) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= level
    return _d(getattr(bar, "low")) <= level


def _first_touch_index(
    bars: tuple[object, ...],
    *,
    start_index: int,
    terminal_at: datetime,
    side: str,
    level: Decimal,
) -> int | None:
    for index in range(start_index, len(bars)):
        bar = bars[index]
        opened = cast(datetime, getattr(bar, "opened_at"))
        closed = cast(datetime, getattr(bar, "closed_at"))
        if opened >= terminal_at or closed > terminal_at:
            break
        if _wall(opened) >= (16, 0, 0):
            break
        if _touches(bar, side=side, level=level):
            return index
    return None


def _apply(
    rows: list[dict[str, object]],
    *,
    by_day: dict[date, tuple[object, ...]],
    eq_fraction: Decimal,
    dol1_fraction: Decimal,
    runner_fraction: Decimal,
    runner_extension_ref: Decimal,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    if eq_fraction + dol1_fraction + runner_fraction != Decimal("1"):
        raise ValueError("target ladder fractions must sum to 1")

    adjusted: list[dict[str, object]] = []
    statuses: Counter[str] = Counter()
    eq_applied = 0
    dol1_staged = 0
    runner_applied = 0
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

        eq_index = _first_touch_index(
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

        eq_r = abs(equilibrium - entry) / risk
        eq_applied += 1

        dol1_index = _first_touch_index(
            day_bars,
            start_index=eq_index + 1,
            terminal_at=terminal_at,
            side=side,
            level=structural_target,
        )

        if dol1_index is None:
            gross = (
                eq_fraction * eq_r
                + (Decimal("1") - eq_fraction) * original_gross
            )
            net = requested_risk * (
                gross
                - engine.FRICTION
                - EXTRA_EQ_FRICTION_R
            )
            updated["target_ladder_status"] = "EQ_ONLY_ORIGINAL_REMAINDER"
            updated["r_multiple"] = format(gross, "f")
            updated["capital_weighted_net_r"] = format(net, "f")
            updated["exit_reason"] = "eq-bank-plus-original-remainder"
            statuses["EQ_ONLY_ORIGINAL_REMAINDER"] += 1
            adjusted.append(updated)
            continue

        dol1_closed = cast(
            datetime,
            getattr(day_bars[dol1_index], "closed_at"),
        )
        if dol1_closed <= eq_closed:
            statuses["CENSORED_EQ_DOL1_ORDER"] += 1
            adjusted.append(updated)
            continue

        dol1_r = abs(structural_target - entry) / risk
        direction = Decimal(1) if side == "long" else Decimal(-1)
        runner_target = (
            structural_target
            + direction * ref_width * runner_extension_ref
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

        updated["target_ladder_status"] = "EQ_DOL1_RUNNER"
        updated["target_ladder_eq_fraction"] = format(eq_fraction, "f")
        updated["target_ladder_dol1_fraction"] = format(dol1_fraction, "f")
        updated["target_ladder_runner_fraction"] = format(
            runner_fraction,
            "f",
        )
        updated["target_ladder_runner_extension_ref"] = format(
            runner_extension_ref,
            "f",
        )
        updated["runner_terminal_r"] = format(runner_r, "f")
        updated["runner_terminal_status"] = runner_status
        updated["runner_structural_protection_armed"] = bool(
            runner_diag.get("structural_protection_armed")
        )
        updated["r_multiple"] = format(gross, "f")
        updated["capital_weighted_net_r"] = format(net, "f")
        updated["exit_reason"] = "structural-target-ladder"

        dol1_staged += 1
        runner_applied += 1
        if updated["runner_structural_protection_armed"]:
            runner_protected += 1
        statuses[f"RUNNER_{runner_status}"] += 1
        adjusted.append(updated)

    return adjusted, {
        "equilibrium_bank_applied_count": eq_applied,
        "dol1_staged_count": dol1_staged,
        "runner_applied_count": runner_applied,
        "runner_structural_protection_armed_count": runner_protected,
        "status_counts": dict(sorted(statuses.items())),
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
        raise ValueError("structural target ladder requires NAS100")

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
                "dol1_staged_count": 0,
                "runner_applied_count": 0,
                "runner_structural_protection_armed_count": 0,
                "status_counts": {},
                "censored_geometry_count": 0,
            }
        else:
            eq_fraction, dol1_fraction, run_fraction, extension = spec
            adjusted, diag = _apply(
                rows,
                by_day=by_day,
                eq_fraction=eq_fraction,
                dol1_fraction=dol1_fraction,
                runner_fraction=run_fraction,
                runner_extension_ref=extension,
            )

        metrics = residual._metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=f"STRUCTURAL_TARGET_LADDER:{name}:{partition}",
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
            "equilibrium_known_before_trade": True,
            "dol1_structural_target_retained": True,
            "runner_only_after_dol1": True,
            "runner_ps2_closed_m1_only": True,
            "runner_stop_can_only_improve_or_hold": True,
            "same_bar_eq_dol1_not_staged": True,
            "same_bar_runner_stop_first": True,
            "future_journey_runtime_input": False,
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
