"""VT31 NAS100 cognition-survivor + DGR interaction frontier V1.

Consumed-evidence research only. This experiment implements the predeclared
Architect-B interaction plan on the exact equal-R OCO admitted population.

Variants:
- BASELINE
- SURVIVOR_PS1_ONLY
- DGR025_SINGLE_ONLY
- SURVIVOR_PS1_PLUS_DGR025_FALLBACK

The combined variant grants mutually exclusive management authority per trade:
if the pre-entry LBB_PATH_SHALLOW survivor is eligible, use PS1; otherwise the
trade may use the single-move DGR025 journey rescue. No trade may receive both.

Admission, entry, initial stop, structural target, baseline 3R breakeven,
lifecycle and friction remain unchanged. No sizing, leverage, compounding,
capital weighting, absolute volume, partial exit, terminal-PnL oracle or future
journey label is used.
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

import vt31_nas100_cognitive_structural_protection_frontier_v1 as cognitive
import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_high_density_structural_protection_v1 as protection
import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    FullCognitivePositionState,
    assess_full_cognitive_position,
)

SCHEMA = "qore.vt31.nas100.survivor_dgr_interaction.v1"
MARKET = "NAS100"
DGR_MAX_CURRENT_CLOSE_R = Decimal("0.25")
DGR_MIN_MFE_R = Decimal("1.50")
DGR_MIN_CLOSE_GIVEBACK_R = Decimal("1.00")
DGR_MAX_PATH_EFFICIENCY = Decimal("0.10")
SURVIVOR_NAME = "LBB_PATH_SHALLOW_PS1"
VARIANTS = (
    "BASELINE",
    "SURVIVOR_PS1_ONLY",
    "DGR025_SINGLE_ONLY",
    "SURVIVOR_PS1_PLUS_DGR025_FALLBACK",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _is_survivor_eligible(
    *,
    state: dict[str, object],
    cognition: FullCognitivePositionState,
) -> bool:
    return bool(
        state["last_structure_event_family"] == "breaker"
        and cognitive._is_path_not_compressed(cognition)
        and cognition.destination_state == "SHALLOW"
    )


def _path_efficiency(
    bars: tuple[object, ...],
    *,
    side: str,
) -> Decimal | None:
    if len(bars) < 2:
        return None
    closes = [_d(getattr(bar, "close")) for bar in bars]
    if side == "long":
        net = closes[-1] - closes[0]
    elif side == "short":
        net = closes[0] - closes[-1]
    else:
        raise ValueError(side)
    gross = sum(
        (
            abs(right - left)
            for left, right in zip(closes, closes[1:], strict=False)
        ),
        Decimal(0),
    )
    return None if gross <= 0 else net / gross


def _journey_features(
    path: tuple[object, ...],
    index: int,
    *,
    entry: Decimal,
    risk: Decimal,
    side: str,
) -> dict[str, Decimal | None]:
    through = path[: index + 1]
    recent = through[-5:]
    close_rs = []
    favorable_rs = []
    for bar in through:
        close = _d(getattr(bar, "close"))
        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        if side == "long":
            close_rs.append((close - entry) / risk)
            favorable_rs.append((high - entry) / risk)
        elif side == "short":
            close_rs.append((entry - close) / risk)
            favorable_rs.append((entry - low) / risk)
        else:
            raise ValueError(side)
    current_close_r = close_rs[-1]
    peak_close_r = max(close_rs)
    return {
        "mfe_r": max(favorable_rs),
        "current_close_r": current_close_r,
        "close_giveback_r": max(
            Decimal(0),
            peak_close_r - current_close_r,
        ),
        "path_efficiency": _path_efficiency(recent, side=side),
    }


def _dgr_qualifies(state: dict[str, Decimal | None]) -> bool:
    efficiency = state["path_efficiency"]
    return bool(
        state["mfe_r"] is not None
        and state["mfe_r"] >= DGR_MIN_MFE_R
        and state["close_giveback_r"] is not None
        and state["close_giveback_r"] >= DGR_MIN_CLOSE_GIVEBACK_R
        and state["current_close_r"] is not None
        and state["current_close_r"] <= DGR_MAX_CURRENT_CLOSE_R
        and efficiency is not None
        and efficiency <= DGR_MAX_PATH_EFFICIENCY
    )


def _simulate_dgr_with_baseline_semantics(
    day_bars: tuple[object, ...],
    setup: object,
) -> dict[str, object]:
    """Add one DGR move while preserving the current VT31 baseline lifecycle."""

    side = str(getattr(getattr(setup, "side"), "value"))
    entry = _d(getattr(setup, "entry_price"))
    initial_stop = _d(getattr(setup, "stop_price"))
    target = _d(getattr(setup, "target_price"))
    three_r = _d(getattr(setup, "three_r_price"))
    risk = _d(getattr(setup, "initial_risk"))
    if risk <= 0:
        return {"status": "censored-invalid-risk"}

    fill_index = v2b._fill_index(day_bars, setup)
    if fill_index is None:
        return {"status": "no-fill"}

    first = day_bars[fill_index]
    low = _d(getattr(first, "low"))
    high = _d(getattr(first, "high"))
    stop_hit = low <= initial_stop if side == "long" else high >= initial_stop
    target_hit = high >= target if side == "long" else low <= target
    if stop_hit or target_hit:
        return {"status": "censored-fill-bar-path"}

    current_stop = initial_stop
    be_armed = False
    rescue_committed = False
    pending_candidate: Decimal | None = None
    dgr_armed = False
    dgr_trigger: dict[str, object] | None = None
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

        if pending_candidate is not None and not rescue_committed:
            if protection._improves_stop(
                side,
                current_stop,
                pending_candidate,
                target,
            ):
                current_stop = pending_candidate
                rescue_committed = True
                dgr_armed = True
            pending_candidate = None

        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        hit_stop = low <= current_stop if side == "long" else high >= current_stop
        hit_target = high >= target if side == "long" else low <= target

        if hit_stop and hit_target:
            return {"status": "censored-same-bar-stop-target"}
        if hit_stop:
            terminal = protection._terminal_r(side, entry, current_stop, risk)
            if current_stop == initial_stop:
                exit_reason = "initial-stop"
            elif current_stop == entry:
                exit_reason = "breakeven-stop"
            else:
                exit_reason = "deep-giveback-rescue-stop"
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break
        if hit_target:
            terminal = abs(target - entry) / risk
            exit_reason = "structural-target"
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break

        # Preserve baseline 3R breakeven exactly. It is observed on the closed
        # bar and becomes the stop for subsequent bars.
        if not be_armed:
            touched_three_r = high >= three_r if side == "long" else low <= three_r
            if touched_three_r:
                be_armed = True
                if protection._improves_stop(side, current_stop, entry, target):
                    current_stop = entry

        if not rescue_committed and pending_candidate is None:
            candidate = protection._protective_swing_level(
                post_fill,
                local_index,
                side,
            )
            if (
                candidate is not None
                and protection._improves_stop(
                    side,
                    current_stop,
                    candidate,
                    target,
                )
            ):
                journey = _journey_features(
                    post_fill,
                    local_index,
                    entry=entry,
                    risk=risk,
                    side=side,
                )
                if _dgr_qualifies(journey):
                    pending_candidate = candidate
                    dgr_trigger = {
                        "trigger_closed_at": cast(
                            datetime,
                            getattr(bar, "closed_at"),
                        ).astimezone(UTC).isoformat(),
                        "effective_next_bar": True,
                        "mfe_r": format(cast(Decimal, journey["mfe_r"]), "f"),
                        "current_close_r": format(
                            cast(Decimal, journey["current_close_r"]),
                            "f",
                        ),
                        "close_giveback_r": format(
                            cast(Decimal, journey["close_giveback_r"]),
                            "f",
                        ),
                        "path_efficiency": format(
                            cast(Decimal, journey["path_efficiency"]),
                            "f",
                        ),
                        "protective_swing_level": format(candidate, "f"),
                    }

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
        "local_date": _day(getattr(setup, "decision_at")).isoformat(),
        "side": side,
        "signal_at": cast(datetime, getattr(setup, "decision_at"))
        .astimezone(UTC)
        .isoformat(),
        "filled_at": filled_at.astimezone(UTC).isoformat(),
        "exit_at": cast(datetime, exit_at).astimezone(UTC).isoformat(),
        "entry_family": str(getattr(getattr(setup, "selected_family"), "value")),
        "exit_reason": exit_reason,
        "r_multiple": format(terminal, "f"),
        "breakeven_armed": be_armed,
        "dgr_armed": dgr_armed,
        "dgr_trigger": dgr_trigger,
    }


def _halfyear(local_date: str) -> str:
    year, month = (int(value) for value in local_date.split("-")[:2])
    return f"{year}H{1 if month <= 6 else 2}"


def _group_metrics(
    rows: list[dict[str, object]],
    *,
    key: str,
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        value = (
            _halfyear(str(row["local_date"]))
            if key == "halfyear"
            else str(row[key])
        )
        grouped[value].append(row)
    return {
        name: cognitive._normalized_metrics(items)
        for name, items in sorted(grouped.items())
    }


def replay(evidence_path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("survivor+DGR interaction requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = oco.Vt31R22ExecutionPolicy()
    trades: dict[str, list[dict[str, object]]] = {
        variant: [] for variant in VARIANTS
    }
    status: Counter[str] = Counter()
    mechanism_counts: dict[str, Counter[str]] = {
        variant: Counter() for variant in VARIANTS
    }

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        timeline = oco._timeline(
            day_bars,
            evidence_fingerprint=evidence,
        )
        if timeline is None:
            status["no-source-timeline"] += 1
            continue
        selected, selection_status = oco._select_oco(
            day_bars,
            timeline,
            policy,
        )
        status[f"oco-{selection_status}"] += 1
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
        situation = cognition_lab._reconstruct_situation(
            state=state,
            selected=selected,
            source=timeline.source,
            observation_at=observation_at,
        )
        reasoning = cognition_lab._reconstruct_reasoning(state)
        cognition = assess_full_cognitive_position(
            situation=situation,
            reasoning=reasoning,
            entry_tier="CORE",
            dol1_acceptance_observed=None,
        )
        survivor_eligible = _is_survivor_eligible(
            state=state,
            cognition=cognition,
        )
        trade_id = cognitive._trade_id(
            local_day=local_day,
            selected=selected,
        )

        baseline = specialist.baseline._simulate(day_bars, selected)
        survivor = protection._simulate_single_structural_trail(
            day_bars,
            selected,
            required_confirmations=1 if survivor_eligible else None,
        )
        dgr = _simulate_dgr_with_baseline_semantics(day_bars, selected)

        outcomes = {
            "BASELINE": (baseline, "BASELINE"),
            "SURVIVOR_PS1_ONLY": (
                survivor,
                SURVIVOR_NAME if survivor_eligible else "BASELINE",
            ),
            "DGR025_SINGLE_ONLY": (
                dgr,
                "DGR025" if bool(dgr.get("dgr_armed")) else "BASELINE",
            ),
            "SURVIVOR_PS1_PLUS_DGR025_FALLBACK": (
                (
                    survivor
                    if survivor_eligible
                    else dgr
                ),
                (
                    SURVIVOR_NAME
                    if survivor_eligible
                    else (
                        "DGR025"
                        if bool(dgr.get("dgr_armed"))
                        else "BASELINE"
                    )
                ),
            ),
        }

        for variant, (outcome, mechanism) in outcomes.items():
            status[f"{variant}:{outcome['status']}"] += 1
            if outcome["status"] != "terminal":
                continue
            mechanism_counts[variant][mechanism] += 1
            row = dict(outcome)
            row["trade_id"] = trade_id
            row["local_date"] = local_day.isoformat()
            row["side"] = selected.side.value
            row["entry_family"] = selected.selected_family.value
            row["management_context"] = cognition.management_context.value
            row["destination_state"] = cognition.destination_state
            row["support_score"] = cognition.support_score
            row["caution_score"] = cognition.caution_score
            row["survivor_eligible"] = survivor_eligible
            row["dgr_eligible_and_armed"] = bool(dgr.get("dgr_armed"))
            row["protection_mechanism"] = mechanism
            row["baseline_r"] = baseline.get("r_multiple")
            row["managed_r"] = outcome.get("r_multiple")
            row["delta_r"] = (
                format(
                    _d(outcome["r_multiple"]) - _d(baseline["r_multiple"]),
                    "f",
                )
                if baseline.get("status") == "terminal"
                and outcome.get("status") == "terminal"
                else None
            )
            row["baseline_winner_changed"] = bool(
                baseline.get("status") == "terminal"
                and _d(baseline["r_multiple"]) - specialist.FRICTION > 0
                and _d(outcome["r_multiple"]) != _d(baseline["r_multiple"])
            )
            trades[variant].append(row)

    baseline_rows = trades["BASELINE"]
    reports: dict[str, object] = {}
    for variant, rows in trades.items():
        reports[variant] = {
            "terminal_count": len(rows),
            "normalized_metrics": cognitive._normalized_metrics(rows),
            "monte_carlo": specialist._monte_carlo(rows),
            "winner_preservation_vs_baseline": (
                None
                if variant == "BASELINE"
                else cognitive._winner_preservation(
                    baseline_rows,
                    rows,
                )
            ),
            "side_metrics": _group_metrics(rows, key="side"),
            "halfyear_metrics": _group_metrics(rows, key="halfyear"),
            "mechanism_counts": dict(
                sorted(mechanism_counts[variant].items())
            ),
            "changed_trade_count": sum(
                row.get("delta_r") not in {None, "0", "0.0"}
                for row in rows
            ),
            "exit_reasons": dict(
                sorted(
                    Counter(
                        str(row["exit_reason"]) for row in rows
                    ).items()
                )
            ),
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "survivor_contract": {
            "name": SURVIVOR_NAME,
            "last_structure": "breaker",
            "current_path_not_compressed": True,
            "destination_state": "SHALLOW",
            "protective_swing_confirmations": 1,
            "maximum_moves_per_trade": 1,
        },
        "dgr_contract": {
            "minimum_mfe_r": format(DGR_MIN_MFE_R, "f"),
            "minimum_close_giveback_r": format(
                DGR_MIN_CLOSE_GIVEBACK_R,
                "f",
            ),
            "maximum_current_close_r": format(
                DGR_MAX_CURRENT_CLOSE_R,
                "f",
            ),
            "maximum_recent_path_efficiency": format(
                DGR_MAX_PATH_EFFICIENCY,
                "f",
            ),
            "protective_swing_confirmations": 1,
            "maximum_moves_per_trade": 1,
        },
        "variant_reports": reports,
        "trade_rows": trades,
        "status_counts": dict(sorted(status.items())),
        "governance": {
            "consumed_evidence_only": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "structural_target_changed": False,
            "baseline_3r_breakeven_preserved": True,
            "lifecycle_changed": False,
            "interaction_authority_mutually_exclusive": True,
            "maximum_architect_b_protection_moves_per_trade": 1,
            "normalized_equal_r_economics": True,
            "capital_weighted_net_r_used": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "absolute_volume_used": False,
            "provider_volume_rule_used": False,
            "partial_exit_required": False,
            "terminal_pnl_runtime_input": False,
            "future_journey_runtime_input": False,
            "fold_identity_runtime_input": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
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
                "variant_reports": payload["variant_reports"],
                "governance": payload["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
