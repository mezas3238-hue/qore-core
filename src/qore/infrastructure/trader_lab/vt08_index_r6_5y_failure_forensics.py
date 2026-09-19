"""VT08 Index R6 — five-year failure forensics.

Consumes the already-failed 2018-09-15..2023-09-15 R6 validation window to
identify causal failure concentrations. This is diagnostic evidence only.

No parameter search, no candidate promotion, no fresh-holdout claim.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_specialist_risk_round6 as r6
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round1 as r1
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as v5y
from qore.infrastructure.trader_lab import vt08_index_r6_governed_candidate_freeze as freeze
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r6_5y_failure_forensics.v1"
IDENTITY = "VT08_INDEX_R6_5Y_FAILURE_FORENSICS_001"
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")


@dataclass(frozen=True, slots=True)
class Admission:
    opportunity: r4.ExpandedOpportunity
    baseline_exit_at: datetime

    @property
    def signal(self) -> v6.CandidateSignal:
        return self.opportunity.signal


@dataclass(frozen=True, slots=True)
class GovernedTrace:
    value: Decimal
    weight: Decimal
    dd_before: Decimal
    loss_streak_before: int
    mode: str


def _admissions(
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[Admission, ...]:
    baseline_policy = r5.Policy(
        target_r=Decimal("2.5"),
        soft_close_loss_r=None,
        soft_close_until_mfe_r=None,
        deadline_bars=None,
        deadline_min_mfe_r=None,
        trail_name="OFF",
        trail_steps=(),
    )
    selected: list[Admission] = []
    for symbol in r1.SYMBOLS:
        bars = bars_by_symbol[symbol]
        opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)
        candidates: list[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]] = []
        for opportunity in v5y._build_surface_5y(symbol=symbol, bars=bars):
            outcome = r5._manage_trade(
                opportunity.signal,
                bars=bars,
                opened=opened,
                policy=baseline_policy,
            )
            candidates.append((opportunity, outcome))
        last_exit: datetime | None = None
        for opportunity, outcome in sorted(
            candidates,
            key=lambda item: item[0].signal.signal_at,
        ):
            signal = opportunity.signal
            if last_exit is not None and signal.signal_at < last_exit:
                continue
            selected.append(
                Admission(
                    opportunity=opportunity,
                    baseline_exit_at=outcome.exited_at,
                )
            )
            last_exit = outcome.exited_at
    selected.sort(key=lambda item: (item.signal.signal_at, item.signal.symbol))
    return tuple(selected)


def _managed(
    admissions: Sequence[Admission],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    opened_by_symbol: dict[str, tuple[datetime, ...]],
) -> tuple[r5.ManagedTrade, ...]:
    policy_map = v5y._frozen_policy_map()
    result: list[r5.ManagedTrade] = []
    for admission in admissions:
        signal = admission.signal
        policy = policy_map[f"{signal.symbol}:{signal.side.value}"]
        result.append(
            r5._manage_trade(
                signal,
                bars=bars_by_symbol[signal.symbol],
                opened=opened_by_symbol[signal.symbol],
                policy=policy,
            )
        )
    return tuple(result)


def _governor_trace(
    admissions: Sequence[Admission],
    outcomes: Sequence[r5.ManagedTrade],
    *,
    stress: Decimal,
) -> tuple[GovernedTrace, ...]:
    governor = v5y._frozen_governor()
    equity = Decimal()
    peak = Decimal()
    loss_streak = 0
    result: list[GovernedTrace] = []
    for admission, outcome in zip(admissions, outcomes, strict=True):
        signal = admission.signal
        dd_before = peak - equity
        dd_multiplier = Decimal("1")
        mode = "NORMAL"
        if dd_before >= governor.hard_dd_r:
            dd_multiplier = governor.hard_multiplier
            mode = "HARD_DD"
        elif dd_before >= governor.warn_dd_r:
            dd_multiplier = governor.warn_multiplier
            mode = "WARN_DD"

        streak_multiplier = Decimal("1")
        if loss_streak >= governor.loss_streak_trigger:
            streak_multiplier = governor.loss_streak_multiplier
            mode = f"{mode}+LOSS_STREAK" if mode != "NORMAL" else "LOSS_STREAK"

        weight = governor.market_weight(signal.symbol) * min(
            dd_multiplier,
            streak_multiplier,
        )
        value = (outcome.r_multiple - stress) * weight
        result.append(
            GovernedTrace(
                value=value,
                weight=weight,
                dd_before=dd_before,
                loss_streak_before=loss_streak,
                mode=mode,
            )
        )
        equity += value
        peak = max(peak, equity)
        if value < 0:
            loss_streak += 1
        else:
            loss_streak = 0
    return tuple(result)


def _metrics(values: Sequence[Decimal]) -> dict[str, Any]:
    return r6._basic_metrics(tuple(values))


def _breakdown(
    admissions: Sequence[Admission],
    raw_values: Sequence[Decimal],
    governed: Sequence[GovernedTrace],
    *,
    key_fn: Callable[[Admission], str],
) -> dict[str, Any]:
    labels = sorted({key_fn(item) for item in admissions})
    result: dict[str, Any] = {}
    for label in labels:
        indices = [
            index
            for index, item in enumerate(admissions)
            if key_fn(item) == label
        ]
        result[label] = {
            "sample": len(indices),
            "raw": _metrics(tuple(raw_values[index] for index in indices)),
            "governed": _metrics(
                tuple(governed[index].value for index in indices)
            ),
            "mean_weight": str(
                sum((governed[index].weight for index in indices), Decimal())
                / len(indices)
            ),
            "hard_mode_share": str(
                Decimal(
                    sum(
                        "HARD_DD" in governed[index].mode
                        for index in indices
                    )
                )
                / Decimal(len(indices))
            ),
        }
    return result


def _density_attribution(admissions: Sequence[Admission]) -> dict[str, Any]:
    rearm_counts: dict[str, int] = defaultdict(int)
    poi_counts: dict[str, int] = defaultdict(int)
    poi_rearm_counts: dict[str, int] = defaultdict(int)
    for item in admissions:
        rearm = int(item.opportunity.rearm_index)
        rearm_label = "initial" if rearm == 0 else f"rearm_{rearm}"
        rearm_counts[rearm_label] += 1
        poi = str(item.opportunity.source_poi_kind)
        poi_counts[poi] += 1
        poi_rearm_counts[f"{poi}:{'initial' if rearm == 0 else 'rearm'}"] += 1
    rearm_trade_count = sum(
        count for label, count in rearm_counts.items() if label != "initial"
    )
    return {
        "total": len(admissions),
        "initial_trade_count": rearm_counts.get("initial", 0),
        "rearm_trade_count": rearm_trade_count,
        "rearm_share": str(
            Decimal(rearm_trade_count) / Decimal(len(admissions))
            if admissions
            else Decimal()
        ),
        "by_rearm_index": dict(sorted(rearm_counts.items())),
        "by_poi": dict(sorted(poi_counts.items())),
        "by_poi_rearm": dict(sorted(poi_rearm_counts.items())),
    }


def _governor_lock_in(
    admissions: Sequence[Admission],
    trace: Sequence[GovernedTrace],
) -> dict[str, Any]:
    hard_indices = [
        index for index, item in enumerate(trace) if "HARD_DD" in item.mode
    ]
    normal = sum(item.mode == "NORMAL" for item in trace)
    warn = sum("WARN_DD" in item.mode for item in trace)
    hard = len(hard_indices)
    streak = sum("LOSS_STREAK" in item.mode for item in trace)
    first_hard = hard_indices[0] if hard_indices else None
    by_year: dict[str, dict[str, int]] = defaultdict(
        lambda: {"sample": 0, "hard": 0, "warn": 0, "streak": 0}
    )
    for admission, item in zip(admissions, trace, strict=True):
        year = str(admission.signal.signal_at.astimezone(v5y._NY).year)
        row = by_year[year]
        row["sample"] += 1
        row["hard"] += int("HARD_DD" in item.mode)
        row["warn"] += int("WARN_DD" in item.mode)
        row["streak"] += int("LOSS_STREAK" in item.mode)
    return {
        "normal_mode_trades": normal,
        "warn_mode_trades": warn,
        "hard_mode_trades": hard,
        "loss_streak_mode_trades": streak,
        "first_hard_trade_index": first_hard,
        "first_hard_signal_at": (
            admissions[first_hard].signal.signal_at.astimezone(UTC).isoformat()
            if first_hard is not None
            else None
        ),
        "hard_mode_share": str(
            Decimal(hard) / Decimal(len(trace)) if trace else Decimal()
        ),
        "by_year": dict(sorted(by_year.items())),
    }


def _root_cause_flags(
    *,
    admissions: Sequence[Admission],
    raw_values: Sequence[Decimal],
    primary_trace: Sequence[GovernedTrace],
    density: dict[str, Any],
) -> list[dict[str, Any]]:
    raw = _metrics(raw_values)
    flags: list[dict[str, Any]] = []
    if Decimal(str(raw["profit_factor"] or "0")) < Decimal("1"):
        flags.append(
            {
                "id": "NEGATIVE_RAW_EXPECTANCY",
                "severity": "CRITICAL",
                "evidence": {
                    "profit_factor": raw["profit_factor"],
                    "max_drawdown_r": raw["max_drawdown_r"],
                    "total_r": raw["total_r"],
                },
                "interpretation": (
                    "The frozen management has negative expectancy before "
                    "portfolio risk scaling. Risk sizing cannot repair this."
                ),
            }
        )
    hard_share = (
        Decimal(
            sum("HARD_DD" in item.mode for item in primary_trace)
        )
        / Decimal(len(primary_trace))
        if primary_trace
        else Decimal()
    )
    if hard_share >= Decimal("0.50"):
        flags.append(
            {
                "id": "GOVERNOR_HARD_MODE_LOCK_IN",
                "severity": "CRITICAL",
                "evidence": {"hard_mode_share": str(hard_share)},
                "interpretation": (
                    "The governor spends most of the validation in hard-DD "
                    "defense, indicating persistent rather than episodic risk."
                ),
            }
        )
    if len(admissions) > v5y.MAX_TRADES:
        flags.append(
            {
                "id": "DENSITY_OVERSHOOT",
                "severity": "HIGH",
                "evidence": {
                    "actual": len(admissions),
                    "maximum_contract": v5y.MAX_TRADES,
                    "overshoot": len(admissions) - v5y.MAX_TRADES,
                    "rearm_trade_count": density["rearm_trade_count"],
                    "rearm_share": density["rearm_share"],
                },
                "interpretation": (
                    "The opportunity generator is denser than the 5Y contract; "
                    "rearm contribution must be diagnosed structurally."
                ),
            }
        )
    return flags


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
        bars, source = v5y._load_cibo_m15_5y(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        opened_by_symbol[symbol] = tuple(
            bar.opened_at.astimezone(UTC) for bar in bars
        )
        provenance[symbol] = source

    admissions = _admissions(bars_by_symbol=bars_by_symbol)
    outcomes = _managed(
        admissions,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
    )
    raw_primary = tuple(
        outcome.r_multiple - PRIMARY_STRESS for outcome in outcomes
    )
    raw_secondary = tuple(
        outcome.r_multiple - SECONDARY_STRESS for outcome in outcomes
    )
    governed_primary = _governor_trace(
        admissions,
        outcomes,
        stress=PRIMARY_STRESS,
    )
    governed_secondary = _governor_trace(
        admissions,
        outcomes,
        stress=SECONDARY_STRESS,
    )

    density = _density_attribution(admissions)
    breakdowns = {
        "market": _breakdown(
            admissions,
            raw_primary,
            governed_primary,
            key_fn=lambda item: item.signal.symbol,
        ),
        "side": _breakdown(
            admissions,
            raw_primary,
            governed_primary,
            key_fn=lambda item: item.signal.side.value,
        ),
        "market_side": _breakdown(
            admissions,
            raw_primary,
            governed_primary,
            key_fn=lambda item: f"{item.signal.symbol}:{item.signal.side.value}",
        ),
        "anchor": _breakdown(
            admissions,
            raw_primary,
            governed_primary,
            key_fn=lambda item: str(
                item.signal.h4_opened_at.astimezone(v5y._NY).hour
            ),
        ),
        "poi": _breakdown(
            admissions,
            raw_primary,
            governed_primary,
            key_fn=lambda item: str(item.opportunity.source_poi_kind),
        ),
        "rearm": _breakdown(
            admissions,
            raw_primary,
            governed_primary,
            key_fn=lambda item: (
                "initial"
                if int(item.opportunity.rearm_index) == 0
                else "rearm"
            ),
        ),
        "model_kind": _breakdown(
            admissions,
            raw_primary,
            governed_primary,
            key_fn=lambda item: item.signal.model_kind.value,
        ),
        "year": _breakdown(
            admissions,
            raw_primary,
            governed_primary,
            key_fn=lambda item: str(
                item.signal.signal_at.astimezone(v5y._NY).year
            ),
        ),
    }

    management_cells = breakdowns["market_side"]
    for cell, row in management_cells.items():
        payload = cast(
            dict[str, object],
            freeze.MANAGEMENT_BY_CELL[cell],
        )
        row["frozen_policy_id"] = str(payload["policy_id"])

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": freeze.CANDIDATE_ID,
            "rule_fingerprint": freeze.RULE_FINGERPRINT,
            "five_year_source_run": 35338881818,
            "five_year_source_artifact": 10544202618,
        },
        "window": {
            "start_date": v5y.START_DATE.isoformat(),
            "end_date_exclusive": v5y.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_FAILURE_FORENSICS",
            "fresh_certification_holdout": False,
        },
        "sample": len(admissions),
        "raw_primary": _metrics(raw_primary),
        "raw_secondary": _metrics(raw_secondary),
        "governed_primary": _metrics(
            tuple(item.value for item in governed_primary)
        ),
        "governed_secondary": _metrics(
            tuple(item.value for item in governed_secondary)
        ),
        "density_attribution": density,
        "governor_lock_in_primary": _governor_lock_in(
            admissions,
            governed_primary,
        ),
        "governor_lock_in_secondary": _governor_lock_in(
            admissions,
            governed_secondary,
        ),
        "breakdowns": breakdowns,
        "root_cause_flags": _root_cause_flags(
            admissions=admissions,
            raw_values=raw_primary,
            primary_trace=governed_primary,
            density=density,
        ),
        "provenance": provenance,
        "governance": {
            "forensics_only": True,
            "window_consumed": True,
            "parameter_search": False,
            "candidate_promotion": False,
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
                "sample": report["sample"],
                "density_attribution": report["density_attribution"],
                "governor_lock_in_primary": report["governor_lock_in_primary"],
                "root_cause_flags": report["root_cause_flags"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
