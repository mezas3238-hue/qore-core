"""Full sensor → actual nine-market Master Frame → PAPER execution regression.

The world/regime evidence here is a documented synthetic FIXTURE. These
tests prove end-to-end call graph only, not historical financial performance.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from test_capitalizer_master_cognitive_frame import (
    _a1_multi_hypothesis_fixture,
    _paper_source,
)

from qore.infrastructure.trader_lab import (
    capitalizer_a1_native_source_session_clock_attestation_v1 as native_clock,
)
from qore.infrastructure.trader_lab.capitalizer_a1_m1_protected_route_forensics_v2 import (
    A1M1ProtectedRouteReview,
    M1ProtectionClass,
    SourceRouteClass,
)
from qore.infrastructure.trader_lab.capitalizer_a1_m1_second_pivot_forensics_v3 import (
    A1SecondPivotReview,
    SecondaryPivotClass,
)
from qore.infrastructure.trader_lab.capitalizer_a1_master_frame_paper_trader_integration_v1 import (
    A1PaperSource,
)
from qore.infrastructure.trader_lab.capitalizer_a1_sensorized_paper_runtime_v1 import (
    A1SensorizedPaperBridgeResult,
    run_sensorized_master_frame_paper,
)
from qore.infrastructure.trader_lab.capitalizer_a1_source_sensor_independent_attestation_v1 import (
    A1SourceSensorAttestation,
    A1SourceSensorEvidence,
    ProofStatus,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_scalper_entry_timing_sensors_shadow_v1 import (
    EntrySensorInput,
)
from qore.infrastructure.trader_lab.capitalizer_source_session_context_v2 import (
    CapitalizerSourceSessionResolution,
)

T = datetime(2026, 1, 5, 1, tzinfo=UTC)


def _bars(symbol: str) -> tuple[CapitalizerM1Bar, ...]:
    candles = (
        ("100", "101", "99.5", "100.5"),
        ("100.5", "100.8", "99", "99.5"),
        ("99.5", "100.2", "99.3", "100"),
        ("100", "100.1", "98.5", "99"),
        ("99", "99.4", "98.8", "99.1"),
        ("99.1", "100.6", "99", "100.4"),
    )
    return tuple(
        CapitalizerM1Bar(
            symbol=symbol,
            opened_at=T-timedelta(minutes=6-i),
            closed_at=T-timedelta(minutes=5-i),
            open=Decimal(o), high=Decimal(hi),
            low=Decimal(low), close=Decimal(close),
            volume=100, digits=3,
        )
        for i, (o, hi, low, close) in enumerate(candles)
    )


def _inputs() -> tuple[
    tuple[A1PaperSource, ...],
    dict[str, EntrySensorInput],
]:
    ids = ("SRC:AUDJPY:A", "SRC:AUDJPY:B", "SRC:USDJPY:C")
    originals = tuple(
        A1PaperSource(
            source_opportunity_id=sid,
            trade=replace(
                _paper_source(sid, T, symbol=market, realized_r=pnl).trade,
                entry_price="100.4",
            ),
        )
        for sid, market, pnl in (
            (ids[0], "AUDJPY", "-1"),
            (ids[1], "AUDJPY", "0.5"),
            (ids[2], "USDJPY", "0.4"),
        )
    )
    inputs = {
        row.source_opportunity_id: EntrySensorInput(
            symbol=row.trade.symbol, session="ASIA",
            decision_at=T, h1_direction="BULLISH",
            h1_basis="SOURCE_CAUSAL_C2", h1_confirmed_at=T-timedelta(hours=1),
            m15_confirmed_at=T-timedelta(minutes=15),
            m15_protected_stop=Decimal("98"),
            m1_bars=_bars(row.trade.symbol),
        )
        for row in originals
    }
    return originals, inputs


def test_native_candles_flow_to_full_master_to_actual_paper_source_decisions() -> None:
    originals, snapshots = _inputs()
    ids = tuple(row.source_opportunity_id for row in originals)
    barrier = _a1_multi_hypothesis_fixture(T, source_ids=ids)
    result = run_sensorized_master_frame_paper(
        barriers=(barrier,), source_evidence=snapshots,
        source_originals=originals, baseline_selected_source_ids=ids,
    )
    assert result.full_master_frame_invoked
    assert result.sensors_reached_full_master_frame
    assert result.observed_sensor_frames == 3
    assert result.source_cisd_identity_conflicts == 0
    assert result.report.cognitively_passed == 3
    assert result.report.paper_selected == 3
    assert result.report.master_frame_paper_metrics["trades"] == 3
    assert all(row.sensor_evidence_present for row in result.report.source_ledger)
    assert any("SCALPER_SENSOR:" in token for token in
               result.report.source_ledger[0].why_tokens) is False
    # HOW: observation tokens enter the real full frame; final WHY remains
    # gate-oriented rather than falsely claiming that missing data are known.
    assert not result.report.full_historical_native_nine_market_run
    assert not result.live_authorized


def test_source_cisd_family_conflict_is_evidence_not_an_automatic_entry_veto() -> None:
    originals, snapshots = _inputs()
    ids = tuple(row.source_opportunity_id for row in originals)
    changed = replace(
        originals[0],
        trade=replace(originals[0].trade, trigger_family="FVG_RETRACE_CISD"),
    )
    result = run_sensorized_master_frame_paper(
        barriers=(_a1_multi_hypothesis_fixture(T, source_ids=ids),),
        source_evidence=snapshots,
        source_originals=(changed, *originals[1:]),
        baseline_selected_source_ids=ids,
    )
    assert result.source_cisd_identity_conflicts == 1
    assert result.report.paper_selected == 3


def test_future_m1_or_missing_original_sensor_fails_before_cognition() -> None:
    originals, snapshots = _inputs()
    ids = tuple(row.source_opportunity_id for row in originals)
    barrier = _a1_multi_hypothesis_fixture(T, source_ids=ids)
    with pytest.raises(ValueError, match="original source IDs"):
        run_sensorized_master_frame_paper(
            barriers=(barrier,), source_evidence={
                key: value for key, value in snapshots.items() if key != ids[0]
            }, source_originals=originals, baseline_selected_source_ids=ids,
        )
    future = replace(
        _bars("AUDJPY")[-1],
        opened_at=T,
        closed_at=T+timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="future/inflight"):
        run_sensorized_master_frame_paper(
            barriers=(barrier,), source_evidence={
                **snapshots, ids[0]: replace(
                    snapshots[ids[0]], m1_bars=(*_bars("AUDJPY")[:-1], future),
                ),
            }, source_originals=originals, baseline_selected_source_ids=ids,
        )


def test_independent_sensor_witnesses_are_actually_consumed_by_paper_master() -> None:
    originals, snapshots = _inputs()
    ids = tuple(x.source_opportunity_id for x in originals)
    proof: dict[str, A1SourceSensorAttestation] = {}
    for item in originals:
        sid = item.source_opportunity_id
        at = T.isoformat()
        proof[sid] = A1SourceSensorAttestation(
            source_opportunity_id=sid,
            symbol=item.trade.symbol,
            decision_at=at,
            evidence=(
                A1SourceSensorEvidence(
                    sensor="ACTUAL_M15_STRUCTURE_REVALIDATION",
                    status=ProofStatus.OBSERVED,
                    reason="COMPLETE_M15_SOURCE_WITNESS",
                    observed_at=at,
                    source_witness=(
                        f"confirmed={(T-timedelta(minutes=15)).isoformat()};stop=98"
                    ),
                    independent_witness=(
                        f"confirmed={(T-timedelta(minutes=15)).isoformat()};"
                        "swing=98;swing_at=2026-01-05T00:30:00+00:00"
                    ),
                    provenance="independently_verified_native_m1_fixture",
                ),
                A1SourceSensorEvidence(
                    sensor="M1_PROTECTED_SWING_ATTESTATION",
                    status=ProofStatus.OBSERVED,
                    reason="EXACT_SOURCE_M1_PROTECTED",
                    observed_at=at,
                    source_witness=f"family={item.trade.trigger_family};at={at}",
                    independent_witness=f"confirmed={at};swing=98.5",
                    provenance="independently_verified_native_m1_fixture",
                ),
                A1SourceSensorEvidence(
                    sensor="H1_TARGET_ROOM_R",
                    status=ProofStatus.OBSERVED,
                    reason="CLOSED_H1_TARGET_UNTOUCHED",
                    observed_at=at,
                    source_witness="target=102;room_r=0.67",
                    independent_witness=(
                        f"target=102;confirmed={(T-timedelta(hours=1)).isoformat()}"
                    ),
                    provenance="independently_verified_native_m1_fixture",
                ),
                A1SourceSensorEvidence(
                    sensor="FULL_COGNITIVE_MASTER_FRAME",
                    status=ProofStatus.NOT_AVAILABLE,
                    reason="REQUIRES_NINE_MARKET_EVALUATION",
                    observed_at=at,
                    source_witness=None, independent_witness=None,
                    provenance="separately_evaluated_master_frame",
                ),
            ),
        )
    bridged = run_sensorized_master_frame_paper(
        barriers=(_a1_multi_hypothesis_fixture(T, source_ids=ids),),
        source_evidence=snapshots, source_originals=originals,
        baseline_selected_source_ids=ids,
        independent_source_witnesses=proof,
    )
    assert bridged.observed_sensor_frames == 3
    assert bridged.independently_validated_source_rows == 3
    assert bridged.independently_observed_market_sensors == 9
    assert bridged.full_master_frame_invoked
    assert bridged.report.paper_selected == 3
    assert not bridged.report.trader_certified
    assert not bridged.live_authorized
    with pytest.raises(ValueError, match="all original source IDs"):
        run_sensorized_master_frame_paper(
            barriers=(_a1_multi_hypothesis_fixture(T, source_ids=ids),),
            source_evidence=snapshots, source_originals=originals,
            baseline_selected_source_ids=ids,
            independent_source_witnesses={ids[0]: proof[ids[0]]},
        )


def test_prior_intact_m1_review_reaches_master_context_but_never_grants_source_veto() -> None:
    originals, snapshots = _inputs()
    ids = tuple(x.source_opportunity_id for x in originals)
    records: dict[str, A1M1ProtectedRouteReview] = {}
    for item in originals:
        records[item.source_opportunity_id] = A1M1ProtectedRouteReview(
            source_opportunity_id=item.source_opportunity_id,
            symbol=item.trade.symbol,
            source_family=item.trade.trigger_family,
            decision_at=T.isoformat(),
            strict_previous_attestation=ProofStatus.NOT_AVAILABLE,
            protection_class=M1ProtectionClass.PRIOR_CONFIRMED_INTACT,
            structurally_protected_at_entry=True,
            protected_price="98.5",
            protection_confirmed_at=(T-timedelta(minutes=1)).isoformat(),
            route_class=SourceRouteClass.SOURCE_ROUTE_CONFIRMED_AT_ENTRY,
            own_route_first_confirmed_at=T.isoformat(),
            other_route_first_confirmed_at=None,
        )
    result = run_sensorized_master_frame_paper(
        barriers=(_a1_multi_hypothesis_fixture(T, source_ids=ids),),
        source_evidence=snapshots,
        source_originals=originals,
        baseline_selected_source_ids=ids,
        m1_route_reviews=records,
    )
    assert result.causal_m1_route_reviews_received == 3
    assert result.prior_intact_m1_context_count == 3
    assert result.full_master_frame_invoked
    assert result.report.paper_selected == 3
    assert result.source_cisd_identity_conflicts == 0
    assert not result.automatically_vetoed_cisd_conflicts
    assert not result.live_authorized
    with pytest.raises(ValueError, match="all original source IDs need M1"):
        run_sensorized_master_frame_paper(
            barriers=(_a1_multi_hypothesis_fixture(T, source_ids=ids),),
            source_evidence=snapshots,
            source_originals=originals,
            baseline_selected_source_ids=ids,
            m1_route_reviews={ids[0]: records[ids[0]]},
        )
    false_id = {
        **records,
        ids[0]: replace(records[ids[0]], source_family=(
            "LIQUIDITY_SWEEP_CISD"
            if records[ids[0]].source_family == "FVG_RETRACE_CISD"
            else "FVG_RETRACE_CISD"
        )),
    }
    with pytest.raises(ValueError, match="M1 route forensic contradicts"):
        run_sensorized_master_frame_paper(
            barriers=(_a1_multi_hypothesis_fixture(T, source_ids=ids),),
            source_evidence=snapshots,
            source_originals=originals,
            baseline_selected_source_ids=ids,
            m1_route_reviews=false_id,
        )
    false_time = {
        **records,
        ids[0]: replace(
            records[ids[0]],
            own_route_first_confirmed_at=(T-timedelta(minutes=1)).isoformat(),
            route_class=SourceRouteClass.SOURCE_ROUTE_CONFIRMED_EARLIER,
        ),
    }
    with pytest.raises(ValueError, match="M1 route forensic contradicts"):
        run_sensorized_master_frame_paper(
            barriers=(_a1_multi_hypothesis_fixture(T, source_ids=ids),),
            source_evidence=snapshots,
            source_originals=originals,
            baseline_selected_source_ids=ids,
            m1_route_reviews=false_time,
        )


def test_second_confirmed_m1_pivot_reaches_true_master_context_not_trade_veto() -> None:
    originals, snapshots = _inputs()
    ids = tuple(x.source_opportunity_id for x in originals)
    first: dict[str, A1M1ProtectedRouteReview] = {}
    second: dict[str, A1SecondPivotReview] = {}
    for original in originals:
        sid = original.source_opportunity_id
        first[sid] = A1M1ProtectedRouteReview(
            source_opportunity_id=sid, symbol=original.trade.symbol,
            source_family=original.trade.trigger_family,
            decision_at=T.isoformat(),
            strict_previous_attestation=ProofStatus.NOT_AVAILABLE,
            protection_class=M1ProtectionClass.PRIOR_CONFIRMED_BREACHED,
            structurally_protected_at_entry=False,
            protected_price="98.5",
            protection_confirmed_at=(T-timedelta(minutes=3)).isoformat(),
            route_class=SourceRouteClass.SOURCE_ROUTE_CONFIRMED_AT_ENTRY,
            own_route_first_confirmed_at=T.isoformat(),
            other_route_first_confirmed_at=None,
        )
        second[sid] = A1SecondPivotReview(
            source_opportunity_id=sid, symbol=original.trade.symbol,
            source_family=original.trade.trigger_family,
            decision_at=T.isoformat(),
            previous_class=M1ProtectionClass.PRIOR_CONFIRMED_BREACHED,
            finding=SecondaryPivotClass.LATER_CONFIRMED_INTACT,
            distinct_pivots=2,
            later_intact=True,
            protected_price="98.8",
            swing_at=(T-timedelta(minutes=2)).isoformat(),
            confirmed_at=(T-timedelta(minutes=1)).isoformat(),
        )
    def invoke(
        route: dict[str, A1M1ProtectedRouteReview] | None,
        revised: dict[str, A1SecondPivotReview] | None,
    ) -> A1SensorizedPaperBridgeResult:
        return run_sensorized_master_frame_paper(
            barriers=(_a1_multi_hypothesis_fixture(T, source_ids=ids),),
            source_evidence=snapshots,
            source_originals=originals,
            baseline_selected_source_ids=ids,
            m1_route_reviews=route,
            m1_secondary_reviews=revised,
        )

    result = invoke(first, second)
    assert result.full_master_frame_invoked
    assert result.causal_m1_route_reviews_received == 3
    assert result.secondary_m1_route_reviews_received == 3
    assert result.newly_intact_second_m1_context_count == 3
    assert result.report.paper_selected == 3
    assert not result.automatically_vetoed_cisd_conflicts
    assert not result.live_authorized
    with pytest.raises(ValueError, match="need original V2 lineage"):
        invoke(None, second)
    with pytest.raises(ValueError, match="false source/V2 ancestry"):
        invoke(
            first,
            {
                **second,
                ids[0]: replace(
                    second[ids[0]],
                    previous_class=M1ProtectionClass.NO_CONFIRMED_STRUCTURAL_PIVOT,
                ),
            },
        )
    with pytest.raises(ValueError, match="need original V2 lineage"):
        invoke(first, {ids[0]: second[ids[0]]})


def test_actual_ny_source_clock_provenance_enters_master_paper_without_killzone_veto() -> None:
    originals, snapshots = _inputs()
    ids = tuple(x.source_opportunity_id for x in originals)
    clock_witnesses: dict[str, native_clock.A1V49SourceClockEvidence] = {}
    for row in originals:
        clock_witnesses[row.source_opportunity_id] = (
            native_clock.A1V49SourceClockEvidence(
                source_opportunity_id=row.source_opportunity_id,
                symbol=row.trade.symbol,
                source_session=CapitalizerSession.ASIA,
                source_operating_date=row.trade.operating_date,
                observed_at=T.isoformat(),
                m1_opened_at=(T - timedelta(minutes=1)).isoformat(),
                new_york_local_time="2026-01-04T20:00:00-05:00",
                new_york_utc_offset_minutes=-300,
                qore_bucket_reconfirmed=(
                    native_clock.ClockAttestationStatus.QORE_BUCKET_RECONFIRMED
                ),
                local_operating_day_reconfirmed=True,
                within_qore_research_session=True,
                remaining_session_seconds=6 * 3600,
                methodology_window_resolution=(
                    CapitalizerSourceSessionResolution.REVIEW_REQUIRED
                ),
                methodology_window_id="ICT_ASIAN_OPEN_REFERENCE_REQUIRED",
            )
        )
    result = run_sensorized_master_frame_paper(
        barriers=(_a1_multi_hypothesis_fixture(T, source_ids=ids),),
        source_evidence=snapshots,
        source_originals=originals,
        baseline_selected_source_ids=ids,
        source_clock_witnesses=clock_witnesses,
    )
    assert result.independently_attested_source_clocks == 3
    assert result.source_methodology_windows_unresolved == 3
    assert result.full_master_frame_invoked
    assert result.report.paper_selected == 3
    assert not result.automatically_vetoed_cisd_conflicts
    assert not result.live_authorized
    with pytest.raises(ValueError, match="all original source IDs need clock provenance"):
        run_sensorized_master_frame_paper(
            barriers=(_a1_multi_hypothesis_fixture(T, source_ids=ids),),
            source_evidence=snapshots, source_originals=originals,
            baseline_selected_source_ids=ids,
            source_clock_witnesses={ids[0]: clock_witnesses[ids[0]]},
        )
    with pytest.raises(ValueError, match="cannot cross V49 ancestry"):
        run_sensorized_master_frame_paper(
            barriers=(_a1_multi_hypothesis_fixture(T, source_ids=ids),),
            source_evidence=snapshots, source_originals=originals,
            baseline_selected_source_ids=ids,
            source_clock_witnesses={
                **clock_witnesses,
                ids[0]: replace(
                    clock_witnesses[ids[0]], source_operating_date="2024-01-01"
                ),
            },
        )
