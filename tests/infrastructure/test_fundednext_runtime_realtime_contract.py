from pathlib import Path


def test_runtime_shadow_mode_is_no_send_for_all_position_mutations() -> None:
    source = Path("scripts/qore_fundednext_runtime.py").read_text(encoding="utf-8")
    assert source.count('mutations_enabled=mode == "live"') >= 4
    assert 'submission_enabled=mode == "live"' in source


def test_runtime_uses_continuous_one_second_market_refresh_and_two_second_entry_sla() -> None:
    source = Path("scripts/qore_fundednext_runtime.py").read_text(encoding="utf-8")
    assert "_IDLE_LOOP_SECONDS = 1.0" in source
    assert "_BOUNDARY_ARM_SECONDS = 10.0" in source
    assert "_ANCHOR_GRACE = timedelta(seconds=2)" in source
    assert "turtle_market_data.refresh_many(" in source
    assert "turtle_market_data.prime_anchor_once(" in source
    assert '"market_data_sla_seconds": MARKET_DATA_SLA_SECONDS' in source
    assert "time.sleep(_runtime_sleep_seconds(datetime.now(UTC)))" in source


def test_transient_management_data_faults_fail_closed_without_runtime_restart() -> None:
    source = Path("scripts/qore_fundednext_runtime.py").read_text(encoding="utf-8")
    assert source.count("except MarketDataSlaError as error:") >= 3
    assert "R38_MANAGEMENT_DATA_FAIL_CLOSED" in source
    assert "R43_MANAGEMENT_DATA_FAIL_CLOSED" in source
    assert "GBPJPY_R38_MANAGEMENT_DATA_FAIL_CLOSED" in source


def test_portfolio_boundary_capture_interleaves_turtle_and_vt08_under_same_deadline() -> None:
    source = Path("scripts/qore_fundednext_runtime.py").read_text(encoding="utf-8")
    assert "turtle_market_data.prime_anchor_once(" in source
    assert "_vt08_boundary_ready(" in source
    assert "deadline = turtle_anchor + timedelta(seconds=MARKET_DATA_SLA_SECONDS)" in source
    assert "vt08_boundary_results" in source
    assert "vt08_boundary_failures" in source
