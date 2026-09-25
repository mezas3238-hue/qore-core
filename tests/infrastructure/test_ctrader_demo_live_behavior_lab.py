from datetime import UTC, datetime, timedelta

from qore.infrastructure.ctrader_demo_live_behavior_lab import (
    BehaviorStage,
    CTraderDemoLiveBehaviorLedger,
    build_case_reports,
    classify_stage,
    management_observation_payload,
    normalize_runtime_event,
    sizing_path_for,
)


NOW = datetime(2026, 9, 25, 15, 0, tzinfo=UTC)


def test_behavior_ledger_round_trip_is_append_only(tmp_path):
    ledger = CTraderDemoLiveBehaviorLedger(tmp_path / "behavior.jsonl")
    first = ledger.record_raw(
        {
            "event": "VT31_CANDIDATE",
            "trader": "VT31_NAS100",
            "symbol": "NAS100",
            "signal_fingerprint": "a" * 64,
            "decision_at_utc": NOW.isoformat(),
        },
        source="runtime",
    )
    second = ledger.record_raw(
        {
            "event": "CTRADER_DEMO_FREE_EXECUTION",
            "trader": "VT31_NAS100",
            "symbol": "NAS100",
            "signal_fingerprint": "a" * 64,
            "requested_volume": "1.0",
            "recorded_at": (NOW + timedelta(seconds=1)).isoformat(),
        },
        source="sink",
    )

    rows = ledger.events()

    assert rows == (first, second)
    assert rows[0].case_id == rows[1].case_id == f"signal:{'a' * 64}"
    assert rows[0].stage is BehaviorStage.SIGNAL
    assert rows[1].stage is BehaviorStage.EXECUTION


def test_vt31_case_reports_missing_cibo_and_protection_as_observation_not_failure():
    signal = "b" * 64
    events = (
        normalize_runtime_event(
            {
                "event": "CTRADER_DEMO_FREE_EXECUTION",
                "trader": "VT31_NAS100",
                "symbol": "NAS100",
                "signal_fingerprint": signal,
                "requested_volume": "1.0",
                "recorded_at": NOW.isoformat(),
            },
            source="runtime",
        ),
        normalize_runtime_event(
            {
                "event": "VT31_NAS100_DEMO_FILL_CONFIRMED",
                "trader": "VT31_NAS100",
                "symbol": "NAS100",
                "signal_fingerprint": signal,
                "position_ticket": 99,
                "filled_at": (NOW + timedelta(seconds=2)).isoformat(),
            },
            source="runtime",
        ),
        normalize_runtime_event(
            {
                "event": "VT31_NAS100_POSITION_CLOSED_RECONCILED",
                "trader": "VT31_NAS100",
                "symbol": "NAS100",
                "signal_fingerprint": signal,
                "logged_at": (NOW + timedelta(minutes=20)).isoformat(),
            },
            source="runtime",
        ),
    )

    report = build_case_reports(events)[0]

    assert report.requested_volumes == ("1.0",)
    assert "no_explicit_cibo_sizing_event_observed_for_vt31" in report.observations
    assert "position_exited_without_observed_protection_event" in report.observations
    assert report.fault_events == ()


def test_vt31_protection_event_is_preserved_in_same_case():
    signal = "c" * 64
    events = (
        normalize_runtime_event(
            {
                "event": "VT31_NAS100_DEMO_FILL_CONFIRMED",
                "trader": "VT31_NAS100",
                "symbol": "NAS100",
                "signal_fingerprint": signal,
                "position_ticket": 101,
                "filled_at": NOW.isoformat(),
            },
            source="runtime",
        ),
        normalize_runtime_event(
            {
                "event": "VT31_NAS100_BASE_BE_ADVANCED",
                "trader": "VT31_NAS100",
                "symbol": "NAS100",
                "signal_fingerprint": signal,
                "stop": "30670.0",
                "logged_at": (NOW + timedelta(minutes=2)).isoformat(),
            },
            source="runtime",
        ),
        normalize_runtime_event(
            {
                "event": "VT31_NAS100_POSITION_CLOSED_RECONCILED",
                "trader": "VT31_NAS100",
                "symbol": "NAS100",
                "signal_fingerprint": signal,
                "logged_at": (NOW + timedelta(minutes=30)).isoformat(),
            },
            source="runtime",
        ),
    )

    report = build_case_reports(events)[0]

    assert report.protection_events == ("VT31_NAS100_BASE_BE_ADVANCED",)
    assert "position_exited_without_observed_protection_event" not in report.observations


def test_stage_classifier_keeps_management_distinct_from_execution():
    assert classify_stage("VT31_NAS100_PS2_STOP_ADVANCED") is BehaviorStage.MANAGEMENT
    assert classify_stage("VT31_NAS100_DOL1_QUARTER_BANKED") is BehaviorStage.MANAGEMENT
    assert classify_stage("CTRADER_DEMO_FREE_SUBMIT") is BehaviorStage.EXECUTION
    assert classify_stage("RISK_REJECT_MINIMUM_BROKER_VOLUME") is BehaviorStage.FAULT



def test_management_observation_is_passive_and_preserves_vt31_state():
    class Opened:
        signal_fingerprint = "d" * 64
        client_order_id = "qore-vt31-1"
        current_stop = "30670"
        initial_stop = "30620"
        base_runner_be_active = True
        runner_active = False
        ps_confirmations = 1

    class State:
        open_trade = Opened()

    payload = management_observation_payload(
        trader="VT31_NAS100",
        symbol="NAS100",
        state=State(),
        reason="vt31-base-runner-hold",
        observed_at=NOW,
    )

    assert payload["event"] == "CTRADER_DEMO_MANAGEMENT_OBSERVATION"
    assert payload["signal_fingerprint"] == "d" * 64
    assert payload["base_runner_be_active"] is True
    assert payload["runner_active"] is False
    assert payload["ps_confirmations"] == 1
    assert (
        sizing_path_for("VT31_NAS100")
        == "VT31_CERTIFIED_RISK_RESOLUTION_THEN_DEMO_NATIVE_VOLUME"
    )
