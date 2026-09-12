"""VT-08 V2 — source-bound TTrades 4H Power-of-Three research contract.

Primary source
--------------
Human Owner-provided TTrades video ``youtube:FAKWJ-1NlLE``
(``1000854868.mp4``, SHA-256
``bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271``).

This module encodes only rules demonstrated or stated by that lesson and the
explicitly required TTrades Candle-2/Candle-3/CISD prerequisites. Qualitative
teaching is not converted into invented numerical thresholds.

Human Owner operating scope
---------------------------
The source may show the complete repeating H4 cycle, but QORE is explicitly
restricted to three New York opening anchors per asset family:

- Forex: 01:00 / 05:00 / 09:00 America/New_York
- Futures: 02:00 / 06:00 / 10:00 America/New_York

Only the configured Forex and futures markets are in scope. XAUUSD is outside
this VT-08 campaign. Source-cycle anchors outside the Human Owner operating scope
must abstain and may not be introduced by research or optimization.

Execution boundary
------------------
The lesson demonstrates several executable entry/exit families rather than one
universal geometry.  This module consequently requires an explicit, causal
execution plan identifying the demonstrated family and its structural evidence.
Resolved cases emit ``SETUP``; only the unresolved case abstains.

Outputs grant no Risk, broker, DEMO, LIVE, Production, or real-capital authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.kernel.errors import InfrastructureError

TRADER_CODE = "vt-08"
TRADER_VERSION = "v2"
METHODOLOGY_ID = "ttrades-h4-po3-source"
METHODOLOGY_VERSION = "v2.6-source-executable"
PRIMARY_SOURCE = "youtube:FAKWJ-1NlLE"
PRIMARY_SOURCE_SHA256 = (
    "bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271"
)
SUPPORTED_MARKETS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "SP500",
    "US30",
    "USDCAD",
    "USDJPY",
)
FUTURES_MARKETS = frozenset({"NAS100", "SP500", "US30"})
FX_MARKETS = frozenset(
    {"AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD", "USDCAD", "USDJPY"}
)
SOURCE_TIMING_AMBIGUOUS_MARKETS: frozenset[str] = frozenset()
SOURCE_FOREX_H4_ANCHOR_HOURS = (1, 5, 9, 13, 17, 21)
SOURCE_FUTURES_H4_ANCHOR_HOURS = (2, 6, 10, 14, 18, 22)
FOREX_H4_ANCHOR_HOURS = (1, 5, 9)
FUTURES_H4_ANCHOR_HOURS = (2, 6, 10)
_NY = ZoneInfo("America/New_York")

RULESET = (
    "primary-video-only-plus-explicit-prerequisites;h4-po3-amd;"
    "human-owner-operating-scope-forex-01-05-09-new-york;"
    "human-owner-operating-scope-futures-02-06-10-new-york;"
    "out-of-owner-scope-h4-anchors-must-abstain;"
    "candle2-shallow-wick-reversal-to-expansion;"
    "candle2-large-opposing-run-wait-candle3-continuation;"
    "m15-lower-timeframe-confirmation;source-poi-reach-required-before-cisd;"
    "cisd-protected-swing;let-wick-form-trade-body;"
    "bias-is-explicit-causal-source-context;"
    "wick-size-is-explicit-qualitative-source-judgment;"
    "cisd-close-confirms-protected-swing;contextual-entry-families;"
    "protected-swing-extreme-is-invalidation-reference;"
    "no-invented-wick-threshold;no-mandatory-d1-formula;"
    "no-invented-poi-selection;structural-or-conditioned-2r-or-minus-1sd-target;"
    "resolved-context-emits-setup;unresolved-context-abstains;research-only"
)


class Vt08CrtH4AmdV2Error(InfrastructureError):
    __slots__ = ()


class Vt08CrtH4AmdV2ValidationError(Vt08CrtH4AmdV2Error):
    __slots__ = ()


class Vt08CrtH4AmdV2Scenario(StrEnum):
    REVERSAL_EXPANSION_C2 = "reversal-expansion-candle2"
    CONTINUATION_EXPANSION_C3 = "continuation-expansion-candle3"


class Vt08CrtH4AmdV2WickProfile(StrEnum):
    """Qualitative source language; deliberately not derived from a ratio."""

    SHALLOW = "shallow"
    LARGE = "large-deep-opposing-run"
    UNRESOLVED = "unresolved"


class Vt08CrtH4AmdV2TimingFamily(StrEnum):
    FUTURES = "futures-owner-02-06-10-new-york"
    FOREX = "forex-owner-01-05-09-new-york"
    SOURCE_UNRESOLVED = "source-unresolved"


class Vt08CrtH4AmdV2PoiType(StrEnum):
    FAIR_VALUE_GAP = "fair-value-gap"
    PREVIOUS_DAY_EXTREME = "previous-day-extreme"
    FAILURE_SWING = "failure-swing"
    CANDLE_EQUILIBRIUM = "candle-equilibrium-tspot"
    IMPORTANT_HIGH_LOW = "important-high-low"


class Vt08CrtH4AmdV2EntryModel(StrEnum):
    CISD_CONFIRMATION_CLOSE = "cisd-confirmation-close"
    POSITIONAL_H4_OPEN = "positional-new-h4-open"
    PROTECTED_SWING_CONTINUATION = "protected-swing-continuation"


class Vt08CrtH4AmdV2TargetType(StrEnum):
    STRUCTURAL_OBJECTIVE = "structural-objective"
    CONDITIONED_TWO_R = "conditioned-two-r"
    NEGATIVE_ONE_STANDARD_DEVIATION = "negative-one-standard-deviation"


class Vt08CrtH4AmdV2AbstainReason(StrEnum):
    UNSUPPORTED_MARKET = "unsupported-market"
    TIMING_FAMILY_REQUIRED = "source-timing-family-required"
    OUTSIDE_SOURCE_H4_ANCHOR = "outside-owner-operating-h4-anchor"
    INVALID_M15_EVIDENCE = "invalid-m15-evidence"
    BIAS_CONTEXT_REQUIRED = "bias-context-required-by-source"
    POINT_OF_INTEREST_REQUIRED = "source-point-of-interest-required"
    POINT_OF_INTEREST_NOT_REACHED = "source-point-of-interest-not-reached"
    NON_CAUSAL_SOURCE_CONTEXT = "source-context-observed-after-confirmation"
    WICK_CLASSIFICATION_REQUIRED = "qualitative-wick-classification-required"
    WAIT_FOR_CANDLE3 = "large-candle2-run-wait-for-candle3"
    CANDLE2_LARGE_RUN_REQUIRED = "candle3-requires-large-candle2-opposing-run"
    CANDLE2_REVERSAL_REQUIRED = "candle3-requires-candle2-reversal"
    REFERENCE_BOUNDARY_NOT_RUN = "reference-boundary-not-run"
    NO_CISD_PROTECTED_SWING = "no-cisd-protected-swing"
    EXECUTION_PLAN_REQUIRED = "source-execution-plan-required"
    UNRESOLVED_POI_AMBIGUITY = "unresolved-poi-ambiguity"
    INVALID_ENTRY = "invalid-entry"
    INVALID_STOP = "invalid-stop"
    INVALID_TARGET = "invalid-target"
    SOURCE_EXECUTION_CONTRACT_INCOMPLETE = "source-execution-entry-target-unresolved"
    INVALID_GEOMETRY = "invalid-geometry"


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Candle:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        for field_name, timestamp_value in (
            ("opened_at", self.opened_at),
            ("closed_at", self.closed_at),
        ):
            if timestamp_value.tzinfo is None or timestamp_value.utcoffset() is None:
                raise Vt08CrtH4AmdV2ValidationError(
                    f"{field_name} must be timezone-aware"
                )
        if self.closed_at <= self.opened_at:
            raise Vt08CrtH4AmdV2ValidationError("candle close must follow open")
        for field_name, price_value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            if not price_value.is_finite() or price_value <= 0:
                raise Vt08CrtH4AmdV2ValidationError(
                    f"{field_name} must be positive finite Decimal"
                )
        if self.low > self.high:
            raise Vt08CrtH4AmdV2ValidationError("low must not exceed high")
        if self.low > min(self.open, self.close) or self.high < max(
            self.open, self.close
        ):
            raise Vt08CrtH4AmdV2ValidationError("OHLC body must lie inside high/low")


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2SourceContext:
    """Source-required qualitative evidence unavailable from raw OHLC alone.

    ``observed_at`` is the latest decision-time observation used by this context,
    so a later annotation cannot authorize an earlier confirmation. The POI fields
    retain whether a source-defined point of interest was reached without inventing
    which FVG/high/low should be selected when the lesson leaves that discretionary.
    """

    bias_side: DemoTradingSetupSide | None
    wick_profile: Vt08CrtH4AmdV2WickProfile
    point_of_interest_reached: bool | None
    point_of_interest_provenance: str | None
    observed_at: datetime
    provenance: str
    execution_plan: Vt08CrtH4AmdV2ExecutionPlan | None = None

    def __post_init__(self) -> None:
        if self.bias_side is not None and type(self.bias_side) is not DemoTradingSetupSide:
            raise Vt08CrtH4AmdV2ValidationError("bias_side must be canonical or None")
        if type(self.wick_profile) is not Vt08CrtH4AmdV2WickProfile:
            raise Vt08CrtH4AmdV2ValidationError("wick_profile must be exact source enum")
        if (
            self.point_of_interest_reached is not None
            and type(self.point_of_interest_reached) is not bool
        ):
            raise Vt08CrtH4AmdV2ValidationError(
                "point_of_interest_reached must be exact bool or None"
            )
        if self.point_of_interest_provenance is not None and (
            type(self.point_of_interest_provenance) is not str
            or not self.point_of_interest_provenance.strip()
        ):
            raise Vt08CrtH4AmdV2ValidationError(
                "point_of_interest_provenance must be non-empty str or None"
            )
        if (
            self.point_of_interest_reached is not None
            and self.point_of_interest_provenance is None
        ):
            raise Vt08CrtH4AmdV2ValidationError(
                "resolved point-of-interest state requires provenance"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise Vt08CrtH4AmdV2ValidationError("context observed_at must be timezone-aware")
        if type(self.provenance) is not str or not self.provenance.strip():
            raise Vt08CrtH4AmdV2ValidationError("source context provenance is required")
        if self.execution_plan is not None and type(
            self.execution_plan
        ) is not Vt08CrtH4AmdV2ExecutionPlan:
            raise Vt08CrtH4AmdV2ValidationError("execution_plan must be exact or None")


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2PointOfInterest:
    poi_type: Vt08CrtH4AmdV2PoiType
    timeframe: str
    formed_at: datetime
    confirmed_at: datetime
    lower_bound: Decimal
    upper_bound: Decimal
    direction: DemoTradingSetupSide
    source_timestamp: str
    evidence_ids: tuple[str, ...]
    selection_reason: str

    def __post_init__(self) -> None:
        if type(self.poi_type) is not Vt08CrtH4AmdV2PoiType:
            raise Vt08CrtH4AmdV2ValidationError("POI type must be exact")
        if type(self.direction) is not DemoTradingSetupSide:
            raise Vt08CrtH4AmdV2ValidationError("POI direction must be exact")
        if (
            self.formed_at.tzinfo is None
            or self.formed_at.utcoffset() is None
            or self.confirmed_at.tzinfo is None
            or self.confirmed_at.utcoffset() is None
        ):
            raise Vt08CrtH4AmdV2ValidationError("POI timestamps must be aware")
        if self.formed_at > self.confirmed_at:
            raise Vt08CrtH4AmdV2ValidationError("POI cannot confirm before formation")
        if not (Decimal(0) < self.lower_bound <= self.upper_bound):
            raise Vt08CrtH4AmdV2ValidationError("POI bounds are invalid")
        if not self.timeframe or not self.source_timestamp or not self.selection_reason:
            raise Vt08CrtH4AmdV2ValidationError("POI provenance fields are required")
        if not self.evidence_ids or len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise Vt08CrtH4AmdV2ValidationError("POI evidence ids must be unique")


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2ExecutionPlan:
    """Decision-time reconstruction of one entry family shown in the source."""

    entry_model: Vt08CrtH4AmdV2EntryModel
    entry_price: Decimal
    methodological_stop: Decimal
    target_type: Vt08CrtH4AmdV2TargetType
    target_price: Decimal
    poi: Vt08CrtH4AmdV2PointOfInterest
    created_at: datetime
    valid_until: datetime
    source_timestamps: tuple[str, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.entry_model) is not Vt08CrtH4AmdV2EntryModel:
            raise Vt08CrtH4AmdV2ValidationError("entry model must be exact")
        if type(self.target_type) is not Vt08CrtH4AmdV2TargetType:
            raise Vt08CrtH4AmdV2ValidationError("target type must be exact")
        if type(self.poi) is not Vt08CrtH4AmdV2PointOfInterest:
            raise Vt08CrtH4AmdV2ValidationError("execution POI must be exact")
        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
            or self.valid_until.tzinfo is None
            or self.valid_until.utcoffset() is None
        ):
            raise Vt08CrtH4AmdV2ValidationError("execution timestamps must be aware")
        if self.created_at >= self.valid_until:
            raise Vt08CrtH4AmdV2ValidationError("execution plan must have positive life")
        if self.created_at < self.poi.confirmed_at:
            raise Vt08CrtH4AmdV2ValidationError("execution cannot predate its POI")
        prices = (
            ("entry", self.entry_price),
            ("stop", self.methodological_stop),
            ("target", self.target_price),
        )
        for name, value in prices:
            if not value.is_finite() or value <= 0:
                raise Vt08CrtH4AmdV2ValidationError(f"{name} must be positive finite")
        if (
            not self.source_timestamps
            or len(set(self.source_timestamps)) != len(self.source_timestamps)
            or not self.evidence_ids
            or len(set(self.evidence_ids)) != len(self.evidence_ids)
        ):
            raise Vt08CrtH4AmdV2ValidationError("execution provenance is required")


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Setup:
    side: DemoTradingSetupSide
    scenario: Vt08CrtH4AmdV2Scenario
    entry_model: Vt08CrtH4AmdV2EntryModel
    entry_price: Decimal
    methodological_invalidation: Decimal
    stop_price: Decimal
    target_type: Vt08CrtH4AmdV2TargetType
    target_price: Decimal
    expected_r: Decimal
    signal_at: datetime
    expires_at: datetime
    cisd_level: Decimal
    protected_swing_extreme: Decimal
    poi: Vt08CrtH4AmdV2PointOfInterest
    evidence_fingerprint: str
    methodology_fingerprint: str
    source_identity: str = PRIMARY_SOURCE
    source_sha256: str = PRIMARY_SOURCE_SHA256

    def __post_init__(self) -> None:
        if self.signal_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise Vt08CrtH4AmdV2ValidationError("setup timestamps must be aware")
        if self.signal_at >= self.expires_at:
            raise Vt08CrtH4AmdV2ValidationError("setup must expire after its signal")
        valid = (
            self.stop_price < self.entry_price < self.target_price
            if self.side is DemoTradingSetupSide.LONG
            else self.target_price < self.entry_price < self.stop_price
        )
        if not valid or self.expected_r <= 0:
            raise Vt08CrtH4AmdV2ValidationError("invalid setup geometry")
        risk = abs(self.entry_price - self.stop_price)
        reward = abs(self.target_price - self.entry_price)
        if self.expected_r != reward / risk:
            raise Vt08CrtH4AmdV2ValidationError("expected R must match setup geometry")
        for fingerprint in (self.evidence_fingerprint, self.methodology_fingerprint):
            if len(fingerprint) != 64 or any(c not in "0123456789abcdef" for c in fingerprint):
                raise Vt08CrtH4AmdV2ValidationError("fingerprints must be SHA-256")
        if self.source_identity != PRIMARY_SOURCE or self.source_sha256 != PRIMARY_SOURCE_SHA256:
            raise Vt08CrtH4AmdV2ValidationError("setup source identity is immutable")


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2ConfirmedOpportunity:
    """Source-confirmed research state; deliberately not an executable setup."""

    side: DemoTradingSetupSide
    scenario: Vt08CrtH4AmdV2Scenario
    confirmation_price: Decimal
    signal_at: datetime
    expires_at: datetime
    cisd_level: Decimal
    protected_swing_extreme: Decimal
    wick_profile: Vt08CrtH4AmdV2WickProfile
    point_of_interest_provenance: str
    executable_entry_price: None = None
    take_profit: None = None

    def __post_init__(self) -> None:
        if self.signal_at.tzinfo is None or self.signal_at.utcoffset() is None:
            raise Vt08CrtH4AmdV2ValidationError("signal_at must be timezone-aware")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise Vt08CrtH4AmdV2ValidationError("expires_at must be timezone-aware")
        if self.signal_at >= self.expires_at:
            raise Vt08CrtH4AmdV2ValidationError("confirmation must precede H4 close")
        for field_name, value in (
            ("confirmation_price", self.confirmation_price),
            ("cisd_level", self.cisd_level),
            ("protected_swing_extreme", self.protected_swing_extreme),
        ):
            if not value.is_finite() or value <= 0:
                raise Vt08CrtH4AmdV2ValidationError(
                    f"{field_name} must be positive finite Decimal"
                )
        if (
            type(self.point_of_interest_provenance) is not str
            or not self.point_of_interest_provenance.strip()
        ):
            raise Vt08CrtH4AmdV2ValidationError(
                "confirmed opportunity requires point-of-interest provenance"
            )
        directional = (
            self.protected_swing_extreme < self.confirmation_price
            if self.side is DemoTradingSetupSide.LONG
            else self.confirmation_price < self.protected_swing_extreme
        )
        if not directional:
            raise Vt08CrtH4AmdV2ValidationError(
                "protected-swing invalidation must be strictly directional"
            )
        if self.executable_entry_price is not None or self.take_profit is not None:
            raise Vt08CrtH4AmdV2ValidationError(
                "source does not authorize a universal executable entry/target"
            )


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Evaluation:
    decision: DemoTradingDecision
    confirmed_opportunity: Vt08CrtH4AmdV2ConfirmedOpportunity | None
    abstain_reason: Vt08CrtH4AmdV2AbstainReason | None
    methodology_fingerprint: str
    setup: Vt08CrtH4AmdV2Setup | None = None


def methodology_fingerprint() -> str:
    material = {
        "trader_code": TRADER_CODE,
        "trader_version": TRADER_VERSION,
        "methodology_id": METHODOLOGY_ID,
        "methodology_version": METHODOLOGY_VERSION,
        "primary_source": PRIMARY_SOURCE,
        "primary_source_sha256": PRIMARY_SOURCE_SHA256,
        "ruleset": RULESET,
        "supported_markets": SUPPORTED_MARKETS,
        "source_forex_h4_anchor_hours": SOURCE_FOREX_H4_ANCHOR_HOURS,
        "source_futures_h4_anchor_hours": SOURCE_FUTURES_H4_ANCHOR_HOURS,
        "owner_forex_h4_anchor_hours": FOREX_H4_ANCHOR_HOURS,
        "owner_futures_h4_anchor_hours": FUTURES_H4_ANCHOR_HOURS,
    }
    return sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def timing_family_for_market(symbol: str) -> Vt08CrtH4AmdV2TimingFamily | None:
    """Map only Human Owner-authorized Forex and futures markets."""

    if symbol not in SUPPORTED_MARKETS:
        return None
    if symbol in FUTURES_MARKETS:
        return Vt08CrtH4AmdV2TimingFamily.FUTURES
    if symbol in FX_MARKETS:
        return Vt08CrtH4AmdV2TimingFamily.FOREX
    return None


def source_anchor_hours_for_market(symbol: str) -> tuple[int, ...] | None:
    """Return the Human Owner-authorized operating anchors in New York time."""

    family = timing_family_for_market(symbol)
    if family is Vt08CrtH4AmdV2TimingFamily.FOREX:
        return FOREX_H4_ANCHOR_HOURS
    if family is Vt08CrtH4AmdV2TimingFamily.FUTURES:
        return FUTURES_H4_ANCHOR_HOURS
    return None


def _protected_swing(
    bars: tuple[Vt08CrtH4AmdV2Candle, ...],
    *,
    side: DemoTradingSetupSide,
    required_run_level: Decimal | None,
) -> tuple[Vt08CrtH4AmdV2Candle, Decimal, Decimal] | None:
    """Return first causal CISD confirmation after the opposing run."""

    sequence_open: Decimal | None = None
    extreme: Decimal | None = None
    extreme_index: int | None = None
    run_observed = required_run_level is None
    in_opposing_sequence = False

    for index, bar in enumerate(bars):
        if required_run_level is not None:
            if side is DemoTradingSetupSide.LONG and bar.low < required_run_level:
                run_observed = True
            elif side is DemoTradingSetupSide.SHORT and bar.high > required_run_level:
                run_observed = True

        opposing = (
            bar.close < bar.open
            if side is DemoTradingSetupSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            if not in_opposing_sequence:
                sequence_open = bar.open
            candidate = bar.low if side is DemoTradingSetupSide.LONG else bar.high
            if extreme is None or (
                candidate < extreme
                if side is DemoTradingSetupSide.LONG
                else candidate > extreme
            ):
                extreme = candidate
                extreme_index = index
            in_opposing_sequence = True
            continue

        if (
            run_observed
            and sequence_open is not None
            and extreme is not None
            and extreme_index is not None
            and index > extreme_index
        ):
            confirmed = (
                bar.close > sequence_open
                if side is DemoTradingSetupSide.LONG
                else bar.close < sequence_open
            )
            if confirmed:
                return bar, sequence_open, extreme
        in_opposing_sequence = False
    return None


def _abstain(
    reason: Vt08CrtH4AmdV2AbstainReason,
    *,
    confirmed_opportunity: Vt08CrtH4AmdV2ConfirmedOpportunity | None = None,
) -> Vt08CrtH4AmdV2Evaluation:
    return Vt08CrtH4AmdV2Evaluation(
        decision=DemoTradingDecision.ABSTAIN,
        confirmed_opportunity=confirmed_opportunity,
        abstain_reason=reason,
        methodology_fingerprint=methodology_fingerprint(),
    )


def _valid_m15_window(
    bars: tuple[Vt08CrtH4AmdV2Candle, ...],
    *,
    h4_closes_at: datetime,
) -> bool:
    if h4_closes_at.tzinfo is None or h4_closes_at.utcoffset() is None:
        return False
    if not bars:
        return False
    h4_opened_at = h4_closes_at - timedelta(hours=4)
    previous_close: datetime | None = None
    for bar in bars:
        if bar.closed_at - bar.opened_at != timedelta(minutes=15):
            return False
        if not (h4_opened_at <= bar.opened_at < bar.closed_at <= h4_closes_at):
            return False
        if previous_close is not None and bar.opened_at != previous_close:
            return False
        previous_close = bar.closed_at
    return True


def _validate_common(
    *,
    symbol: str,
    h4_closes_at: datetime,
    observed_m15: tuple[Vt08CrtH4AmdV2Candle, ...],
    context: Vt08CrtH4AmdV2SourceContext,
) -> Vt08CrtH4AmdV2Evaluation | None:
    family = timing_family_for_market(symbol)
    if family is None:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.UNSUPPORTED_MARKET)
    if family is Vt08CrtH4AmdV2TimingFamily.SOURCE_UNRESOLVED:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.TIMING_FAMILY_REQUIRED)
    if h4_closes_at.tzinfo is None or h4_closes_at.utcoffset() is None:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_GEOMETRY)
    local_open = (h4_closes_at - timedelta(hours=4)).astimezone(_NY)
    anchors = source_anchor_hours_for_market(symbol)
    if (
        anchors is None
        or local_open.minute != 0
        or local_open.second != 0
        or local_open.microsecond != 0
    ):
        return _abstain(Vt08CrtH4AmdV2AbstainReason.OUTSIDE_SOURCE_H4_ANCHOR)
    if local_open.hour not in anchors:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.OUTSIDE_SOURCE_H4_ANCHOR)
    if not _valid_m15_window(observed_m15, h4_closes_at=h4_closes_at):
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_M15_EVIDENCE)
    if context.bias_side is None:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.BIAS_CONTEXT_REQUIRED)
    if context.point_of_interest_reached is None:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.POINT_OF_INTEREST_REQUIRED)
    if context.point_of_interest_reached is False:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.POINT_OF_INTEREST_NOT_REACHED)
    if context.wick_profile is Vt08CrtH4AmdV2WickProfile.UNRESOLVED:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.WICK_CLASSIFICATION_REQUIRED)
    return None


def _confirmed_opportunity(
    *,
    side: DemoTradingSetupSide,
    scenario: Vt08CrtH4AmdV2Scenario,
    confirmation: Vt08CrtH4AmdV2Candle,
    cisd_level: Decimal,
    extreme: Decimal,
    expires_at: datetime,
    context: Vt08CrtH4AmdV2SourceContext,
) -> Vt08CrtH4AmdV2Evaluation:
    if context.observed_at.astimezone(UTC) > confirmation.closed_at.astimezone(UTC):
        return _abstain(Vt08CrtH4AmdV2AbstainReason.NON_CAUSAL_SOURCE_CONTEXT)
    if context.point_of_interest_provenance is None:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.POINT_OF_INTEREST_REQUIRED)
    try:
        opportunity = Vt08CrtH4AmdV2ConfirmedOpportunity(
            side=side,
            scenario=scenario,
            confirmation_price=confirmation.close,
            signal_at=confirmation.closed_at.astimezone(UTC),
            expires_at=expires_at.astimezone(UTC),
            cisd_level=cisd_level,
            protected_swing_extreme=extreme,
            wick_profile=context.wick_profile,
            point_of_interest_provenance=context.point_of_interest_provenance,
        )
    except Vt08CrtH4AmdV2ValidationError:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_GEOMETRY)
    plan = context.execution_plan
    if plan is None:
        return _abstain(
            Vt08CrtH4AmdV2AbstainReason.EXECUTION_PLAN_REQUIRED,
            confirmed_opportunity=opportunity,
        )
    confirmation_at = confirmation.closed_at.astimezone(UTC)
    if (
        plan.created_at.astimezone(UTC) > confirmation_at
        or plan.poi.confirmed_at.astimezone(UTC) > confirmation_at
        or plan.valid_until.astimezone(UTC) > expires_at.astimezone(UTC)
        or plan.poi.direction is not side
    ):
        return _abstain(Vt08CrtH4AmdV2AbstainReason.NON_CAUSAL_SOURCE_CONTEXT)
    if not (plan.poi.lower_bound <= plan.entry_price <= plan.poi.upper_bound):
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_ENTRY)
    if plan.methodological_stop != extreme:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_STOP)
    risk = (
        plan.entry_price - plan.methodological_stop
        if side is DemoTradingSetupSide.LONG
        else plan.methodological_stop - plan.entry_price
    )
    reward = (
        plan.target_price - plan.entry_price
        if side is DemoTradingSetupSide.LONG
        else plan.entry_price - plan.target_price
    )
    if risk <= 0 or reward <= 0:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_GEOMETRY)
    expected_r = reward / risk
    if plan.target_type is Vt08CrtH4AmdV2TargetType.CONDITIONED_TWO_R and expected_r != Decimal(2):
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_TARGET)
    evidence_material = {
        "side": side.value,
        "scenario": scenario.value,
        "signal_at": confirmation_at.isoformat(),
        "cisd": format(cisd_level, "f"),
        "protected_swing": format(extreme, "f"),
        "entry": format(plan.entry_price, "f"),
        "stop": format(plan.methodological_stop, "f"),
        "target": format(plan.target_price, "f"),
        "poi_evidence": plan.poi.evidence_ids,
        "execution_evidence": plan.evidence_ids,
    }
    evidence_fingerprint = sha256(
        json.dumps(evidence_material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    try:
        setup = Vt08CrtH4AmdV2Setup(
            side=side,
            scenario=scenario,
            entry_model=plan.entry_model,
            entry_price=plan.entry_price,
            methodological_invalidation=extreme,
            stop_price=plan.methodological_stop,
            target_type=plan.target_type,
            target_price=plan.target_price,
            expected_r=expected_r,
            signal_at=confirmation_at,
            expires_at=plan.valid_until.astimezone(UTC),
            cisd_level=cisd_level,
            protected_swing_extreme=extreme,
            poi=plan.poi,
            evidence_fingerprint=evidence_fingerprint,
            methodology_fingerprint=methodology_fingerprint(),
        )
    except Vt08CrtH4AmdV2ValidationError:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_GEOMETRY)
    return Vt08CrtH4AmdV2Evaluation(
        decision=DemoTradingDecision.SETUP,
        confirmed_opportunity=opportunity,
        abstain_reason=None,
        methodology_fingerprint=methodology_fingerprint(),
        setup=setup,
    )


def evaluate_reversal_expansion_candle2(
    *,
    symbol: str,
    h4_reference: Vt08CrtH4AmdV2Candle,
    h4_candle2_closes_at: datetime,
    observed_m15: tuple[Vt08CrtH4AmdV2Candle, ...],
    context: Vt08CrtH4AmdV2SourceContext,
) -> Vt08CrtH4AmdV2Evaluation:
    """Evaluate the source's shallow-wick Candle-2 reversal-to-expansion case."""

    blocked = _validate_common(
        symbol=symbol,
        h4_closes_at=h4_candle2_closes_at,
        observed_m15=observed_m15,
        context=context,
    )
    if blocked is not None:
        return blocked
    if h4_reference.closed_at - h4_reference.opened_at != timedelta(hours=4):
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_GEOMETRY)
    if context.wick_profile is Vt08CrtH4AmdV2WickProfile.LARGE:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.WAIT_FOR_CANDLE3)
    side = context.bias_side
    assert side is not None
    required_run_level = (
        h4_reference.low if side is DemoTradingSetupSide.LONG else h4_reference.high
    )
    protected = _protected_swing(
        observed_m15,
        side=side,
        required_run_level=required_run_level,
    )
    if protected is None:
        touched = any(
            bar.low < required_run_level
            if side is DemoTradingSetupSide.LONG
            else bar.high > required_run_level
            for bar in observed_m15
        )
        return _abstain(
            Vt08CrtH4AmdV2AbstainReason.NO_CISD_PROTECTED_SWING
            if touched
            else Vt08CrtH4AmdV2AbstainReason.REFERENCE_BOUNDARY_NOT_RUN
        )
    confirmation, cisd_level, extreme = protected
    return _confirmed_opportunity(
        side=side,
        scenario=Vt08CrtH4AmdV2Scenario.REVERSAL_EXPANSION_C2,
        confirmation=confirmation,
        cisd_level=cisd_level,
        extreme=extreme,
        expires_at=h4_candle2_closes_at,
        context=context,
    )


def _candle2_reversal_side(
    reference: Vt08CrtH4AmdV2Candle,
    candle2: Vt08CrtH4AmdV2Candle,
) -> DemoTradingSetupSide | None:
    swept_high = candle2.high > reference.high
    swept_low = candle2.low < reference.low
    if swept_high == swept_low:
        return None
    closes_back_inside = reference.low < candle2.close < reference.high
    if not closes_back_inside:
        return None
    return DemoTradingSetupSide.SHORT if swept_high else DemoTradingSetupSide.LONG


def evaluate_continuation_expansion_candle3(
    *,
    symbol: str,
    h4_reference: Vt08CrtH4AmdV2Candle,
    h4_candle2: Vt08CrtH4AmdV2Candle,
    h4_candle3_closes_at: datetime,
    observed_m15: tuple[Vt08CrtH4AmdV2Candle, ...],
    candle2_wick_profile: Vt08CrtH4AmdV2WickProfile,
    context: Vt08CrtH4AmdV2SourceContext,
) -> Vt08CrtH4AmdV2Evaluation:
    """Evaluate Candle 3 only after a source-classified large Candle-2 reversal."""

    blocked = _validate_common(
        symbol=symbol,
        h4_closes_at=h4_candle3_closes_at,
        observed_m15=observed_m15,
        context=context,
    )
    if blocked is not None:
        return blocked
    if (
        h4_reference.closed_at - h4_reference.opened_at != timedelta(hours=4)
        or h4_candle2.closed_at - h4_candle2.opened_at != timedelta(hours=4)
    ):
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_GEOMETRY)
    if candle2_wick_profile is not Vt08CrtH4AmdV2WickProfile.LARGE:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.CANDLE2_LARGE_RUN_REQUIRED)
    if context.wick_profile is not Vt08CrtH4AmdV2WickProfile.SHALLOW:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.WICK_CLASSIFICATION_REQUIRED)
    side = context.bias_side
    assert side is not None
    reversal_side = _candle2_reversal_side(h4_reference, h4_candle2)
    if reversal_side is not side:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.CANDLE2_REVERSAL_REQUIRED)
    protected = _protected_swing(
        observed_m15,
        side=side,
        required_run_level=None,
    )
    if protected is None:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.NO_CISD_PROTECTED_SWING)
    confirmation, cisd_level, extreme = protected
    return _confirmed_opportunity(
        side=side,
        scenario=Vt08CrtH4AmdV2Scenario.CONTINUATION_EXPANSION_C3,
        confirmation=confirmation,
        cisd_level=cisd_level,
        extreme=extreme,
        expires_at=h4_candle3_closes_at,
        context=context,
    )
