"""Causal M5 portfolio batch adapter for cTrader DEMO Phase20D shadow.

The adapter has no broker, sizing, Risk or execution authority.  It converts
the already-observed five-market M5 actor population into the canonical
Phase20 decision-epoch batch.  Missing actor terminals become deadline misses;
no sequential pseudo-competition is manufactured.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_phase20_epoch_aggregator import (
    Phase20DecisionEpochAggregator,
    Phase20DecisionEpochBatch,
    Phase20DecisionEpochSlot,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_epoch import (
    Phase20ForwardObservedOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardPopulationDisposition,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ctrader_demo_economic_observation,
    normalize_provider_economics,
)
from qore.infrastructure.ctrader_demo_compat import (
    CTraderDemoSymbolSpecification,
)
from qore.infrastructure.r34_xauusd_live import (
    R34LiveSignal,
    build_r34_opportunity,
)
from qore.infrastructure.r38_eurusd_live import (
    R38LiveSignal,
    build_r38_opportunity,
)
from qore.infrastructure.r38_gbpjpy_live import (
    R38GbpJpyLiveSignal,
    build_r38_gbpjpy_opportunity,
)
from qore.infrastructure.r42_audjpy_live import (
    R42AudJpyLiveSignal,
    build_r42_audjpy_opportunity,
)
from qore.infrastructure.r43_gbpusd_live import (
    R43LiveSignal,
    build_r43_opportunity,
)

_PROVIDER_KEY = "ctrader-demo"

_M5_SLOT_SPECS: tuple[tuple[str, str, TraderLineage], ...] = (
    ("R43_GBPUSD", "GBPUSD", TraderLineage.R43_GBPUSD),
    ("R34_XAUUSD", "XAUUSD", TraderLineage.R34_XAUUSD),
    ("R38_GBPJPY", "GBPJPY", TraderLineage.R38_GBPJPY),
    ("R38_EURUSD", "EURUSD", TraderLineage.R38_EURUSD),
    ("R42_AUDJPY", "AUDJPY", TraderLineage.R42_AUDJPY),
)
_M5_BY_IDENTITY = {
    identity: (symbol, trader)
    for identity, symbol, trader in _M5_SLOT_SPECS
}


@dataclass(frozen=True, slots=True)
class Phase20M5ShadowTerminal:
    identity: str
    symbol: str
    observed_at: datetime
    disposition: Phase20ForwardPopulationDisposition
    reason: str
    opportunity: Phase20ForwardObservedOpportunity | None = None

    def __post_init__(self) -> None:
        if self.identity not in _M5_BY_IDENTITY:
            raise CiboCapitalManagementError(
                "Phase20D M5 terminal identity is unsupported"
            )
        expected_symbol, expected_trader = _M5_BY_IDENTITY[self.identity]
        if self.symbol != expected_symbol:
            raise CiboCapitalManagementError(
                "Phase20D M5 terminal symbol/identity mismatch"
            )
        _aware(self.observed_at, name="terminal observed_at")
        if type(self.disposition) is not Phase20ForwardPopulationDisposition:
            raise CiboCapitalManagementError(
                "Phase20D M5 terminal disposition must be canonical"
            )
        if not self.reason:
            raise CiboCapitalManagementError(
                "Phase20D M5 terminal reason is required"
            )
        if self.disposition is Phase20ForwardPopulationDisposition.CANDIDATE:
            if not isinstance(
                self.opportunity,
                Phase20ForwardObservedOpportunity,
            ):
                raise CiboCapitalManagementError(
                    "Phase20D M5 candidate needs observed opportunity"
                )
            envelope = self.opportunity.opportunity
            if (
                envelope.qore_symbol != expected_symbol
                or envelope.trader_id is not expected_trader
            ):
                raise CiboCapitalManagementError(
                    "Phase20D M5 candidate opportunity identity mismatch"
                )
        elif self.opportunity is not None:
            raise CiboCapitalManagementError(
                "Phase20D M5 non-candidate cannot carry opportunity"
            )


def m5_phase20_expected_slots() -> tuple[Phase20DecisionEpochSlot, ...]:
    return tuple(
        Phase20DecisionEpochSlot(
            slot_id=f"{identity}|{symbol}",
            trader_id=trader,
            qore_symbol=symbol,
        )
        for identity, symbol, trader in _M5_SLOT_SPECS
    )


def build_ctrader_demo_m5_observed_opportunity(
    *,
    identity: str,
    signal: object,
    provider_spec: CTraderDemoSymbolSpecification,
    observed_at: datetime,
) -> Phase20ForwardObservedOpportunity:
    """Build one shadow opportunity from the Trader's actual causal signal."""

    if identity not in _M5_BY_IDENTITY:
        raise CiboCapitalManagementError(
            "Phase20D M5 opportunity identity is unsupported"
        )
    expected_symbol, expected_trader = _M5_BY_IDENTITY[identity]
    if not isinstance(provider_spec, CTraderDemoSymbolSpecification):
        raise CiboCapitalManagementError(
            "Phase20D M5 opportunity requires cTrader provider spec"
        )
    if provider_spec.observed_at > observed_at:
        raise CiboCapitalManagementError(
            "Phase20D M5 provider snapshot cannot postdate terminal"
        )

    builder: Callable[[object, CTraderDemoSymbolSpecification, datetime], TraderOpportunityEnvelope]
    builder = _opportunity_builder(identity)
    opportunity = builder(signal, provider_spec, observed_at)
    if (
        opportunity.qore_symbol != expected_symbol
        or opportunity.trader_id is not expected_trader
    ):
        raise CiboCapitalManagementError(
            "Phase20D M5 opportunity builder returned wrong identity"
        )

    provider = ctrader_demo_economic_observation(
        qore_symbol=expected_symbol,
        provider_key=_PROVIDER_KEY,
        spec=provider_spec,
    )
    normalized = normalize_provider_economics(
        opportunity=opportunity,
        observation=provider,
    )
    return Phase20ForwardObservedOpportunity(
        provider_evidence_id=_provider_evidence_id(
            opportunity=opportunity,
            spec=provider_spec,
        ),
        opportunity=opportunity,
        provider_observation=provider,
        concentration_group=f"SYMBOL:{expected_symbol}",
        concentration_risk_usd=normalized.minimum_stop_risk_usd,
    )


def build_ctrader_demo_m5_phase20_batch(
    *,
    epoch_scope: str,
    opened_at: datetime,
    deadline_at: datetime,
    terminals: tuple[Phase20M5ShadowTerminal, ...],
    decision_at: datetime | None = None,
) -> Phase20DecisionEpochBatch:
    """Seal one five-slot M5 shadow population without waiting on execution."""

    _aware(opened_at, name="opened_at")
    _aware(deadline_at, name="deadline_at")
    if deadline_at <= opened_at:
        raise CiboCapitalManagementError(
            "Phase20D M5 deadline must follow open"
        )
    if not epoch_scope:
        raise CiboCapitalManagementError(
            "Phase20D M5 epoch_scope is required"
        )

    aggregator = Phase20DecisionEpochAggregator(
        epoch_scope=epoch_scope,
        opened_at=opened_at,
        deadline_at=deadline_at,
        expected_slots=m5_phase20_expected_slots(),
    )
    seen: set[str] = set()
    last_terminal = opened_at
    for terminal in sorted(
        terminals,
        key=lambda item: (item.observed_at, item.identity),
    ):
        slot_id = f"{terminal.identity}|{terminal.symbol}"
        if slot_id in seen:
            raise CiboCapitalManagementError(
                "Phase20D M5 terminal slot duplicated"
            )
        seen.add(slot_id)
        if terminal.observed_at > deadline_at:
            # A late actor is intentionally left missing; canonical seal turns
            # it into DEADLINE_MISSED at the actual epoch deadline.
            continue
        last_terminal = max(last_terminal, terminal.observed_at)
        if terminal.disposition is Phase20ForwardPopulationDisposition.CANDIDATE:
            assert terminal.opportunity is not None
            aggregator.record_candidate(
                slot_id=slot_id,
                opportunity=terminal.opportunity,
                observed_at=terminal.observed_at,
                reason=terminal.reason,
            )
        else:
            aggregator.record_non_candidate(
                slot_id=slot_id,
                disposition=terminal.disposition,
                observed_at=terminal.observed_at,
                reason=terminal.reason,
            )

    inferred_decision_at = (
        last_terminal
        if len(seen) == len(_M5_SLOT_SPECS)
        and all(item.observed_at <= deadline_at for item in terminals)
        else deadline_at
    )
    seal_at = inferred_decision_at if decision_at is None else decision_at
    _aware(seal_at, name="decision_at")
    if seal_at < last_terminal:
        raise CiboCapitalManagementError(
            "Phase20D M5 decision cannot predate observed terminal population"
        )
    if seal_at > deadline_at:
        raise CiboCapitalManagementError(
            "Phase20D M5 decision cannot exceed epoch deadline"
        )
    try:
        return aggregator.seal(decision_at=seal_at)
    except CiboCapitalManagementError:
        if seal_at != deadline_at and decision_at is None:
            return aggregator.seal(decision_at=deadline_at)
        raise


def _opportunity_builder(
    identity: str,
) -> Callable[
    [object, CTraderDemoSymbolSpecification, datetime],
    TraderOpportunityEnvelope,
]:
    if identity == "R34_XAUUSD":
        def r34(
            signal: object,
            spec: CTraderDemoSymbolSpecification,
            observed_at: datetime,
        ) -> TraderOpportunityEnvelope:
            del observed_at
            if not isinstance(signal, R34LiveSignal):
                raise CiboCapitalManagementError(
                    "Phase20D R34 signal type mismatch"
                )
            return build_r34_opportunity(signal=signal, provider_spec=spec)

        return r34
    if identity == "R38_EURUSD":
        def r38(
            signal: object,
            spec: CTraderDemoSymbolSpecification,
            observed_at: datetime,
        ) -> TraderOpportunityEnvelope:
            del observed_at
            if not isinstance(signal, R38LiveSignal):
                raise CiboCapitalManagementError(
                    "Phase20D R38 EURUSD signal type mismatch"
                )
            return build_r38_opportunity(signal=signal, provider_spec=spec)

        return r38
    if identity == "R43_GBPUSD":
        def r43(
            signal: object,
            spec: CTraderDemoSymbolSpecification,
            observed_at: datetime,
        ) -> TraderOpportunityEnvelope:
            del observed_at
            if not isinstance(signal, R43LiveSignal):
                raise CiboCapitalManagementError(
                    "Phase20D R43 signal type mismatch"
                )
            return build_r43_opportunity(signal=signal, provider_spec=spec)

        return r43
    if identity == "R38_GBPJPY":
        def gbpjpy(
            signal: object,
            spec: CTraderDemoSymbolSpecification,
            observed_at: datetime,
        ) -> TraderOpportunityEnvelope:
            del observed_at
            if not isinstance(signal, R38GbpJpyLiveSignal):
                raise CiboCapitalManagementError(
                    "Phase20D R38 GBPJPY signal type mismatch"
                )
            return build_r38_gbpjpy_opportunity(
                signal=signal,
                provider_spec=spec,
            )

        return gbpjpy
    if identity == "R42_AUDJPY":
        def audjpy(
            signal: object,
            spec: CTraderDemoSymbolSpecification,
            observed_at: datetime,
        ) -> TraderOpportunityEnvelope:
            if not isinstance(signal, R42AudJpyLiveSignal):
                raise CiboCapitalManagementError(
                    "Phase20D R42 AUDJPY signal type mismatch"
                )
            return build_r42_audjpy_opportunity(
                signal=signal,
                provider_spec=spec,
                now=observed_at,
            )

        return audjpy
    raise CiboCapitalManagementError(
        "Phase20D M5 opportunity identity is unsupported"
    )


def _provider_evidence_id(
    *,
    opportunity: TraderOpportunityEnvelope,
    spec: CTraderDemoSymbolSpecification,
) -> str:
    payload: dict[str, Any] = {
        "provider_key": _PROVIDER_KEY,
        "signal_fingerprint": opportunity.signal_fingerprint,
        "qore_symbol": opportunity.qore_symbol,
        "provider_symbol": opportunity.provider_symbol,
        "bid": format(spec.bid, "f"),
        "ask": format(spec.ask, "f"),
        "contract_size": format(spec.contract_size, "f"),
        "tick_size": format(spec.tick_size, "f"),
        "tick_value": format(spec.tick_value, "f"),
        "minimum_volume": format(spec.minimum_volume, "f"),
        "maximum_volume": format(spec.maximum_volume, "f"),
        "volume_step": format(spec.volume_step, "f"),
        "margin_per_volume": format(spec.margin_per_volume, "f"),
        "commission_per_volume_usd": format(
            spec.open_commission_per_lot_usd,
            "f",
        ),
        "observed_at": spec.observed_at.isoformat(),
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"ctrader-demo-provider:{sha256(raw).hexdigest()}"


def _aware(value: datetime, *, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase20D M5 {name} must be timezone-aware"
        )
