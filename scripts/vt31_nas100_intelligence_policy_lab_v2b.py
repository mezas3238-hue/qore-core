"""Finite causal policy lab for VT31_NAS100 Super Intelligence V2B.

The entry-state policy is fixed before economic execution:
- require at least one causal support:
  * last observed CIBO event is reference-liquidity-sweep, OR
  * both peer indices have already breached the same expected side;
- abstain when the source reclaim is in the predeclared stale 8-14m state;
- abstain when both peers have already breached the opposite side.

The lab then compares only predeclared stop and destination/management families:
S0 source swing; S1 adverse extreme observed from raid through decision.
P0 structural boundary + source 3R BE;
P1/P125/P15 realize 50% at local R, then move runner to BE next bar and
retain the opposite 09:00 boundary as structural destination.

Research only.  No holdout is opened and no family is promoted automatically.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_r1_candidate as baseline

from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.intelligence_policy_lab.v2b"
SNAPSHOT_SCHEMA = "qore.vt31.nas100.market_understanding_snapshot.v1"
MARKET = "NAS100"
FRICTION = Decimal("0.05")
PARTIAL_FRACTIONS = {
    "P0_STRUCTURAL_BOUNDARY": None,
    "P1_PARTIAL_1R_RUNNER": Decimal("1.0"),
    "P125_PARTIAL_1_25R_RUNNER": Decimal("1.25"),
    "P15_PARTIAL_1_5R_RUNNER": Decimal("1.5"),
}
STOP_FAMILIES = ("S0_SOURCE_SWING", "S1_DECISION_ADVERSE_EXTREME")
LIFECYCLE_MINUTE = 16 * 60


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _policy_id(stop_family: str, target_family: str) -> str:
    return f"VT31_NAS100_V2B__{stop_family}__{target_family}"


def _policy_fingerprint(stop_family: str, target_family: str) -> str:
    raw = json.dumps(
        {
            "entry": (
                "support_count>=1;not-stale-8-14;"
                "not-both-peers-opposite"
            ),
            "stop_family": stop_family,
            "target_family": target_family,
            "partial_fraction": "0.50",
            "runner_stop": "breakeven-next-bar-after-partial",
            "runner_destination": "opposite-frozen-09-boundary",
            "friction_r": format(FRICTION, "f"),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _snapshot_index(payload: dict[str, object]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in cast(list[dict[str, Any]], payload["snapshots"]):
        key = (str(row["local_date"]), str(row["decision_at"]))
        if key in result:
            raise ValueError(f"duplicate snapshot {key}")
        result[key] = row
    return result


def _entry_decision(snapshot: dict[str, Any]) -> tuple[str, list[str]]:
    primitives = cast(dict[str, object], snapshot["reasoning_primitives"])
    reasons: list[str] = []
    if bool(primitives["sequence_stale_8_14"]):
        reasons.append("sequence-stale-8-14")
    if bool(primitives["both_peers_opposite_breach_conflict"]):
        reasons.append("both-peers-opposite-breach-conflict")
    support_count = int(primitives["support_count"])
    if support_count < 1:
        reasons.append("no-causal-support")
    if reasons:
        return "ABSTAIN", reasons
    support_reasons = []
    if bool(primitives["reference_liquidity_support"]):
        support_reasons.append("reference-liquidity-sweep-support")
    if bool(primitives["both_peers_same_breach_support"]):
        support_reasons.append("both-peers-same-breach-support")
    return "EXECUTE", support_reasons


def _decision_stop(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
    stop_family: str,
) -> Decimal:
    if stop_family == "S0_SOURCE_SWING":
        return setup.stop_price
    if stop_family != "S1_DECISION_ADVERSE_EXTREME":
        raise ValueError(stop_family)
    relevant = [
        bar
        for bar in day_bars
        if setup.source_setup.structure.raid_at
        <= getattr(bar, "closed_at")
        <= setup.decision_at
    ]
    if not relevant:
        return setup.stop_price
    if setup.side.value == "long":
        return min(_d(getattr(bar, "low")) for bar in relevant)
    return max(_d(getattr(bar, "high")) for bar in relevant)


def _clone_with_stop(
    setup: Vt31R22ExecutableSetup,
    stop: Decimal,
    stop_family: str,
    target_family: str,
) -> Vt31R22ExecutableSetup | None:
    entry = setup.entry_price
    target = setup.target_price
    if setup.side.value == "long":
        if not stop < entry < target:
            return None
        three_r = entry + (entry - stop) * Decimal(3)
    else:
        if not target < entry < stop:
            return None
        three_r = entry - (stop - entry) * Decimal(3)
    return Vt31R22ExecutableSetup(
        side=setup.side,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        three_r_price=three_r,
        selected_family=setup.selected_family,
        candidate_families=setup.candidate_families,
        decision_at=setup.decision_at,
        pending_expires_at=setup.pending_expires_at,
        source_setup=setup.source_setup,
        execution_policy_fingerprint=_policy_fingerprint(
            stop_family,
            target_family,
        ),
    )


def _fill_index(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
) -> int | None:
    for index, bar in enumerate(day_bars):
        if getattr(bar, "opened_at") < setup.decision_at:
            continue
        if baseline._local_minute(bar) >= 11 * 60:
            break
        if baseline._touch(bar, setup.entry_price):
            return index
    return None


def _target_price(
    side: str,
    entry: Decimal,
    risk: Decimal,
    local_r: Decimal,
) -> Decimal:
    return (
        entry + risk * local_r
        if side == "long"
        else entry - risk * local_r
    )


def _simulate_partial_runner(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
    local_r: Decimal,
) -> dict[str, object]:
    side = setup.side.value
    entry = setup.entry_price
    stop = setup.stop_price
    boundary = setup.target_price
    risk = setup.initial_risk
    if risk <= 0:
        return {"status": "censored-invalid-risk"}

    boundary_r = abs(boundary - entry) / risk
    if boundary_r <= local_r:
        outcome = baseline._simulate(day_bars, setup)
        if outcome.get("status") == "terminal":
            outcome["management_family"] = "boundary-closer-than-local-partial"
            outcome["partial_target_r"] = format(local_r, "f")
            outcome["boundary_r"] = format(boundary_r, "f")
        return outcome

    fill_index = _fill_index(day_bars, setup)
    if fill_index is None:
        return {"status": "no-fill"}

    partial = _target_price(side, entry, risk, local_r)
    first = day_bars[fill_index]
    first_low = _d(getattr(first, "low"))
    first_high = _d(getattr(first, "high"))
    stop_hit = first_low <= stop if side == "long" else first_high >= stop
    partial_hit = (
        first_high >= partial if side == "long" else first_low <= partial
    )
    boundary_hit = (
        first_high >= boundary if side == "long" else first_low <= boundary
    )
    if stop_hit and (partial_hit or boundary_hit):
        return {"status": "censored-fill-bar-path"}
    if stop_hit:
        return {"status": "censored-fill-bar-path"}
    if boundary_hit:
        return {"status": "censored-fill-bar-path"}
    if partial_hit:
        return {"status": "censored-fill-bar-path"}

    filled_at = getattr(first, "closed_at")
    previous = first
    partial_done = False
    runner_be_active = False
    max_favorable = Decimal(0)
    max_adverse = Decimal(0)
    mfe_at = filled_at
    exit_at = None
    exit_reason: str | None = None
    terminal: Decimal | None = None

    for index in range(fill_index + 1, len(day_bars)):
        bar = day_bars[index]
        if baseline._local_minute(bar) >= LIFECYCLE_MINUTE:
            break
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return {"status": "censored-gap-after-fill"}
        previous = bar

        favorable, adverse = baseline._favorable_adverse(
            bar,
            side,
            entry,
            risk,
        )
        if favorable > max_favorable:
            max_favorable = favorable
            mfe_at = getattr(bar, "closed_at")
        max_adverse = max(max_adverse, adverse)

        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        hit_initial_stop = low <= stop if side == "long" else high >= stop
        hit_partial = high >= partial if side == "long" else low <= partial
        hit_boundary = high >= boundary if side == "long" else low <= boundary
        hit_runner_be = (
            (low <= entry if side == "long" else high >= entry)
            if runner_be_active
            else False
        )

        if not partial_done:
            if hit_initial_stop and (hit_partial or hit_boundary):
                return {"status": "censored-same-bar-stop-target"}
            if hit_initial_stop:
                terminal = Decimal("-1")
                exit_reason = "initial-stop"
                exit_at = getattr(bar, "closed_at")
                break
            if hit_boundary:
                terminal = (
                    Decimal("0.5") * local_r
                    + Decimal("0.5") * boundary_r
                )
                exit_reason = "partial-plus-structural-boundary"
                exit_at = getattr(bar, "closed_at")
                partial_done = True
                break
            if hit_partial:
                partial_done = True
                runner_be_active = False
                continue
        else:
            if hit_runner_be and hit_boundary:
                return {"status": "censored-same-bar-be-boundary"}
            if hit_boundary:
                terminal = (
                    Decimal("0.5") * local_r
                    + Decimal("0.5") * boundary_r
                )
                exit_reason = "runner-structural-boundary"
                exit_at = getattr(bar, "closed_at")
                break
            if hit_runner_be:
                terminal = Decimal("0.5") * local_r
                exit_reason = "partial-plus-runner-breakeven"
                exit_at = getattr(bar, "closed_at")
                break

        if partial_done and not runner_be_active:
            runner_be_active = True

    if terminal is None:
        eligible = [
            bar
            for bar in day_bars[fill_index:]
            if baseline._local_minute(bar) < LIFECYCLE_MINUTE
        ]
        if not eligible:
            return {"status": "censored-no-lifecycle-close"}
        final = eligible[-1]
        close = _d(getattr(final, "close"))
        close_r = (
            (close - entry) / risk
            if side == "long"
            else (entry - close) / risk
        )
        terminal = (
            Decimal("0.5") * local_r + Decimal("0.5") * close_r
            if partial_done
            else close_r
        )
        exit_reason = (
            "partial-plus-16:00-runner"
            if partial_done
            else "16:00-lifecycle-before-partial"
        )
        exit_at = getattr(final, "closed_at")

    return {
        "status": "terminal",
        "local_date": baseline._day(setup.decision_at).isoformat(),
        "side": side,
        "signal_at": setup.decision_at.astimezone(UTC).isoformat(),
        "filled_at": filled_at.astimezone(UTC).isoformat(),
        "exit_at": exit_at.astimezone(UTC).isoformat(),
        "entry_family": setup.selected_family.value,
        "entry": format(entry, "f"),
        "initial_stop": format(stop, "f"),
        "structural_target": format(boundary, "f"),
        "boundary_r": format(boundary_r, "f"),
        "partial_target_r": format(local_r, "f"),
        "partial_fraction": "0.5",
        "partial_done": partial_done,
        "runner_be_active": runner_be_active,
        "exit_reason": exit_reason,
        "r_multiple": format(terminal, "f"),
        "mfe_r": format(max_favorable, "f"),
        "mae_r": format(max_adverse, "f"),
        "mfe_at": mfe_at.astimezone(UTC).isoformat(),
        "minutes_fill_to_mfe": str(
            int((mfe_at - filled_at).total_seconds() // 60)
        ),
        "minutes_fill_to_exit": str(
            int((exit_at - filled_at).total_seconds() // 60)
        ),
    }


def _metrics(trades: list[dict[str, object]]) -> dict[str, object]:
    return baseline._metrics(trades, friction=FRICTION)


def _blocks(
    trades: list[dict[str, object]],
    halfyear: bool,
) -> dict[str, dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for trade in trades:
        local_date = str(trade["local_date"])
        month = int(local_date[5:7])
        if halfyear:
            key = f"{local_date[:4]}-H{1 if month <= 6 else 2}"
        else:
            key = f"{local_date[:4]}-Q{(month - 1) // 3 + 1}"
        groups[key].append(trade)
    return {
        key: _metrics(group)
        for key, group in sorted(groups.items())
    }


def _variant_gates(
    stress: dict[str, object],
    halfyears: dict[str, dict[str, object]],
) -> dict[str, bool]:
    eligible = [
        block
        for block in halfyears.values()
        if int(block["sample"]) >= 10
    ]
    positive = sum(
        Decimal(str(block["mean_r"])) > 0
        for block in eligible
    )
    return {
        "sample_at_least_90": int(stress["sample"]) >= 90,
        "mean_positive": Decimal(str(stress["mean_r"])) > 0,
        "profit_factor_at_least_1_15": (
            stress["profit_factor"] is not None
            and Decimal(str(stress["profit_factor"])) >= Decimal("1.15")
        ),
        "max_drawdown_at_most_20r": (
            Decimal(str(stress["max_drawdown_r"])) <= Decimal(20)
        ),
        "losing_streak_at_most_15": int(
            stress["max_losing_streak"]
        ) <= 15,
        "halfyear_positive_share_at_least_70pct": (
            len(eligible) >= 3
            and Decimal(positive) / Decimal(len(eligible))
            >= Decimal("0.70")
        ),
    }


def replay(
    snapshot_path: Path,
    evidence_path: Path,
) -> dict[str, object]:
    snapshot_payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot_payload.get("schema") != SNAPSHOT_SCHEMA:
        raise ValueError("unexpected snapshot schema")
    if snapshot_payload.get("research_only") is not True:
        raise ValueError("snapshot governance mismatch")
    snapshots = _snapshot_index(snapshot_payload)

    series, account, evidence, checked, evidence_sha, provider = (
        baseline.load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("V2B requires NAS100 evidence")

    by_day: dict[object, list[object]] = defaultdict(list)
    for bar in series:
        by_day[baseline._day(getattr(bar, "opened_at"))].append(bar)

    policy = Vt31R22ExecutionPolicy()
    variants: dict[str, list[dict[str, object]]] = {
        _policy_id(stop, target): []
        for stop in STOP_FAMILIES
        for target in PARTIAL_FRACTIONS
    }
    traces: list[dict[str, object]] = []
    decision_counts: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = tuple(by_day[local_day])
        reference = tuple(
            bar
            for bar in day_bars
            if (9, 0, 0)
            <= baseline._wall(getattr(bar, "opened_at"))
            < (10, 0, 0)
        )
        session = tuple(
            bar
            for bar in day_bars
            if (10, 0, 0)
            <= baseline._wall(getattr(bar, "opened_at"))
            < (11, 0, 0)
        )
        if len(reference) != 60 or len(session) != 60:
            decision_counts["incomplete-day"] += 1
            continue

        prefix = list(reference)
        selected: Vt31R22ExecutableSetup | None = None
        for bar in session:
            prefix.append(bar)
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=getattr(bar, "closed_at"),
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                continue
            executable, _ = make_executable_setup(
                evaluation.setup,
                policy,
            )
            if executable is None:
                decision_counts["source-not-executable"] += 1
                break
            selected = executable
            break

        if selected is None:
            decision_counts["no-source-setup"] += 1
            continue

        key = (
            baseline._day(selected.decision_at).isoformat(),
            selected.decision_at.astimezone(UTC).isoformat(),
        )
        state = snapshots.get(key)
        if state is None:
            decision_counts["missing-understanding-snapshot"] += 1
            continue
        decision, reasons = _entry_decision(state)
        decision_counts[decision] += 1
        traces.append(
            {
                "local_date": key[0],
                "decision_at": key[1],
                "action": decision,
                "reasons": reasons,
                "reasoning_primitives": state["reasoning_primitives"],
                "market_context": state["market_context"],
                "outcome_fields_used_for_decision": False,
            }
        )
        if decision != "EXECUTE":
            continue

        for stop_family in STOP_FAMILIES:
            stop = _decision_stop(day_bars, selected, stop_family)
            for target_family, local_r in PARTIAL_FRACTIONS.items():
                candidate = _clone_with_stop(
                    selected,
                    stop,
                    stop_family,
                    target_family,
                )
                if candidate is None:
                    continue
                if local_r is None:
                    outcome = baseline._simulate(day_bars, candidate)
                else:
                    outcome = _simulate_partial_runner(
                        day_bars,
                        candidate,
                        local_r,
                    )
                if outcome.get("status") != "terminal":
                    continue
                outcome["stop_family"] = stop_family
                outcome["target_family"] = target_family
                variants[
                    _policy_id(stop_family, target_family)
                ].append(outcome)

    reports: dict[str, object] = {}
    for stop_family in STOP_FAMILIES:
        for target_family in PARTIAL_FRACTIONS:
            policy_id = _policy_id(stop_family, target_family)
            trades = sorted(
                variants[policy_id],
                key=lambda row: str(row["signal_at"]),
            )
            stress = _metrics(trades)
            halfyears = _blocks(trades, halfyear=True)
            quarters = _blocks(trades, halfyear=False)
            reports[policy_id] = {
                "policy_id": policy_id,
                "policy_fingerprint": _policy_fingerprint(
                    stop_family,
                    target_family,
                ),
                "stop_family": stop_family,
                "target_family": target_family,
                "stress_0_05r": stress,
                "halfyear_stress": halfyears,
                "quarter_stress": quarters,
                "gates": _variant_gates(stress, halfyears),
                "passes_all_development_gates": all(
                    _variant_gates(stress, halfyears).values()
                ),
                "trade_count": len(trades),
                "trades": trades,
            }

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "partition": snapshot_payload["partition"],
        "research_only": True,
        "selection_prohibited": True,
        "candidate_frozen": False,
        "opens_new_holdout": False,
        "live_authorized": False,
        "production_authorized": False,
        "fixed_entry_state_policy": {
            "require_support_count_at_least": 1,
            "support": [
                "reference-liquidity-sweep-is-last-observed-cibo-event",
                "both-peers-same-breach-observed",
            ],
            "abstain": [
                "reclaim-latency-bin-8-14-stale",
                "both-peers-opposite-breach-observed",
                "no-causal-support",
            ],
            "future_lookup": False,
        },
        "finite_family_contract": {
            "stop_families": list(STOP_FAMILIES),
            "target_management_families": {
                key: (
                    None if value is None else format(value, "f")
                )
                for key, value in PARTIAL_FRACTIONS.items()
            },
            "partial_fraction": "0.5",
            "runner_destination": "opposite-frozen-09-boundary",
            "runner_stop_after_partial": "breakeven-next-bar",
            "automatic_best-aggregate-selection": False,
        },
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "decision_counts": dict(sorted(decision_counts.items())),
        "variant_reports": reports,
        "decision_trace": traces,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = replay(args.snapshot, args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "decision_counts": payload["decision_counts"],
                "variants": {
                    key: {
                        "stress": cast(dict[str, object], value)[
                            "stress_0_05r"
                        ],
                        "passes": cast(dict[str, object], value)[
                            "passes_all_development_gates"
                        ],
                    }
                    for key, value in cast(
                        dict[str, dict[str, object]],
                        payload["variant_reports"],
                    ).items()
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
