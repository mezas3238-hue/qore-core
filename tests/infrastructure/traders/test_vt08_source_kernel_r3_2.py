from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab.trader_daily_cardinality import (
    MarketDayId,
    MarketDayLedger,
)
from qore.infrastructure.trader_lab.vt08_market_day_ledger import (
    VT08MarketDayLedger,
    VT08MarketDayLedgerValidationError,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_source_kernel_r3_2 import (
    OWNER_FOREX_ANCHORS,
    OWNER_FUTURES_ANCHORS,
    SOURCE_FOREX_ANCHORS,
    SOURCE_FUTURES_ANCHORS,
    VT08CisdEvidence,
    VT08DeliverySequence,
    VT08EntryCandidate,
    VT08EntryFamily,
    VT08EquilibriumReference,
    VT08HtfLifecycle,
    VT08LtfProfile,
    VT08MarketFamily,
    VT08ProtectedSwing,
    VT08ProvenanceClass,
    VT08Scenario,
    VT08SourceBundle,
    VT08SourceKernelValidationError,
    VT08SourceProvenance,
    VT08StopCandidate,
    VT08StopFamily,
    VT08TargetCandidate,
    VT08TargetFamily,
    VT08TimingProfile,
    VT08WickEvidence,
    anchor_hours,
    delivery_sequence,
    is_authorized_anchor,
    ltf_minutes,
    scenario_for_wick,
    validate_source_bundle,
)

_NY = ZoneInfo("America/New_York")
_SHA40 = "a" * 40
_SHA256 = "b" * 64


def _source(note: str = "primary-audio") -> VT08SourceProvenance:
    return VT08SourceProvenance(
        classification=VT08ProvenanceClass.SOURCE_EXPLICIT,
        source_refs=("youtube:FAKWJ-1NlLE",),
        note=note,
    )


def _entry(decision_at: datetime) -> VT08EntryCandidate:
    return VT08EntryCandidate(
        candidate_id="entry:1",
        family=VT08EntryFamily.POSITIONAL_ENTRY,
        side=DemoTradingSetupSide.LONG,
        ltf_profile=VT08LtfProfile.M15,
        formed_at=decision_at - timedelta(minutes=30),
        confirmed_at=decision_at - timedelta(minutes=15),
        decision_at=decision_at,
        zone_low=Decimal("100"),
        zone_high=Decimal("101"),
        executable_price=Decimal("100.5"),
        compatible_stop_families=(VT08StopFamily.PS_STOP,),
        compatible_target_families=(VT08TargetFamily.TWO_R_PLUS,),
        provenance=_source(),
    )


def test_primary_audio_delivery_mapping_is_explicit_not_future_inferred() -> None:
    assert delivery_sequence(DemoTradingSetupSide.LONG) is VT08DeliverySequence.BULL_OLHC
    assert delivery_sequence(DemoTradingSetupSide.SHORT) is VT08DeliverySequence.BEAR_OHLC


def test_qualitative_wick_evidence_selects_c2_or_c3_without_numeric_threshold() -> None:
    assert (
        scenario_for_wick(VT08WickEvidence.SHALLOW_EARLY_RANGE_AVAILABLE)
        is VT08Scenario.C2
    )
    assert scenario_for_wick(VT08WickEvidence.LARGE_OPPOSING_MOVE) is VT08Scenario.C3
    assert scenario_for_wick(VT08WickEvidence.RANGE_CONSUMED) is VT08Scenario.C3
    assert scenario_for_wick(VT08WickEvidence.UNRESOLVED) is None


def test_source_complete_and_owner_timing_profiles_are_not_conflated() -> None:
    assert SOURCE_FOREX_ANCHORS == (1, 5, 9, 13)
    assert SOURCE_FUTURES_ANCHORS == (2, 6, 10, 14)
    assert OWNER_FOREX_ANCHORS == (1, 5, 9)
    assert OWNER_FUTURES_ANCHORS == (2, 6, 10)
    assert anchor_hours(VT08MarketFamily.FOREX, VT08TimingProfile.SOURCE_COMPLETE) == (
        1,
        5,
        9,
        13,
    )
    assert anchor_hours(VT08MarketFamily.FUTURES, VT08TimingProfile.OWNER_OPERATIONAL) == (
        2,
        6,
        10,
    )


def test_source_anchor_validation_is_new_york_dst_aware() -> None:
    winter = datetime(2026, 1, 5, 18, 0, tzinfo=UTC)
    summer = datetime(2026, 7, 6, 17, 0, tzinfo=UTC)
    for opened_at in (winter, summer):
        assert opened_at.astimezone(_NY).hour == 13
        assert is_authorized_anchor(
            family=VT08MarketFamily.FOREX,
            profile=VT08TimingProfile.SOURCE_COMPLETE,
            opened_at=opened_at,
        )
        assert not is_authorized_anchor(
            family=VT08MarketFamily.FOREX,
            profile=VT08TimingProfile.OWNER_OPERATIONAL,
            opened_at=opened_at,
        )


def test_ltf_profiles_are_independent_observation_profiles() -> None:
    assert ltf_minutes(VT08LtfProfile.M15) == 15
    assert ltf_minutes(VT08LtfProfile.M5_FRACTAL) == 5
    assert ltf_minutes(VT08LtfProfile.M3_FRACTAL) == 3


def test_equilibrium_is_exact_fifty_percent_and_causal() -> None:
    formed = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    eq = VT08EquilibriumReference(
        range_source="current-h4",
        range_high=Decimal("110"),
        range_low=Decimal("90"),
        formed_at=formed,
        known_at=formed,
        provenance=_source(),
    )
    assert eq.eq_price == Decimal("100")
    with pytest.raises(VT08SourceKernelValidationError):
        VT08EquilibriumReference(
            range_source="future-range",
            range_high=Decimal("110"),
            range_low=Decimal("90"),
            formed_at=formed,
            known_at=formed - timedelta(minutes=1),
            provenance=_source(),
        )


def test_cisd_requires_causal_close_through_opposing_series() -> None:
    formed = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    cisd = VT08CisdEvidence(
        side=DemoTradingSetupSide.LONG,
        important_level_ref="poi:fvg:1",
        opposing_series_open=Decimal("100"),
        opposing_series_extreme=Decimal("95"),
        confirmed_close=Decimal("101"),
        formed_at=formed,
        confirmed_at=formed + timedelta(minutes=15),
        provenance=_source(),
    )
    assert cisd.confirmed_close > cisd.opposing_series_open
    with pytest.raises(VT08SourceKernelValidationError):
        VT08CisdEvidence(
            side=DemoTradingSetupSide.LONG,
            important_level_ref="poi:fvg:1",
            opposing_series_open=Decimal("100"),
            opposing_series_extreme=Decimal("95"),
            confirmed_close=Decimal("99"),
            formed_at=formed,
            confirmed_at=formed + timedelta(minutes=15),
            provenance=_source(),
        )


def test_multiple_protected_swings_can_exist_without_hidden_priority() -> None:
    formed = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    cisd = VT08CisdEvidence(
        side=DemoTradingSetupSide.LONG,
        important_level_ref="poi:1",
        opposing_series_open=Decimal("100"),
        opposing_series_extreme=Decimal("95"),
        confirmed_close=Decimal("101"),
        formed_at=formed,
        confirmed_at=formed + timedelta(minutes=15),
        provenance=_source(),
    )
    first = VT08ProtectedSwing(
        DemoTradingSetupSide.LONG,
        Decimal("95"),
        formed + timedelta(minutes=15),
        cisd,
        _source(),
    )
    second = VT08ProtectedSwing(
        DemoTradingSetupSide.LONG,
        Decimal("96"),
        formed + timedelta(minutes=30),
        cisd,
        _source(),
    )
    assert first.price != second.price


def test_revision_3_2_exposes_all_entry_and_stop_families_without_priority() -> None:
    assert {item for item in VT08EntryFamily} == {
        VT08EntryFamily.REVERSAL_ENTRY,
        VT08EntryFamily.CONTINUATION_ENTRY,
        VT08EntryFamily.CONFIDENT_ENTRY,
        VT08EntryFamily.POSITIONAL_ENTRY,
        VT08EntryFamily.OPEN_ENTRY,
        VT08EntryFamily.POI_CONTINUATION_ENTRY,
    }
    assert {item for item in VT08StopFamily} == {
        VT08StopFamily.PS_STOP,
        VT08StopFamily.CISD_EQ_50_STOP,
        VT08StopFamily.OPPOSING_CANDLE_STOP,
        VT08StopFamily.FVG_STOP,
        VT08StopFamily.BODY_LOW_STOP,
    }


def test_h4_lifecycle_forces_time_exit_boundary_and_new_h4_reevaluation() -> None:
    opened = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)
    lifecycle = VT08HtfLifecycle(opened, opened + timedelta(hours=4), _source())
    assert lifecycle.trade_valid_until == opened + timedelta(hours=4)
    lifecycle.require_decision_inside(opened + timedelta(hours=3, minutes=59))
    with pytest.raises(VT08SourceKernelValidationError):
        lifecycle.require_decision_inside(lifecycle.closes_at)
    next_lifecycle = VT08HtfLifecycle(
        lifecycle.closes_at,
        lifecycle.closes_at + timedelta(hours=4),
        _source("fresh-h4"),
    )
    assert next_lifecycle.opened_at == lifecycle.closes_at


def test_source_bundle_rejects_blind_cartesian_product_and_future_evidence() -> None:
    opened = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)
    decision = opened + timedelta(hours=1)
    lifecycle = VT08HtfLifecycle(opened, opened + timedelta(hours=4), _source())
    entry = _entry(decision)
    stop = VT08StopCandidate(VT08StopFamily.PS_STOP, Decimal("99"), decision, _source())
    target = VT08TargetCandidate(
        VT08TargetFamily.TWO_R_PLUS,
        Decimal("103.5"),
        decision,
        _source(),
    )
    bundle = VT08SourceBundle(
        "positional-ps-2r",
        VT08EntryFamily.POSITIONAL_ENTRY,
        VT08StopFamily.PS_STOP,
        VT08TargetFamily.TWO_R_PLUS,
        _source(),
    )
    validate_source_bundle(
        entry=entry,
        stop=stop,
        target=target,
        bundle=bundle,
        lifecycle=lifecycle,
    )
    bad_bundle = VT08SourceBundle(
        "positional-fvg-2r",
        VT08EntryFamily.POSITIONAL_ENTRY,
        VT08StopFamily.FVG_STOP,
        VT08TargetFamily.TWO_R_PLUS,
        _source(),
    )
    with pytest.raises(VT08SourceKernelValidationError):
        validate_source_bundle(
            entry=entry,
            stop=stop,
            target=target,
            bundle=bad_bundle,
            lifecycle=lifecycle,
        )
    future_target = VT08TargetCandidate(
        VT08TargetFamily.TWO_R_PLUS,
        Decimal("103.5"),
        decision + timedelta(minutes=1),
        _source(),
    )
    with pytest.raises(VT08SourceKernelValidationError):
        validate_source_bundle(
            entry=entry,
            stop=stop,
            target=future_target,
            bundle=bundle,
            lifecycle=lifecycle,
        )


def test_vt08_market_day_ledger_keeps_diagnostics_many_to_one() -> None:
    cardinality = MarketDayLedger(
        market_day_id=MarketDayId("vt08-forex", "EURUSD", date(2026, 1, 5)),
        eligible_day=True,
        data_complete=True,
        authorized_windows=SOURCE_FOREX_ANCHORS,
        source_rule_version="r3.2-primary-audio-v1",
        software_sha=_SHA40,
        evidence_fingerprint=_SHA256,
    )
    ledger = VT08MarketDayLedger(
        cardinality=cardinality,
        market_family=VT08MarketFamily.FOREX,
        timing_profile=VT08TimingProfile.SOURCE_COMPLETE,
        ltf_profile=VT08LtfProfile.M15,
        source_provenance=("primary-audio",),
    )
    for hour in SOURCE_FOREX_ANCHORS:
        ledger = replace(ledger, cardinality=ledger.cardinality.observe_window(hour))
    ledger = ledger.add_scenario_candidate(candidate_id="c2:1", scenario="c2")
    ledger = ledger.add_scenario_candidate(candidate_id="c3:1", scenario="c3")
    ledger = ledger.add_diagnostic(diagnostic_id="entry:1", category="entry")
    ledger = ledger.add_diagnostic(diagnostic_id="entry:2", category="entry")
    payload = ledger.payload()
    assert payload["window_count"] == 4
    assert payload["candidate_count"] == 2
    assert payload["entry_family_candidates"] == 2
    assert payload["selected_setup_count"] == 0
    assert payload["fill_count"] == 0


def test_vt08_market_day_ledger_rejects_timing_profile_window_mismatch() -> None:
    cardinality = MarketDayLedger(
        market_day_id=MarketDayId("vt08-futures", "NAS100", date(2026, 1, 5)),
        eligible_day=True,
        data_complete=True,
        authorized_windows=OWNER_FUTURES_ANCHORS,
        source_rule_version="r3.2-primary-audio-v1",
        software_sha=_SHA40,
        evidence_fingerprint=_SHA256,
    )
    with pytest.raises(VT08MarketDayLedgerValidationError):
        VT08MarketDayLedger(
            cardinality=cardinality,
            market_family=VT08MarketFamily.FUTURES,
            timing_profile=VT08TimingProfile.SOURCE_COMPLETE,
            ltf_profile=VT08LtfProfile.M15,
        )
