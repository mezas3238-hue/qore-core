from qore.infrastructure.trader_lab.capitalizer_ict_source_binding_status_v48 import (
    SOURCES,
    V48_ICT_SOURCE_BINDING_STATUS,
    V48ICTBindingState,
)


def test_all_ict_sources_require_exact_timestamp_binding_before_v48_productive_use() -> None:
    assert SOURCES
    for source in SOURCES:
        assert source.video_state is V48ICTBindingState.PRIMARY_VIDEO_ID_VERIFIED
        assert source.timestamp_state is V48ICTBindingState.TIMESTAMP_BINDING_REQUIRED
        assert source.productive_hard_gate_authorized is False


def test_ict_timestamp_gap_is_local_block_not_program_stop() -> None:
    status = V48_ICT_SOURCE_BINDING_STATUS
    assert status.exact_timestamp_binding_required is True
    assert status.partial_source_block_blocks_ttrades_reconstruction is False
    assert status.fresh_holdout_authorized is False
