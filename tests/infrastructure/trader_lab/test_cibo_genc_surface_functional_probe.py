from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding

LEDGER = Path("docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json")
EXPECTED = tuple(f"GEN-C{index}" for index in range(2, 15))


def _tag(candidate: TraderLabCandidateBinding, suffix: str) -> str:
    return f"trader-lab:{candidate.fingerprint.value}:{suffix}"


def test_trader_lab_genc_surface_binds_exact_c2_c14_and_executable_evidence(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=980)
    payload = json.loads(LEDGER.read_text(encoding="utf-8"))
    rows = tuple(
        row
        for row in payload["workstreams"]
        if row["id"] in EXPECTED
    )

    assert tuple(row["id"] for row in rows) == EXPECTED
    assert len(rows) == 13
    assert _tag(candidate, "GEN-C2-GEN-C14")

    for row in rows:
        refs = tuple(str(ref) for ref in row.get("evidence_refs", ()))
        source_refs = tuple(ref for ref in refs if ref.startswith("src/"))
        test_refs = tuple(ref for ref in refs if ref.startswith("tests/"))

        assert source_refs, f"{row['id']} has no executable source evidence"
        assert test_refs, f"{row['id']} has no behavioral test evidence"
        assert all(Path(ref).is_file() for ref in source_refs), row["id"]
        assert all(Path(ref).is_file() for ref in test_refs), row["id"]
        assert row["mandatory"] is True
        assert row["certification_blocking"] is True
