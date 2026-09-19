"""VT31 NAS100 Sequential Structural Replacement Frontier V2.

Thin composition of existing Core laboratories:
- Market State V2 supplies predecision structural state features;
- Hypothesis Lifecycle V1 supplies causal family maturation;
- Sequential Structural Replacement V1 supplies the replacement architecture;
- Transition Forensics V1 supplies cross-fold replacement guards.

No new market ontology is introduced here.  This is an economic frontier over
already-observed, already-consumed causal states.

Frozen Silver Bullet identity, structural stop, opposite-reference target and
3R->BE remain unchanged.  Future labels, terminal PnL, fold identity, H4/H1
trend and target trade count are forbidden as runtime inputs.
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

import vt31_nas100_causal_hybrid_rearm_v1 as capital
import vt31_nas100_hypothesis_lifecycle_frontier_v1 as lifecycle
import vt31_nas100_market_state_lab_v2 as market_state
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
)

SCHEMA = "qore.vt31.nas100.sequential_structural_replacement_frontier.v2"
IDENTITY = "VT31_NAS100_SEQUENTIAL_STRUCTURAL_REPLACEMENT_FRONTIER_V2"
MARKET = "NAS100"
FRICTION = Decimal("0.05")
MAX_SOURCE_CYCLES_PER_DAY = 6
MAX_EXECUTIONS_PER_DAY = 2
EXPECTED_SOURCE_SHA256 = lifecycle.EXPECTED_SOURCE_SHA256
EXPECTED_METHODOLOGY_ID = lifecycle.EXPECTED_METHODOLOGY_ID

VARIANTS = (
    "NEGATIVE_VETO_FLAT060",
    "NEGATIVE_VETO_SUPPORT_RISK",
    "TRANSITION_GUARD_SUPPORT_RISK",
    "MATURATION_INVALIDATION_PRIORITY",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _rejection_class(status: str) -> str:
    if status == "NON_EXECUTABLE":
        return "NON_EXECUTABLE"
    if status == "INVALIDATED":
        return "EVENT_INVALIDATED"
    if status.startswith("REJECT_INVALIDATED"):
        return "MATURATION_INVALIDATED"
    if status.startswith("REJECT_WEAK_CLOSE"):
        return "WEAK_CLOSE"
    if status.startswith("REJECT_WEAK_FOLLOW"):
        return "WEAK_FOLLOW"
    if status.startswith("REJECT_EXCESSIVE"):
        return "EXCESSIVE_GIVEBACK"
    if status.startswith("REJECT_TARGET"):
        return "TARGET_EXHAUSTED"
    if status.startswith("REJECT_SESSION"):
        return "SESSION_EXHAUSTED"
    if status.startswith("REJECT_AMBIGUOUS"):
        return "AMBIGUOUS"
    if status == "ROUTER_NEGATIVE_STATE":
        return status
    return status


def _rejection_decision_at(
    session: tuple[object, ...],
    source: Vt31R22SourceSetup,
    setup: Vt31R22ExecutableSetup,
) -> datetime:
    bars_required, _, _, _ = lifecycle._maturity_contract(
        setup.selected_family.value,
        "FAMILY",
    )
    confirmation_index = next(
        index
        for index, bar in enumerate(session)
        if cast(datetime, getattr(bar, "closed_at"))
        == source.structure.confirmation_at
    )
    final_index = min(
        len(session) - 1,
        confirmation_index + bars_required,
    )
    return cast(datetime, getattr(session[final_index], "closed_at"))


def _source_state(
    reference: tuple[object, ...],
    session: tuple[object, ...],
    source: Vt31R22SourceSetup,
    setup: Vt31R22ExecutableSetup,
) -> dict[str, object]:
    prefix = tuple(
        [*reference]
        + [
            bar
            for bar in session
            if cast(datetime, getattr(bar, "closed_at"))
            <= setup.decision_at
        ]
    )
    return market_state._decorate_bins(
        market_state._state_features(prefix, source, setup)
    )


def _negative_state(state: dict[str, object]) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    # Stable negative across R5/R6/R8 Market State V2.
    if state["reclaim_latency_bin"] == "8-14":
        reasons.append("RECLAIM_LATENCY_8_14")
    if state["target_r_bin"] == "4-6":
        reasons.append("TARGET_R_4_6")
    return bool(reasons), tuple(reasons)


def _support_count(state: dict[str, object]) -> tuple[int, tuple[str, ...]]:
    reasons: list[str] = []
    # Stable positive structural states across R5/R6/R8 Market State V2.
    if state["candidate_family_count"] == 1:
        reasons.append("SINGLE_FAMILY")
    if state["session_range_ref_bin"] == "<0.75":
        reasons.append("SESSION_RANGE_LT_075")
    if state["decision_time_bucket"] == "10:00-10:14":
        reasons.append("EARLY_DECISION")
    if state["side"] == "long":
        reasons.append("LONG")
    if state["raid_latency_bin"] == "5-14":
        reasons.append("RAID_LATENCY_5_14")
    if state["entry_family"] == "fair-value-gap":
        reasons.append("FVG")
    if state["recent_range_ref_bin"] == "0.50-0.75":
        reasons.append("RECENT_RANGE_050_075")
    if state["risk_ref_bin"] in {"0.15-0.25", "0.25-0.40"}:
        reasons.append("RISK_REF_015_040")
    if state["raid_depth_ref_bin"] == "0.25-0.50":
        reasons.append("RAID_DEPTH_025_050")
    return len(reasons), tuple(reasons)


def _risk_for(
    variant: str,
    *,
    support: int,
    is_replacement: bool,
    prior_rejection_class: str,
) -> Decimal:
    if variant == "NEGATIVE_VETO_FLAT060":
        return Decimal("0.60")

    if support >= 3:
        risk = Decimal("0.60")
    elif support == 2:
        risk = Decimal("0.40")
    elif support == 1:
        risk = Decimal("0.20")
    else:
        risk = Decimal("0.08")

    if (
        variant == "MATURATION_INVALIDATION_PRIORITY"
        and is_replacement
        and prior_rejection_class != "MATURATION_INVALIDATED"
    ):
        return min(risk, Decimal("0.10"))
    return risk


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
    blocks = []
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
        blocks.append(
            {
                "start": start.isoformat(),
                "end_exclusive": end.isoformat(),
                "trade_count": len(selected),
                "metrics": metrics,
                "positive": bool(selected) and _d(metrics["total_r"]) > 0,
            }
        )
    return blocks


def _run_variant(
    by_day: dict[date, tuple[object, ...]],
    *,
    evidence: str,
    partition: str,
    variant: str,
) -> dict[str, object]:
    policy = Vt31R22ExecutionPolicy()
    rows: list[dict[str, object]] = []
    status: Counter[str] = Counter()
    rejection_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    support_counts: Counter[int] = Counter()

    use_transition_guard = variant in {
        "TRANSITION_GUARD_SUPPORT_RISK",
        "MATURATION_INVALIDATION_PRIORITY",
    }

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        cursor = cast(datetime, getattr(reference[-1], "closed_at"))
        executions = 0
        rejection_depth = 0
        prior_rejection: dict[str, object] | None = None

        for _ in range(MAX_SOURCE_CYCLES_PER_DAY):
            if executions >= MAX_EXECUTIONS_PER_DAY:
                status["execution-cap-reached"] += 1
                break

            event = lifecycle._next_source(
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
                rejection_depth += 1
                decision_at = cast(datetime, event["decision_at"])
                prior_rejection = {
                    "class": _rejection_class(event_status),
                    "decision_at": decision_at,
                }
                rejection_counts[_rejection_class(event_status)] += 1
                cursor = decision_at
                continue

            source = cast(Vt31R22SourceSetup, event["source"])
            setup = cast(Vt31R22ExecutableSetup, event["setup"])
            state = _source_state(reference, session, source, setup)
            is_negative, negative_reasons = _negative_state(state)
            if is_negative:
                rejection_depth += 1
                prior_rejection = {
                    "class": "ROUTER_NEGATIVE_STATE",
                    "decision_at": setup.decision_at,
                }
                status["router-negative-state"] += 1
                for reason in negative_reasons:
                    status[f"router-negative:{reason}"] += 1
                cursor = setup.decision_at
                continue

            maturity = lifecycle._mature(
                session=session,
                source=source,
                setup=setup,
                mode="FAMILY",
            )
            maturity_status = cast(str, maturity["status"])
            status[maturity_status] += 1
            if maturity_status != "MATURED":
                decision_at = _rejection_decision_at(
                    session,
                    source,
                    setup,
                )
                rejection_depth += 1
                cls = _rejection_class(maturity_status)
                prior_rejection = {
                    "class": cls,
                    "decision_at": decision_at,
                }
                rejection_counts[cls] += 1
                cursor = decision_at
                continue

            authorization_at = cast(datetime, maturity["authorization_at"])
            prior_class = (
                "NONE"
                if prior_rejection is None
                else cast(str, prior_rejection["class"])
            )
            is_replacement = rejection_depth > 0

            if use_transition_guard and is_replacement:
                if rejection_depth >= 3:
                    status["transition-veto-depth-3-plus"] += 1
                    cursor = authorization_at
                    rejection_depth += 1
                    prior_rejection = {
                        "class": "TRANSITION_DEPTH_VETO",
                        "decision_at": authorization_at,
                    }
                    continue
                rejection_at = cast(datetime, prior_rejection["decision_at"])
                latency = int(
                    (authorization_at - rejection_at).total_seconds() // 60
                )
                if 6 <= latency <= 10:
                    status["transition-veto-auth-latency-6-10"] += 1
                    cursor = authorization_at
                    rejection_depth += 1
                    prior_rejection = {
                        "class": "TRANSITION_LATENCY_VETO",
                        "decision_at": authorization_at,
                    }
                    continue

            market_setup = lifecycle._market_setup(
                source,
                setup,
                authorization_at=authorization_at,
                authorization_price=_d(maturity["authorization_price"]),
                variant=f"{IDENTITY}:{variant}",
            )
            if market_setup is None:
                status["market-translation-invalid-geometry"] += 1
                cursor = authorization_at
                rejection_depth += 1
                prior_rejection = {
                    "class": "MARKET_INVALID_GEOMETRY",
                    "decision_at": authorization_at,
                }
                continue

            outcome = lifecycle._simulate_market_at_close(
                day_bars,
                market_setup,
            )
            status[f"outcome-{outcome['status']}"] += 1
            if outcome.get("status") != "terminal":
                break

            support, support_reasons = _support_count(state)
            support_counts[support] += 1
            risk = _risk_for(
                variant,
                support=support,
                is_replacement=is_replacement,
                prior_rejection_class=prior_class,
            )
            risk_counts[format(risk, "f")] += 1
            capital_r = risk * (
                _d(outcome["r_multiple"]) - FRICTION
            )

            row = dict(outcome)
            row.update(
                {
                    "partition": partition,
                    "local_date": local_day.isoformat(),
                    "source_event_index": executions + 1,
                    "replacement_depth": rejection_depth,
                    "is_replacement": is_replacement,
                    "prior_rejection_class": prior_class,
                    "market_state_support_count": support,
                    "market_state_support_reasons": list(support_reasons),
                    "requested_risk_r": format(risk, "f"),
                    "capital_weighted_net_r": format(capital_r, "f"),
                    "entry_family": market_setup.selected_family.value,
                    "future_label_used_at_runtime": False,
                }
            )
            rows.append(row)
            executions += 1
            rejection_depth = 0
            prior_rejection = None

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
        variant=f"{IDENTITY}:{variant}:{partition}",
    )
    annual = _annual_blocks(rows) if partition == "consumed_holdout" else []
    objectives = {
        "density_300_350": 300 <= len(rows) <= 350,
        "pf_ge_1_50": (
            metrics["profit_factor"] is not None
            and _d(metrics["profit_factor"]) >= Decimal("1.50")
        ),
        "dd_le_6": _d(metrics["max_drawdown_r"]) <= Decimal("6"),
        "raw_losing_streak_le_12": _max_loss_streak(rows) <= 12,
        "material_losing_streak_le_8": (
            _max_loss_streak(rows, material=Decimal("0.10")) <= 8
        ),
        "mc_positive_ge_0_90": (
            _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
        ),
        "mc_p95_dd_le_15": (
            _d(mc["p95_max_drawdown_r"]) <= Decimal("15")
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
        "risk_counts": dict(sorted(risk_counts.items())),
        "support_counts": {
            str(k): v for k, v in sorted(support_counts.items())
        },
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "status_counts": dict(sorted(status.items())),
        "objectives": objectives,
        "passes_all_objectives": all(objectives.values()),
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    if silver.SOURCE_SHA256 != EXPECTED_SOURCE_SHA256:
        raise AssertionError("Silver Bullet source SHA changed")
    if silver.METHODOLOGY_ID != EXPECTED_METHODOLOGY_ID:
        raise AssertionError("Silver Bullet methodology changed")

    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("sequential replacement V2 requires NAS100")

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
        variant: _run_variant(
            by_day,
            evidence=evidence,
            partition=partition,
            variant=variant,
        )
        for variant in VARIANTS
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
            "market_state_v2_reused": True,
            "sequential_replacement_v1_architecture_reused": True,
            "hypothesis_lifecycle_v1_reused": True,
            "transition_forensics_v1_reused": True,
            "future_labels_runtime_forbidden": True,
            "terminal_pnl_used_at_runtime": False,
            "fold_identity_used_at_runtime": False,
            "h4_primary_causal_feature": False,
            "h1_primary_causal_feature": False,
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
        {"partition": payload["partition"], "variants": payload["variants"]},
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
