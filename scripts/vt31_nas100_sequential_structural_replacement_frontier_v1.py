"""Sequential structural replacement frontier for VT31_NAS100.

Consumed-evidence development only.

Purpose: replace weak fallback density with genuinely new causal source events.
The router scans successive executable source events inside the 10:00-11:00 NY
session. A rejected event is not traded; the next considered event must be a
new source built after that decision. An accepted trade blocks all further
events until its terminal exit.

Accepted contexts are based only on cross-period stable evidence already found:
- CORE action remains admissible.
- SECONDARY FVG with H1 mixed is stably positive.
- Breaker may be accepted only on SHORT and only outside all stably-negative
  SECONDARY contexts.
- Order-block LONG is never accepted as secondary because it is stably negative.

No future PnL, fold identity, target trade count, or arbitrary cooldown is used.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_causal_hybrid_density_v2 as hybrid
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_specialist_r1_candidate as specialist
import vt31_nas100_structural_rearm_density_frontier_v1 as frontier

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutionPolicy,
)

SCHEMA = "qore.vt31.nas100.sequential_structural_replacement_frontier.v1"
MARKET = "NAS100"
GLOBAL_SCALAR = Decimal("0.60")
CORE_RISK = Decimal("1.00")
SECONDARY_RISK = Decimal("0.05")
MONTHLY_SECONDARY_BUDGET = Decimal("0.60")
MAX_SOURCE_EVENTS_PER_DAY = 6

VARIANTS = (
    "CORE_ONLY",
    "CORE_PLUS_FVG_H1_MIXED",
    "CONTEXTUAL_SECONDARY",
)


def _secondary_allowed(
    *,
    variant: str,
    family: str,
    side: str,
    state: dict[str, object],
) -> bool:
    if variant == "CORE_ONLY":
        return False

    fvg_h1_mixed = (
        family == "fair-value-gap"
        and state.get("h1_state") == "mixed"
    )
    if variant == "CORE_PLUS_FVG_H1_MIXED":
        return fvg_h1_mixed

    breaker_short_contextual = (
        family == "breaker"
        and side == "short"
        and state.get("h1_state") != "mixed"
        and state.get("reference_volatility_state") != "expanded"
        and state.get("last_structure_event_family") != "breaker"
        and state.get("cash_open_state") != "bullish"
    )
    order_block_short = (
        family == "order-block"
        and side == "short"
        and state.get("cash_open_state") != "bullish"
    )
    return fvg_h1_mixed or breaker_short_contextual or order_block_short


def replay(path: Path, *, partition: str) -> dict[str, object]:
    (
        series,
        account,
        evidence,
        checked,
        evidence_sha,
        provider,
    ) = load_market_evidence(path)
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("replacement frontier requires NAS100")

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
    policy = Vt31R22ExecutionPolicy()

    results: dict[str, object] = {}

    for variant in VARIANTS:
        trades: list[dict[str, object]] = []
        status: Counter[str] = Counter()
        monthly_budget: dict[str, Decimal] = {}

        for local_day in sorted(by_day):
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

            (
                previous_path_range,
                prior_ref_median,
                prior_admitted_day_bars,
            ) = context_by_day[local_day]

            month = local_day.isoformat()[:7]
            if month not in monthly_budget:
                monthly_budget[month] = MONTHLY_SECONDARY_BUDGET

            after_at = cast(datetime, getattr(reference[-1], "closed_at"))
            event_count = 0

            while event_count < MAX_SOURCE_EVENTS_PER_DAY:
                selected = frontier._next_executable_after(
                    reference=reference,
                    session=session,
                    after_at=after_at,
                    evidence=evidence,
                    policy=policy,
                )
                if selected is None:
                    status["no-more-source-events"] += 1
                    break

                source, setup = selected
                event_count += 1
                if setup.decision_at <= after_at:
                    raise ValueError("source event did not advance causally")

                session_prefix = tuple(
                    bar
                    for bar in session
                    if cast(datetime, getattr(bar, "closed_at"))
                    <= setup.decision_at
                )
                state = specialist._state_snapshot(
                    day_bars,
                    previous_path_range,
                    prior_ref_median,
                    prior_admitted_day_bars,
                    session_prefix,
                    source,
                    setup,
                    setup.decision_at,
                )
                action = cast(str, state["action"])
                family = setup.selected_family.value
                side = setup.side.value

                tier: str | None = None
                risk: Decimal | None = None
                reason: str | None = None

                if action == "EXECUTE":
                    tier = "CORE"
                    risk = CORE_RISK
                    reason = "CORE_EXECUTE"
                elif _secondary_allowed(
                    variant=variant,
                    family=family,
                    side=side,
                    state=state,
                ):
                    if monthly_budget[month] < SECONDARY_RISK:
                        status["secondary-budget-exhausted"] += 1
                        after_at = setup.decision_at
                        continue
                    tier = "SECONDARY"
                    risk = SECONDARY_RISK
                    reason = f"SEQUENTIAL_{variant}"

                if tier is None or risk is None or reason is None:
                    status[
                        f"rejected:{action}:{family}:{side}"
                    ] += 1
                    after_at = setup.decision_at
                    continue

                if tier == "CORE":
                    outcome = specialist._simulate_selected_plan(
                        day_bars,
                        setup,
                        state,
                    )
                else:
                    outcome = specialist.baseline._simulate(
                        day_bars,
                        setup,
                    )

                status[f"{tier}:{outcome['status']}"] += 1
                if outcome.get("status") != "terminal":
                    after_at = setup.decision_at
                    continue

                weighted = hybrid._weighted(
                    outcome,
                    tier=tier,
                    risk=risk,
                    reason=reason,
                )
                weighted.update(
                    {
                        "local_date": local_day.isoformat(),
                        "source_event_index": event_count,
                        "entry_family": family,
                        "side": side,
                        "reasoning_action": action,
                        "h1_state": state.get("h1_state"),
                        "h4_state": state.get("h4_state"),
                        "reference_volatility_state": state.get(
                            "reference_volatility_state"
                        ),
                        "cash_open_state": state.get("cash_open_state"),
                        "last_structure_event_family": state.get(
                            "last_structure_event_family"
                        ),
                    }
                )
                trades.append(weighted)

                if tier == "SECONDARY":
                    monthly_budget[month] -= SECONDARY_RISK

                exit_at = datetime.fromisoformat(
                    cast(str, outcome["exit_at"])
                )
                if _wall(exit_at) >= (11, 0, 0):
                    break
                after_at = exit_at

        trades.sort(key=lambda row: cast(str, row["signal_at"]))
        scaled = engine._scale_capital_rows(
            trades,
            scalar=GLOBAL_SCALAR,
        )
        metrics = engine._capital_metrics(scaled)
        mc = engine._monte_carlo(
            scaled,
            variant=f"SEQUENTIAL_REPLACEMENT:{variant}:{partition}",
        )
        tier_counts = Counter(str(row["tier"]) for row in scaled)
        results[variant] = {
            "trade_count": len(scaled),
            "tier_counts": dict(sorted(tier_counts.items())),
            "metrics": metrics,
            "monte_carlo": mc,
            "status_counts": dict(sorted(status.items())),
            "objectives": {
                "density_300_350": 300 <= len(scaled) <= 350,
                "pf_ge_1_50": (
                    metrics["profit_factor"] is not None
                    and Decimal(cast(str, metrics["profit_factor"]))
                    >= Decimal("1.50")
                ),
                "dd_le_6": (
                    Decimal(cast(str, metrics["max_drawdown_r"]))
                    <= Decimal("6")
                ),
                "mc_positive_ge_0_90": (
                    Decimal(
                        cast(str, mc["positive_terminal_probability"])
                    )
                    >= Decimal("0.90")
                ),
                "mc_p95_dd_le_15": (
                    Decimal(cast(str, mc["p95_max_drawdown_r"]))
                    <= Decimal("15")
                ),
            },
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "variants": results,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "sequential_sources_are_genuine": True,
            "one_trade_max_per_source_event": True,
            "rejected_event_requires_new_source_before_reconsideration": True,
            "accepted_trade_blocks_until_terminal_exit": True,
            "entry_acceptance_uses_pre_entry_state_only": True,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "uses_target_trade_count_at_runtime": False,
            "global_risk_scalar": "0.60",
            "secondary_risk_r_pre_scalar": "0.05",
            "policy_promoted": False,
            "opens_new_holdout": False,
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
