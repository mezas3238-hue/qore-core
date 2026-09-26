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
    legacy_net_outcome_r: Decimal | None = None

    def __post_init__(self) -> None:
        if self.outcome.exit_at < self.causal.entry_at:
            raise CiboChronologicalReplayError("exit_at cannot precede entry_at")
        if self.legacy_net_outcome_r is not None:
            _finite(self.legacy_net_outcome_r, "legacy_net_outcome_r")


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


@dataclass(frozen=True, slots=True)
class ReplayStrategyMetrics:
    """Chronological legacy-strategy economics on the frozen signal population."""

    trades: int
    gross_profit_r: Decimal
    gross_loss_r: Decimal
    total_r: Decimal
    profit_factor: Decimal | None
    max_drawdown_r: Decimal
    max_loss_streak: int
    stop_count: int
    first_entry_at: datetime
    last_exit_at: datetime


@dataclass(frozen=True, slots=True)
class CiboReplayCapitalSample:
    """One reconciled chronological CMA capital state for a replayed trade."""

    observed_at: datetime
    original_base_capital_at_risk_usd: Decimal
    margin_in_use_usd: Decimal
    hard_risk_headroom_usd: Decimal
    margin_headroom_usd: Decimal
    self_financing_capacity_usd: Decimal
    available_future_capacity_usd: Decimal
    cumulative_released_capacity_usd: Decimal
    evidence_id: str
    reconciled: bool = True

    def __post_init__(self) -> None:
        _aware(self.observed_at, "observed_at")
        for name in (
            "original_base_capital_at_risk_usd",
            "margin_in_use_usd",
            "hard_risk_headroom_usd",
            "margin_headroom_usd",
            "self_financing_capacity_usd",
            "available_future_capacity_usd",
            "cumulative_released_capacity_usd",
        ):
            _nonnegative(getattr(self, name), name)
        if not self.evidence_id:
            raise CiboChronologicalReplayError(
                "capital sample evidence_id must be non-empty"
            )
        if type(self.reconciled) is not bool:
            raise CiboChronologicalReplayError(
                "capital sample reconciled must be bool"
            )


@dataclass(frozen=True, slots=True)
class ReplayCapitalMetrics:
    """Capital-efficiency metrics produced from one complete CMA trade lifecycle."""

    samples: int
    peak_original_capital_at_risk_usd: Decimal
    peak_margin_in_use_usd: Decimal
    peak_self_financing_capacity_usd: Decimal
    ending_available_future_capacity_usd: Decimal
    cumulative_released_capacity_usd: Decimal
    peak_risk_utilization: Decimal
    peak_margin_utilization: Decimal
    base_recovery_seconds: Decimal | None
    base_recovered_before_exit: bool
    base_capital_block_seconds: Decimal
    false_recovery_incidents: int


def score_legacy_replay(
    trades: tuple[CiboChronologicalReplayTrade, ...],
) -> ReplayStrategyMetrics:
    """Score the frozen legacy capital baseline without changing signal identity."""

    if not trades:
        raise CiboChronologicalReplayError("legacy replay requires at least one trade")

    fingerprints: set[str] = set()
    prior_entry: datetime | None = None
    gross_profit = Decimal(0)
    gross_loss = Decimal(0)
    equity = Decimal(0)
    peak = Decimal(0)
    max_drawdown = Decimal(0)
    max_loss_streak = 0
    current_loss_streak = 0
    stop_count = 0

    for trade in trades:
        fingerprint = trade.causal.signal_fingerprint
        if fingerprint in fingerprints:
            raise CiboChronologicalReplayError(
                f"duplicate replay signal fingerprint: {fingerprint}"
            )
        fingerprints.add(fingerprint)

        if prior_entry is not None and trade.causal.entry_at < prior_entry:
            raise CiboChronologicalReplayError(
                "legacy replay trades must remain in chronological entry order"
            )
        prior_entry = trade.causal.entry_at

        weighted_r = (
            trade.legacy_net_outcome_r
            if trade.legacy_net_outcome_r is not None
            else trade.outcome.net_outcome_r * trade.causal.legacy_risk_scale
        )
        if weighted_r > 0:
            gross_profit += weighted_r
            current_loss_streak = 0
        elif weighted_r < 0:
            gross_loss += weighted_r
            current_loss_streak += 1
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        else:
            current_loss_streak = 0

        if trade.outcome.exit_reason.strip().upper().startswith("STOP"):
            stop_count += 1

        equity += weighted_r
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)

    profit_factor = (
        gross_profit / abs(gross_loss)
        if gross_loss < 0
        else None
    )
    return ReplayStrategyMetrics(
        trades=len(trades),
        gross_profit_r=gross_profit,
        gross_loss_r=gross_loss,
        total_r=equity,
        profit_factor=profit_factor,
        max_drawdown_r=max_drawdown,
        max_loss_streak=max_loss_streak,
        stop_count=stop_count,
        first_entry_at=trades[0].causal.entry_at,
        last_exit_at=max(trade.outcome.exit_at for trade in trades),
    )


def _utilization(used: Decimal, remaining: Decimal) -> Decimal:
    total = used + remaining
    if total == 0:
        return Decimal(0)
    return used / total


def score_cibo_capital_path(
    *,
    entry_at: datetime,
    exit_at: datetime,
    samples: tuple[CiboReplayCapitalSample, ...],
) -> ReplayCapitalMetrics:
    """Score a fully reconciled CMA lifecycle without interpolating missing edges."""

    _aware(entry_at, "entry_at")
    _aware(exit_at, "exit_at")
    if exit_at < entry_at:
        raise CiboChronologicalReplayError("exit_at cannot precede entry_at")
    if not samples:
        raise CiboChronologicalReplayError("capital path requires samples")
    if samples[0].observed_at != entry_at:
        raise CiboChronologicalReplayError(
            "capital path must start exactly at entry_at"
        )
    if samples[-1].observed_at != exit_at:
        raise CiboChronologicalReplayError(
            "capital path must end exactly at exit_at"
        )

    prior_at: datetime | None = None
    prior_release = Decimal(0)
    recovered = False
    positive_after_recovery = False
    false_recovery_incidents = 0
    recovery_at: datetime | None = None
    block_seconds = Decimal(0)

    peak_original = Decimal(0)
    peak_margin = Decimal(0)
    peak_self_financing = Decimal(0)
    peak_risk_utilization = Decimal(0)
    peak_margin_utilization = Decimal(0)

    for index, sample in enumerate(samples):
        if not sample.reconciled:
            raise CiboChronologicalReplayError(
                f"unreconciled capital sample: {sample.evidence_id}"
            )
        if prior_at is not None and sample.observed_at < prior_at:
            raise CiboChronologicalReplayError(
                "capital samples must remain chronological"
            )
        if sample.cumulative_released_capacity_usd < prior_release:
            raise CiboChronologicalReplayError(
                "cumulative released capacity cannot decrease"
            )

        if index > 0:
            previous = samples[index - 1]
            if previous.original_base_capital_at_risk_usd > 0:
                interval = sample.observed_at - previous.observed_at
                block_seconds += Decimal(str(interval.total_seconds()))

        base_risk = sample.original_base_capital_at_risk_usd
        if base_risk == 0 and not recovered:
            recovered = True
            recovery_at = sample.observed_at
        elif recovered and base_risk > 0 and not positive_after_recovery:
            false_recovery_incidents += 1
            positive_after_recovery = True
        elif recovered and base_risk == 0:
            positive_after_recovery = False

        peak_original = max(peak_original, base_risk)
        peak_margin = max(peak_margin, sample.margin_in_use_usd)
        peak_self_financing = max(
            peak_self_financing,
            sample.self_financing_capacity_usd,
        )
        peak_risk_utilization = max(
            peak_risk_utilization,
            _utilization(base_risk, sample.hard_risk_headroom_usd),
        )
        peak_margin_utilization = max(
            peak_margin_utilization,
            _utilization(
                sample.margin_in_use_usd,
                sample.margin_headroom_usd,
            ),
        )
        prior_at = sample.observed_at
        prior_release = sample.cumulative_released_capacity_usd

    recovery_seconds = None
    if recovery_at is not None:
        recovery_seconds = Decimal(
            str((recovery_at - entry_at).total_seconds())
        )

    return ReplayCapitalMetrics(
        samples=len(samples),
        peak_original_capital_at_risk_usd=peak_original,
        peak_margin_in_use_usd=peak_margin,
        peak_self_financing_capacity_usd=peak_self_financing,
        ending_available_future_capacity_usd=(
            samples[-1].available_future_capacity_usd
        ),
        cumulative_released_capacity_usd=(
            samples[-1].cumulative_released_capacity_usd
        ),
        peak_risk_utilization=peak_risk_utilization,
        peak_margin_utilization=peak_margin_utilization,
        base_recovery_seconds=recovery_seconds,
        base_recovered_before_exit=(
            recovery_at is not None and recovery_at < exit_at
        ),
        base_capital_block_seconds=block_seconds,
        false_recovery_incidents=false_recovery_incidents,
    )
