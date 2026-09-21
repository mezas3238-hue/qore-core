"""Post-DOL1 structural runner protection frontier for VT31_NAS100.

Consumed development research only.

Root-cause hypothesis:
DOL1 is often followed by additional expansion, but a runner that keeps the
original initial stop can give back too much of an already-proven journey.
This frontier keeps DOL1 as a bank point and tests only causal M1 protective
swings AFTER DOL1 for the residual runner.

Rules:
- Silver Bullet and trade admission remain frozen;
- entry and original target are unchanged;
- 75% banks at DOL1, 25% remains runner;
- runner destination is DOL2 (+0.25 ref) or DOL3 (+0.50 ref);
- original methodological stop is the starting runner stop;
- protective swing requires left/middle/right closed M1 anatomy;
- confirmed swing becomes actionable only from the next M1;
- stop can improve or hold, never widen and never cross runner target;
- PS1 acts on first valid post-DOL1 protective swing;
- PS2 waits for the second valid post-DOL1 protective swing;
- same-M1 runner-target/stop ambiguity is fail-closed STOP FIRST;
- unresolved runner exits on final close before 16:00 NY;
- no BE, no universal DOL-lock, no future label.
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
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = (
    "qore.vt31.nas100.post_dol1_structural_runner_protection_frontier.v1"
)
MARKET = "NAS100"
BANK_FRACTION = Decimal("0.75")
RUNNER_FRACTION = Decimal("0.25")
EXTRA_RUNNER_FRICTION_R = Decimal("0.01")

VARIANTS = {
    "BASE": None,
    "DOL2_INITIAL_STOP": (Decimal("0.25"), 0),
    "DOL2_PS1": (Decimal("0.25"), 1),
    "DOL2_PS2": (Decimal("0.25"), 2),
    "DOL3_PS1": (Decimal("0.50"), 1),
    "DOL3_PS2": (Decimal("0.50"), 2),
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


def _touches_target(
    bar: object,
    *,
    side: str,
    level: Decimal,
) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= level
    return _d(getattr(bar, "low")) <= level


def _touches_stop(
    bar: object,
    *,
    side: str,
    level: Decimal,
) -> bool:
    if side == "long":
        return _d(getattr(bar, "low")) <= level
    return _d(getattr(bar, "high")) >= level


def _improves_stop(
    *,
    side: str,
    current_stop: Decimal,
    candidate: Decimal,
    runner_target: Decimal,
) -> bool:
    if side == "long":
        return current_stop < candidate < runner_target
    return runner_target < candidate < current_stop


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


def _runner_outcome(
    day_bars: tuple[object, ...],
    *,
    target_exit_at: datetime,
    side: str,
    entry: Decimal,
    initial_stop: Decimal,
    runner_target: Decimal,
    risk: Decimal,
    required_confirmations: int,
) -> tuple[Decimal, str, dict[str, object]]:
    target_index = next(
        (
            index
            for index, bar in enumerate(day_bars)
            if cast(datetime, getattr(bar, "closed_at"))
            == target_exit_at
        ),
        None,
    )
    if target_index is None:
        return Decimal(0), "CENSORED_TARGET_BAR_NOT_FOUND", {}

    path = tuple(
        bar
        for bar in day_bars[target_index:]
        if _wall(getattr(bar, "opened_at")) < (16, 0, 0)
    )
    if len(path) < 2:
        return Decimal(0), "CENSORED_NO_POST_TARGET_BARS", {}

    current_stop = initial_stop
    confirmations = 0
    protection_armed = False
    stop_improvements: list[str] = []

    # path[0] is the DOL1 target bar. Runner begins on path[1].
    for index in range(1, len(path)):
        bar = path[index]
        stop_hit = _touches_stop(
            bar,
            side=side,
            level=current_stop,
        )
        target_hit = _touches_target(
            bar,
            side=side,
            level=runner_target,
        )
        if stop_hit and target_hit:
            return (
                _stop_r(
                    side=side,
                    entry=entry,
                    risk=risk,
                    stop=current_stop,
                ),
                "SAME_BAR_STOP_FIRST",
                {
                    "protective_confirmations_seen": confirmations,
                    "structural_protection_armed": protection_armed,
                    "stop_improvements": stop_improvements,
                },
            )
        if stop_hit:
            return (
                _stop_r(
                    side=side,
                    entry=entry,
                    risk=risk,
                    stop=current_stop,
                ),
                (
                    "PROTECTIVE_SWING_STOP"
                    if current_stop != initial_stop
                    else "METHODOLOGICAL_STOP"
                ),
                {
                    "protective_confirmations_seen": confirmations,
                    "structural_protection_armed": protection_armed,
                    "stop_improvements": stop_improvements,
                },
            )
        if target_hit:
            return (
                abs(runner_target - entry) / risk,
                "RUNNER_TARGET",
                {
                    "protective_confirmations_seen": confirmations,
                    "structural_protection_armed": protection_armed,
                    "stop_improvements": stop_improvements,
                },
            )

        if required_confirmations > 0 and not protection_armed:
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
                    runner_target=runner_target,
                )
            ):
                confirmations += 1
                if confirmations >= required_confirmations:
                    current_stop = candidate
                    protection_armed = True
                    stop_improvements.append(format(candidate, "f"))

    final_close = _d(getattr(path[-1], "close"))
    return (
        _close_r(
            side=side,
            entry=entry,
            risk=risk,
            close=final_close,
        ),
        "16:00_LIFECYCLE",
        {
            "protective_confirmations_seen": confirmations,
            "structural_protection_armed": protection_armed,
            "stop_improvements": stop_improvements,
        },
    )


def _apply(
    rows: list[dict[str, object]],
    *,
    by_day: dict[date, tuple[object, ...]],
    extension_ref: Decimal,
    required_confirmations: int,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    statuses: Counter[str] = Counter()
    applied = 0
    armed = 0
    censored = 0

    for row in rows:
        updated = dict(row)
        if (
            row.get("exit_reason") != "structural-target"
            or _d(row["capital_weighted_net_r"]) <= 0
        ):
            adjusted.append(updated)
            continue

        entry = _opt_d(row.get("entry"))
        initial_stop = _opt_d(row.get("initial_stop"))
        target = _opt_d(row.get("structural_target"))
        risk_ref = _opt_d(row.get("risk_ref"))
        requested_risk = _opt_d(row.get("requested_risk_r"))
        exit_at = row.get("exit_at")
        if (
            entry is None
            or initial_stop is None
            or target is None
            or risk_ref is None
            or risk_ref <= 0
            or requested_risk is None
            or exit_at is None
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

        ref_width = risk / risk_ref
        side = str(row["side"])
        direction = Decimal(1) if side == "long" else Decimal(-1)
        runner_target = (
            target + direction * ref_width * extension_ref
        )

        runner_r, status, diag = _runner_outcome(
            day_bars,
            target_exit_at=_dt(exit_at),
            side=side,
            entry=entry,
            initial_stop=initial_stop,
            runner_target=runner_target,
            risk=risk,
            required_confirmations=required_confirmations,
        )
        target_r = abs(target - entry) / risk
        gross = (
            BANK_FRACTION * target_r
            + RUNNER_FRACTION * runner_r
        )
        net = requested_risk * (
            gross
            - engine.FRICTION
            - EXTRA_RUNNER_FRICTION_R
        )

        updated["bank_fraction"] = format(BANK_FRACTION, "f")
        updated["runner_fraction"] = format(RUNNER_FRACTION, "f")
        updated["runner_extension_ref"] = format(
            extension_ref,
            "f",
        )
        updated["runner_required_protective_confirmations"] = (
            required_confirmations
        )
        updated["runner_terminal_r"] = format(runner_r, "f")
        updated["runner_terminal_status"] = status
        updated["runner_structural_protection_armed"] = bool(
            diag.get("structural_protection_armed")
        )
        updated["runner_protective_confirmations_seen"] = int(
            diag.get("protective_confirmations_seen", 0)
        )
        updated["runner_stop_improvements"] = list(
            diag.get("stop_improvements", [])
        )
        updated["r_multiple"] = format(gross, "f")
        updated["capital_weighted_net_r"] = format(net, "f")
        updated["exit_reason"] = "structural-bank-plus-runner"

        applied += 1
        if updated["runner_structural_protection_armed"]:
            armed += 1
        statuses[status] += 1
        adjusted.append(updated)

    return adjusted, {
        "runner_applied_trade_count": applied,
        "structural_protection_armed_count": armed,
        "censored_geometry_count": censored,
        "runner_status_counts": dict(sorted(statuses.items())),
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
        raise ValueError("post-DOL1 runner protection requires NAS100")

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
                "runner_applied_trade_count": 0,
                "structural_protection_armed_count": 0,
                "censored_geometry_count": 0,
                "runner_status_counts": {},
            }
        else:
            extension_ref, confirmations = spec
            adjusted, diag = _apply(
                rows,
                by_day=by_day,
                extension_ref=extension_ref,
                required_confirmations=confirmations,
            )

        metrics = residual._metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=(
                f"POST_DOL1_STRUCTURAL_PROTECTION:{name}:{partition}"
            ),
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
                bool(block["positive"])
                for block in annual
            )

        variants[name] = {
            "trade_count": len(adjusted),
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "runner_diagnostics": diag,
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
            "consumed_evidence_only": True,
            "development_frontier_only": True,
            "dol1_bank_retained": True,
            "runner_fraction_fixed_025": True,
            "protective_swing_confirmed_on_closed_m1": True,
            "protective_swing_effective_next_m1": True,
            "stop_can_only_improve_or_hold": True,
            "stop_widened": False,
            "universal_dol_lock_used": False,
            "breakeven_rule_used": False,
            "same_bar_stop_first": True,
            "future_extension_runtime_input": False,
            "silver_bullet_changed": False,
            "trade_admission_changed": False,
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
