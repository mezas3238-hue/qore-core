"""Cross-market factor-pressure governor for Capitalizer.

V2 nearly reached the 6R DD gate but compressed the entire portfolio for too
long. This V3 localizes danger: before each valid entry it measures recent,
already-closed normalized R for the current symbol and its shared market
factors. Exposure hardens only when portfolio DD and local/factor deterioration
agree.

All entries remain executable. No current or counterfactual outcome is used.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_adaptive_context_risk_governor_v1 as memory,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_contextual_stability_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cross_market_stability_governor_2r_v1 as governor,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import capitalizer_native_market_context_v1 as context

IDENTITY = "QORE_CAPITALIZER_CROSS_MARKET_FACTOR_PRESSURE_V3"
BASE_POLICY = "CONTEXT_STABILITY_STAGE"

SYMBOL_FACTORS: dict[str, tuple[str, ...]] = {
    "USDJPY": ("USD", "JPY"),
    "AUDJPY": ("AUD", "JPY"),
    "AUDUSD": ("AUD", "USD"),
    "GBPJPY": ("GBP", "JPY"),
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "XAUUSD": ("XAU", "USD"),
    "USDCAD": ("USD", "CAD"),
    "NAS100": ("USD", "RISK"),
}

RECENT_SYMBOL = 8
RECENT_FACTOR = 10
MIN_SYMBOL = 5
MIN_FACTOR = 6

POLICIES = (
    "FACTOR_GATED",
    "FACTOR_SYMBOL_CONSENSUS",
    "FACTOR_RECOVERY",
    "FACTOR_CEILING",
)


@dataclass(frozen=True, slots=True)
class FactorRecord:
    symbol: str
    factors: tuple[str, ...]
    exit_at: str
    normalized_r: str


@dataclass(frozen=True, slots=True)
class FactorDecision:
    role: str
    policy: str
    symbol: str
    entry_at: str
    current_drawdown_r: str
    symbol_adverse: bool
    adverse_factors: tuple[str, ...]
    pressure_votes: int
    risk_multiplier: str
    current_outcome_visible_to_decision: bool = False


def _stats(rows: tuple[FactorRecord, ...]) -> tuple[Decimal, Decimal]:
    values = tuple(Decimal(row.normalized_r) for row in rows)
    if not values:
        return Decimal("0"), Decimal("0")
    return (
        sum(values, Decimal("0")) / Decimal(len(values)),
        Decimal(sum(value < 0 for value in values)) / Decimal(len(values)),
    )


def _adverse(rows: tuple[FactorRecord, ...], *, minimum: int) -> bool:
    if len(rows) < minimum:
        return False
    mean_r, negative_rate = _stats(rows)
    return mean_r < 0 and negative_rate >= Decimal("0.55")


def _pressure(
    *,
    records: tuple[FactorRecord, ...],
    symbol: str,
) -> tuple[bool, tuple[str, ...], int]:
    symbol_rows = tuple(row for row in records if row.symbol == symbol)[-RECENT_SYMBOL:]
    symbol_adverse = _adverse(symbol_rows, minimum=MIN_SYMBOL)

    adverse_factors: list[str] = []
    for factor in SYMBOL_FACTORS[symbol]:
        factor_rows = tuple(
            row for row in records if factor in row.factors
        )[-RECENT_FACTOR:]
        if _adverse(factor_rows, minimum=MIN_FACTOR):
            adverse_factors.append(factor)
    votes = int(symbol_adverse) + len(adverse_factors)
    return symbol_adverse, tuple(adverse_factors), votes


def _multiplier(
    *,
    policy: str,
    current_dd: Decimal,
    pressure_votes: int,
    symbol_adverse: bool,
) -> Decimal:
    if policy == "FACTOR_GATED":
        if current_dd >= Decimal("5"):
            if pressure_votes >= 2:
                return Decimal("0.20")
            if pressure_votes >= 1:
                return Decimal("0.40")
            return Decimal("0.75")
        if current_dd >= Decimal("4"):
            if pressure_votes >= 2:
                return Decimal("0.35")
            if pressure_votes >= 1:
                return Decimal("0.55")
            return Decimal("1")
        if current_dd >= Decimal("3") and pressure_votes >= 2:
            return Decimal("0.65")
        return Decimal("1")

    if policy == "FACTOR_SYMBOL_CONSENSUS":
        if current_dd >= Decimal("5") and symbol_adverse and pressure_votes >= 2:
            return Decimal("0.15")
        if current_dd >= Decimal("4") and symbol_adverse and pressure_votes >= 2:
            return Decimal("0.30")
        if current_dd >= Decimal("3") and pressure_votes >= 3:
            return Decimal("0.50")
        if pressure_votes >= 3:
            return Decimal("0.70")
        return Decimal("1")

    if policy == "FACTOR_RECOVERY":
        if current_dd >= Decimal("5.5"):
            return Decimal("0.25") if pressure_votes >= 1 else Decimal("0.65")
        if current_dd >= Decimal("4.5"):
            return Decimal("0.35") if pressure_votes >= 1 else Decimal("0.80")
        if current_dd >= Decimal("3.5") and pressure_votes >= 2:
            return Decimal("0.55")
        return Decimal("1")

    if policy == "FACTOR_CEILING":
        if current_dd >= Decimal("5.5"):
            if pressure_votes >= 1:
                return Decimal("0.10")
            return Decimal("0.50")
        if current_dd >= Decimal("5"):
            return Decimal("0.20") if pressure_votes >= 1 else Decimal("0.65")
        if current_dd >= Decimal("4"):
            return Decimal("0.30") if pressure_votes >= 2 else Decimal("0.75")
        if current_dd >= Decimal("3") and pressure_votes >= 2:
            return Decimal("0.55")
        return Decimal("1")

    raise ValueError(f"unknown factor pressure policy: {policy}")


def _closed_records(
    records: tuple[FactorRecord, ...],
    *,
    entry_at: str,
) -> tuple[FactorRecord, ...]:
    current = direct._aware(entry_at)
    return tuple(row for row in records if direct._aware(row.exit_at) <= current)


def _simulate(
    *,
    role: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[FactorDecision, ...]]:
    by_mode = {
        arm: {(row.symbol, row.entry_at): row for row in rows}
        for arm, rows in ledgers.items()
    }
    baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    ordered = tuple(
        sorted(baseline, key=lambda row: (direct._aware(row.entry_at), row.symbol))
    )

    chosen_scaled: list[milestone.SimulatedTrade] = []
    records: list[FactorRecord] = []
    decisions: list[FactorDecision] = []
    multiplier_counts: dict[str, int] = defaultdict(int)
    pressure_counts: dict[str, int] = defaultdict(int)

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        ctx = contexts[key]
        history = governor._closed_history(
            tuple(chosen_scaled),
            entry_at=direct._aware(trade.entry_at),
        )
        state, _eq, _peak, current_dd, _ls = governor._state(history)
        base_mode, _level, _support = router._lookup(model, ctx)
        final_mode, _overlay = router._overlay(
            policy=BASE_POLICY,
            base_mode=base_mode,
            state=state,
        )
        unscaled = by_mode[final_mode][key]

        causal_records = _closed_records(tuple(records), entry_at=trade.entry_at)
        symbol_adverse, adverse_factors, votes = _pressure(
            records=causal_records,
            symbol=trade.symbol,
        )
        multiplier = _multiplier(
            policy=policy,
            current_dd=current_dd,
            pressure_votes=votes,
            symbol_adverse=symbol_adverse,
        )
        scaled = replace(
            unscaled,
            realized_gross_r=str(Decimal(unscaled.realized_gross_r) * multiplier),
        )
        chosen_scaled.append(scaled)
        records.append(
            FactorRecord(
                symbol=trade.symbol,
                factors=SYMBOL_FACTORS[trade.symbol],
                exit_at=unscaled.exit_at,
                normalized_r=unscaled.realized_gross_r,
            )
        )
        multiplier_counts[str(multiplier)] += 1
        pressure_counts[str(votes)] += 1
        decisions.append(
            FactorDecision(
                role=role,
                policy=policy,
                symbol=trade.symbol,
                entry_at=trade.entry_at,
                current_drawdown_r=str(current_dd),
                symbol_adverse=symbol_adverse,
                adverse_factors=adverse_factors,
                pressure_votes=votes,
                risk_multiplier=str(multiplier),
            )
        )

    result = tuple(chosen_scaled)
    return {
        "role": role,
        "policy": policy,
        "trades": len(result),
        "density_retention": "1",
        "metrics": milestone._metrics(result),
        "multiplier_counts": dict(sorted(multiplier_counts.items())),
        "pressure_counts": dict(sorted(pressure_counts.items())),
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    context_root: Path,
) -> tuple[dict[str, Any], tuple[FactorDecision, ...]]:
    development = router._load_selected(
        development_root,
        expected=memory.EXPECTED_DEVELOPMENT_TRADES,
    )
    validation = router._load_selected(
        validation_root,
        expected=memory.EXPECTED_VALIDATION_TRADES,
    )
    dev_context = router._load_contexts(context_root, role="dev")
    val_context = router._load_contexts(context_root, role="holdout")
    model = router._freeze_model(development=development, contexts=dev_context)

    control_dev, _ = router._simulate(
        role="DEV_CONTROL",
        policy=BASE_POLICY,
        ledgers=development,
        contexts=dev_context,
        model=model,
    )
    control_val, _ = router._simulate(
        role="VAL_CONTROL",
        policy=BASE_POLICY,
        ledgers=validation,
        contexts=val_context,
        model=model,
    )

    results: list[dict[str, Any]] = []
    audits: list[FactorDecision] = []
    for policy in POLICIES:
        dev, da = _simulate(
            role="DEVELOPMENT",
            policy=policy,
            ledgers=development,
            contexts=dev_context,
            model=model,
        )
        val, va = _simulate(
            role="CONSUMED_VALIDATION_2022_2024",
            policy=policy,
            ledgers=validation,
            contexts=val_context,
            model=model,
        )
        for current, control in ((dev, control_dev), (val, control_val)):
            m, c = current["metrics"], control["metrics"]
            current["pf_at_least_contextual_control"] = (
                Decimal(str(m["profit_factor"])) >= Decimal(str(c["profit_factor"]))
            )
            current["dd_below_contextual_control"] = (
                Decimal(str(m["max_drawdown_r"])) < Decimal(str(c["max_drawdown_r"]))
            )
            current["dd_at_or_below_6r"] = Decimal(str(m["max_drawdown_r"])) <= Decimal("6")
            current["total_r_retention"] = str(
                Decimal(str(m["total_r"])) / Decimal(str(c["total_r"]))
            )
        results.append({"policy": policy, "development": dev, "validation": val})
        audits.extend(da)
        audits.extend(va)

    robust = tuple(
        row for row in results
        if row["development"]["pf_at_least_contextual_control"]
        and row["development"]["dd_below_contextual_control"]
        and row["validation"]["pf_at_least_contextual_control"]
        and row["validation"]["dd_below_contextual_control"]
    )
    dd6 = tuple(row for row in robust if row["validation"]["dd_at_or_below_6r"])

    return {
        "identity": IDENTITY,
        "development_trades": memory.EXPECTED_DEVELOPMENT_TRADES,
        "validation_trades": memory.EXPECTED_VALIDATION_TRADES,
        "policy_count": len(POLICIES),
        "results": results,
        "robust_pf_up_dd_down_policy_count": len(robust),
        "robust_validation_dd6_policy_count": len(dd6),
        "all_entries_preserved": True,
        "factor_state_uses_prior_closed_chosen_outcomes_only": True,
        "current_outcome_visible_to_factor_state": False,
        "validation_is_fresh_holdout": False,
        "new_holdout_reserved": "2020-09-17_TO_2022-09-17",
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_FACTOR_GOVERNOR_AND_RUN_RESERVED_HOLDOUT"
            if robust
            else "COMBINE_FACTOR_PRESSURE_WITH_DESTINATION_EDGE_MEMORY"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[FactorDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cross-market-factor-pressure-v3.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-cross-market-factor-pressure-v3-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, audits = build_report(
        args.development_root,
        args.validation_root,
        args.context_root,
    )
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
