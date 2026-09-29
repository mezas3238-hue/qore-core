"""Historical cognitive-gate replay readiness audit for Capitalizer V47-P0.

This audit is intentionally pre-economic. It verifies whether the frozen
cognitive architecture can produce CapitalizerCognitiveGateDecision
historically for new canonical source candidates without fabricating inputs.

Frozen in PR #623 comment 5889396977.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_attention as attention,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_blocker_census_2r_v1 as blocker_census,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_pressure as pressure,
)
from qore.infrastructure.trader_lab import (
    capitalizer_confidence as confidence,
)
from qore.infrastructure.trader_lab import (
    capitalizer_decision_sovereignty as sovereignty,
)
from qore.infrastructure.trader_lab import (
    capitalizer_hypothesis_lifecycle as lifecycle,
)
from qore.infrastructure.trader_lab import (
    capitalizer_master_cognitive_frame as master_frame,
)
from qore.infrastructure.trader_lab import (
    capitalizer_metacognition_v2 as metacognition,
)
from qore.infrastructure.trader_lab import (
    capitalizer_opportunity_competition as competition,
)
from qore.infrastructure.trader_lab import (
    capitalizer_perception_integrity as perception,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regime_intelligence as regime,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_historical_replay_adapter_v46 as v46_adapter,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_GATE_HISTORICAL_REPLAY_READINESS_V47_P0"
PREDECLARATION_COMMENT_ID = 5889396977


class HistoricalReadinessStatus(StrEnum):
    HISTORICAL_RESOLVER_READY = "HISTORICAL_RESOLVER_READY"
    DERIVABLE_FROM_V46_CANONICAL_FACTS = "DERIVABLE_FROM_V46_CANONICAL_FACTS"
    COMPOSER_READY_REQUIRES_UNBOUND_INPUT = (
        "COMPOSER_READY_REQUIRES_UNBOUND_INPUT"
    )
    RESEARCH_OPEN = "RESEARCH_OPEN"
    LIVE_ONLY = "LIVE_ONLY"


@dataclass(frozen=True, slots=True)
class CognitiveDependency:
    key: str
    status: HistoricalReadinessStatus
    pass_critical: bool
    blocker: bool
    evidence: str


def _source(module: Any) -> str:
    return inspect.getsource(module)


def build_report() -> dict[str, Any]:
    attention_source = _source(attention)
    confidence_source = _source(confidence)
    perception_source = _source(perception)
    regime_source = _source(regime)
    master_source = _source(master_frame)
    pressure_source = _source(pressure)
    competition_source = _source(competition)
    lifecycle_source = _source(lifecycle)
    sovereignty_source = _source(sovereignty)
    census_source = _source(blocker_census)
    v46_source = _source(v46_adapter)

    hypothesis_composer = (
        "transition_hypothesis" in lifecycle_source
        and "CapitalizerHypothesisStage" in lifecycle_source
    )
    historical_hypothesis_resolver = (
        "historical" in lifecycle_source.lower()
        and "source_event" in lifecycle_source
        and "replay" in lifecycle_source.lower()
    )
    attention_composer = "derive_attention_state" in attention_source
    knowledge_composer = "assess_knowledge_state" in confidence_source
    perception_composer = "assess_perception_integrity" in perception_source
    regime_composer = "assess_regime" in regime_source
    cognitive_gate_composer = "assess_cognitive_gate" in sovereignty_source
    pressure_composer = "assess_cognitive_pressure" in pressure_source
    competition_composer = (
        "build_opportunity_competition_state" in competition_source
    )
    master_composer = "build_master_cognitive_frame" in master_source

    quote_fresh_live_only = (
        "HISTORICAL_REPLAY_CANNOT_PROVE_LIVE_FEED_AGE" in census_source
        and 'name="PERCEPTION_QUOTE_FRESH"' in census_source
        and "CognitiveReadinessStatus.LIVE_ONLY" in census_source
    )
    regime_research_open = (
        "final nine market families are deliberately not hard-coded"
        in regime_source
        and 'name="REGIME_INTELLIGENCE"' in census_source
        and "REGIME_FAMILY_ID_NOT_SELECTED" in census_source
    )
    loss_memory_research_open = (
        'name="LOSS_MEMORY_RESOLUTION"' in census_source
        and "UNRESOLVED_FAILURE_LIFETIME_SEMANTICS_NOT_DEFINED"
        in census_source
    )
    full_competition_research_open = (
        'name="FULL_OPPORTUNITY_COMPETITION"' in census_source
        and "NO_COLLISION_POLICY_SELECTED_OR_PROMOTED" in census_source
    )

    v46_destination_ready = (
        "structural_target" in v46_source
        and "passes_to_qore_risk" in v46_source
        and "trade_plan" in v46_source
    )
    v46_provenance_ready = (
        "evidence_timestamps" in v46_source
        and "future" in v46_source.lower()
    )

    dependencies = (
        CognitiveDependency(
            "HYPOTHESIS_STAGE",
            (
                HistoricalReadinessStatus.HISTORICAL_RESOLVER_READY
                if historical_hypothesis_resolver
                else HistoricalReadinessStatus.COMPOSER_READY_REQUIRES_UNBOUND_INPUT
            ),
            True,
            not historical_hypothesis_resolver,
            (
                "Lifecycle transition composer exists, but no canonical "
                "historical source-event -> decision-stage resolver is bound."
            ),
        ),
        CognitiveDependency(
            "DECISION_ATTENTION",
            (
                HistoricalReadinessStatus.COMPOSER_READY_REQUIRES_UNBOUND_INPUT
                if attention_composer
                else HistoricalReadinessStatus.RESEARCH_OPEN
            ),
            True,
            True,
            "derive_attention_state requires decision-ready hypothesis + KNOWN knowledge.",
        ),
        CognitiveDependency(
            "KNOWLEDGE_STATE_KNOWN",
            (
                HistoricalReadinessStatus.COMPOSER_READY_REQUIRES_UNBOUND_INPUT
                if knowledge_composer
                else HistoricalReadinessStatus.RESEARCH_OPEN
            ),
            True,
            True,
            (
                "assess_knowledge_state requires provenance-bound calibration; "
                "no generic calibration binder exists for new canonical candidates."
            ),
        ),
        CognitiveDependency(
            "PERCEPTION_BARS_ORDER_SESSION_PROVENANCE",
            HistoricalReadinessStatus.HISTORICAL_RESOLVER_READY,
            True,
            False,
            "V46 provider-native census proved causal bars/time/session substrate.",
        ),
        CognitiveDependency(
            "PERCEPTION_QUOTE_FRESH",
            (
                HistoricalReadinessStatus.LIVE_ONLY
                if quote_fresh_live_only
                else HistoricalReadinessStatus.RESEARCH_OPEN
            ),
            True,
            True,
            (
                "Frozen blocker census classifies quote freshness as LIVE_ONLY; "
                "no quote-age threshold may be invented."
            ),
        ),
        CognitiveDependency(
            "PERCEPTION_FULL_STATUS",
            (
                HistoricalReadinessStatus.COMPOSER_READY_REQUIRES_UNBOUND_INPUT
                if perception_composer
                else HistoricalReadinessStatus.RESEARCH_OPEN
            ),
            True,
            True,
            "Perception GOOD cannot be established while quote_fresh is unbound.",
        ),
        CognitiveDependency(
            "REGIME_RESOLUTION_SUPPORTED",
            (
                HistoricalReadinessStatus.RESEARCH_OPEN
                if regime_research_open
                else HistoricalReadinessStatus.COMPOSER_READY_REQUIRES_UNBOUND_INPUT
            ),
            True,
            True,
            (
                "assess_regime exists, but final family semantics/selection are "
                "deliberately not closed."
            ),
        ),
        CognitiveDependency(
            "EVIDENCE_PROVENANCE_COMPLETE",
            (
                HistoricalReadinessStatus.DERIVABLE_FROM_V46_CANONICAL_FACTS
                if v46_provenance_ready
                else HistoricalReadinessStatus.RESEARCH_OPEN
            ),
            True,
            not v46_provenance_ready,
            "V46 rejects future evidence and binds explicit causal timestamps.",
        ),
        CognitiveDependency(
            "DESTINATION_CONTEXT_KNOWN_AVAILABLE",
            (
                HistoricalReadinessStatus.DERIVABLE_FROM_V46_CANONICAL_FACTS
                if v46_destination_ready
                else HistoricalReadinessStatus.RESEARCH_OPEN
            ),
            True,
            not v46_destination_ready,
            (
                "For accepted canonical candidates, one intact structural/HTF "
                "target supplies decision-time destination context."
            ),
        ),
        CognitiveDependency(
            "LOSS_MEMORY_RESOLUTION",
            (
                HistoricalReadinessStatus.RESEARCH_OPEN
                if loss_memory_research_open
                else HistoricalReadinessStatus.COMPOSER_READY_REQUIRES_UNBOUND_INPUT
            ),
            True,
            True,
            "Failure fingerprints exist, but unresolved-memory lifetime semantics are open.",
        ),
        CognitiveDependency(
            "COGNITIVE_PRESSURE",
            (
                HistoricalReadinessStatus.COMPOSER_READY_REQUIRES_UNBOUND_INPUT
                if pressure_composer
                else HistoricalReadinessStatus.RESEARCH_OPEN
            ),
            True,
            True,
            (
                "Pressure composer exists; same-failure/loss-cluster/upstream "
                "stop inputs are not generically bound for new canonical candidates."
            ),
        ),
        CognitiveDependency(
            "OPPORTUNITY_COMPETITION",
            (
                HistoricalReadinessStatus.COMPOSER_READY_REQUIRES_UNBOUND_INPUT
                if competition_composer and full_competition_research_open
                else HistoricalReadinessStatus.HISTORICAL_RESOLVER_READY
            ),
            True,
            full_competition_research_open,
            (
                "MAX3 slot state is reconstructible, but full simultaneous "
                "opportunity competition policy remains research-open."
            ),
        ),
        CognitiveDependency(
            "MASTER_COGNITIVE_FRAME",
            (
                HistoricalReadinessStatus.COMPOSER_READY_REQUIRES_UNBOUND_INPUT
                if master_composer
                else HistoricalReadinessStatus.RESEARCH_OPEN
            ),
            True,
            True,
            "Frame composer exists but inherits the unresolved dependencies above.",
        ),
        CognitiveDependency(
            "COGNITIVE_GATE_DECISION",
            (
                HistoricalReadinessStatus.COMPOSER_READY_REQUIRES_UNBOUND_INPUT
                if cognitive_gate_composer
                else HistoricalReadinessStatus.RESEARCH_OPEN
            ),
            True,
            True,
            (
                "Gate composer exists; PASS cannot be generated faithfully until "
                "all PASS-critical inputs are historically bound."
            ),
        ),
    )

    blockers = tuple(
        item.key
        for item in dependencies
        if item.pass_critical and item.blocker
    )
    ready = not blockers

    return {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "evaluation": "STATIC_HISTORICAL_COGNITIVE_GATE_READINESS_ONLY",
        "dependency_count": len(dependencies),
        "dependencies": [asdict(item) for item in dependencies],
        "blocking_dependency_count": len(blockers),
        "blocking_dependencies": blockers,
        "historical_cognitive_gate_replay_ready": ready,
        "constant_pass_to_strategy_used": False,
        "quote_fresh_invented": False,
        "regime_family_invented": False,
        "knowledge_known_forced": False,
        "hypothesis_stage_forced": False,
        "metacognition_forced": False,
        "strategy_economics_calculated": False,
        "outcomes_read": False,
        "fresh_holdout_opened": False,
        "runtime_policy_candidate": False,
        "candidate_count": 0,
        "trader_certified": False,
        "next_phase": (
            "COGNITIVE_GATE_HISTORICAL_REPLAY_READY"
            if ready
            else "COGNITIVE_GATE_HISTORICAL_REPLAY_BLOCKED_DO_NOT_FORCE_PASS"
        ),
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-cognitive-gate-historical-readiness-v47-p0.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    report = build_report()
    write_report(report, Path("audit-output"))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
