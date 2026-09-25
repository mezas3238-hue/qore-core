from datetime import UTC, datetime, timedelta

from qore.infrastructure.ctrader_demo_live_behavior_lab import (
    BehaviorStage,
    CTraderDemoLiveBehaviorLedger,
    build_case_reports,
    classify_stage,
    management_observation_payload,
    normalize_runtime_event,
    position_path_observation_payload,
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



def test_position_path_samples_measure_favorable_adverse_and_protection_history():
    signal = "e" * 64
    samples = (
        position_path_observation_payload(
            trader="VT31_NAS100",
            symbol="NAS100",
            signal_fingerprint=signal,
            position_id=202,
            side="long",
            entry_price=Decimal("100"),
            bid=Decimal("102"),
            ask=Decimal("102.2"),
            stop_loss=Decimal("99"),
            take_profit=Decimal("105"),
            volume=Decimal("1"),
            unrealized_pnl=Decimal("20"),
            observed_at=NOW,
        ),
        position_path_observation_payload(
            trader="VT31_NAS100",
            symbol="NAS100",
            signal_fingerprint=signal,
            position_id=202,
            side="long",
            entry_price=Decimal("100"),
            bid=Decimal("98.5"),
            ask=Decimal("98.7"),
            stop_loss=Decimal("100"),
            take_profit=Decimal("105"),
            volume=Decimal("0.5"),
            unrealized_pnl=Decimal("-15"),
            observed_at=NOW + timedelta(seconds=1),
        ),
    )
    events = tuple(
        normalize_runtime_event(sample, source="runtime")
        for sample in samples
    )

    report = build_case_reports(events)[0]

    assert report.path_sample_count == 2
    assert report.max_unrealized_pnl == "20"
    assert report.min_unrealized_pnl == "-15"
    assert report.max_favorable_price_delta == "2"
    assert report.max_adverse_price_delta == "-1.5"
    assert report.stop_history == ("99", "100")
    assert report.volume_history == ("1", "0.5")


def test_position_path_preserves_zero_missing_protection():
    payload = position_path_observation_payload(
        trader="R34_XAUUSD",
        symbol="XAUUSD",
        signal_fingerprint="f" * 64,
        position_id=303,
        side="short",
        entry_price=Decimal("4000"),
        bid=Decimal("3998"),
        ask=Decimal("3999"),
        stop_loss=Decimal("0"),
        take_profit=Decimal("0"),
        volume=Decimal("0.01"),
        unrealized_pnl=Decimal("1.25"),
        observed_at=NOW,
    )

    assert payload["stop_loss"] == "0"
    assert payload["take_profit"] == "0"
    assert payload["directional_price_delta"] == "1"
