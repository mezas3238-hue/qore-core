"""VT31 NAS100 causal hypothesis-lifecycle and replacement frontier.

This laboratory implements a state machine above the frozen TTrades Silver
Bullet source.  A confirmed source is a hypothesis, not an automatic trade.

The hypothesis may:
- mature after additional CLOSED M1 evidence;
- invalidate before capital is authorized;
- exhaust by already reaching its structural target;
- be rejected for weak post-confirmation delivery;
- be replaced only by a genuinely new raid + confirmation after the cursor.

Two QORE execution translations are falsified after causal maturation:
1. keep the original pending translation;
2. execute the matured hypothesis at the closed M1 market price.

All maturation inputs exist before authorization.  Future outcome labels,
terminal PnL, fold identity, H4/H1 trend and target trade counts are forbidden
as runtime inputs.  Silver Bullet source, structural stop, opposite-reference
target and 3R->BE semantics remain frozen.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_causal_hybrid_rearm_v1 as capital
import vt31_nas100_causal_hybrid_replay_v1 as activation
import vt31_nas100_r1_candidate as baseline
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders import vt31_silver_bullet_r2_2 as silver
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.hypothesis_lifecycle_frontier.v1"
IDENTITY = "VT31_NAS100_HYPOTHESIS_LIFECYCLE_FRONTIER_V1"
MARKET = "NAS100"
FRICTION = Decimal("0.05")
LIFECYCLE_MINUTE = 16 * 60
MAX_SOURCE_CYCLES_PER_DAY = 6
MAX_EXECUTIONS_PER_DAY = 2
EXPECTED_SOURCE_SHA256 = (
    "bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf"
)
EXPECTED_METHODOLOGY_ID = "ttrades-am-silver-bullet-nq-r2.2"

VARIANTS: dict[str, dict[str, object]] = {
    "IMMEDIATE_PENDING_FLAT060": {
        "maturity": "IMMEDIATE",
        "translation": "PENDING",
        "risk": "FLAT060",
    },
    "MATURE2_PENDING_FLAT060": {
        "maturity": "GENERIC2",
        "translation": "PENDING",
        "risk": "FLAT060",
    },
    "MATURE2_MARKET_FLAT060": {
        "maturity": "GENERIC2",
        "translation": "MARKET",
        "risk": "FLAT060",
    },
    "MATURE3_MARKET_FLAT060": {
        "maturity": "GENERIC3",
        "translation": "MARKET",
        "risk": "FLAT060",
    },
    "FAMILY_MATURE_MARKET_FLAT060": {
        "maturity": "FAMILY",
        "translation": "MARKET",
        "risk": "FLAT060",
    },
    "FAMILY_MATURE_MARKET_FAMILY_RISK": {
        "maturity": "FAMILY",
        "translation": "MARKET",
        "risk": "FAMILY",
    },
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _touches(
    bar: object,
    *,
    side: str,
    stop: Decimal,
    target: Decimal,
) -> tuple[bool, bool]:
    low = _d(getattr(bar, "low"))
    high = _d(getattr(bar, "high"))
    if side == "long":
        return low <= stop, high >= target
    return high >= stop, low <= target


def _maturity_contract(
    family: str,
    mode: str,
) -> tuple[int, Decimal, Decimal, Decimal]:
    if mode == "IMMEDIATE":
        return 0, Decimal(0), Decimal(0), Decimal("999")
    if mode == "GENERIC2":
        return 2, Decimal("0.02"), Decimal("0.04"), Decimal("0.12")
    if mode == "GENERIC3":
        return 3, Decimal("0.04"), Decimal("0.07"), Decimal("0.10")
    if mode != "FAMILY":
        raise ValueError(mode)
    if family == "fair-value-gap":
        return 1, Decimal("0.01"), Decimal("0.03"), Decimal("0.15")
    if family == "breaker":
        return 3, Decimal("0.05"), Decimal("0.08"), Decimal("0.10")
    return 2, Decimal("0.03"), Decimal("0.05"), Decimal("0.12")


def _mature(
    *,
    session: tuple[object, ...],
    source: Vt31R22SourceSetup,
    setup: Vt31R22ExecutableSetup,
    mode: str,
) -> dict[str, object]:
    family = setup.selected_family.value
    bars_required, min_close, min_favorable, max_adverse = (
        _maturity_contract(family, mode)
    )
    confirmation_index = next(
        (
            index
            for index, bar in enumerate(session)
            if cast(datetime, getattr(bar, "closed_at"))
            == source.structure.confirmation_at
        ),
        None,
    )
    if confirmation_index is None:
        raise ValueError("confirmation bar not found")

    confirmation_bar = session[confirmation_index]
    confirmation_close = _d(getattr(confirmation_bar, "close"))
    ref_width = source.reference.high - source.reference.low
    if ref_width <= 0:
        return {"status": "REJECT_INVALID_REFERENCE"}

    if bars_required == 0:
        return {
            "status": "MATURED",
            "authorization_at": source.structure.confirmation_at,
            "authorization_price": confirmation_close,
            "bars_observed": 0,
            "close_progress_ref": "0",
            "favorable_ref": "0",
            "adverse_ref": "0",
        }

    end_index = confirmation_index + bars_required
    if end_index >= len(session):
        return {"status": "REJECT_SESSION_EXHAUSTED"}

    observed = session[confirmation_index + 1 : end_index + 1]
    side = source.side.value
    stop = source.structure.swing_extreme
    target = source.target_price
    favorable = Decimal(0)
    adverse = Decimal(0)

    for bar in observed:
        stop_hit, target_hit = _touches(
            bar,
            side=side,
            stop=stop,
            target=target,
        )
        if stop_hit and target_hit:
            return {"status": "REJECT_AMBIGUOUS_STOP_TARGET"}
        if stop_hit:
            return {"status": "REJECT_INVALIDATED_DURING_MATURATION"}
        if target_hit:
            return {"status": "REJECT_TARGET_EXHAUSTED_BEFORE_ENTRY"}

        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        if side == "long":
            favorable = max(favorable, (high - confirmation_close) / ref_width)
            adverse = max(adverse, (confirmation_close - low) / ref_width)
        else:
            favorable = max(favorable, (confirmation_close - low) / ref_width)
            adverse = max(adverse, (high - confirmation_close) / ref_width)

    final = observed[-1]
    final_close = _d(getattr(final, "close"))
    close_progress = (
        (final_close - confirmation_close) / ref_width
        if side == "long"
        else (confirmation_close - final_close) / ref_width
    )
    close_progress = max(Decimal(0), close_progress)

    if close_progress < min_close:
        return {
            "status": "REJECT_WEAK_CLOSE_PROGRESS",
            "close_progress_ref": format(close_progress, "f"),
            "favorable_ref": format(favorable, "f"),
            "adverse_ref": format(adverse, "f"),
        }
    if favorable < min_favorable:
        return {
            "status": "REJECT_WEAK_FOLLOW_THROUGH",
            "close_progress_ref": format(close_progress, "f"),
            "favorable_ref": format(favorable, "f"),
            "adverse_ref": format(adverse, "f"),
        }
    if adverse > max_adverse:
        return {
            "status": "REJECT_EXCESSIVE_GIVEBACK",
            "close_progress_ref": format(close_progress, "f"),
            "favorable_ref": format(favorable, "f"),
            "adverse_ref": format(adverse, "f"),
        }

    return {
        "status": "MATURED",
        "authorization_at": cast(datetime, getattr(final, "closed_at")),
        "authorization_price": final_close,
        "bars_observed": bars_required,
        "close_progress_ref": format(close_progress, "f"),
        "favorable_ref": format(favorable, "f"),
        "adverse_ref": format(adverse, "f"),
    }


def _market_setup(
    source: Vt31R22SourceSetup,
    current: Vt31R22ExecutableSetup,
    *,
    authorization_at: datetime,
    authorization_price: Decimal,
    variant: str,
) -> Vt31R22ExecutableSetup | None:
    stop = source.structure.swing_extreme
    target = source.target_price
    entry = authorization_price
    if source.side.value == "long":
        if not stop < entry < target:
            return None
        three_r = entry + (entry - stop) * Decimal(3)
    else:
        if not target < entry < stop:
            return None
        three_r = entry - (stop - entry) * Decimal(3)

    return Vt31R22ExecutableSetup(
        side=source.side,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        three_r_price=three_r,
        selected_family=current.selected_family,
        candidate_families=current.candidate_families,
        decision_at=authorization_at,
        pending_expires_at=current.pending_expires_at,
        source_setup=source,
        execution_policy_fingerprint=(
            f"{IDENTITY}:{variant}:market-at-maturity"
        ),
    )


def _simulate_market_at_close(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
) -> dict[str, object]:
    side = setup.side.value
    entry = setup.entry_price
    stop = setup.stop_price
    target = setup.target_price
    three_r = setup.three_r_price
    risk = setup.initial_risk
    if risk <= 0:
        return {"status": "censored-invalid-risk"}

    authorization_index = next(
        (
            index
            for index, bar in enumerate(day_bars)
            if cast(datetime, getattr(bar, "closed_at")) == setup.decision_at
        ),
        None,
    )
    if authorization_index is None:
        return {"status": "censored-authorization-bar-missing"}

    be_armed = False
    current_stop = stop
    max_favorable = Decimal(0)
    max_adverse = Decimal(0)
    filled_at = setup.decision_at
    exit_at: datetime | None = None
    terminal: Decimal | None = None
    exit_reason: str | None = None
    previous = day_bars[authorization_index]

    for bar in day_bars[authorization_index + 1 :]:
        if baseline._local_minute(bar) >= LIFECYCLE_MINUTE:
            break
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return {"status": "censored-gap-after-market-entry"}
        previous = bar

        favorable, adverse = baseline._favorable_adverse(
            bar,
            side,
            entry,
            risk,
        )
        max_favorable = max(max_favorable, favorable)
        max_adverse = max(max_adverse, adverse)

        low = _d(getattr(bar, "low"))
        high = _d(getattr(bar, "high"))
        hit_stop = low <= current_stop if side == "long" else high >= current_stop
        hit_target = high >= target if side == "long" else low <= target
        if hit_stop and hit_target:
            return {"status": "censored-same-bar-stop-target"}
        if hit_stop:
            terminal = baseline._terminal_r(side, entry, current_stop, risk)
            exit_reason = (
                "breakeven-stop" if current_stop == entry else "initial-stop"
            )
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break
        if hit_target:
            terminal = abs(target - entry) / risk
            exit_reason = "structural-target"
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break

        if not be_armed:
            touched_three_r = (
                high >= three_r if side == "long" else low <= three_r
            )
            if touched_three_r:
                be_armed = True
                current_stop = entry

    if terminal is None:
        eligible = [
            bar
            for bar in day_bars[authorization_index + 1 :]
            if baseline._local_minute(bar) < LIFECYCLE_MINUTE
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
        "signal_at": setup.decision_at.isoformat(),
        "filled_at": filled_at.isoformat(),
        "exit_at": cast(datetime, exit_at).isoformat(),
        "entry_family": setup.selected_family.value,
        "candidate_families": [
            family.value for family in setup.candidate_families
        ],
        "entry": format(entry, "f"),
        "initial_stop": format(stop, "f"),
        "structural_target": format(target, "f"),
        "planned_target_r": format(abs(target - entry) / risk, "f"),
        "three_r_boundary": format(three_r, "f"),
        "breakeven_armed": be_armed,
        "exit_reason": exit_reason,
        "r_multiple": format(terminal, "f"),
        "mfe_r": format(max_favorable, "f"),
        "mae_r": format(max_adverse, "f"),
    }


def _next_source(
    *,
    reference: tuple[object, ...],
    session: tuple[object, ...],
    after_at: datetime,
    evidence: str,
    policy: Vt31R22ExecutionPolicy,
) -> dict[str, object]:
    prefix: list[object] = list(reference)
    for bar in session:
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        if closed_at <= after_at:
            continue
        prefix.append(bar)
        evaluation = evaluate_vt31_r2_2_source(
            instrument=getattr(bar, "instrument"),
            as_of=closed_at,
            m1_candles=cast(Any, tuple(prefix)),
            evidence_fingerprint=evidence,
        )
        if evaluation.setup is None:
            if evaluation.both_sides_swept:
                return {"status": "INVALIDATED", "decision_at": closed_at}
            continue

        source = evaluation.setup
        if (
            source.structure.raid_at <= after_at
            or source.structure.confirmation_at <= after_at
        ):
            continue
        executable, reason = make_executable_setup(source, policy)
        if executable is None:
            return {
                "status": "NON_EXECUTABLE",
                "decision_at": closed_at,
                "reason": None if reason is None else reason.value,
            }
        return {
            "status": "SOURCE",
            "decision_at": closed_at,
            "source": source,
            "setup": executable,
        }
    return {"status": "NO_EVENT", "decision_at": after_at}


def _risk_for(family: str, mode: str) -> Decimal:
    if mode == "FLAT060":
        return Decimal("0.60")
    if mode != "FAMILY":
        raise ValueError(mode)
    if family == "fair-value-gap":
        return Decimal("0.60")
    if family == "order-block":
        return Decimal("0.30")
    return Decimal("0.20")


def _max_loss_streak(
    rows: list[dict[str, object]],
    *,
    material: Decimal | None = None,
) -> int:
    current = 0
    maximum = 0
    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        value = _d(row["capital_weighted_net_r"])
        is_loss = value < 0 if material is None else value <= -material
        if is_loss:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def _annual_blocks(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    result = []
    for start, end in (
        (date(2022, 7, 18), date(2023, 7, 18)),
        (date(2023, 7, 18), date(2024, 7, 18)),
    ):
        selected = [
            row
            for row in rows
            if start
            <= date.fromisoformat(cast(str, row["local_date"]))
            < end
        ]
        metrics = capital._capital_metrics(selected)
        result.append(
            {
                "start": start.isoformat(),
                "end_exclusive": end.isoformat(),
                "trade_count": len(selected),
                "metrics": metrics,
                "positive": (
                    bool(selected) and _d(metrics["total_r"]) > 0
                ),
            }
        )
    return result


def _run_variant(
    by_day: dict[date, tuple[object, ...]],
    *,
    evidence: str,
    partition: str,
    name: str,
    config: dict[str, object],
) -> dict[str, object]:
    policy = Vt31R22ExecutionPolicy()
    rows: list[dict[str, object]] = []
    status: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    maturity_counts: Counter[str] = Counter()
    replacement_count = 0

    maturity_mode = cast(str, config["maturity"])
    translation_mode = cast(str, config["translation"])
    risk_mode = cast(str, config["risk"])

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        cursor = cast(datetime, getattr(reference[-1], "closed_at"))
        executions = 0
        rejected_hypothesis = False

        for _ in range(MAX_SOURCE_CYCLES_PER_DAY):
            if executions >= MAX_EXECUTIONS_PER_DAY:
                status["execution-cap-reached"] += 1
                break

            event = _next_source(
                reference=reference,
                session=session,
                after_at=cursor,
                evidence=evidence,
                policy=policy,
            )
            event_status = cast(str, event["status"])
            status[event_status] += 1
            if event_status == "NO_EVENT":
                break
            if event_status in {"INVALIDATED", "NON_EXECUTABLE"}:
                cursor = cast(datetime, event["decision_at"])
                rejected_hypothesis = True
                continue
            if event_status != "SOURCE":
                raise AssertionError(event_status)

            source = cast(Vt31R22SourceSetup, event["source"])
            current = cast(Vt31R22ExecutableSetup, event["setup"])
            maturity = _mature(
                session=session,
                source=source,
                setup=current,
                mode=maturity_mode,
            )
            maturity_status = cast(str, maturity["status"])
            maturity_counts[maturity_status] += 1

            if maturity_status != "MATURED":
                decision_at = source.structure.confirmation_at
                for key in ("authorization_at",):
                    if key in maturity:
                        decision_at = cast(datetime, maturity[key])
                # The rejection is known no later than the last observed bar.
                if maturity_mode != "IMMEDIATE":
                    bars_required, _, _, _ = _maturity_contract(
                        current.selected_family.value,
                        maturity_mode,
                    )
                    confirmation_index = next(
                        index
                        for index, bar in enumerate(session)
                        if cast(datetime, getattr(bar, "closed_at"))
                        == source.structure.confirmation_at
                    )
                    final_index = min(
                        len(session) - 1,
                        confirmation_index + int(bars_required),
                    )
                    decision_at = cast(
                        datetime,
                        getattr(session[final_index], "closed_at"),
                    )
                cursor = decision_at
                rejected_hypothesis = True
                continue

            authorization_at = cast(datetime, maturity["authorization_at"])
            authorization_price = _d(maturity["authorization_price"])
            if rejected_hypothesis:
                replacement_count += 1
                rejected_hypothesis = False

            if translation_mode == "PENDING":
                setup = activation._activation_setup(
                    current,
                    authorization_at,
                )
                outcome = baseline._simulate(day_bars, setup)
            elif translation_mode == "MARKET":
                setup = _market_setup(
                    source,
                    current,
                    authorization_at=authorization_at,
                    authorization_price=authorization_price,
                    variant=name,
                )
                if setup is None:
                    status["market-translation-invalid-geometry"] += 1
                    cursor = authorization_at
                    rejected_hypothesis = True
                    continue
                outcome = _simulate_market_at_close(day_bars, setup)
            else:
                raise ValueError(translation_mode)

            status[f"outcome-{outcome['status']}"] += 1
            if outcome.get("status") != "terminal":
                # Once a hypothesis is authorized it owns the pending/position
                # lifecycle.  Do not fabricate a concurrent replacement.
                break

            family = setup.selected_family.value
            risk = _risk_for(family, risk_mode)
            row = dict(outcome)
            row.update(
                {
                    "partition": partition,
                    "local_date": local_day.isoformat(),
                    "event_index": executions + 1,
                    "hypothesis_maturity_mode": maturity_mode,
                    "execution_translation": translation_mode,
                    "maturation_bars": maturity["bars_observed"],
                    "maturation_close_progress_ref": maturity[
                        "close_progress_ref"
                    ],
                    "maturation_favorable_ref": maturity["favorable_ref"],
                    "maturation_adverse_ref": maturity["adverse_ref"],
                    "requested_risk_r": format(risk, "f"),
                    "capital_weighted_net_r": format(
                        risk * (_d(outcome["r_multiple"]) - FRICTION),
                        "f",
                    ),
                    "future_label_used": False,
                    "hypothesis_replacement_enabled": True,
                }
            )
            rows.append(row)
            family_counts[family] += 1
            executions += 1

            exit_at = datetime.fromisoformat(cast(str, outcome["exit_at"]))
            if exit_at.tzinfo is None:
                raise ValueError("terminal exit must be timezone-aware")
            cursor = exit_at
            if _wall(exit_at) >= (11, 0, 0):
                break

    rows.sort(key=lambda row: cast(str, row["signal_at"]))
    metrics = capital._capital_metrics(rows)
    mc = capital._monte_carlo(
        rows,
        variant=f"{IDENTITY}:{name}:{partition}",
    )
    annual = _annual_blocks(rows) if partition == "consumed_holdout" else []
    objectives = {
        "density_300_350": 300 <= len(rows) <= 350,
        "pf_ge_1_50": (
            metrics["profit_factor"] is not None
            and _d(metrics["profit_factor"]) >= Decimal("1.50")
        ),
        "dd_le_6": _d(metrics["max_drawdown_r"]) <= Decimal(6),
        "raw_losing_streak_le_12": _max_loss_streak(rows) <= 12,
        "material_losing_streak_le_8": (
            _max_loss_streak(rows, material=Decimal("0.10")) <= 8
        ),
        "mc_positive_ge_0_90": (
            _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
        ),
        "mc_p95_dd_le_15": (
            _d(mc["p95_max_drawdown_r"]) <= Decimal(15)
        ),
    }
    if annual:
        objectives["both_consumed_years_positive"] = all(
            bool(block["positive"]) for block in annual
        )

    return {
        "trade_count": len(rows),
        "metrics": metrics,
        "raw_max_losing_streak": _max_loss_streak(rows),
        "material_max_losing_streak_010r": _max_loss_streak(
            rows,
            material=Decimal("0.10"),
        ),
        "monte_carlo": mc,
        "annual_blocks": annual,
        "family_counts": dict(sorted(family_counts.items())),
        "maturity_status_counts": dict(sorted(maturity_counts.items())),
        "status_counts": dict(sorted(status.items())),
        "replacement_execution_count": replacement_count,
        "objectives": objectives,
        "passes_all_objectives": all(objectives.values()),
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    if silver.SOURCE_SHA256 != EXPECTED_SOURCE_SHA256:
        raise AssertionError("Silver Bullet source SHA changed")
    if silver.METHODOLOGY_ID != EXPECTED_METHODOLOGY_ID:
        raise AssertionError("Silver Bullet methodology identity changed")

    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("hypothesis lifecycle frontier requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    variants = {
        name: _run_variant(
            by_day,
            evidence=evidence,
            partition=partition,
            name=name,
            config=config,
        )
        for name, config in VARIANTS.items()
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "partition": partition,
        "market": MARKET,
        "variants": variants,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "silver_bullet_modified": False,
            "silver_bullet_source_frozen": True,
            "source_sha256": silver.SOURCE_SHA256,
            "methodology_id": silver.METHODOLOGY_ID,
            "consumed_evidence_only": True,
            "future_labels_runtime_forbidden": True,
            "terminal_pnl_used_at_runtime": False,
            "fold_identity_used_at_runtime": False,
            "h4_primary_causal_feature": False,
            "h1_primary_causal_feature": False,
            "new_event_requires_new_post_cursor_raid_confirmation": True,
            "hypothesis_replacement_requires_prior_rejection_or_exit": True,
            "structural_stop_changed": False,
            "opposite_reference_target_changed": False,
            "three_r_breakeven_changed": False,
            "market_at_closed_m1_is_qore_translation_research": True,
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
    print(json.dumps(
        {
            "partition": payload["partition"],
            "variants": payload["variants"],
        },
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
