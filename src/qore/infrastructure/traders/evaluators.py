"""Deterministic methodology evaluators for the first five DEMO Traders.

Each evaluator is a pure, frozen, versioned object implementing:

``MARKET EVIDENCE -> EXACT TRADER VERSION/CONFIG/METHODOLOGY -> SETUP / STATE / ABSTAIN``

Every evaluator binds exact trader identity, methodology identity, a config
fingerprint, and an explicit methodology fingerprint. Evaluation is a pure
function of closed-candle evidence and an explicit ``as_of`` instant: no ambient
time, no random identity, no partial-candle leakage, and no future leakage.

Methodology semantics recorded here are the formalized deterministic contracts
for the cohort (see the FAMILY_MODEL). No evaluator carries order/account/
quantity/provider/Risk/Production authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.market_observation import MarketTimeframeCode
from qore.infrastructure.traders.contracts import (
    DemoTradingAbstainReason,
    DemoTradingConfigFingerprint,
    DemoTradingConfigParameter,
    DemoTradingDecision,
    DemoTradingError,
    DemoTradingEvidenceRef,
    DemoTradingMethodologyFingerprint,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingOutput,
    DemoTradingSetupSide,
    DemoTradingSetupSpec,
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
    DemoTradingValidationError,
    compute_trader_config_fingerprint,
    compute_trader_methodology_fingerprint,
    compute_trader_output_fingerprint,
)
from qore.infrastructure.traders.primitives import (
    ClosedCandle,
    DemoTradingPrimitiveValidationError,
    FairValueGap,
    FvgDirection,
    SwingPivotKind,
    closed_candles_as_of,
    detect_amd_context,
    detect_fair_value_gaps,
    detect_swing_pivots,
    false_break_direction,
    session_extrema,
)
from qore.infrastructure.traders.windows import (
    NY_AM_SESSION,
    NinetyMinuteCycle,
    active_silver_bullet_window,
    is_in_window,
    ninety_minute_cycle,
)
from qore.kernel.result import Failure, Result, Success


class DemoTradingEvaluatorError(DemoTradingError):
    """Base error for deterministic methodology evaluation."""

    __slots__ = ()


def _utc(value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise DemoTradingValidationError("instant must be timezone-aware")
    return value.astimezone(UTC)


def _timeframe_mismatch(
    candles: tuple[ClosedCandle, ...],
    *,
    code: MarketTimeframeCode,
) -> bool:
    """Return True if any supplied candle is not exactly the required timeframe."""

    return any(item.timeframe is not code for item in candles)


@dataclass(frozen=True, slots=True)
class DemoTradingInput:
    """Deterministic evaluation input: exact evidence + an explicit as_of."""

    as_of: datetime
    evidence_refs: tuple[DemoTradingEvidenceRef, ...]
    execution_candles: tuple[ClosedCandle, ...]
    context_candles: tuple[ClosedCandle, ...] = ()

    def __post_init__(self) -> None:
        _utc(self.as_of)
        if type(self.evidence_refs) is not tuple or any(
            type(item) is not DemoTradingEvidenceRef for item in self.evidence_refs
        ):
            raise DemoTradingValidationError(
                "input evidence_refs must be a DemoTradingEvidenceRef tuple"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise DemoTradingValidationError("input evidence refs must be unique")
        if type(self.execution_candles) is not tuple or any(
            type(item) is not ClosedCandle for item in self.execution_candles
        ):
            raise DemoTradingValidationError(
                "input execution_candles must be a ClosedCandle tuple"
            )
        if type(self.context_candles) is not tuple or any(
            type(item) is not ClosedCandle for item in self.context_candles
        ):
            raise DemoTradingValidationError(
                "input context_candles must be a ClosedCandle tuple"
            )


def _methodology_identity(
    *,
    methodology_id: str,
    version: str,
    timeframe: str,
    session: str,
    ruleset: str,
) -> tuple[
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingMethodologyFingerprint,
]:
    methodology_id_value = DemoTradingMethodologyId(methodology_id)
    version_value = DemoTradingMethodologyVersion(version)
    fingerprint = compute_trader_methodology_fingerprint(
        methodology_id=methodology_id_value,
        methodology_version=version_value,
        timeframe=timeframe,
        session=session,
        ruleset=ruleset,
    )
    return methodology_id_value, version_value, fingerprint


def _setup_spec(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    invalidation: Decimal,
    take_profit: Decimal,
    reason: str,
) -> DemoTradingSetupSpec:
    return DemoTradingSetupSpec(
        side=side,
        entry_price=entry,
        invalidation_price=invalidation,
        take_profit_price=take_profit,
        entry_reason=reason,
    )


def _risk_multiple(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    invalidation: Decimal,
    multiple: Decimal,
) -> Decimal:
    risk = (entry - invalidation) if side is DemoTradingSetupSide.LONG else (
        invalidation - entry
    )
    if risk <= 0:
        raise DemoTradingValidationError("setup risk must be positive")
    return entry + risk * multiple if side is DemoTradingSetupSide.LONG else entry - risk * multiple


def _build_output(
    *,
    trader_code: str,
    version: str,
    config_fingerprint: DemoTradingConfigFingerprint,
    methodology_id: DemoTradingMethodologyId,
    methodology_version: DemoTradingMethodologyVersion,
    methodology_fingerprint: DemoTradingMethodologyFingerprint,
    evidence_refs: tuple[DemoTradingEvidenceRef, ...],
    timeframe: str,
    session: str,
    decision: DemoTradingDecision,
    side: DemoTradingSetupSide | None,
    setup: DemoTradingSetupSpec | None,
    abstain_reason: DemoTradingAbstainReason | None,
    evaluated_at: datetime,
) -> Result[DemoTradingOutput, DemoTradingError]:
    code = DemoTradingTraderCode(trader_code)
    version_value = DemoTradingTraderVersion(version)
    fingerprint = compute_trader_output_fingerprint(
        trader_code=code,
        version=version_value,
        config_fingerprint=config_fingerprint,
        methodology_id=methodology_id,
        methodology_version=methodology_version,
        methodology_fingerprint=methodology_fingerprint,
        evidence_refs=evidence_refs,
        timeframe=timeframe,
        session=session,
        decision=decision,
        side=side,
        setup=setup,
        abstain_reason=abstain_reason,
        evaluated_at=evaluated_at,
    )
    try:
        return Success(
            DemoTradingOutput(
                trader_code=code,
                version=version_value,
                config_fingerprint=config_fingerprint,
                methodology_id=methodology_id,
                methodology_version=methodology_version,
                methodology_fingerprint=methodology_fingerprint,
                evidence_refs=evidence_refs,
                timeframe=timeframe,
                session=session,
                decision=decision,
                side=side,
                setup=setup,
                abstain_reason=abstain_reason,
                evaluated_at=evaluated_at,
                output_fingerprint=fingerprint,
            )
        )
    except DemoTradingError as error:
        return Failure(error)


def _sweep_fvg_setup(
    candles: tuple[ClosedCandle, ...],
    *,
    strength: int,
    as_of: datetime,
) -> DemoTradingSetupSpec | None:
    """Shared sweep-then-FVG reversal primitive used by VT-01 and VT-31.

    Detect the most recent swing high and low over closed candles, require the
    latest candle to false-break one of them on the pivot's own side, then
    require a Fair Value Gap in the reversal direction. Returns a fully
    validated setup spec, or None. This function never raises: malformed,
    empty, or degenerate-geometry evidence yields None (abstain).
    """

    if not candles:
        return None
    try:
        ordered = closed_candles_as_of(candles, as_of=as_of)
    except DemoTradingPrimitiveValidationError:
        return None
    if len(ordered) < 2 * strength + 2:
        return None
    # Swing pivots are prior structure: detected on all candles except the latest
    # (the latest candle is the one that may false-break a prior level).
    pivots = detect_swing_pivots(ordered[:-1], strength=strength)
    if not pivots:
        return None
    latest = ordered[-1]

    def _fvg_confirms(direction: SwingPivotKind) -> FairValueGap | None:
        gaps = detect_fair_value_gaps(ordered)
        wanted = FvgDirection.BULLISH if direction is SwingPivotKind.LOW else FvgDirection.BEARISH
        for gap in reversed(gaps):
            if gap.direction is wanted:
                return gap
        return None

    for pivot in reversed(pivots):
        direction = false_break_direction(latest, pivot.price, side=pivot.kind)
        if direction is None:
            continue
        gap = _fvg_confirms(direction)
        if gap is None:
            continue
        side = (
            DemoTradingSetupSide.LONG
            if direction is SwingPivotKind.LOW
            else DemoTradingSetupSide.SHORT
        )
        entry = (gap.upper + gap.lower) / Decimal(2)
        invalidation = pivot.price
        try:
            return _setup_spec(
                side=side,
                entry=entry,
                invalidation=invalidation,
                take_profit=_risk_multiple(
                    side=side,
                    entry=entry,
                    invalidation=invalidation,
                    multiple=Decimal("2"),
                ),
                reason=f"liquidity-sweep-{direction.value}-with-fvg-confirmation",
            )
        except DemoTradingError:
            continue
    return None


# ---------------------------------------------------------------------------
# VT-01 NY Precision Core — M5, bounded NY-session liquidity family.
# ---------------------------------------------------------------------------

_VT01_METHODOLOGY_ID = "ny-precision-core"
_VT01_RULESET = (
    "m5-execution;ny-am-session-07:00-11:00;liquidity-sweep-of-swing-level;"
    "fvg-confirmation;reversal-entry-at-fvg-midpoint;invalidation-at-swept-level;"
    "take-profit-2r"
)


@dataclass(frozen=True, slots=True)
class Vt01NyPrecisionCore:
    """VT-01 NY Precision Core deterministic methodology evaluator."""

    version: str = "v1"
    sweep_strength: int = 2

    def __post_init__(self) -> None:
        if type(self.sweep_strength) is not int or self.sweep_strength < 1:
            raise DemoTradingValidationError("sweep_strength must be a positive int")

    @property
    def trader_code(self) -> str:
        return "vt-01"

    @property
    def timeframe(self) -> str:
        return "M5"

    @property
    def session(self) -> str:
        return NY_AM_SESSION.name

    def config_fingerprint(self) -> DemoTradingConfigFingerprint:
        return compute_trader_config_fingerprint(
            schema_version="trader-config-v1",
            parameters=(
                DemoTradingConfigParameter("sweep.strength", self.sweep_strength),
            ),
        )

    def methodology(self) -> tuple[
        DemoTradingMethodologyId,
        DemoTradingMethodologyVersion,
        DemoTradingMethodologyFingerprint,
    ]:
        return _methodology_identity(
            methodology_id=_VT01_METHODOLOGY_ID,
            version=self.version,
            timeframe=self.timeframe,
            session=self.session,
            ruleset=_VT01_RULESET,
        )

    def evaluate(
        self,
        input: DemoTradingInput,
    ) -> Result[DemoTradingOutput, DemoTradingError]:
        if type(input) is not DemoTradingInput:
            return Failure(
                DemoTradingValidationError("VT-01 requires DemoTradingInput")
            )
        methodology_id, methodology_version, methodology_fingerprint = self.methodology()
        config_fingerprint = self.config_fingerprint()
        as_of = _utc(input.as_of)
        if _timeframe_mismatch(input.execution_candles, code=MarketTimeframeCode.M5):
            return Failure(
                DemoTradingValidationError("VT-01 requires M5 execution candles")
            )
        if not is_in_window(as_of, NY_AM_SESSION):
            return _build_output(
                trader_code=self.trader_code,
                version=self.version,
                config_fingerprint=config_fingerprint,
                methodology_id=methodology_id,
                methodology_version=methodology_version,
                methodology_fingerprint=methodology_fingerprint,
                evidence_refs=input.evidence_refs,
                timeframe=self.timeframe,
                session=self.session,
                decision=DemoTradingDecision.ABSTAIN,
                side=None,
                setup=None,
                abstain_reason=DemoTradingAbstainReason.NO_SESSION,
                evaluated_at=as_of,
            )
        spec = _sweep_fvg_setup(
            input.execution_candles,
            strength=self.sweep_strength,
            as_of=as_of,
        )
        if spec is None:
            return _build_output(
                trader_code=self.trader_code,
                version=self.version,
                config_fingerprint=config_fingerprint,
                methodology_id=methodology_id,
                methodology_version=methodology_version,
                methodology_fingerprint=methodology_fingerprint,
                evidence_refs=input.evidence_refs,
                timeframe=self.timeframe,
                session=self.session,
                decision=DemoTradingDecision.ABSTAIN,
                side=None,
                setup=None,
                abstain_reason=DemoTradingAbstainReason.NO_SWEEP,
                evaluated_at=as_of,
            )
        return _build_output(
            trader_code=self.trader_code,
            version=self.version,
            config_fingerprint=config_fingerprint,
            methodology_id=methodology_id,
            methodology_version=methodology_version,
            methodology_fingerprint=methodology_fingerprint,
            evidence_refs=input.evidence_refs,
            timeframe=self.timeframe,
            session=self.session,
            decision=DemoTradingDecision.SETUP,
            side=spec.side,
            setup=spec,
            abstain_reason=None,
            evaluated_at=as_of,
        )


# ---------------------------------------------------------------------------
# VT-08 CRT 4H AMD — M5 execution with closed H4 structural context.
# ---------------------------------------------------------------------------

_VT08_METHODOLOGY_ID = "crt-4h-amd"
_VT08_RULESET = (
    "m5-execution;closed-h4-amd-context;accumulation-manipulation-distribution;"
    "distribution-phase-sets-bias;m5-fvg-in-bias-direction;invalidation-at-"
    "manipulation-extreme;take-profit-at-opposite-h4-range-extreme"
)


@dataclass(frozen=True, slots=True)
class Vt08Crt4hAmd:
    """VT-08 CRT 4H AMD deterministic methodology evaluator."""

    version: str = "v1"
    range_length: int = 4

    def __post_init__(self) -> None:
        if type(self.range_length) is not int or self.range_length < 2:
            raise DemoTradingValidationError("range_length must be an int >= 2")

    @property
    def trader_code(self) -> str:
        return "vt-08"

    @property
    def timeframe(self) -> str:
        return "M5"

    @property
    def session(self) -> str:
        return "h4-structural"

    def config_fingerprint(self) -> DemoTradingConfigFingerprint:
        return compute_trader_config_fingerprint(
            schema_version="trader-config-v1",
            parameters=(
                DemoTradingConfigParameter("amd.range_length", self.range_length),
            ),
        )

    def methodology(self) -> tuple[
        DemoTradingMethodologyId,
        DemoTradingMethodologyVersion,
        DemoTradingMethodologyFingerprint,
    ]:
        return _methodology_identity(
            methodology_id=_VT08_METHODOLOGY_ID,
            version=self.version,
            timeframe=self.timeframe,
            session=self.session,
            ruleset=_VT08_RULESET,
        )

    def evaluate(
        self,
        input: DemoTradingInput,
    ) -> Result[DemoTradingOutput, DemoTradingError]:
        if type(input) is not DemoTradingInput:
            return Failure(
                DemoTradingValidationError("VT-08 requires DemoTradingInput")
            )
        methodology_id, methodology_version, methodology_fingerprint = self.methodology()
        config_fingerprint = self.config_fingerprint()
        as_of = _utc(input.as_of)
        if _timeframe_mismatch(input.execution_candles, code=MarketTimeframeCode.M5):
            return Failure(
                DemoTradingValidationError("VT-08 requires M5 execution candles")
            )
        if _timeframe_mismatch(input.context_candles, code=MarketTimeframeCode.H4):
            return Failure(
                DemoTradingValidationError("VT-08 requires H4 context candles")
            )

        def _abstain(
            reason: DemoTradingAbstainReason,
        ) -> Result[DemoTradingOutput, DemoTradingError]:
            return _build_output(
                trader_code=self.trader_code,
                version=self.version,
                config_fingerprint=config_fingerprint,
                methodology_id=methodology_id,
                methodology_version=methodology_version,
                methodology_fingerprint=methodology_fingerprint,
                evidence_refs=input.evidence_refs,
                timeframe=self.timeframe,
                session=self.session,
                decision=DemoTradingDecision.ABSTAIN,
                side=None,
                setup=None,
                abstain_reason=reason,
                evaluated_at=as_of,
            )

        try:
            h4_candles = closed_candles_as_of(input.context_candles, as_of=as_of)
            if len(h4_candles) < self.range_length + 1:
                return _abstain(DemoTradingAbstainReason.NO_STRUCTURE)
            amd = detect_amd_context(h4_candles, range_length=self.range_length)
            if amd.distribution_direction is None:
                return _abstain(DemoTradingAbstainReason.NO_STRUCTURE)
        except DemoTradingPrimitiveValidationError:
            return _abstain(DemoTradingAbstainReason.NO_STRUCTURE)

        bias = amd.distribution_direction
        side = (
            DemoTradingSetupSide.LONG
            if bias is SwingPivotKind.HIGH
            else DemoTradingSetupSide.SHORT
        )
        try:
            m5_candles = closed_candles_as_of(input.execution_candles, as_of=as_of)
        except DemoTradingPrimitiveValidationError:
            return _abstain(DemoTradingAbstainReason.NO_FVG)
        wanted = (
            FvgDirection.BULLISH if side is DemoTradingSetupSide.LONG else FvgDirection.BEARISH
        )
        gaps = tuple(
            gap
            for gap in detect_fair_value_gaps(m5_candles)
            if gap.direction is wanted
        )
        if not gaps:
            return _abstain(DemoTradingAbstainReason.NO_FVG)
        gap = gaps[-1]
        entry = (gap.upper + gap.lower) / Decimal(2)
        # Invalidation is the manipulation-side extreme: the swept side of the
        # H4 deal range that the distribution is now leaving behind.
        if bias is SwingPivotKind.HIGH:
            invalidation = amd.range_low
            take_profit = amd.range_high
        else:
            invalidation = amd.range_high
            take_profit = amd.range_low
        # Guard against a degenerate range where the R:R is not strict.
        try:
            spec = _setup_spec(
                side=side,
                entry=entry,
                invalidation=invalidation,
                take_profit=take_profit,
                reason=f"amd-distribution-{bias.value}-with-m5-fvg",
            )
        except DemoTradingError:
            return _abstain(DemoTradingAbstainReason.NO_FVG)
        return _build_output(
            trader_code=self.trader_code,
            version=self.version,
            config_fingerprint=config_fingerprint,
            methodology_id=methodology_id,
            methodology_version=methodology_version,
            methodology_fingerprint=methodology_fingerprint,
            evidence_refs=input.evidence_refs,
            timeframe=self.timeframe,
            session=self.session,
            decision=DemoTradingDecision.SETUP,
            side=side,
            setup=spec,
            abstain_reason=None,
            evaluated_at=as_of,
        )


# ---------------------------------------------------------------------------
# VT-09 Turtle Soup — false-break reversal; M15 path required.
# ---------------------------------------------------------------------------

_VT09_METHODOLOGY_ID = "turtle-soup"
_VT09_RULESET = (
    "m15-execution;false-break-of-swing-high-low;reversal-entry-at-false-break-"
    "close;invalidation-at-swing-extreme;take-profit-2r"
)


@dataclass(frozen=True, slots=True)
class Vt09TurtleSoup:
    """VT-09 Turtle Soup false-break reversal evaluator (M15)."""

    version: str = "v1"
    swing_strength: int = 2

    def __post_init__(self) -> None:
        if type(self.swing_strength) is not int or self.swing_strength < 1:
            raise DemoTradingValidationError("swing_strength must be a positive int")

    @property
    def trader_code(self) -> str:
        return "vt-09"

    @property
    def timeframe(self) -> str:
        return "M15"

    @property
    def session(self) -> str:
        return "continuous"

    def config_fingerprint(self) -> DemoTradingConfigFingerprint:
        return compute_trader_config_fingerprint(
            schema_version="trader-config-v1",
            parameters=(
                DemoTradingConfigParameter("swing.strength", self.swing_strength),
            ),
        )

    def methodology(self) -> tuple[
        DemoTradingMethodologyId,
        DemoTradingMethodologyVersion,
        DemoTradingMethodologyFingerprint,
    ]:
        return _methodology_identity(
            methodology_id=_VT09_METHODOLOGY_ID,
            version=self.version,
            timeframe=self.timeframe,
            session=self.session,
            ruleset=_VT09_RULESET,
        )

    def evaluate(
        self,
        input: DemoTradingInput,
    ) -> Result[DemoTradingOutput, DemoTradingError]:
        if type(input) is not DemoTradingInput:
            return Failure(
                DemoTradingValidationError("VT-09 requires DemoTradingInput")
            )
        methodology_id, methodology_version, methodology_fingerprint = self.methodology()
        config_fingerprint = self.config_fingerprint()
        as_of = _utc(input.as_of)
        if _timeframe_mismatch(input.execution_candles, code=MarketTimeframeCode.M15):
            return Failure(
                DemoTradingValidationError("VT-09 requires M15 execution candles")
            )
        ordered: tuple[ClosedCandle, ...]
        if not input.execution_candles:
            ordered = ()
        else:
            try:
                ordered = closed_candles_as_of(input.execution_candles, as_of=as_of)
            except DemoTradingPrimitiveValidationError:
                ordered = ()
        if len(ordered) < 2 * self.swing_strength + 2:
            return _build_output(
                trader_code=self.trader_code,
                version=self.version,
                config_fingerprint=config_fingerprint,
                methodology_id=methodology_id,
                methodology_version=methodology_version,
                methodology_fingerprint=methodology_fingerprint,
                evidence_refs=input.evidence_refs,
                timeframe=self.timeframe,
                session=self.session,
                decision=DemoTradingDecision.ABSTAIN,
                side=None,
                setup=None,
                abstain_reason=DemoTradingAbstainReason.INSUFFICIENT_EVIDENCE,
                evaluated_at=as_of,
            )
        pivots = detect_swing_pivots(ordered[:-1], strength=self.swing_strength)
        if not pivots:
            return _build_output(
                trader_code=self.trader_code,
                version=self.version,
                config_fingerprint=config_fingerprint,
                methodology_id=methodology_id,
                methodology_version=methodology_version,
                methodology_fingerprint=methodology_fingerprint,
                evidence_refs=input.evidence_refs,
                timeframe=self.timeframe,
                session=self.session,
                decision=DemoTradingDecision.ABSTAIN,
                side=None,
                setup=None,
                abstain_reason=DemoTradingAbstainReason.NO_FALSE_BREAK,
                evaluated_at=as_of,
            )
        latest = ordered[-1]
        for pivot in reversed(pivots):
            direction = false_break_direction(latest, pivot.price, side=pivot.kind)
            if direction is None:
                continue
            side = (
                DemoTradingSetupSide.LONG
                if direction is SwingPivotKind.LOW
                else DemoTradingSetupSide.SHORT
            )
            entry = latest.close
            invalidation = pivot.price
            try:
                spec = _setup_spec(
                    side=side,
                    entry=entry,
                    invalidation=invalidation,
                    take_profit=_risk_multiple(
                        side=side,
                        entry=entry,
                        invalidation=invalidation,
                        multiple=Decimal("2"),
                    ),
                    reason=f"turtle-soup-false-break-{direction.value}",
                )
            except DemoTradingError:
                continue
            return _build_output(
                trader_code=self.trader_code,
                version=self.version,
                config_fingerprint=config_fingerprint,
                methodology_id=methodology_id,
                methodology_version=methodology_version,
                methodology_fingerprint=methodology_fingerprint,
                evidence_refs=input.evidence_refs,
                timeframe=self.timeframe,
                session=self.session,
                decision=DemoTradingDecision.SETUP,
                side=side,
                setup=spec,
                abstain_reason=None,
                evaluated_at=as_of,
            )
        return _build_output(
            trader_code=self.trader_code,
            version=self.version,
            config_fingerprint=config_fingerprint,
            methodology_id=methodology_id,
            methodology_version=methodology_version,
            methodology_fingerprint=methodology_fingerprint,
            evidence_refs=input.evidence_refs,
            timeframe=self.timeframe,
            session=self.session,
            decision=DemoTradingDecision.ABSTAIN,
            side=None,
            setup=None,
            abstain_reason=DemoTradingAbstainReason.NO_FALSE_BREAK,
            evaluated_at=as_of,
        )


# ---------------------------------------------------------------------------
# VT-17 QT Scalper — M5; deterministic 90-minute cycle semantics.
# ---------------------------------------------------------------------------

_VT17_METHODOLOGY_ID = "qt-scalper"
_VT17_RULESET = (
    "m5-execution;epoch-aligned-90-minute-cycle;ny-am-session;cycle-anchored-"
    "liquidity-sweep;reversal-entry-at-false-break-close;invalidation-at-cycle-"
    "extreme;take-profit-2r"
)


@dataclass(frozen=True, slots=True)
class Vt17QtScalper:
    """VT-17 QT Scalper deterministic 90-minute-cycle evaluator."""

    version: str = "v1"

    @property
    def trader_code(self) -> str:
        return "vt-17"

    @property
    def timeframe(self) -> str:
        return "M5"

    @property
    def session(self) -> str:
        return NY_AM_SESSION.name

    def config_fingerprint(self) -> DemoTradingConfigFingerprint:
        return compute_trader_config_fingerprint(
            schema_version="trader-config-v1",
            parameters=(
                DemoTradingConfigParameter("cycle.minutes", 90),
            ),
        )

    def methodology(self) -> tuple[
        DemoTradingMethodologyId,
        DemoTradingMethodologyVersion,
        DemoTradingMethodologyFingerprint,
    ]:
        return _methodology_identity(
            methodology_id=_VT17_METHODOLOGY_ID,
            version=self.version,
            timeframe=self.timeframe,
            session=self.session,
            ruleset=_VT17_RULESET,
        )

    def _cycle_candles(
        self,
        candles: tuple[ClosedCandle, ...],
        cycle: NinetyMinuteCycle,
        *,
        as_of: datetime,
    ) -> tuple[ClosedCandle, ...]:
        if not candles:
            return ()
        try:
            ordered = closed_candles_as_of(candles, as_of=as_of)
        except DemoTradingPrimitiveValidationError:
            # A gap-bearing, overlapping, or otherwise malformed execution
            # sequence is not valid closed-candle evidence for the cycle range;
            # fail closed to an empty cycle (abstain) like the rest of the
            # cohort instead of leaking an uncaught primitive error.
            return ()
        return tuple(
            item
            for item in ordered
            if item.opened_at >= cycle.opened_at and item.closed_at <= as_of
        )

    def evaluate(
        self,
        input: DemoTradingInput,
    ) -> Result[DemoTradingOutput, DemoTradingError]:
        if type(input) is not DemoTradingInput:
            return Failure(
                DemoTradingValidationError("VT-17 requires DemoTradingInput")
            )
        methodology_id, methodology_version, methodology_fingerprint = self.methodology()
        config_fingerprint = self.config_fingerprint()
        as_of = _utc(input.as_of)
        if _timeframe_mismatch(input.execution_candles, code=MarketTimeframeCode.M5):
            return Failure(
                DemoTradingValidationError("VT-17 requires M5 execution candles")
            )
        if not is_in_window(as_of, NY_AM_SESSION):
            return _build_output(
                trader_code=self.trader_code,
                version=self.version,
                config_fingerprint=config_fingerprint,
                methodology_id=methodology_id,
                methodology_version=methodology_version,
                methodology_fingerprint=methodology_fingerprint,
                evidence_refs=input.evidence_refs,
                timeframe=self.timeframe,
                session=self.session,
                decision=DemoTradingDecision.ABSTAIN,
                side=None,
                setup=None,
                abstain_reason=DemoTradingAbstainReason.NO_SESSION,
                evaluated_at=as_of,
            )
        cycle = ninety_minute_cycle(as_of)
        cycle_candles = self._cycle_candles(input.execution_candles, cycle, as_of=as_of)
        if len(cycle_candles) < 3:
            return _build_output(
                trader_code=self.trader_code,
                version=self.version,
                config_fingerprint=config_fingerprint,
                methodology_id=methodology_id,
                methodology_version=methodology_version,
                methodology_fingerprint=methodology_fingerprint,
                evidence_refs=input.evidence_refs,
                timeframe=self.timeframe,
                session=self.session,
                decision=DemoTradingDecision.ABSTAIN,
                side=None,
                setup=None,
                abstain_reason=DemoTradingAbstainReason.NO_CYCLE,
                evaluated_at=as_of,
            )
        # Cycle extrema are the running range established by all but the latest
        # candle; the latest candle is the one that may sweep the range.
        extrema = session_extrema(cycle_candles[:-1])
        latest = cycle_candles[-1]
        direction = (
            false_break_direction(latest, extrema.high, side=SwingPivotKind.HIGH)
            or false_break_direction(latest, extrema.low, side=SwingPivotKind.LOW)
        )
        if direction is None:
            return _build_output(
                trader_code=self.trader_code,
                version=self.version,
                config_fingerprint=config_fingerprint,
                methodology_id=methodology_id,
                methodology_version=methodology_version,
                methodology_fingerprint=methodology_fingerprint,
                evidence_refs=input.evidence_refs,
                timeframe=self.timeframe,
                session=self.session,
                decision=DemoTradingDecision.ABSTAIN,
                side=None,
                setup=None,
                abstain_reason=DemoTradingAbstainReason.NO_SWEEP,
                evaluated_at=as_of,
            )
        side = (
            DemoTradingSetupSide.LONG
            if direction is SwingPivotKind.LOW
            else DemoTradingSetupSide.SHORT
        )
        entry = latest.close
        invalidation = extrema.high if direction is SwingPivotKind.HIGH else extrema.low
        try:
            spec = _setup_spec(
                side=side,
                entry=entry,
                invalidation=invalidation,
                take_profit=_risk_multiple(
                    side=side,
                    entry=entry,
                    invalidation=invalidation,
                    multiple=Decimal("2"),
                ),
                reason=f"qt-scalper-cycle-{cycle.index}-{direction.value}-sweep",
            )
        except DemoTradingError:
            return _build_output(
                trader_code=self.trader_code,
                version=self.version,
                config_fingerprint=config_fingerprint,
                methodology_id=methodology_id,
                methodology_version=methodology_version,
                methodology_fingerprint=methodology_fingerprint,
                evidence_refs=input.evidence_refs,
                timeframe=self.timeframe,
                session=self.session,
                decision=DemoTradingDecision.ABSTAIN,
                side=None,
                setup=None,
                abstain_reason=DemoTradingAbstainReason.NO_SWEEP,
                evaluated_at=as_of,
            )
        return _build_output(
            trader_code=self.trader_code,
            version=self.version,
            config_fingerprint=config_fingerprint,
            methodology_id=methodology_id,
            methodology_version=methodology_version,
            methodology_fingerprint=methodology_fingerprint,
            evidence_refs=input.evidence_refs,
            timeframe=self.timeframe,
            session=self.session,
            decision=DemoTradingDecision.SETUP,
            side=side,
            setup=spec,
            abstain_reason=None,
            evaluated_at=as_of,
        )


# ---------------------------------------------------------------------------
# VT-31 Silver Bullet — M5/M1, fixed NY windows.
# ---------------------------------------------------------------------------

_VT31_METHODOLOGY_ID = "silver-bullet"
_VT31_RULESET = (
    "m5-m1-execution;fixed-ny-windows-10:00-11:00-and-14:00-15:00;liquidity-sweep-"
    "of-swing-level;fvg-confirmation;reversal-entry-at-fvg-midpoint;invalidation-"
    "at-swept-level;take-profit-2r"
)


@dataclass(frozen=True, slots=True)
class Vt31SilverBullet:
    """VT-31 Silver Bullet fixed-NY-window sweep/FVG evaluator."""

    version: str = "v1"
    sweep_strength: int = 2

    def __post_init__(self) -> None:
        if type(self.sweep_strength) is not int or self.sweep_strength < 1:
            raise DemoTradingValidationError("sweep_strength must be a positive int")

    @property
    def trader_code(self) -> str:
        return "vt-31"

    @property
    def timeframe(self) -> str:
        return "M5"

    @property
    def session(self) -> str:
        return "ny-silver-bullet"

    def config_fingerprint(self) -> DemoTradingConfigFingerprint:
        return compute_trader_config_fingerprint(
            schema_version="trader-config-v1",
            parameters=(
                DemoTradingConfigParameter("sweep.strength", self.sweep_strength),
            ),
        )

    def methodology(self) -> tuple[
        DemoTradingMethodologyId,
        DemoTradingMethodologyVersion,
        DemoTradingMethodologyFingerprint,
    ]:
        return _methodology_identity(
            methodology_id=_VT31_METHODOLOGY_ID,
            version=self.version,
            timeframe=self.timeframe,
            session=self.session,
            ruleset=_VT31_RULESET,
        )

    def evaluate(
        self,
        input: DemoTradingInput,
    ) -> Result[DemoTradingOutput, DemoTradingError]:
        if type(input) is not DemoTradingInput:
            return Failure(
                DemoTradingValidationError("VT-31 requires DemoTradingInput")
            )
        methodology_id, methodology_version, methodology_fingerprint = self.methodology()
        config_fingerprint = self.config_fingerprint()
        as_of = _utc(input.as_of)
        if _timeframe_mismatch(input.execution_candles, code=MarketTimeframeCode.M5):
            return Failure(
                DemoTradingValidationError("VT-31 requires M5 execution candles")
            )
        window = active_silver_bullet_window(as_of)
        if window is None:
            return _build_output(
                trader_code=self.trader_code,
                version=self.version,
                config_fingerprint=config_fingerprint,
                methodology_id=methodology_id,
                methodology_version=methodology_version,
                methodology_fingerprint=methodology_fingerprint,
                evidence_refs=input.evidence_refs,
                timeframe=self.timeframe,
                session=self.session,
                decision=DemoTradingDecision.ABSTAIN,
                side=None,
                setup=None,
                abstain_reason=DemoTradingAbstainReason.WINDOW_CLOSED,
                evaluated_at=as_of,
            )
        spec = _sweep_fvg_setup(
            input.execution_candles,
            strength=self.sweep_strength,
            as_of=as_of,
        )
        if spec is None:
            return _build_output(
                trader_code=self.trader_code,
                version=self.version,
                config_fingerprint=config_fingerprint,
                methodology_id=methodology_id,
                methodology_version=methodology_version,
                methodology_fingerprint=methodology_fingerprint,
                evidence_refs=input.evidence_refs,
                timeframe=self.timeframe,
                session=self.session,
                decision=DemoTradingDecision.ABSTAIN,
                side=None,
                setup=None,
                abstain_reason=DemoTradingAbstainReason.NO_SWEEP,
                evaluated_at=as_of,
            )
        return _build_output(
            trader_code=self.trader_code,
            version=self.version,
            config_fingerprint=config_fingerprint,
            methodology_id=methodology_id,
            methodology_version=methodology_version,
            methodology_fingerprint=methodology_fingerprint,
            evidence_refs=input.evidence_refs,
            timeframe=self.timeframe,
            session=self.session,
            decision=DemoTradingDecision.SETUP,
            side=spec.side,
            setup=spec,
            abstain_reason=None,
            evaluated_at=as_of,
        )


# ---------------------------------------------------------------------------
# Cohort catalog.
# ---------------------------------------------------------------------------

def cohort_evaluators() -> tuple[
    Vt01NyPrecisionCore | Vt08Crt4hAmd | Vt09TurtleSoup | Vt17QtScalper | Vt31SilverBullet,
    ...,
]:
    """Return the five first-cohort deterministic methodology evaluators."""

    return (
        Vt01NyPrecisionCore(),
        Vt08Crt4hAmd(),
        Vt09TurtleSoup(),
        Vt17QtScalper(),
        Vt31SilverBullet(),
    )
