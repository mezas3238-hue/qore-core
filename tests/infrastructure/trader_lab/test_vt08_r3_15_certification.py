from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.candidate import TraderLabValidationError
from qore.infrastructure.trader_lab.lifecycle import MANDATORY_STAGES
from qore.infrastructure.trader_lab.stage_evidence import TraderLabStage
from qore.infrastructure.trader_lab.vt08_r3_15_artifact_evidence import (
    R312_RISK_ARTIFACT,
    R315_HOLDOUT_ARTIFACT,
    Vt08R315ArtifactEvidence,
)
from qore.infrastructure.trader_lab.vt08_r3_15_certification import (
    METHODOLOGY_FINGERPRINT,
    SOURCE_CONTRACT_FINGERPRINT,
    Vt08R315CertificationError,
    _candidate,
    certify_vt08_r315,
)
from qore.infrastructure.vt08_r3_15_governed_authorities import (
    Vt08R315AuthorityError,
)

_CERTIFIED_AT = datetime(2026, 9, 13, 17, 0, tzinfo=UTC)


def _payloads() -> tuple[dict[str, object], ...]:
    holdout: dict[str, object] = {
        "schema": "qore.vt08.r3.15.final-independent-holdout.v1",
        "holdout_id": "VT08_R3_15_FINAL_INDEPENDENT_2020_2022",
        "software_sha": "64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222",
        "methodology_fingerprint": METHODOLOGY_FINGERPRINT,
        "portfolio": "B_COMBINED",
        "sample_size": 124,
        "wins": 57,
        "losses": 67,
        "flats": 0,
        "max_losing_streak": 7,
        "independent_validation": True,
        "methodology_mutation_after_holdout": False,
        "live_authorized": False,
        "win_rate": "0.4596774193548387096774193548",
        "profit_factor": "1.196270253543172529737553595",
        "compounded_return": "0.015898649288157281707521779",
        "maximum_drawdown": "0.01837083102440645070088295985",
        "population_variance": "0.000003229064513282220060032071879",
        "risk_policy": {
            "approved": True,
            "max_population_variance": "0.01",
            "min_sample_size": 30,
            "policy_id": "vt08-r315-final-demo-v1",
        },
    }
    adaptive: dict[str, object] = {
        "holdout_not_accessed": True,
        "risk_policy_fingerprint": (
            "dfb3fc8217b9895356ed19f8d7e1ee47fae765d39a9bb2e72e14c4ac41fad1f5"
        ),
        "primary_policy": {
            "name": "balanced-adaptive-v1",
            "a_base_bps": "25",
            "gbpjpy_base_bps": "20",
        },
    }
    monte_carlo: dict[str, object] = {
        "original_sample": 229,
        "primary_0_50bp": {
            "any_prop_firm_breach_probability": 0.0,
            "maximum_drawdown": {"p99": 0.03151683788407168},
        },
    }
    two_phase: dict[str, object] = {
        "schema": "qore.vt08.r3.14.two-phase-funding-qualification.v1",
        "git_sha": "266fa60df2654ffcbce3a89569295bb19f791022",
        "classification": "CONSUMED-DATA RESEARCH ONLY",
        "selection_status": "SAFE_BUT_LOW_60D_COMPLETION",
        "demo_eligible": False,
        "independent_validation": False,
        "holdout_not_accessed": True,
        "live_authorized": False,
        "methodology_fingerprints": [METHODOLOGY_FINGERPRINT],
        "source_contract_fingerprints": [SOURCE_CONTRACT_FINGERPRINT],
    }
    return holdout, adaptive, monte_carlo, two_phase


def _write(path: Path, value: dict[str, object]) -> Path:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return path


def _certify(tmp_path: Path, payloads: tuple[dict[str, object], ...]) -> dict[str, object]:
    holdout, adaptive, monte_carlo, two_phase = payloads
    return certify_vt08_r315(
        holdout_path=_write(tmp_path / "holdout.json", holdout),
        adaptive_policy_path=_write(tmp_path / "adaptive.json", adaptive),
        adaptive_monte_carlo_path=_write(tmp_path / "monte-carlo.json", monte_carlo),
        two_phase_path=_write(tmp_path / "two-phase.json", two_phase),
        certification_software_sha="a" * 40,
        workflow_run_id=123,
        certified_at=_CERTIFIED_AT,
    )


def test_official_chain_reaches_canonical_demo_eligible(tmp_path: Path) -> None:
    certificate = _certify(tmp_path, _payloads())

    assert certificate["promotion_status"] == "demo_eligible"
    assert certificate["lifecycle_state"] == "demo_eligible"
    assert certificate["demo_eligible"] is True
    assert certificate["live_authorized"] is False
    assert certificate["production_authorized"] is False
    assert certificate["completed_stages"] == [stage.value for stage in MANDATORY_STAGES]
    assert certificate["holdout"] == {
        "state": "consumed",
        "reopened": False,
        "run_id": 34759027136,
        "artifact_id": 10318827002,
        "artifact_digest": R315_HOLDOUT_ARTIFACT.digest,
        "sample": 124,
        "wins": 57,
        "losses": 67,
        "flats": 0,
    }
    portfolio = certificate["portfolio"]
    assert isinstance(portfolio, dict)
    assert portfolio["qualified_markets"] == ["AUDJPY", "GBPJPY", "GBPUSD"]
    assert portfolio["qualified_timeframes"] == ["M15", "H4"]
    assert portfolio["single_broker_order_composition"] == "pending-operational-boundary"
    authorities = certificate["governed_authorities"]
    assert isinstance(authorities, list)
    assert [item["authority_kind"] for item in authorities] == [
        "robustness",
        "risk",
        "cibo",
        "independent_validation",
    ]
    assert all(item["proof_fingerprint"] for item in authorities)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("sample_size", 123),
        ("independent_validation", False),
        ("methodology_mutation_after_holdout", True),
        ("live_authorized", True),
        ("portfolio", "A_CORE"),
    ),
)
def test_holdout_adapter_fails_closed_on_mutation(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    payloads = list(_payloads())
    payloads[0][field] = value

    with pytest.raises(Vt08R315AuthorityError):
        _certify(tmp_path, tuple(payloads))


def test_certification_rejects_invalid_software_sha(tmp_path: Path) -> None:
    holdout, adaptive, monte_carlo, two_phase = _payloads()
    with pytest.raises(Vt08R315CertificationError):
        certify_vt08_r315(
            holdout_path=_write(tmp_path / "holdout.json", holdout),
            adaptive_policy_path=_write(tmp_path / "adaptive.json", adaptive),
            adaptive_monte_carlo_path=_write(tmp_path / "mc.json", monte_carlo),
            two_phase_path=_write(tmp_path / "two-phase.json", two_phase),
            certification_software_sha="not-a-sha",
            workflow_run_id=123,
            certified_at=_CERTIFIED_AT,
        )


def test_artifact_adapter_rejects_cross_stage_artifact_laundering() -> None:
    with pytest.raises(TraderLabValidationError):
        Vt08R315ArtifactEvidence(
            stage=TraderLabStage.ECONOMIC_EVIDENCE,
            candidate=_candidate(),
            artifacts=(R312_RISK_ARTIFACT,),
            payload_digest="b" * 64,
            produced_at=_CERTIFIED_AT,
        )
