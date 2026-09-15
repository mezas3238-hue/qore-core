from qore.infrastructure.trader_lab.turtle_soup_candidate_r5_classic_tick_wave2_targets import (
    frozen_wave2_tick_target_manifest,
)


def test_r5_wave2_is_frozen_to_20_causally_exposed_pre_oos_minutes() -> None:
    manifest = frozen_wave2_tick_target_manifest()
    assert manifest["manifest_digest_sha256"] == (
        "839714b3be5a461d0994bb5c5d155b100ac41aae28cd471c509f3c202a092290"
    )
    assert manifest["target_count"] == 20
    assert manifest["m1_data_unavailable_count"] == 0
    targets = manifest["targets"]
    assert {symbol: len(rows) for symbol, rows in targets.items()} == {
        "EURUSD": 1,
        "GBPUSD": 6,
        "USDJPY": 1,
        "AUDUSD": 2,
        "USDCAD": 2,
        "GBPJPY": 4,
        "AUDJPY": 4,
    }
