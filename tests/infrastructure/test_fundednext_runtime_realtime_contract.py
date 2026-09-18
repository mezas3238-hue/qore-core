from pathlib import Path


def test_runtime_shadow_mode_is_no_send_for_all_position_mutations() -> None:
    source = Path("scripts/qore_fundednext_runtime.py").read_text(encoding="utf-8")
    assert source.count('mutations_enabled=mode == "live"') >= 4
    assert 'submission_enabled=mode == "live"' in source


def test_runtime_uses_continuous_one_second_market_refresh_and_two_second_entry_sla() -> None:
    source = Path("scripts/qore_fundednext_runtime.py").read_text(encoding="utf-8")
    assert "_IDLE_LOOP_SECONDS = 1.0" in source
    assert "turtle_market_data.refresh_many(" in source
    assert "turtle_market_data.prime_anchor_group(" in source
    assert '"market_data_sla_seconds": MARKET_DATA_SLA_SECONDS' in source
    assert "time.sleep(_runtime_sleep_seconds(datetime.now(UTC)))" in source
