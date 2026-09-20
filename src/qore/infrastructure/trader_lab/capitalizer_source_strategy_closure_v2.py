"""Frozen Source Strategy Closure V2 for QORE Capitalizer.

This closes only the reviewed ICT/TTrades methodology grammar and provenance boundary.
It does not claim economic edge, replay completion, market-family closure, funded-account
survivability, certification, or deployment authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.trader_lab.capitalizer_cognitive_closure_manifest import (
    FROZEN_COGNITIVE_CLOSURE_MANIFEST,
)
from qore.infrastructure.trader_lab.capitalizer_source_faithful_trader_design_v2 import (
    FROZEN_SOURCE_FAITHFUL_TRADER_DESIGN,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerChainStatus,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_grammar_v2 import (
    SOURCE_STRATEGY_GRAMMAR_ID,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_provenance_v2 import (
    FROZEN_SOURCE_STRATEGY_PROVENANCE,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_review_v2 import (
    FROZEN_SOURCE_STRATEGY_REVIEW,
)

SOURCE_STRATEGY_CLOSURE_ID = "QORE_CAPITALIZER_SOURCE_STRATEGY_CLOSURE_V2"


@dataclass(frozen=True, slots=True)
class CapitalizerSourceStrategyClosure:
    closure_id: str = SOURCE_STRATEGY_CLOSURE_ID
    cognitive_dependency_status: CapitalizerChainStatus = CapitalizerChainStatus.FROZEN_APT
    source_inventory_status: CapitalizerChainStatus = CapitalizerChainStatus.FROZEN_APT
    deterministic_grammar_status: CapitalizerChainStatus = CapitalizerChainStatus.FROZEN_APT
    provenance_status: CapitalizerChainStatus = CapitalizerChainStatus.FROZEN_APT
    methodology_design_status: CapitalizerChainStatus = CapitalizerChainStatus.FROZEN_APT
    source_strategy_status: CapitalizerChainStatus = CapitalizerChainStatus.RESEARCH_OPEN
    source_faithful_methodology_design_closed: bool = True
    deterministic_source_observation_layer_closed: bool = False
    source_faithful_trader_engine_closed: bool = False
    full_source_faithful_trader_design_closed: bool = False
    source_trade_plan_closed: bool = True

    asian_session_requires_historical_open_reference: bool = True
    london_source_window_frozen: bool = True
    new_york_source_window_frozen: bool = True
    qore_surveillance_bucket_equated_to_source_killzone: bool = False

    ready_for_integrated_nine_market_replay: bool = False
    integrated_nine_market_replay_completed: bool = False
    final_nine_market_family_taxonomy_closed: bool = False
    stop_intelligence_closed: bool = False
    target_intelligence_closed: bool = False
    break_even_policy_closed: bool = False
    trailing_stop_policy_closed: bool = False
    trailing_target_policy_closed: bool = False
    zig_zig_policy_closed: bool = False
    daily_loss_funded_survivability_closed: bool = False
    economic_edge_claimed: bool = False
    trader_certified: bool = False
    demo_authorized: bool = False
    live_authorized: bool = False
    production_authorized: bool = False

    def __post_init__(self) -> None:
        if self.closure_id != SOURCE_STRATEGY_CLOSURE_ID:
            raise ValueError("Source Strategy Closure identity is frozen")
        if (
            FROZEN_COGNITIVE_CLOSURE_MANIFEST.cognitive_base_status
            is not CapitalizerChainStatus.FROZEN_APT
        ):
            raise ValueError("source strategy closure requires frozen cognitive base")
        if self.cognitive_dependency_status is not CapitalizerChainStatus.FROZEN_APT:
            raise ValueError("cognitive dependency must be FROZEN_APT")
        if (
            FROZEN_SOURCE_STRATEGY_REVIEW.inventory_status
            is not CapitalizerChainStatus.FROZEN_APT
        ):
            raise ValueError("reviewed source inventory must be FROZEN_APT")
        if (
            FROZEN_SOURCE_STRATEGY_REVIEW.deterministic_strategy_grammar_status
            is not CapitalizerChainStatus.FROZEN_APT
        ):
            raise ValueError("reviewed deterministic grammar must be FROZEN_APT")
        if self.source_inventory_status is not CapitalizerChainStatus.FROZEN_APT:
            raise ValueError("source inventory status must be FROZEN_APT")
        if self.deterministic_grammar_status is not CapitalizerChainStatus.FROZEN_APT:
            raise ValueError("deterministic grammar status must be FROZEN_APT")
        if self.provenance_status is not CapitalizerChainStatus.FROZEN_APT:
            raise ValueError("source provenance status must be FROZEN_APT")
        if self.methodology_design_status is not CapitalizerChainStatus.FROZEN_APT:
            raise ValueError("source methodology design must be FROZEN_APT")
        if self.source_strategy_status is not CapitalizerChainStatus.RESEARCH_OPEN:
            raise ValueError(
                "source trader remains RESEARCH_OPEN until observation/engine layers close"
            )
        if not self.source_faithful_methodology_design_closed:
            raise ValueError("source-faithful methodology design must be closed")
        if self.deterministic_source_observation_layer_closed:
            raise ValueError("deterministic source observation layer is not closed yet")
        if self.source_faithful_trader_engine_closed:
            raise ValueError("composed source-faithful trader engine is not closed yet")
        if self.full_source_faithful_trader_design_closed:
            raise ValueError(
                "full trader cannot close before observation and engine layers"
            )
        if not self.source_trade_plan_closed:
            raise ValueError("source-faithful trade plan boundary must be closed")
        if (
            FROZEN_SOURCE_FAITHFUL_TRADER_DESIGN.status
            is not CapitalizerChainStatus.FROZEN_APT
        ):
            raise ValueError("source-faithful methodology design dependency not frozen")
        if SOURCE_STRATEGY_GRAMMAR_ID != "QORE_CAPITALIZER_SOURCE_STRATEGY_GRAMMAR_V2":
            raise ValueError("unexpected source strategy grammar identity")
        if FROZEN_SOURCE_STRATEGY_PROVENANCE.outcome_derived_rule_allowed:
            raise ValueError("source strategy closure forbids outcome-derived rules")
        if not self.asian_session_requires_historical_open_reference:
            raise ValueError("Asia must remain source-relative to historical Asian Open")
        if not self.london_source_window_frozen or not self.new_york_source_window_frozen:
            raise ValueError("reviewed London/New York source windows must remain frozen")
        if self.qore_surveillance_bucket_equated_to_source_killzone:
            raise ValueError("QORE surveillance buckets cannot masquerade as source killzones")
        if self.ready_for_integrated_nine_market_replay:
            raise ValueError(
                "integrated replay remains blocked until source observation and engine close"
            )
        if self.integrated_nine_market_replay_completed:
            raise ValueError("integrated replay is the next chain, not part of source closure")
        if self.final_nine_market_family_taxonomy_closed:
            raise ValueError("market-family closure occurs after integrated replay")
        if (
            self.stop_intelligence_closed
            or self.target_intelligence_closed
            or self.break_even_policy_closed
            or self.trailing_stop_policy_closed
            or self.trailing_target_policy_closed
            or self.zig_zig_policy_closed
        ):
            raise ValueError("advanced position-management chains remain open")
        if (
            self.daily_loss_funded_survivability_closed
            or self.economic_edge_claimed
            or self.trader_certified
        ):
            raise ValueError("economic/certification chains remain open")
        if self.demo_authorized or self.live_authorized or self.production_authorized:
            raise ValueError("Source Strategy Closure grants no deployment authority")


FROZEN_SOURCE_STRATEGY_CLOSURE = CapitalizerSourceStrategyClosure()
