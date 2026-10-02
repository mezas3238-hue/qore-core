from pathlib import Path

from scripts.cibo_phase20_arch_b_forward_economic_manifest import (
    load_arch_b_forward_manifest,
    manifest_payload,
)


def test_empty_durable_books_export_fail_closed_manifest(tmp_path: Path) -> None:
    manifest = load_arch_b_forward_manifest(
        forward_store_path=tmp_path / "forward.json",
        policy_store_path=tmp_path / "policy.json",
        executed_risk_store_path=tmp_path / "risk.json",
        settlement_store_path=tmp_path / "settlement.json",
        release_store_path=tmp_path / "release.json",
    )
    payload = manifest_payload(manifest)

    assert manifest.ready_for_scientific_consumption is False
    assert manifest.certification_ready is False
    assert manifest.productive_authority is False
    assert payload["qualification_status"] == "NOT_READY"
    assert payload["rows"] == []
    assert str(payload["manifest_sha256"]).startswith("sha256:")
