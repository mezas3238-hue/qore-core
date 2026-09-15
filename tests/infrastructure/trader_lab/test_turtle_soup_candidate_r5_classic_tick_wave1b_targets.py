from qore.infrastructure.trader_lab.turtle_soup_candidate_r5_classic_tick_wave1b_targets import (
    frozen_wave1b_tick_target_manifest,
)


def test_r5_wave1b_restores_only_two_omitted_pre_oos_targets() -> None:
    manifest = frozen_wave1b_tick_target_manifest()
    assert manifest["manifest_digest_sha256"] == (
        "cb22a2ece84238492f526247295c4c0ee5ede01a1827f0a9a42b45f6943c64be"
    )
    assert manifest["target_count"] == 2
    assert manifest["m1_data_unavailable_count"] == 0
    assert manifest["targets"] == {
        "GBPUSD": [
            {
                "minute_opened_at": "2024-04-10T15:45:00+00:00",
                "side": "long",
            }
        ],
        "USDCAD": [
            {
                "minute_opened_at": "2025-07-29T12:05:00+00:00",
                "side": "short",
            }
        ],
    }
