"""Decision-time feature extraction for the QORE Capitalizer Behavior Lab.

The extractor consumes only already-built causal brain state. It does not inspect economic
outcomes, future bars, later destinations, or post-trade labels.
"""

from __future__ import annotations

from datetime import datetime

from qore.infrastructure.trader_lab.capitalizer_behavior_lab import (
    CapitalizerFeatureValue,
)
from qore.infrastructure.trader_lab.capitalizer_context_brains import (
    CapitalizerMarketBrainState,
    CapitalizerSessionBrainState,
)
from qore.infrastructure.trader_lab.capitalizer_situation_model import (
    CapitalizerSituationModel,
)


def _bool_token(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def extract_behavior_features(
    *,
    situation: CapitalizerSituationModel,
    market_brain: CapitalizerMarketBrainState,
    session_brain: CapitalizerSessionBrainState,
) -> tuple[CapitalizerFeatureValue, ...]:
    """Build canonical pre-entry features from one exact causal snapshot."""

    if market_brain.symbol != situation.symbol:
        raise ValueError("market brain symbol must match situation symbol")
    if market_brain.session is not situation.session:
        raise ValueError("market brain session must match situation session")
    if session_brain.session is not situation.session:
        raise ValueError("session brain must match situation session")
    if market_brain.microstructure.decision_at != situation.observed_at:
        raise ValueError("microstructure decision time must match situation observed_at")

    observed_at: datetime = situation.observed_at
    handoff = session_brain.prior_handoff
    experience = market_brain.experience
    micro_path = ">".join(item.value for item in market_brain.microstructure.path) or "EMPTY"

    raw: dict[str, str] = {
        "CORRELATED_EXPOSURE_BLOCKED": _bool_token(
            situation.correlated_exposure_blocked
        ),
        "DESTINATION_AVAILABLE": _bool_token(situation.destination_available),
        "DISPLACEMENT_CONFIRMED": _bool_token(situation.displacement_confirmed),
        "EVIDENCE_STRENGTH": situation.evidence_strength.value,
        "EXECUTION_QUALITY": situation.execution.quality.value,
        "EXPERIENCE_PRESENT": _bool_token(experience is not None),
        "HANDOFF_PRESENT": _bool_token(handoff is not None),
        "LATE_ENTRY": _bool_token(situation.late_entry),
        "MARKET_STATE": situation.market_state.value,
        "MICRO_PATH": micro_path,
        "SESSION_PHASE": session_brain.phase.value,
        "STATE_FAMILY_ID": market_brain.state_family_id,
        "STRATEGY_TRIGGER_READY": _bool_token(situation.strategy_trigger_ready),
    }
    if experience is not None:
        raw["EXPERIENCE_STRENGTH"] = experience.calibration.strength.value
        raw["EXPERIENCE_OBSERVATIONS"] = str(experience.calibration.observations)
    else:
        raw["EXPERIENCE_STRENGTH"] = "UNKNOWN"
        raw["EXPERIENCE_OBSERVATIONS"] = "0"

    if handoff is not None:
        raw["PRIOR_SESSION_EXECUTIONS"] = str(handoff.prior_executions)
        raw["PRIOR_FAILURE_STATE_COUNT"] = str(
            len(handoff.unresolved_failure_fingerprints)
        )
        raw["PRIOR_DOMINANT_FACTOR_COUNT"] = str(len(handoff.dominant_factors))
        raw["PRIOR_CONSUMED_DESTINATION_COUNT"] = str(
            len(handoff.consumed_destinations)
        )
    else:
        raw["PRIOR_SESSION_EXECUTIONS"] = "0"
        raw["PRIOR_FAILURE_STATE_COUNT"] = "0"
        raw["PRIOR_DOMINANT_FACTOR_COUNT"] = "0"
        raw["PRIOR_CONSUMED_DESTINATION_COUNT"] = "0"

    return tuple(
        CapitalizerFeatureValue(
            name=name,
            value=value,
            observed_at=observed_at,
        )
        for name, value in sorted(raw.items())
    )
