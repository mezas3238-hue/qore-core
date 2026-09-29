from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab import (
    capitalizer_native_source_provider_time_coverage_v46 as phase_b,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession


def test_phase_b_asian_session_uses_r3_provenance_not_synthetic() -> None:
    winter = datetime(2024, 1, 15, 1, 0, tzinfo=UTC)
    summer = datetime(2024, 7, 15, 1, 0, tzinfo=UTC)

    winter_assessment, winter_reference = phase_b._session_assessment(
        session=CapitalizerSession.ASIA,
        decision_at=winter,
    )
    summer_assessment, summer_reference = phase_b._session_assessment(
        session=CapitalizerSession.ASIA,
        decision_at=summer,
    )

    assert winter_assessment.eligible is True
    assert summer_assessment.eligible is True
    assert winter_reference is not None
    assert summer_reference is not None
    assert winter_reference.synthetic is False
    assert summer_reference.synthetic is False
    assert winter_reference.reference_at.hour == 0
    assert summer_reference.reference_at.hour == 0


def test_phase_b_coverage_row_passes_only_with_complete_causal_history() -> None:
    spec = phase_b.PeriodSpec(
        "test",
        "TEST_PERIOD",
        datetime(2024, 1, 22, tzinfo=UTC),
        datetime(2024, 1, 23, tzinfo=UTC),
    )
    state = phase_b._PeriodState(spec)
    decision = datetime(2024, 1, 22, 8, 0, tzinfo=UTC)
    state.earliest_artifact_at = spec.lookback_start
    state.source_rows = 100
    state.lookback_rows = 100
    state.first_source_at = spec.start
    state.last_source_at = spec.end
    assert state.eligible_clocks is not None
    assert state.h1_completed is not None
    assert state.m15_completed is not None
    state.eligible_clocks.extend((decision, decision + timedelta(minutes=1)))
    state.h1_completed.append(decision - timedelta(minutes=30))
    state.m15_completed.append(decision - timedelta(minutes=5))

    row = phase_b._coverage_row(
        state,
        symbol="EURUSD",
        session=CapitalizerSession.LONDON,
    )

    assert row["hard_gate_passed"] is True
    assert row["h1_m15_causal_history_coverage"] == "1"
    assert row["missing_history_clocks"] == 0
    assert row["future_bar_count"] == 0
    assert row["synthetic_source_fact_count"] == 0


def test_phase_b_missing_history_stays_in_denominator_and_fails() -> None:
    spec = phase_b.PeriodSpec(
        "test",
        "TEST_PERIOD",
        datetime(2024, 1, 22, tzinfo=UTC),
        datetime(2024, 1, 23, tzinfo=UTC),
    )
    state = phase_b._PeriodState(spec)
    decision = datetime(2024, 1, 22, 8, 0, tzinfo=UTC)
    state.earliest_artifact_at = spec.lookback_start
    assert state.eligible_clocks is not None
    assert state.m15_completed is not None
    state.eligible_clocks.append(decision)
    state.m15_completed.append(decision - timedelta(minutes=5))

    row = phase_b._coverage_row(
        state,
        symbol="EURUSD",
        session=CapitalizerSession.LONDON,
    )

    assert row["hard_gate_passed"] is False
    assert row["eligible_source_session_decision_clocks"] == 1
    assert row["missing_history_clocks"] == 1
    assert row["h1_m15_causal_history_coverage"] == "0"


def test_phase_b_contract_never_opens_economics() -> None:
    spec = phase_b.PeriodSpec(
        "test",
        "TEST_PERIOD",
        datetime(2024, 1, 22, tzinfo=UTC),
        datetime(2024, 1, 23, tzinfo=UTC),
    )
    state = phase_b._PeriodState(spec)
    decision = datetime(2024, 1, 22, 8, 0, tzinfo=UTC)
    state.earliest_artifact_at = spec.lookback_start
    assert state.eligible_clocks is not None
    assert state.h1_completed is not None
    assert state.m15_completed is not None
    state.eligible_clocks.append(decision)
    state.h1_completed.append(decision - timedelta(minutes=30))
    state.m15_completed.append(decision - timedelta(minutes=5))

    row = phase_b._coverage_row(
        state,
        symbol="EURUSD",
        session=CapitalizerSession.LONDON,
    )

    assert row["outcomes_read"] is False
    assert row["realized_r_read"] is False
    assert row["exit_read"] is False
    assert row["mae_mfe_read"] is False
    assert row["fixed_2r_used"] is False
    assert row["fresh_holdout_opened"] is False
    assert row["candidate_count"] == 0
    assert row["trader_certified"] is False
