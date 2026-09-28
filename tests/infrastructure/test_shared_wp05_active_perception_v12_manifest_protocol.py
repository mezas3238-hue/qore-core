from __future__ import annotations

from pathlib import Path


def test_v12_manifest_extractor_cannot_select_on_matured_targets() -> None:
    source = Path(
        "scripts/shared_wp05_active_perception_v12_acquisition_manifest.py"
    ).read_text(encoding="utf-8")

    forbidden = (
        "terminal_failure",
        "relabel_partition_with_structural_failure_v2",
        "_terminal_failure(",
        "TARGET_HORIZON_MINUTES",
        "r6-nas",
        "r5-nas",
    )
    for token in forbidden:
        assert token not in source


def test_v12_manifest_extractor_is_r8_source_only_and_non_authoritative() -> None:
    source = Path(
        "scripts/shared_wp05_active_perception_v12_acquisition_manifest.py"
    ).read_text(encoding="utf-8")

    assert '"r8_only": True' in source
    assert '"r6_r5_read": False' in source
    assert '"fresh_holdout_opened": False' in source
    assert '"shared_order_authority": False' in source
    assert '"shared_execution_authority": False' in source
