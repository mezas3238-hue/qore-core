from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: str, old: str, new: str) -> None:
    file_path = ROOT / path
    text = file_path.read_text()
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one match, found {count}: {old[:80]!r}")
    file_path.write_text(text.replace(old, new, 1))


def append_once(path: str, marker: str, block: str) -> None:
    file_path = ROOT / path
    text = file_path.read_text()
    if marker in text:
        return
    file_path.write_text(text.rstrip() + "\n\n" + block.strip() + "\n")


# ---------------------------------------------------------------------------
# FAMILY-C / F-EXTERNAL-GATE-MINT + FAMILY-D candidate binding
# ---------------------------------------------------------------------------
stage = "src/qore/infrastructure/trader_lab/stage_evidence.py"

replace_once(
    stage,
    "        TraderLabEvidenceKind.STRESS_EVIDENCE,\n        TraderLabEvidenceKind.ECONOMIC_EVALUATION,\n",
    "        TraderLabEvidenceKind.ECONOMIC_EVALUATION,\n",
)
replace_once(
    stage,
    "        TraderLabEvidenceKind.INDEPENDENT_VALIDATION,\n    }\n)\n",
    "        TraderLabEvidenceKind.INDEPENDENT_VALIDATION,\n        TraderLabEvidenceKind.STRESS_EVIDENCE,\n    }\n)\n",
)
replace_once(
    stage,
    "    strategy_binding_fingerprint: str | None = None\n    external_authenticity_proof: str | None = field(default=None, init=False)\n",
    "    strategy_binding_fingerprint: str | None = None\n    candidate_binding_fingerprint: str | None = None\n    external_authenticity_proof: str | None = field(default=None, init=False)\n",
)
replace_once(
    stage,
    "    def canonical_sort_key(self) -> tuple[str, str, str, str, bool, str, str]:\n",
    "    def canonical_sort_key(self) -> tuple[str, str, str, str, bool, str, str, str]:\n",
)
replace_once(
    stage,
    "            (\n                self.external_authenticity_proof\n                if self.external_authenticity_proof is not None\n                else \"\"\n            ),\n",
    "            (\n                self.candidate_binding_fingerprint\n                if self.candidate_binding_fingerprint is not None\n                else \"\"\n            ),\n            (\n                self.external_authenticity_proof\n                if self.external_authenticity_proof is not None\n                else \"\"\n            ),\n",
)
replace_once(
    stage,
    "            self.strategy_binding_fingerprint,\n            self.external_authenticity_proof,\n",
    "            self.strategy_binding_fingerprint,\n            self.candidate_binding_fingerprint,\n            self.external_authenticity_proof,\n",
)
replace_once(
    stage,
    "    if not isinstance(reference.kind, TraderLabEvidenceKind):\n        raise TraderLabValidationError(\n            f\"{field_name} kind must be TraderLabEvidenceKind\"\n        )\n",
    "    if type(reference) is not TraderLabEvidenceReference:\n        raise TraderLabValidationError(\n            f\"{field_name} must be exact TraderLabEvidenceReference\"\n        )\n    if type(reference.kind) is not TraderLabEvidenceKind:\n        raise TraderLabValidationError(\n            f\"{field_name} kind must be exact TraderLabEvidenceKind\"\n        )\n",
)
replace_once(
    stage,
    "    if reference.strategy_binding_fingerprint is not None:\n        _validate_sha256(\n            reference.strategy_binding_fingerprint,\n            field_name=f\"{field_name} strategy binding fingerprint\",\n        )\n    if reference.external_authenticity_proof is not None:\n",
    "    if reference.strategy_binding_fingerprint is not None:\n        _validate_sha256(\n            reference.strategy_binding_fingerprint,\n            field_name=f\"{field_name} strategy binding fingerprint\",\n        )\n    if reference.candidate_binding_fingerprint is not None:\n        _validate_sha256(\n            reference.candidate_binding_fingerprint,\n            field_name=f\"{field_name} candidate binding fingerprint\",\n        )\n    if reference.external_authenticity_proof is not None:\n",
)
replace_once(
    stage,
    "        if reference.external_authenticity_proof is None:\n            raise TraderLabValidationError(\n                f\"{field_name} external-authenticated evidence kind requires a \"\n                \"sealed authenticity proof issued by an owning authority\"\n            )\n",
    "        if reference.external_authenticity_proof is None:\n            raise TraderLabValidationError(\n                f\"{field_name} external-authenticated evidence kind requires a \"\n                \"sealed authenticity proof issued by an owning authority\"\n            )\n        if reference.candidate_binding_fingerprint is None:\n            raise TraderLabValidationError(\n                f\"{field_name} external-authenticated evidence kind requires exact \"\n                \"candidate binding\"\n            )\n",
)
replace_once(
    stage,
    "    if not isinstance(reference, TraderLabEvidenceReference):\n        raise TraderLabValidationError(\n            f\"{field_name} must be TraderLabEvidenceReference\"\n        )\n",
    "    if type(reference) is not TraderLabEvidenceReference:\n        raise TraderLabValidationError(\n            f\"{field_name} must be exact TraderLabEvidenceReference\"\n        )\n",
)
replace_once(
    stage,
    "    object.__setattr__(\n        reference, \"strategy_binding_fingerprint\", strategy_binding_fingerprint\n    )\n    object.__setattr__(reference, \"external_authenticity_proof\", None)\n",
    "    object.__setattr__(\n        reference, \"strategy_binding_fingerprint\", strategy_binding_fingerprint\n    )\n    object.__setattr__(reference, \"candidate_binding_fingerprint\", None)\n    object.__setattr__(reference, \"external_authenticity_proof\", None)\n",
)
replace_once(
    stage,
    "    strategy_binding_fingerprint: str | None,\n    authenticity_proof_fingerprint: str,\n) -> TraderLabEvidenceReference:\n",
    "    strategy_binding_fingerprint: str | None,\n    candidate_binding_fingerprint: str,\n    authenticity_proof_fingerprint: str,\n) -> TraderLabEvidenceReference:\n",
)
replace_once(
    stage,
    "    object.__setattr__(\n        reference, \"strategy_binding_fingerprint\", strategy_binding_fingerprint\n    )\n    object.__setattr__(\n        reference, \"external_authenticity_proof\", authenticity_proof_fingerprint\n    )\n",
    "    object.__setattr__(\n        reference, \"strategy_binding_fingerprint\", strategy_binding_fingerprint\n    )\n    object.__setattr__(\n        reference, \"candidate_binding_fingerprint\", candidate_binding_fingerprint\n    )\n    object.__setattr__(\n        reference, \"external_authenticity_proof\", authenticity_proof_fingerprint\n    )\n",
)
replace_once(
    stage,
    "    if reference.strategy_binding_fingerprint != (\n        candidate.strategy_binding.binding_fingerprint.value\n    ):\n        raise TraderLabValidationError(\n            f\"{field_name} strategy lineage does not match the candidate\"\n        )\n",
    "    if reference.strategy_binding_fingerprint != (\n        candidate.strategy_binding.binding_fingerprint.value\n    ):\n        raise TraderLabValidationError(\n            f\"{field_name} strategy lineage does not match the candidate\"\n        )\n    if evidence_kind_is_external_authenticated(reference.kind):\n        if reference.candidate_binding_fingerprint != candidate.fingerprint.value:\n            raise TraderLabValidationError(\n                f\"{field_name} external evidence candidate binding does not match \"\n                \"the exact candidate\"\n            )\n",
)

# ---------------------------------------------------------------------------
# FAMILY-A stress: STRESS becomes externally authenticated governance evidence.
# ---------------------------------------------------------------------------
governed = "src/qore/infrastructure/trader_lab/governed_gate.py"
replace_once(
    governed,
    "    RISK_REVIEW = \"risk_review\"\n    CIBO_REVIEW = \"cibo_review\"\n    INDEPENDENT_VALIDATION = \"independent_validation\"\n",
    "    STRESS_REVIEW = \"stress_review\"\n    RISK_REVIEW = \"risk_review\"\n    CIBO_REVIEW = \"cibo_review\"\n    INDEPENDENT_VALIDATION = \"independent_validation\"\n",
)
replace_once(
    governed,
    "    RISK = \"risk\"\n    CIBO = \"cibo\"\n    INDEPENDENT_VALIDATION = \"independent_validation\"\n",
    "    ROBUSTNESS = \"robustness\"\n    RISK = \"risk\"\n    CIBO = \"cibo\"\n    INDEPENDENT_VALIDATION = \"independent_validation\"\n",
)
replace_once(
    governed,
    "_GATE_KINDS: dict[TraderLabGovernedGate, TraderLabEvidenceKind] = {\n    TraderLabGovernedGate.RISK_REVIEW: TraderLabEvidenceKind.RISK_REVIEW,\n",
    "_GATE_KINDS: dict[TraderLabGovernedGate, TraderLabEvidenceKind] = {\n    TraderLabGovernedGate.STRESS_REVIEW: TraderLabEvidenceKind.STRESS_EVIDENCE,\n    TraderLabGovernedGate.RISK_REVIEW: TraderLabEvidenceKind.RISK_REVIEW,\n",
)
replace_once(
    governed,
    "] = {\n    TraderLabGovernedGate.RISK_REVIEW: TraderLabGovernedAuthorityKind.RISK,\n",
    "] = {\n    TraderLabGovernedGate.STRESS_REVIEW: TraderLabGovernedAuthorityKind.ROBUSTNESS,\n    TraderLabGovernedGate.RISK_REVIEW: TraderLabGovernedAuthorityKind.RISK,\n",
)
replace_once(
    governed,
    "                \"Risk/CIBO/independent-validation evidence requires an \"\n",
    "                \"Stress/Risk/CIBO/independent-validation evidence requires an \"\n",
)
replace_once(
    governed,
    "                authenticity_proof_fingerprint=proof.proof_fingerprint.value,\n",
    "                candidate_binding_fingerprint=candidate.fingerprint.value,\n                authenticity_proof_fingerprint=proof.proof_fingerprint.value,\n",
)

robustness = "src/qore/infrastructure/trader_lab/robustness.py"
replace_once(
    robustness,
    "    return _make_self_authenticating_reference(\n        kind=TraderLabEvidenceKind.STRESS_EVIDENCE,\n        reference_id=evidence.evidence_id.value,\n        content_digest=TraderLabEvidenceDigest(evidence.fingerprint.value),\n        schema_version=\"trader_lab.stress.v1\",\n        strategy_binding_fingerprint=candidate.strategy_binding.binding_fingerprint.value,\n    )\n",
    "    raise TraderLabValidationError(\n        \"qualified stress evidence is an external-governance dependency: use \"\n        \"TraderLabGovernedGate.STRESS_REVIEW with an externally issued \"\n        \"robustness-authority authenticity proof\"\n    )\n",
)

# ---------------------------------------------------------------------------
# FAMILY-A fast-forward: reference boundary re-runs chronology/no-lookahead.
# ---------------------------------------------------------------------------
ff = "src/qore/infrastructure/trader_lab/fast_forward.py"
old_reference = '''def reference_trader_lab_fast_forward(\n    candidate: TraderLabCandidateBinding,\n    qualification: TraderLabFastForwardQualification,\n) -> TraderLabEvidenceReference:\n    \"\"\"Reference an exact fast-forward qualification bound to the candidate.\"\"\"\n\n    if not isinstance(qualification, TraderLabFastForwardQualification):\n        raise TraderLabValidationError(\n            \"fast-forward reference requires TraderLabFastForwardQualification\"\n        )\n    if qualification.candidate != candidate:\n        raise TraderLabValidationError(\n            \"fast-forward qualification must bind the exact candidate\"\n        )\n    return _make_self_authenticating_reference(\n        kind=TraderLabEvidenceKind.FAST_FORWARD_QUALIFICATION,\n        reference_id=qualification.qualification_id.value,\n        content_digest=TraderLabEvidenceDigest(qualification.fingerprint.value),\n        schema_version=\"trader_lab.fast-forward.v1\",\n        strategy_binding_fingerprint=candidate.strategy_binding.binding_fingerprint.value,\n    )\n'''
new_reference = '''def validate_trader_lab_fast_forward_qualification(\n    qualification: TraderLabFastForwardQualification,\n    *,\n    observations: tuple[RetainedMarketEventObservation, ...],\n) -> None:\n    \"\"\"Re-run chronology and no-lookahead proofs at the reference trust boundary.\"\"\"\n\n    if type(qualification) is not TraderLabFastForwardQualification:\n        raise TraderLabValidationError(\n            \"fast-forward qualification must be exact TraderLabFastForwardQualification\"\n        )\n    # Re-enter retained structural/fingerprint invariants first.\n    TraderLabFastForwardQualification.__post_init__(qualification)\n    base_instants = derive_market_event_availability_instants(observations)\n    if len(base_instants) < 2:\n        raise TraderLabValidationError(\n            \"insufficient availability instants to validate fast-forward\"\n        )\n    if tuple(step.simulated_now for step in qualification.schedule.steps) != base_instants:\n        raise TraderLabValidationError(\n            \"fast-forward qualification schedule does not match the exact replay chronology\"\n        )\n    base_wall_clock = base_instants[-1] - base_instants[0]\n    accelerated_wall_clock = sum(\n        (step.wall_clock_advance for step in qualification.schedule.steps),\n        timedelta(0),\n    )\n    if (\n        base_wall_clock\n        != accelerated_wall_clock * qualification.schedule.acceleration_factor\n    ):\n        raise TraderLabValidationError(\n            \"fast-forward qualification acceleration no longer matches replay chronology\"\n        )\n    _verify_no_lookahead(observations, base_instants)\n    observations_digest = compute_replay_chronology_digest(observations)\n    if qualification.observations_digest != observations_digest:\n        raise TraderLabValidationError(\n            \"fast-forward qualification observations digest does not match replay evidence\"\n        )\n    if qualification.availability_instants != base_instants:\n        raise TraderLabValidationError(\n            \"fast-forward qualification availability instants do not match replay evidence\"\n        )\n\n\ndef reference_trader_lab_fast_forward(\n    candidate: TraderLabCandidateBinding,\n    qualification: TraderLabFastForwardQualification,\n    *,\n    observations: tuple[RetainedMarketEventObservation, ...],\n) -> TraderLabEvidenceReference:\n    \"\"\"Reference a revalidated fast-forward qualification bound to exact replay.\"\"\"\n\n    validate_trader_lab_fast_forward_qualification(\n        qualification, observations=observations\n    )\n    if qualification.candidate != candidate:\n        raise TraderLabValidationError(\n            \"fast-forward qualification must bind the exact candidate\"\n        )\n    return _make_self_authenticating_reference(\n        kind=TraderLabEvidenceKind.FAST_FORWARD_QUALIFICATION,\n        reference_id=qualification.qualification_id.value,\n        content_digest=TraderLabEvidenceDigest(qualification.fingerprint.value),\n        schema_version=\"trader_lab.fast-forward.v1\",\n        strategy_binding_fingerprint=candidate.strategy_binding.binding_fingerprint.value,\n    )\n'''
replace_once(ff, old_reference, new_reference)

# ---------------------------------------------------------------------------
# Test fixtures: real fast-forward qualification and externally governed stress.
# ---------------------------------------------------------------------------
conftest = "tests/infrastructure/trader_lab/conftest.py"
replace_once(
    conftest,
    "    RetainedMarketEventObservation,\n)",
    "    RetainedMarketEventObservation,\n    derive_market_event_availability_instants,\n)",
)
replace_once(
    conftest,
    "from qore.infrastructure.trader_lab.fast_forward import (\n    TraderLabFastForwardFingerprint,\n    TraderLabFastForwardQualification,\n    TraderLabFastForwardQualificationId,\n    reference_trader_lab_fast_forward,\n)\n",
    "from qore.infrastructure.trader_lab.fast_forward import (\n    TraderLabFastForwardQualification,\n    TraderLabFastForwardQualificationId,\n    TraderLabFastForwardSchedule,\n    TraderLabFastForwardStep,\n    qualify_trader_lab_fast_forward,\n    reference_trader_lab_fast_forward,\n)\n",
)
replace_once(
    conftest,
    "    TraderLabGovernedGate.RISK_REVIEW: TraderLabGovernedAuthorityKind.RISK,\n",
    "    TraderLabGovernedGate.STRESS_REVIEW: TraderLabGovernedAuthorityKind.ROBUSTNESS,\n    TraderLabGovernedGate.RISK_REVIEW: TraderLabGovernedAuthorityKind.RISK,\n",
)
old_ff_fixture = '''def _fast_forward_qualification(\n    candidate: TraderLabCandidateBinding,\n    *,\n    suffix: int,\n) -> TraderLabFastForwardQualification:\n    \"\"\"Build a fast-forward qualification object bound to the candidate.\"\"\"\n\n    qualification = object.__new__(TraderLabFastForwardQualification)\n    object.__setattr__(\n        qualification,\n        \"qualification_id\",\n        TraderLabFastForwardQualificationId(_uuid(suffix)),\n    )\n    object.__setattr__(qualification, \"candidate\", candidate)\n    object.__setattr__(\n        qualification, \"fingerprint\", TraderLabFastForwardFingerprint(\"a\" * 64)\n    )\n    return qualification\n'''
new_ff_fixture = '''def _fast_forward_qualification(\n    candidate: TraderLabCandidateBinding,\n    *,\n    suffix: int,\n) -> TraderLabFastForwardQualification:\n    \"\"\"Build a real qualification whose chronology proofs can be re-entered.\"\"\"\n\n    observations = _replay_observations()\n    instants = derive_market_event_availability_instants(observations)\n    base_wall = instants[-1] - instants[0]\n    factor = 2\n    per_step = base_wall // (factor * (len(instants) - 1))\n    schedule = TraderLabFastForwardSchedule(\n        steps=tuple(\n            TraderLabFastForwardStep(\n                simulated_now=instant,\n                wall_clock_advance=(\n                    per_step if index < len(instants) - 1 else timedelta(0)\n                ),\n            )\n            for index, instant in enumerate(instants)\n        ),\n        acceleration_factor=factor,\n    )\n    built = qualify_trader_lab_fast_forward(\n        qualification_id=TraderLabFastForwardQualificationId(_uuid(suffix)),\n        candidate=candidate,\n        schedule=schedule,\n        observations=observations,\n        certified_at=_PROCESS_TIME,\n    )\n    assert isinstance(built, Success), built\n    return built.value\n'''
replace_once(conftest, old_ff_fixture, new_ff_fixture)
replace_once(
    conftest,
    "    if stage is TraderLabStage.FAST_FORWARD:\n        return reference_trader_lab_fast_forward(\n            candidate, _fast_forward_qualification(candidate, suffix=suffix)\n        )\n",
    "    if stage is TraderLabStage.FAST_FORWARD:\n        observations = _replay_observations()\n        return reference_trader_lab_fast_forward(\n            candidate,\n            _fast_forward_qualification(candidate, suffix=suffix),\n            observations=observations,\n        )\n",
)
replace_once(
    conftest,
    "    if stage is TraderLabStage.STRESS:\n        return reference_trader_lab_stress(\n            candidate, _stress_evidence(candidate, suffix=suffix)\n        )\n",
    "    if stage is TraderLabStage.STRESS:\n        return _governed_reference(\n            candidate, gate=TraderLabGovernedGate.STRESS_REVIEW, suffix=suffix\n        )\n",
)

# ---------------------------------------------------------------------------
# Adversarial regression tests for the exact External Expert witnesses.
# ---------------------------------------------------------------------------
auth_test = "tests/infrastructure/trader_lab/test_governed_evidence_authenticity.py"
replace_once(
    auth_test,
    "    TraderLabGovernedGate.RISK_REVIEW: TraderLabGovernedAuthorityKind.RISK,\n",
    "    TraderLabGovernedGate.STRESS_REVIEW: TraderLabGovernedAuthorityKind.ROBUSTNESS,\n    TraderLabGovernedGate.RISK_REVIEW: TraderLabGovernedAuthorityKind.RISK,\n",
)
append_once(
    auth_test,
    "test_external_r2_reference_subclass_mint_is_rejected",
    r'''
def test_external_r2_reference_subclass_mint_is_rejected(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()

    @dataclass(frozen=True, slots=True)
    class _ForgedReference(TraderLabEvidenceReference):
        external_authenticity_proof: str | None = "a" * 64
        candidate_binding_fingerprint: str | None = candidate.fingerprint.value

    with pytest.raises(TraderLabValidationError, match="exact TraderLabEvidenceReference"):
        _ForgedReference(
            kind=TraderLabEvidenceKind.RISK_REVIEW,
            reference_id=_uuid(9901),
            content_digest=TraderLabEvidenceDigest("a" * 64),
            schema_version="forged.v1",
            strategy_binding_fingerprint=(
                candidate.strategy_binding.binding_fingerprint.value
            ),
        )


def test_external_r2_governed_reference_cannot_launder_across_candidates(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate_a = candidate_factory(candidate_suffix=91)
    candidate_b = candidate_factory(
        candidate_suffix=92,
        binding=candidate_a.strategy_binding,
    )
    carrier = _mint_carrier(
        candidate_a, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=9902
    )
    proof = _issue_proof(evidence=carrier, candidate=candidate_a)
    verified = verify_governed_gate_evidence(candidate_a, carrier, proof)
    assert isinstance(verified, Success)
    built = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(_uuid(9903)),
        stage=TraderLabStage.RISK_REVIEW,
        candidate=candidate_b,
        source_reference=verified.value,
        produced_at=_PROCESS_TIME,
    )
    assert isinstance(built, Failure)
    assert "candidate binding does not match" in str(built.error)


def test_external_r2_stress_requires_external_robustness_authority(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory(candidate_suffix=93)
    carrier = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.STRESS_REVIEW, suffix=9904
    )
    without_proof = verify_governed_gate_evidence(candidate, carrier, None)
    assert isinstance(without_proof, Failure)
    assert isinstance(without_proof.error, TraderLabExternalEvidenceDependencyError)

    proof = _issue_proof(evidence=carrier, candidate=candidate)
    verified = verify_governed_gate_evidence(candidate, carrier, proof)
    assert isinstance(verified, Success)
    assert verified.value.kind is TraderLabEvidenceKind.STRESS_EVIDENCE
    built = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(_uuid(9905)),
        stage=TraderLabStage.STRESS,
        candidate=candidate,
        source_reference=verified.value,
        produced_at=_PROCESS_TIME,
    )
    assert isinstance(built, Success)
''',
)

rob_test = "tests/infrastructure/trader_lab/test_robustness.py"
append_once(
    rob_test,
    "test_external_r2_qualified_stress_cannot_self_certify",
    r'''
def test_external_r2_qualified_stress_cannot_self_certify(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    built = build_trader_lab_stress_evidence(
        evidence_id=TraderLabStressEvidenceId(_uuid(131)),
        candidate=candidate,
        family=TraderLabRobustnessFamily.COST_PERTURBATION,
        scenario="totally-fabricated-no-evaluation-run",
        bounds=(Decimal("0.0"), Decimal("0.01")),
        status=TraderLabStressStatus.QUALIFIED,
        certified_at=_PROCESS_TIME,
    )
    assert isinstance(built, Success)
    with pytest.raises(TraderLabValidationError, match="external-governance dependency"):
        reference_trader_lab_stress(candidate, built.value)
''',
)

ff_test = "tests/infrastructure/trader_lab/test_fast_forward.py"
replace_once(
    ff_test,
    "from qore.infrastructure.trader_lab.fast_forward import (\n    TraderLabFastForwardQualificationId,\n    TraderLabFastForwardSchedule,\n    TraderLabFastForwardStep,\n    qualify_trader_lab_fast_forward,\n)\n",
    "from qore.infrastructure.trader_lab.fast_forward import (\n    TraderLabFastForwardQualification,\n    TraderLabFastForwardQualificationId,\n    TraderLabFastForwardSchedule,\n    TraderLabFastForwardStep,\n    compute_trader_lab_fast_forward_fingerprint,\n    qualify_trader_lab_fast_forward,\n    reference_trader_lab_fast_forward,\n)\nfrom qore.infrastructure.trader_lab.stage_evidence import TraderLabEvidenceDigest\n",
)
append_once(
    ff_test,
    "test_external_r2_public_constructor_cannot_bypass_reference_revalidation",
    r'''
def test_external_r2_public_constructor_cannot_bypass_reference_revalidation(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    observations = _observations()
    real_instants = derive_market_event_availability_instants(observations)
    forged_instants = (
        real_instants[0],
        real_instants[1] + timedelta(seconds=30),
        real_instants[2],
    )
    forged_schedule = _schedule(forged_instants)
    forged_digest = TraderLabEvidenceDigest("a" * 64)
    certified_at = _BASE + timedelta(minutes=10)
    fingerprint = compute_trader_lab_fast_forward_fingerprint(
        candidate=candidate,
        schedule=forged_schedule,
        observations_digest=forged_digest,
        availability_instants=forged_instants,
        certified_at=certified_at,
    )
    forged = TraderLabFastForwardQualification(
        qualification_id=TraderLabFastForwardQualificationId(_uuid(799)),
        candidate=candidate,
        schedule=forged_schedule,
        observations_digest=forged_digest,
        availability_instants=forged_instants,
        certified_at=certified_at,
        fingerprint=fingerprint,
    )
    with pytest.raises(TraderLabValidationError, match="does not match the exact replay chronology"):
        reference_trader_lab_fast_forward(
            candidate, forged, observations=observations
        )


def test_fast_forward_reference_revalidates_legitimate_qualification(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    observations = _observations()
    instants = derive_market_event_availability_instants(observations)
    built = qualify_trader_lab_fast_forward(
        qualification_id=TraderLabFastForwardQualificationId(_uuid(798)),
        candidate=candidate,
        schedule=_schedule(instants),
        observations=observations,
        certified_at=_BASE + timedelta(minutes=10),
    )
    assert isinstance(built, Success)
    reference = reference_trader_lab_fast_forward(
        candidate, built.value, observations=observations
    )
    assert reference.kind.value == "trader_lab.fast_forward"
''',
)

# Keep package-level public surface aligned for the new validator.
init_file = "src/qore/infrastructure/trader_lab/__init__.py"
text = (ROOT / init_file).read_text()
if "validate_trader_lab_fast_forward_qualification" not in text:
    text = text.replace(
        "    reference_trader_lab_fast_forward,\n",
        "    reference_trader_lab_fast_forward,\n    validate_trader_lab_fast_forward_qualification,\n",
        1,
    )
    (ROOT / init_file).write_text(text)

print("Trader Lab R2 IA closure patch applied")
