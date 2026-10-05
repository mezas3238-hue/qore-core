"""Market-native structural reloss frontier for VT31 NAS100.

Tests whether the source confirmation level can serve as a causal post-fill
thesis invalidation before the original swing-extreme stop.

Runtime decision inputs are price/structure/time only:
- original source structural confirmation level;
- closed M1 prices;
- original structural stop;
- opposite frozen 09 reference boundary;
- lifecycle.

R is computed only after terminal outcomes for evaluation.
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

SCHEMA = "qore.vt31.nas100.market_native_structural_reloss.v1"
VARIANTS = {
    "BASELINE": None,
    "STRUCTURE_RELOSS_1_CLOSE": 1,
    "STRUCTURE_RELOSS_2_CLOSE": 2,
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _beyond_structural_level(
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


def _open_through_original_level(
    *,
    side: str,
    opened: Decimal,
    stop: Decimal,
    target: Decimal,
) -> str | None:
    if side == "long":
        if opened <= stop:
            return "stop"
        if opened >= target:
            return "target"
    elif side == "short":
        if opened >= stop:
            return "stop"
        if opened <= target:
            return "target"
    else:
        raise ValueError(f"unsupported side: {side}")
    return None


def _simulate_structural_reloss(
    day_bars: tuple[object, ...],
    executable: object,
    *,
    required_closes: int,
) -> dict[str, object]:
    if required_closes not in {1, 2}:
        raise ValueError("required_closes must be 1 or 2")

    side = str(getattr(getattr(executable, "side"), "value"))
    entry = _d(getattr(executable, "entry_price"))
    stop = _d(getattr(executable, "stop_price"))
    target = _d(getattr(executable, "target_price"))
    risk = _d(getattr(executable, "initial_risk"))
    structural_level = _d(
        getattr(getattr(getattr(executable, "source_setup"), "structure"), "structural_level")
    )
    decision_at = cast(datetime, getattr(executable, "decision_at"))
    selected_family = str(
        getattr(getattr(executable, "selected_family"), "value")
    )
    if risk <= 0:
        return {"status": "censored-invalid-risk"}

    fill_index = v2b._fill_index(day_bars, executable)
    if fill_index is None:
        return {"status": "no-fill"}

    first = day_bars[fill_index]
    first_low = _d(getattr(first, "low"))
    first_high = _d(getattr(first, "high"))
    stop_hit = first_low <= stop if side == "long" else first_high >= stop
    target_hit = first_high >= target if side == "long" else first_low <= target
    if stop_hit or target_hit:
        return {"status": "censored-fill-bar-path"}

    previous = first
    filled_at = cast(datetime, getattr(first, "closed_at"))
    max_favorable = Decimal(0)
    max_adverse = Decimal(0)
    reloss_streak = 0
    pending_reloss = False
    trigger_at: datetime | None = None
    terminal: Decimal | None = None
    exit_reason: str | None = None
    exit_at: datetime | None = None
    exit_price: Decimal | None = None

    for bar in day_bars[fill_index + 1 :]:
        if specialist.baseline._local_minute(bar) >= specialist.LIFECYCLE_MINUTE:
            break
        opened_at = cast(datetime, getattr(bar, "opened_at"))
        if opened_at != cast(datetime, getattr(previous, "closed_at")):
            return {"status": "censored-gap-after-fill"}
        previous = bar

        opened = _d(getattr(bar, "open"))
        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))

        if pending_reloss:
            through = _open_through_original_level(
                side=side,
                opened=opened,
                stop=stop,
                target=target,
            )
            if through == "stop":
                terminal = specialist.baseline._terminal_r(
                    side,
                    entry,
                    stop,
                    risk,
                )
                exit_reason = "structural-invalidation-gap"
                exit_price = stop
            elif through == "target":
                terminal = abs(target - entry) / risk
                exit_reason = "structural-target-gap"
                exit_price = target
            else:
                terminal = (
                    (opened - entry) / risk
                    if side == "long"
                    else (entry - opened) / risk
                )
                exit_reason = "confirmation-structure-reloss"
                exit_price = opened
            exit_at = opened_at
            break

        favorable, adverse = specialist.baseline._favorable_adverse(
            bar,
            side,
            entry,
            risk,
        )
        max_favorable = max(max_favorable, favorable)
        max_adverse = max(max_adverse, adverse)

        hit_stop = low <= stop if side == "long" else high >= stop
        hit_target = high >= target if side == "long" else low <= target
        if hit_stop and hit_target:
            return {"status": "censored-same-bar-stop-target"}
        if hit_stop:
            terminal = specialist.baseline._terminal_r(
                side,
                entry,
                stop,
                risk,
            )
            exit_reason = "structural-invalidation"
            exit_price = stop
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break
        if hit_target:
            terminal = abs(target - entry) / risk
            exit_reason = "structural-target"
            exit_price = target
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break

        close = _d(getattr(bar, "close"))
        if _beyond_structural_level(
            side=side,
            close=close,
            structural_level=structural_level,
        ):
            reloss_streak += 1
        else:
            reloss_streak = 0

        if reloss_streak >= required_closes:
            pending_reloss = True
            trigger_at = cast(datetime, getattr(bar, "closed_at"))

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
        terminal = (
            (close - entry) / risk
            if side == "long"
            else (entry - close) / risk
        )
        exit_reason = "16:00-lifecycle"
        exit_price = close
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
        "exit_price": format(cast(Decimal, exit_price), "f"),
        "structural_confirmation_level": format(structural_level, "f"),
        "structural_reloss_required_closes": required_closes,
        "structural_reloss_trigger_at": (
            None
            if trigger_at is None
            else trigger_at.astimezone(UTC).isoformat()
        ),
        "r_multiple": format(terminal, "f"),
        "mfe_r": format(max_favorable, "f"),
        "mae_r": format(max_adverse, "f"),
        "r_runtime_authority": False,
        "volume_runtime_authority": False,
        "partial_exit_used": False,
        "breakeven_armed": False,
    }


def _variant_simulator(
    required_closes: int,
) -> Callable[[tuple[object, ...], object, dict[str, object]], dict[str, object]]:
    def simulate(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        outcome = _simulate_structural_reloss(
            day_bars,
            executable,
            required_closes=required_closes,
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
        for name, required_closes in VARIANTS.items():
            if required_closes is None:
                specialist._simulate_selected_plan = original
            else:
                specialist._simulate_selected_plan = _variant_simulator(
                    required_closes
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
            "quarter_stress": payload["quarter_stress"],
            "monte_carlo": payload["monte_carlo"],
            "winner_preservation_vs_baseline": (
                None
                if name == "BASELINE"
                else _winner_preservation(baseline, trades)
            ),
            "reloss_exit_count": sum(
                str(row.get("exit_reason"))
                == "confirmation-structure-reloss"
                for row in trades
            ),
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
            "initial_swing_stop_changed": False,
            "runtime_r_decision_authority": False,
            "runtime_volume_decision_authority": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "partial_exit_used": False,
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
