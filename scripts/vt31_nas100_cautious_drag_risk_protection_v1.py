"""VT31 NAS100 CAUTIOUS drag-aware risk/protection lab V1.

Consumed-evidence development only.

The prior CAUTIOUS decomposition defined structural groups without terminal PnL,
then found a small set of cross-fold negative associations. This lab tests a
capital/management response without removing entries:

- the OCO opportunity universe is unchanged;
- causal state is captured at decision time;
- negative-association flags apply only inside CAUTIOUS;
- requested risk is reduced by structural drag severity;
- optional first confirmed protective swing is tested only as management;
- QORE Risk remains sovereign.

The association set was discovered on consumed evidence. Therefore every
result here is tuning evidence, never a fresh validation or promotion.
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
from typing import cast

import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_high_density_management_intelligence_v1 as management
import vt31_nas100_high_density_structural_protection_v1 as protection
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutionPolicy,
)

SCHEMA = "qore.vt31.nas100.cautious_drag_risk_protection.v1"
IDENTITY = "VT31_NAS100_CAUTIOUS_DRAG_RISK_PROTECTION_V1"
MARKET = "NAS100"

PROFILES: dict[str, dict[str, Decimal]] = {
    "CONSERVATIVE": {
        "SUPPORTIVE": Decimal("1.00"),
        "MIXED": Decimal("0.60"),
        "CAUTIOUS_0": Decimal("0.35"),
        "CAUTIOUS_1": Decimal("0.12"),
        "CAUTIOUS_2P": Decimal("0.05"),
    },
    "BALANCED": {
        "SUPPORTIVE": Decimal("1.00"),
        "MIXED": Decimal("0.75"),
        "CAUTIOUS_0": Decimal("0.50"),
        "CAUTIOUS_1": Decimal("0.20"),
        "CAUTIOUS_2P": Decimal("0.08"),
    },
    "DENSITY_CAPITAL": {
        "SUPPORTIVE": Decimal("1.00"),
        "MIXED": Decimal("0.75"),
        "CAUTIOUS_0": Decimal("0.60"),
        "CAUTIOUS_1": Decimal("0.25"),
        "CAUTIOUS_2P": Decimal("0.10"),
    },
}

PROTECTION_MODES = (
    "RISK_ONLY",
    "DRAG_FIRST_SWING",
    "HEAVY_DRAG_FIRST_SWING",
)


def _reclaim_bucket(value: object) -> str:
    if value is None:
        return "no-reclaim"
    age = int(cast(int, value))
    if age <= 4:
        return "fresh-0-4m"
    if age <= 7:
        return "developing-5-7m"
    if age <= 14:
        return "stale-8-14m"
    return "old-15m-plus"


def _decision_bucket(value: object) -> str:
    minute = int(cast(int, value))
    if minute < 10 * 60 + 20:
        return "1000-1019"
    if minute < 10 * 60 + 40:
        return "1020-1039"
    return "1040-1059"


def _drag_flags(
    state: dict[str, object],
    *,
    context: str,
    side: str,
    family: str,
) -> tuple[str, ...]:
    if context != "CAUTIOUS":
        return ()

    structure = str(state["last_structure_event_family"])
    reclaim = _reclaim_bucket(state["reference_reclaim_age_minutes"])
    decision = _decision_bucket(state["decision_minute_ny"])
    flags: list[str] = []

    if side == "short" and family == "breaker":
        flags.append("SHORT_BREAKER")
    if structure == "breaker" and reclaim == "no-reclaim":
        flags.append("BREAKER_NO_RECLAIM")
    if (
        structure == "reference-liquidity-sweep"
        and reclaim == "fresh-0-4m"
    ):
        flags.append("REF_SWEEP_FRESH_RECLAIM")
    if decision == "1000-1019" and family == "breaker":
        flags.append("EARLY_BREAKER")
    if decision == "1040-1059" and family == "fair-value-gap":
        flags.append("LATE_FVG")
    return tuple(flags)


def _risk_class(context: str, drag_count: int) -> str:
    if context != "CAUTIOUS":
        return context
    if drag_count == 0:
        return "CAUTIOUS_0"
    if drag_count == 1:
        return "CAUTIOUS_1"
    return "CAUTIOUS_2P"


def _required_confirmations(mode: str, drag_count: int) -> int | None:
    if mode == "RISK_ONLY":
        return None
    if mode == "DRAG_FIRST_SWING":
        return 1 if drag_count >= 1 else None
    if mode == "HEAVY_DRAG_FIRST_SWING":
        return 1 if drag_count >= 2 else None
    raise ValueError(mode)


def _weighted_row(
    outcome: dict[str, object],
    *,
    weight: Decimal,
    context: str,
    risk_class: str,
    drag_flags: tuple[str, ...],
    state: dict[str, object],
) -> dict[str, object]:
    gross = Decimal(cast(str, outcome["r_multiple"]))
    net = weight * (gross - specialist.FRICTION)
    encoded_gross = net + specialist.FRICTION
    return {
        **outcome,
        "management_context": context,
        "risk_class": risk_class,
        "requested_risk_r": format(weight, "f"),
        "capital_weighted_net_r": format(net, "f"),
        "encoded_gross_r": format(encoded_gross, "f"),
        "drag_count": len(drag_flags),
        "drag_flags": list(drag_flags),
        "reference_volatility_state": state[
            "reference_volatility_state"
        ],
        "h1_state": state["h1_state"],
        "h4_state": state["h4_state"],
        "premarket_state": state["premarket_state"],
        "cash_open_state": state["cash_open_state"],
        "last_structure_event_family": state[
            "last_structure_event_family"
        ],
        "reference_reclaim_age_minutes": state[
            "reference_reclaim_age_minutes"
        ],
        "decision_minute_ny": state["decision_minute_ny"],
    }


def _weighted_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    converted = [
        {**row, "r_multiple": row["encoded_gross_r"]}
        for row in rows
    ]
    return _metrics(converted, friction=specialist.FRICTION)


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
            terminals[(n - 1) * 5 // 100],
            "f",
        ),
        "p50_terminal_r": format(
            terminals[(n - 1) * 50 // 100],
            "f",
        ),
        "p95_max_drawdown_r": format(
            drawdowns[(n - 1) * 95 // 100],
            "f",
        ),
        "p99_max_drawdown_r": format(
            drawdowns[(n - 1) * 99 // 100],
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
        raise ValueError("drag-risk lab requires NAS100 evidence")

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

    rows_by_variant: dict[str, list[dict[str, object]]] = {
        f"{profile}_{mode}": []
        for profile in PROFILES
        for mode in PROTECTION_MODES
    }
    status: Counter[str] = Counter()
    selected_count = 0
    structural_class_counts: Counter[str] = Counter()
    flag_counts: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        timeline = oco._timeline(day_bars, evidence_fingerprint=evidence)
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
        selected_count += 1

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
        context = management._context_state(state)
        flags = _drag_flags(
            state,
            context=context,
            side=selected.side.value,
            family=selected.selected_family.value,
        )
        risk_class = _risk_class(context, len(flags))
        structural_class_counts[risk_class] += 1
        for flag in flags:
            flag_counts[flag] += 1

        outcome_by_mode: dict[str, dict[str, object]] = {}
        for mode in PROTECTION_MODES:
            confirmations = _required_confirmations(mode, len(flags))
            outcome_by_mode[mode] = (
                protection._simulate_single_structural_trail(
                    day_bars,
                    selected,
                    required_confirmations=confirmations,
                )
            )

        for profile_name, weights in PROFILES.items():
            weight = weights[risk_class]
            for mode in PROTECTION_MODES:
                variant = f"{profile_name}_{mode}"
                outcome = outcome_by_mode[mode]
                status[f"{variant}:{outcome['status']}"] += 1
                if outcome.get("status") != "terminal":
                    continue
                rows_by_variant[variant].append(
                    _weighted_row(
                        outcome,
                        weight=weight,
                        context=context,
                        risk_class=risk_class,
                        drag_flags=flags,
                        state=state,
                    )
                )

    variants: dict[str, object] = {}
    for variant, rows in rows_by_variant.items():
        rows.sort(key=lambda row: cast(str, row["signal_at"]))
        metrics = _weighted_metrics(rows)
        mc = _monte_carlo(rows, variant=variant)
        counts = Counter(str(row["risk_class"]) for row in rows)
        drag_count = Counter(int(row["drag_count"]) for row in rows)
        gates = {
            "density_250_to_330": 250 <= len(rows) <= 330,
            "profit_factor_at_least_1_50": (
                metrics["profit_factor"] is not None
                and Decimal(cast(str, metrics["profit_factor"]))
                >= Decimal("1.50")
            ),
            "observed_dd_at_most_10r": (
                Decimal(cast(str, metrics["max_drawdown_r"]))
                <= Decimal("10")
            ),
            "mc_positive_at_least_0_90": (
                Decimal(cast(str, mc["positive_terminal_probability"]))
                >= Decimal("0.90")
            ),
            "mc_p95_dd_at_most_15r": (
                Decimal(cast(str, mc["p95_max_drawdown_r"]))
                <= Decimal("15")
            ),
        }
        variants[variant] = {
            "trade_count": len(rows),
            "capital_weighted_metrics": metrics,
            "monte_carlo": mc,
            "risk_class_counts": dict(sorted(counts.items())),
            "drag_count_distribution": {
                str(key): value
                for key, value in sorted(drag_count.items())
            },
            "development_gates": gates,
            "passes_development_gates": all(gates.values()),
        }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET,
        "partition": partition,
        "candidate_contract_fingerprint": specialist.contract_fingerprint(),
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "oco_selected_setup_count": selected_count,
        "structural_class_counts": dict(
            sorted(structural_class_counts.items())
        ),
        "drag_flag_counts": dict(sorted(flag_counts.items())),
        "profiles": {
            name: {
                key: format(value, "f")
                for key, value in weights.items()
            }
            for name, weights in PROFILES.items()
        },
        "variants": variants,
        "status_counts": dict(sorted(status.items())),
        "governance": {
            "entry_filtering": False,
            "one_trade_max_per_source_event": True,
            "trade_count_reduced_by_risk_policy": False,
            "risk_flags_use_future_bars": False,
            "risk_flags_use_terminal_pnl_at_runtime": False,
            "risk_map_derived_from_consumed_association_research": True,
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
                "oco_selected_setup_count": payload[
                    "oco_selected_setup_count"
                ],
                "structural_class_counts": payload[
                    "structural_class_counts"
                ],
                "drag_flag_counts": payload["drag_flag_counts"],
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
