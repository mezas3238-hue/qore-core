"""Lane-1 adversarial/normal tests for shared Trader architecture contracts.

Covers the exact runtime-type/identity/config/methodology/state contracts, the
timeframe/aggregation primitives, and the DST-aware window/90-minute-cycle
primitives. Deliberately includes reflective corruption of frozen value objects
and exact wrong-type inputs, so every shared contract is exercised at a trust
boundary rather than only at construction time.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast

import pytest

from qore.infrastructure.market_observation import MarketTimeframe, MarketTimeframeCode
from qore.infrastructure.traders.contracts import (
    DemoTradingAbstainReason,
    DemoTradingConfigFingerprint,
    DemoTradingConfigParameter,
    DemoTradingDecision,
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
    aggregate_closed_candles,
    timeframe_seconds,
    validate_closed_candle_sequence,
)
from qore.infrastructure.traders.windows import (
    NY_AM_SESSION,
    DemoTradingWindowValidationError,
    NinetyMinuteCycle,
    is_in_window,
    ninety_minute_cycle,
)

_BASE = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)

Bar = tuple[str, str, str, str]


def _candle(
    code: MarketTimeframeCode,
    opened_at: datetime,
    o: str,
    h: str,
    lo: str,
    c: str,
) -> ClosedCandle:
    return ClosedCandle(
        timeframe=code,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(seconds=timeframe_seconds(code)),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(lo),
        close=Decimal(c),
    )


def _seq(
    code: MarketTimeframeCode,
    start: datetime,
    bars: tuple[Bar, ...],
) -> tuple[ClosedCandle, ...]:
    seconds = timeframe_seconds(code)
    return tuple(
        _candle(code, start + timedelta(seconds=i * seconds), o, h, lo, c)
        for i, (o, h, lo, c) in enumerate(bars)
    )


def _m1(start: datetime, bars: tuple[Bar, ...]) -> tuple[ClosedCandle, ...]:
    return _seq(MarketTimeframeCode.M1, start, bars)


def _m5(start: datetime, bars: tuple[Bar, ...]) -> tuple[ClosedCandle, ...]:
    return _seq(MarketTimeframeCode.M5, start, bars)


def _m15(start: datetime, bars: tuple[Bar, ...]) -> tuple[ClosedCandle, ...]:
    return _seq(MarketTimeframeCode.M15, start, bars)


def _params(
    *items: tuple[str, str | bool | int | Decimal],
) -> tuple[DemoTradingConfigParameter, ...]:
    return tuple(DemoTradingConfigParameter(name, value) for name, value in items)


def _config_fingerprint(
    *,
    schema_version: str = "trader-config-v1",
    parameters: tuple[DemoTradingConfigParameter, ...],
) -> DemoTradingConfigFingerprint:
    return compute_trader_config_fingerprint(
        schema_version=schema_version,
        parameters=parameters,
    )


def _methodology_fingerprint(
    *,
    methodology_id: str = "ny-precision-core",
    version: str = "v1",
    timeframe: str = "M5",
    session: str = "ny-am-session",
    ruleset: str = "rule",
) -> DemoTradingMethodologyFingerprint:
    return compute_trader_methodology_fingerprint(
        methodology_id=DemoTradingMethodologyId(methodology_id),
        methodology_version=DemoTradingMethodologyVersion(version),
        timeframe=timeframe,
        session=session,
        ruleset=ruleset,
    )


def _output(
    *,
    decision: DemoTradingDecision,
    evidence_refs: tuple[DemoTradingEvidenceRef, ...],
    evaluated_at: datetime = _BASE,
) -> DemoTradingOutput:
    methodology_id = DemoTradingMethodologyId("ny-precision-core")
    methodology_version = DemoTradingMethodologyVersion("v1")
    methodology_fingerprint = compute_trader_methodology_fingerprint(
        methodology_id=methodology_id,
        methodology_version=methodology_version,
        timeframe="M5",
        session="ny-am-session",
        ruleset="rule",
    )
    config_fingerprint = compute_trader_config_fingerprint(
        schema_version="trader-config-v1",
        parameters=(DemoTradingConfigParameter("sweep.strength", 2),),
    )
    side: DemoTradingSetupSide | None = None
    setup: DemoTradingSetupSpec | None = None
    abstain_reason: DemoTradingAbstainReason | None = None
    if decision is DemoTradingDecision.SETUP:
        side = DemoTradingSetupSide.LONG
        setup = DemoTradingSetupSpec(
            side=side,
            entry_price=Decimal("1.1000"),
            invalidation_price=Decimal("1.0950"),
            take_profit_price=Decimal("1.1100"),
            entry_reason="fvg",
        )
    else:
        abstain_reason = DemoTradingAbstainReason.NO_SESSION
    output_fingerprint = compute_trader_output_fingerprint(
        trader_code=DemoTradingTraderCode("vt-01"),
        version=DemoTradingTraderVersion("v1"),
        config_fingerprint=config_fingerprint,
        methodology_id=methodology_id,
        methodology_version=methodology_version,
        methodology_fingerprint=methodology_fingerprint,
        evidence_refs=evidence_refs,
        timeframe="M5",
        session="ny-am-session",
        decision=decision,
        side=side,
        setup=setup,
        abstain_reason=abstain_reason,
        evaluated_at=evaluated_at,
    )
    return DemoTradingOutput(
        trader_code=DemoTradingTraderCode("vt-01"),
        version=DemoTradingTraderVersion("v1"),
        config_fingerprint=config_fingerprint,
        methodology_id=methodology_id,
        methodology_version=methodology_version,
        methodology_fingerprint=methodology_fingerprint,
        evidence_refs=evidence_refs,
        timeframe="M5",
        session="ny-am-session",
        decision=decision,
        side=side,
        setup=setup,
        abstain_reason=abstain_reason,
        evaluated_at=evaluated_at,
        output_fingerprint=output_fingerprint,
    )


# ---------------------------------------------------------------------------
# Config fingerprint determinism / order-insensitivity / identity sensitivity.
# ---------------------------------------------------------------------------


def test_config_fingerprint_is_order_insensitive_and_deterministic() -> None:
    a = _config_fingerprint(
        parameters=_params(("a", 1), ("b", Decimal("2.5"))),
    )
    b = _config_fingerprint(
        parameters=_params(("b", Decimal("2.50")), ("a", 1)),
    )
    assert a == b


def test_config_fingerprint_changes_on_parameter_value() -> None:
    assert _config_fingerprint(
        parameters=_params(("sweep.strength", 2)),
    ) != _config_fingerprint(
        parameters=_params(("sweep.strength", 3)),
    )


def test_config_fingerprint_changes_on_schema_version() -> None:
    parameters = _params(("sweep.strength", 2))
    assert _config_fingerprint(
        schema_version="trader-config-v1", parameters=parameters
    ) != _config_fingerprint(
        schema_version="trader-config-v2", parameters=parameters
    )


def test_config_fingerprint_changes_on_parameter_name() -> None:
    assert _config_fingerprint(
        parameters=_params(("a", 1)),
    ) != _config_fingerprint(
        parameters=_params(("b", 1)),
    )


# ---------------------------------------------------------------------------
# Methodology fingerprint sensitivity to every identity/semantic field.
# ---------------------------------------------------------------------------


def test_methodology_fingerprint_changes_when_any_field_changes() -> None:
    base = _methodology_fingerprint()
    assert _methodology_fingerprint(methodology_id="turtle-soup") != base
    assert _methodology_fingerprint(version="v2") != base
    assert _methodology_fingerprint(timeframe="M15") != base
    assert _methodology_fingerprint(session="continuous") != base
    assert _methodology_fingerprint(ruleset="other-ruleset") != base


# ---------------------------------------------------------------------------
# Evidence-ref canonicalization and output logical identity.
# ---------------------------------------------------------------------------


def test_output_evidence_refs_duplicate_rejected() -> None:
    ref = DemoTradingEvidenceRef("qore:demo:ev:1")
    with pytest.raises(DemoTradingValidationError):
        _output(decision=DemoTradingDecision.SETUP, evidence_refs=(ref, ref))


def test_output_evidence_refs_sorted_order_gives_identical_fingerprint() -> None:
    first = DemoTradingEvidenceRef("qore:demo:ev:1")
    second = DemoTradingEvidenceRef("qore:demo:ev:2")
    a = _output(decision=DemoTradingDecision.SETUP, evidence_refs=(second, first))
    b = _output(decision=DemoTradingDecision.SETUP, evidence_refs=(first, second))
    assert a.output_fingerprint == b.output_fingerprint
    assert a.evidence_refs == (first, second)
    assert b.evidence_refs == (first, second)


def test_output_fingerprint_stable_under_reconstruction() -> None:
    evidence = (DemoTradingEvidenceRef("qore:demo:ev:1"),)
    first = _output(decision=DemoTradingDecision.SETUP, evidence_refs=evidence)
    second = _output(decision=DemoTradingDecision.SETUP, evidence_refs=evidence)
    assert first.output_fingerprint == second.output_fingerprint
    assert first.logical_values() == second.logical_values()


def test_same_identity_and_evidence_does_not_mint_new_logical_identity() -> None:
    evidence = (DemoTradingEvidenceRef("qore:demo:ev:1"),)
    a = _output(decision=DemoTradingDecision.SETUP, evidence_refs=evidence)
    b = _output(decision=DemoTradingDecision.SETUP, evidence_refs=evidence)
    assert a.output_fingerprint.value == b.output_fingerprint.value
    assert a.logical_values() == b.logical_values()


def test_output_fingerprint_changes_with_evidence() -> None:
    a = _output(
        decision=DemoTradingDecision.SETUP,
        evidence_refs=(DemoTradingEvidenceRef("qore:demo:ev:1"),),
    )
    b = _output(
        decision=DemoTradingDecision.SETUP,
        evidence_refs=(DemoTradingEvidenceRef("qore:demo:ev:2"),),
    )
    assert a.output_fingerprint != b.output_fingerprint


# ---------------------------------------------------------------------------
# Reflective corruption of frozen contracts must fail closed on revalidation.
# ---------------------------------------------------------------------------


def test_reflective_corruption_of_setup_side_fails_closed() -> None:
    corrupted = object.__new__(DemoTradingSetupSpec)
    object.__setattr__(corrupted, "side", "long")  # raw str, not the StrEnum
    object.__setattr__(corrupted, "entry_price", Decimal("1.10"))
    object.__setattr__(corrupted, "invalidation_price", Decimal("1.09"))
    object.__setattr__(corrupted, "take_profit_price", Decimal("1.12"))
    object.__setattr__(corrupted, "entry_reason", "fvg")
    with pytest.raises(DemoTradingValidationError):
        corrupted.__post_init__()


def test_reflective_corruption_of_candle_timeframe_fails_closed() -> None:
    corrupted = object.__new__(ClosedCandle)
    object.__setattr__(corrupted, "timeframe", "M5")  # raw str, not the StrEnum
    object.__setattr__(corrupted, "opened_at", _BASE)
    object.__setattr__(corrupted, "closed_at", _BASE + timedelta(minutes=5))
    object.__setattr__(corrupted, "open", Decimal("1.0"))
    object.__setattr__(corrupted, "high", Decimal("1.1"))
    object.__setattr__(corrupted, "low", Decimal("0.9"))
    object.__setattr__(corrupted, "close", Decimal("1.05"))
    with pytest.raises(DemoTradingPrimitiveValidationError):
        corrupted.__post_init__()


def test_reflective_corruption_of_built_output_decision_fails_closed() -> None:
    output = _output(
        decision=DemoTradingDecision.SETUP,
        evidence_refs=(DemoTradingEvidenceRef("qore:demo:ev:1"),),
    )
    object.__setattr__(output, "decision", "setup")  # raw str, not the StrEnum
    with pytest.raises(DemoTradingValidationError):
        output.__post_init__()


# ---------------------------------------------------------------------------
# ClosedCandle exact-type / interval / price rejection.
# ---------------------------------------------------------------------------


def test_closed_candle_rejects_partial_interval() -> None:
    with pytest.raises(DemoTradingPrimitiveValidationError):
        ClosedCandle(
            timeframe=MarketTimeframeCode.M5,
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=4),
            open=Decimal("1.0"),
            high=Decimal("1.1"),
            low=Decimal("0.9"),
            close=Decimal("1.05"),
        )


def test_closed_candle_rejects_bool_timeframe_code() -> None:
    with pytest.raises(DemoTradingPrimitiveValidationError):
        ClosedCandle(
            timeframe=cast(MarketTimeframeCode, True),
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=5),
            open=Decimal("1.0"),
            high=Decimal("1.1"),
            low=Decimal("0.9"),
            close=Decimal("1.05"),
        )


def test_closed_candle_rejects_timeframe_wrapper() -> None:
    wrapper = MarketTimeframe(MarketTimeframeCode.M5)
    with pytest.raises(DemoTradingPrimitiveValidationError):
        ClosedCandle(
            timeframe=cast(MarketTimeframeCode, wrapper),
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=5),
            open=Decimal("1.0"),
            high=Decimal("1.1"),
            low=Decimal("0.9"),
            close=Decimal("1.05"),
        )


@pytest.mark.parametrize("bad_price", [1.5, "1.0", 1])
def test_closed_candle_rejects_non_decimal_prices(bad_price: object) -> None:
    with pytest.raises(DemoTradingPrimitiveValidationError):
        ClosedCandle(
            timeframe=MarketTimeframeCode.M5,
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=5),
            open=cast(Decimal, bad_price),
            high=Decimal("1.1"),
            low=Decimal("0.9"),
            close=Decimal("1.05"),
        )


def test_closed_candle_sequence_gap_rejected() -> None:
    first = _candle(MarketTimeframeCode.M1, _BASE, "1.0", "1.1", "0.9", "1.0")
    gapped = _candle(
        MarketTimeframeCode.M1,
        _BASE + timedelta(minutes=2),
        "1.0",
        "1.1",
        "0.9",
        "1.0",
    )
    with pytest.raises(DemoTradingPrimitiveValidationError):
        validate_closed_candle_sequence((first, gapped))


# ---------------------------------------------------------------------------
# Timeframe aggregation exactness and fail-closed boundaries.
# ---------------------------------------------------------------------------


def test_aggregation_m1_to_m5_exact_ohlc() -> None:
    m1 = _m1(
        _BASE,
        (
            ("1.000", "1.100", "0.900", "1.050"),
            ("1.050", "1.200", "1.000", "1.150"),
            ("1.150", "1.300", "1.100", "1.250"),
            ("1.250", "1.280", "1.150", "1.200"),
            ("1.200", "1.350", "1.180", "1.320"),
        ),
    )
    m5 = aggregate_closed_candles(m1, target=MarketTimeframeCode.M5)
    assert len(m5) == 1
    agg = m5[0]
    assert agg.open == Decimal("1.000")
    assert agg.close == Decimal("1.320")
    assert agg.high == Decimal("1.350")
    assert agg.low == Decimal("0.900")
    assert agg.opened_at == _BASE
    assert agg.closed_at == _BASE + timedelta(minutes=5)


def test_aggregation_m5_to_m15_exact_ohlc() -> None:
    m5 = _m5(
        _BASE,
        (
            ("1.00", "1.10", "0.90", "1.05"),
            ("1.05", "1.20", "1.00", "1.15"),
            ("1.15", "1.25", "1.05", "1.18"),
        ),
    )
    m15 = aggregate_closed_candles(m5, target=MarketTimeframeCode.M15)
    assert len(m15) == 1
    agg = m15[0]
    assert agg.open == Decimal("1.00")
    assert agg.close == Decimal("1.18")
    assert agg.high == Decimal("1.25")
    assert agg.low == Decimal("0.90")
    assert agg.opened_at == _BASE
    assert agg.closed_at == _BASE + timedelta(minutes=15)


def test_aggregation_m15_to_h4_exact_ohlc() -> None:
    bars: list[Bar] = []
    for i in range(16):
        base_price = Decimal("1.0000") + Decimal(i) * Decimal("0.0010")
        bars.append(
            (
                str(base_price),
                str(base_price + Decimal("0.0020")),
                str(base_price - Decimal("0.0010")),
                str(base_price + Decimal("0.0005")),
            )
        )
    m15 = _m15(_BASE, tuple(bars))
    h4 = aggregate_closed_candles(m15, target=MarketTimeframeCode.H4)
    assert len(h4) == 1
    agg = h4[0]
    assert agg.open == Decimal("1.0000")
    assert agg.close == Decimal("1.0155")
    assert agg.high == Decimal("1.0170")
    assert agg.low == Decimal("0.9990")
    assert agg.opened_at == _BASE
    assert agg.closed_at == _BASE + timedelta(hours=4)


def test_aggregation_drops_trailing_partial_block() -> None:
    # 7 M1 candles = 1 complete M5 block (5 candles) + 2 trailing -> dropped.
    m1 = _m1(
        _BASE,
        tuple(
            (f"1.{index:03d}", "1.10", "0.90", "1.05") for index in range(7)
        ),
    )
    m5 = aggregate_closed_candles(m1, target=MarketTimeframeCode.M5)
    assert len(m5) == 1
    assert m5[0].closed_at == _BASE + timedelta(minutes=5)


def test_aggregation_rejects_gap_in_sequence() -> None:
    first = _candle(MarketTimeframeCode.M1, _BASE, "1.0", "1.1", "0.9", "1.0")
    gapped = _candle(
        MarketTimeframeCode.M1,
        _BASE + timedelta(minutes=2),
        "1.0",
        "1.1",
        "0.9",
        "1.0",
    )
    with pytest.raises(DemoTradingPrimitiveValidationError):
        aggregate_closed_candles((first, gapped), target=MarketTimeframeCode.M5)


@pytest.mark.parametrize(
    "target",
    [MarketTimeframeCode.M5, MarketTimeframeCode.M1],
)
def test_aggregation_rejects_equal_or_lower_target(target: MarketTimeframeCode) -> None:
    m5 = _m5(
        _BASE,
        (
            ("1.0", "1.1", "0.9", "1.05"),
            ("1.05", "1.2", "1.0", "1.15"),
        ),
    )
    with pytest.raises(DemoTradingPrimitiveValidationError):
        aggregate_closed_candles(m5, target=target)


# ---------------------------------------------------------------------------
# timeframe_seconds cohort/exact-type gate.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (MarketTimeframeCode.M1, 60),
        (MarketTimeframeCode.M5, 300),
        (MarketTimeframeCode.M15, 900),
        (MarketTimeframeCode.H4, 14400),
    ],
)
def test_timeframe_seconds_cohort_codes(code: MarketTimeframeCode, expected: int) -> None:
    assert timeframe_seconds(code) == expected


@pytest.mark.parametrize(
    "code",
    [MarketTimeframeCode.D1, MarketTimeframeCode.W1, MarketTimeframeCode.MN1],
)
def test_timeframe_seconds_rejects_non_cohort_codes(code: MarketTimeframeCode) -> None:
    with pytest.raises(DemoTradingPrimitiveValidationError):
        timeframe_seconds(code)


@pytest.mark.parametrize("bad", ["M5", 5, True, 300.0])
def test_timeframe_seconds_rejects_non_market_timeframe_code(bad: object) -> None:
    with pytest.raises(DemoTradingPrimitiveValidationError):
        timeframe_seconds(cast(MarketTimeframeCode, bad))


# ---------------------------------------------------------------------------
# Windows / 90-minute cycle primitives.
# ---------------------------------------------------------------------------


def test_ny_am_session_half_open_membership() -> None:
    # 2026-01-06 12:00 UTC == 07:00 America/New_York (EST, UTC-5).
    inside = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
    before = datetime(2026, 1, 6, 11, 59, tzinfo=UTC)
    after = datetime(2026, 1, 6, 16, 0, tzinfo=UTC)
    assert is_in_window(inside, NY_AM_SESSION) is True
    assert is_in_window(before, NY_AM_SESSION) is False
    assert is_in_window(after, NY_AM_SESSION) is False


def test_ninety_minute_cycle_epoch_alignment() -> None:
    instant = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
    cycle = ninety_minute_cycle(instant)
    assert cycle.opened_at <= instant < cycle.closed_at
    assert (cycle.closed_at - cycle.opened_at).total_seconds() == 5400
    assert cycle.opened_at.tzinfo is UTC
    assert ninety_minute_cycle(instant).logical_values() == cycle.logical_values()
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    assert cycle.index == int((cycle.opened_at - epoch).total_seconds()) // 5400


def test_ninety_minute_cycle_rejects_unaligned() -> None:
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    with pytest.raises(DemoTradingWindowValidationError):
        NinetyMinuteCycle(
            index=1,
            opened_at=epoch + timedelta(seconds=60),
            closed_at=epoch + timedelta(seconds=5460),
        )


def test_ninety_minute_cycle_rejects_subsecond_epoch_offset() -> None:
    # A cycle shifted 0.5s off the 5400s grid is NOT epoch-aligned; the check
    # must use exact microsecond arithmetic, not float truncation.
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    with pytest.raises(DemoTradingWindowValidationError):
        NinetyMinuteCycle(
            index=1,
            opened_at=epoch + timedelta(seconds=5400, microseconds=500000),
            closed_at=epoch + timedelta(seconds=10800, microseconds=500000),
        )


def _valid_output_identity() -> tuple[
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
    DemoTradingConfigFingerprint,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingMethodologyFingerprint,
    DemoTradingSetupSpec,
]:
    code = DemoTradingTraderCode("vt-01")
    version = DemoTradingTraderVersion("v1")
    config = compute_trader_config_fingerprint(
        schema_version="trader-config-v1",
        parameters=_params(("sweep.strength", 2)),
    )
    methodology_id = DemoTradingMethodologyId("ny-precision-core")
    methodology_version = DemoTradingMethodologyVersion("v1")
    methodology_fingerprint = _methodology_fingerprint()
    setup = DemoTradingSetupSpec(
        side=DemoTradingSetupSide.LONG,
        entry_price=Decimal("1.1000"),
        invalidation_price=Decimal("1.0950"),
        take_profit_price=Decimal("1.1100"),
        entry_reason="fvg",
    )
    return (
        code,
        version,
        config,
        methodology_id,
        methodology_version,
        methodology_fingerprint,
        setup,
    )


def test_output_fingerprint_rejects_raw_side_string() -> None:
    code, version, config, mid, mver, mfp, setup = _valid_output_identity()
    with pytest.raises(DemoTradingValidationError):
        compute_trader_output_fingerprint(
            trader_code=code,
            version=version,
            config_fingerprint=config,
            methodology_id=mid,
            methodology_version=mver,
            methodology_fingerprint=mfp,
            evidence_refs=(),
            timeframe="M5",
            session="ny-am-session",
            decision=DemoTradingDecision.SETUP,
            side=cast(DemoTradingSetupSide, "long"),
            setup=setup,
            abstain_reason=None,
            evaluated_at=_BASE,
        )


def test_output_fingerprint_rejects_setup_decision_without_side_or_setup() -> None:
    code, version, config, mid, mver, mfp, _ = _valid_output_identity()
    with pytest.raises(DemoTradingValidationError):
        compute_trader_output_fingerprint(
            trader_code=code,
            version=version,
            config_fingerprint=config,
            methodology_id=mid,
            methodology_version=mver,
            methodology_fingerprint=mfp,
            evidence_refs=(),
            timeframe="M5",
            session="ny-am-session",
            decision=DemoTradingDecision.SETUP,
            side=None,
            setup=None,
            abstain_reason=None,
            evaluated_at=_BASE,
        )


def test_config_fingerprint_revalidates_corrupted_parameter_material() -> None:
    # A reflectively corrupted retained parameter (float smuggled into the value)
    # must fail closed rather than being silently hashed into the fingerprint.
    param = DemoTradingConfigParameter("sweep.strength", 2)
    object.__setattr__(param, "value", 1.5)
    with pytest.raises(DemoTradingValidationError):
        compute_trader_config_fingerprint(
            schema_version="trader-config-v1",
            parameters=(param,),
        )
