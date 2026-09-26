"""Causal chronological replay contracts for CIBO CMA / CE2I Phase 18.

Phase 18 must compare legacy Trader sizing with CIBO capital management while
holding the Trader opportunity constant.  This module therefore separates
pre-trade causal evidence from post-trade outcomes and fails closed when exact
provider economics are not available.

Nothing in this module mutates a broker or authorizes LIVE/DEMO execution.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.kernel.errors import InfrastructureError


class CiboChronologicalReplayError(InfrastructureError):
    """Replay evidence violates a causal or economic invariant."""

    __slots__ = ()


class ReplayEconomicsStatus(StrEnum):
    """Economic completeness of one historical replay opportunity."""

    R_DENOMINATED_ONLY = "R_DENOMINATED_ONLY"
    PROVIDER_ECONOMICS_COMPLETE = "PROVIDER_ECONOMICS_COMPLETE"


class ReplaySignalFingerprintOrigin(StrEnum):
    """Origin of the signal identity retained by the replay."""

    TRADER_NATIVE = "TRADER_NATIVE"
    PHASE18_RECONSTRUCTED = "PHASE18_RECONSTRUCTED"


_FORBIDDEN_PRE_TRADE_KEYS = frozenset(
    {
        "exit_at",
        "exit_price",
        "exit_reason",
        "future_price",
        "future_return",
        "mae",
        "mfe",
        "outcome",
        "outcome_r",
        "pnl",
        "realized_pnl",
        "target_hit",
        "win",
        "winner",
    }
)


def _finite(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboChronologicalReplayError(f"{name} must be finite Decimal")


def _positive(value: Decimal, name: str) -> None:
    _finite(value, name)
    if value <= 0:
        raise CiboChronologicalReplayError(f"{name} must be positive")


def _nonnegative(value: Decimal, name: str) -> None:
    _finite(value, name)
    if value < 0:
        raise CiboChronologicalReplayError(f"{name} must be non-negative")


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboChronologicalReplayError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ReplayProviderEconomics:
    """Exact provider economics known at replay decision time."""

    provider_symbol: str
    tick_size: Decimal
    tick_value: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal
    margin_per_volume: Decimal
    execution_cost_reserve_per_volume_usd: Decimal
    broker_risk_buffer: Decimal
    evidence_id: str

    def __post_init__(self) -> None:
        if not self.provider_symbol:
            raise CiboChronologicalReplayError("provider_symbol must be non-empty")
        if not self.evidence_id:
            raise CiboChronologicalReplayError("economic evidence_id must be non-empty")
        for name, value in (
            ("tick_size", self.tick_size),
            ("tick_value", self.tick_value),
            ("minimum_volume", self.minimum_volume),
            ("maximum_volume", self.maximum_volume),
            ("volume_step", self.volume_step),
            ("margin_per_volume", self.margin_per_volume),
            ("broker_risk_buffer", self.broker_risk_buffer),
        ):
            _positive(value, name)
        _nonnegative(
            self.execution_cost_reserve_per_volume_usd,
            "execution_cost_reserve_per_volume_usd",
        )
        if self.maximum_volume < self.minimum_volume:
            raise CiboChronologicalReplayError("provider volume range invalid")
        if self.minimum_volume < self.volume_step:
            raise CiboChronologicalReplayError(
                "provider minimum cannot be below volume step"
            )


@dataclass(frozen=True, slots=True)
class CiboReplayCausalTrade:
    """All evidence that may influence capital decisions for one replay trade."""

    trader_id: TraderLineage
    signal_fingerprint: str
    signal_fingerprint_origin: ReplaySignalFingerprintOrigin
    qore_symbol: str
    side: str
    signal_at: datetime
    entry_at: datetime
    entry_price: Decimal
    structural_stop: Decimal
    technical_target: Decimal
    legacy_risk_scale: Decimal
    minimum_execution_steps: int
    pre_trade_state: tuple[tuple[str, str], ...]
    source_evidence_ids: tuple[str, ...]
    economics_status: ReplayEconomicsStatus
    provider_economics: ReplayProviderEconomics | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.trader_id, TraderLineage):
            raise CiboChronologicalReplayError("trader_id must be TraderLineage")
        if not self.signal_fingerprint:
            raise CiboChronologicalReplayError("signal_fingerprint must be non-empty")
        if not self.qore_symbol:
            raise CiboChronologicalReplayError("qore_symbol must be non-empty")
        _aware(self.signal_at, "signal_at")
        _aware(self.entry_at, "entry_at")
        if self.entry_at < self.signal_at:
            raise CiboChronologicalReplayError("entry_at cannot precede signal_at")
        for name, value in (
            ("entry_price", self.entry_price),
            ("structural_stop", self.structural_stop),
            ("technical_target", self.technical_target),
            ("legacy_risk_scale", self.legacy_risk_scale),
        ):
            _positive(value, name)
        if self.minimum_execution_steps < 1:
            raise CiboChronologicalReplayError(
                "minimum_execution_steps must be at least one"
            )
        if self.side == "long":
            if not self.structural_stop < self.entry_price < self.technical_target:
                raise CiboChronologicalReplayError("invalid long technical geometry")
        elif self.side == "short":
            if not self.technical_target < self.entry_price < self.structural_stop:
                raise CiboChronologicalReplayError("invalid short technical geometry")
        else:
            raise CiboChronologicalReplayError("side must be long/short")

        keys: set[str] = set()
        for key, _value in self.pre_trade_state:
            normalized = key.strip().lower()
            if not normalized:
                raise CiboChronologicalReplayError(
                    "pre_trade_state keys must be non-empty"
                )
            if normalized in keys:
                raise CiboChronologicalReplayError(
                    f"duplicate pre_trade_state key: {normalized}"
                )
            if normalized in _FORBIDDEN_PRE_TRADE_KEYS:
                raise CiboChronologicalReplayError(
                    f"post-trade field forbidden in pre_trade_state: {normalized}"
                )
            keys.add(normalized)

        if not self.source_evidence_ids or any(
            not item for item in self.source_evidence_ids
        ):
            raise CiboChronologicalReplayError(
                "source_evidence_ids must contain non-empty identifiers"
            )
        if len(set(self.source_evidence_ids)) != len(self.source_evidence_ids):
            raise CiboChronologicalReplayError(
                "source_evidence_ids cannot contain duplicates"
            )

        if self.economics_status is ReplayEconomicsStatus.R_DENOMINATED_ONLY:
            if self.provider_economics is not None:
                raise CiboChronologicalReplayError(
                    "R-denominated replay cannot carry unclassified provider economics"
                )
        elif self.economics_status is ReplayEconomicsStatus.PROVIDER_ECONOMICS_COMPLETE:
            if self.provider_economics is None:
                raise CiboChronologicalReplayError(
                    "complete provider economics require an evidence envelope"
                )
        else:
            raise CiboChronologicalReplayError("unsupported economics_status")


@dataclass(frozen=True, slots=True)
class CiboReplayOutcome:
    """Post-trade evidence retained for scoring only, never for sizing."""

    exit_at: datetime
    raw_outcome_r: Decimal
    net_outcome_r: Decimal
    exit_reason: str

    def __post_init__(self) -> None:
        _aware(self.exit_at, "exit_at")
        _finite(self.raw_outcome_r, "raw_outcome_r")
        _finite(self.net_outcome_r, "net_outcome_r")
        if not self.exit_reason:
            raise CiboChronologicalReplayError("exit_reason must be non-empty")


@dataclass(frozen=True, slots=True)
class CiboChronologicalReplayTrade:
    """One causally partitioned Phase-18 historical trade."""

    causal: CiboReplayCausalTrade
    outcome: CiboReplayOutcome

    def __post_init__(self) -> None:
        if self.outcome.exit_at < self.causal.entry_at:
            raise CiboChronologicalReplayError("exit_at cannot precede entry_at")


def reconstructed_signal_fingerprint(
    *,
    trader_id: TraderLineage,
    qore_symbol: str,
    side: str,
    signal_at: datetime,
    entry_at: datetime,
    entry_price: Decimal,
    structural_stop: Decimal,
    technical_target: Decimal,
    source_evidence_ids: tuple[str, ...],
) -> str:
    """Create a replay-only signal identity without consuming future outcome."""

    _aware(signal_at, "signal_at")
    _aware(entry_at, "entry_at")
    if entry_at < signal_at:
        raise CiboChronologicalReplayError("entry_at cannot precede signal_at")
    if side not in {"long", "short"}:
        raise CiboChronologicalReplayError("side must be long/short")
    for name, value in (
        ("entry_price", entry_price),
        ("structural_stop", structural_stop),
        ("technical_target", technical_target),
    ):
        _positive(value, name)
    if not source_evidence_ids:
        raise CiboChronologicalReplayError("source evidence is required")

    payload = {
        "schema": "qore.cibo.phase18.reconstructed_signal_fingerprint.v1",
        "trader_id": trader_id.value,
        "qore_symbol": qore_symbol,
        "side": side,
        "signal_at": signal_at.astimezone(UTC).isoformat(),
        "entry_at": entry_at.astimezone(UTC).isoformat(),
        "entry_price": str(entry_price),
        "structural_stop": str(structural_stop),
        "technical_target": str(technical_target),
        "source_evidence_ids": list(source_evidence_ids),
    }
    material = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(material).hexdigest()


def build_replay_opportunity(
    causal: CiboReplayCausalTrade,
) -> TraderOpportunityEnvelope:
    """Build CIBO input from causal evidence only.

    Outcome is intentionally not accepted by this function.  Historical rows
    without exact provider economics remain useful for R-denominated strategy
    replay but cannot be promoted into a USD CIBO sizing comparison.
    """

    economics = causal.provider_economics
    if (
        causal.economics_status
        is not ReplayEconomicsStatus.PROVIDER_ECONOMICS_COMPLETE
        or economics is None
    ):
        raise CiboChronologicalReplayError(
            "provider economics calibration required before CIBO sizing replay"
        )

    ticks_to_stop = abs(causal.entry_price - causal.structural_stop) / economics.tick_size
    stop_loss_per_volume = (
        ticks_to_stop * economics.tick_value
        + economics.execution_cost_reserve_per_volume_usd
    ) * economics.broker_risk_buffer
    _positive(stop_loss_per_volume, "stop_loss_per_volume")

    return TraderOpportunityEnvelope(
        trader_id=causal.trader_id,
        signal_fingerprint=causal.signal_fingerprint,
        qore_symbol=causal.qore_symbol,
        provider_symbol=economics.provider_symbol,
        side=causal.side,
        entry_type="historical_replay",
        intended_entry=causal.entry_price,
        stop_loss=causal.structural_stop,
        take_profit=causal.technical_target,
        stop_loss_per_volume=stop_loss_per_volume,
        margin_per_volume=economics.margin_per_volume,
        volume_step=economics.volume_step,
        minimum_volume=economics.minimum_volume,
        maximum_volume=economics.maximum_volume,
        minimum_execution_steps=causal.minimum_execution_steps,
    )
