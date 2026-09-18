"""VT31 NAS100 high-density capacity-weighted risk intelligence V2.

Research-only consumed-evidence lab.

Goal:
- preserve the high-density OCO opportunity set (no entry filtering);
- use only causal pre-entry structural state to assign requested risk;
- concentrate capital where cross-fold journey-capacity memory is stronger;
- reduce drawdown without manufacturing a lower trade count.

The score is derived from structural journey-capacity evidence, not terminal PnL:
- fair-value-gap entry evidence is favored over breaker;
- H1 mixed is favored for cross-fold stability;
- compressed reference is favored;
- cash-open rotation and bullish premarket are favored;
- reference-liquidity / order-block recent structure is favored;
- long side receives a small stability bonus.

No trade is removed by this layer. QORE Risk remains sovereign.
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

SCHEMA = "qore.vt31.nas100.high_density_capacity_risk.v2"
IDENTITY = "VT31_NAS100_HIGH_DENSITY_CAPACITY_RISK_V2"
MARKET = "NAS100"

RISK_TIERS = {
    "A": Decimal("1.00"),
    "B": Decimal("0.50"),
    "C": Decimal("0.25"),
    "D": Decimal("0.10"),
}
VARIANTS = (
    "BASELINE_MANAGEMENT",
    "CAUTIOUS_FIRST_SWING",
    "NON_SUPPORTIVE_FIRST_SWING",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _capacity_score(state: dict[str, object], entry_family: str, side: str) -> int:
    score = 0

    if entry_family == "fair-value-gap":
        score += 2
    elif entry_family == "breaker":
        score -= 2

    if state.get("h1_state") == "mixed":
        score += 1

    ref_state = state.get("reference_volatility_state")
    if ref_state == "compressed":
        score += 2
    elif ref_state == "expanded":
        score -= 1

    if state.get("cash_open_state") == "rotation":
        score += 1

    premarket = state.get("premarket_state")
    if premarket == "bullish":
        score += 1
    elif premarket == "bearish":
        score -= 1

    last_structure = state.get("last_structure_event_family")
    if last_structure in {"reference-liquidity-sweep", "order-block"}:
        score += 1
    elif last_structure == "breaker":
        score -= 1

    if side == "long":
        score += 1

    return score


def _risk_tier(score: int) -> str:
    if score >= 4:
        return "A"
    if score >= 2:
        return "B"
    if score >= 0:
        return "C"
    return "D"


def _weighted_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    converted = [
        {
            **row,
            "r_multiple": row["encoded_gross_r"],
        }
        for row in rows
    ]
    return _metrics(converted, friction=specialist.FRICTION)


def _monte_carlo(rows: list[dict[str, object]]) -> dict[str, object]:
    values = [
        Decimal(cast(str, row["capital_weighted_net_r"]))
        for row in rows
    ]
    n = len(values)
    if n == 0:
        return {
            "paths": 10000,
            "block_length": 5,
            "positive_terminal_probability": "0",
            "p95_max_drawdown_r": "0",
        }
    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    domain = IDENTITY.encode()
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
            sampled.extend(values[(start + offset) % n] for offset in range(5))
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


def _encode_weighted_trade(
    outcome: dict[str, object],
    *,
    state: dict[str, object],
    score: int,
    tier: str,
    weight: Decimal,
) -> dict[str, object]:
    gross = Decimal(cast(str, outcome["r_multiple"]))
    weighted_net = weight * (gross - specialist.FRICTION)
    encoded_gross = weighted_net + specialist.FRICTION
    return {
        **outcome,
        "capacity_score": score,
        "risk_tier": tier,
        "requested_risk_r": format(weight, "f"),
        "capital_weighted_net_r": format(weighted_net, "f"),
        "encoded_gross_r": format(encoded_gross, "f"),
        "h1_state": state.get("h1_state"),
        "h4_state": state.get("h4_state"),
        "premarket_state": state.get("premarket_state"),
        "cash_open_state": state.get("cash_open_state"),
        "reference_volatility_state": state.get(
            "reference_volatility_state"
        ),
        "last_structure_event_family": state.get(
            "last_structure_event_family"
        ),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("capacity-risk lab requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        day: tuple(sorted(rows, key=lambda item: getattr(item, "opened_at")))
        for day, rows in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = Vt31R22ExecutionPolicy()

    rows_by_variant: dict[str, list[dict[str, object]]] = {
        variant: [] for variant in VARIANTS
    }
    tier_counts: Counter[str] = Counter()
    score_counts: Counter[int] = Counter()
    status_counts: Counter[str] = Counter()
    selected_count = 0

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            continue

        timeline = oco._timeline(
            day_bars,
            evidence_fingerprint=evidence,
        )
        if timeline is None:
            continue
        selected, selection_status = oco._select_oco(
            day_bars,
            timeline,
            policy,
        )
        status_counts[f"oco-{selection_status}"] += 1
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

        score = _capacity_score(
            state,
            selected.selected_family.value,
            selected.side.value,
        )
        tier = _risk_tier(score)
        weight = RISK_TIERS[tier]
        tier_counts[tier] += 1
        score_counts[score] += 1

        management_context = str(
            protection.management._context_state(state)
        )
        variant_confirmations = {
            "BASELINE_MANAGEMENT": None,
            "CAUTIOUS_FIRST_SWING": (
                1 if management_context == "CAUTIOUS" else None
            ),
            "NON_SUPPORTIVE_FIRST_SWING": (
                None if management_context == "SUPPORTIVE" else 1
            ),
        }
        for variant, confirmations in variant_confirmations.items():
            outcome = protection._simulate_single_structural_trail(
                day_bars,
                selected,
                required_confirmations=confirmations,
            )
            status_counts[f"{variant}:{outcome['status']}"] += 1
            if outcome.get("status") != "terminal":
                continue
            rows_by_variant[variant].append(
                _encode_weighted_trade(
                    outcome,
                    state=state,
                    score=score,
                    tier=tier,
                    weight=weight,
                )
            )

    variants: dict[str, object] = {}
    for variant, rows in rows_by_variant.items():
        rows.sort(key=lambda item: cast(str, item["signal_at"]))
        metrics = _weighted_metrics(rows)
        mc = _monte_carlo(rows)
        variants[variant] = {
            "trade_count": len(rows),
            "capital_weighted_metrics": metrics,
            "monte_carlo": mc,
            "risk_tier_counts": dict(sorted(Counter(
                str(row["risk_tier"]) for row in rows
            ).items())),
            "exit_reason_counts": dict(sorted(Counter(
                str(row["exit_reason"]) for row in rows
            ).items())),
            "development_gates": {
                "trade_count_at_least_300": len(rows) >= 300,
                "profit_factor_at_least_1_50": (
                    metrics["profit_factor"] is not None
                    and Decimal(cast(str, metrics["profit_factor"]))
                    >= Decimal("1.50")
                ),
                "max_drawdown_at_most_10r": (
                    Decimal(cast(str, metrics["max_drawdown_r"]))
                    <= Decimal("10")
                ),
                "mc_positive_at_least_0_90": (
                    Decimal(cast(str, mc["positive_terminal_probability"]))
                    >= Decimal("0.90")
                ),
                "mc_p95_drawdown_at_most_20r": (
                    Decimal(cast(str, mc["p95_max_drawdown_r"]))
                    <= Decimal("20")
                ),
            },
        }
        variants[variant]["passes_development_gates"] = all(
            cast(dict[str, bool], variants[variant]["development_gates"]).values()
        )

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
        "oco_selected_setup_count": selected_count,
        "capacity_score_counts": {
            str(key): value for key, value in sorted(score_counts.items())
        },
        "risk_tier_counts": dict(sorted(tier_counts.items())),
        "risk_tiers": {
            key: format(value, "f") for key, value in RISK_TIERS.items()
        },
        "variants": variants,
        "status_counts": dict(sorted(status_counts.items())),
        "governance": {
            "entry_filtering": False,
            "trade_count_reduced_by_risk_policy": False,
            "risk_score_uses_terminal_pnl": False,
            "risk_score_uses_post_outcome_fields": False,
            "risk_score_basis": "cross-fold-structural-journey-capacity",
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
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "oco_selected_setup_count": payload["oco_selected_setup_count"],
        "risk_tier_counts": payload["risk_tier_counts"],
        "variants": payload["variants"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
