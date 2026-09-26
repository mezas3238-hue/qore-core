"""Cognitive blocker census for the true-2R Capitalizer research state.

This is a declarative readiness audit. It consumes only already-frozen research
artifacts and classifies each cognitive layer as BOUND, PARTIAL, RESEARCH_OPEN,
LIVE_ONLY, or UNBOUND.

It does not create a trade filter, call the final cognitive engine, inspect
current-trade outcomes, or promote any rule. The purpose is to separate:
- historical evidence that is already causally bound;
- historical cognitive layers that remain research-open;
- facts that are inherently live-only and cannot be fabricated in replay.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_BLOCKER_CENSUS_2R_V1"
CONTROL_TRADES = 948


class CognitiveReadinessStatus(StrEnum):
    BOUND = "BOUND"
    PARTIAL = "PARTIAL"
    RESEARCH_OPEN = "RESEARCH_OPEN"
    LIVE_ONLY = "LIVE_ONLY"
    UNBOUND = "UNBOUND"


@dataclass(frozen=True, slots=True)
class CognitiveLayerReadiness:
    layer: str
    status: CognitiveReadinessStatus
    bound_trades: int
    total_trades: int
    coverage: str
    blocks_historical_master_replay: bool
    blocks_final_execution_decision: bool
    reasons: tuple[str, ...]


def _load_one(root: Path, pattern: str, *, identity: str) -> dict[str, Any]:
    paths = sorted(root.rglob(pattern))
    if len(paths) != 1:
        raise ValueError(f"expected one artifact for {pattern}, got {len(paths)}")
    payload = json.loads(paths[0].read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"artifact {pattern} must be a JSON object")
    if payload.get("identity") != identity:
        raise ValueError(f"unexpected identity for {pattern}")
    return payload


def _coverage(bound: int, total: int = CONTROL_TRADES) -> str:
    if total <= 0 or bound < 0 or bound > total:
        raise ValueError("invalid readiness coverage")
    return str(Decimal(bound) / Decimal(total))


def _layer(
    *,
    name: str,
    status: CognitiveReadinessStatus,
    bound: int,
    historical_blocker: bool,
    final_blocker: bool,
    reasons: tuple[str, ...],
) -> CognitiveLayerReadiness:
    return CognitiveLayerReadiness(
        layer=name,
        status=status,
        bound_trades=bound,
        total_trades=CONTROL_TRADES,
        coverage=_coverage(bound),
        blocks_historical_master_replay=historical_blocker,
        blocks_final_execution_decision=final_blocker,
        reasons=reasons,
    )


def build_report(
    rebase_root: Path,
    perception_root: Path,
    regime_root: Path,
    destination_root: Path,
    fingerprint_root: Path,
    evidence_root: Path,
    collision_root: Path,
) -> dict[str, Any]:
    rebase = _load_one(
        rebase_root,
        "capitalizer-cognitive-economic-rebase-2r-v1.json",
        identity="QORE_CAPITALIZER_COGNITIVE_ECONOMIC_REBASE_2R_V1",
    )
    perception = _load_one(
        perception_root,
        "capitalizer-cognitive-perception-bars-complete-binding-2r-v2.json",
        identity="QORE_CAPITALIZER_COGNITIVE_PERCEPTION_BARS_COMPLETE_BINDING_2R_V2",
    )
    regime = _load_one(
        regime_root,
        "capitalizer-cognitive-regime-evidence-binding-audit-2r-v1.json",
        identity="QORE_CAPITALIZER_COGNITIVE_REGIME_EVIDENCE_BINDING_AUDIT_2R_V1",
    )
    destination = _load_one(
        destination_root,
        "capitalizer-nine-market-destination-untouched-persistence-matrix-2r-v1.json",
        identity=(
            "QORE_CAPITALIZER_COGNITIVE_DESTINATION_UNTOUCHED_"
            "PERSISTENCE_MATRIX_2R_V1"
        ),
    )
    fingerprint = _load_one(
        fingerprint_root,
        "capitalizer-cognitive-failure-fingerprint-audit-2y-v1.json",
        identity="QORE_CAPITALIZER_COGNITIVE_FAILURE_FINGERPRINT_AUDIT_2Y_V1",
    )
    evidence = _load_one(
        evidence_root,
        "capitalizer-cognitive-evidence-binding-audit-2y-v2.json",
        identity="QORE_CAPITALIZER_COGNITIVE_EVIDENCE_BINDING_AUDIT_2Y_V2",
    )
    collision = _load_one(
        collision_root,
        "capitalizer-cognitive-simultaneous-factor-collision-atlas-2r-v1.json",
        identity=(
            "QORE_CAPITALIZER_COGNITIVE_SIMULTANEOUS_FACTOR_"
            "COLLISION_ATLAS_2R_V1"
        ),
    )

    if int(rebase["control_trades"]) != CONTROL_TRADES:
        raise ValueError("cognitive census control population drift")
    for payload in (perception, regime, fingerprint, evidence, collision):
        if int(payload["control_trades"]) != CONTROL_TRADES:
            raise ValueError("cognitive census artifact population drift")

    evidence_coverage = dict(evidence["binding_coverage"])
    source_bound = int(evidence_coverage["source_microstructure"])
    journey_bound = int(evidence_coverage["day_session_journey"])
    exposure_bound = int(evidence_coverage["baseline_portfolio_exposure"])
    slot_bound = int(evidence_coverage["baseline_slot_state"])
    bars_bound = int(
        perception["bars_complete_state_counts"]["SUPPORTED_TRUE"]
    )
    regime_bound = int(regime["regime_evidence_bound_trades"])
    destination_bound = int(destination["departure_bound_trades"])
    destination_survivors = int(
        destination["at_least_one_candidate_untouched_through_entry_trades"]
    )
    fingerprint_bound = int(fingerprint["fingerprint_candidate_coverage"])
    collision_candidates = int(collision["collision_candidate_count"])

    if bars_bound != CONTROL_TRADES:
        raise ValueError("bars_complete is not globally bound")
    if perception["quote_fresh_evidence_bound"] is not False:
        raise ValueError("historical quote freshness must remain unbound")
    if regime["regime_intelligence_supported"] is not False:
        raise ValueError("regime intelligence unexpectedly promoted")
    if destination["destination_intelligence_supported"] is not False:
        raise ValueError("destination intelligence unexpectedly promoted")
    if fingerprint["runtime_failure_fingerprint_selected"] is not False:
        raise ValueError("failure fingerprint unexpectedly promoted")
    if fingerprint["loss_memory_resolution_bound"] is not False:
        raise ValueError("loss-memory resolution unexpectedly bound")
    if collision["collision_policy_selected"] is not False:
        raise ValueError("collision policy unexpectedly selected")
    if collision["combined_rule_selected"] is not False:
        raise ValueError("combined collision rule unexpectedly selected")

    layers = (
        _layer(
            name="SOURCE_MICROSTRUCTURE",
            status=CognitiveReadinessStatus.BOUND,
            bound=source_bound,
            historical_blocker=False,
            final_blocker=False,
            reasons=("CAUSAL_SOURCE_EVIDENCE_COMPLETE",),
        ),
        _layer(
            name="SESSION_DAY_JOURNEY",
            status=CognitiveReadinessStatus.BOUND,
            bound=journey_bound,
            historical_blocker=False,
            final_blocker=False,
            reasons=("DAY_SESSION_JOURNEY_RECONSTRUCTED_CAUSALLY",),
        ),
        _layer(
            name="PORTFOLIO_EXPOSURE_BASELINE",
            status=CognitiveReadinessStatus.BOUND,
            bound=exposure_bound,
            historical_blocker=False,
            final_blocker=False,
            reasons=("BASELINE_ACTIVE_EXPOSURE_RECONSTRUCTED",),
        ),
        _layer(
            name="SESSION_SLOT_STATE",
            status=CognitiveReadinessStatus.BOUND,
            bound=slot_bound,
            historical_blocker=False,
            final_blocker=False,
            reasons=("MAX3_SLOT_STATE_RECONSTRUCTED",),
        ),
        _layer(
            name="PERCEPTION_BARS_COMPLETE",
            status=CognitiveReadinessStatus.BOUND,
            bound=bars_bound,
            historical_blocker=False,
            final_blocker=False,
            reasons=(
                "946_NATIVE_M1_CONTIGUOUS",
                "2_AUDJPY_SPANS_EXPLAINED_BY_ZERO_BID_ASK_TICKS",
            ),
        ),
        _layer(
            name="PERCEPTION_QUOTE_FRESH",
            status=CognitiveReadinessStatus.LIVE_ONLY,
            bound=0,
            historical_blocker=False,
            final_blocker=True,
            reasons=("HISTORICAL_REPLAY_CANNOT_PROVE_LIVE_FEED_AGE",),
        ),
        _layer(
            name="PERCEPTION_FULL_STATUS",
            status=CognitiveReadinessStatus.UNBOUND,
            bound=0,
            historical_blocker=True,
            final_blocker=True,
            reasons=("QUOTE_FRESH_UNBOUND",),
        ),
        _layer(
            name="REGIME_DESCRIPTIVE_EVIDENCE",
            status=CognitiveReadinessStatus.PARTIAL,
            bound=regime_bound,
            historical_blocker=True,
            final_blocker=True,
            reasons=("M5_MICRO_CONTEXT_BOUND_WITHOUT_REGIME_LABEL_PROMOTION",),
        ),
        _layer(
            name="REGIME_INTELLIGENCE",
            status=CognitiveReadinessStatus.RESEARCH_OPEN,
            bound=0,
            historical_blocker=True,
            final_blocker=True,
            reasons=("REGIME_FAMILY_ID_NOT_SELECTED",),
        ),
        _layer(
            name="DESTINATION_DEPARTURE_CONTEXT",
            status=CognitiveReadinessStatus.PARTIAL,
            bound=destination_bound,
            historical_blocker=True,
            final_blocker=True,
            reasons=("EXACT_DEPARTURE_CONTEXT_BOUND_FOR_SUBSET_ONLY",),
        ),
        _layer(
            name="DESTINATION_UNTOUCHED_TO_ENTRY",
            status=CognitiveReadinessStatus.PARTIAL,
            bound=destination_survivors,
            historical_blocker=True,
            final_blocker=True,
            reasons=("M1_TOUCH_PERSISTENCE_RECONSTRUCTED_FOR_BOUND_SUBSET",),
        ),
        _layer(
            name="DESTINATION_INTELLIGENCE",
            status=CognitiveReadinessStatus.RESEARCH_OPEN,
            bound=0,
            historical_blocker=True,
            final_blocker=True,
            reasons=(
                "STRUCTURAL_CURRENT_AT_ENTRY_NOT_PROVEN",
                "DESTINATION_AVAILABLE_AT_ENTRY_NOT_PROMOTED",
            ),
        ),
        _layer(
            name="FAILURE_FINGERPRINT_CANDIDATE",
            status=CognitiveReadinessStatus.BOUND,
            bound=fingerprint_bound,
            historical_blocker=False,
            final_blocker=False,
            reasons=("OUTCOME_FREE_CAUSAL_FINGERPRINT_CANDIDATE_BUILT",),
        ),
        _layer(
            name="LOSS_MEMORY_RESOLUTION",
            status=CognitiveReadinessStatus.RESEARCH_OPEN,
            bound=0,
            historical_blocker=True,
            final_blocker=True,
            reasons=("UNRESOLVED_FAILURE_LIFETIME_SEMANTICS_NOT_DEFINED",),
        ),
        _layer(
            name="SIMULTANEOUS_OPPORTUNITY_COMPETITION",
            status=CognitiveReadinessStatus.PARTIAL,
            bound=collision_candidates,
            historical_blocker=True,
            final_blocker=True,
            reasons=("11_SAME_TIMESTAMP_FACTOR_COLLISION_CLUSTERS_IDENTIFIED",),
        ),
        _layer(
            name="FULL_OPPORTUNITY_COMPETITION",
            status=CognitiveReadinessStatus.RESEARCH_OPEN,
            bound=0,
            historical_blocker=True,
            final_blocker=True,
            reasons=("NO_COLLISION_POLICY_SELECTED_OR_PROMOTED",),
        ),
        _layer(
            name="EXECUTION_QUALITY",
            status=CognitiveReadinessStatus.LIVE_ONLY,
            bound=0,
            historical_blocker=False,
            final_blocker=True,
            reasons=("SPREAD_SLIPPAGE_COMMISSION_LATENCY_REQUIRE_MEASURED_EXECUTION",),
        ),
    )

    historical_blockers = tuple(
        item.layer for item in layers if item.blocks_historical_master_replay
    )
    final_blockers = tuple(
        item.layer for item in layers if item.blocks_final_execution_decision
    )
    bound_layers = tuple(
        item.layer for item in layers if item.status is CognitiveReadinessStatus.BOUND
    )
    partial_layers = tuple(
        item.layer for item in layers if item.status is CognitiveReadinessStatus.PARTIAL
    )
    live_only_layers = tuple(
        item.layer for item in layers if item.status is CognitiveReadinessStatus.LIVE_ONLY
    )

    return {
        "identity": IDENTITY,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": CONTROL_TRADES,
        "control_metrics": rebase["control_metrics"],
        "layers": [asdict(item) for item in layers],
        "bound_layers": bound_layers,
        "partial_layers": partial_layers,
        "historical_research_blockers": historical_blockers,
        "live_only_layers": live_only_layers,
        "final_execution_blockers": final_blockers,
        "historical_master_replay_ready": len(historical_blockers) == 0,
        "final_cognitive_engine_ready": len(final_blockers) == 0,
        "current_trade_outcome_visible_to_census": False,
        "numeric_confidence_fabricated": False,
        "missing_evidence_fabricated": False,
        "runtime_engine_called": False,
        "strategy_rules_changed": False,
        "cognitive_rules_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "CLOSE_REGIME_DESTINATION_LOSS_MEMORY_AND_FULL_COMPETITION_"
            "BEFORE_MASTER_REPLAY"
        ),
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cognitive-blocker-census-2r-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("perception_root", type=Path)
    parser.add_argument("regime_root", type=Path)
    parser.add_argument("destination_root", type=Path)
    parser.add_argument("fingerprint_root", type=Path)
    parser.add_argument("evidence_root", type=Path)
    parser.add_argument("collision_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(
        args.rebase_root,
        args.perception_root,
        args.regime_root,
        args.destination_root,
        args.fingerprint_root,
        args.evidence_root,
        args.collision_root,
    )
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
