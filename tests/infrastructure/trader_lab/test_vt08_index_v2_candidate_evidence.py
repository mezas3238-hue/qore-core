import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.vt08_index_v2_candidate import (
    PRIMARY_SOURCE_SHA256,
    Vt08IndexV2CandidateError,
    _load_candidate_market,
)


def _evidence(path: Path, software_sha: str) -> None:
    payload = {
        "schema": "qore.ctrader_demo.vt08_crt_h4_amd_v2_evidence.v3",
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "canonical_symbol": "NAS100",
        "provider_symbol_name": "USTEC",
        "software_sha": software_sha,
        "account_fingerprint": "a" * 64,
        "checked_at": "2024-08-13T00:15:00+00:00",
        "primary_source_sha256": PRIMARY_SOURCE_SHA256,
        "periods": {
            "M15": [
                {
                    "period": "M15",
                    "opened_at": "2024-08-13T00:00:00+00:00",
                    "closed_at": "2024-08-13T00:15:00+00:00",
                    "open": "100",
                    "high": "101",
                    "low": "99",
                    "close": "100.5",
                }
            ]
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_fresh_acquisition_sha_is_verified_without_rewriting(tmp_path: Path) -> None:
    path = tmp_path / "market.json"
    software_sha = "b" * 40
    _evidence(path, software_sha)
    fingerprint, provider, _checked_at, bars = _load_candidate_market(
        path,
        expected_symbol="NAS100",
        expected_software_sha=software_sha,
        minimum_evidence_days=0,
    )
    assert fingerprint == "a" * 64
    assert provider == "USTEC"
    assert len(bars) == 1


def test_fresh_acquisition_sha_drift_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "market.json"
    _evidence(path, "b" * 40)
    with pytest.raises(Vt08IndexV2CandidateError):
        _load_candidate_market(
            path,
            expected_symbol="NAS100",
            expected_software_sha="c" * 40,
            minimum_evidence_days=0,
        )
