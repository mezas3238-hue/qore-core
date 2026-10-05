"""Market-native momentum + structural-swing protection for VT31 NAS100.

Development research on consumed evidence only.

A stop may improve once when a confirmed M1 protective swing exists and recent
closed-price momentum has stopped progressing in the trade direction.
A stricter variant additionally requires current price to have relost the
source confirmation structure.

No R multiple, MFE/MAE, volume, sizing, leverage, or fixed profit threshold is
used by the runtime decision.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.market_native_momentum_swing_protection.v1"
VARIANTS = {
    "BASELINE": "BASELINE",
    "MOMENTUM_SWING_ONCE": "MOMENTUM",
    "RELOSS_MOMENTUM_SWING_ONCE": "RELOSS_MOMENTUM",
}
MOMENTUM_WINDOW_CLOSED_BARS = 5


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _improves_stop(
    *,
    side: str,
    current_stop: Decimal,
    candidate: Decimal,
    target: Decimal,
) -> bool:
    if side == "long":
        return current_stop < candidate < target
    if side == "short":
        return target < candidate < current_stop
    raise ValueError(f"unsupported side: {side}")


def _protective_swing(
    bars: tuple[object, ...],
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
    if side == "short":
        level = _d(getattr(middle, "high"))
        if (
            level > _d(getattr(left, "high"))
            and level > _d(getattr(right, "high"))
        ):
            return level
        return None
    raise ValueError(f"unsupported side: {side}")


def _momentum_deteriorated(
    bars: tuple[object, ...],
    right_index: int,
    side: str,
) -> bool:
    start = right_index - MOMENTUM_WINDOW_CLOSED_BARS + 1
    if start < 0:
        return False
    first = _d(getattr(bars[start], "close"))
    last = _d(getattr(bars[right_index], "close"))
    if side == "long":
        return last <= first
    if side == "short":
        return last >= first
    raise ValueError(f"unsupported side: {side}")


def _structure_relost(
    *,
    side: str,
    close: Decimal,
    structural_level: Decimal,
) -> bool:
    if side == "long":
        return close < structural_level
    if side == "short":
        return close > structural_level
    raise ValueError(f"unsupported side: {side}")


def _terminal_r(
    *,
    side: str,
    entry: Decimal,
    price: Decimal,
    risk: Decimal,
) -> Decimal:
    if side == "long":
        return (price - entry) / risk
    if side == "short":
        return (entry - price) / risk
    raise ValueError(f"unsupported side: {side}")


def _simulate(
    day_bars: tuple[object, ...],
    executable: object,
    *,
    require_structure_reloss: bool,
) -> dict[str, object]:
    side = str(getattr(executable.side, "value"))
    entry = _d(getattr(executable, "entry_price"))
    initial_stop = _d(getattr(executable, "stop_price"))
    target = _d(getattr(executable, "target_price"))
    risk = _d(getattr(executable, "initial_risk"))
    structural_level = _d(executable.source_setup.structure.structural_level)
    decision_at = cast(datetime, getattr(executable, "decision_at"))
    selected_family = str(getattr(executable.selected_family, "value"))
    if risk <= 0:
        return {"status": "censored-invalid-risk"}

    fill_index = v2b._fill_index(day_bars, executable)
    if fill_index is None:
        return {"status": "no-fill"}

    first = day_bars[fill_index]
    first_low = _d(getattr(first, "low"))
    first_high = _d(getattr(first, "high"))
    stop_hit = (
        first_low <= initial_stop
        if side == "long"
        else first_high >= initial_stop
    )
    target_hit = (
        first_high >= target
        if side == "long"
        else first_low <= target
    )
    if stop_hit or target_hit:
        return {"status": "censored-fill-bar-path"}

    post_fill = tuple(day_bars[fill_index:])
    current_stop = initial_stop
    pending_stop: Decimal | None = None
    protection_armed = False
    protection_trigger_at: datetime | None = None
    max_favorable = Decimal(0)
    max_adverse = Decimal(0)
    previous = first
    filled_at = cast(datetime, getattr(first, "closed_at"))
    terminal: Decimal | None = None
    exit_reason: str | None = None
    exit_at: datetime | None = None

    for local_index in range(1, len(post_fill)):
        bar = post_fill[local_index]
        if specialist.baseline._local_minute(bar) >= specialist.LIFECYCLE_MINUTE:
            break
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return {"status": "censored-gap-after-fill"}
        previous = bar

        # A closed-bar observation may change the stop only from this new bar.
        if pending_stop is not None:
            if _improves_stop(
                side=side,
                current_stop=current_stop,
                candidate=pending_stop,
                target=target,
            ):
                current_stop = pending_stop
                protection_armed = True
            pending_stop = None

        favorable, adverse = specialist.baseline._favorable_adverse(
            bar,
            side,
            entry,
            risk,
        )
        max_favorable = max(max_favorable, favorable)
        max_adverse = max(max_adverse, adverse)

        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        hit_stop = (
            low <= current_stop if side == "long" else high >= current_stop
        )
        hit_target = high >= target if side == "long" else low <= target
        if hit_stop and hit_target:
            return {"status": "censored-same-bar-stop-target"}
        if hit_stop:
            terminal = _terminal_r(
                side=side,
                entry=entry,
                price=current_stop,
                risk=risk,
            )
            exit_reason = (
                "confirmed-structural-swing-stop"
                if current_stop != initial_stop
                else "structural-invalidation"
            )
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break
        if hit_target:
            terminal = abs(target - entry) / risk
            exit_reason = "structural-target"
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break

        if not protection_armed and pending_stop is None:
            candidate = _protective_swing(
                post_fill,
                local_index,
                side,
            )
            if candidate is not None and _improves_stop(
                side=side,
                current_stop=current_stop,
                candidate=candidate,
                target=target,
            ):
                momentum_bad = _momentum_deteriorated(
                    post_fill,
                    local_index,
                    side,
                )
                close = _d(getattr(bar, "close"))
                relost = _structure_relost(
                    side=side,
                    close=close,
                    structural_level=structural_level,
                )
                eligible = momentum_bad and (
                    relost if require_structure_reloss else True
                )
                if eligible:
                    pending_stop = candidate
                    protection_trigger_at = cast(
                        datetime,
                        getattr(bar, "closed_at"),
                    )

    if terminal is None:
        eligible = [
            bar
            for bar in day_bars[fill_index:]
            if specialist.baseline._local_minute(bar)
            < specialist.LIFECYCLE_MINUTE
        ]
        if not eligible:
            return {"status": "censored-no-lifecycle-close"}
        final = eligible[-1]
        close = _d(getattr(final, "close"))
        terminal = _terminal_r(
            side=side,
            entry=entry,
            price=close,
            risk=risk,
        )
        exit_reason = "16:00-lifecycle"
        exit_at = cast(datetime, getattr(final, "closed_at"))

    return {
        "status": "terminal",
        "local_date": specialist._day(decision_at).isoformat(),
        "side": side,
        "signal_at": decision_at.astimezone(UTC).isoformat(),
        "filled_at": filled_at.astimezone(UTC).isoformat(),
        "exit_at": cast(datetime, exit_at).astimezone(UTC).isoformat(),
        "entry_family": selected_family,
        "exit_reason": exit_reason,
        "r_multiple": format(terminal, "f"),
        "mfe_r": format(max_favorable, "f"),
        "mae_r": format(max_adverse, "f"),
        "structural_confirmation_level": format(structural_level, "f"),
        "momentum_window_closed_bars": MOMENTUM_WINDOW_CLOSED_BARS,
        "requires_structure_reloss": require_structure_reloss,
        "structural_protection_armed": protection_armed,
        "structural_protection_trigger_at": (
            None
            if protection_trigger_at is None
            else protection_trigger_at.astimezone(UTC).isoformat()
        ),
        "r_runtime_authority": False,
        "volume_runtime_authority": False,
        "partial_exit_used": False,
        "breakeven_armed": False,
    }


def _variant_simulator(
    *,
    require_structure_reloss: bool,
) -> Callable[[tuple[object, ...], object, dict[str, object]], dict[str, object]]:
    def simulate(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        outcome = _simulate(
            day_bars,
            executable,
            require_structure_reloss=require_structure_reloss,
        )
        if outcome.get("status") == "terminal":
            outcome["target_plan"] = state["target_plan"]
        return outcome

    return simulate


def _winner_preservation(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> dict[str, object]:
    base = {
        str(row["signal_at"]): _d(row["r_multiple"]) - specialist.FRICTION
        for row in baseline
    }
    cand = {
        str(row["signal_at"]): _d(row["r_multiple"]) - specialist.FRICTION
        for row in candidate
    }
    winners = {key: value for key, value in base.items() if value > 0}
    if not winners:
        return {
            "baseline_winner_count": 0,
            "winner_count_preservation": None,
            "winner_r_preservation": None,
        }
    kept = {
        key: cand[key]
        for key in winners
        if key in cand and cand[key] > 0
    }
    return {
        "baseline_winner_count": len(winners),
        "winner_count_preservation": format(
            Decimal(len(kept)) / Decimal(len(winners)),
            "f",
        ),
        "winner_r_preservation": format(
            sum(kept.values(), Decimal(0))
            / sum(winners.values(), Decimal(0)),
            "f",
        ),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    payloads: dict[str, dict[str, object]] = {}
    try:
        for name, mode in VARIANTS.items():
            if mode == "BASELINE":
                specialist._simulate_selected_plan = original
            else:
                specialist._simulate_selected_plan = _variant_simulator(
                    require_structure_reloss=(mode == "RELOSS_MOMENTUM"),
                )
            payloads[name] = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    baseline = cast(list[dict[str, object]], payloads["BASELINE"]["trades"])
    reports: dict[str, object] = {}
    for name, payload in payloads.items():
        trades = cast(list[dict[str, object]], payload["trades"])
        reports[name] = {
            "trade_count": len(trades),
            "stress_0_05r": payload["stress_0_05r"],
            "halfyear_stress": payload["halfyear_stress"],
            "monte_carlo": payload["monte_carlo"],
            "winner_preservation_vs_baseline": (
                None
                if name == "BASELINE"
                else _winner_preservation(baseline, trades)
            ),
            "protection_armed_count": sum(
                row.get("structural_protection_armed") is True
                for row in trades
            ),
            "trade_rows": trades,
        }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "variants": reports,
        "governance": {
            "consumed_evidence_only": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "primary_structural_target_changed": False,
            "runtime_r_decision_authority": False,
            "runtime_volume_decision_authority": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "fixed_profit_threshold_used": False,
            "fresh_holdout_opened": False,
            "automatic_policy_promotion": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "variants": payload["variants"],
                "governance": payload["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
