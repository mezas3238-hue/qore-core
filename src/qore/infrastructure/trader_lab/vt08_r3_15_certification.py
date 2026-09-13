"""Formal DEMO eligibility certification from immutable VT-08 R3.15 evidence."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from re import fullmatch
from typing import cast
from uuid import NAMESPACE_URL, uuid5

from qore.infrastructure.historical_dataset import (
    HistoricalDatasetDigest,
    HistoricalDatasetDigestAlgorithm,
    HistoricalDatasetId,
    HistoricalDatasetManifest,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalOhlcDatasetScope,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.market_data import Instrument, Timeframe
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
from qore.infrastructure.research_run import (
    ResearchExecutionModelId,
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    ResearchTransactionCostModelId,
    build_research_run_evidence,
)
from qore.infrastructure.research_strategy_freeze import (
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabCandidateId,
    TraderLabCandidateVersion,
    build_trader_lab_candidate_binding,
)
from qore.infrastructure.trader_lab.lifecycle import (
    MANDATORY_STAGES,
    TraderLabLifecycle,
    TraderLabPromotionRequest,
    TraderLabState,
    apply_trader_lab_promotion,
    start_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.promotion import (
    TraderLabPromotionStatus,
    evaluate_demo_eligibility,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceReference,
    TraderLabStage,
    TraderLabStageEvidenceId,
    build_trader_lab_stage_evidence,
)
from qore.infrastructure.trader_lab.vt08_r3_15_artifact_evidence import (
    R312_RISK_ARTIFACT,
    R314_FUNDING_ARTIFACT,
    R315_HOLDOUT_ARTIFACT,
    Vt08R315ArtifactEvidence,
    reference_vt08_r315_artifact_evidence,
)
from qore.infrastructure.vt08_r3_15_governed_authorities import (
    Vt08R315AuthorityIssuance,
    Vt08R315OfficialEvidence,
    issue_vt08_b01_r315_cibo,
    issue_vt08_r315_independent_validation,
    issue_vt08_r315_risk,
    issue_vt08_r315_robustness,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure

EVIDENCE_HEAD = "64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222"
PRE_HOLDOUT_FREEZE_SHA = "35767e3ef9915830b02cabbb92ab952e7bc4d619"
EXECUTABLE_VERSION = "r3.8-b01-author-clarified-v1"
METHODOLOGY_ID = "ttrades-h4-po3-b01"
METHODOLOGY_VERSION = "r3.8-author-clarified-b01-v1"
METHODOLOGY_FINGERPRINT = (
    "0c3fe8e1353386f7384a8532c7fe71bbbe9fcfdf1da7530be4b53e01bc59de0d"
)
SOURCE_CONTRACT_FINGERPRINT = (
    "403d54304f241f4a11b1ef847aa2a8b12d5ba6ffa2d9be5bb5cd9c19586943e3"
)
RISK_POLICY_ID = "balanced-adaptive-v1"
VALIDATION_POLICY_ID = "vt08-r315-final-demo-v1"
PORTFOLIO = "B_COMBINED"
QUALIFIED_MARKETS = ("AUDJPY", "GBPJPY", "GBPUSD")
QUALIFIED_TIMEFRAMES = ("M15", "H4")
PORTFOLIO_MEMBERS = (
    ("AUDJPY", "short", "A_CORE"),
    ("GBPUSD", "short", "A_CORE"),
    ("GBPJPY", "long", "GBPJPY_RETURN_ENHANCER"),
    ("GBPJPY", "short", "GBPJPY_RETURN_ENHANCER"),
)
_OPENED_AT = datetime(2020, 7, 1, tzinfo=UTC)
_CLOSED_AT = datetime(2022, 7, 1, tzinfo=UTC)
_EVIDENCE_PRODUCED_AT = datetime(2026, 9, 13, 13, 34, 13, tzinfo=UTC)


class Vt08R315CertificationError(InfrastructureError):
    """The formal certificate could not be produced without violating governance."""

    __slots__ = ()


def _load(path: Path, field: str) -> dict[str, object]:
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08R315CertificationError(f"cannot read {field}") from error
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08R315CertificationError(f"{field} must be an object")
    return cast(dict[str, object], value)


def _file_digest(path: Path) -> str:
    try:
        return sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise Vt08R315CertificationError(f"cannot digest {path.name}") from error


def _config_fingerprint() -> str:
    encoded = json.dumps(
        {
            "schema": "qore.vt08.r3.15.b01-portfolio-config.v1",
            "executable_version": EXECUTABLE_VERSION,
            "methodology_id": METHODOLOGY_ID,
            "methodology_version": METHODOLOGY_VERSION,
            "methodology_fingerprint": METHODOLOGY_FINGERPRINT,
            "source_contract_fingerprint": SOURCE_CONTRACT_FINGERPRINT,
            "portfolio": PORTFOLIO,
            "members": PORTFOLIO_MEMBERS,
            "qualified_markets": QUALIFIED_MARKETS,
            "qualified_timeframes": QUALIFIED_TIMEFRAMES,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _candidate() -> TraderLabCandidateBinding:
    configuration_id = ResearchStrategyConfigurationId(
        uuid5(NAMESPACE_URL, "qore:vt08:r315:b01-portfolio-config")
    )
    source = ExternalSourceDescriptor(
        adapter_id=AdapterId(uuid5(NAMESPACE_URL, "qore:vt08:r315:artifact-adapter")),
        source_id=SourceId(uuid5(NAMESPACE_URL, "qore:vt08:r315:official-holdout")),
        port_name=PortName("market-data.github-actions-artifact"),
    )
    scope = HistoricalOhlcDatasetScope(
        source=source,
        window=HistoricalOhlcWindow(
            instrument=Instrument(PORTFOLIO),
            timeframe=Timeframe(900),
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
        ),
    )
    dataset = HistoricalDatasetManifest(
        dataset_id=HistoricalDatasetId(
            uuid5(NAMESPACE_URL, "qore:vt08:r315:holdout-dataset")
        ),
        revision_id=HistoricalDatasetRevisionId(
            uuid5(NAMESPACE_URL, "qore:vt08:r315:holdout-dataset:rev1")
        ),
        parent_revision_id=None,
        revision_reason=None,
        scope=scope,
        assembled_at=_EVIDENCE_PRODUCED_AT,
        schema_version=HistoricalDatasetSchemaVersion("r315-artifact-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion("r315-frozen-v1"),
        observation_count=124,
        actual_opened_at=_OPENED_AT,
        actual_closed_at=_CLOSED_AT,
        gaps=(),
        digest_algorithm=HistoricalDatasetDigestAlgorithm.SHA256,
        evidence_digest=HistoricalDatasetDigest(R315_HOLDOUT_ARTIFACT.digest),
    )
    built_run = build_research_run_evidence(
        run_id=ResearchRunId(uuid5(NAMESPACE_URL, "qore:vt08:r315:official-run")),
        created_at=_EVIDENCE_PRODUCED_AT,
        datasets=(dataset,),
        replay_policy_version=ResearchReplayPolicyVersion(
            "r3.15-consumed-official-holdout-v1"
        ),
        simulated_start=_OPENED_AT,
        simulated_end=_CLOSED_AT,
        strategy_configuration_id=configuration_id,
        software_revision=ResearchSoftwareRevision(EVIDENCE_HEAD),
        execution_model_id=ResearchExecutionModelId(
            uuid5(NAMESPACE_URL, "qore:vt08:r315:execution-model")
        ),
        transaction_cost_model_id=ResearchTransactionCostModelId(
            uuid5(NAMESPACE_URL, "qore:vt08:r315:transaction-cost-model")
        ),
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    if isinstance(built_run, Failure):
        raise Vt08R315CertificationError(f"research run binding failed: {built_run.error}")
    built_manifest = build_research_strategy_configuration_manifest(
        configuration_id=configuration_id,
        schema_version=ResearchStrategySchemaVersion("vt08-r315-b01-v1"),
        parameters=tuple(
            ResearchStrategyParameter(name, value)
            for name, value in {
                "trader.code": "vt-08",
                "trader.config_fingerprint": _config_fingerprint(),
                "trader.executable_version": EXECUTABLE_VERSION,
                "trader.methodology_fingerprint": METHODOLOGY_FINGERPRINT,
                "trader.methodology_id": METHODOLOGY_ID,
                "trader.methodology_version": METHODOLOGY_VERSION,
                "trader.portfolio": PORTFOLIO,
                "trader.pre_holdout_freeze_sha": PRE_HOLDOUT_FREEZE_SHA,
                "trader.qualified_markets": ",".join(QUALIFIED_MARKETS),
                "trader.qualified_timeframes": ",".join(QUALIFIED_TIMEFRAMES),
                "trader.source_contract_fingerprint": SOURCE_CONTRACT_FINGERPRINT,
            }.items()
        ),
        frozen_at=datetime(2026, 9, 13, 12, 0, tzinfo=UTC),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(
            uuid5(NAMESPACE_URL, f"qore:vt08:r315:freeze:{PRE_HOLDOUT_FREEZE_SHA}")
        ),
    )
    if isinstance(built_manifest, Failure):
        raise Vt08R315CertificationError(
            f"strategy manifest binding failed: {built_manifest.error}"
        )
    bound = build_research_run_strategy_binding(
        run=built_run.value,
        manifest=built_manifest.value,
    )
    if isinstance(bound, Failure):
        raise Vt08R315CertificationError(f"strategy binding failed: {bound.error}")
    built_candidate = build_trader_lab_candidate_binding(
        candidate_id=TraderLabCandidateId(
            uuid5(NAMESPACE_URL, "qore:trader-lab:candidate:vt-08:r315-b01")
        ),
        version=TraderLabCandidateVersion(EXECUTABLE_VERSION),
        strategy_binding=bound.value,
    )
    if isinstance(built_candidate, Failure):
        raise Vt08R315CertificationError(
            f"candidate binding failed: {built_candidate.error}"
        )
    return built_candidate.value


def _promote(
    lifecycle: TraderLabLifecycle,
    stage: TraderLabStage,
    reference: TraderLabEvidenceReference,
    produced_at: datetime,
) -> TraderLabLifecycle:
    evidence = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            uuid5(
                NAMESPACE_URL,
                f"qore:vt08:r315:stage:{lifecycle.candidate.fingerprint.value}:{stage.value}",
            )
        ),
        stage=stage,
        candidate=lifecycle.candidate,
        source_reference=reference,
        produced_at=produced_at,
    )
    if isinstance(evidence, Failure):
        raise Vt08R315CertificationError(f"{stage.value} evidence failed: {evidence.error}")
    promoted = apply_trader_lab_promotion(
        lifecycle,
        TraderLabPromotionRequest(stage=stage, evidence=evidence.value),
    )
    if isinstance(promoted, Failure):
        raise Vt08R315CertificationError(
            f"{stage.value} promotion failed: {promoted.error}"
        )
    return promoted.value


def _artifact_reference(
    candidate: TraderLabCandidateBinding,
    stage: TraderLabStage,
    payload_digest: str,
    produced_at: datetime,
) -> TraderLabEvidenceReference:
    artifacts = {
        TraderLabStage.RESEARCH: (R314_FUNDING_ARTIFACT,),
        TraderLabStage.REPLAY: (R315_HOLDOUT_ARTIFACT,),
        TraderLabStage.FAST_FORWARD: (R314_FUNDING_ARTIFACT,),
        TraderLabStage.OOS: (R314_FUNDING_ARTIFACT,),
        TraderLabStage.MONTE_CARLO: (R312_RISK_ARTIFACT,),
        TraderLabStage.ECONOMIC_EVIDENCE: (R315_HOLDOUT_ARTIFACT,),
    }[stage]
    return reference_vt08_r315_artifact_evidence(
        Vt08R315ArtifactEvidence(
            stage=stage,
            candidate=candidate,
            artifacts=artifacts,
            payload_digest=payload_digest,
            produced_at=produced_at,
        )
    )


def _authority_payload(item: Vt08R315AuthorityIssuance) -> dict[str, object]:
    return {
        "gate": item.gate.value,
        "authority_kind": item.authority_kind.value,
        "authority_name": item.authority_name,
        "evidence_id": str(item.evidence.evidence_id.value),
        "evidence_digest": item.evidence.authority_evidence_digest.value,
        "evidence_fingerprint": item.evidence.fingerprint.value,
        "proof_fingerprint": item.proof.proof_fingerprint.value,
    }


def certify_vt08_r315(
    *,
    holdout_path: Path,
    adaptive_policy_path: Path,
    adaptive_monte_carlo_path: Path,
    two_phase_path: Path,
    certification_software_sha: str,
    workflow_run_id: int,
    certified_at: datetime,
) -> dict[str, object]:
    if fullmatch(r"[0-9a-f]{40}", certification_software_sha) is None:
        raise Vt08R315CertificationError("certification software SHA must be exact")
    if type(workflow_run_id) is not int or workflow_run_id <= 0:
        raise Vt08R315CertificationError("workflow run id must be positive")
    if type(certified_at) is not datetime or certified_at.tzinfo is None:
        raise Vt08R315CertificationError("certified_at must be timezone-aware")
    holdout = _load(holdout_path, "official holdout")
    adaptive_policy = _load(adaptive_policy_path, "official adaptive Risk policy")
    adaptive_mc = _load(adaptive_monte_carlo_path, "official adaptive Monte Carlo")
    two_phase = _load(two_phase_path, "official two-phase evidence")
    official = Vt08R315OfficialEvidence(
        holdout=holdout,
        adaptive_risk_policy=adaptive_policy,
        adaptive_monte_carlo_b_combined=adaptive_mc,
        two_phase=two_phase,
    )
    candidate = _candidate()
    lifecycle = start_trader_lab_lifecycle(candidate)
    r314_digest = _file_digest(two_phase_path)
    r315_digest = _file_digest(holdout_path)
    r312_digest = _file_digest(adaptive_monte_carlo_path)
    for stage, digest in (
        (TraderLabStage.RESEARCH, r314_digest),
        (TraderLabStage.REPLAY, r315_digest),
        (TraderLabStage.FAST_FORWARD, r314_digest),
        (TraderLabStage.OOS, r314_digest),
    ):
        lifecycle = _promote(
            lifecycle,
            stage,
            _artifact_reference(candidate, stage, digest, certified_at),
            certified_at,
        )
    robustness = issue_vt08_r315_robustness(
        lifecycle,
        official,
        decided_at=certified_at,
    )
    lifecycle = _promote(
        lifecycle,
        TraderLabStage.STRESS,
        robustness.reference,
        certified_at,
    )
    lifecycle = _promote(
        lifecycle,
        TraderLabStage.MONTE_CARLO,
        _artifact_reference(
            candidate,
            TraderLabStage.MONTE_CARLO,
            r312_digest,
            certified_at,
        ),
        certified_at,
    )
    risk = issue_vt08_r315_risk(lifecycle, official, decided_at=certified_at)
    lifecycle = _promote(
        lifecycle,
        TraderLabStage.RISK_REVIEW,
        risk.reference,
        certified_at,
    )
    economic = _artifact_reference(
        candidate,
        TraderLabStage.ECONOMIC_EVIDENCE,
        r315_digest,
        certified_at,
    )
    cibo = issue_vt08_b01_r315_cibo(
        lifecycle,
        official,
        economic,
        decided_at=certified_at,
    )
    lifecycle = _promote(
        lifecycle,
        TraderLabStage.CIBO_REVIEW,
        cibo.reference,
        certified_at,
    )
    independent = issue_vt08_r315_independent_validation(
        lifecycle,
        official,
        economic,
        decided_at=certified_at,
    )
    lifecycle = _promote(
        lifecycle,
        TraderLabStage.INDEPENDENT_VALIDATION,
        independent.reference,
        certified_at,
    )
    lifecycle = _promote(
        lifecycle,
        TraderLabStage.ECONOMIC_EVIDENCE,
        economic,
        certified_at,
    )
    promotion = evaluate_demo_eligibility(lifecycle, economic_evidence=economic)
    demo_eligible = promotion.status is TraderLabPromotionStatus.DEMO_ELIGIBLE
    completed = tuple(stage.value for stage in lifecycle.completed_stages)
    mandatory = tuple(stage.value for stage in MANDATORY_STAGES)
    if not demo_eligible or lifecycle.state is not TraderLabState.DEMO_ELIGIBLE:
        raise Vt08R315CertificationError("canonical gate did not reach DEMO_ELIGIBLE")
    if completed != mandatory:
        raise Vt08R315CertificationError("mandatory stage chain is incomplete")
    authorities = (robustness, risk, cibo, independent)
    if any(item.reference.external_authenticity_proof is None for item in authorities):
        raise Vt08R315CertificationError("governed authority proof is missing")
    certificate: dict[str, object] = {
        "schema": "qore.vt08.r3.15.demo-eligibility-certificate.v1",
        "certificate_version": "1",
        "trader": {
            "code": "vt-08",
            "executable_version": EXECUTABLE_VERSION,
            "candidate_fingerprint": candidate.fingerprint.value,
            "config_fingerprint": _config_fingerprint(),
        },
        "methodology": {
            "id": METHODOLOGY_ID,
            "version": METHODOLOGY_VERSION,
            "fingerprint": METHODOLOGY_FINGERPRINT,
            "source_contract_fingerprint": SOURCE_CONTRACT_FINGERPRINT,
        },
        "portfolio": {
            "id": PORTFOLIO,
            "members": [
                {"market": market, "side": side, "sleeve": sleeve}
                for market, side, sleeve in PORTFOLIO_MEMBERS
            ],
            "qualified_markets": list(QUALIFIED_MARKETS),
            "qualified_timeframes": list(QUALIFIED_TIMEFRAMES),
            "single_broker_order_composition": "pending-operational-boundary",
        },
        "evidence_lineage": [
            {
                "artifact_name": item.name,
                "artifact_id": item.artifact_id,
                "run_id": item.run_id,
                "head_sha": item.head_sha,
                "archive_digest": item.digest,
            }
            for item in (
                R312_RISK_ARTIFACT,
                R314_FUNDING_ARTIFACT,
                R315_HOLDOUT_ARTIFACT,
            )
        ],
        "holdout": {
            "state": "consumed",
            "reopened": False,
            "run_id": R315_HOLDOUT_ARTIFACT.run_id,
            "artifact_id": R315_HOLDOUT_ARTIFACT.artifact_id,
            "artifact_digest": R315_HOLDOUT_ARTIFACT.digest,
            "sample": 124,
            "wins": 57,
            "losses": 67,
            "flats": 0,
        },
        "risk": {
            "funded_policy_id": RISK_POLICY_ID,
            "validation_policy_id": VALIDATION_POLICY_ID,
            "minimum_independent_sample": 30,
            "maximum_population_variance": "0.01",
        },
        "mandatory_stages": list(mandatory),
        "completed_stages": list(completed),
        "governed_authorities": [_authority_payload(item) for item in authorities],
        "promotion_status": promotion.status.value,
        "promotion_reasons": list(promotion.reasons),
        "lifecycle_state": lifecycle.state.value,
        "demo_eligible": True,
        "live_authorized": False,
        "production_authorized": False,
        "pre_holdout_freeze_sha": PRE_HOLDOUT_FREEZE_SHA,
        "methodology_mutation_after_holdout": False,
        "certification_software_sha": certification_software_sha,
        "workflow_run_id": workflow_run_id,
        "certified_at": certified_at.astimezone(UTC).isoformat(),
    }
    return certificate


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 8:
        print(
            "usage: ... HOLDOUT POLICY MONTE_CARLO TWO_PHASE SOFTWARE_SHA "
            "WORKFLOW_RUN_ID CERTIFIED_AT OUTPUT",
            file=sys.stderr,
        )
        return 2
    try:
        certificate = certify_vt08_r315(
            holdout_path=Path(args[0]),
            adaptive_policy_path=Path(args[1]),
            adaptive_monte_carlo_path=Path(args[2]),
            two_phase_path=Path(args[3]),
            certification_software_sha=args[4],
            workflow_run_id=int(args[5]),
            certified_at=datetime.fromisoformat(args[6]),
        )
        output = Path(args[7])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                certificate,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, Vt08R315CertificationError) as error:
        print(f"VT-08 R3.15 certification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(certificate, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
