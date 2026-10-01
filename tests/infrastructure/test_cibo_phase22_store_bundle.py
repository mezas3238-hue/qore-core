from pathlib import Path

import pytest

from qore.infrastructure.cibo_phase22_store_bundle import (
    build_phase22_store_bundle,
)


def test_phase22_bundle_uses_five_disjoint_pristine_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "phase22-v2-stores"
    bundle = build_phase22_store_bundle(root)

    bundle.assert_pristine()
    assert len(bundle.paths) == 5
    assert len(set(bundle.paths)) == 5
    assert all(path.parent == root for path in bundle.paths)
    payload = bundle.contract_payload()
    assert payload["canonical_semantics_reused"] is True
    assert payload["physical_store_reused"] is False
    assert payload["phase20_paths_reused"] is False
    assert payload["fresh_outcomes_executed"] is False


def test_phase22_bundle_rejects_wrong_namespace(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must end with"):
        build_phase22_store_bundle(tmp_path / "phase20d-stores")


def test_phase22_bundle_rejects_preexisting_file(tmp_path: Path) -> None:
    root = tmp_path / "phase22-v2-stores"
    root.mkdir()
    (root / "holdout-policy.json").write_text("{}\n", encoding="utf-8")
    bundle = build_phase22_store_bundle(root)

    with pytest.raises(ValueError, match="not pristine"):
        bundle.assert_pristine()
