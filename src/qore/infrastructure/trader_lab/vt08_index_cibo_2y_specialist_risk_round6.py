"""VT08 Index CIBO Round 6 — specialist management + sovereign risk governor.

R6 preserves every one of the 657 fixed admissions from R4/R5. It researches
whether the same entries can be managed differently by broad causal cells
(market, then market+side) and whether a strictly causal non-zero risk governor
can hold portfolio drawdown near 5-6R without skipping trades.

The tuning window is consumed. No result from this module is a fresh holdout or
certification claim.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round1 as r1
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round2 as r2
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_cibo_2y_specialist_risk_round6.v1"
IDENTITY = "VT08_INDEX_CIBO_2Y_SPECIALIST_RISK_ROUND6_FIXED_657"
FIXED_DENSITY = r5.FIXED_DENSITY
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
RAW_PF_FLOOR = Decimal("1.25")
GOVERNED_PF_GOAL = Decimal("1.50")
GOVERNED_DD_GOAL = Decimal("6")
SECONDARY_PF_GOAL = Decimal("1.30")
SECONDARY_DD_GOAL = Decimal("8")


@dataclass(frozen=True, slots=True)
class ManagementMap:
    kind: str
    policy_by_cell: tuple[tuple[str, str], ...]

    @property
    def mapping(self) -> dict[str, str]:
        return dict(self.policy_by_cell)

    @property
    def management_id(self) -> str:
        material = {
            "kind": self.kind,
            "policy_by_cell": list(self.policy_by_cell),
        }
        digest = sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        return f"R6M-{digest}"

    def payload(self) -> dict[str, Any]:
        return {
            "management_id": self.management_id,
            "kind": self.kind,
            "policy_by_cell": dict(self.policy_by_cell),
        }


@dataclass(frozen=True, slots=True)
class RiskGovernor:
    nas100_weight: Decimal
    sp500_weight: Decimal
    us30_weight: Decimal
    warn_dd_r: Decimal
    warn_multiplier: Decimal
    hard_dd_r: Decimal
    hard_multiplier: Decimal
    loss_streak_trigger: int
    loss_streak_multiplier: Decimal

    @property
    def governor_id(self) -> str:
        payload = self.payload(include_id=False)
        digest = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        return f"R6G-{digest}"

    def market_weight(self, symbol: str) -> Decimal:
        if symbol == "NAS100":
            return self.nas100_weight
        if symbol == "SP500":
            return self.sp500_weight
        if symbol == "US30":
            return self.us30_weight
        raise ValueError(f"unsupported symbol {symbol}")

    def payload(self, *, include_id: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "market_weights": {
                "NAS100": str(self.nas100_weight),
                "SP500": str(self.sp500_weight),
                "US30": str(self.us30_weight),
            },
            "warn_dd_r": str(self.warn_dd_r),
            "warn_multiplier": str(self.warn_multiplier),
            "hard_dd_r": str(self.hard_dd_r),
            "hard_multiplier": str(self.hard_multiplier),
            "loss_streak_trigger": self.loss_streak_trigger,
            "loss_streak_multiplier": str(self.loss_streak_multiplier),
            "minimum_risk_multiplier": str(
                min(
                    self.nas100_weight,
                    self.sp500_weight,
                    self.us30_weight,
                )
                * min(
                    self.hard_multiplier,
                    self.loss_streak_multiplier,
                )
            ),
        }
        if include_id:
            result["governor_id"] = self.governor_id
        return result


def _basic_metrics(values: Sequence[Decimal]) -> dict[str, Any]:
    total = sum(values, Decimal())
    gains = sum((value for value in values if value > 0), Decimal())
    losses = -sum((value for value in values if value < 0), Decimal())
    equity = Decimal()
    peak = Decimal()
    dd = Decimal()
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_r": str(total),
        "mean_r": str(total / len(values)) if values else "0",
        "profit_factor": str(gains / losses) if losses else None,
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
    }


def _cell_key(signal: v6.CandidateSignal, kind: str) -> str:
    if kind == "market":
        return signal.symbol
    if kind == "market-side":
        return f"{signal.symbol}:{signal.side.value}"
    raise ValueError(f"unsupported management kind {kind}")


def _policy_outcomes(
    signals: Sequence[v6.CandidateSignal],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    opened_by_symbol: dict[str, tuple[datetime, ...]],
) -> tuple[
    dict[str, r5.Policy],
    dict[str, tuple[r5.ManagedTrade, ...]],
]:
    policies = {policy.policy_id: policy for policy in r5._policy_grid()}
    outcomes: dict[str, tuple[r5.ManagedTrade, ...]] = {}
    for policy_id, policy in policies.items():
        outcomes[policy_id] = tuple(
            r5._manage_trade(
                signal,
                bars=bars_by_symbol[signal.symbol],
                opened=opened_by_symbol[signal.symbol],
                policy=policy,
            )
            for signal in signals
        )
    return policies, outcomes


def _cell_policy_rank(
    *,
    indices: Sequence[int],
    outcomes: Sequence[r5.ManagedTrade],
) -> tuple[Decimal, Decimal, Decimal]:
    values = tuple(outcomes[index].r_multiple - PRIMARY_STRESS for index in indices)
    metrics = _basic_metrics(values)
    return (
        Decimal(str(metrics["profit_factor"] or "0")),
        -Decimal(str(metrics["max_drawdown_r"])),
        Decimal(str(metrics["total_r"])),
    )


def _top_policies_by_cell(
    signals: Sequence[v6.CandidateSignal],
    *,
    kind: str,
    outcomes_by_policy: dict[str, tuple[r5.ManagedTrade, ...]],
    top_k: int,
) -> dict[str, tuple[str, ...]]:
    cells = sorted({_cell_key(signal, kind) for signal in signals})
    result: dict[str, tuple[str, ...]] = {}
    for cell in cells:
        indices = [
            index
            for index, signal in enumerate(signals)
            if _cell_key(signal, kind) == cell
        ]
        ranked = sorted(
            outcomes_by_policy,
            key=lambda policy_id: _cell_policy_rank(
                indices=indices,
                outcomes=outcomes_by_policy[policy_id],
            ),
            reverse=True,
        )
        result[cell] = tuple(ranked[:top_k])
    return result


def _management_candidates(
    signals: Sequence[v6.CandidateSignal],
    *,
    outcomes_by_policy: dict[str, tuple[r5.ManagedTrade, ...]],
) -> tuple[ManagementMap, ...]:
    result: dict[str, ManagementMap] = {}

    global_ranked = sorted(
        outcomes_by_policy,
        key=lambda policy_id: _cell_policy_rank(
            indices=tuple(range(len(signals))),
            outcomes=outcomes_by_policy[policy_id],
        ),
        reverse=True,
    )
    for policy_id in global_ranked[:10]:
        mapping = ManagementMap(
            kind="global",
            policy_by_cell=(("*", policy_id),),
        )
        result[mapping.management_id] = mapping

    for kind, top_k in (("market", 6), ("market-side", 3)):
        top = _top_policies_by_cell(
            signals,
            kind=kind,
            outcomes_by_policy=outcomes_by_policy,
            top_k=top_k,
        )
        cells = tuple(sorted(top))
        for choices in itertools.product(*(top[cell] for cell in cells)):
            mapping = ManagementMap(
                kind=kind,
                policy_by_cell=tuple(zip(cells, choices, strict=True)),
            )
            result[mapping.management_id] = mapping
    return tuple(result.values())


def _outcomes_for_management(
    signals: Sequence[v6.CandidateSignal],
    management: ManagementMap,
    outcomes_by_policy: dict[str, tuple[r5.ManagedTrade, ...]],
) -> tuple[r5.ManagedTrade, ...]:
    mapping = management.mapping
    selected: list[r5.ManagedTrade] = []
    for index, signal in enumerate(signals):
        if management.kind == "global":
            policy_id = mapping["*"]
        else:
            policy_id = mapping[_cell_key(signal, management.kind)]
        selected.append(outcomes_by_policy[policy_id][index])
    return tuple(selected)


def _raw_report(
    signals: Sequence[v6.CandidateSignal],
    outcomes: Sequence[r5.ManagedTrade],
) -> dict[str, Any]:
    primary = tuple(item.r_multiple - PRIMARY_STRESS for item in outcomes)
    secondary = tuple(item.r_multiple - SECONDARY_STRESS for item in outcomes)
    by_market: dict[str, Any] = {}
    for symbol in r1.SYMBOLS:
        indices = [
            index for index, signal in enumerate(signals) if signal.symbol == symbol
        ]
        by_market[symbol] = {
            "sample": len(indices),
            "primary": _basic_metrics(tuple(primary[index] for index in indices)),
            "secondary": _basic_metrics(tuple(secondary[index] for index in indices)),
        }
    return {
        "primary": _basic_metrics(primary),
        "secondary": _basic_metrics(secondary),
        "by_market": by_market,
    }


def _raw_rank(row: dict[str, Any]) -> tuple[int, Decimal, Decimal, Decimal]:
    raw = cast(dict[str, Any], row["raw"])
    primary = cast(dict[str, Any], raw["primary"])
    return (
        int(Decimal(str(primary["profit_factor"] or "0")) >= RAW_PF_FLOOR),
        Decimal(str(primary["profit_factor"] or "0")),
        -Decimal(str(primary["max_drawdown_r"])),
        Decimal(str(primary["total_r"])),
    )


def _governor_grid() -> tuple[RiskGovernor, ...]:
    result: list[RiskGovernor] = []
    for nas, sp, us in itertools.product(
        (Decimal("0.75"), Decimal("1.0")),
        (Decimal("0.5"), Decimal("0.75"), Decimal("1.0")),
        (Decimal("0.75"), Decimal("1.0")),
    ):
        for warn_dd, warn_mult, hard_dd, hard_mult, trigger, streak_mult in itertools.product(
            (Decimal("1.5"), Decimal("2.0"), Decimal("2.5")),
            (Decimal("0.5"), Decimal("0.75")),
            (Decimal("3.5"), Decimal("4.0"), Decimal("4.5")),
            (Decimal("0.10"), Decimal("0.25")),
            (2, 3),
            (Decimal("0.25"), Decimal("0.5")),
        ):
            if hard_dd <= warn_dd:
                continue
            result.append(
                RiskGovernor(
                    nas100_weight=nas,
                    sp500_weight=sp,
                    us30_weight=us,
                    warn_dd_r=warn_dd,
                    warn_multiplier=warn_mult,
                    hard_dd_r=hard_dd,
                    hard_multiplier=hard_mult,
                    loss_streak_trigger=trigger,
                    loss_streak_multiplier=streak_mult,
                )
            )
    return tuple(result)


def _governed_values(
    signals: Sequence[v6.CandidateSignal],
    outcomes: Sequence[r5.ManagedTrade],
    *,
    governor: RiskGovernor,
    stress: Decimal,
) -> tuple[tuple[Decimal, ...], dict[str, Any]]:
    equity = Decimal()
    peak = Decimal()
    loss_streak = 0
    values: list[Decimal] = []
    weights: list[Decimal] = []
    hard_mode_count = 0
    warn_mode_count = 0
    streak_mode_count = 0
    for signal, outcome in zip(signals, outcomes, strict=True):
        current_dd = peak - equity
        dd_multiplier = Decimal("1")
        if current_dd >= governor.hard_dd_r:
            dd_multiplier = governor.hard_multiplier
            hard_mode_count += 1
        elif current_dd >= governor.warn_dd_r:
            dd_multiplier = governor.warn_multiplier
            warn_mode_count += 1
        streak_multiplier = Decimal("1")
        if loss_streak >= governor.loss_streak_trigger:
            streak_multiplier = governor.loss_streak_multiplier
            streak_mode_count += 1
        weight = (
            governor.market_weight(signal.symbol)
            * min(dd_multiplier, streak_multiplier)
        )
        if weight <= 0:
            raise ValueError("risk governor may not skip a fixed trade")
        value = (outcome.r_multiple - stress) * weight
        values.append(value)
        weights.append(weight)
        equity += value
        peak = max(peak, equity)
        if value < 0:
            loss_streak += 1
        else:
            loss_streak = 0

    return tuple(values), {
        "minimum_weight_used": str(min(weights)),
        "maximum_weight_used": str(max(weights)),
        "mean_weight_used": str(sum(weights, Decimal()) / len(weights)),
        "warn_mode_trades": warn_mode_count,
        "hard_mode_trades": hard_mode_count,
        "loss_streak_mode_trades": streak_mode_count,
        "zero_weight_trades": sum(weight == 0 for weight in weights),
    }


def _governed_report(
    signals: Sequence[v6.CandidateSignal],
    outcomes: Sequence[r5.ManagedTrade],
    governor: RiskGovernor,
) -> dict[str, Any]:
    primary_values, primary_diag = _governed_values(
        signals,
        outcomes,
        governor=governor,
        stress=PRIMARY_STRESS,
    )
    secondary_values, secondary_diag = _governed_values(
        signals,
        outcomes,
        governor=governor,
        stress=SECONDARY_STRESS,
    )
    return {
        "primary": _basic_metrics(primary_values),
        "secondary": _basic_metrics(secondary_values),
        "primary_governor_diagnostics": primary_diag,
        "secondary_governor_diagnostics": secondary_diag,
    }


def _goal(row: dict[str, Any]) -> bool:
    raw = cast(dict[str, Any], row["raw"])
    governed = cast(dict[str, Any], row["governed"])
    rp = cast(dict[str, Any], raw["primary"])
    gp = cast(dict[str, Any], governed["primary"])
    gs = cast(dict[str, Any], governed["secondary"])
    diagnostics = cast(dict[str, Any], governed["primary_governor_diagnostics"])
    return (
        int(rp["sample"]) == FIXED_DENSITY
        and Decimal(str(rp["profit_factor"] or "0")) >= RAW_PF_FLOOR
        and Decimal(str(gp["profit_factor"] or "0")) >= GOVERNED_PF_GOAL
        and Decimal(str(gp["max_drawdown_r"])) <= GOVERNED_DD_GOAL
        and Decimal(str(gs["profit_factor"] or "0")) >= SECONDARY_PF_GOAL
        and Decimal(str(gs["max_drawdown_r"])) <= SECONDARY_DD_GOAL
        and int(diagnostics["zero_weight_trades"]) == 0
    )


def _final_rank(row: dict[str, Any]) -> tuple[int, Decimal, Decimal, Decimal]:
    governed = cast(dict[str, Any], row["governed"])
    gp = cast(dict[str, Any], governed["primary"])
    raw = cast(dict[str, Any], row["raw"])
    rp = cast(dict[str, Any], raw["primary"])
    return (
        int(_goal(row)),
        Decimal(str(gp["profit_factor"] or "0")),
        -Decimal(str(gp["max_drawdown_r"])),
        Decimal(str(rp["profit_factor"] or "0")),
    )


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {}
    opened_by_symbol: dict[str, tuple[datetime, ...]] = {}
    provenance: dict[str, Any] = {}
    for symbol in r1.SYMBOLS:
        bars, source = r2._load_cibo_m15_available(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        opened_by_symbol[symbol] = tuple(
            bar.opened_at.astimezone(UTC) for bar in bars
        )
        provenance[symbol] = source

    signals = r5._fixed_admissions(bars_by_symbol=bars_by_symbol)
    if len(signals) != FIXED_DENSITY:
        raise ValueError("fixed 657 density contract drift")

    policies, outcomes_by_policy = _policy_outcomes(
        signals,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
    )
    management_rows: list[dict[str, Any]] = []
    management_outcomes: dict[str, tuple[r5.ManagedTrade, ...]] = {}
    for management in _management_candidates(
        signals,
        outcomes_by_policy=outcomes_by_policy,
    ):
        outcomes = _outcomes_for_management(
            signals,
            management,
            outcomes_by_policy,
        )
        management_outcomes[management.management_id] = outcomes
        management_rows.append(
            {
                "management": management.payload(),
                "raw": _raw_report(signals, outcomes),
            }
        )
    management_rows.sort(key=_raw_rank, reverse=True)
    finalists = management_rows[:20]

    governors = _governor_grid()
    final_rows: list[dict[str, Any]] = []
    for management_row in finalists:
        management_payload = cast(dict[str, Any], management_row["management"])
        management_id = str(management_payload["management_id"])
        outcomes = management_outcomes[management_id]
        for governor in governors:
            row: dict[str, Any] = {
                "management": management_payload,
                "governor": governor.payload(),
                "raw": management_row["raw"],
                "governed": _governed_report(signals, outcomes, governor),
            }
            row["goal_pass"] = _goal(row)
            final_rows.append(row)

    final_rows.sort(key=_final_rank, reverse=True)
    goals = [row for row in final_rows if bool(row["goal_pass"])]
    best_raw = management_rows[0] if management_rows else None
    best = final_rows[0] if final_rows else None

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "window": {
            "window_id": r1.WINDOW_ID,
            "start_date": r1.START_DATE.isoformat(),
            "end_date_exclusive": r1.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_TUNING",
            "fresh_certification_holdout": False,
        },
        "fixed_admission_contract": {
            "sample": len(signals),
            "required_sample": FIXED_DENSITY,
            "entry_skips_allowed": False,
            "all_entries_preserved": len(signals) == FIXED_DENSITY,
        },
        "policy_count": len(policies),
        "management_candidate_count": len(management_rows),
        "governor_count": len(governors),
        "final_combination_count": len(final_rows),
        "owner_goal": {
            "raw_pf_floor": str(RAW_PF_FLOOR),
            "governed_pf_minimum": str(GOVERNED_PF_GOAL),
            "governed_max_drawdown_r": str(GOVERNED_DD_GOAL),
            "secondary_pf_minimum": str(SECONDARY_PF_GOAL),
            "secondary_max_drawdown_r": str(SECONDARY_DD_GOAL),
        },
        "goal_candidate_count": len(goals),
        "best_raw_management": best_raw,
        "best": best,
        "goal_candidates": goals[:20],
        "top_20": final_rows[:20],
        "provenance": provenance,
        "governance": {
            "research_only": True,
            "tuning_window_consumed": True,
            "fresh_holdout_claim": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "fixed_density": FIXED_DENSITY,
                "goal_candidate_count": report["goal_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
