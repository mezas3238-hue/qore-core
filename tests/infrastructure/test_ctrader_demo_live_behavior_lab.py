from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.ctrader_demo_live_behavior_lab import (
    BehaviorStage,
    CTraderDemoLiveBehaviorLedger,
    build_case_reports,
    classify_stage,
    management_observation_payload,
    normalize_runtime_event,
    position_path_observation_payload,
    settlement_observation_payload,
    sizing_path_for,
)

NOW = datetime(2026, 9, 25, 15, 0, tzinfo=UTC)


def test_behavior_ledger_round_trip_is_append_only(tmp_path: Path) -> None:
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


def test_vt31_case_reports_missing_cibo_and_protection_as_observation_not_failure() -> None:
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


def test_vt31_protection_event_is_preserved_in_same_case() -> None:
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


def test_stage_classifier_keeps_management_distinct_from_execution() -> None:
    assert classify_stage("VT31_NAS100_PS2_STOP_ADVANCED") is BehaviorStage.MANAGEMENT
    assert classify_stage("VT31_NAS100_DOL1_QUARTER_BANKED") is BehaviorStage.MANAGEMENT
    assert classify_stage("CTRADER_DEMO_FREE_SUBMIT") is BehaviorStage.EXECUTION
    assert classify_stage("RISK_REJECT_MINIMUM_BROKER_VOLUME") is BehaviorStage.FAULT



def test_management_observation_is_passive_and_preserves_vt31_state() -> None:
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



def test_position_path_samples_measure_favorable_adverse_and_protection_history() -> None:
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


def test_position_path_preserves_zero_missing_protection() -> None:
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



def test_settlement_evidence_reports_realized_pnl_and_prices() -> None:
    signal = "9" * 64
    partial = settlement_observation_payload(
        trader="VT31_NAS100",
        symbol="NAS100",
        signal_fingerprint=signal,
        position_id=404,
        deal_id=501,
        order_id=601,
        side="short",
        execution_price=Decimal("30612.5"),
        filled_units=Decimal("0.20"),
        source_volume=Decimal("0.02"),
        net_profit=Decimal("28.86"),
        gross_profit=Decimal("28.86"),
        commission=Decimal("0"),
        swap=Decimal("0"),
        pnl_conversion_fee=Decimal("0"),
        balance_after=Decimal("1000018.27"),
        executed_at=NOW,
        position_open_after=True,
    )
    exit_row = settlement_observation_payload(
        trader="VT31_NAS100",
        symbol="NAS100",
        signal_fingerprint=signal,
        position_id=404,
        deal_id=502,
        order_id=602,
        side="short",
        execution_price=Decimal("30644.8"),
        filled_units=Decimal("0.20"),
        source_volume=Decimal("0.02"),
        net_profit=Decimal("35.32"),
        gross_profit=Decimal("35.32"),
        commission=Decimal("0"),
        swap=Decimal("0"),
        pnl_conversion_fee=Decimal("0"),
        balance_after=Decimal("1000053.59"),
        executed_at=NOW + timedelta(minutes=1),
        position_open_after=False,
    )

    reports = build_case_reports(
        (
            normalize_runtime_event(partial, source="settlement"),
            normalize_runtime_event(exit_row, source="settlement"),
        )
    )
    report = reports[0]

    assert report.settlement_events == (
        "CTRADER_DEMO_PARTIAL_SETTLEMENT",
        "CTRADER_DEMO_EXIT_SETTLEMENT",
    )
    assert report.realized_net_pnl == "64.18"
    assert report.settlement_prices == ("30612.5", "30644.8")
    assert report.settled_source_volumes == ("0.02",)
    assert classify_stage("CTRADER_DEMO_PARTIAL_SETTLEMENT") is BehaviorStage.MANAGEMENT
    assert classify_stage("CTRADER_DEMO_EXIT_SETTLEMENT") is BehaviorStage.EXIT



def test_economic_floor_combines_realized_partial_and_remaining_stop() -> None:
    signal = "8" * 64
    submit = normalize_runtime_event(
        {
            "event": "CTRADER_DEMO_FREE_SUBMIT",
            "trader": "VT31_NAS100",
            "symbol": "NAS100",
            "signal_fingerprint": signal,
            "requested_volume": "0.04",
            "requested_stop_risk": "26.0712",
            "recorded_at": NOW.isoformat(),
        },
        source="sink",
    )
    first_path = normalize_runtime_event(
        position_path_observation_payload(
            trader="VT31_NAS100",
            symbol="NAS100",
            signal_fingerprint=signal,
            position_id=707,
            side="long",
            entry_price=Decimal("30468.2"),
            bid=Decimal("30600.0"),
            ask=Decimal("30600.9"),
            stop_loss=Decimal("30404.6"),
            take_profit=Decimal("30684.0"),
            volume=Decimal("0.04"),
            unrealized_pnl=Decimal("52.72"),
            observed_at=NOW + timedelta(seconds=1),
        ),
        source="runtime",
    )
    partial = normalize_runtime_event(
        settlement_observation_payload(
            trader="VT31_NAS100",
            symbol="NAS100",
            signal_fingerprint=signal,
            position_id=707,
            deal_id=801,
            order_id=901,
            side="short",
            execution_price=Decimal("30612.5"),
            filled_units=Decimal("0.20"),
            source_volume=Decimal("0.02"),
            net_profit=Decimal("28.86"),
            gross_profit=Decimal("28.86"),
            commission=Decimal("0"),
            swap=Decimal("0"),
            pnl_conversion_fee=Decimal("0"),
            balance_after=Decimal("1000018.27"),
            executed_at=NOW + timedelta(seconds=2),
            position_open_after=True,
        ),
        source="settlement",
    )
    latest_path = normalize_runtime_event(
        position_path_observation_payload(
            trader="VT31_NAS100",
            symbol="NAS100",
            signal_fingerprint=signal,
            position_id=707,
            side="long",
            entry_price=Decimal("30468.2"),
            bid=Decimal("30598.2"),
            ask=Decimal("30599.1"),
            stop_loss=Decimal("30404.6"),
            take_profit=Decimal("30684.0"),
            volume=Decimal("0.02"),
            unrealized_pnl=Decimal("26.00"),
            observed_at=NOW + timedelta(seconds=3),
        ),
        source="runtime",
    )

    report = build_case_reports((submit, first_path, partial, latest_path))[0]

    assert Decimal(report.estimated_initial_risk_pnl or "0") == Decimal("25.44")
    assert Decimal(report.estimated_remaining_stop_pnl or "0") == Decimal("-12.72")
    assert Decimal(report.estimated_economic_floor_pnl or "0") == Decimal("16.14")
    assert Decimal(report.estimated_economic_floor_r or "0") > Decimal("0.63")
    assert "estimated_economic_floor_pnl=16.14" in report.observations
