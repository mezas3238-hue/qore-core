"""R21 full-CIBO CAUTIOUS/MIXED subtype causal memory.

Consumed-evidence research only.

The objective is not to blacklist CAUTIOUS or MIXED. It decomposes those
memory states into structurally interpretable subtypes:

RECOVERABLE_NOW:
    NEXT_SOURCE_OPEN reaches at least one active CIBO DOL before Protected
    Swing invalidation/lifecycle end.
WAIT_FOR_CONFIRMATION:
    immediate entry does not preserve journey capacity, but the already
    canonical CISD_THRESHOLD_RETEST entry does.
ABSTAIN_STRUCTURAL:
    neither entry timing preserves journey capacity.
UNRESOLVED:
    historical temporal blocks disagree or support is insufficient.

No PnL, return, PF, drawdown, or economic score is used to assign labels.
A subtype is stable only when the same structural label has a strict majority
in every temporal block and each block meets a fixed governance sample floor.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import (
    cibo_xauusd_trader_memory_bridge_v1 as cibo_memory,
)
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r9_journey_divergence_forensics as divergence,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r15_cibo_first_market_brain as r15,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r18_memory_driven_cibo_brain as r18,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R21_CAUTIOUS_MIXED_SUBTYPE_MEMORY_V1"

RECOVERABLE = "RECOVERABLE_NOW"
WAIT = "WAIT_FOR_CONFIRMATION"
ABSTAIN = "ABSTAIN_STRUCTURAL"
UNRESOLVED = "UNRESOLVED"

PERIODS = (
    "early_2016_2020",
    "transition_2021_2023",
    "recent_2024_2026",
)
MIN_OBSERVATIONS_PER_PERIOD = 5

SIGNATURE_FIELDS = (
    "memory_state",
    "source_timeframe",
    "fvg_before_entry",
    "cisd_progress_bucket",
    "protected_risk_range_bucket",
    "source_range_state_bucket",
    "brain_posture",
)


def _period(year: int) -> str:
    if 2016 <= year <= 2020:
        return "early_2016_2020"
    if 2021 <= year <= 2023:
        return "transition_2021_2023"
    if 2024 <= year <= 2026:
        return "recent_2024_2026"
    return "outside"


def _signature(row: dict[str, Any]) -> str:
    return "|".join(str(row[field]) for field in SIGNATURE_FIELDS)


def _strict_majority(counts: Counter[str]) -> str | None:
    total = sum(counts.values())
    if total == 0:
        return None
    top = counts.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return None
    if top[0][1] * 2 <= total:
        return None
    return top[0][0]


def _stable_label(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_period: dict[str, Counter[str]] = {
        period: Counter() for period in PERIODS
    }
    for row in rows:
        period = str(row["period"])
        if period in by_period:
            by_period[period][str(row["structural_label"])] += 1

    majorities: dict[str, str | None] = {}
    sufficient = True
    for period in PERIODS:
        counts = by_period[period]
        n = sum(counts.values())
        if n < MIN_OBSERVATIONS_PER_PERIOD:
            sufficient = False
        majorities[period] = _strict_majority(counts)

    labels = {label for label in majorities.values() if label is not None}
    stable = (
        sufficient
        and len(labels) == 1
        and all(majorities[period] is not None for period in PERIODS)
    )
    classification = next(iter(labels)) if stable else UNRESOLVED

    return {
        "classification": classification,
        "stable_across_all_periods": stable,
        "period_counts": {
            period: dict(by_period[period]) for period in PERIODS
        },
        "period_majorities": majorities,
        "observations": len(rows),
    }


def _entry_capacity(
    *,
    setup: r3.Setup,
    target_rows: Sequence[r3.TargetCandidate],
    evidence: Any,
    opens: Sequence[datetime],
    entry_mode: str,
) -> dict[str, Any]:
    fill = r3._entry(setup, evidence, opens, entry_mode)
    if fill is None:
        return {
            "filled": False,
            "capable": False,
            "entry_at": None,
            "active_dol_count": 0,
            "nearest_dol_r": None,
            "failure_stage": "NO_FILL_OR_INVALIDATED_BEFORE_FILL",
        }

    entry_at, entry = fill
    active = r15._all_active_targets(
        target_rows,
        at=entry_at,
        side=setup.context.signal.side,
        anchor=entry,
    )
    ladder = r15._distinct_target_ladder(active, anchor=entry)
    if not ladder:
        return {
            "filled": True,
            "capable": False,
            "entry_at": entry_at.isoformat(),
            "active_dol_count": 0,
            "nearest_dol_r": None,
            "failure_stage": "NO_ACTIVE_DOL_AT_FILL",
        }

    trade = r15._simulate_selected(
        setup,
        entry_mode=entry_mode,
        entry_at=entry_at,
        entry=entry,
        target_row=ladder[0],
        evidence=evidence,
        opens=opens,
    )
    if trade is None:
        return {
            "filled": True,
            "capable": False,
            "entry_at": entry_at.isoformat(),
            "active_dol_count": len(ladder),
            "nearest_dol_r": None,
            "failure_stage": "INVALID_EXECUTION_GEOMETRY",
        }

    path = divergence._path_diagnostic(
        trade,
        target_rows,
        evidence,
        opens,
    )
    return {
        "filled": True,
        "capable": int(path["touched_dol_count"]) > 0,
        "entry_at": entry_at.isoformat(),
        "active_dol_count": int(path["active_dol_count"]),
        "nearest_dol_r": (
            None
            if path["nearest_dol_distance_r"] is None
            else str(path["nearest_dol_distance_r"])
        ),
        "failure_stage": str(path["journey_failure_stage"]),
    }


def _label(
    immediate: dict[str, Any],
    retest: dict[str, Any],
) -> str:
    if bool(immediate["capable"]):
        return RECOVERABLE
    if bool(retest["capable"]):
        return WAIT
    return ABSTAIN


def run(
    source_root: Path,
    target_root: Path,
    dossier_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(source_root)
    if evidence.symbol != r3.SYMBOL or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD corpus")

    memory_store, dossier_manifest = cibo_memory.build_memory_store(dossier_root)
    episodes, source_index = repair._load_targets_fail_closed(target_root)

    original_open, original_close = r1.EVAL_OPEN, r1.EVAL_CLOSE
    try:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = r3.EVAL_OPEN, r3.EVAL_CLOSE
        setups, funnel = r3._build_setups(evidence)
    finally:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = original_open, original_close

    opens = tuple(bar.opened_at for bar in evidence.bars)
    d1 = r5._aggregate(evidence.bars, "D1")
    h4 = r5._aggregate(evidence.bars, "H4")

    ledger: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()

    for setup in setups:
        signal = setup.context.signal
        episode_id = source_index.get(
            (
                signal.cisd_at,
                signal.side.value,
                setup.context.timeframe,
                signal.target,
            )
        )
        if episode_id is None:
            counts["UNMATCHED_CAUSAL_EPISODE"] += 1
            continue

        memory = cibo_memory.context_memory(
            memory_store,
            timeframe=setup.context.timeframe,
            side=signal.side.value,
            session=setup.context.session,
            prior_body_alignment=setup.context.prior_body_alignment,
            fvg_before_entry=setup.context.fvg_before_entry,
            exact_equal_liquidity=setup.context.exact_equal_liquidity,
        )
        if memory.state not in {"CAUTIOUS", "MIXED"}:
            counts["OUTSIDE_CAUTIOUS_MIXED"] += 1
            continue

        if (
            setup.context.protected_risk_range_bucket
            in r18.LOW_CAPACITY_RISK_BUCKETS
        ):
            counts["PREEXISTING_LOW_CAPACITY_ABSTAIN"] += 1
            continue

        regime = r5._regime_features(
            {"entry_at": signal.entry_at.isoformat(), "side": signal.side.value},
            d1,
            h4,
        )
        posture = r15._market_posture(regime)
        target_rows = episodes[episode_id]

        immediate = _entry_capacity(
            setup=setup,
            target_rows=target_rows,
            evidence=evidence,
            opens=opens,
            entry_mode="NEXT_SOURCE_OPEN",
        )
        retest = _entry_capacity(
            setup=setup,
            target_rows=target_rows,
            evidence=evidence,
            opens=opens,
            entry_mode="CISD_THRESHOLD_RETEST",
        )
        structural_label = _label(immediate, retest)
        counts[structural_label] += 1

        row = {
            "setup_at": signal.entry_at.isoformat(),
            "year": signal.entry_at.year,
            "period": _period(signal.entry_at.year),
            "memory_state": memory.state,
            "memory_support_votes": memory.support_votes,
            "memory_caution_votes": memory.caution_votes,
            "memory_mixed_votes": memory.mixed_votes,
            "source_timeframe": setup.context.timeframe,
            "side": signal.side.value,
            "session": setup.context.session,
            "weekday": setup.context.weekday,
            "prior_body_alignment": setup.context.prior_body_alignment,
            "fvg_before_entry": setup.context.fvg_before_entry,
            "exact_equal_liquidity": setup.context.exact_equal_liquidity,
            "raid_depth_range_bucket": setup.context.raid_depth_range_bucket,
            "reclaim_latency_bucket": setup.context.reclaim_latency_bucket,
            "cisd_progress_bucket": setup.context.cisd_progress_bucket,
            "protected_risk_range_bucket": (
                setup.context.protected_risk_range_bucket
            ),
            "source_range_state_bucket": (
                setup.context.source_range_state_bucket
            ),
            "brain_posture": posture,
            "d1_trend_state_20": regime["d1_trend_state_20"],
            "h4_trend_state_20": regime["h4_trend_state_20"],
            "d1_range_5v20": regime["d1_range_5v20"],
            "h4_range_3v20": regime["h4_range_3v20"],
            "structural_label": structural_label,
            "immediate": immediate,
            "retest": retest,
        }
        row["signature"] = _signature(row)
        ledger.append(row)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ledger:
        grouped[str(row["signature"])].append(row)

    subtype_memory = {
        signature: {
            **_stable_label(rows),
            "signature_fields": {
                field: rows[0][field] for field in SIGNATURE_FIELDS
            },
        }
        for signature, rows in sorted(grouped.items())
    }

    stable_counts = Counter(
        str(item["classification"])
        for item in subtype_memory.values()
    )
    stable_signatures = {
        signature: item
        for signature, item in subtype_memory.items()
        if item["classification"] != UNRESOLVED
    }

    covered_rows = sum(
        item["observations"] for item in stable_signatures.values()
    )

    payload = {
        "schema": "qore.turtle_soup_xauusd_r21.cautious_mixed_subtype_memory.v1",
        "identity": IDENTITY,
        "evidence_status": (
            "CONSUMED_10Y_STRUCTURAL_SUBTYPE_MEMORY_NOT_FRESH_HOLDOUT"
        ),
        "knowledge_sources": {
            "full_cibo_dossier": cibo_memory.DOSSIER_IDENTITY,
            "full_cibo_dossier_run_id": cibo_memory.DOSSIER_RUN_ID,
            "full_cibo_dossier_artifact_id": cibo_memory.DOSSIER_ARTIFACT_ID,
            "target_destination": r3.TARGET_IDENTITY,
        },
        "classification_contract": {
            "labels": [RECOVERABLE, WAIT, ABSTAIN, UNRESOLVED],
            "RECOVERABLE_NOW": (
                "NEXT_SOURCE_OPEN touches any active CIBO DOL before invalidation/lifecycle"
            ),
            "WAIT_FOR_CONFIRMATION": (
                "immediate fails capacity but CISD_THRESHOLD_RETEST preserves capacity"
            ),
            "ABSTAIN_STRUCTURAL": (
                "neither immediate nor retest preserves journey capacity"
            ),
            "UNRESOLVED": (
                "temporal blocks disagree or fixed sample floor is not met"
            ),
            "minimum_observations_per_period": MIN_OBSERVATIONS_PER_PERIOD,
            "strict_majority_required_each_period": True,
            "same_label_required_all_periods": True,
            "pnl_used": False,
            "profit_factor_used": False,
            "drawdown_used": False,
            "automatic_threshold_search": False,
        },
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setups": len(setups),
            "ledger_rows": len(ledger),
            "counts": dict(counts),
            "ambiguous_bindings_fail_closed": repair._LAST_AMBIGUOUS_KEYS,
        },
        "subtype_memory": {
            "signature_fields": list(SIGNATURE_FIELDS),
            "total_signatures": len(subtype_memory),
            "classification_counts": dict(stable_counts),
            "stable_signatures": len(stable_signatures),
            "covered_observations": covered_rows,
            "coverage_of_cautious_mixed_eligible": (
                None
                if not ledger
                else str(covered_rows / len(ledger))
            ),
            "signatures": subtype_memory,
        },
        "dossier_manifest": dossier_manifest,
        "governance": {
            "diagnostic_memory_only": True,
            "fresh_holdout_consumed": False,
            "rule_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
        "funnel": funnel,
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "r21-cautious-mixed-subtype-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r21-cautious-mixed-subtype-ledger.json").write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    )
    (output / "r21-subtype-memory.json").write_text(
        json.dumps(subtype_memory, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: module SOURCE_ROOT TARGET_ROOT DOSSIER_ROOT OUTPUT_DIR"
        )
    print(
        json.dumps(
            run(
                Path(sys.argv[1]),
                Path(sys.argv[2]),
                Path(sys.argv[3]),
                Path(sys.argv[4]),
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
