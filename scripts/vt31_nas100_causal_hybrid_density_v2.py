"""VT31 NAS100 Causal Hybrid Density V2.

Consumed-evidence research only.

This expands the fully causal CORE + SECONDARY architecture without using a
date-level "CORE did not trade" oracle.

Capital hierarchy:
- CORE: 1.00R requested risk when the intelligent specialist executes.
- SECONDARY: 0.05R after causal CORE ABSTAIN / unresolved source routing.
- SCOUT: 0.02R when CORE remains in WAIT past a predeclared clock threshold.

SCOUT is not a new strategy. It uses the same causal OCO source/candidates and
may fill only after its authorization timestamp. At most one selected position
exists per market day.

Variants are predeclared to study density:
- WAIT_NONE: current causal hybrid semantics.
- WAIT_1025: release a tiny-risk scout after persistent WAIT at 10:25 NY.
- WAIT_1020: release a tiny-risk scout after persistent WAIT at 10:20 NY.

No future outcome, date-level nontrade oracle, or post-outcome field authorizes
entry. QORE Risk remains sovereign.
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

import vt31_nas100_causal_hybrid_replay_v1 as v1
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

SCHEMA = "qore.vt31.nas100.causal_hybrid_density.v2"
IDENTITY = "VT31_NAS100_CAUSAL_HYBRID_DENSITY_V2"
MARKET = "NAS100"
FRICTION = Decimal("0.05")
CORE_RISK = Decimal("1.00")
SECONDARY_RISK = Decimal("0.05")
SCOUT_RISK = Decimal("0.02")
VARIANTS: dict[str, tuple[int | None, Decimal]] = {
    "WAIT_NONE_B060": (None, Decimal("0.60")),
    "WAIT_1025_B060": (10 * 60 + 25, Decimal("0.60")),
    "WAIT_1020_B060": (10 * 60 + 20, Decimal("0.60")),
    "WAIT_1020_B075": (10 * 60 + 20, Decimal("0.75")),
    "WAIT_1015_B075": (10 * 60 + 15, Decimal("0.75")),
    "WAIT_1010_B075": (10 * 60 + 10, Decimal("0.75")),
    "WAIT_1015_B090": (10 * 60 + 15, Decimal("0.90")),
}


def _weighted(
    outcome: dict[str, object],
    *,
    tier: str,
    risk: Decimal,
    reason: str,
) -> dict[str, object]:
    raw_r = Decimal(cast(str, outcome["r_multiple"]))
    row = dict(outcome)
    row.update(
        {
            "tier": tier,
            "requested_risk_r": format(risk, "f"),
            "capital_weighted_net_r": format(
                risk * (raw_r - FRICTION),
                "f",
            ),
            "authorization_reason": reason,
        }
    )
    return row


def _capital_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    converted = [
        {**row, "r_multiple": row["capital_weighted_net_r"]}
        for row in rows
    ]
    return _metrics(converted, friction=Decimal(0))


def _monte_carlo(
    rows: list[dict[str, object]],
    *,
    variant: str,
) -> dict[str, object]:
    values = [
        Decimal(cast(str, row["capital_weighted_net_r"]))
        for row in rows
    ]
    n = len(values)
    if not n:
        return {
            "paths": 10000,
            "block_length": 5,
            "positive_terminal_probability": "0",
            "p95_max_drawdown_r": "0",
        }
    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    domain = IDENTITY.encode() + b":" + variant.encode()
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
            Decimal(sum(item > 0 for item in terminals)) / Decimal(10000),
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


def _run_variant(
    by_day: dict[date, tuple[object, ...]],
    context_by_day: dict[date, tuple[Decimal | None, Decimal | None, tuple[object, ...]]],
    *,
    evidence: str,
    wait_release_minute: int | None,
    monthly_alt_budget: Decimal,
    variant: str,
) -> dict[str, object]:
    policy = Vt31R22ExecutionPolicy()
    trades: list[dict[str, object]] = []
    status: Counter[str] = Counter()
    budget_ledger: dict[str, dict[str, object]] = {}
    current_month: str | None = None
    alt_budget = Decimal(0)

    for local_day in sorted(by_day):
        month = local_day.isoformat()[:7]
        if month != current_month:
            current_month = month
            alt_budget = monthly_alt_budget
            budget_ledger[month] = {
                "opening_budget_r": format(alt_budget, "f"),
                "secondary_count": 0,
                "scout_count": 0,
                "remaining_budget_r": format(alt_budget, "f"),
            }

        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        timeline = oco._timeline(day_bars, evidence_fingerprint=evidence)
        prefix = list(reference)
        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        ) = context_by_day[local_day]

        core_selected: Vt31R22ExecutableSetup | None = None
        core_state: dict[str, object] | None = None
        alt_authorized_at: datetime | None = None
        alt_reason: str | None = None
        alt_tier: str | None = None
        alt_risk: Decimal | None = None
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

            executable, _ = make_executable_setup(evaluation.setup, policy)
            if executable is None:
                alt_authorized_at = closed_at
                alt_reason = "CORE_SOURCE_NOT_SINGLE_ROUTE_EXECUTABLE"
                alt_tier = "SECONDARY"
                alt_risk = SECONDARY_RISK
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
                if (
                    wait_release_minute is not None
                    and specialist.baseline._local_minute(bar)
                    >= wait_release_minute
                ):
                    alt_authorized_at = closed_at
                    alt_reason = f"CORE_PERSISTENT_WAIT_{wait_release_minute}"
                    alt_tier = "SCOUT"
                    alt_risk = SCOUT_RISK
                    status["scout-authorized-persistent-wait"] += 1
                    break
                continue
            if action == "ABSTAIN":
                alt_authorized_at = closed_at
                alt_reason = "CORE_CAUSAL_ABSTAIN"
                alt_tier = "SECONDARY"
                alt_risk = SECONDARY_RISK
                status["secondary-authorized-core-abstain"] += 1
                break
            if action != "EXECUTE":
                raise ValueError(action)
            core_selected = v1._activation_setup(executable, closed_at)
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
                    _weighted(
                        outcome,
                        tier="CORE",
                        risk=CORE_RISK,
                        reason="CORE_EXECUTE",
                    )
                )
            continue

        if (
            source_invalidated
            or alt_authorized_at is None
            or alt_risk is None
            or alt_tier is None
        ):
            status["no-alt-authorization"] += 1
            continue
        if timeline is None:
            status["alt-no-oco-timeline"] += 1
            continue
        if alt_budget < alt_risk:
            status["alt-monthly-budget-exhausted"] += 1
            continue

        selected, selection_status = v1._select_secondary_after(
            day_bars,
            timeline,
            policy,
            authorization_at=alt_authorized_at,
        )
        status[f"alt-{selection_status}"] += 1
        if selected is None:
            continue

        outcome = specialist.baseline._simulate(day_bars, selected)
        status[f"alt-outcome-{outcome['status']}"] += 1
        if outcome.get("status") != "terminal":
            continue

        alt_budget -= alt_risk
        key = "scout_count" if alt_tier == "SCOUT" else "secondary_count"
        budget_ledger[month][key] = int(budget_ledger[month][key]) + 1
        budget_ledger[month]["remaining_budget_r"] = format(alt_budget, "f")
        trades.append(
            _weighted(
                outcome,
                tier=alt_tier,
                risk=alt_risk,
                reason=cast(str, alt_reason),
            )
        )

    trades.sort(key=lambda item: cast(str, item["signal_at"]))
    metrics = _capital_metrics(trades)
    mc = _monte_carlo(trades, variant=variant)
    tier_counts = Counter(str(row["tier"]) for row in trades)
    gates = {
        "r5_like_density_at_least_300": len(trades) >= 300,
        "profit_factor_at_least_2": (
            metrics["profit_factor"] is not None
            and Decimal(cast(str, metrics["profit_factor"])) >= Decimal("2")
        ),
        "observed_dd_at_most_10r": (
            Decimal(cast(str, metrics["max_drawdown_r"])) <= Decimal("10")
        ),
        "mc_positive_at_least_0_90": (
            Decimal(cast(str, mc["positive_terminal_probability"]))
            >= Decimal("0.90")
        ),
        "mc_p95_dd_at_most_15r": (
            Decimal(cast(str, mc["p95_max_drawdown_r"])) <= Decimal("15")
        ),
    }
    return {
        "variant": variant,
        "wait_release_minute": wait_release_minute,
        "monthly_alt_budget_r": format(monthly_alt_budget, "f"),
        "trade_count": len(trades),
        "tier_counts": dict(sorted(tier_counts.items())),
        "capital_weighted_metrics": metrics,
        "monte_carlo": mc,
        "development_gates": gates,
        "passes_development_gates": all(gates.values()),
        "status_counts": dict(sorted(status.items())),
        "budget_ledger": budget_ledger,
        "trades": trades,
    }


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("causal hybrid density requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda bar: getattr(bar, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    variants = {
        name: _run_variant(
            by_day,
            context_by_day,
            evidence=evidence,
            wait_release_minute=minute,
            monthly_alt_budget=budget,
            variant=name,
        )
        for name, (minute, budget) in VARIANTS.items()
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
        },
        "capital_policy": {
            "core_requested_risk_r": format(CORE_RISK, "f"),
            "secondary_requested_risk_r": format(SECONDARY_RISK, "f"),
            "scout_requested_risk_r": format(SCOUT_RISK, "f"),
            "monthly_alt_budget_r": "variant-specific",
            "one_selected_position_per_market_day": True,
            "qore_risk_remains_sovereign": True,
        },
        "variants": variants,
        "governance": {
            "date_level_core_nontrade_oracle_used": False,
            "wait_release_is_clock_and_core_state_causal": True,
            "secondary_fill_before_authorization_allowed": False,
            "scout_fill_before_authorization_allowed": False,
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
    print(json.dumps({
        "variants": {
            name: {
                "trade_count": item["trade_count"],
                "tier_counts": item["tier_counts"],
                "metrics": item["capital_weighted_metrics"],
                "mc": item["monte_carlo"],
                "gates": item["development_gates"],
                "passes": item["passes_development_gates"],
            }
            for name, item in cast(dict[str, dict[str, object]], payload["variants"]).items()
        }
    }, sort_keys=True))


if __name__ == "__main__":
    main()
