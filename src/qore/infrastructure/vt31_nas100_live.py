"""Common live infrastructure for VT31 NAS100 on the resident MT5 runtime.

This module contains only execution/runtime mechanics that do not select or
retune the VT31 economic identity:

- one-time historical M1 preload + incremental recent cache;
- exact newly-closed M1 + exact newly-opened M1 boundary validation;
- broker tick freshness <= 2.0 seconds;
- T-10s pre-arm and 75ms critical-boundary retry;
- M1 2.0s decision deadline guard, including post-risk/pre-send checks;
- virtual OCO trigger selection without multiple broker pending orders;
- certified R-unit -> broker volume translation, always rounded DOWN;
- Account-Wide Risk request under the VT31_NAS100 lineage.

The target/lifecycle policy is bound separately to the final frozen candidate.
"""
# ruff: noqa: I001, N818
from __future__ import annotations

import hashlib
import json
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.infrastructure.account_wide_risk import CiboRiskRequest, TraderLineage
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.fundednext_mt5_clock import (
    NEW_YORK_TZ,
    normalise_fundednext_server_epoch,
)
from qore.infrastructure.fundednext_stellar_instant import resolve_pilot_symbol
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.trader_execution_profile import M1_PROFILE
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)

IDENTITY = "VT31_NAS100"
SYMBOL = "NAS100"
PROVIDER_SYMBOL = resolve_pilot_symbol(SYMBOL)
STRATEGY_IDENTITY = "VT31_NAS100_STRUCTURAL_TARGET_V1"
CERTIFIED_STRATEGY_FINGERPRINT = (
    "089c41f98a72295278063cfc29caf8419538f68315d9f5e57be144fbdae15e08"
)
CERTIFICATION_RUN_ID = 35519882906
CERTIFICATION_ARTIFACT_ID = 10607439608
CERTIFICATION_ARTIFACT_DIGEST = (
    "sha256:a08eb5ab18833e8112002a2ab908460c152b7b39b3314c879df6b2c499858568"
)
CERTIFICATION_REPORT_SHA256 = (
    "0d3aaa077cf8e7de27a08fcd84a7b83f62ee45561bd4deba3a19ebe6e13e9018"
)
EXECUTION_BINDING_ID = "VT31_NAS100_STRUCTURAL_TARGET_EXECUTION_BINDING_V4"
EXECUTION_BINDING_FINGERPRINT = (
    "e85ecc5d82f6c59061afd68863b0f641a3512b1cf132f3b8fb01be324ce7e842"
)
EXECUTION_BINDING_RUN_ID = 35530365775
EXECUTION_BINDING_ARTIFACT_ID = 10611515228
EXECUTION_BINDING_ARTIFACT_DIGEST = (
    "sha256:57fb0028840abe45ae692f76167322ce62521b93d9725b8cc425958b63b9e13d"
)
EXECUTION_BINDING_FREEZE_RUN_ID = 35530015392
EXECUTION_BINDING_FREEZE_ARTIFACT_ID = 10610782898
EXECUTION_BINDING_FREEZE_ARTIFACT_DIGEST = (
    "sha256:94d79e14dd0772e1ba494b0202c4a55e0c60edc2a458af1941a5a5a9a639aa2a"
)
EXECUTION_BINDING_5Y_RUN_ID = 35530059080
EXECUTION_BINDING_5Y_ARTIFACT_ID = 10610673464
EXECUTION_BINDING_5Y_ARTIFACT_DIGEST = (
    "sha256:f811bf67db29a9fc0305d4b14e55dd5b33671df6b9ba3ae1c7173f3dd3d14f4d"
)
TARGET_ARCHITECTURE_ID = "EQ50_COMPRESSED_ACCEPT_RUN25_PHYSICAL_V4"
STRATEGY_MEMORY_FINGERPRINT = (
    "26d7288e6ac293fdbf3fdad23969c7b815b26592209d7cb19975a6712aab8929"
)
CIBO_MEMORY_FINGERPRINT = (
    "0d3531d9f87e3b6e3fad64d583bf237e44ac70d32eb111e747fdfbfdfba07621"
)
TRADER_EXPERIENCE_FINGERPRINT = (
    "e21de399386c4f1fcee45f13c3e39c87828d492eb4cd32621ec2a40cbac5544b"
)
COGNITIVE_MEMORY_FINGERPRINT = (
    "d160185f5717c9dd6a79b8048543938b199f101d3fc7d45de33f994f1e95dba1"
)
SILVER_BULLET_SOURCE_FINGERPRINT = (
    "86f9602a5bc550c6c1f038f28779228484ac5c0a3b5f91e64460a5b7d139b9da"
)
SERVICE_24_7 = True
MARKET_READING = "CONTINUOUS"

DECISION_DEADLINE_SECONDS = M1_PROFILE.decision_deadline_seconds
DECISION_DEADLINE = M1_PROFILE.decision_deadline
MAX_BROKER_TICK_AGE = M1_PROFILE.tick_max_age
FUTURE_TICK_TOLERANCE = timedelta(seconds=0.5)
BOUNDARY_ARM_LEAD_SECONDS = M1_PROFILE.boundary_arm_lead_seconds
BOUNDARY_ARM_LEAD = timedelta(seconds=float(BOUNDARY_ARM_LEAD_SECONDS))
NORMAL_FEED_REFRESH_SECONDS = float(M1_PROFILE.normal_feed_refresh_seconds)
BOUNDARY_RETRY_MS = M1_PROFILE.boundary_retry_ms
BOUNDARY_RETRY_SECONDS = BOUNDARY_RETRY_MS / 1000
DOL1_RETRACE_WATCH_MS = 75
DOL1_RETRACE_WATCH_SECONDS = DOL1_RETRACE_WATCH_MS / 1000
HISTORY_M1_BARS = 30_000
MIN_PRELOAD_M1_BARS = 10_000
RECENT_M1_BARS = 32
BOUNDARY_RECENT_M1_BARS = 8
FINALIZATION_LAG = DECISION_DEADLINE
LATE_TICK_RECONCILIATION_WINDOW = timedelta(seconds=30)
RECONCILIATION_RECEIPT_LIMIT = 512

# QORE runtime normalization used by every currently integrated specialist:
# 1.00 strategy-R maps to 0.20% account equity before the trader's frozen
# causal risk multipliers. This is portfolio/runtime normalization, not VT31
# strategy calibration.
QORE_ONE_R_ACCOUNT_FRACTION = Decimal("0.002")
BROKER_RISK_BUFFER = Decimal("1.02")

_INSTRUMENT = Instrument(SYMBOL)
_TIMEFRAME_M1 = Timeframe(60)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("9b310000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("9b310000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.vt31-nas100-live"),
)


class Vt31Nas100LiveError(RuntimeError):
    """VT31 NAS100 runtime invariant failed closed."""

    def __init__(
        self,
        message: str,
        *,
        receipt: Vt31M1BarReconciliationReceipt | None = None,
    ) -> None:
        super().__init__(message)
        self.receipt = receipt


class Vt31Nas100SlaExpired(Vt31Nas100LiveError):
    """M1 execution decision deadline expired."""


@dataclass(frozen=True, slots=True)
class Vt31M1BarReconciliationReceipt:
    """Complete, serializable evidence for one M1 reconciliation decision."""

    result: str
    provider_symbol: str
    qore_symbol: str
    bar_open_time: datetime
    bar_close_time: datetime
    broker_timestamp: int
    broker_wall_time: datetime
    utc_time: datetime
    new_york_time: datetime
    first_seen_at: datetime
    sealed_at: datetime | None
    sealed_now: bool
    observed_at: datetime
    source: str
    previous_source: str | None
    history_source: str | None
    incremental_source: str | None
    sequence: int
    bar_state: str
    ohlc: tuple[str, str, str, str]
    previous_ohlc: tuple[str, str, str, str] | None
    tick_volume: int | None
    previous_tick_volume: int | None
    real_volume: int | None
    previous_real_volume: int | None
    spread: int | None
    previous_spread: int | None
    fingerprint: str
    previous_fingerprint: str | None
    revision_count: int
    cache_version: int
    cache_state: str
    history_state: str
    incremental_state: str
    decision_state: str
    changed_fields: tuple[str, ...]
    differences: tuple[tuple[str, str, str, str], ...]

    def as_payload(self) -> dict[str, object]:
        previous_ohlc = None
        if self.previous_ohlc is not None:
            previous_ohlc = _ohlc_payload(self.previous_ohlc)
        return {
            "event": "VT31_M1_BAR_RECONCILIATION",
            "result": self.result,
            "provider_symbol": self.provider_symbol,
            "qore_symbol": self.qore_symbol,
            "bar_open_time": self.bar_open_time.isoformat(),
            "bar_close_time": self.bar_close_time.isoformat(),
            "broker_timestamp": self.broker_timestamp,
            "broker_wall_time": self.broker_wall_time.isoformat(),
            "utc_time": self.utc_time.isoformat(),
            "new_york_time": self.new_york_time.isoformat(),
            "first_seen_at": self.first_seen_at.isoformat(),
            "sealed_at": self.sealed_at.isoformat() if self.sealed_at else None,
            "sealed_now": self.sealed_now,
            "observed_at": self.observed_at.isoformat(),
            "source": self.source,
            "previous_source": self.previous_source,
            "history_source": self.history_source,
            "incremental_source": self.incremental_source,
            "sequence": self.sequence,
            "bar_state": self.bar_state,
            "ohlc": _ohlc_payload(self.ohlc),
            "previous_ohlc": previous_ohlc,
            "tick_volume": self.tick_volume,
            "previous_tick_volume": self.previous_tick_volume,
            "real_volume": self.real_volume,
            "previous_real_volume": self.previous_real_volume,
            "spread": self.spread,
            "previous_spread": self.previous_spread,
            "fingerprint": self.fingerprint,
            "previous_fingerprint": self.previous_fingerprint,
            "revision_count": self.revision_count,
            "cache_version": self.cache_version,
            "cache_state": self.cache_state,
            "history_state": self.history_state,
            "incremental_state": self.incremental_state,
            "decision_state": self.decision_state,
            "changed_fields": list(self.changed_fields),
            "differences": [
                {
                    "field": field,
                    "previous": previous,
                    "current": current,
                    "difference": difference,
                }
                for field, previous, current, difference in self.differences
            ],
        }


@dataclass(frozen=True, slots=True)
class _Vt31M1Observation:
    snapshot: OhlcSnapshot
    broker_timestamp: int
    broker_wall_time: datetime
    raw_ohlc: tuple[str, str, str, str]
    canonical_ohlc: tuple[str, str, str, str]
    tick_volume: int | None
    real_volume: int | None
    spread: int | None
    source: str
    sequence: int
    fingerprint: str


@dataclass(frozen=True, slots=True)
class Vt31Nas100BoundarySnapshot:
    anchor: datetime
    closed_m1: tuple[OhlcSnapshot, ...]
    current_open: Decimal
    broker_bid: Decimal
    broker_ask: Decimal
    broker_tick_at: datetime
    observed_at: datetime
    evidence_fingerprint: str


@dataclass(frozen=True, slots=True)
class Vt31VirtualCandidate:
    candidate_id: str
    signal_fingerprint: str
    side: str
    family: str
    formed_at: datetime
    decision_at: datetime
    expires_at: datetime
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal

    def __post_init__(self) -> None:
        if self.side not in {"long", "short"}:
            raise ValueError("VT31 virtual candidate side must be long or short")
        if not self.candidate_id or not self.signal_fingerprint:
            raise ValueError("VT31 virtual candidate identity missing")
        for value in (self.formed_at, self.decision_at, self.expires_at):
            _aware(value, "virtual candidate timestamp")
        if self.expires_at <= self.decision_at:
            raise ValueError("VT31 virtual candidate expiry must follow decision")
        if self.side == "long":
            valid = self.stop_loss < self.entry_price < self.take_profit
        else:
            valid = self.take_profit < self.entry_price < self.stop_loss
        if not valid:
            raise ValueError("VT31 virtual candidate geometry invalid")


@dataclass(frozen=True, slots=True)
class Vt31RiskContext:
    tier: str
    entry_family: str
    side: str
    nominal_risk_r: Decimal
    h1_state: str
    premarket_state: str
    cash_open_state: str
    confirmation_latency_minutes: int | None
    risk_ref: Decimal | None
    current_path_vs_previous: Decimal | None

    def __post_init__(self) -> None:
        if self.tier not in {"CORE", "SECONDARY", "SCOUT", "REARM"}:
            raise ValueError("VT31 risk tier invalid")
        if self.entry_family not in {"breaker", "fair-value-gap", "order-block"}:
            raise ValueError("VT31 risk entry family invalid")
        if self.side not in {"long", "short"}:
            raise ValueError("VT31 risk side invalid")
        if self.nominal_risk_r <= 0:
            raise ValueError("VT31 nominal risk must be positive")
        if (
            self.confirmation_latency_minutes is not None
            and self.confirmation_latency_minutes < 0
        ):
            raise ValueError("VT31 confirmation latency invalid")


@dataclass(frozen=True, slots=True)
class Vt31RiskResolution:
    nominal_risk_r: Decimal
    allocation_multiplier: Decimal
    global_scalar: Decimal
    state_shield_multiplier: Decimal
    loss_cluster_multiplier: Decimal
    breaker_regime_multiplier: Decimal
    final_risk_r: Decimal
    reasons: tuple[str, ...]


class Vt31Nas100M1Cache:
    """One preload, then deterministic incremental M1 reconciliation."""

    def __init__(
        self,
        *,
        max_bars: int = HISTORY_M1_BARS,
        price_digits: int = 1,
    ) -> None:
        if max_bars < MIN_PRELOAD_M1_BARS:
            raise ValueError("VT31 M1 cache max_bars below minimum")
        if isinstance(price_digits, bool) or not 0 <= price_digits <= 10:
            raise ValueError("VT31 price digits invalid")
        self._max_bars = max_bars
        self._price_digits = price_digits
        self._price_quantum = Decimal(1).scaleb(-price_digits)
        self._bars: dict[datetime, OhlcSnapshot] = {}
        self._observations: dict[datetime, _Vt31M1Observation] = {}
        self._finalized_bars: set[datetime] = set()
        self._first_seen_at: dict[datetime, datetime] = {}
        self._sealed_at: dict[datetime, datetime] = {}
        self._revision_counts: dict[datetime, int] = {}
        self._receipts: deque[Vt31M1BarReconciliationReceipt] = deque(
            maxlen=RECONCILIATION_RECEIPT_LIMIT
        )
        self._sequence = 0
        self._cache_version = 0
        self._preloaded = False
        self._preload_calls = 0
        self._incremental_calls = 0
        self._last_refresh_at: datetime | None = None

    @property
    def preloaded(self) -> bool:
        return self._preloaded

    @property
    def preload_calls(self) -> int:
        return self._preload_calls

    @property
    def incremental_calls(self) -> int:
        return self._incremental_calls

    @property
    def last_refresh_at(self) -> datetime | None:
        return self._last_refresh_at

    @property
    def cache_version(self) -> int:
        return self._cache_version

    def drain_reconciliation_receipts(
        self,
    ) -> tuple[Vt31M1BarReconciliationReceipt, ...]:
        receipts = tuple(self._receipts)
        self._receipts.clear()
        return receipts

    def closed_m1(self, *, through: datetime) -> tuple[OhlcSnapshot, ...]:
        """Return only immutable bars closed no later than the cutoff."""
        cutoff = _utc(through, "through")
        return tuple(
            self._bars[key]
            for key in sorted(self._bars)
            if self._bars[key].closed_at <= cutoff
        )

    def _ingest(
        self,
        rows: Any,
        *,
        observed_at: datetime,
        source: str = "incremental",
        emit_receipts: bool = True,
    ) -> None:
        observed = _utc(observed_at, "observed_at")
        for row in rows:
            self._sequence += 1
            current = self._observation_from_row(
                row,
                source=source,
                sequence=self._sequence,
            )
            snapshot = current.snapshot
            opened = snapshot.opened_at
            prior = self._bars.get(opened)
            prior_observation = self._observations.get(opened)
            first_seen = self._first_seen_at.setdefault(opened, observed)
            result: str | None = None

            if prior is None or prior_observation is None:
                self._accept_observation(current)
                result = "LEGITIMATE_UPDATE"
            elif (
                prior_observation.fingerprint == current.fingerprint
                and prior_observation.raw_ohlc == current.raw_ohlc
            ):
                result = None
            elif _only_precision_difference(prior_observation, current):
                self._accept_observation(current, revision=True)
                result = "PRECISION_NORMALIZED"
            elif opened not in self._finalized_bars:
                self._accept_observation(current, revision=True)
                result = "LEGITIMATE_UPDATE"
            elif self._is_admissible_late_tick(
                prior_observation,
                current,
                observed_at=observed,
            ):
                self._accept_observation(current, revision=True)
                result = "LATE_TICK_RECONCILED"
            else:
                receipt = self._receipt(
                    result="TRUE_CONTRADICTION",
                    current=current,
                    previous=prior_observation,
                    observed_at=observed,
                    first_seen_at=first_seen,
                    decision_state="FAIL_CLOSED",
                    sealed_now=False,
                )
                self._receipts.append(receipt)
                payload = receipt.as_payload()
                raise Vt31Nas100LiveError(
                    "VT31 contradictory completed M1 bar "
                    + json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    receipt=receipt,
                )

            newly_sealed = False
            if (
                opened not in self._finalized_bars
                and snapshot.closed_at + FINALIZATION_LAG <= observed
            ):
                self._finalized_bars.add(opened)
                self._sealed_at[opened] = observed
                self._cache_version += 1
                newly_sealed = True

            if emit_receipts and (result is not None or newly_sealed):
                accepted = self._observations[opened]
                self._receipts.append(
                    self._receipt(
                        result=result or "IDENTICAL",
                        current=accepted,
                        previous=prior_observation,
                        observed_at=observed,
                        first_seen_at=first_seen,
                        decision_state=(
                            "READY" if opened in self._finalized_bars else "WAIT"
                        ),
                        sealed_now=newly_sealed,
                    )
                )

        if len(self._bars) > self._max_bars:
            keys = sorted(self._bars)
            for key in keys[: len(keys) - self._max_bars]:
                del self._bars[key]
                self._observations.pop(key, None)
                self._finalized_bars.discard(key)
                self._first_seen_at.pop(key, None)
                self._sealed_at.pop(key, None)
                self._revision_counts.pop(key, None)

    def _observation_from_row(
        self,
        row: Any,
        *,
        source: str,
        sequence: int,
    ) -> _Vt31M1Observation:
        broker_timestamp = int(row["time"])
        opened = normalise_fundednext_server_epoch(broker_timestamp)
        raw_ohlc = (
            str(_row_value(row, "open")),
            str(_row_value(row, "high")),
            str(_row_value(row, "low")),
            str(_row_value(row, "close")),
        )
        canonical_ohlc = (
            _canonical_price(raw_ohlc[0], self._price_quantum),
            _canonical_price(raw_ohlc[1], self._price_quantum),
            _canonical_price(raw_ohlc[2], self._price_quantum),
            _canonical_price(raw_ohlc[3], self._price_quantum),
        )
        snapshot = OhlcSnapshot(
            snapshot_id=MarketDataSnapshotId(
                uuid5(
                    NAMESPACE_URL,
                    f"qore:vt31:nas100:m1:{opened.isoformat()}",
                )
            ),
            instrument=_INSTRUMENT,
            source=_SOURCE,
            timeframe=_TIMEFRAME_M1,
            opened_at=opened,
            closed_at=opened + timedelta(minutes=1),
            open=float(canonical_ohlc[0]),
            high=float(canonical_ohlc[1]),
            low=float(canonical_ohlc[2]),
            close=float(canonical_ohlc[3]),
        )
        tick_volume = _optional_int(row, "tick_volume")
        real_volume = _optional_int(row, "real_volume")
        spread = _optional_int(row, "spread")
        material = {
            "bar_open_time": opened.isoformat(),
            "ohlc": canonical_ohlc,
            "tick_volume": tick_volume,
            "real_volume": real_volume,
            "spread": spread,
        }
        fingerprint = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        broker_wall_time = datetime.fromtimestamp(broker_timestamp, tz=UTC)
        return _Vt31M1Observation(
            snapshot=snapshot,
            broker_timestamp=broker_timestamp,
            broker_wall_time=broker_wall_time,
            raw_ohlc=raw_ohlc,
            canonical_ohlc=canonical_ohlc,
            tick_volume=tick_volume,
            real_volume=real_volume,
            spread=spread,
            source=source,
            sequence=sequence,
            fingerprint=fingerprint,
        )

    def _accept_observation(
        self,
        observation: _Vt31M1Observation,
        *,
        revision: bool = False,
    ) -> None:
        opened = observation.snapshot.opened_at
        self._bars[opened] = observation.snapshot
        self._observations[opened] = observation
        if revision:
            self._revision_counts[opened] = self._revision_counts.get(opened, 0) + 1
        else:
            self._revision_counts.setdefault(opened, 0)
        self._cache_version += 1

    def _is_admissible_late_tick(
        self,
        previous: _Vt31M1Observation,
        current: _Vt31M1Observation,
        *,
        observed_at: datetime,
    ) -> bool:
        if (
            observed_at
            > current.snapshot.closed_at + LATE_TICK_RECONCILIATION_WINDOW
        ):
            return False
        if previous.tick_volume is None or current.tick_volume is None:
            return False
        previous_prices = tuple(Decimal(value) for value in previous.canonical_ohlc)
        current_prices = tuple(Decimal(value) for value in current.canonical_ohlc)
        previous_open, previous_high, previous_low, _ = previous_prices
        current_open, current_high, current_low, current_close = current_prices
        return (
            current_open == previous_open
            and current_high >= previous_high
            and current_low <= previous_low
            and current_low <= current_close <= current_high
            and current.tick_volume >= previous.tick_volume
            and (
                previous.real_volume is None
                or current.real_volume is None
                or current.real_volume >= previous.real_volume
            )
        )

    def _receipt(
        self,
        *,
        result: str,
        current: _Vt31M1Observation,
        previous: _Vt31M1Observation | None,
        observed_at: datetime,
        first_seen_at: datetime,
        decision_state: str,
        sealed_now: bool,
    ) -> Vt31M1BarReconciliationReceipt:
        opened = current.snapshot.opened_at
        previous_ohlc = previous.canonical_ohlc if previous else None
        changed_fields = _changed_bar_fields(previous, current)
        differences = _bar_differences(previous, current)
        previous_source = previous.source if previous else None
        return Vt31M1BarReconciliationReceipt(
            result=result,
            provider_symbol=PROVIDER_SYMBOL,
            qore_symbol=SYMBOL,
            bar_open_time=opened,
            bar_close_time=current.snapshot.closed_at,
            broker_timestamp=current.broker_timestamp,
            broker_wall_time=current.broker_wall_time,
            utc_time=opened,
            new_york_time=opened.astimezone(NEW_YORK_TZ),
            first_seen_at=first_seen_at,
            sealed_at=self._sealed_at.get(opened),
            sealed_now=sealed_now,
            observed_at=observed_at,
            source=current.source,
            previous_source=previous_source,
            history_source=(
                previous_source if previous_source == "history_preload" else None
            ),
            incremental_source=(
                current.source if current.source == "incremental" else None
            ),
            sequence=current.sequence,
            bar_state=("CLOSED" if current.snapshot.closed_at <= observed_at else "OPEN"),
            ohlc=current.canonical_ohlc,
            previous_ohlc=previous_ohlc,
            tick_volume=current.tick_volume,
            previous_tick_volume=previous.tick_volume if previous else None,
            real_volume=current.real_volume,
            previous_real_volume=previous.real_volume if previous else None,
            spread=current.spread,
            previous_spread=previous.spread if previous else None,
            fingerprint=current.fingerprint,
            previous_fingerprint=previous.fingerprint if previous else None,
            revision_count=self._revision_counts.get(opened, 0),
            cache_version=self._cache_version,
            cache_state="DETERMINISTIC",
            history_state="PRELOADED" if self._preloaded else "PRELOADING",
            incremental_state=("ACTIVE" if self._incremental_calls else "STARTING"),
            decision_state=decision_state,
            changed_fields=changed_fields,
            differences=differences,
        )

    def preload(self, api: Any, *, now: datetime) -> None:
        if self._preloaded:
            raise Vt31Nas100LiveError(
                "VT31 historical M1 preload may run only once"
            )
        self._sync_provider_precision(api)
        rows = api.copy_rates_from_pos(
            PROVIDER_SYMBOL,
            api.TIMEFRAME_M1,
            0,
            HISTORY_M1_BARS,
        )
        if rows is None or len(rows) < MIN_PRELOAD_M1_BARS:
            raise Vt31Nas100LiveError("VT31 historical M1 preload unavailable")
        self._ingest(
            rows,
            observed_at=now,
            source="history_preload",
            emit_receipts=False,
        )
        self._preloaded = True
        self._preload_calls += 1
        self._last_refresh_at = now.astimezone(UTC)

    def refresh_incremental(
        self,
        api: Any,
        *,
        now: datetime,
        count: int = RECENT_M1_BARS,
    ) -> None:
        if not self._preloaded:
            raise Vt31Nas100LiveError("VT31 M1 cache not preloaded")
        if count <= 0 or count > 64:
            raise ValueError("VT31 incremental M1 count invalid")
        self._sync_provider_precision(api)
        rows = api.copy_rates_from_pos(
            PROVIDER_SYMBOL,
            api.TIMEFRAME_M1,
            0,
            count,
        )
        if rows is None or len(rows) < 2:
            raise Vt31Nas100LiveError("VT31 incremental M1 refresh unavailable")
        self._ingest(rows, observed_at=now, source="incremental")
        self._incremental_calls += 1
        self._last_refresh_at = now.astimezone(UTC)

    def _sync_provider_precision(self, api: Any) -> None:
        symbol_info = getattr(api, "symbol_info", None)
        if not callable(symbol_info):
            return
        info = symbol_info(PROVIDER_SYMBOL)
        if info is None:
            return
        digits = getattr(info, "digits", None)
        if isinstance(digits, bool) or not isinstance(digits, int):
            raise Vt31Nas100LiveError("VT31 provider price digits unavailable")
        if not 0 <= digits <= 10:
            raise Vt31Nas100LiveError("VT31 provider price digits invalid")
        if self._bars and digits != self._price_digits:
            raise Vt31Nas100LiveError("VT31 provider price precision drift")
        self._price_digits = digits
        self._price_quantum = Decimal(1).scaleb(-digits)

    def boundary_snapshot(
        self,
        api: Any,
        *,
        anchor: datetime,
        observed_at: datetime,
    ) -> Vt31Nas100BoundarySnapshot:
        anchor = _utc(anchor, "anchor")
        observed = _utc(observed_at, "observed_at")
        assert_deadline(anchor=anchor, now=observed, stage="boundary_snapshot")
        if observed < anchor:
            raise Vt31Nas100LiveError("VT31 boundary not reached")

        prior = self._bars.get(anchor - timedelta(minutes=1))
        current = self._bars.get(anchor)
        if prior is None or prior.closed_at != anchor:
            raise Vt31Nas100LiveError("VT31 exact newly-closed M1 unavailable")
        if current is None or current.opened_at != anchor:
            raise Vt31Nas100LiveError("VT31 exact new M1 unavailable")

        tick = api.symbol_info_tick(PROVIDER_SYMBOL)
        if tick is None:
            raise Vt31Nas100LiveError("VT31 broker tick unavailable")
        broker_tick_at = _tick_timestamp(tick)
        tick_age = observed - broker_tick_at
        if tick_age < -FUTURE_TICK_TOLERANCE:
            raise Vt31Nas100LiveError("VT31 broker tick is from the future")
        if tick_age > MAX_BROKER_TICK_AGE:
            raise Vt31Nas100LiveError("VT31 broker tick older than 2s")

        closed = tuple(
            self._bars[key]
            for key in sorted(self._bars)
            if self._bars[key].closed_at <= anchor
        )
        if len(closed) < 120:
            raise Vt31Nas100LiveError("VT31 M1 causal cache underfilled")
        fingerprint = _evidence_fingerprint(closed)
        return Vt31Nas100BoundarySnapshot(
            anchor=anchor,
            closed_m1=closed,
            current_open=Decimal(str(current.open)),
            broker_bid=Decimal(str(tick.bid)),
            broker_ask=Decimal(str(tick.ask)),
            broker_tick_at=broker_tick_at,
            observed_at=observed,
            evidence_fingerprint=fingerprint,
        )


def _row_value(row: Any, field: str) -> object:
    try:
        return row[field]
    except (IndexError, KeyError, TypeError, ValueError) as error:
        raise Vt31Nas100LiveError(
            f"VT31 M1 row missing required field {field}"
        ) from error


def _optional_int(row: Any, field: str) -> int | None:
    try:
        value = row[field]
    except (IndexError, KeyError, TypeError, ValueError):
        return None
    if value is None:
        return None
    return int(value)


def _ohlc_payload(values: tuple[str, str, str, str]) -> dict[str, str]:
    return dict(zip(("open", "high", "low", "close"), values, strict=True))


def _canonical_price(value: str, quantum: Decimal) -> str:
    return str(Decimal(value).quantize(quantum, rounding=ROUND_HALF_UP))


def _only_precision_difference(
    previous: _Vt31M1Observation,
    current: _Vt31M1Observation,
) -> bool:
    return (
        previous.canonical_ohlc == current.canonical_ohlc
        and previous.raw_ohlc != current.raw_ohlc
        and previous.tick_volume == current.tick_volume
        and previous.real_volume == current.real_volume
        and previous.spread == current.spread
    )


def _changed_bar_fields(
    previous: _Vt31M1Observation | None,
    current: _Vt31M1Observation,
) -> tuple[str, ...]:
    if previous is None:
        return ("new_bar",)
    fields: list[str] = []
    for index, field in enumerate(("open", "high", "low", "close")):
        if previous.canonical_ohlc[index] != current.canonical_ohlc[index]:
            fields.append(field)
        elif previous.raw_ohlc[index] != current.raw_ohlc[index]:
            fields.append(f"{field}_precision")
    for field in ("tick_volume", "real_volume", "spread"):
        if getattr(previous, field) != getattr(current, field):
            fields.append(field)
    return tuple(fields)


def _bar_differences(
    previous: _Vt31M1Observation | None,
    current: _Vt31M1Observation,
) -> tuple[tuple[str, str, str, str], ...]:
    if previous is None:
        return ()
    differences: list[tuple[str, str, str, str]] = []
    for index, field in enumerate(("open", "high", "low", "close")):
        previous_value = Decimal(previous.raw_ohlc[index])
        current_value = Decimal(current.raw_ohlc[index])
        if previous_value != current_value:
            differences.append(
                (
                    field,
                    str(previous_value),
                    str(current_value),
                    str(current_value - previous_value),
                )
            )
    return tuple(differences)


def next_minute_boundary(now: datetime) -> datetime:
    current = _utc(now, "now")
    base = current.replace(second=0, microsecond=0)
    return base + timedelta(minutes=1)


def boundary_to_arm(now: datetime) -> datetime | None:
    current = _utc(now, "now")
    anchor = next_minute_boundary(current)
    remaining = anchor - current
    if timedelta(0) < remaining <= BOUNDARY_ARM_LEAD:
        return anchor
    return None


def await_boundary_snapshot(
    api: Any,
    *,
    cache: Vt31Nas100M1Cache,
    anchor: datetime,
    now_fn: Callable[[], datetime] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Vt31Nas100BoundarySnapshot:
    clock = now_fn or (lambda: datetime.now(UTC))
    anchor = _utc(anchor, "anchor")
    deadline = anchor + DECISION_DEADLINE
    last_reason = "boundary-data-not-ready"
    last_pre_refresh: datetime | None = None

    while True:
        observed = _utc(clock(), "clock")
        if observed > deadline:
            raise Vt31Nas100SlaExpired(
                f"VT31 hard M1 decision deadline expired:{last_reason}"
            )

        if observed < anchor:
            if (
                last_pre_refresh is None
                or (
                    observed - last_pre_refresh
                ).total_seconds() >= NORMAL_FEED_REFRESH_SECONDS
            ):
                cache.refresh_incremental(
                    api,
                    now=observed,
                    count=RECENT_M1_BARS,
                )
                last_pre_refresh = observed
            remaining = (anchor - observed).total_seconds()
            sleep_fn(min(BOUNDARY_RETRY_SECONDS, max(0.001, remaining)))
            continue

        cache.refresh_incremental(
            api,
            now=observed,
            count=BOUNDARY_RECENT_M1_BARS,
        )
        checked = _utc(clock(), "clock")
        assert_deadline(anchor=anchor, now=checked, stage="post_feed_read")
        try:
            return cache.boundary_snapshot(
                api,
                anchor=anchor,
                observed_at=checked,
            )
        except Vt31Nas100LiveError as error:
            last_reason = str(error)
            remaining = (deadline - checked).total_seconds()
            if remaining <= 0:
                raise Vt31Nas100SlaExpired(
                    f"VT31 hard M1 decision deadline expired:{last_reason}"
                ) from error
            sleep_fn(min(BOUNDARY_RETRY_SECONDS, remaining))


def assert_deadline(
    *,
    anchor: datetime,
    now: datetime,
    stage: str,
) -> None:
    anchor_utc = _utc(anchor, "anchor")
    now_utc = _utc(now, "now")
    if now_utc > anchor_utc + DECISION_DEADLINE:
        raise Vt31Nas100SlaExpired(
            f"VT31 SLA_FAIL_CLOSED:{stage}:deadline_exceeded"
        )


def virtual_oco_trigger(
    candidates: tuple[Vt31VirtualCandidate, ...],
    *,
    bid: Decimal,
    ask: Decimal,
    tick_at: datetime,
    now: datetime,
) -> Vt31VirtualCandidate | None:
    if bid <= 0 or ask <= 0 or ask < bid:
        raise Vt31Nas100LiveError("VT31 broker quote invalid")
    tick_at = _utc(tick_at, "tick_at")
    now = _utc(now, "now")
    age = now - tick_at
    if age < -FUTURE_TICK_TOLERANCE:
        raise Vt31Nas100LiveError("VT31 virtual OCO tick is from the future")
    if age > MAX_BROKER_TICK_AGE:
        raise Vt31Nas100LiveError("VT31 virtual OCO tick older than 2s")

    fillable: list[Vt31VirtualCandidate] = []
    for candidate in candidates:
        if now > candidate.expires_at:
            continue
        if candidate.side == "long" and ask <= candidate.entry_price:
            fillable.append(candidate)
        elif candidate.side == "short" and bid >= candidate.entry_price:
            fillable.append(candidate)

    if not fillable:
        return None
    entries = {item.entry_price for item in fillable}
    if len(entries) != 1:
        raise Vt31Nas100LiveError(
            "VT31 virtual OCO ambiguous multi-price trigger"
        )
    return min(
        fillable,
        key=lambda item: (
            item.formed_at,
            item.family,
            item.candidate_id,
        ),
    )


def nominal_risk_r(
    *,
    tier: str,
    rearm_quality: str | None = None,
) -> Decimal:
    if tier == "CORE":
        return Decimal("1.00")
    if tier == "SECONDARY":
        return Decimal("0.05")
    if tier == "SCOUT":
        return Decimal("0.02")
    if tier != "REARM":
        raise ValueError("VT31 unknown tier")
    if rearm_quality == "HIGH":
        return Decimal("0.10")
    if rearm_quality == "MID":
        return Decimal("0.05")
    if rearm_quality == "LOW":
        return Decimal("0.02")
    raise ValueError("VT31 rearm quality required")


def resolve_certified_risk(context: Vt31RiskContext) -> Vt31RiskResolution:
    reasons: list[str] = []
    allocation = _allocation_multiplier(context, reasons)
    global_scalar = Decimal("0.60")
    state_shield = (
        Decimal("0.60") if _state_shielded(context, reasons) else Decimal("1")
    )
    loss_cluster = (
        Decimal("0.35")
        if (
            context.entry_family == "order-block"
            and context.confirmation_latency_minutes is not None
            and context.confirmation_latency_minutes >= 11
        )
        else Decimal("1")
    )
    if loss_cluster != 1:
        reasons.append("LOSS_CLUSTER_OB_LATENCY_GE_11_X035")

    breaker_regime = (
        Decimal("0.35")
        if _breaker_regime_shielded(context, reasons)
        else Decimal("1")
    )
    final = (
        context.nominal_risk_r
        * allocation
        * global_scalar
        * state_shield
        * loss_cluster
        * breaker_regime
    )
    if final <= 0:
        raise ValueError("VT31 final certified risk must be positive")
    return Vt31RiskResolution(
        nominal_risk_r=context.nominal_risk_r,
        allocation_multiplier=allocation,
        global_scalar=global_scalar,
        state_shield_multiplier=state_shield,
        loss_cluster_multiplier=loss_cluster,
        breaker_regime_multiplier=breaker_regime,
        final_risk_r=final,
        reasons=tuple(reasons),
    )


def build_risk_request(
    *,
    request_id: str,
    signal_fingerprint: str,
    side: str,
    entry: Decimal,
    stop_loss: Decimal,
    take_profit: Decimal,
    certified_risk_r: Decimal,
    provider_spec: Mt5SymbolSpecification,
    account_equity: Decimal,
    decision_anchor: datetime,
    reservation_expires_at: datetime,
    now: datetime,
) -> tuple[CiboRiskRequest, Decimal]:
    decision_anchor = _utc(decision_anchor, "decision_anchor")
    reservation_expires_at = _utc(
        reservation_expires_at,
        "reservation_expires_at",
    )
    now = _utc(now, "now")
    assert_deadline(
        anchor=decision_anchor,
        now=now,
        stage="risk_request",
    )
    if reservation_expires_at <= now:
        raise Vt31Nas100LiveError("VT31 pending expiry already elapsed")

    if side not in {"long", "short"}:
        raise ValueError("VT31 risk request side invalid")
    if certified_risk_r <= 0 or account_equity <= 0:
        raise ValueError("VT31 risk/equity invalid")
    if side == "long" and not stop_loss < entry < take_profit:
        raise ValueError("VT31 long geometry invalid")
    if side == "short" and not take_profit < entry < stop_loss:
        raise ValueError("VT31 short geometry invalid")
    if not provider_spec.trade_enabled or not provider_spec.session_open:
        raise Vt31Nas100LiveError("VT31 broker trading unavailable")
    if provider_spec.provider_symbol != PROVIDER_SYMBOL:
        raise Vt31Nas100LiveError("VT31 provider symbol binding drift")
    if now - provider_spec.observed_at > MAX_BROKER_TICK_AGE:
        raise Vt31Nas100LiveError("VT31 broker symbol snapshot older than 2s")

    for name, value in (
        ("volume_min", provider_spec.minimum_volume),
        ("volume_step", provider_spec.volume_step),
        ("volume_max", provider_spec.maximum_volume),
        ("tick_size", provider_spec.tick_size),
        ("tick_value", provider_spec.tick_value),
        ("contract_size", provider_spec.contract_size),
        ("point", provider_spec.point),
        ("margin_per_volume", provider_spec.margin_per_volume),
    ):
        if value <= 0:
            raise ValueError(f"VT31 broker {name} invalid")

    stop_points = abs(entry - stop_loss) / provider_spec.point
    target_points = abs(take_profit - entry) / provider_spec.point
    if stop_points < provider_spec.minimum_stop_distance_points:
        raise Vt31Nas100LiveError("VT31 stop inside broker stops level")
    if target_points < provider_spec.minimum_stop_distance_points:
        raise Vt31Nas100LiveError("VT31 target inside broker stops level")

    ticks = abs(entry - stop_loss) / provider_spec.tick_size
    stop_per_volume = ticks * provider_spec.tick_value * BROKER_RISK_BUFFER
    one_r_usd = account_equity * QORE_ONE_R_ACCOUNT_FRACTION
    requested_risk_usd = one_r_usd * certified_risk_r
    volume = _floor_to_step(
        requested_risk_usd / stop_per_volume,
        provider_spec.volume_step,
    )
    volume = min(volume, provider_spec.maximum_volume)
    if volume < provider_spec.minimum_volume:
        raise Vt31Nas100LiveError(
            "VT31 certified risk maps below broker minimum volume"
        )
    half_leg = _floor_to_step(
        volume * Decimal("0.50"),
        provider_spec.volume_step,
    )
    quarter_leg = _floor_to_step(
        volume * Decimal("0.25"),
        provider_spec.volume_step,
    )
    if (
        half_leg < provider_spec.minimum_volume
        or quarter_leg < provider_spec.minimum_volume
    ):
        raise Vt31Nas100LiveError(
            "VT31 broker granularity cannot express certified partial legs"
        )

    request = CiboRiskRequest(
        request_id=request_id,
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint=signal_fingerprint,
        qore_symbol=SYMBOL,
        provider_symbol=provider_spec.provider_symbol,
        side=side,
        entry_type="limit",
        intended_entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        requested_volume=volume,
        volume_step=provider_spec.volume_step,
        minimum_volume=provider_spec.minimum_volume,
        stop_loss_per_volume=stop_per_volume,
        margin_per_volume=provider_spec.margin_per_volume,
        requested_at=now,
        expires_at=reservation_expires_at,
    )
    return request, one_r_usd


def signal_fingerprint(material: dict[str, object]) -> str:
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _allocation_multiplier(
    context: Vt31RiskContext,
    reasons: list[str],
) -> Decimal:
    if context.tier == "CORE":
        if context.entry_family == "breaker":
            reasons.append("ALLOC_G_CORE_BREAKER_X120")
            return Decimal("1.20")
        if context.entry_family == "fair-value-gap":
            reasons.append("ALLOC_G_CORE_FVG_X050")
            return Decimal("0.50")
        if context.entry_family == "order-block":
            reasons.append("ALLOC_G_CORE_OB_X050")
            return Decimal("0.50")
        return Decimal("1")

    if context.tier == "SCOUT":
        reasons.append("ALLOC_G_SCOUT_X050")
        return Decimal("0.50")
    if context.tier == "REARM":
        reasons.append("ALLOC_G_REARM_X050")
        return Decimal("0.50")

    if (
        context.tier == "SECONDARY"
        and context.entry_family == "fair-value-gap"
        and context.h1_state == "mixed"
    ):
        reasons.append("ALLOC_G_SECONDARY_FVG_H1_MIXED_X100")
        return Decimal("1.00")

    weak = (
        context.entry_family == "breaker"
        or (
            context.entry_family == "order-block"
            and context.side == "long"
        )
        or context.cash_open_state == "bullish"
    )
    if weak:
        reasons.append("ALLOC_G_SECONDARY_WEAK_X050")
        return Decimal("0.50")
    reasons.append("ALLOC_G_SECONDARY_OTHER_X075")
    return Decimal("0.75")


def _state_shielded(
    context: Vt31RiskContext,
    reasons: list[str],
) -> bool:
    matched = False
    if (
        context.entry_family == "fair-value-gap"
        and context.premarket_state == "rotation"
    ):
        reasons.append("SHIELD_FVG_PREMARKET_ROTATION_X060")
        matched = True
    if context.entry_family == "fair-value-gap" and context.h1_state == "bullish":
        reasons.append("SHIELD_FVG_H1_BULLISH_X060")
        matched = True
    if (
        context.entry_family == "order-block"
        and context.risk_ref is not None
        and context.risk_ref < Decimal("0.30")
    ):
        reasons.append("SHIELD_OB_LOW_RISK_REF_X060")
        matched = True
    if (
        context.entry_family == "order-block"
        and context.current_path_vs_previous is not None
        and context.current_path_vs_previous < Decimal("0.75")
    ):
        reasons.append("SHIELD_OB_LOW_CURRENT_PATH_X060")
        matched = True
    if context.tier == "SECONDARY" and context.entry_family == "breaker":
        reasons.append("SHIELD_SECONDARY_BREAKER_X060")
        matched = True
    latency = context.confirmation_latency_minutes
    if context.tier == "REARM" and latency is not None and 3 <= latency <= 5:
        reasons.append("SHIELD_REARM_LATENCY_3_5_X060")
        matched = True
    if context.tier == "REARM" and context.premarket_state == "rotation":
        reasons.append("SHIELD_REARM_PREMARKET_ROTATION_X060")
        matched = True
    if context.tier == "REARM" and context.cash_open_state == "bullish":
        reasons.append("SHIELD_REARM_CASH_OPEN_BULLISH_X060")
        matched = True
    return matched


def _breaker_regime_shielded(
    context: Vt31RiskContext,
    reasons: list[str],
) -> bool:
    latency = context.confirmation_latency_minutes
    primary = (
        context.entry_family == "breaker"
        and latency is not None
        and 3 <= latency <= 5
        and context.premarket_state == "bearish"
    )
    secondary = (
        context.entry_family == "breaker"
        and context.side == "short"
        and context.cash_open_state == "rotation"
        and context.risk_ref is not None
        and context.risk_ref < Decimal("0.30")
    )
    if primary:
        reasons.append("BREAKER_REGIME_PRIMARY_X035")
    if secondary:
        reasons.append("BREAKER_REGIME_SECONDARY_X035")
    return primary or secondary


def _tick_timestamp(tick: Any) -> datetime:
    raw_msc = int(getattr(tick, "time_msc", 0) or 0)
    if raw_msc > 0:
        raw_seconds, millis = divmod(raw_msc, 1000)
        return normalise_fundednext_server_epoch(raw_seconds) + timedelta(
            milliseconds=millis
        )
    raw_seconds = int(getattr(tick, "time", 0) or 0)
    if raw_seconds <= 0:
        raise Vt31Nas100LiveError("VT31 broker tick timestamp unavailable")
    return normalise_fundednext_server_epoch(raw_seconds)


def _evidence_fingerprint(bars: tuple[OhlcSnapshot, ...]) -> str:
    material = [
        (
            bar.opened_at.isoformat(),
            bar.closed_at.isoformat(),
            str(bar.open),
            str(bar.high),
            str(bar.low),
            str(bar.close),
        )
        for bar in bars
    ]
    return hashlib.sha256(
        json.dumps(material, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        raise ValueError("VT31 volume step must be positive")
    units = (value / step).to_integral_value(rounding=ROUND_FLOOR)
    return units * step


def _utc(value: datetime, field: str) -> datetime:
    _aware(value, field)
    return value.astimezone(UTC)


def _aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
