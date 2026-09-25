from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r133_shared_r75_density_attribution as r133,
)


def test_r133_source_r132_is_pinned() -> None:
    assert r133.SOURCE_R132_RUN_ID == 36174146167
    assert r133.SOURCE_R132_ARTIFACT_ID == 10881626079
    assert r133.SOURCE_R132_ARTIFACT_DIGEST == (
        "sha256:346dc6605d59203b6069fb9a00434dc"
        "9c9eb696cf5b18b1a7d348ee9417dadfc"
    )


def test_r133_transport_sample_floor_is_frozen() -> None:
    assert r133.MIN_TRANSPORT_SAMPLE == 10
