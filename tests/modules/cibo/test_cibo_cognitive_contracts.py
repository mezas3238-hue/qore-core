from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboCognitiveValidationError,
    CiboConfidence,
    CiboConfidenceLevel,
    CiboDeliberationRole,
    CiboEpistemicClaim,
    CiboEpistemicState,
    CiboFormalRecommendation,
    CiboReasoningMode,
    CiboUncertainty,
    CiboUncertaintyKind,
    contains_secret_material,
)

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)


def _ref(value: str) -> CiboCognitiveEvidenceRef:
    return CiboCognitiveEvidenceRef(value)


def _bounded_uncertainty() -> CiboUncertainty:
    return CiboUncertainty(
        kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE,
        confidence=CiboConfidence(
            level=CiboConfidenceLevel.MEDIUM,
            evidence_refs=(_ref("evidence:bounded"),),
        ),
    )


def _insufficient_uncertainty() -> CiboUncertainty:
    return CiboUncertainty(kind=CiboUncertaintyKind.INSUFFICIENT_EVIDENCE)


def _recommendation(
    *,
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...] = (_ref("evidence:exposure"),),
    issued_at: datetime = _NOW,
    summary: str = "Review portfolio exposure",
) -> CiboFormalRecommendation:
    return CiboFormalRecommendation(
        recommendation_id=UUID("30000000-0000-0000-0000-000000000001"),
        recommendation_code="cibo.review-portfolio",
        reasoning_mode=CiboReasoningMode.HIGH,
        summary=summary,
        evidence_refs=evidence_refs,
        uncertainty=_bounded_uncertainty(),
        issued_at=issued_at,
    )


class TestReasoningModesAndEpistemicStates:
    def test_reasoning_modes_are_policy_semantics_not_models(self) -> None:
        assert {mode.value for mode in CiboReasoningMode} == {
            "fast",
            "high",
            "max",
            "council-adversarial",
        }
        for mode in CiboReasoningMode:
            assert "gpt" not in mode.value
            assert "claude" not in mode.value
            assert "model" not in mode.value

    def test_epistemic_states_exclude_authorized_action(self) -> None:
        assert CiboEpistemicState.FORMAL_RECOMMENDATION.value == "formal-recommendation"
        assert not hasattr(CiboEpistemicState, "AUTHORIZED_ACTION")
        assert not hasattr(CiboEpistemicState, "EXECUTION")


class TestConfidence:
    def test_confidence_rejects_bool_level_laundering(self) -> None:
        with pytest.raises(CiboCognitiveValidationError):
            CiboConfidence(level=True, evidence_refs=(_ref("evidence:x"),))  # type: ignore[arg-type]

    def test_confidence_requires_backing_evidence(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="evidence"):
            CiboConfidence(level=CiboConfidenceLevel.HIGH, evidence_refs=())

    def test_confidence_canonicalizes_evidence_order(self) -> None:
        left = CiboConfidence(
            level=CiboConfidenceLevel.LOW,
            evidence_refs=(_ref("evidence:a"), _ref("evidence:b")),
        )
        right = CiboConfidence(
            level=CiboConfidenceLevel.LOW,
            evidence_refs=(_ref("evidence:b"), _ref("evidence:a")),
        )
        assert left == right
        assert left.logical_values() == right.logical_values()


class TestEvidenceRef:
    def test_evidence_ref_rejects_secret_material(self) -> None:
        for bad in ("evidence:token=abc", "evidence:bearer xyz", "secret=value"):
            with pytest.raises(CiboCognitiveValidationError):
                CiboCognitiveEvidenceRef(bad)

    @pytest.mark.parametrize(
        "witness",
        (
            "evidence:sk-abcdefghijklmnop",
            "evidence:ghp_abcdefghijklmnopqrstuvwxyz1234",
            "evidence:gho_abcdefghijklmnopqrstuvwxyz1234",
            "evidence:ghu_abcdefghijklmnopqrstuvwxyz1234",
            "evidence:ghs_abcdefghijklmnopqrstuvwxyz1234",
            "evidence:ghr_abcdefghijklmnopqrstuvwxyz1234",
            "evidence:xoxb-123456789012-abcdefghijklmnopqrstuvwxyz",
            "evidence:xoxp-123456789012-abcdefghijklmnopqrstuvwxyz",
            "evidence:xoxa-123456789012-abcdefghijklmnopqrstuvwxyz",
            "evidence:xoxr-123456789012-abcdefghijklmnopqrstuvwxyz",
            "evidence:xoxs-123456789012-abcdefghijklmnopqrstuvwxyz",
        ),
    )
    def test_evidence_ref_rejects_structural_secrets(self, witness: str) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="sensitive"):
            CiboCognitiveEvidenceRef(witness)

    def test_evidence_ref_revalidate_rejects_reflective_secret(self) -> None:
        ref = _ref("evidence:demo")
        object.__setattr__(ref, "value", "evidence:xoxb-123456789012-abcdefghijklmnopqrstuvwxyz")
        with pytest.raises(CiboCognitiveValidationError, match="sensitive"):
            ref.revalidate()

    def test_evidence_ref_accepts_bare_field_name_mention(self) -> None:
        assert _ref("evidence:client_secret_demo").value == "evidence:client_secret_demo"

    def test_evidence_ref_rejects_non_string(self) -> None:
        with pytest.raises(CiboCognitiveValidationError):
            CiboCognitiveEvidenceRef(True)  # type: ignore[arg-type]


class TestUncertainty:
    def test_bounded_confidence_requires_confidence(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="confidence"):
            CiboUncertainty(kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE)

    def test_competing_hypotheses_requires_details(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="detail"):
            CiboUncertainty(kind=CiboUncertaintyKind.COMPETING_HYPOTHESES)

    def test_insufficient_evidence_is_first_class(self) -> None:
        uncertainty = _insufficient_uncertainty()
        assert uncertainty.kind is CiboUncertaintyKind.INSUFFICIENT_EVIDENCE
        assert uncertainty.confidence is None


class TestEpistemicClaim:
    def test_claim_rejects_formal_recommendation_state(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="CiboFormalRecommendation"):
            CiboEpistemicClaim(
                claim_id=UUID("30000000-0000-0000-0000-000000000010"),
                epistemic_state=CiboEpistemicState.FORMAL_RECOMMENDATION,
                reasoning_mode=CiboReasoningMode.FAST,
                content_code="cibo.claim",
                evidence_refs=(_ref("evidence:x"),),
                uncertainty=_insufficient_uncertainty(),
            )

    def test_claim_requires_exact_uuid(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="UUID"):
            CiboEpistemicClaim(
                claim_id="not-a-uuid",  # type: ignore[arg-type]
                epistemic_state=CiboEpistemicState.OBSERVATION,
                reasoning_mode=CiboReasoningMode.FAST,
                content_code="cibo.claim",
                evidence_refs=(_ref("evidence:x"),),
                uncertainty=_insufficient_uncertainty(),
            )

    def test_claim_rejects_bool_epistemic_state(self) -> None:
        with pytest.raises(CiboCognitiveValidationError):
            CiboEpistemicClaim(
                claim_id=UUID("30000000-0000-0000-0000-000000000010"),
                epistemic_state=True,  # type: ignore[arg-type]
                reasoning_mode=CiboReasoningMode.FAST,
                content_code="cibo.claim",
                evidence_refs=(_ref("evidence:x"),),
                uncertainty=_insufficient_uncertainty(),
            )


class TestFormalRecommendation:
    def test_recommendation_requires_evidence(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="evidence"):
            _recommendation(evidence_refs=())

    def test_recommendation_rejects_naive_datetime(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="timezone"):
            _recommendation(issued_at=datetime(2026, 8, 9, 0, 0))

    def test_recommendation_rejects_secret_summary(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="sensitive"):
            _recommendation(summary="token=abc123 leaked")

    @pytest.mark.parametrize(
        "witness",
        (
            "sk-proj-abcdefghijklmnopqrstuvwxyz123456",
            "AKIAIOSFODNN7EXAMPLE",
            "ghp_abcdefghijklmnopqrstuvwxyz1234",
            "gho_abcdefghijklmnopqrstuvwxyz1234",
            "ghu_abcdefghijklmnopqrstuvwxyz1234",
            "ghs_abcdefghijklmnopqrstuvwxyz1234",
            "ghr_abcdefghijklmnopqrstuvwxyz1234",
            "xoxb-123456789012-abcdefghijklmnopqrstuvwxyz",
            "xoxp-123456789012-abcdefghijklmnopqrstuvwxyz",
            "xoxa-123456789012-abcdefghijklmnopqrstuvwxyz",
            "xoxr-123456789012-abcdefghijklmnopqrstuvwxyz",
            "xoxs-123456789012-abcdefghijklmnopqrstuvwxyz",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature",
            "https://alice:correcthorsebatterystaple@example.com/x",
            "client_secret=abcdefghijklmnopqrstuvwxyz123456",
            "Authorization: Bearer abcdef1234567890",
            "-----BEGIN PRIVATE KEY-----",
        ),
    )
    def test_recommendation_rejects_structural_secret_summary(self, witness: str) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="sensitive"):
            _recommendation(summary=witness)

    def test_revalidate_rejects_injected_structural_secret(self) -> None:
        recommendation = _recommendation()
        object.__setattr__(
            recommendation, "summary", "sk-proj-abcdefghijklmnopqrstuvwxyz123456"
        )
        with pytest.raises(CiboCognitiveValidationError):
            recommendation.revalidate()

    def test_recommendation_has_no_authority_fields(self) -> None:
        recommendation = _recommendation()
        for absent in (
            "order",
            "intent",
            "provider",
            "instrument",
            "quantity",
            "account",
            "authorization",
            "promotion",
        ):
            assert not hasattr(recommendation, absent)

    def test_recommendation_epistemic_state_is_never_an_action(self) -> None:
        assert _recommendation().epistemic_state is CiboEpistemicState.FORMAL_RECOMMENDATION

    def test_recommendation_deterministic(self) -> None:
        assert _recommendation().logical_values() == _recommendation().logical_values()

    def test_revalidate_detects_tampered_nested_confidence(self) -> None:
        recommendation = _recommendation()
        object.__setattr__(recommendation.uncertainty, "confidence", object())
        with pytest.raises(CiboCognitiveValidationError):
            recommendation.revalidate()

    def test_revalidate_detects_tampered_evidence_ref(self) -> None:
        recommendation = _recommendation()
        object.__setattr__(recommendation.evidence_refs[0], "value", "secret=injected")
        with pytest.raises(CiboCognitiveValidationError):
            recommendation.revalidate()


class TestDeliberationRole:
    def test_role_is_generic_faculty_identity(self) -> None:
        role = CiboDeliberationRole("market-strategist")
        assert role.value == "market-strategist"
        assert CiboDeliberationRole("risk-aware-critic").value == "risk-aware-critic"

    def test_role_rejects_non_canonical_code(self) -> None:
        with pytest.raises(CiboCognitiveValidationError):
            CiboDeliberationRole("Market Strategist")


class TestRevalidationEquivalence:
    def test_epistemic_claim_revalidate_rejects_formal_recommendation_state(self) -> None:
        claim = CiboEpistemicClaim(
            claim_id=UUID("30000000-0000-0000-0000-0000000000bb"),
            epistemic_state=CiboEpistemicState.OBSERVATION,
            reasoning_mode=CiboReasoningMode.HIGH,
            content_code="content-code",
            evidence_refs=(_ref("evidence:claim"),),
            uncertainty=_insufficient_uncertainty(),
        )
        object.__setattr__(claim, "epistemic_state", CiboEpistemicState.FORMAL_RECOMMENDATION)
        with pytest.raises(CiboCognitiveValidationError):
            claim.revalidate()

    def test_role_rejects_secret_code(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="sensitive"):
            CiboDeliberationRole("sk-abcdefghijklmnop")


class TestTimezoneMetamorphism:
    def test_recommendation_logical_values_identical_across_offsets(self) -> None:
        utc = datetime(2026, 8, 9, 5, 0, tzinfo=UTC)
        est = datetime(2026, 8, 9, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
        left = _recommendation(issued_at=utc, evidence_refs=(_ref("evidence:exposure"),))
        right = _recommendation(issued_at=est, evidence_refs=(_ref("evidence:exposure"),))
        assert left.logical_values() == right.logical_values()

    def test_recommendation_distinct_instants_stay_distinct(self) -> None:
        left = _recommendation(
            issued_at=datetime(2026, 8, 9, 5, 0, tzinfo=UTC),
            evidence_refs=(_ref("evidence:exposure"),),
        )
        right = _recommendation(
            issued_at=datetime(2026, 8, 9, 5, 1, tzinfo=UTC),
            evidence_refs=(_ref("evidence:exposure"),),
        )
        assert left.logical_values() != right.logical_values()


class TestSecretHygieneResiduals:
    @pytest.mark.parametrize(
        "witness",
        (
            "client_secret\u200b = abc123",
            "secret\u200b_key = abcdef",
            "secret_key\u200b= abcdef",
            "client_secret\u200c = abc123",
            "client_secret\u200d = abc123",
            "client_secret\u2060 = abc123",
            "client_secret\ufeff = abc123",
            "AKIA\u200b1234567890ABCDEF",
            "AKIA\u200c1234567890ABCDEF",
        ),
    )
    def test_zero_width_cf_chars_cannot_split_labels_or_ids(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            "client_secret\ufe0f = abc123",
            "client\ufe0f_secret = abc123",
            "client_secret\ufe00 = abc123",
            "client\U000e0100_secret = abc123",
            "client\U000e01ef_secret = abc123",
            "client_secret\u180b = abc123",
            "client\u180c_secret = abc123",
            "client\u180d_secret = abc123",
            "client\u034f_secret = abc123",
            "AKIA\ufe0f1234567890ABCDEF",
            "AKIA\u180b1234567890ABCDEF",
        ),
    )
    def test_variation_selectors_and_fvs_cannot_split_labels_or_ids(
        self, witness: str
    ) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            "aws_secret_access_key = wJalrXUtnFEMI7KMDENGbPxRfiCYEXAMPLEKEY",
            "AWS_SECRET_ACCESS_KEY=syntheticvalue",
            "awsSecretAccessKey = syntheticvalue",
            '{"aws_secret_access_key":"wJalrXUtnFEMI7KMDENGbPxRfiCYEXAMPLEKEY"}',
            "aws_access_key_id = AKIA1234567890ABCDEF",
            "secret_access_key = syntheticvalue",
        ),
    )
    def test_aws_secret_access_key_assignment_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            "Basic 2008 outlook was bearish",
            "Basic 2024 results were strong",
            "authorization: OAuth2 flow",
            "authorization: 2FA is required",
            "token: 12 units were issued",
            "Basic principles",
            "Basic authentication",
            "Bearer certificate",
            "Bearer obligations",
            "the client_secret field must be configured",
            "the password must be at least 8 characters",
        ),
    )
    def test_benign_financial_technical_prose_admissible(self, witness: str) -> None:
        assert not contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            "AKIA1234567890ABCDEF",
            "ASIA1234567890ABCDEF",
            "api_key = sk-abcdef1234567890",
            "ghp_abcdefghijklmnopqrstuvwxyz1234",
            "xoxb-123456789012-abcdefghijklmnopqrstuvwxyz",
        ),
    )
    def test_existing_key_and_token_families_preserved(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Uppercase cross-script homoglyphs of real credential labels and of
            # the Basic literal: re.IGNORECASE does not fold Cyrillic/Greek
            # capitals to Latin, so the map must fold them explicitly.
            "\u0410WS_SECRET_ACCESS_KEY = wJalrXUtnFEMI/K7MDENGbPxRfiCYEXAMPLEKEY",
            "\u0391WS_SECRET_ACCESS_KEY = syntheticvalue",
            "\u0420ASSWORD = syntheticvalue",
            "S\u0415CRET_ACCESS_KEY = syntheticvalue",
            "\u0420ASSWORD: abc12345",
            "\u0392asic dXNlcjpwYXNz",
        ),
    )
    def test_uppercase_homoglyph_labels_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    def test_safe_text_boundary_rejects_split_secret(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="sensitive"):
            _recommendation(summary="client_secret\u200b = abc123")

    def test_safe_text_boundary_accepts_benign_prose(self) -> None:
        recommendation = _recommendation(
            summary="Basic 2008 outlook was bearish",
            evidence_refs=(_ref("evidence:benign"),),
        )
        assert recommendation.summary == "Basic 2008 outlook was bearish"


class TestSecretHygieneBasicAndAssignmentRegression:
    """R4-F1: Basic/base64 and assignment discriminators fail closed without the
    uppercase proxy and the 8+ mixed colon rule that regressed short/all-digit/
    all-letter/mixed secrets."""

    @pytest.mark.parametrize(
        "witness",
        (
            # Basic/base64 discriminator classes (padding, uppercase/special,
            # unpadded mixed — never requiring uppercase as a proxy).
            "Basic enp6eg==",
            "Basic dXNlcg==",
            "Basic cGFzcw==",
            "Basic cGFzc3dvcmQ=",
            "Basic dXNlcjpwYXNz",
            "Basic enp6eg",
            "Basic ZW5wNmVn",
            "Basic AAAA",
            # Strong-label colon assignment: short/all-digit/all-letter/mixed.
            "password: a1b2c3",
            "password: 12345678",
            "password: hunter",
            "password: correcthorsebatterystaple",
            "password: 2008",
            "api_key: abc123",
            "api_key: 123456",
            "secret: abc123",
            "client_secret: abc123",
            "private_key: abc123",
            "credential: abc123",
            # Strong-label equals assignment remains strong for any value.
            "password = 123",
            "api_key = abc",
        ),
    )
    def test_credential_basic_and_assignment_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Basic prose: pure-digit runs, bare lowercase English words,
            # leading-capital words, all-caps acronym keywords, and fiscal
            # year-quarter labels stay admissible; only structurally
            # base64-like tokens are flagged.
            "Basic 2008 outlook was bearish",
            "Basic 2024 results were strong",
            "Basic principles",
            "Basic authentication",
            "Basic Authentication",
            "BASIC Authentication",
            "BASIC HTML",
            "Basic 2008",
            "Basic 2FA",
            "Basic 2024q1 results were strong",
            "Basic 2024h1 results",
            "Basic q12024 results",
            # Weak (prose-ambiguous) labels keep the credible-value colon shape.
            "authorization: OAuth2 flow",
            "authorization: 2FA is required",
            "authorization: delegated",
            "authorization: OAuth2",
            "token: 12 units were issued",
            "token: the gateway issued one",
            # Ambiguous bare-word labels (secret/credential) are prose unless the
            # value is digit-bearing or quoted.
            "secret: the recipe is a family tradition",
            "secret: to happiness",
            "the secret: a simple algorithm",
            "my secret: the password is stored here",
            "credential: management is quarterly",
            # Unequivocal labels ignore prose function words as bare values.
            "password: must be rotated quarterly",
            "access key: is rotated quarterly",
            # Bare field-name mentions are not secret material.
            "the client_secret field must be configured",
            "the password must be at least 8 characters",
            "the api_key must be rotated",
        ),
    )
    def test_benign_prose_stays_admissible(self, witness: str) -> None:
        assert not contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Preserved families must stay detected after the discriminator change.
            "AKIA1234567890ABCDEF",
            "ASIA1234567890ABCDEF",
            "api_key = sk-abcdef1234567890",
            "ghp_abcdefghijklmnopqrstuvwxyz1234",
            "xoxb-123456789012-abcdefghijklmnopqrstuvwxyz",
            "Bearer abcdef1234567890",
            "authorization: Bearer abcdef1234567890",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig-abcdef",
            "-----BEGIN PRIVATE KEY-----",
            "https://user:pass@example.com",
            "aws_secret_access_key = wJalrXUtnFEMI7KMDENGbPxRfiCYEXAMPLEKEY",
        ),
    )
    def test_preserved_key_token_and_userinfo_families(self, witness: str) -> None:
        assert contains_secret_material(witness)


class TestConfusableLabelEquivalence:
    """R4-F1 residual: Greek ETA/ZETA/small-eta confusables in credential labels
    are folded via bounded Unicode equivalence classes (not ad-hoc witnesses)."""

    @pytest.mark.parametrize(
        "witness",
        (
            "toke\u03b7 = abc",  # GREEK SMALL ETA -> n in "token"
            "crede\u03b7tial = abc",  # small ETA -> n in "credential"
            "authorizatio\u03b7 = abc",  # small ETA -> n in "authorization"
            "aut\u0397orization = abc",  # capital ETA -> h in "authorization"
            "authori\u0396ation = abc",  # capital ZETA -> z in "authorization"
            "authori\u03b6ation = abc",  # small zeta -> z in "authorization"
        ),
    )
    def test_greek_eta_zeta_confusables_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Non-label confusable letters do not manufacture a secret.
            "the \u03b7eta function converges",
            "a \u03b6eta distribution",
        ),
    )
    def test_confusable_outside_labels_stays_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)


class TestFormalRecommendationUncertaintyCoherence:
    """R4-F4: an unresolved contradiction must not be laundered into a formal
    recommendation; competing hypotheses stays admissible when detail-carrying."""

    def _recommendation_with(self, uncertainty: CiboUncertainty) -> CiboFormalRecommendation:
        return CiboFormalRecommendation(
            recommendation_id=UUID("30000000-0000-0000-0000-0000000000ff"),
            recommendation_code="cibo.uncertainty",
            reasoning_mode=CiboReasoningMode.HIGH,
            summary="Review exposure",
            evidence_refs=(_ref("evidence:exposure"),),
            uncertainty=uncertainty,
            issued_at=_NOW,
        )

    def test_recommendation_rejects_unresolved_contradiction(self) -> None:
        uncertainty = CiboUncertainty(
            kind=CiboUncertaintyKind.UNRESOLVED_CONTRADICTION, detail_codes=("conflict",)
        )
        with pytest.raises(CiboCognitiveValidationError, match="non-actionable"):
            self._recommendation_with(uncertainty)

    def test_recommendation_rejects_abstain_defer_kinds(self) -> None:
        for kind in (
            CiboUncertaintyKind.INSUFFICIENT_EVIDENCE,
            CiboUncertaintyKind.MORE_EVIDENCE_REQUESTED,
            CiboUncertaintyKind.ABSTAIN_DEFER,
        ):
            with pytest.raises(CiboCognitiveValidationError, match="non-actionable"):
                self._recommendation_with(CiboUncertainty(kind=kind))

    def test_recommendation_accepts_competing_hypotheses(self) -> None:
        uncertainty = CiboUncertainty(
            kind=CiboUncertaintyKind.COMPETING_HYPOTHESES, detail_codes=("h1", "h2")
        )
        recommendation = self._recommendation_with(uncertainty)
        recommendation.revalidate()
        assert recommendation.uncertainty.kind is CiboUncertaintyKind.COMPETING_HYPOTHESES

    def test_revalidate_rejects_reflective_unresolved_contradiction(self) -> None:
        recommendation = _recommendation(evidence_refs=(_ref("evidence:exposure"),))
        object.__setattr__(
            recommendation,
            "uncertainty",
            CiboUncertainty(
                kind=CiboUncertaintyKind.UNRESOLVED_CONTRADICTION, detail_codes=("conflict",)
            ),
        )
        with pytest.raises(CiboCognitiveValidationError, match="non-actionable"):
            recommendation.revalidate()


class TestSecretHygieneUnicodeNormalizationExhaustion:
    """R4-F1 root-family exhaustion: precomposed and combining diacritics are
    normalized, space-separated strong labels and fullwidth Basic homoglyphs are
    detected, and the Basic base64 discriminator is structural (non-initial
    uppercase/special, explicit padding, or unpadded mixed non-fiscal tokens)."""

    @pytest.mark.parametrize(
        "witness",
        (
            # Mn combining marks: NFKC would compose o+U+0301 -> ó and reshape the
            # label; stripping before NFKC re-joins "password"/"Basic".
            "passwo\u0301rd: abc123",
            "passwo\u0300rd: abc123",
            "passwo\u0308rd: abc123",
            "Basic\u0301 dXNlcjpwYXNz",
            # Precomposed accented homoglyphs: NFD decomposes then Mn-strips,
            # so "passwórd"/"sécret" re-join to their ASCII labels.
            "passw\u00f3rd: abc123",
            "passw\u00f3rd = abc123",
            "s\u00e9cret: abc123",
            "cl\u00edent_secret: abc123",
            # Space-separated strong labels (delimiter partition).
            "api key: abc123",
            "api key = abc123",
            "access key: abc123",
            "secret key: abc123",
            "client secret: abc123",
            "private key: abc123",
            "secret access key: abc123",
            "aws secret access key = abc123",
            "aws access key id = abc123",
            "access_key_id: abc123",
            # Fullwidth confusables that fold into the Basic scheme keyword
            # (a fullwidth B folds to ASCII "B", matching [Bb]asic).
            "\uff22asic dXNlcjpwYXNz",
            # Basic branch (b): uppercase/+// at a NON-INITIAL position in a 4+
            # base64 token (scattered uppercase is structural, not a capital word).
            "Basic aBcd",
            "Basic abCd",
            "Basic abcD",
            "Basic ab+c",
            "Basic a/bc",
            "Basic abcdefgH",
        ),
    )
    def test_unicode_and_structural_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Space-separated label WITHOUT an assignment delimiter is prose.
            "api key rotation is quarterly",
            "the access key must be rotated",
            "private key management",
            # Combining marks outside a credential label stay benign.
            "a\u0301 b\u0301 c\u0301",
            "the \u0301 accent is decorative",
            # All-caps / fullwidth-mixed Basic keyword stays prose-safe.
            "BASIC principles",
            "BASIC 2008 outlook was bearish",
            "BASIC Authentication",
            # A fullwidth A in the keyword yields "BAsic", which [Bb]asic does
            # not match, keeping the keyword prose-safe.
            "B\uff21sic Authentication",
        ),
    )
    def test_unicode_structural_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)
