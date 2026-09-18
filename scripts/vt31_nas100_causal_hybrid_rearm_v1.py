"""VT31 NAS100 causal hybrid + structural rearm V1.

Consumed-evidence tuning only.

This lab preserves WAIT_1025_B060 as the first-position architecture and adds
at most one genuinely new post-exit source event per day.

The first position keeps the exact causal hybrid capital semantics:
- CORE 1.00R;
- SECONDARY 0.05R;
- SCOUT 0.02R;
- monthly alternate budget 0.60R.

A rearm requires a new raid + confirmation + decision strictly after the first
terminal exit. Rearm exposure is modulated by a pre-entry causal quality score.
Weak rearms are not fabricated or duplicated; they are genuine trades with
smaller requested exposure. QORE Risk remains sovereign.

No fresh holdout is opened and no policy is promoted here.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_causal_hybrid_density_v2 as hybrid
import vt31_nas100_high_density_structural_protection_v1 as protection
import vt31_nas100_specialist_r1_candidate as specialist
import vt31_nas100_structural_rearm_density_frontier_v1 as frontier
import vt31_nas100_structural_rearm_quality_frontier_v1 as quality

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    structurally_rearmed,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutionPolicy,
)

SCHEMA = "qore.vt31.nas100.causal_hybrid_rearm.v1"
IDENTITY = "VT31_NAS100_CAUSAL_HYBRID_REARM_V1"
MARKET = "NAS100"
BASE_VARIANT = "WAIT_1025_B060"
WAIT_RELEASE_MINUTE = 10 * 60 + 25
MONTHLY_ALT_BUDGET = Decimal("0.60")
FRICTION = Decimal("0.05")

RISK_PROFILES: dict[str, dict[str, Decimal]] = {
    "REARM_CONSERVATIVE": {
        "HIGH": Decimal("0.10"),
        "MID": Decimal("0.05"),
        "LOW": Decimal("0.02"),
    },
    "REARM_BALANCED": {
        "HIGH": Decimal("0.20"),
        "MID": Decimal("0.08"),
        "LOW": Decimal("0.03"),
    },
    "REARM_ASSERTIVE": {
        "HIGH": Decimal("0.30"),
        "MID": Decimal("0.10"),
        "LOW": Decimal("0.05"),
    },
}
MANAGEMENT_MODES = ("BASELINE_REARM", "SCORE_PROTECT")
REARM_MONTHLY_BUDGETS = (
    Decimal("0.10"),
    Decimal("0.12"),
    Decimal("0.15"),
    Decimal("0.18"),
    Decimal("0.20"),
    Decimal("0.25"),
    Decimal("0.30"),
)
ADAPTIVE_REARM_BUDGET_PROFILES: dict[str, dict[str, object]] = {
    "ACTIVITY_A": {
        "sparse_max": 9,
        "balanced_max": 11,
        "sparse_budget": Decimal("0.25"),
        "balanced_budget": Decimal("0.18"),
        "dense_budget": Decimal("0.10"),
    },
    "ACTIVITY_B": {
        "sparse_max": 9,
        "balanced_max": 11,
        "sparse_budget": Decimal("0.30"),
        "balanced_budget": Decimal("0.20"),
        "dense_budget": Decimal("0.10"),
    },
    "ACTIVITY_C": {
        "sparse_max": 8,
        "balanced_max": 10,
        "sparse_budget": Decimal("0.30"),
        "balanced_budget": Decimal("0.20"),
        "dense_budget": Decimal("0.10"),
    },
    "ACTIVITY_D": {
        "sparse_max": 10,
        "balanced_max": 12,
        "sparse_budget": Decimal("0.25"),
        "balanced_budget": Decimal("0.15"),
        "dense_budget": Decimal("0.08"),
    },
    "ACTIVITY_E": {
        "sparse_max": 8,
        "balanced_max": 10,
        "sparse_budget": Decimal("0.30"),
        "balanced_budget": Decimal("0.20"),
        "dense_budget": Decimal("0.08"),
    },
    "ACTIVITY_F": {
        "sparse_max": 8,
        "balanced_max": 10,
        "sparse_budget": Decimal("0.30"),
        "balanced_budget": Decimal("0.20"),
        "dense_budget": Decimal("0.06"),
    },
    "ACTIVITY_G": {
        "sparse_max": 8,
        "balanced_max": 10,
        "sparse_budget": Decimal("0.25"),
        "balanced_budget": Decimal("0.18"),
        "dense_budget": Decimal("0.08"),
    },
    "ACTIVITY_H": {
        "sparse_max": 8,
        "balanced_max": 10,
        "sparse_budget": Decimal("0.30"),
        "balanced_budget": Decimal("0.20"),
        "dense_budget": Decimal("0.04"),
    },
    "ACTIVITY_I": {
        "sparse_max": 8,
        "balanced_max": 10,
        "sparse_budget": Decimal("0.30"),
        "balanced_budget": Decimal("0.20"),
        "dense_budget": Decimal("0.03"),
    },
    "ACTIVITY_J": {
        "sparse_max": 8,
        "balanced_max": 10,
        "sparse_budget": Decimal("0.30"),
        "balanced_budget": Decimal("0.20"),
        "dense_budget": Decimal("0.02"),
    },
    "ACTIVITY_K": {
        "sparse_max": 8,
        "balanced_max": 10,
        "sparse_budget": Decimal("0.30"),
        "balanced_budget": Decimal("0.18"),
        "dense_budget": Decimal("0.04"),
    },
    "ACTIVITY_L": {
        "sparse_max": 8,
        "balanced_max": 10,
        "sparse_budget": Decimal("0.30"),
        "balanced_budget": Decimal("0.17"),
        "dense_budget": Decimal("0.04"),
    },
    "ACTIVITY_M": {
        "sparse_max": 8,
        "balanced_max": 10,
        "sparse_budget": Decimal("0.30"),
        "balanced_budget": Decimal("0.16"),
        "dense_budget": Decimal("0.04"),
    },
}

GLOBAL_RISK_SCALARS = (
    Decimal("0.75"),
    Decimal("0.70"),
    Decimal("0.68"),
    Decimal("0.65"),
    Decimal("0.62"),
    Decimal("0.60"),
)
DD6_FRONTIER_ONLY = os.getenv("QORE_DD6_FRONTIER_ONLY") == "1"
DD6_FRONTIER_PROFILES = {"ACTIVITY_K", "ACTIVITY_L", "ACTIVITY_M"}
DD6_FRONTIER_SCALARS = (Decimal("0.62"), Decimal("0.60"))
EVAL_START_DATE = (
    date.fromisoformat(os.environ["QORE_EVAL_START_DATE"])
    if os.environ.get("QORE_EVAL_START_DATE")
    else None
)
EVAL_END_EXCLUSIVE_DATE = (
    date.fromisoformat(os.environ["QORE_EVAL_END_EXCLUSIVE_DATE"])
    if os.environ.get("QORE_EVAL_END_EXCLUSIVE_DATE")
    else None
)
INCLUDE_TRADE_ROWS = os.getenv("QORE_INCLUDE_TRADE_ROWS") == "1"
FIXED_ACTIVITY_PROFILE = os.getenv("QORE_FIXED_ACTIVITY_PROFILE")
FIXED_GLOBAL_RISK_SCALAR = (
    Decimal(os.environ["QORE_FIXED_GLOBAL_RISK_SCALAR"])
    if os.environ.get("QORE_FIXED_GLOBAL_RISK_SCALAR")
    else None
)


def _inside_eval_window(local_day: date) -> bool:
    if EVAL_START_DATE is not None and local_day < EVAL_START_DATE:
        return False
    if (
        EVAL_END_EXCLUSIVE_DATE is not None
        and local_day >= EVAL_END_EXCLUSIVE_DATE
    ):
        return False
    return True



def _risk_class(score: int) -> str:
    if score >= 5:
        return "HIGH"
    if score >= 3:
        return "MID"
    return "LOW"


def _weighted_rearm(
    outcome: dict[str, object],
    *,
    risk: Decimal,
    score: int,
    risk_class: str,
    mode: str,
) -> dict[str, object]:
    gross = Decimal(cast(str, outcome["r_multiple"]))
    net = risk * (gross - FRICTION)
    row = dict(outcome)
    row.update(
        {
            "tier": "REARM",
            "requested_risk_r": format(risk, "f"),
            "capital_weighted_net_r": format(net, "f"),
            "rearm_quality_score": score,
            "rearm_risk_class": risk_class,
            "rearm_management_mode": mode,
            "authorization_reason": (
                "NEW_RAID_CONFIRMATION_DECISION_AFTER_TERMINAL_EXIT"
            ),
        }
    )
    return row


def _capital_metrics(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    converted = [
        {**row, "r_multiple": row["capital_weighted_net_r"]}
        for row in rows
    ]
    return _metrics(converted, friction=Decimal(0))


def _scale_capital_rows(
    rows: list[dict[str, object]],
    *,
    scalar: Decimal,
) -> list[dict[str, object]]:
    scaled: list[dict[str, object]] = []
    for row in rows:
        updated = dict(row)
        updated["capital_weighted_net_r"] = format(
            Decimal(cast(str, row["capital_weighted_net_r"])) * scalar,
            "f",
        )
        if "requested_risk_r" in row:
            updated["requested_risk_r"] = format(
                Decimal(cast(str, row["requested_risk_r"])) * scalar,
                "f",
            )
        updated["global_risk_scalar"] = format(scalar, "f")
        scaled.append(updated)
    return scaled


def _budgeted_rearm_rows(
    raw_rows: list[dict[str, object]],
    *,
    risk_map: dict[str, Decimal],
    monthly_budget: Decimal,
    mode: str,
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    """Authorize rearms chronologically from a causal monthly capital budget."""
    selected: list[dict[str, object]] = []
    ledger: dict[str, dict[str, object]] = {}

    for raw_row in sorted(
        raw_rows,
        key=lambda row: cast(str, row["signal_at"]),
    ):
        month = cast(str, raw_row["local_date"])[:7]
        if month not in ledger:
            ledger[month] = {
                "opening_budget_r": format(monthly_budget, "f"),
                "authorized_count": 0,
                "budget_denied_count": 0,
                "remaining_budget_r": format(monthly_budget, "f"),
            }

        risk_class = cast(str, raw_row["rearm_risk_class"])
        risk = risk_map[risk_class]
        remaining = Decimal(
            cast(str, ledger[month]["remaining_budget_r"])
        )
        if risk > remaining:
            ledger[month]["budget_denied_count"] = (
                int(ledger[month]["budget_denied_count"]) + 1
            )
            continue

        selected.append(
            _weighted_rearm(
                raw_row,
                risk=risk,
                score=int(cast(int, raw_row["rearm_quality_score"])),
                risk_class=risk_class,
                mode=mode,
            )
        )
        remaining -= risk
        ledger[month]["authorized_count"] = (
            int(ledger[month]["authorized_count"]) + 1
        )
        ledger[month]["remaining_budget_r"] = format(remaining, "f")

    return selected, ledger


def _previous_month(month: str) -> str:
    year_text, month_text = month.split("-")
    year = int(year_text)
    value = int(month_text)
    if value == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{value - 1:02d}"


def _adaptive_budgeted_rearm_rows(
    raw_rows: list[dict[str, object]],
    *,
    risk_map: dict[str, Decimal],
    first_rows: list[dict[str, object]],
    profile: dict[str, object],
    mode: str,
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    """Allocate this month's rearm capital from prior-month base activity."""
    base_counts: Counter[str] = Counter(
        cast(str, row["local_date"])[:7]
        for row in first_rows
    )
    selected: list[dict[str, object]] = []
    ledger: dict[str, dict[str, object]] = {}

    sparse_max = int(cast(int, profile["sparse_max"]))
    balanced_max = int(cast(int, profile["balanced_max"]))
    sparse_budget = cast(Decimal, profile["sparse_budget"])
    balanced_budget = cast(Decimal, profile["balanced_budget"])
    dense_budget = cast(Decimal, profile["dense_budget"])

    for raw_row in sorted(
        raw_rows,
        key=lambda row: cast(str, row["signal_at"]),
    ):
        month = cast(str, raw_row["local_date"])[:7]
        if month not in ledger:
            prior_month = _previous_month(month)
            prior_base_count = base_counts.get(prior_month, 0)
            if prior_base_count <= sparse_max:
                budget = sparse_budget
                activity_state = "SPARSE"
            elif prior_base_count <= balanced_max:
                budget = balanced_budget
                activity_state = "BALANCED"
            else:
                budget = dense_budget
                activity_state = "DENSE"
            ledger[month] = {
                "prior_month": prior_month,
                "prior_month_base_trade_count": prior_base_count,
                "activity_state": activity_state,
                "opening_budget_r": format(budget, "f"),
                "authorized_count": 0,
                "budget_denied_count": 0,
                "remaining_budget_r": format(budget, "f"),
            }

        risk_class = cast(str, raw_row["rearm_risk_class"])
        risk = risk_map[risk_class]
        remaining = Decimal(
            cast(str, ledger[month]["remaining_budget_r"])
        )
        if risk > remaining:
            ledger[month]["budget_denied_count"] = (
                int(ledger[month]["budget_denied_count"]) + 1
            )
            continue

        selected.append(
            _weighted_rearm(
                raw_row,
                risk=risk,
                score=int(cast(int, raw_row["rearm_quality_score"])),
                risk_class=risk_class,
                mode=mode,
            )
        )
        remaining -= risk
        ledger[month]["authorized_count"] = (
            int(ledger[month]["authorized_count"]) + 1
        )
        ledger[month]["remaining_budget_r"] = format(remaining, "f")

    return selected, ledger


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
            "p99_max_drawdown_r": "0",
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
        "p99_max_drawdown_r": format(
            drawdowns[(len(drawdowns) - 1) * 99 // 100],
            "f",
        ),
    }


def replay(
    evidence_path: Path,
    *,
    partition: str,
) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("causal hybrid rearm requires NAS100")

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

    first_report = hybrid._run_variant(
        by_day,
        context_by_day,
        evidence=evidence,
        wait_release_minute=WAIT_RELEASE_MINUTE,
        monthly_alt_budget=MONTHLY_ALT_BUDGET,
        variant=BASE_VARIANT,
    )
    all_first_rows = [
        dict(row)
        for row in cast(
            list[dict[str, object]],
            first_report["trades"],
        )
    ]
    first_rows = [
        row
        for row in all_first_rows
        if _inside_eval_window(
            date.fromisoformat(cast(str, row["local_date"]))
        )
    ]
    first_by_day = {
        date.fromisoformat(cast(str, row["local_date"])): row
        for row in first_rows
    }

    policy = Vt31R22ExecutionPolicy()
    rearm_raw_by_mode: dict[str, list[dict[str, object]]] = {
        mode: [] for mode in MANAGEMENT_MODES
    }
    status: Counter[str] = Counter()
    quality_counts: Counter[int] = Counter()

    for local_day, first_row in sorted(first_by_day.items()):
        exit_at = datetime.fromisoformat(
            cast(str, first_row["exit_at"])
        )
        if exit_at.tzinfo is None:
            raise ValueError("first terminal exit must be timezone-aware")
        if _wall(exit_at) >= (11, 0, 0):
            status["first-exit-after-source-window"] += 1
            continue

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
            status["rearm-incomplete-day"] += 1
            continue

        selected = frontier._next_executable_after(
            reference=reference,
            session=session,
            after_at=exit_at,
            evidence=evidence,
            policy=policy,
        )
        if selected is None:
            status["no-post-exit-source"] += 1
            continue
        source, setup = selected
        if not structurally_rearmed(
            protected_exit_at_epoch=int(exit_at.timestamp()),
            new_raid_at_epoch=int(source.structure.raid_at.timestamp()),
            new_confirmation_at_epoch=int(
                source.structure.confirmation_at.timestamp()
            ),
            new_decision_at_epoch=int(setup.decision_at.timestamp()),
        ):
            status["rearm-invariant-failed"] += 1
            continue

        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        ) = context_by_day[local_day]
        observation_at = setup.decision_at
        session_prefix = tuple(
            bar
            for bar in session
            if cast(datetime, getattr(bar, "closed_at"))
            <= observation_at
        )
        state = specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            session_prefix,
            source,
            setup,
            observation_at,
        )
        score, reasons = quality._quality_score(state, setup)
        quality_counts[score] += 1
        risk_class = _risk_class(score)

        baseline_outcome = specialist.baseline._simulate(
            day_bars,
            setup,
        )
        protected_outcome = (
            protection._simulate_single_structural_trail(
                day_bars,
                setup,
                required_confirmations=(
                    1 if score < 5 else None
                ),
            )
        )
        outcomes = {
            "BASELINE_REARM": baseline_outcome,
            "SCORE_PROTECT": protected_outcome,
        }

        for mode, outcome in outcomes.items():
            status[f"{mode}:{outcome['status']}"] += 1
            if outcome.get("status") != "terminal":
                continue
            row = dict(outcome)
            row.update(
                {
                    "local_date": local_day.isoformat(),
                    "rearm_quality_score": score,
                    "rearm_quality_reasons": list(reasons),
                    "rearm_risk_class": risk_class,
                    "first_tier": first_row["tier"],
                    "first_exit_reason": first_row.get(
                        "exit_reason"
                    ),
                    "first_requested_risk_r": first_row[
                        "requested_risk_r"
                    ],
                    "used_for_runtime_decision": False,
                }
            )
            rearm_raw_by_mode[mode].append(row)

    variants: dict[str, object] = {}
    for profile_name, risk_map in (
        () if DD6_FRONTIER_ONLY else RISK_PROFILES.items()
    ):
        for mode in MANAGEMENT_MODES:
            rearm_rows = []
            for raw_row in rearm_raw_by_mode[mode]:
                risk_class = cast(
                    str,
                    raw_row["rearm_risk_class"],
                )
                rearm_rows.append(
                    _weighted_rearm(
                        raw_row,
                        risk=risk_map[risk_class],
                        score=int(
                            cast(
                                int,
                                raw_row["rearm_quality_score"],
                            )
                        ),
                        risk_class=risk_class,
                        mode=mode,
                    )
                )
            combined = sorted(
                [*first_rows, *rearm_rows],
                key=lambda row: cast(str, row["signal_at"]),
            )
            variant = f"{profile_name}_{mode}"
            metrics = _capital_metrics(combined)
            mc = _monte_carlo(combined, variant=variant)
            trade_count = len(combined)
            variants[variant] = {
                "trade_count": trade_count,
                "base_trade_count": len(first_rows),
                "rearm_trade_count": len(rearm_rows),
                "metrics": metrics,
                "monte_carlo": mc,
                "density": {
                    "at_least_300": trade_count >= 300,
                    "inside_300_350": 300 <= trade_count <= 350,
                },
                "development_objectives": {
                    "density_300_350": 300 <= trade_count <= 350,
                    "profit_factor_at_least_2": (
                        metrics["profit_factor"] is not None
                        and Decimal(
                            cast(str, metrics["profit_factor"])
                        )
                        >= Decimal("2")
                    ),
                    "observed_dd_at_most_10r": (
                        Decimal(
                            cast(str, metrics["max_drawdown_r"])
                        )
                        <= Decimal("10")
                    ),
                    "stretch_observed_dd_at_most_5r": (
                        Decimal(
                            cast(str, metrics["max_drawdown_r"])
                        )
                        <= Decimal("5")
                    ),
                    "mc_positive_at_least_0_90": (
                        Decimal(
                            cast(
                                str,
                                mc[
                                    "positive_terminal_probability"
                                ],
                            )
                        )
                        >= Decimal("0.90")
                    ),
                    "mc_p95_dd_at_most_15r": (
                        Decimal(
                            cast(str, mc["p95_max_drawdown_r"])
                        )
                        <= Decimal("15")
                    ),
                },
            }

    conservative = RISK_PROFILES["REARM_CONSERVATIVE"]
    for monthly_budget in (
        () if DD6_FRONTIER_ONLY else REARM_MONTHLY_BUDGETS
    ):
        mode = "SCORE_PROTECT"
        rearm_rows, budget_ledger = _budgeted_rearm_rows(
            rearm_raw_by_mode[mode],
            risk_map=conservative,
            monthly_budget=monthly_budget,
            mode=mode,
        )
        combined = sorted(
            [*first_rows, *rearm_rows],
            key=lambda row: cast(str, row["signal_at"]),
        )
        budget_tag = format(monthly_budget, "f").replace(".", "")
        variant = (
            "REARM_CONSERVATIVE_SCORE_PROTECT_"
            f"MONTHLY_BUDGET_{budget_tag}"
        )
        metrics = _capital_metrics(combined)
        mc = _monte_carlo(combined, variant=variant)
        trade_count = len(combined)
        variants[variant] = {
            "trade_count": trade_count,
            "base_trade_count": len(first_rows),
            "rearm_trade_count": len(rearm_rows),
            "metrics": metrics,
            "monte_carlo": mc,
            "monthly_rearm_budget_r": format(monthly_budget, "f"),
            "monthly_budget_ledger": budget_ledger,
            "density": {
                "at_least_300": trade_count >= 300,
                "inside_300_350": 300 <= trade_count <= 350,
            },
            "development_objectives": {
                "density_300_350": 300 <= trade_count <= 350,
                "profit_factor_at_least_2": (
                    metrics["profit_factor"] is not None
                    and Decimal(cast(str, metrics["profit_factor"]))
                    >= Decimal("2")
                ),
                "observed_dd_at_most_10r": (
                    Decimal(cast(str, metrics["max_drawdown_r"]))
                    <= Decimal("10")
                ),
                "stretch_observed_dd_at_most_5r": (
                    Decimal(cast(str, metrics["max_drawdown_r"]))
                    <= Decimal("5")
                ),
                "mc_positive_at_least_0_90": (
                    Decimal(
                        cast(str, mc["positive_terminal_probability"])
                    )
                    >= Decimal("0.90")
                ),
                "mc_p95_dd_at_most_15r": (
                    Decimal(cast(str, mc["p95_max_drawdown_r"]))
                    <= Decimal("15")
                ),
            },
        }

    if FIXED_ACTIVITY_PROFILE is not None:
        if FIXED_ACTIVITY_PROFILE not in ADAPTIVE_REARM_BUDGET_PROFILES:
            raise ValueError("unknown fixed activity profile")
        adaptive_items = (
            (
                FIXED_ACTIVITY_PROFILE,
                ADAPTIVE_REARM_BUDGET_PROFILES[FIXED_ACTIVITY_PROFILE],
            ),
        )
    else:
        adaptive_items = (
            (
                (name, profile)
                for name, profile in ADAPTIVE_REARM_BUDGET_PROFILES.items()
                if name in DD6_FRONTIER_PROFILES
            )
            if DD6_FRONTIER_ONLY
            else ADAPTIVE_REARM_BUDGET_PROFILES.items()
        )
    for profile_name, profile in adaptive_items:
        mode = "SCORE_PROTECT"
        rearm_rows, activity_ledger = _adaptive_budgeted_rearm_rows(
            rearm_raw_by_mode[mode],
            risk_map=RISK_PROFILES["REARM_CONSERVATIVE"],
            first_rows=all_first_rows,
            profile=profile,
            mode=mode,
        )
        combined = sorted(
            [*first_rows, *rearm_rows],
            key=lambda row: cast(str, row["signal_at"]),
        )
        variant = f"REARM_ADAPTIVE_{profile_name}_SCORE_PROTECT"
        metrics = _capital_metrics(combined)
        mc = _monte_carlo(combined, variant=variant)
        trade_count = len(combined)
        variants[variant] = {
            "trade_count": trade_count,
            "base_trade_count": len(first_rows),
            "rearm_trade_count": len(rearm_rows),
            "metrics": metrics,
            "monte_carlo": mc,
            "activity_budget_profile": {
                key: (
                    format(value, "f")
                    if isinstance(value, Decimal)
                    else value
                )
                for key, value in profile.items()
            },
            "monthly_activity_budget_ledger": activity_ledger,
            "density": {
                "at_least_300": trade_count >= 300,
                "inside_300_350": 300 <= trade_count <= 350,
            },
            "development_objectives": {
                "density_300_350": 300 <= trade_count <= 350,
                "profit_factor_at_least_2": (
                    metrics["profit_factor"] is not None
                    and Decimal(cast(str, metrics["profit_factor"]))
                    >= Decimal("2")
                ),
                "observed_dd_at_most_10r": (
                    Decimal(cast(str, metrics["max_drawdown_r"]))
                    <= Decimal("10")
                ),
                "observed_dd_at_most_6r": (
                    Decimal(cast(str, metrics["max_drawdown_r"]))
                    <= Decimal("6")
                ),
                "stretch_observed_dd_at_most_5r": (
                    Decimal(cast(str, metrics["max_drawdown_r"]))
                    <= Decimal("5")
                ),
                "mc_positive_at_least_0_90": (
                    Decimal(
                        cast(str, mc["positive_terminal_probability"])
                    )
                    >= Decimal("0.90")
                ),
                "mc_p95_dd_at_most_15r": (
                    Decimal(cast(str, mc["p95_max_drawdown_r"]))
                    <= Decimal("15")
                ),
            },
        }

        if profile_name in {"ACTIVITY_K", "ACTIVITY_L", "ACTIVITY_M"}:
            if FIXED_GLOBAL_RISK_SCALAR is not None:
                scalars = (FIXED_GLOBAL_RISK_SCALAR,)
            else:
                scalars = (
                    DD6_FRONTIER_SCALARS
                    if DD6_FRONTIER_ONLY
                    else GLOBAL_RISK_SCALARS
                )
            for scalar in scalars:
                scaled = _scale_capital_rows(combined, scalar=scalar)
                scalar_tag = format(scalar, "f").replace(".", "")
                scaled_variant = (
                    f"REARM_ADAPTIVE_{profile_name}_SCORE_PROTECT_"
                    f"RISK_SCALAR_{scalar_tag}"
                )
                scaled_metrics = _capital_metrics(scaled)
                scaled_mc = _monte_carlo(
                    scaled,
                    variant=scaled_variant,
                )
                variants[scaled_variant] = {
                    "trade_count": trade_count,
                    "base_trade_count": len(first_rows),
                    "rearm_trade_count": len(rearm_rows),
                    "metrics": scaled_metrics,
                    "monte_carlo": scaled_mc,
                    "trade_rows": scaled if INCLUDE_TRADE_ROWS else [],
                    "global_risk_scalar": format(scalar, "f"),
                    "activity_budget_profile": {
                        key: (
                            format(value, "f")
                            if isinstance(value, Decimal)
                            else value
                        )
                        for key, value in profile.items()
                    },
                    "monthly_activity_budget_ledger": activity_ledger,
                    "density": {
                        "at_least_300": trade_count >= 300,
                        "inside_300_350": 300 <= trade_count <= 350,
                    },
                    "development_objectives": {
                        "density_300_350": 300 <= trade_count <= 350,
                        "profit_factor_at_least_2": (
                            scaled_metrics["profit_factor"] is not None
                            and Decimal(
                                cast(
                                    str,
                                    scaled_metrics["profit_factor"],
                                )
                            )
                            >= Decimal("2")
                        ),
                        "observed_dd_at_most_10r": (
                            Decimal(
                                cast(
                                    str,
                                    scaled_metrics["max_drawdown_r"],
                                )
                            )
                            <= Decimal("10")
                        ),
                        "observed_dd_at_most_6r": (
                            Decimal(
                                cast(
                                    str,
                                    scaled_metrics["max_drawdown_r"],
                                )
                            )
                            <= Decimal("6")
                        ),
                        "stretch_observed_dd_at_most_5r": (
                            Decimal(
                                cast(
                                    str,
                                    scaled_metrics["max_drawdown_r"],
                                )
                            )
                            <= Decimal("5")
                        ),
                        "mc_positive_at_least_0_90": (
                            Decimal(
                                cast(
                                    str,
                                    scaled_mc[
                                        "positive_terminal_probability"
                                    ],
                                )
                            )
                            >= Decimal("0.90")
                        ),
                        "mc_p95_dd_at_most_15r": (
                            Decimal(
                                cast(
                                    str,
                                    scaled_mc["p95_max_drawdown_r"],
                                )
                            )
                            <= Decimal("15")
                        ),
                    },
                }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET,
        "partition": partition,
        "base_variant": BASE_VARIANT,
        "evaluation_window": {
            "start_date": (
                None if EVAL_START_DATE is None else EVAL_START_DATE.isoformat()
            ),
            "end_exclusive_date": (
                None
                if EVAL_END_EXCLUSIVE_DATE is None
                else EVAL_END_EXCLUSIVE_DATE.isoformat()
            ),
            "warmup_context_retained": True,
        },
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "base_trade_count": len(first_rows),
        "base_metrics": _capital_metrics(first_rows),
        "base_monte_carlo": _monte_carlo(
            first_rows,
            variant=f"{BASE_VARIANT}:evaluation-window",
        ),
        "rearm_candidate_count": max(
            (
                len(rows)
                for rows in rearm_raw_by_mode.values()
            ),
            default=0,
        ),
        "quality_score_distribution": {
            str(key): value
            for key, value in sorted(quality_counts.items())
        },
        "risk_profiles": {
            name: {
                key: format(value, "f")
                for key, value in mapping.items()
            }
            for name, mapping in RISK_PROFILES.items()
        },
        "variants": variants,
        "status_counts": dict(sorted(status.items())),
        "governance": {
            "base_wait1025_semantics_preserved": True,
            "one_rearm_max_per_day": True,
            "one_trade_max_per_source_event": True,
            "new_raid_confirmation_decision_required": True,
            "rearm_quality_uses_terminal_pnl": False,
            "rearm_quality_uses_future_bars": False,
            "risk_modulation_reduces_trade_count": False,
            "monthly_rearm_budget_is_capital_governance": True,
            "monthly_rearm_budget_uses_terminal_pnl": False,
            "monthly_rearm_budget_uses_fold_identity": False,
            "adaptive_rearm_budget_uses_prior_activity_only": True,
            "adaptive_rearm_budget_uses_terminal_pnl": False,
            "adaptive_rearm_budget_uses_fold_identity": False,
            "global_risk_scalar_uses_terminal_pnl": False,
            "global_risk_scalar_uses_fold_identity": False,
            "global_risk_scalar_changes_trade_count": False,
            "fixed_activity_profile": FIXED_ACTIVITY_PROFILE,
            "fixed_global_risk_scalar": (
                None
                if FIXED_GLOBAL_RISK_SCALAR is None
                else format(FIXED_GLOBAL_RISK_SCALAR, "f")
            ),
            "dd6_frontier_only": DD6_FRONTIER_ONLY,
            "evaluation_window_uses_date_only_not_outcome": True,
            "warmup_context_retained_before_evaluation_window": True,
            "first_swing_is_universal": False,
            "qore_risk_remains_sovereign": True,
            "consumed_evidence_only": True,
            "policy_promoted": False,
            "opens_new_holdout": False,
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
                "base_trade_count": payload["base_trade_count"],
                "base_metrics": payload["base_metrics"],
                "rearm_candidate_count": payload[
                    "rearm_candidate_count"
                ],
                "quality_score_distribution": payload[
                    "quality_score_distribution"
                ],
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
