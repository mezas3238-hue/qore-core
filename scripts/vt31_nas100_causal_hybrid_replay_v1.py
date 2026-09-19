"""Causal VT31 NAS100 CORE + SECONDARY replay.

This is the causality repair for the artifact-composition hybrid experiment.

CORE:
- exact current VT31_NAS100 intelligent reasoning;
- risk request 1.00R;
- preserves current dynamic destination management.

SECONDARY:
- never depends on knowing whether CORE trades later in the day;
- becomes eligible only when the causal CORE path has already:
  a) returned ABSTAIN, or
  b) produced a valid source that legacy single-route execution cannot resolve;
- causal OCO candidates may fill only after SECONDARY authorization;
- second-side sweep before fill invalidates the source;
- at most one position is selected per market day;
- risk request 0.05R;
- monthly SECONDARY risk budget 0.45R, no carry.

The replay therefore cannot use a date-level "CORE did not trade" oracle.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.causal_hybrid_replay.v1"
IDENTITY = "VT31_NAS100_CAUSAL_HYBRID_V1"
MARKET = "NAS100"
CORE_RISK = Decimal("1.00")
SECONDARY_RISK = Decimal("0.05")
SECONDARY_MONTHLY_BUDGET = Decimal("0.45")
FRICTION = Decimal("0.05")


def _activation_setup(
    setup: Vt31R22ExecutableSetup,
    authorization_at: datetime,
) -> Vt31R22ExecutableSetup:
    decision_at = max(setup.decision_at, authorization_at)
    return Vt31R22ExecutableSetup(
        side=setup.side,
        entry_price=setup.entry_price,
        stop_price=setup.stop_price,
        target_price=setup.target_price,
        three_r_price=setup.three_r_price,
        selected_family=setup.selected_family,
        candidate_families=setup.candidate_families,
        decision_at=decision_at,
        pending_expires_at=setup.pending_expires_at,
        source_setup=setup.source_setup,
        execution_policy_fingerprint=setup.execution_policy_fingerprint,
    )


def _fill_after_authorization(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
    *,
    authorization_at: datetime,
    both_sides_swept_at: datetime | None,
) -> tuple[int | None, str | None]:
    active = max(setup.decision_at, authorization_at)
    for index, bar in enumerate(day_bars):
        opened_at = cast(datetime, getattr(bar, "opened_at"))
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        if opened_at < active:
            continue
        if opened_at >= setup.pending_expires_at:
            break
        if both_sides_swept_at is not None:
            if opened_at >= both_sides_swept_at:
                return None, "cancelled-before-fill-by-second-side-sweep"
        low = Decimal(str(getattr(bar, "low")))
        high = Decimal(str(getattr(bar, "high")))
        if not low <= setup.entry_price <= high:
            continue
        if (
            both_sides_swept_at is not None
            and opened_at < both_sides_swept_at <= closed_at
        ):
            return None, "censored-same-bar-fill-vs-second-side-sweep"
        return index, None
    return None, None


def _select_secondary_after(
    day_bars: tuple[object, ...],
    timeline: oco.SourceTimeline,
    policy: Vt31R22ExecutionPolicy,
    *,
    authorization_at: datetime,
) -> tuple[Vt31R22ExecutableSetup | None, str]:
    if (
        timeline.both_sides_swept_at is not None
        and timeline.both_sides_swept_at <= authorization_at
    ):
        return None, "source-invalidated-before-authorization"

    candidates: list[tuple[int, Vt31R22ExecutableSetup]] = []
    censored = False
    for evidence in timeline.candidates:
        raw_setup = oco._candidate_order(timeline.source, evidence, policy)
        if raw_setup is None:
            continue
        setup = _activation_setup(raw_setup, authorization_at)
        fill_index, reason = _fill_after_authorization(
            day_bars,
            setup,
            authorization_at=authorization_at,
            both_sides_swept_at=timeline.both_sides_swept_at,
        )
        if reason == "censored-same-bar-fill-vs-second-side-sweep":
            censored = True
        if fill_index is not None:
            candidates.append((fill_index, setup))

    if not candidates:
        return (
            None,
            (
                "censored-second-side-fill-ambiguity"
                if censored
                else "no-causal-fill"
            ),
        )

    earliest_index = min(item[0] for item in candidates)
    first = [
        setup for index, setup in candidates if index == earliest_index
    ]
    prices = {setup.entry_price for setup in first}
    if len(prices) > 1:
        return None, "censored-same-bar-multi-price-oco-fill"
    selected = sorted(
        first,
        key=lambda item: (
            item.decision_at,
            item.selected_family.value,
        ),
    )[0]
    return selected, "selected"


def _weighted_trade(
    outcome: dict[str, object],
    *,
    tier: str,
    requested_risk: Decimal,
    authorization_reason: str,
) -> dict[str, object]:
    raw_r = Decimal(cast(str, outcome["r_multiple"]))
    result = dict(outcome)
    result.update(
        {
            "tier": tier,
            "requested_risk_r": format(requested_risk, "f"),
            "capital_weighted_net_r": format(
                requested_risk * (raw_r - FRICTION),
                "f",
            ),
            "secondary_authorization_reason": authorization_reason,
        }
    )
    return result


def _capital_metrics(
    trades: list[dict[str, object]],
) -> dict[str, object]:
    converted = [
        {
            **trade,
            "r_multiple": trade["capital_weighted_net_r"],
        }
        for trade in trades
    ]
    return _metrics(converted, friction=Decimal(0))


def _monte_carlo(
    trades: list[dict[str, object]],
) -> dict[str, object]:
    values = [
        Decimal(cast(str, trade["capital_weighted_net_r"]))
        for trade in trades
    ]
    n = len(values)
    if n == 0:
        return {
            "paths": 10000,
            "block_length": 5,
            "positive_terminal_probability": "0",
            "p95_max_drawdown_r": "0",
        }
    domain = (
        IDENTITY.encode()
        + b":"
        + specialist.contract_fingerprint().encode()
    )
    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    for path_index in range(10000):
        sampled: list[Decimal] = []
        block_index = 0
        while len(sampled) < n:
            digest = hashlib.sha256(
                domain
                + b":"
                + str(path_index).encode()
                + b":"
                + str(block_index).encode()
            ).digest()
            start = int.from_bytes(digest, "big") % n
            sampled.extend(
                values[(start + offset) % n]
                for offset in range(5)
            )
            block_index += 1
        equity = Decimal(0)
        peak = Decimal(0)
        max_dd = Decimal(0)
        for value in sampled[:n]:
            equity += value
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        terminals.append(equity)
        drawdowns.append(max_dd)
    terminals.sort()
    drawdowns.sort()
    return {
        "algorithm": "sha256-moving-block-bootstrap-v1",
        "paths": 10000,
        "block_length": 5,
        "positive_terminal_probability": format(
            Decimal(sum(item > 0 for item in terminals))
            / Decimal(10000),
            "f",
        ),
        "p05_terminal_r": format(
            terminals[(len(terminals) - 1) * 5 // 100],
            "f",
        ),
        "p50_terminal_r": format(
            terminals[(len(terminals) - 1) * 50 // 100],
            "f",
        ),
        "p95_max_drawdown_r": format(
            drawdowns[(len(drawdowns) - 1) * 95 // 100],
            "f",
        ),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("causal hybrid requires NAS100 evidence")

    raw_by_day: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw_by_day[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda bar: getattr(bar, "opened_at"))
        )
        for local_day, items in raw_by_day.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = Vt31R22ExecutionPolicy()

    trades: list[dict[str, object]] = []
    status: Counter[str] = Counter()
    monthly_budget_ledger: dict[str, dict[str, object]] = {}
    current_month: str | None = None
    secondary_budget = Decimal(0)

    for local_day in sorted(by_day):
        month = local_day.isoformat()[:7]
        if month != current_month:
            current_month = month
            secondary_budget = SECONDARY_MONTHLY_BUDGET
            monthly_budget_ledger[month] = {
                "opening_budget_r": format(secondary_budget, "f"),
                "executed_secondary": 0,
                "remaining_budget_r": format(secondary_budget, "f"),
            }

        day_bars = by_day[local_day]
        reference = specialist._slice(
            day_bars,
            (9, 0, 0),
            (10, 0, 0),
        )
        session = specialist._slice(
            day_bars,
            (10, 0, 0),
            (11, 0, 0),
        )
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        timeline = oco._timeline(
            day_bars,
            evidence_fingerprint=evidence,
        )

        prefix = list(reference)
        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        ) = context_by_day[local_day]
        core_selected: Vt31R22ExecutableSetup | None = None
        core_state: dict[str, object] | None = None
        secondary_authorized_at: datetime | None = None
        secondary_reason: str | None = None
        saw_wait = False
        source_invalidated = False

        for bar in session:
            prefix.append(bar)
            closed_at = cast(datetime, getattr(bar, "closed_at"))
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=closed_at,
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                if saw_wait and evaluation.both_sides_swept:
                    source_invalidated = True
                    status["core-invalidated-after-wait"] += 1
                    break
                continue

            executable, _ = make_executable_setup(
                evaluation.setup,
                policy,
            )
            if executable is None:
                secondary_authorized_at = closed_at
                secondary_reason = "CORE_SOURCE_NOT_SINGLE_ROUTE_EXECUTABLE"
                status["secondary-authorized-source-router"] += 1
                break

            session_prefix = tuple(
                item
                for item in prefix
                if (10, 0, 0)
                <= _wall(getattr(item, "opened_at"))
                < (11, 0, 0)
            )
            state = specialist._state_snapshot(
                day_bars,
                previous_path_range,
                prior_ref_median,
                prior_admitted_day_bars,
                session_prefix,
                evaluation.setup,
                executable,
                closed_at,
            )
            action = cast(str, state["action"])
            if action == "WAIT":
                saw_wait = True
                status["core-wait-observation"] += 1
                continue
            if action == "ABSTAIN":
                secondary_authorized_at = closed_at
                secondary_reason = "CORE_CAUSAL_ABSTAIN"
                status["secondary-authorized-core-abstain"] += 1
                break
            if action != "EXECUTE":
                raise ValueError(action)

            core_selected = _activation_setup(executable, closed_at)
            core_state = state
            break

        if core_selected is not None and core_state is not None:
            outcome = specialist._simulate_selected_plan(
                day_bars,
                core_selected,
                core_state,
            )
            status[f"core-{outcome['status']}"] += 1
            if outcome.get("status") == "terminal":
                trades.append(
                    _weighted_trade(
                        outcome,
                        tier="CORE",
                        requested_risk=CORE_RISK,
                        authorization_reason="CORE_EXECUTE",
                    )
                )
            continue

        if source_invalidated or secondary_authorized_at is None:
            status["no-secondary-authorization"] += 1
            continue
        if timeline is None:
            status["secondary-no-oco-timeline"] += 1
            continue
        if secondary_budget < SECONDARY_RISK:
            status["secondary-monthly-budget-exhausted"] += 1
            continue

        selected, selection_status = _select_secondary_after(
            day_bars,
            timeline,
            policy,
            authorization_at=secondary_authorized_at,
        )
        status[f"secondary-{selection_status}"] += 1
        if selected is None:
            continue

        outcome = specialist.baseline._simulate(day_bars, selected)
        status[f"secondary-outcome-{outcome['status']}"] += 1
        if outcome.get("status") != "terminal":
            continue

        secondary_budget -= SECONDARY_RISK
        monthly_budget_ledger[month]["executed_secondary"] = (
            int(monthly_budget_ledger[month]["executed_secondary"]) + 1
        )
        monthly_budget_ledger[month]["remaining_budget_r"] = format(
            secondary_budget,
            "f",
        )
        trades.append(
            _weighted_trade(
                outcome,
                tier="SECONDARY",
                requested_risk=SECONDARY_RISK,
                authorization_reason=cast(str, secondary_reason),
            )
        )

    trades.sort(key=lambda item: cast(str, item["signal_at"]))
    metrics = _capital_metrics(trades)
    mc = _monte_carlo(trades)
    core_count = sum(item["tier"] == "CORE" for item in trades)
    secondary_count = sum(item["tier"] == "SECONDARY" for item in trades)
    gates = {
        "trade_count_250_to_300": 250 <= len(trades) <= 300,
        "capital_weighted_pf_at_least_2": (
            metrics["profit_factor"] is not None
            and Decimal(cast(str, metrics["profit_factor"])) >= Decimal(2)
        ),
        "capital_weighted_dd_at_most_10r": (
            Decimal(cast(str, metrics["max_drawdown_r"])) <= Decimal(10)
        ),
        "mc_positive_at_least_0_90": (
            Decimal(cast(str, mc["positive_terminal_probability"]))
            >= Decimal("0.90")
        ),
        "mc_p95_dd_at_most_20r": (
            Decimal(cast(str, mc["p95_max_drawdown_r"])) <= Decimal(20)
        ),
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET,
        "candidate_contract_fingerprint": specialist.contract_fingerprint(),
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
            "bar_count": len(series),
        },
        "capital_policy": {
            "core_requested_risk_r": format(CORE_RISK, "f"),
            "secondary_requested_risk_r": format(SECONDARY_RISK, "f"),
            "secondary_monthly_budget_r": format(
                SECONDARY_MONTHLY_BUDGET,
                "f",
            ),
            "secondary_budget_carry": False,
            "one_selected_position_per_market_day": True,
            "risk_authorization_remains_external_qore_risk": True,
        },
        "trade_count": len(trades),
        "core_trade_count": core_count,
        "secondary_trade_count": secondary_count,
        "capital_weighted_metrics": metrics,
        "monte_carlo": mc,
        "development_gates": gates,
        "passes_development_gates": all(gates.values()),
        "status_counts": dict(sorted(status.items())),
        "monthly_secondary_budget": monthly_budget_ledger,
        "trades": trades,
        "governance": {
            "date_level_core_nontrade_oracle_used": False,
            "secondary_authorized_only_from_causal_core_state": True,
            "secondary_fill_before_authorization_allowed": False,
            "post_outcome_field_used_for_entry": False,
            "consumed_evidence_only": True,
            "opens_new_holdout": False,
            "live_authorized": False,
            "real_capital_authorized": False,
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
                "trades": payload["trade_count"],
                "core": payload["core_trade_count"],
                "secondary": payload["secondary_trade_count"],
                "metrics": payload["capital_weighted_metrics"],
                "mc": payload["monte_carlo"],
                "gates": payload["development_gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
