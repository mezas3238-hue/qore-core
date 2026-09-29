from __future__ import annotations

import inspect
from datetime import UTC, date, datetime, timedelta

import pytest

import qore.infrastructure.core_stack_v2.global_temporal_comparability as module
from qore.infrastructure.core_stack_v2.global_temporal_comparability import (
    CalendarDateOverride,
    CanonicalCalendarMappingRecord,
    CanonicalCalendarMappingRegistry,
    CanonicalCalendarMappingStatus,
    ComparabilityConfidence,
    ComparabilityUncertainty,
    DateSessionInterval,
    ExpectedUpdateCadencePolicy,
    GlobalMarketCalendar,
    GlobalMarketCalendarRegistry,
    GlobalTemporalAlignmentEngine,
    LiquidityObservation,
    LiquidityState,
    MarketCalendarBinding,
    MarketSessionSnapshot,
    MarketSessionState,
    ProviderInstrumentIdentity,
    ProviderObservabilityState,
    ProviderOperationalSignal,
    RelationalComparabilityPolicy,
    RelationalComparabilityPolicyRegistry,
    RelationalComparabilityState,
    TemporalComparabilityError,
    TemporalMarketObservation,
    WeeklySessionRule,
    assess_provider_observability,
    assess_relational_comparability,
    evaluate_market_session,
)
from qore.infrastructure.market_clock_schedule import WallClockBoundary

NOW = datetime(2026, 7, 1, 14, 0, tzinfo=UTC)
CALENDAR_SHA = "1" * 64

SOURCE = ProviderInstrumentIdentity(
    instrument_key="CTRADER_DEMO:AAA:1",
    provider="CTRADER_DEMO",
    provider_symbol_id=1,
)
TARGET = ProviderInstrumentIdentity(
    instrument_key="CTRADER_DEMO:BBB:2",
    provider="CTRADER_DEMO",
    provider_symbol_id=2,
)


def _calendar(
    *,
    overrides: tuple[CalendarDateOverride, ...] = (),
) -> GlobalMarketCalendar:
    return GlobalMarketCalendar(
        calendar_id="XNYS-RTH",
        version="calendar-test-001",
        venue="XNYS",
        iana_timezone="America/New_York",
        weekly_sessions=tuple(
            WeeklySessionRule(
                weekday=weekday,
                opens_at=WallClockBoundary(9, 30),
                closes_at=WallClockBoundary(16),
            )
            for weekday in range(5)
        ),
        date_overrides=overrides,
        provenance_refs=("calendar:test",),
    )


def _registry(
    *,
    calendar: GlobalMarketCalendar | None = None,
) -> GlobalMarketCalendarRegistry:
    if calendar is None:
        return GlobalMarketCalendarRegistry(
            version="registry-001",
            calendars=(),
            bindings=(),
            provenance_refs=("registry:test",),
        )
    return GlobalMarketCalendarRegistry(
        version="registry-001",
        calendars=(calendar,),
        bindings=tuple(
            sorted(
                (
                    MarketCalendarBinding(
                        instrument_key=SOURCE.instrument_key,
                        canonical_instrument_id="canonical:AAA",
                        calendar_id=calendar.calendar_id,
                        provider_schedule_timezone="UTC",
                        timezone_mapping_version="tz-map-001",
                        provenance_refs=("binding:AAA",),
                    ),
                    MarketCalendarBinding(
                        instrument_key=TARGET.instrument_key,
                        canonical_instrument_id="canonical:BBB",
                        calendar_id=calendar.calendar_id,
                        provider_schedule_timezone="UTC",
                        timezone_mapping_version="tz-map-001",
                        provenance_refs=("binding:BBB",),
                    ),
                ),
                key=lambda item: item.instrument_key,
            )
        ),
        provenance_refs=("registry:test",),
    )


def _observation(
    identity: ProviderInstrumentIdentity,
    *,
    event_at: datetime,
    transport_ms: int = 50,
) -> TemporalMarketObservation:
    receipt = event_at + timedelta(milliseconds=transport_ms)
    observed = receipt + timedelta(milliseconds=10)
    processing = observed + timedelta(milliseconds=10)
    return TemporalMarketObservation(
        identity=identity,
        canonical_instrument_id=f"canonical:{identity.provider_symbol_id}",
        market_time_at=event_at,
        venue_time_at=event_at,
        provider_event_time_at=event_at,
        receipt_time_at=receipt,
        observation_time_at=observed,
        processing_time_at=processing,
        evidence_ref=f"evidence:{identity.provider_symbol_id}:{event_at.isoformat()}",
    )


def _session(
    identity: ProviderInstrumentIdentity,
    state: MarketSessionState = MarketSessionState.OPEN_ACTIVE,
    *,
    active: bool = True,
    evaluation_at: datetime = NOW,
) -> MarketSessionSnapshot:
    return MarketSessionSnapshot(
        instrument_key=identity.instrument_key,
        evaluation_at=evaluation_at,
        state=state,
        is_economically_active=active,
        calendar_id="XNYS-RTH",
        calendar_version="calendar-test-001",
        iana_timezone="America/New_York",
        local_date=NOW.date(),
        provenance_refs=(f"session:{identity.provider_symbol_id}",),
    )


def _liquidity(
    identity: ProviderInstrumentIdentity,
    state: LiquidityState = LiquidityState.NORMAL,
    *,
    activity: int = 8000,
) -> LiquidityObservation:
    return LiquidityObservation(
        instrument_key=identity.instrument_key,
        evaluation_at=NOW,
        state=state,
        activity_ratio_bps=activity,
        spread_quality_bps=9000,
        provenance_refs=(f"liquidity:{identity.provider_symbol_id}",),
    )


def _cadence(identity: ProviderInstrumentIdentity) -> ExpectedUpdateCadencePolicy:
    return ExpectedUpdateCadencePolicy(
        version="cadence-001",
        instrument_key=identity.instrument_key,
        provider=identity.provider,
        session_state=MarketSessionState.OPEN_ACTIVE,
        expected_interval_ms=100,
        delayed_after_ms=500,
        stale_after_ms=5000,
        provenance_refs=(f"cadence:{identity.provider_symbol_id}",),
    )


def _provider(
    identity: ProviderInstrumentIdentity,
    observation: TemporalMarketObservation | None,
    *,
    signal: ProviderOperationalSignal = ProviderOperationalSignal.HEALTHY,
) -> object:
    return assess_provider_observability(
        identity=identity,
        observation=observation,
        evaluation_at=NOW,
        cadence=_cadence(identity),
        operational_signal=signal,
        provenance_refs=(f"provider:{identity.provider_symbol_id}",),
    )


def _policy(**overrides: object) -> RelationalComparabilityPolicy:
    values: dict[str, object] = {
        "version": "compare-001",
        "relation_scope": "test:index:index:m1",
        "source_max_age_ms": 2000,
        "target_max_age_ms": 2000,
        "max_temporal_skew_ms": 500,
        "minimum_activity_ratio_bps": 5000,
        "allow_open_low_liquidity": True,
        "allow_partial_session": True,
        "provenance_refs": ("policy:test",),
    }
    values.update(overrides)
    return RelationalComparabilityPolicy(**values)  # type: ignore[arg-type]


def _canonical_mapping(
    *,
    identity: ProviderInstrumentIdentity = SOURCE,
    provider_symbol: str = "AAA",
    status: CanonicalCalendarMappingStatus = (
        CanonicalCalendarMappingStatus.UNRESOLVED
    ),
    **overrides: object,
) -> CanonicalCalendarMappingRecord:
    values: dict[str, object] = {
        "instrument_key": identity.instrument_key,
        "provider": identity.provider,
        "provider_symbol": provider_symbol,
        "provider_symbol_id": identity.provider_symbol_id,
        "status": status,
        "canonical_instrument_id": None,
        "venue": None,
        "calendar_id": None,
        "calendar_version": None,
        "iana_timezone": None,
        "provider_schedule_timezone": "UTC",
        "timezone_mapping_version": None,
        "identity_evidence_refs": (),
        "venue_evidence_refs": (),
        "calendar_evidence_refs": (),
        "provider_schedule_evidence_refs": ("provider:schedule:test",),
        "reason_codes": ("UNRESOLVED_CANONICAL_MAPPING",),
    }
    values.update(overrides)
    return CanonicalCalendarMappingRecord(**values)  # type: ignore[arg-type]


def _assess(
    *,
    source_event_at: datetime | None = None,
    target_event_at: datetime | None = None,
    source_session: MarketSessionSnapshot | None = None,
    target_session: MarketSessionSnapshot | None = None,
    source_signal: ProviderOperationalSignal = ProviderOperationalSignal.HEALTHY,
    target_signal: ProviderOperationalSignal = ProviderOperationalSignal.HEALTHY,
    source_liquidity: LiquidityObservation | None = None,
    target_liquidity: LiquidityObservation | None = None,
    policy: RelationalComparabilityPolicy | None = None,
):
    source = None if source_event_at is None else _observation(
        SOURCE,
        event_at=source_event_at,
    )
    target = None if target_event_at is None else _observation(
        TARGET,
        event_at=target_event_at,
    )
    pair = GlobalTemporalAlignmentEngine.align_pair(
        source_observations=() if source is None else (source,),
        target_observations=() if target is None else (target,),
        evaluation_at=NOW,
        source_identity=SOURCE,
        target_identity=TARGET,
    )
    return assess_relational_comparability(
        pair=pair,
        source_session=source_session or _session(SOURCE),
        target_session=target_session or _session(TARGET),
        source_provider=_provider(SOURCE, source, signal=source_signal),
        target_provider=_provider(TARGET, target, signal=target_signal),
        source_liquidity=source_liquidity or _liquidity(SOURCE),
        target_liquidity=target_liquidity or _liquidity(TARGET),
        policy=policy or _policy(),
        calendar_registry_fingerprint=CALENDAR_SHA,
        provenance_refs=("relation:test",),
    )


def test_market_calendar_uses_iana_dst_for_summer_and_winter() -> None:
    registry = _registry(calendar=_calendar())

    summer = evaluate_market_session(
        registry=registry,
        instrument_key=SOURCE.instrument_key,
        evaluation_at=datetime(2026, 7, 1, 13, 30, tzinfo=UTC),
    )
    winter = evaluate_market_session(
        registry=registry,
        instrument_key=SOURCE.instrument_key,
        evaluation_at=datetime(2026, 1, 15, 14, 30, tzinfo=UTC),
    )

    assert summer.state is MarketSessionState.OPEN_ACTIVE
    assert winter.state is MarketSessionState.OPEN_ACTIVE


def test_dst_transition_preserves_local_open_across_utc_offset_change() -> None:
    registry = _registry(calendar=_calendar())

    before_dst = evaluate_market_session(
        registry=registry,
        instrument_key=SOURCE.instrument_key,
        evaluation_at=datetime(2026, 3, 6, 14, 30, tzinfo=UTC),
    )
    after_dst = evaluate_market_session(
        registry=registry,
        instrument_key=SOURCE.instrument_key,
        evaluation_at=datetime(2026, 3, 9, 13, 30, tzinfo=UTC),
    )

    assert before_dst.state is MarketSessionState.OPEN_ACTIVE
    assert after_dst.state is MarketSessionState.OPEN_ACTIVE
    assert before_dst.iana_timezone == "America/New_York"
    assert after_dst.iana_timezone == "America/New_York"


def test_comparability_policy_registry_is_deterministic_and_exact_match_only() -> None:
    first = _policy(
        relation_scope="correlation:index:index:m1",
        version="compare-correlation-001",
        provenance_refs=("policy:correlation",),
    )
    second = _policy(
        relation_scope="lead_lag:index:index:m1",
        version="compare-lead-lag-001",
        max_temporal_skew_ms=250,
        provenance_refs=("policy:lead-lag",),
    )
    registry = RelationalComparabilityPolicyRegistry(
        version="comparability-registry-001",
        policies=(first, second),
        provenance_refs=("registry:comparability:test",),
    )
    replica = RelationalComparabilityPolicyRegistry(
        version="comparability-registry-001",
        policies=(first, second),
        provenance_refs=("registry:comparability:test",),
    )

    assert registry.policy_for(first.relation_scope) == first
    assert registry.policy_for("unknown:index:index:m1") is None
    assert registry.fingerprint() == replica.fingerprint()
    assert len(registry.fingerprint()) == 64

    with pytest.raises(
        TemporalComparabilityError,
        match="canonical scope order",
    ):
        RelationalComparabilityPolicyRegistry(
            version="comparability-registry-001",
            policies=(second, first),
            provenance_refs=("registry:comparability:test",),
        )


def test_overnight_rollover_gap_is_explicit_session_break() -> None:
    calendar = GlobalMarketCalendar(
        calendar_id="XCME-OVERNIGHT",
        version="calendar-overnight-001",
        venue="XCME",
        iana_timezone="America/Chicago",
        weekly_sessions=tuple(
            WeeklySessionRule(
                weekday=weekday,
                opens_at=WallClockBoundary(17),
                closes_at=WallClockBoundary(16),
            )
            for weekday in range(5)
        ),
        date_overrides=(),
        provenance_refs=("calendar:overnight:test",),
    )
    registry = GlobalMarketCalendarRegistry(
        version="registry-overnight-001",
        calendars=(calendar,),
        bindings=(
            MarketCalendarBinding(
                instrument_key=SOURCE.instrument_key,
                canonical_instrument_id="canonical:OVERNIGHT",
                calendar_id=calendar.calendar_id,
                provider_schedule_timezone="UTC",
                timezone_mapping_version="tz-map-001",
                provenance_refs=("binding:overnight:test",),
            ),
        ),
        provenance_refs=("registry:overnight:test",),
    )

    before_break = evaluate_market_session(
        registry=registry,
        instrument_key=SOURCE.instrument_key,
        evaluation_at=datetime(2026, 7, 7, 20, 30, tzinfo=UTC),
    )
    maintenance_break = evaluate_market_session(
        registry=registry,
        instrument_key=SOURCE.instrument_key,
        evaluation_at=datetime(2026, 7, 7, 21, 30, tzinfo=UTC),
    )
    reopened = evaluate_market_session(
        registry=registry,
        instrument_key=SOURCE.instrument_key,
        evaluation_at=datetime(2026, 7, 7, 22, 0, tzinfo=UTC),
    )

    assert before_break.state is MarketSessionState.OPEN_ACTIVE
    assert maintenance_break.state is MarketSessionState.SESSION_BREAK
    assert maintenance_break.is_economically_active is False
    assert reopened.state is MarketSessionState.OPEN_ACTIVE


def test_cross_timezone_overlap_respects_independent_dst_calendars() -> None:
    london = GlobalMarketCalendar(
        calendar_id="XLON-RTH",
        version="calendar-london-001",
        venue="XLON",
        iana_timezone="Europe/London",
        weekly_sessions=tuple(
            WeeklySessionRule(
                weekday=weekday,
                opens_at=WallClockBoundary(8),
                closes_at=WallClockBoundary(16, 30),
            )
            for weekday in range(5)
        ),
        date_overrides=(),
        provenance_refs=("calendar:london:test",),
    )
    new_york = _calendar()
    registry = GlobalMarketCalendarRegistry(
        version="registry-cross-timezone-001",
        calendars=(london, new_york),
        bindings=tuple(
            sorted(
                (
                    MarketCalendarBinding(
                        instrument_key=SOURCE.instrument_key,
                        canonical_instrument_id="canonical:NY",
                        calendar_id=new_york.calendar_id,
                        provider_schedule_timezone="UTC",
                        timezone_mapping_version="tz-map-001",
                        provenance_refs=("binding:NY",),
                    ),
                    MarketCalendarBinding(
                        instrument_key=TARGET.instrument_key,
                        canonical_instrument_id="canonical:LONDON",
                        calendar_id=london.calendar_id,
                        provider_schedule_timezone="UTC",
                        timezone_mapping_version="tz-map-001",
                        provenance_refs=("binding:LONDON",),
                    ),
                ),
                key=lambda item: item.instrument_key,
            )
        ),
        provenance_refs=("registry:cross-timezone:test",),
    )

    before_us_dst = datetime(2026, 3, 6, 14, 0, tzinfo=UTC)
    after_us_before_uk_dst = datetime(2026, 3, 20, 13, 45, tzinfo=UTC)

    ny_before = evaluate_market_session(
        registry=registry,
        instrument_key=SOURCE.instrument_key,
        evaluation_at=before_us_dst,
    )
    london_before = evaluate_market_session(
        registry=registry,
        instrument_key=TARGET.instrument_key,
        evaluation_at=before_us_dst,
    )
    ny_after = evaluate_market_session(
        registry=registry,
        instrument_key=SOURCE.instrument_key,
        evaluation_at=after_us_before_uk_dst,
    )
    london_after = evaluate_market_session(
        registry=registry,
        instrument_key=TARGET.instrument_key,
        evaluation_at=after_us_before_uk_dst,
    )

    assert ny_before.state is MarketSessionState.PRE_SESSION
    assert london_before.state is MarketSessionState.OPEN_ACTIVE
    assert ny_after.state is MarketSessionState.OPEN_ACTIVE
    assert london_after.state is MarketSessionState.OPEN_ACTIVE


def test_provider_schedule_alone_cannot_create_canonical_binding() -> None:
    unresolved = _canonical_mapping()

    with pytest.raises(
        TemporalComparabilityError,
        match="only VERIFIED canonical mapping",
    ):
        unresolved.to_binding()


@pytest.mark.parametrize(
    ("missing_field", "expected_error"),
    (
        ("identity", "identity evidence"),
        ("venue", "venue evidence"),
        ("calendar", "calendar evidence"),
    ),
)
def test_verified_mapping_requires_independent_evidence_planes(
    missing_field: str,
    expected_error: str,
) -> None:
    identity_refs = ("identity:instrument-master",)
    venue_refs = ("venue:exchange-master",)
    calendar_refs = ("calendar:official-version",)
    if missing_field == "identity":
        identity_refs = ()
    elif missing_field == "venue":
        venue_refs = ()
    else:
        calendar_refs = ()

    with pytest.raises(TemporalComparabilityError, match=expected_error):
        _canonical_mapping(
            status=CanonicalCalendarMappingStatus.VERIFIED,
            canonical_instrument_id="canonical:AAA",
            venue="XNYS",
            calendar_id="XNYS-RTH",
            calendar_version="calendar-test-001",
            iana_timezone="America/New_York",
            timezone_mapping_version="tz-map-001",
            identity_evidence_refs=identity_refs,
            venue_evidence_refs=venue_refs,
            calendar_evidence_refs=calendar_refs,
            reason_codes=("INDEPENDENT_EVIDENCE_VERIFIED",),
        )


def test_verified_canonical_mapping_emits_provenance_bound_binding() -> None:
    record = _canonical_mapping(
        status=CanonicalCalendarMappingStatus.VERIFIED,
        canonical_instrument_id="canonical:AAA",
        venue="XNYS",
        calendar_id="XNYS-RTH",
        calendar_version="calendar-test-001",
        iana_timezone="America/New_York",
        timezone_mapping_version="tz-map-001",
        identity_evidence_refs=("identity:instrument-master",),
        venue_evidence_refs=("venue:exchange-master",),
        calendar_evidence_refs=("calendar:official-version",),
        reason_codes=("INDEPENDENT_EVIDENCE_VERIFIED",),
    )

    binding = record.to_binding()

    assert binding.instrument_key == SOURCE.instrument_key
    assert binding.canonical_instrument_id == "canonical:AAA"
    assert binding.calendar_id == "XNYS-RTH"
    assert binding.provider_schedule_timezone == "UTC"
    assert binding.provenance_refs == (
        "calendar:official-version",
        "identity:instrument-master",
        "provider:schedule:test",
        "venue:exchange-master",
    )


def test_verified_mapping_rejects_invalid_iana_timezone() -> None:
    with pytest.raises(
        TemporalComparabilityError,
        match="IANA timezone is invalid",
    ):
        _canonical_mapping(
            status=CanonicalCalendarMappingStatus.VERIFIED,
            canonical_instrument_id="canonical:AAA",
            venue="XNYS",
            calendar_id="XNYS-RTH",
            calendar_version="calendar-test-001",
            iana_timezone="Not/A_Real_Zone",
            timezone_mapping_version="tz-map-001",
            identity_evidence_refs=("identity:instrument-master",),
            venue_evidence_refs=("venue:exchange-master",),
            calendar_evidence_refs=("calendar:official-version",),
            reason_codes=("INDEPENDENT_EVIDENCE_VERIFIED",),
        )


def test_canonical_mapping_registry_is_deterministic_and_fail_closed() -> None:
    unresolved = _canonical_mapping()
    verified = _canonical_mapping(
        identity=TARGET,
        provider_symbol="BBB",
        status=CanonicalCalendarMappingStatus.VERIFIED,
        canonical_instrument_id="canonical:BBB",
        venue="XNYS",
        calendar_id="XNYS-RTH",
        calendar_version="calendar-test-001",
        iana_timezone="America/New_York",
        timezone_mapping_version="tz-map-001",
        identity_evidence_refs=("identity:bbb",),
        venue_evidence_refs=("venue:xnys",),
        calendar_evidence_refs=("calendar:xnys-rth",),
        reason_codes=("INDEPENDENT_EVIDENCE_VERIFIED",),
    )
    registry = CanonicalCalendarMappingRegistry(
        version="canonical-map-registry-001",
        records=(unresolved, verified),
        provenance_refs=("registry:canonical-map:test",),
    )
    replica = CanonicalCalendarMappingRegistry(
        version="canonical-map-registry-001",
        records=(unresolved, verified),
        provenance_refs=("registry:canonical-map:test",),
    )

    assert registry.record_for(SOURCE.instrument_key) == unresolved
    assert registry.record_for("missing:instrument") is None
    assert registry.verified_bindings() == (verified.to_binding(),)
    assert registry.fingerprint() == replica.fingerprint()
    assert len(registry.fingerprint()) == 64

    with pytest.raises(
        TemporalComparabilityError,
        match="canonical instrument order",
    ):
        CanonicalCalendarMappingRegistry(
            version="canonical-map-registry-001",
            records=(verified, unresolved),
            provenance_refs=("registry:canonical-map:test",),
        )


def test_canonical_mapping_provider_identity_is_multi_provider_safe() -> None:
    other_provider = ProviderInstrumentIdentity(
        instrument_key="OTHER:AAA:1",
        provider="OTHER",
        provider_symbol_id=1,
    )
    first = _canonical_mapping()
    second = _canonical_mapping(
        identity=other_provider,
        provider_symbol="AAA",
    )
    records = tuple(
        sorted(
            (first, second),
            key=lambda item: item.instrument_key,
        )
    )

    registry = CanonicalCalendarMappingRegistry(
        version="canonical-map-registry-001",
        records=records,
        provenance_refs=("registry:canonical-map:test",),
    )

    assert len(registry.records) == 2


def test_unknown_calendar_is_explicit_insufficient_input() -> None:
    session = evaluate_market_session(
        registry=_registry(),
        instrument_key=SOURCE.instrument_key,
        evaluation_at=NOW,
    )

    assert session.state is MarketSessionState.UNKNOWN
    assert session.is_economically_active is False


def test_holiday_and_partial_early_close_are_explicit() -> None:
    holiday = CalendarDateOverride(
        local_date=date(2026, 7, 3),
        state=MarketSessionState.HOLIDAY,
    )
    early_close = CalendarDateOverride(
        local_date=date(2026, 7, 2),
        state=MarketSessionState.PARTIAL_SESSION,
        intervals=(
            DateSessionInterval(
                opens_at=WallClockBoundary(9, 30),
                closes_at=WallClockBoundary(13),
            ),
        ),
    )
    registry = _registry(calendar=_calendar(overrides=(early_close, holiday)))

    holiday_state = evaluate_market_session(
        registry=registry,
        instrument_key=SOURCE.instrument_key,
        evaluation_at=datetime(2026, 7, 3, 15, 0, tzinfo=UTC),
    )
    early_active = evaluate_market_session(
        registry=registry,
        instrument_key=SOURCE.instrument_key,
        evaluation_at=datetime(2026, 7, 2, 16, 0, tzinfo=UTC),
    )
    after_early_close = evaluate_market_session(
        registry=registry,
        instrument_key=SOURCE.instrument_key,
        evaluation_at=datetime(2026, 7, 2, 18, 0, tzinfo=UTC),
    )

    assert holiday_state.state is MarketSessionState.HOLIDAY
    assert early_active.state is MarketSessionState.PARTIAL_SESSION
    assert early_active.is_economically_active is True
    assert after_early_close.state is MarketSessionState.PARTIAL_SESSION
    assert after_early_close.is_economically_active is False


def test_both_active_fresh_and_aligned_are_comparable() -> None:
    result = _assess(
        source_event_at=NOW - timedelta(milliseconds=900),
        target_event_at=NOW - timedelta(milliseconds=1000),
    )

    assert result.comparability_state is RelationalComparabilityState.COMPARABLE
    assert result.confidence is ComparabilityConfidence.HIGH
    assert result.uncertainty is ComparabilityUncertainty.LOW
    assert result.execution_authority is False
    assert len(result.fingerprint()) == 64


def test_stale_peer_is_not_divergence() -> None:
    result = _assess(
        source_event_at=NOW - timedelta(milliseconds=900),
        target_event_at=NOW - timedelta(seconds=6),
        policy=_policy(target_max_age_ms=7000),
    )

    assert result.target_provider_state is ProviderObservabilityState.STALE
    assert result.comparability_state is RelationalComparabilityState.STALE_PEER


def test_closed_holiday_partial_and_halt_preempt_relational_claims() -> None:
    source_at = NOW - timedelta(milliseconds=900)
    target_at = NOW - timedelta(milliseconds=1000)

    closed = _assess(
        source_event_at=source_at,
        target_event_at=target_at,
        target_session=_session(
            TARGET,
            MarketSessionState.CLOSED,
            active=False,
        ),
    )
    holiday = _assess(
        source_event_at=source_at,
        target_event_at=target_at,
        target_session=_session(
            TARGET,
            MarketSessionState.HOLIDAY,
            active=False,
        ),
    )
    partial = _assess(
        source_event_at=source_at,
        target_event_at=target_at,
        target_session=_session(
            TARGET,
            MarketSessionState.PARTIAL_SESSION,
            active=True,
        ),
    )
    halt = _assess(
        source_event_at=source_at,
        target_event_at=target_at,
        target_session=_session(
            TARGET,
            MarketSessionState.HALTED,
            active=False,
        ),
    )

    assert closed.comparability_state is RelationalComparabilityState.CLOSED_PEER
    assert holiday.comparability_state is RelationalComparabilityState.HOLIDAY_SESSION
    assert (
        partial.comparability_state
        is RelationalComparabilityState.PARTIALLY_COMPARABLE
    )
    assert halt.comparability_state is RelationalComparabilityState.TRADING_HALT


def test_provider_delay_and_degradation_are_not_market_behavior() -> None:
    source = _observation(
        SOURCE,
        event_at=NOW - timedelta(seconds=2),
        transport_ms=1000,
    )
    target = _observation(
        TARGET,
        event_at=NOW - timedelta(seconds=2),
    )
    pair = GlobalTemporalAlignmentEngine.align_pair(
        source_observations=(source,),
        target_observations=(target,),
        evaluation_at=NOW,
        source_identity=SOURCE,
        target_identity=TARGET,
    )
    delayed = assess_relational_comparability(
        pair=pair,
        source_session=_session(SOURCE),
        target_session=_session(TARGET),
        source_provider=_provider(SOURCE, source),
        target_provider=_provider(TARGET, target),
        source_liquidity=_liquidity(SOURCE),
        target_liquidity=_liquidity(TARGET),
        policy=_policy(
            source_max_age_ms=3000,
            target_max_age_ms=3000,
        ),
        calendar_registry_fingerprint=CALENDAR_SHA,
        provenance_refs=("relation:test",),
    )
    degraded = _assess(
        source_event_at=NOW - timedelta(milliseconds=900),
        target_event_at=NOW - timedelta(milliseconds=1000),
        target_signal=ProviderOperationalSignal.DEGRADED,
    )

    assert delayed.comparability_state is RelationalComparabilityState.PROVIDER_DELAYED
    assert (
        degraded.comparability_state
        is RelationalComparabilityState.PROVIDER_DEGRADED
    )


def test_excessive_skew_and_illiquid_peer_degrade_epistemically() -> None:
    async_result = _assess(
        source_event_at=NOW - timedelta(milliseconds=100),
        target_event_at=NOW - timedelta(milliseconds=1600),
    )
    illiquid = _assess(
        source_event_at=NOW - timedelta(milliseconds=900),
        target_event_at=NOW - timedelta(milliseconds=1000),
        target_liquidity=_liquidity(
            TARGET,
            LiquidityState.ILLIQUID,
            activity=1000,
        ),
    )

    assert async_result.comparability_state is RelationalComparabilityState.ASYNC_MARKET
    assert illiquid.comparability_state is RelationalComparabilityState.ILLIQUID_PEER


def test_unknown_session_means_insufficient_not_divergence() -> None:
    result = _assess(
        source_event_at=NOW - timedelta(milliseconds=900),
        target_event_at=NOW - timedelta(milliseconds=1000),
        target_session=_session(
            TARGET,
            MarketSessionState.UNKNOWN,
            active=False,
        ),
    )

    assert result.comparability_state is RelationalComparabilityState.INSUFFICIENT
    assert result.confidence is ComparabilityConfidence.UNKNOWN


def test_timestamp_inversion_fails_closed() -> None:
    event = NOW - timedelta(seconds=1)
    with pytest.raises(TemporalComparabilityError, match="provider_event"):
        TemporalMarketObservation(
            identity=SOURCE,
            canonical_instrument_id="canonical:AAA",
            market_time_at=event,
            venue_time_at=event,
            provider_event_time_at=event,
            receipt_time_at=event - timedelta(milliseconds=1),
            observation_time_at=event,
            processing_time_at=event,
            evidence_ref="evidence:bad-clock",
        )


def test_future_quote_cannot_be_paired_backwards_or_repair_missing_history() -> None:
    legal = _observation(
        SOURCE,
        event_at=NOW - timedelta(seconds=1),
    )
    future = _observation(
        SOURCE,
        event_at=NOW + timedelta(seconds=1),
    )

    with pytest.raises(TemporalComparabilityError, match="future observation"):
        GlobalTemporalAlignmentEngine.latest_at(
            (legal, future),
            evaluation_at=NOW,
            expected_identity=SOURCE,
        )


def test_future_session_snapshot_cannot_contaminate_prior_evaluation() -> None:
    source = _observation(
        SOURCE,
        event_at=NOW - timedelta(milliseconds=900),
    )
    target = _observation(
        TARGET,
        event_at=NOW - timedelta(milliseconds=1000),
    )
    pair = GlobalTemporalAlignmentEngine.align_pair(
        source_observations=(source,),
        target_observations=(target,),
        evaluation_at=NOW,
        source_identity=SOURCE,
        target_identity=TARGET,
    )

    with pytest.raises(
        TemporalComparabilityError,
        match="session snapshot evaluation time drift",
    ):
        assess_relational_comparability(
            pair=pair,
            source_session=_session(
                SOURCE,
                evaluation_at=NOW + timedelta(seconds=1),
            ),
            target_session=_session(TARGET),
            source_provider=_provider(SOURCE, source),
            target_provider=_provider(TARGET, target),
            source_liquidity=_liquidity(SOURCE),
            target_liquidity=_liquidity(TARGET),
            policy=_policy(),
            calendar_registry_fingerprint=CALENDAR_SHA,
            provenance_refs=("relation:test",),
        )


def test_post_hoc_future_observation_cannot_repair_historical_pair() -> None:
    source = _observation(
        SOURCE,
        event_at=NOW - timedelta(milliseconds=900),
    )
    future_target = _observation(
        TARGET,
        event_at=NOW + timedelta(milliseconds=1),
    )

    with pytest.raises(TemporalComparabilityError, match="future observation"):
        GlobalTemporalAlignmentEngine.align_pair(
            source_observations=(source,),
            target_observations=(future_target,),
            evaluation_at=NOW,
            source_identity=SOURCE,
            target_identity=TARGET,
        )


def test_provider_identity_drift_fails_closed() -> None:
    wrong = _observation(
        TARGET,
        event_at=NOW - timedelta(seconds=1),
    )

    with pytest.raises(TemporalComparabilityError, match="identity drift"):
        GlobalTemporalAlignmentEngine.latest_at(
            (wrong,),
            evaluation_at=NOW,
            expected_identity=SOURCE,
        )


def test_same_inputs_are_deterministic() -> None:
    left = _assess(
        source_event_at=NOW - timedelta(milliseconds=900),
        target_event_at=NOW - timedelta(milliseconds=1000),
    )
    right = _assess(
        source_event_at=NOW - timedelta(milliseconds=900),
        target_event_at=NOW - timedelta(milliseconds=1000),
    )

    assert left == right
    assert left.fingerprint() == right.fingerprint()


def test_gen2_core_has_no_trader_specific_logic_or_hidden_runtime_io() -> None:
    source = inspect.getsource(module).lower()
    for forbidden in (
        "vt31",
        "silver_bullet",
        "nas100",
        "xauusd trader",
        "buy",
        "sell",
        "send_order",
        "datetime.now(",
        "datetime.utcnow(",
        "requests.",
        "httpx",
        "aiohttp",
        "socket",
    ):
        assert forbidden not in source
