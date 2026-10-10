"""V48 adjudication of the historical Source Strategy Closure V2.

The V2 artifacts are preserved as historical evidence. V48 does not rewrite or delete
them. It records that their source-fidelity authority is superseded because newer source
review established session/route conflicts with the universal H1-M15-M1 composition.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_SOURCE_CLOSURE_ADJUDICATION"


class V48HistoricalClosureStatus(StrEnum):
    PRESERVED_HISTORICAL_EVIDENCE = "PRESERVED_HISTORICAL_EVIDENCE"
    SUPERSEDED_FOR_SOURCE_FIDELITY = "SUPERSEDED_FOR_SOURCE_FIDELITY"


@dataclass(frozen=True, slots=True)
class V48SourceClosureAdjudication:
    identity: str = IDENTITY
    historical_closure_id: str = "QORE_CAPITALIZER_SOURCE_STRATEGY_CLOSURE_V2"
    historical_status: V48HistoricalClosureStatus = (
        V48HistoricalClosureStatus.PRESERVED_HISTORICAL_EVIDENCE
    )
    current_source_fidelity_status: V48HistoricalClosureStatus = (
        V48HistoricalClosureStatus.SUPERSEDED_FOR_SOURCE_FIDELITY
    )
    reasons: tuple[str, ...] = (
        "SESSION_SPECIFIC_TIMEFRAME_GRAPH_CONFLICT",
        "ALTERNATIVE_EXECUTION_ROUTES_COLLAPSED_INTO_GLOBAL_SEQUENCE",
        "M1_EXECUTION_LAYER_OVERCOMPOSED_AS_FULL_INDEPENDENT_GATE",
        "DUAL_SOURCE_SUPERINTERSECTION_NOT_SOURCE_PROVEN",
    )
    historical_files_must_be_deleted: bool = False
    v47_results_invalidated_as_history: bool = False
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 source closure adjudication identity is frozen")
        if not self.reasons:
            raise ValueError("V48 closure adjudication requires explicit reasons")
        if self.historical_files_must_be_deleted or self.v47_results_invalidated_as_history:
            raise ValueError("V48 must preserve V45-V47 evidence and history")
        if self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("closure supersession does not authorize new economics")


V48_SOURCE_CLOSURE_ADJUDICATION = V48SourceClosureAdjudication()
