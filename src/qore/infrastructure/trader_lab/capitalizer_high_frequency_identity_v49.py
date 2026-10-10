"""QORE Capitalizer High-Frequency Scalper V49 identity.

Owner correction:
- the Scalper decision stack is H1 -> M15 -> M1 only;
- Daily and H4 are forbidden as decision/gating timeframes;
- V48's 159 opportunities/year is rejected as insufficient density;
- H1 is a persistent market state, not a one-shot ticket consumed by one trade;
- M15 may form multiple independent setups while the H1 state remains valid;
- M1 supplies execution triggers;
- MAX3 per session remains a ceiling, never a quota.

This is a pre-economic research identity. It grants no Fresh Holdout, certification,
deployment, sizing or capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
    allowed_markets,
)

IDENTITY = "QORE_CAPITALIZER_HIGH_FREQUENCY_SCALPER_V49"


class V49Timeframe(StrEnum):
    H1 = "H1"
    M15 = "M15"
    M1 = "M1"


class V49LayerRole(StrEnum):
    CONTEXT_STATE = "CONTEXT_STATE"
    SETUP_FORMATION = "SETUP_FORMATION"
    EXECUTION_TRIGGER = "EXECUTION_TRIGGER"


@dataclass(frozen=True, slots=True)
class V49Layer:
    timeframe: V49Timeframe
    role: V49LayerRole
    can_create_multiple_downstream_opportunities: bool


LAYERS: tuple[V49Layer, ...] = (
    V49Layer(
        V49Timeframe.H1,
        V49LayerRole.CONTEXT_STATE,
        True,
    ),
    V49Layer(
        V49Timeframe.M15,
        V49LayerRole.SETUP_FORMATION,
        True,
    ),
    V49Layer(
        V49Timeframe.M1,
        V49LayerRole.EXECUTION_TRIGGER,
        False,
    ),
)


@dataclass(frozen=True, slots=True)
class V49HighFrequencyScalperIdentity:
    identity: str = IDENTITY
    layers: tuple[V49Layer, ...] = LAYERS
    sessions: tuple[CapitalizerSession, ...] = (
        CapitalizerSession.ASIA,
        CapitalizerSession.LONDON,
        CapitalizerSession.NEW_YORK,
    )
    max_executions_per_session: int = MAX_EXECUTIONS_PER_SESSION
    daily_decision_layer_allowed: bool = False
    h4_decision_layer_allowed: bool = False
    h1_signal_consumed_after_one_trade: bool = False
    multiple_m15_setups_per_h1_state_allowed: bool = True
    multiple_m1_opportunities_per_h1_state_allowed: bool = True
    max3_is_quota: bool = False
    outcome_aware_candidate_selection_allowed: bool = False
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V49 high-frequency identity is frozen")
        if tuple(layer.timeframe for layer in self.layers) != (
            V49Timeframe.H1,
            V49Timeframe.M15,
            V49Timeframe.M1,
        ):
            raise ValueError("V49 Scalper stack must be exactly H1 -> M15 -> M1")
        if self.daily_decision_layer_allowed or self.h4_decision_layer_allowed:
            raise ValueError("Daily/H4 are forbidden in the V49 Scalper decision stack")
        if self.h1_signal_consumed_after_one_trade:
            raise ValueError("H1 is persistent context, not a one-shot trade ticket")
        if not self.multiple_m15_setups_per_h1_state_allowed:
            raise ValueError("high-frequency identity requires reusable H1 context")
        if not self.multiple_m1_opportunities_per_h1_state_allowed:
            raise ValueError("high-frequency identity requires multiple intrastate opportunities")
        if self.max3_is_quota:
            raise ValueError("MAX3/session remains a ceiling, never a quota")
        if self.max_executions_per_session != 3:
            raise ValueError("Capitalizer MAX3/session ceiling is frozen")
        if self.outcome_aware_candidate_selection_allowed:
            raise ValueError("candidate generation cannot use future outcomes")
        if (
            self.fresh_holdout_authorized
            or self.economics_authorized
            or self.live_authorized
            or self.real_capital_authorized
        ):
            raise ValueError("V49 identity is pre-economic and non-deployable")

        configured = {
            session: frozenset(allowed_markets(session))
            for session in self.sessions
        }
        if configured != {
            CapitalizerSession.ASIA: frozenset(
                {"USDJPY", "AUDJPY", "AUDUSD", "GBPJPY"}
            ),
            CapitalizerSession.LONDON: frozenset({"EURUSD", "GBPUSD"}),
            CapitalizerSession.NEW_YORK: frozenset(
                {"XAUUSD", "USDCAD", "NAS100"}
            ),
        }:
            raise ValueError("V49 must preserve the frozen nine-market session identity")


V49_HIGH_FREQUENCY_SCALPER_IDENTITY = V49HighFrequencyScalperIdentity()
