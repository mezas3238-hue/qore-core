"""High-density structural protection lab for VT31_NAS100.

Consumed-evidence research only.

The causal OCO router supplies one selected entry per source event. This lab
keeps the original structural destination and tests whether drawdown can be
reduced by a *single* confirmed M1 protective-swing stop improvement.

A protective swing:
- is confirmed only when the right bar closes;
- is actionable from the next M1 bar;
- may only improve the current stop;
- never widens risk;
- never crosses the structural target.

Predeclared variants:
- BASELINE: original source stop + 3R breakeven.
- CAUTIOUS_FIRST: one protective swing only in CAUTIOUS.
- NON_SUPPORTIVE_FIRST: one protective swing in MIXED or CAUTIOUS.
- CONTEXT_0_2_1: SUPPORTIVE no swing, MIXED waits for two confirmed protective
  swings, CAUTIOUS acts on the first.

No context is filtered from entry. No terminal PnL enters the context state.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_high_density_management_intelligence_v1 as management
import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
)

SCHEMA = "qore.vt31.nas100.high_density_structural_protection.v1"
MARKET = "NAS100"
VARIANTS = (
    "BASELINE",
    "CAUTIOUS_FIRST",
    "NON_SUPPORTIVE_FIRST",
    "CONTEXT_0_2_1",
)

EXPOSURE_PROFILES = {
    "FULL_RISK": {
        "SUPPORTIVE": Decimal("1.0"),
        "MIXED": Decimal("1.0"),
        "CAUTIOUS": Decimal("1.0"),
    },
    "S1_M05_C025": {
        "SUPPORTIVE": Decimal("1.0"),
        "MIXED": Decimal("0.5"),
        "CAUTIOUS": Decimal("0.25"),
    },
    "S1_M075_C025": {
        "SUPPORTIVE": Decimal("1.0"),
        "MIXED": Decimal("0.75"),
        "CAUTIOUS": Decimal("0.25"),
    },
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _improves_stop(
    side: str,
    current: Decimal,
    candidate: Decimal,
    target: Decimal,
) -> bool:
    if side == "long":
        return current < candidate < target
    return target < candidate < current


def _required_confirmations(variant: str, context: str) -> int | None:
    if variant == "BASELINE":
        return None
    if variant == "CAUTIOUS_FIRST":
        return 1 if context == "CAUTIOUS" else None
    if variant == "NON_SUPPORTIVE_FIRST":
        return None if context == "SUPPORTIVE" else 1
    if variant == "CONTEXT_0_2_1":
        if context == "SUPPORTIVE":
            return None
        return 2 if context == "MIXED" else 1
    raise ValueError(variant)


def _protective_swing_level(
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
    level = _d(getattr(middle, "high"))
    if (
        level > _d(getattr(left, "high"))
        and level > _d(getattr(right, "high"))
    ):
        return level
    return None


def _terminal_r(
    side: str,
    entry: Decimal,
    stop: Decimal,
    risk: Decimal,
) -> Decimal:
    return (
        (stop - entry) / risk
        if side == "long"
        else (entry - stop) / risk
    )


def _simulate_single_structural_trail(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
    *,
    required_confirmations: int | None,
) -> dict[str, object]:
    if required_confirmations is None:
        return specialist.baseline._simulate(day_bars, setup)

    side = setup.side.value
    entry = setup.entry_price
    initial_stop = setup.stop_price
    target = setup.target_price
    three_r = setup.three_r_price
    risk = setup.initial_risk
    if risk <= 0:
        return {"status": "censored-invalid-risk"}

    fill_index = v2b._fill_index(day_bars, setup)
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

    current_stop = initial_stop
    be_armed = False
    structural_trail_armed = False
    protective_confirmations = 0
    previous = first
    filled_at = cast(datetime, getattr(first, "closed_at"))
    exit_at: datetime | None = None
    exit_reason: str | None = None
    terminal: Decimal | None = None

    post_fill = tuple(day_bars[fill_index:])
    for local_index in range(1, len(post_fill)):
        bar = post_fill[local_index]
        if specialist.baseline._local_minute(bar) >= specialist.LIFECYCLE_MINUTE:
            break
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return {"status": "censored-gap-after-fill"}
        previous = bar

        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        hit_stop = (
            low <= current_stop if side == "long" else high >= current_stop
        )
        hit_target = (
            high >= target if side == "long" else low <= target
        )
        if hit_stop and hit_target:
            return {"status": "censored-same-bar-stop-target"}
        if hit_stop:
            terminal = _terminal_r(side, entry, current_stop, risk)
            if current_stop == initial_stop:
                exit_reason = "initial-stop"
            elif current_stop == entry:
                exit_reason = "breakeven-stop"
            else:
                exit_reason = "single-protective-swing-stop"
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break
        if hit_target:
            terminal = abs(target - entry) / risk
            exit_reason = "structural-target"
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break

        # Events observed on this closed bar become active only next bar.
        if not be_armed:
            touched_three_r = (
                high >= three_r if side == "long" else low <= three_r
            )
            if touched_three_r:
                be_armed = True
                if _improves_stop(side, current_stop, entry, target):
                    current_stop = entry

        if not structural_trail_armed:
            candidate = _protective_swing_level(
                post_fill,
                local_index,
                side,
            )
            if (
                candidate is not None
                and _improves_stop(
                    side,
                    initial_stop,
                    candidate,
                    target,
                )
            ):
                protective_confirmations += 1
                if protective_confirmations >= required_confirmations:
                    if _improves_stop(
                        side,
                        current_stop,
                        candidate,
                        target,
                    ):
                        current_stop = candidate
                    structural_trail_armed = True

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
        exit_at = cast(datetime, getattr(final, "closed_at"))

    return {
        "status": "terminal",
        "local_date": _day(setup.decision_at).isoformat(),
        "side": side,
        "signal_at": setup.decision_at.astimezone(UTC).isoformat(),
        "filled_at": filled_at.astimezone(UTC).isoformat(),
        "exit_at": cast(datetime, exit_at).astimezone(UTC).isoformat(),
        "entry_family": setup.selected_family.value,
        "exit_reason": exit_reason,
        "r_multiple": format(terminal, "f"),
        "protective_confirmations_seen": protective_confirmations,
        "structural_trail_armed": structural_trail_armed,
    }


def _exposure_adjusted_trades(
    trades: list[dict[str, object]],
    profile: dict[str, Decimal],
) -> list[dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    for trade in trades:
        context = str(trade["management_context"])
        weight = profile[context]
        gross = Decimal(cast(str, trade["r_multiple"]))
        # _metrics/_monte_carlo subtract 0.05R per trade. Encode the gross so
        # that the resulting net is weight * (gross - 0.05R).
        encoded_gross = (
            weight * gross
            + specialist.FRICTION * (Decimal("1") - weight)
        )
        row = dict(trade)
        row["r_multiple"] = format(encoded_gross, "f")
        row["exposure_weight"] = format(weight, "f")
        adjusted.append(row)
    return adjusted


def _bundle(trades: list[dict[str, object]]) -> dict[str, object]:
    exposure_profiles = {}
    for name, profile in EXPOSURE_PROFILES.items():
        adjusted = _exposure_adjusted_trades(trades, profile)
        exposure_profiles[name] = {
            "weights": {
                key: format(value, "f")
                for key, value in profile.items()
            },
            "stress_0_05r_base": _metrics(
                adjusted,
                friction=specialist.FRICTION,
            ),
            "monte_carlo_base": specialist._monte_carlo(adjusted),
        }
    return {
        "sample": len(trades),
        "stress_0_05r": _metrics(
            trades,
            friction=specialist.FRICTION,
        ),
        "monte_carlo": specialist._monte_carlo(trades),
        "exit_reasons": dict(
            sorted(
                Counter(
                    str(trade["exit_reason"]) for trade in trades
                ).items()
            )
        ),
        "exposure_profiles": exposure_profiles,
    }


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("structural protection lab requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        day: tuple(sorted(rows, key=lambda item: getattr(item, "opened_at")))
        for day, rows in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = Vt31R22ExecutionPolicy()

    trades: dict[str, list[dict[str, object]]] = {
        variant: [] for variant in VARIANTS
    }
    context_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            continue
        timeline = oco._timeline(
            day_bars,
            evidence_fingerprint=evidence,
        )
        if timeline is None:
            continue
        selected, selection_status = oco._select_oco(
            day_bars,
            timeline,
            policy,
        )
        status_counts[f"oco-{selection_status}"] += 1
        if selected is None:
            continue

        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        ) = context_by_day[local_day]
        observation_at = selected.decision_at
        session_prefix = tuple(
            bar
            for bar in session
            if cast(datetime, getattr(bar, "closed_at")) <= observation_at
        )
        state = specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            session_prefix,
            timeline.source,
            selected,
            observation_at,
        )
        context = management._context_state(state)
        context_counts[context] += 1

        for variant in VARIANTS:
            required = _required_confirmations(variant, context)
            outcome = _simulate_single_structural_trail(
                day_bars,
                selected,
                required_confirmations=required,
            )
            status_counts[f"{variant}:{outcome['status']}"] += 1
            if outcome.get("status") != "terminal":
                continue
            enriched = dict(outcome)
            enriched["management_context"] = context
            trades[variant].append(enriched)

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "candidate_contract_fingerprint": specialist.contract_fingerprint(),
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
            "first_opened_at": getattr(series[0], "opened_at")
            .astimezone(UTC)
            .isoformat(),
            "last_closed_at": getattr(series[-1], "closed_at")
            .astimezone(UTC)
            .isoformat(),
        },
        "oco_selected_setup_count": sum(context_counts.values()),
        "management_context_counts": dict(sorted(context_counts.items())),
        "variant_metrics": {
            variant: _bundle(values)
            for variant, values in trades.items()
        },
        "status_counts": dict(sorted(status_counts.items())),
        "governance": {
            "entry_filtering": False,
            "initial_stop_widening": False,
            "single_structural_trail_move_max": True,
            "trail_effective_next_bar": True,
            "context_classifier_uses_terminal_pnl": False,
            "consumed_evidence_only": True,
            "policy_promoted": False,
            "opens_new_holdout": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
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
                "oco_selected_setup_count": payload[
                    "oco_selected_setup_count"
                ],
                "management_context_counts": payload[
                    "management_context_counts"
                ],
                "variant_metrics": payload["variant_metrics"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
