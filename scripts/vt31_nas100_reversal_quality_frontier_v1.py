"""Causal reversal-quality admission and translation frontier for VT31 NAS100.

Consumed research evidence only.

This lab keeps the frozen TTrades Silver Bullet source identity immutable and
tests whether the newly falsified pre-entry geometry can improve QORE's
admission / execution translation without using future labels.

Causal inputs are observable at the source decision:
- reclaim depth versus the frozen reference;
- confirmation displacement / body / penetration;
- confirmation clock minute;
- current executable entry family and risk/reference geometry.

The lab may reject a source hypothesis and wait for a genuinely new
raid+confirmation event.  An executed event must terminate before a later
execution is considered.  No terminal PnL, fold identity, date oracle, H4/H1
trend, future journey label, or target trade count is a runtime input.

Silver Bullet stop, opposite-reference target and 3R->BE lifecycle are
unchanged.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_causal_hybrid_rearm_v1 as capital
import vt31_nas100_causal_hybrid_replay_v1 as activation
import vt31_nas100_execution_translation_falsification_v1 as translation
import vt31_nas100_r1_candidate as baseline
import vt31_nas100_reversal_vs_expansion_forensics_v1 as reversal
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
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.reversal_quality_frontier.v1"
IDENTITY = "VT31_NAS100_REVERSAL_QUALITY_FRONTIER_V1"
MARKET = "NAS100"
FRICTION = Decimal("0.05")
MAX_SOURCE_CYCLES_PER_DAY = 5
MAX_EXECUTIONS_PER_DAY = 2
EXPECTED_SOURCE_SHA256 = (
    "bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf"
)
EXPECTED_METHODOLOGY_ID = "ttrades-am-silver-bullet-nq-r2.2"

VARIANTS: dict[str, dict[str, object]] = {
    "ALL_CURRENT_FLAT060": {
        "minimum_score": -99,
        "hard_negative_veto": False,
        "translation": "CURRENT",
        "risk_mode": "FLAT060",
    },
    "Q0_CURRENT_FLAT060": {
        "minimum_score": 0,
        "hard_negative_veto": False,
        "translation": "CURRENT",
        "risk_mode": "FLAT060",
    },
    "Q1_CURRENT_FLAT060": {
        "minimum_score": 1,
        "hard_negative_veto": False,
        "translation": "CURRENT",
        "risk_mode": "FLAT060",
    },
    "Q2_CURRENT_FLAT060": {
        "minimum_score": 2,
        "hard_negative_veto": False,
        "translation": "CURRENT",
        "risk_mode": "FLAT060",
    },
    "Q0_FVG_PROX_QUALITY_RISK": {
        "minimum_score": 0,
        "hard_negative_veto": True,
        "translation": "FVG_PROXIMAL",
        "risk_mode": "QUALITY",
    },
    "Q1_FVG_PROX_QUALITY_RISK": {
        "minimum_score": 1,
        "hard_negative_veto": True,
        "translation": "FVG_PROXIMAL",
        "risk_mode": "QUALITY",
    },
    "Q0_HQ_PROX_QUALITY_RISK": {
        "minimum_score": 0,
        "hard_negative_veto": True,
        "translation": "HIGH_QUALITY_PROXIMAL",
        "risk_mode": "QUALITY",
    },
    "Q1_HQ_PROX_QUALITY_RISK": {
        "minimum_score": 1,
        "hard_negative_veto": True,
        "translation": "HIGH_QUALITY_PROXIMAL",
        "risk_mode": "QUALITY",
    },
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _quality(
    features: dict[str, object],
) -> tuple[int, tuple[str, ...], bool]:
    reclaim = _d(features["reclaim_depth_ref"])
    displacement = _d(features["confirmation_displacement_ref"])
    penetration = _d(features["confirmation_penetration_ref"])
    body = _d(features["confirmation_body_fraction"])
    risk_ref = _d(features["risk_ref"])
    minute = int(cast(int, features["confirmation_minute"]))
    family = cast(str, features["entry_family"])

    score = 0
    reasons: list[str] = []

    if reclaim <= Decimal("0.10"):
        score -= 2
        reasons.append("RECLAIM_LE_010")
    elif reclaim <= Decimal("0.25"):
        score += 2
        reasons.append("RECLAIM_010_025")
    elif reclaim <= Decimal("0.50"):
        score += 3
        reasons.append("RECLAIM_025_050")
    else:
        score += 1
        reasons.append("RECLAIM_GT_050")

    if displacement <= Decimal("0.10"):
        score -= 2
        reasons.append("DISPLACEMENT_LE_010")
    elif displacement <= Decimal("0.25"):
        score += 1
        reasons.append("DISPLACEMENT_010_025")
    elif displacement <= Decimal("0.50"):
        score += 3
        reasons.append("DISPLACEMENT_025_050")
    else:
        score += 1
        reasons.append("DISPLACEMENT_GT_050")

    if penetration <= Decimal("0.10"):
        score -= 1
        reasons.append("PENETRATION_LE_010")
    elif penetration <= Decimal("0.25"):
        score += 1
        reasons.append("PENETRATION_010_025")
    else:
        score += 1
        reasons.append("PENETRATION_GT_025")

    if body < Decimal("0.25"):
        score -= 1
        reasons.append("BODY_LT_025")
    elif body >= Decimal("0.75"):
        score += 1
        reasons.append("BODY_GE_075")

    if risk_ref <= Decimal("0.10"):
        score -= 2
        reasons.append("RISK_REF_LE_010")
    elif risk_ref <= Decimal("0.25"):
        score += 1
        reasons.append("RISK_REF_010_025")
    elif risk_ref <= Decimal("0.50"):
        score += 2
        reasons.append("RISK_REF_025_050")

    if family == "fair-value-gap":
        score += 1
        reasons.append("FVG_RUNNER_ENRICHED")

    if 30 <= minute < 40:
        score -= 3
        reasons.append("CONFIRMATION_MINUTE_30_39")

    hard_negative = (
        30 <= minute < 40
        or (
            reclaim <= Decimal("0.10")
            and displacement <= Decimal("0.10")
        )
    )
    return score, tuple(reasons), hard_negative


def _risk_for(score: int, mode: str) -> Decimal:
    if mode == "FLAT060":
        return Decimal("0.60")
    if mode != "QUALITY":
        raise ValueError(mode)
    if score >= 4:
        return Decimal("0.60")
    if score >= 2:
        return Decimal("0.30")
    return Decimal("0.10")


def _research_setup(
    source: Vt31R22SourceSetup,
    current: Vt31R22ExecutableSetup,
    *,
    score: int,
    mode: str,
    variant: str,
    decision_at: datetime,
) -> Vt31R22ExecutableSetup | None:
    if mode == "CURRENT":
        return activation._activation_setup(current, decision_at)

    depth = Decimal("0.5")
    if mode == "FVG_PROXIMAL":
        if current.selected_family.value == "fair-value-gap" and score >= 2:
            depth = Decimal(0)
    elif mode == "HIGH_QUALITY_PROXIMAL":
        if score >= 4:
            depth = Decimal(0)
    else:
        raise ValueError(mode)

    setup = translation._make_research_setup(
        source,
        family=current.selected_family,
        depth=depth,
        variant=f"{IDENTITY}:{variant}",
    )
    if setup is None:
        return None
    return activation._activation_setup(setup, decision_at)


def _next_source_event(
    *,
    reference: tuple[object, ...],
    session: tuple[object, ...],
    after_at: datetime,
    evidence: str,
    policy: Vt31R22ExecutionPolicy,
) -> dict[str, object]:
    event_prefix: list[object] = list(reference)
    for bar in session:
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        if closed_at <= after_at:
            continue
        event_prefix.append(bar)
        evaluation = evaluate_vt31_r2_2_source(
            instrument=getattr(bar, "instrument"),
            as_of=closed_at,
            m1_candles=cast(Any, tuple(event_prefix)),
            evidence_fingerprint=evidence,
        )
        if evaluation.setup is None:
            if evaluation.both_sides_swept:
                return {
                    "status": "INVALIDATED",
                    "decision_at": closed_at,
                }
            continue

        source = evaluation.setup
        if (
            source.structure.raid_at <= after_at
            or source.structure.confirmation_at <= after_at
        ):
            continue

        executable, reason = make_executable_setup(source, policy)
        if executable is None:
            return {
                "status": "NON_EXECUTABLE",
                "decision_at": closed_at,
                "reason": None if reason is None else reason.value,
            }
        return {
            "status": "SOURCE",
            "decision_at": closed_at,
            "source": source,
            "setup": executable,
        }

    return {"status": "NO_EVENT", "decision_at": after_at}


def _max_loss_streak(
    rows: list[dict[str, object]],
    *,
    material_threshold: Decimal | None = None,
) -> int:
    current = 0
    maximum = 0
    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        value = _d(row["capital_weighted_net_r"])
        is_loss = value < 0
        if material_threshold is not None:
            is_loss = value <= -material_threshold
        if is_loss:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def _annual_blocks(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
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
                "positive": (
                    bool(selected)
                    and _d(metrics["total_r"]) > 0
                ),
            }
        )
    return blocks


def _objectives(
    rows: list[dict[str, object]],
    metrics: dict[str, object],
    mc: dict[str, object],
    annual: list[dict[str, object]],
) -> dict[str, bool]:
    out = {
        "density_300_350": 300 <= len(rows) <= 350,
        "pf_ge_1_50": (
            metrics["profit_factor"] is not None
            and _d(metrics["profit_factor"]) >= Decimal("1.50")
        ),
        "dd_le_6": _d(metrics["max_drawdown_r"]) <= Decimal(6),
        "raw_losing_streak_le_12": (
            _max_loss_streak(rows) <= 12
        ),
        "material_losing_streak_le_8": (
            _max_loss_streak(
                rows,
                material_threshold=Decimal("0.10"),
            )
            <= 8
        ),
        "mc_positive_ge_0_90": (
            _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
        ),
        "mc_p95_dd_le_15": (
            _d(mc["p95_max_drawdown_r"]) <= Decimal(15)
        ),
    }
    if annual:
        out["both_consumed_years_positive"] = all(
            bool(block["positive"]) for block in annual
        )
    return out


def _run_variant(
    by_day: dict[date, tuple[object, ...]],
    *,
    evidence: str,
    partition: str,
    name: str,
    config: dict[str, object],
) -> dict[str, object]:
    policy = Vt31R22ExecutionPolicy()
    status: Counter[str] = Counter()
    quality_counts: Counter[int] = Counter()
    risk_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    rows: list[dict[str, object]] = []

    minimum_score = int(cast(int, config["minimum_score"]))
    hard_veto = bool(config["hard_negative_veto"])
    translation_mode = cast(str, config["translation"])
    risk_mode = cast(str, config["risk_mode"])

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        cursor = cast(datetime, getattr(reference[-1], "closed_at"))
        executions = 0

        for _ in range(MAX_SOURCE_CYCLES_PER_DAY):
            if executions >= MAX_EXECUTIONS_PER_DAY:
                status["execution-cap-reached"] += 1
                break

            event = _next_source_event(
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
                cursor = cast(datetime, event["decision_at"])
                continue
            if event_status != "SOURCE":
                raise AssertionError(event_status)

            source = cast(Vt31R22SourceSetup, event["source"])
            current_setup = cast(Vt31R22ExecutableSetup, event["setup"])
            decision_at = cast(datetime, event["decision_at"])
            features = reversal._features(
                day_bars=day_bars,
                source=source,
                setup=current_setup,
            )
            score, reasons, is_hard_negative = _quality(features)
            quality_counts[score] += 1

            if hard_veto and is_hard_negative:
                status["quality-hard-veto"] += 1
                cursor = decision_at
                continue
            if score < minimum_score:
                status["quality-score-veto"] += 1
                cursor = decision_at
                continue

            setup = _research_setup(
                source,
                current_setup,
                score=score,
                mode=translation_mode,
                variant=name,
                decision_at=decision_at,
            )
            if setup is None:
                status["translation-non-executable"] += 1
                cursor = decision_at
                continue

            outcome = baseline._simulate(day_bars, setup)
            status[f"outcome-{outcome['status']}"] += 1
            if outcome.get("status") != "terminal":
                # An admitted pending hypothesis remains sovereign until its
                # source window expiry. Do not manufacture another concurrent
                # trade after a no-fill/censored admitted setup.
                break

            risk = _risk_for(score, risk_mode)
            raw_r = _d(outcome["r_multiple"])
            capital_r = risk * (raw_r - FRICTION)
            row = dict(outcome)
            row.update(
                {
                    "partition": partition,
                    "local_date": local_day.isoformat(),
                    "event_index": executions + 1,
                    "reversal_quality_score": score,
                    "reversal_quality_reasons": list(reasons),
                    "reversal_quality_hard_negative": is_hard_negative,
                    "translation_mode": translation_mode,
                    "risk_mode": risk_mode,
                    "requested_risk_r": format(risk, "f"),
                    "capital_weighted_net_r": format(capital_r, "f"),
                    "reclaim_depth_ref": features["reclaim_depth_ref"],
                    "confirmation_displacement_ref": features[
                        "confirmation_displacement_ref"
                    ],
                    "confirmation_penetration_ref": features[
                        "confirmation_penetration_ref"
                    ],
                    "confirmation_body_fraction": features[
                        "confirmation_body_fraction"
                    ],
                    "confirmation_minute": features[
                        "confirmation_minute"
                    ],
                    "risk_ref": features["risk_ref"],
                    "future_label_used": False,
                }
            )
            rows.append(row)
            risk_counts[format(risk, "f")] += 1
            family_counts[setup.selected_family.value] += 1
            executions += 1

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
        variant=f"{IDENTITY}:{name}:{partition}",
    )
    annual = (
        _annual_blocks(rows)
        if partition == "consumed_holdout"
        else []
    )
    objectives = _objectives(rows, metrics, mc, annual)
    return {
        "trade_count": len(rows),
        "metrics": metrics,
        "raw_max_losing_streak": _max_loss_streak(rows),
        "material_max_losing_streak_010r": _max_loss_streak(
            rows,
            material_threshold=Decimal("0.10"),
        ),
        "monte_carlo": mc,
        "annual_blocks": annual,
        "quality_score_counts": {
            str(key): value for key, value in sorted(quality_counts.items())
        },
        "risk_counts": dict(sorted(risk_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "status_counts": dict(sorted(status.items())),
        "objectives": objectives,
        "passes_all_objectives": all(objectives.values()),
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    if silver.SOURCE_SHA256 != EXPECTED_SOURCE_SHA256:
        raise AssertionError("Silver Bullet source SHA changed")
    if silver.METHODOLOGY_ID != EXPECTED_METHODOLOGY_ID:
        raise AssertionError("Silver Bullet methodology identity changed")

    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("reversal quality frontier requires NAS100")

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
        name: _run_variant(
            by_day,
            evidence=evidence,
            partition=partition,
            name=name,
            config=config,
        )
        for name, config in VARIANTS.items()
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
            "silver_bullet_source_frozen": True,
            "source_sha256": silver.SOURCE_SHA256,
            "methodology_id": silver.METHODOLOGY_ID,
            "consumed_evidence_only": True,
            "future_journey_labels_used_at_runtime": False,
            "terminal_pnl_used_at_runtime": False,
            "fold_identity_used_at_runtime": False,
            "h4_primary_causal_feature": False,
            "h1_primary_causal_feature": False,
            "structural_stop_changed": False,
            "opposite_reference_target_changed": False,
            "three_r_breakeven_changed": False,
            "maximum_executions_per_day": MAX_EXECUTIONS_PER_DAY,
            "new_event_requires_new_post_cursor_raid_confirmation": True,
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
