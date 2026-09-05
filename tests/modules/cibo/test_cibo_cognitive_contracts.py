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


class TestCorrection009SecretClosure:
    """F1 (Correction-009): credential-label grammar is closed under compound/
    snake/kebab/camel equivalence, underscore token-prefix delimiters, and
    non-ASCII width-space separators, while Basic scheme-name prose and
    quantifier-prose stay admissible."""

    @pytest.mark.parametrize(
        "label",
        (
            "access_token", "refresh_token", "bearer_token", "auth_token",
            "id_token", "personal_access_token", "oauth_token", "slack_token",
            "github_token", "openai_key", "apiToken", "secretToken",
            "client_id", "x_auth_token",
            "access-token", "access token", "accessToken", "xAuthToken",
            "session_token", "aws_session_token", "sessionToken",
        ),
    )
    def test_compound_credential_label_assignment_detected(self, label: str) -> None:
        assert contains_secret_material(f"{label} = abc123def")
        assert contains_secret_material(f"{label}: abc123def")

    @pytest.mark.parametrize(
        "witness",
        (
            "sk_abcdefgh12345",
            "xoxb_abcdefghijklm",
            "sk-proj-abcdefghijklmnopqrstuvwxyz123456",
            "xoxb-123456789012-abcdefghijklmnopqrstuvwxyz",
        ),
    )
    def test_token_prefix_delimiter_equivalence_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            "access\u2007token: abc123",
            "client\u00a0id = abc123",
            "xoxb-a\u2007bcdefghijklm",
            "AKIA\u20071234567890ABCDEF",
            "Basic\u2007enp6eg",
            "Bearer\u00a0abcdef1234567890",
        ),
    )
    def test_width_space_separators_rejoin(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            "Basic oauth2",
            "Basic sha256",
            "Basic kerberos5",
            "Basic sha512",
        ),
    )
    def test_basic_scheme_name_prose_stays_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Only the closed English auxiliary/modal/copula verb class marks a
            # verb-phrase (predicate) after an UNEQUIVOCAL label, so these prose
            # statements stay admissible ("password: must be rotated" is prose).
            "password: must be rotated",
            "password: is rotated quarterly",
            "password: are rotated",
            "password: was reset",
            "password: should be rotated",
            "password: can be rotated",
            "password: will expire",
            "password: has expired",
        ),
    )
    def test_password_auxiliary_verb_prose_stays_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Ordinary pronouns/quantifiers/determiners/conjunctions are VALUES,
            # not prose markers: an unequivocal credential label used as an
            # assignment fails closed even when the value is a prose word
            # (R6 F1 fail-open closure). They must never be exempted merely
            # because they are "prose words".
            "password: one",
            "password: them",
            "password: each",
            "password: all",
            "password: several",
            "password: which",
            "password: because",
            "client_secret: some",
            "api key: another",
        ),
    )
    def test_unequivocal_label_pronoun_values_fail_closed(self, witness: str) -> None:
        assert contains_secret_material(witness)


class TestCorrection010CredentialTwoSidedContract:
    """R6 F1 closure: a two-sided detection contract — UNEQUIVOCAL labels fail
    closed for any non-predicate value, while COMPOUND/ambiguous labels require a
    credential-value signal (quoting or digit-bearing) rather than rejecting
    benign prose by label alone."""

    @pytest.mark.parametrize(
        "witness",
        (
            # R6 greedy false-positive witnesses: compound labels with plain-word
            # values are prose, not credentials.
            "access token: expires daily",
            "client id: unique",
            "openai key: billing",
            "personal access token: revoked",
            # Neighboring compound-label prose (same equivalence class).
            "refresh token: rotates daily",
            "bearer token: is short-lived",
            "auth token: expires hourly",
            "id token: revoked",
            "oauth token: scoped",
            "slack token: revoked",
            "github token: expired",
            "x auth token: rotated",
            "session token: reused",
            "aws session token: expires",
        ),
    )
    def test_compound_label_prose_stays_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # The SAME compound labels with a credential-value signal (digit-
            # bearing or quoted) ARE credentials.
            "access token: abc123def",
            "client id: 42ab",
            "openai key: sk-abcdef1234567890",
            "personal access token: 9f8e7d6c5b",
            "refresh token: abc123",
            "github token: ghp_abcdefghijklmnopqrstuvwxyz1234",
            'access token: "expires-daily-token"',
        ),
    )
    def test_compound_label_credential_signal_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Quoted value is always a deliberate assignment for every label.
            'password: "one"',
            'client_secret: "some"',
            'access token: "expires daily"',
            'secret: "the recipe"',
        ),
    )
    def test_quoted_values_always_credential(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # NBSP/width-space between an UNEQUIVOCAL label and a predicate verb
            # still yields prose (the verb class is the discriminator, not the
            # separator), while an NBSP inside a split token still re-joins
            # fail-closed.
            "password:\u00a0must be rotated",
            "access key:\u2007is rotated",
        ),
    )
    def test_unicode_separator_predicate_prose_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # NBSP/width-space inside an intentionally split credential token
            # re-joins and is still detected (fail closed).
            "access\u00a0token: abc123",
            "client\u2007id = abc123",
            "openai\u00a0key: abc123",
        ),
    )
    def test_unicode_separator_split_token_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)


class TestCorrection011SecretFamilyRecertification:
    """RF-1 recertification (R8): Unicode dash-homoglyph delimiter class,
    script-neutral credential-value class, and the case-sensitive provider-prefix
    / Cyrillic-Greek-Armenian label confusable classes."""

    @pytest.mark.parametrize(
        "witness",
        (
            # Unicode dash/hyphen/minus homoglyphs in the ``sk-`` provider prefix.
            "sk\u2013abcdefghijklmnopqrstuvwxyz",  # EN DASH
            "sk\u2014abcdefghijklmnopqrstuvwxyz",  # EM DASH
            "sk\u2010abcdefghijklmnopqrstuvwxyz",  # HYPHEN
            "sk\u2011abcdefghijklmnopqrstuvwxyz",  # NON-BREAKING HYPHEN
            "sk\u2012abcdefghijklmnopqrstuvwxyz",  # FIGURE DASH
            "sk\u2015abcdefghijklmnopqrstuvwxyz",  # HORIZONTAL BAR
            "sk\u2212abcdefghijklmnopqrstuvwxyz",  # MINUS SIGN
            "sk\u058aabcdefghijklmnopqrstuvwxyz",  # ARMENIAN HYPHEN
            "sk\u00adabcdefghijklmnopqrstuvwxyz",  # SOFT HYPHEN (Cf)
            "sk\U000e002dabcdefghijklmnopqrstuvwxyz",  # TAG HYPHEN-MINUS (Cf)
            "sk\u301cabcdefghijklmnopqrstuvwxyz",  # WAVE DASH
            "sk\U00010eadabcdefghijklmnopqrstuvwxyz",  # YEZIDI HYPHENATION MARK
            # Dash homoglyph in a compound credential label and Slack prefix.
            "access\u2013token: abc123def",
            "xoxb\u2013abcdefghijklm",
        ),
    )
    def test_dash_homoglyph_delimiters_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Non-Latin all-letter credential/token values under AMBIGUOUS/WEAK
            # labels (script-neutral: the alphabetic credential class is NOT
            # ASCII-script authority — Greek/Cyrillic/CJK letter runs are
            # credential-shaped too).
            "secret: αβγδεζηθικλμν",
            "token: абвгдежзиклмн",
            "secret: 密码密码密码密码密码",
            "credential: αβγδεζηθικλμν",
            "authorization: абвгдежзиклмн",
            "access_token: 密码密码密码密码密码",
            "token: αβγδεζηθικλμν",
            "openai key: абвгдежзиклмн",
        ),
    )
    def test_non_latin_all_letter_token_values_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Short all-letter prose values stay benign under the two-sided contract.
            "secret: the recipe is a family tradition",
            "credential: management is quarterly",
            "access token: expires daily",
            "token: 12 units were issued",
            "authorization: delegated",
            "openai key: billing",
        ),
    )
    def test_short_all_letter_prose_stays_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # A long all-letter word that merely HEADS a multi-word prose phrase
            # is prose, not a credential: the all-letter token value must be a
            # SINGLE complete token, never a prefix of a prose sentence.
            "secret: authentication is required",
            "token: authentication happens at the edge",
            "credential: authentication is handled by the broker",
            "authorization: authentication precedes it",
            "access token: authentication flow",
            "token: confidentiality is preserved",
            "secret: implementation is deferred",
            "credential: infrastructure is shared",
        ),
    )
    def test_long_word_headed_prose_stays_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Cyrillic GHE as an r homoglyph and Greek GAMMA as a g homoglyph.
            "passwo\u0433d = 123",
            "p\u0433ivate_key: abc123",
            "ref\u0433esh_token = abc123",
            "beare\u0433_token: abc123",
            "\u03b3ithub_token = abc123",
            # Homoglyph capitals re-join the case-sensitive AKIA/ASIA prefix.
            "\u0410KIA1234567890ABCDEF",
            "\u0391SIA1234567890ABCDEF",
            # Armenian OH/VO homoglyphs in credential labels.
            "t\u0585ken = abc123",
            "T\u0555KEN = abc123",
            "toke\u0578 = abc123",
        ),
    )
    def test_confusable_label_letters_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Non-label confusable letters stay benign.
            "the \u03b7eta function converges",
            "a \u03b6eta distribution",
        ),
    )
    def test_confusable_outside_labels_stays_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)


class TestRF1PrefixDelimiterEquivalence:
    """R8 RF-1 QF-R8-1 closure: the provider-prefix delimiter slot is a full
    equivalence class — literal ``-``/``_``, dash homoglyph, visible Po/Sm/So
    separator, and invisible delimiter — never an allowlisted dash set."""

    @pytest.mark.parametrize(
        "witness",
        (
            # U+180A MONGOLIAN NIRUGU (Po) occupies the literal prefix delimiter.
            "sk\u180aabcdefghijklmnop",
            "sk\u180a-Pro-abcdefghijklmnop",
            "xoxb\u180aabcdefghijklm",
            "Bearer\u180aabc123def",
            "Basic\u180aYWJjZA==",
            # The compound-label delimiter slot folds equivalently: the SAME
            # label with a digit-bearing value is detected (the short all-letter
            # value "abc" stays benign symmetric with ``access-token: abc``).
            "access\u180atoken: abc123",
            # Further Po/Sm/So separators (property-generated over the Po/Sm/So
            # categories, not witness-specific): middle dot, bullet, times sign,
            # hyphen bullet, minus sign.
            "sk\u00b7abcdefghijklmnop",
            "xoxb\u2022abcdefghijklm",
            "ghp\u00d7abcdefghijklmnopqrstuvwxyz1234",
            "sk\u2043abcdefghijklmnop",
            "Bearer\u2212abc123def",
            "Basic\u00b7YWJjZA==",
        ),
    )
    def test_po_sm_so_delimiter_equivalence_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # An invisible (Cf/Zs) character REPLACING the required delimiter is
            # folded to the delimiter, not stripped into a joined string that
            # evades the literal prefix grammar.
            "sk\u200babcdefghijklmnop",
            "sk\u2060abcdefghijklmnop",
            "xoxb\ufeffabcdefghijklm",
            "ghp\u200babcdefghijklmnopqrstuvwxyz1234",
            "gho\u00a0abcdefghijklmnopqrstuvwxyz1234",
        ),
    )
    def test_invisible_delimiter_replacement_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # An invisible ADJACENT to a real delimiter remains fail-closed: the
            # real delimiter survives and the invisible is stripped.
            "sk-\u200babcdefghijklmnop",
            "xoxb-\u200babcdefghijklm",
            "ghp_\u200babcdefghijklmnopqrstuvwxyz1234",
        ),
    )
    def test_invisible_adjacent_to_real_delimiter_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # An invisible char INSERTED BEFORE a real delimiter must re-join the
            # prefix to that delimiter (strip), not fold to ``-`` and double the
            # delimiter. ``gh*_``'s token class excludes ``-``/``_``, so the
            # doubling (``ghp-_…``) would fail the detector open. Regression fix.
            "ghp\u200b_abcdefghijklmnopqrstuvwxyz1234",
            "gho\u200b_abcdefghijklmnopqrstuvwxyz1234",
            "ghu\u200b_abcdefghijklmnopqrstuvwxyz1234",
            "ghs\u200b_abcdefghijklmnopqrstuvwxyz1234",
            "ghr\u200b_abcdefghijklmnopqrstuvwxyz1234",
            "ghp\ufeff_abcdefghijklmnopqrstuvwxyz1234",
            "ghp\u200c\u200d_abcdefghijklmnopqrstuvwxyz1234",
            "sk\u200b-abcdefghijklmnop",
            "s\u200bk\u200d_abcdefghijklmnop",  # split prefix + invisible + real delim
            # Invisible before a colon-confusable delimiter folds equivalently.
            "sk\u200b\u2236abcdefghijklmnop",  # ZWSP + RATIO -> sk=...
        ),
    )
    def test_invisible_before_real_delimiter_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # The confusable-folded homoglyph provider prefix + invisible
            # delimiter cross-product fails closed (the confusable fold runs
            # before the delimiter-slot inspection).
            "\u0455\u043a\u200babcdefghijklmnop",  # Cyrillic sk + ZWSP
            "\u0445\u043e\u0445b\u200babcdefghijklm",  # Cyrillic xoxb + ZWSP
        ),
    )
    def test_confusable_prefix_invisible_delimiter_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)


class TestRF1CredentialValueScriptClosure:
    """R8 RF-1 QF-R8-2/QF-R8-3 closure: credential-value detection is not
    ASCII-script authority, and benign Latin prose (terminal single word, comma
    list, hyphenated compound, multi-word prose) stays admissible."""

    @pytest.mark.parametrize(
        "witness",
        (
            # The accepted R8 English-prose false positives must stay benign.
            "secret: authentication, authorization, and accounting",
            "token: authentication.",
            "access token: reconnaissance, exploitation, persistence",
            "authorization: compartmentalization",
            "credential: interoperability",
            "openai key: interoperability",
            "secret: authentication",
            "token: confidentiality, integrity, availability",
            "access token: authentication-based flows are common",
            "token: authentication-based",
            # Neighboring single-word / hyphenated Latin prose (same class).
            "secret: characterization",
            "credential: reinterpretation",
            "secret: interoperability-based",
            "token: implementation",
            "authorization: infrastructure",
        ),
    )
    def test_latin_all_letter_prose_stays_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Non-Latin all-letter values under credential-bearing labels are
            # credential-shaped (not ASCII-script authority): Greek, Cyrillic,
            # CJK, and a further representative script partition.
            "secret: αβγδεζηθικλμν",
            "token: абвгдежзиклмн",
            "secret: 密码密码密码密码密码",
            "credential: αβγδεζηθικλμν",
            "authorization: абвгдежзиклмн",
        ),
    )
    def test_non_latin_all_letter_values_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Benign multilingual prose controls: short non-Latin words and
            # multi-word non-Latin prose stay admissible.
            "token: 密码",
            "secret: 安全",
            "token: 密码安全",
            "secret: αυθεντικοποίηση και εξουσιοδότηση",
            "token: авторизация учетной записи",
            # Non-ASCII LATIN-script prose is still prose (the script check is
            # Latin-vs-non-Latin, NOT ASCII-vs-non-ASCII): Danish/Norwegian/
            # Polish/Turkish/Swedish single words stay admissible even when 8+.
            "token: økonomistyring",
            "secret: økonomistyring",
            "token: æstetikklære",
            "secret: specjalistyczne",
            "authorization: özgürleştirme",
            "credential: pålitelighet",
        ),
    )
    def test_benign_multilingual_prose_stays_admissible(self, witness: str) -> None:
        assert not contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # The Basic/Bearer delimiter fold to ``-`` must not manufacture a
            # credential from prose where a dash-equivalent sits between the
            # scheme keyword and a non-credential word.
            "Basic-principles",
            "Basic-authentication",
            "Bearer-certificate",
            "Bearer-obligations",
            "Basic-2008 outlook was bearish",
            "Bearer-certificate obligations",
        ),
    )
    def test_scheme_keyword_dash_separator_prose_stays_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)


class TestRF1AllLetterCredentialClosure:
    """R8 RF-1 L5/L4 closure: the all-letter credential-value class is not
    ASCII-script authority and not uniform-case-only. An internal Latin
    lower->upper case transition is a token/passphrase signal, and the
    confusable fold must not erase the script of a non-Latin value."""

    @pytest.mark.parametrize(
        "witness",
        (
            # Mixed-case Latin all-letter values (internal lower->upper capital)
            # are credential-shaped: an English word never carries an internal
            # case transition. These were R7-accepted and the predecessor
            # accidentally dropped them.
            "token: AbCdEfGhIjKlMn",
            "secret: aBcDeFgHiJkLmN",
            "secret: abCdefgh",
            "secret: correctHorseBatteryStaple",
            "token: qwertYuiop",
            "token: aBcDeFgH",
            "credential: AbCdEfGhIj",
            "authorization: AbCdEfGhIjKl",
            "token: accessTokenValue",
        ),
    )
    def test_mixed_case_latin_all_letter_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # A non-Latin value composed ENTIRELY of Cyrillic/Greek confusable
            # homoglyphs must keep its script: the confusable fold re-joins
            # homoglyph LABELS but must not ASCII-ify a non-Latin VALUE.
            "secret: αεικινητος",
            "secret: οοοοοοοο",
            "secret: αααααααα",
            "secret: сонетсонетсонет",
            "secret: соснасоснасосна",
        ),
    )
    def test_confusable_only_non_latin_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Mc-mark (Indic/Brahmic) scripts: vowel signs are spacing combining
            # marks (Mc) and must not split the word into sub-8-letter runs.
            "secret: हिन्दीभाषाशब्द",
            "token: বাংলাভাষাবিজ্ঞান",
            "secret: தமிழ்மொழிச்சொல்",
            "secret: కన్నడభాషాపదం",
            "secret: ਪੰਜਾਬੀਭਾਸ਼ਾਵਿਗਿਆਨ",
            "secret: ગુજરાતીભાષાવિજ્ઞાન",
            "secret: ಕನ್ನಡಭಾಷಾವಿಜ್ಞಾನ",
            "secret: മലയാളഭാഷാവിജ്ഞാനം",
            "secret: සිංහලභාෂාවිද්යාව",
            "secret: ភាសាខ្មែរវិទ្យាសាស្ត្រ",
            "secret: ภาษาไทยวิทยา",
        ),
    )
    def test_mc_mark_script_all_letter_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Uniform-case Latin all-letter tokens are prose: a bare lowercase
            # run is indistinguishable from an English word without a wordlist,
            # and a Title/all-caps run is ordinary prose. This pins the QF-R8-2
            # re-adjudication of the former 12+ ASCII length rule.
            "secret: abcdefghijklmnop",
            "access_token: abcdefghijklmnop",
            "token: abcdefghijklmnop",
            "credential: abcdefghijklmnop",
            "authorization: abcdefghijklmnop",
            "secret: correcthorsebatterystaple",
            "secret: Authentication",
            "token: AUTHENTICATION",
            "secret: ABCDEFGHIJKL",
            # Non-ASCII Latin prose and non-cased scripts stay benign when short.
            "token: økonomistyring",
            "secret: økonomistyring",
            "token: macOS",
            "token: iPhone",
        ),
    )
    def test_uniform_case_latin_all_letter_stays_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)


class TestRF1UnicodeDelimiterAndScriptClosure:
    """R8 RF-1 L3 closure: colon-confusable delimiters, Pc connector punctuation,
    and empty-name (Tangut) letters cannot fail the detector open."""

    @pytest.mark.parametrize(
        "delimiter",
        (
            "\uff1a",  # FULLWIDTH COLON
            "\u2236",  # RATIO
            "\u0589",  # ARMENIAN FULL STOP
            "\u05c3",  # HEBREW PUNCTUATION SOF PASUQ
            "\ufe13",  # PRESENTATION FORM FOR VERTICAL COLON
            "\ufe30",  # PRESENTATION FORM FOR VERTICAL TWO DOT LEADER
            "\ufe55",  # SMALL COLON
        ),
    )
    def test_colon_confusable_prefix_delimiter_detected(self, delimiter: str) -> None:
        assert contains_secret_material(f"sk{delimiter}abcdefghijklmnop")
        assert contains_secret_material(f"xoxb{delimiter}abcdefghijklm")
        assert contains_secret_material(f"ghp{delimiter}abcdefghijklmnopqrstuvwxyz1234")

    @pytest.mark.parametrize(
        "delimiter",
        (
            "\u203f",  # UNDERTIE (Pc underscore homoglyph)
            "\u2040",  # CHARACTER TIE
            "\u2054",  # INVERTED UNDERTIE
        ),
    )
    def test_pc_connector_prefix_delimiter_detected(self, delimiter: str) -> None:
        assert contains_secret_material(f"sk{delimiter}abcdefghijklmnop")

    def test_equals_and_decomposed_prefix_delimiter_detected(self) -> None:
        # The widened prefix class also covers ASCII ``=`` and a Sm char whose
        # NFD decomposition (``=`` + combining mark) leaves an ``=`` residue.
        assert contains_secret_material("sk=abcdefghijklmnop")
        assert contains_secret_material("sk\u2260abcdefghijklmnop")  # NOT EQUAL TO

    def test_tangut_empty_name_letters_are_non_latin(self) -> None:
        # Tangut letters have an empty unicodedata.name in the stdlib database;
        # they must not be misread as Latin prose.
        assert contains_secret_material("secret: " + "\U00017000" * 8)
        assert contains_secret_material("token: " + "\U000187f7" * 8)

    def test_fullwidth_colon_assignment_still_detected(self) -> None:
        # The colon-confusable ``=`` fold for label assignment must be preserved.
        assert contains_secret_material("client_secret\uff1aabc123")
        assert contains_secret_material("secret_key\uff1aabcdef")


class TestRF1InternalExpertClosure:
    """R8 RF-1 Internal Expert repair closure: URL-userinfo colon-confusables,
    invisible-split provider prefixes, and SCREAMING-prefix mixed-case values."""

    # L6 Finding 1: URL userinfo colon-confusable delimiter must not escape.
    @pytest.mark.parametrize(
        "delimiter",
        (
            "\uff1a",  # FULLWIDTH COLON
            "\u2236",  # RATIO
            "\u0589",  # ARMENIAN FULL STOP
            "\u02d0",  # MODIFIER LETTER TRIANGULAR COLON
            "\u05c3",  # HEBREW PUNCTUATION SOF PASUQ
            "\ufe13",  # PRESENTATION FORM FOR VERTICAL COLON
        ),
    )
    def test_url_userinfo_colon_confusable_detected(self, delimiter: str) -> None:
        assert contains_secret_material(f"//alice{delimiter}secret@example.com")

    def test_url_userinfo_ascii_baseline_detected(self) -> None:
        assert contains_secret_material("//alice:secret@example.com")

    # L6 Finding 2: invisible split prefix + invisible delimiter must not escape.
    @pytest.mark.parametrize(
        "witness",
        (
            "s\u0301k\u200dabcdefghijklmnop",  # Mn inside prefix + ZWJ delimiter
            "s\u200bk\u200dabcdefghijklmnop",  # ZWSP inside prefix + ZWJ delimiter
            "s\u0301k\u200babcdefghijklmnop",  # Mn inside prefix + ZWSP delimiter
            "xox\u200db\u200dabcdefghijklm",
            "gh\u200dp\u200dabcdefghijklmnopqrstuvwxyz1234",
        ),
    )
    def test_invisible_split_prefix_with_invisible_delimiter_detected(
        self, witness: str
    ) -> None:
        assert contains_secret_material(witness)

    def test_invisible_split_prefix_with_literal_delimiter_detected(self) -> None:
        # The inside-prefix invisible is stripped; the literal delimiter survives.
        assert contains_secret_material("s\u0301k-abcdefghijklmnop")
        assert contains_secret_material("s\u200bk-abcdefghijklmnop")

    # Internal Expert Finding 3: leading all-caps run + lowercase tail (an
    # internal capital with no lower->upper transition) is credential-shaped.
    @pytest.mark.parametrize(
        "witness",
        (
            "token: AUTHtoken",
            "token: TOKENValue",
            "secret: ABcdefgh",
            "token: SSHtunneling",
            "token: HTMLparser",
            "authorization: AUTHtoken",
            "credential: TOKENValue",
            "secret: ABCDEFGh",
        ),
    )
    def test_leading_caps_lowercase_tail_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Title-case / all-caps / all-lower stay prose (no internal capital).
            "token: Authentication",
            "token: AUTHENTICATION",
            "token: authentication",
            "secret: Compartmentalization",
            "authorization: INTEROPERABILITY",
            "credential: interoperability",
        ),
    )
    def test_uniform_and_title_case_stay_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)


class TestAuditRepairNFKCCompatClosure:
    """Audit repair: NFKC-compatibility forms must not fail the detector open.

    The Po/Sm/So/Pc separator fold and the provider-prefix recognition ran BEFORE
    NFKC, so (a) a compatibility form of grammar-significant punctuation
    (fullwidth/small/superscript/subscript ``=``/``.``/``@``/``+``/``"``/``'``/
    ``_``/``/``) was erased to ``-`` instead of NFKC-folding to its canonical
    delimiter, and (b) a compatibility form of a provider-prefix letter (fullwidth
    ``ｓ``, long ``ſ``, circled ``ⓢ``, mathematical-bold ``𝐬``) was not recognized,
    so an invisible delimiter in the delimiter slot was stripped into a
    delimiter-less join. Both fail the detector open (regression vs HEAD, which
    ran NFKC over the raw text). The repair makes both transforms NFKC-aware."""

    @pytest.mark.parametrize("delimiter", ("\uff1d", "\ufe66", "\u207c", "\u208c"))
    def test_equals_compat_forms_detected(self, delimiter: str) -> None:
        assert contains_secret_material(f"client_secret{delimiter}abc123")
        assert contains_secret_material(f"password{delimiter}secret")
        assert contains_secret_material(f"api_key{delimiter}abc123")

    @pytest.mark.parametrize("delimiter", ("\uff0e", "\ufe52", "\u2024"))
    def test_jwt_fullstop_compat_forms_detected(self, delimiter: str) -> None:
        jwt = f"eyJhbGciOiJIUzI1NiJ9{delimiter}eyJzdWIiOiIxIn0{delimiter}signature"
        assert contains_secret_material(jwt)

    @pytest.mark.parametrize("delimiter", ("\uff20", "\ufe6b"))
    def test_url_userinfo_at_compat_forms_detected(self, delimiter: str) -> None:
        assert contains_secret_material(f"//alice:secret{delimiter}example.com")

    @pytest.mark.parametrize("delimiter", ("\uff0b", "\ufe62", "\u207a", "\u208a", "\ufb29"))
    def test_basic_base64_plus_compat_forms_detected(self, delimiter: str) -> None:
        assert contains_secret_material(f"Basic a{delimiter}bcd")
        assert contains_secret_material(f"Basic YWJj{delimiter}ZA==")

    def test_fullwidth_solidus_quote_and_lowline_detected(self) -> None:
        assert contains_secret_material("http:\uff0f\uff0falice:secret@example.com")
        assert contains_secret_material("secret: \uff02the recipe\uff02")
        assert contains_secret_material("secret: \uff07the recipe\uff07")
        assert contains_secret_material("sk\uff3fabcdefghijklmnop")

    @pytest.mark.parametrize(
        "witness",
        (
            "\uff53\uff4b\u200babcdefghijklmnop",  # fullwidth sk + ZWSP
            "\uff58\uff4f\uff58\uff42\u200babcdefghijklm",  # fullwidth xoxb + ZWSP
            "\uff47\uff48\uff50\u200babcdefghijklmnopqrstuvwxyz1234",  # fullwidth ghp
            "\u017fk\u200babcdefghijklmnop",  # long s + k + ZWSP
            "\u24e2\u24da\u200babcdefghijklmnop",  # circled sk + ZWSP
            "\U0001d42c\U0001d424\u200babcdefghijklmnop",  # math-bold sk + ZWSP
            "\uff53\u200b\uff4b\u200babcdefghijklmnop",  # fullwidth s<ZWSP>k<ZWSP>
            "\uff53\uff4b\u00a0abcdefghijklmnop",  # fullwidth sk + NBSP
            "\uff53\uff4b\ufeffabcdefghijklmnop",  # fullwidth sk + BOM
            "\uff53\uff4b\u200dabcdefghijklmnop",  # fullwidth sk + ZWJ
        ),
    )
    def test_nfkc_compat_prefix_invisible_delimiter_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            "token: 12 units were issued",
            "secret: the recipe is a family tradition",
            "Basic principles",
            "Basic 2008 outlook was bearish",
            "the client_secret field must be configured",
            "authorization: delegated",
        ),
    )
    def test_benign_prose_still_admissible(self, witness: str) -> None:
        assert not contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            "sk\u00b7abcdefghijklmnop",  # middle dot still folds to the delimiter
            "sk\u180aabcdefghijklmnop",  # nirugu still folds to the delimiter
            "sk\u203fabcdefghijklmnop",  # undertie still folds to the delimiter
            "xoxb\u2022abcdefghijklm",  # bullet still folds to the delimiter
        ),
    )
    def test_true_separators_still_fold_to_delimiter(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Invisible Cf dashes (soft hyphen U+00AD / tag hyphen U+E002D) must
            # re-join inside a token/label, not split it to a visible ``-``.
            "s\u00adk-abcdefghijklmnop",  # soft hyphen inside the sk prefix
            "s\U000e002dk-abcdefghijklmnop",  # tag hyphen inside the sk prefix
            "p\u00adassword: abc123",  # soft hyphen inside the password label
            "c\u00adlient_secret=abc123",  # soft hyphen inside the client label
            "/\u00ad/alice:secret@example.com",  # soft hyphen inside the URL ``//``
            "sk\u00adabcdefghijklmnop",  # soft hyphen in the delimiter slot folds
            "sk\U000e002dabcdefghijklmnop",  # tag hyphen in the delimiter slot folds
            "access\u00adtoken: abc123",  # soft hyphen inside a compound label
        ),
    )
    def test_invisible_cf_dash_rejoins_token(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # Unmapped colon-lookalikes (siblings of the mapped RATIO U+2236) fold
            # to the STRONG ``=`` too, so they cannot fail the detector open.
            "password\u2237secret",  # PROPORTION
            "password\u205asecret",  # TWO DOT PUNCTUATION
            "client_secret\u2237abc123",
            "client_secret\u205aabc123",
            "sk\u2237abcdefghijklmnop",
            "sk\u205aabcdefghijklmnop",
        ),
    )
    def test_unmapped_colon_confusables_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)


class TestAuditRepairHomoglyphLabelScriptClosure:
    """Audit repair: a homoglyph-normalized credential LABEL plus a non-Latin
    VALUE composed entirely of confusable homoglyph letters must not escape.

    The confusable-FOLDED skeleton ASCII-ifies the value (hiding its script, so
    it reads as uniform Latin prose) while the script-preserving skeleton must
    still see the homoglyph label through a confusable-insensitive label
    spelling. The two transforms must not fail open in their cross-product."""

    @pytest.mark.parametrize(
        "witness",
        (
            # Homoglyph label + confusable-only non-Latin value (the exact gap).
            "sеcret: αεικινητος",  # CYRILLIC SMALL IE for e
            "sеcret: οοοοοοοο",  # Cyrillic e + Greek omicron-only value
            "sеcret: αααααααα",
            "sεcret: αεικινητος",  # GREEK SMALL EPSILON for e
            "σecret: αεικινητος",  # GREEK SMALL SIGMA for s
            "ѕecret: αεικινητος",  # CYRILLIC SMALL DZE for s
            "seсret: αεικινητος",  # CYRILLIC SMALL ES for c
            "secгet: αεικινητος",  # CYRILLIC SMALL GHE for r
            "secreτ: αεικινητος",  # GREEK SMALL TAU for t
            "tоken: αεικινητος",  # CYRILLIC SMALL O for o
            "tοken: αεικινητος",  # GREEK SMALL OMICRON for o
            "tоκen: αεικινητος",  # Cyrillic o + Greek kappa
            "credentіal: αεικινητος",  # CYRILLIC BYELORUSSIAN-UKRAINIAN I for i
            "authorizatiоn: αεικινητος",  # Cyrillic o in authorization
            "access_tоken: αεικινητος",  # Cyrillic o in compound label
            "оpenai_key: αεικινητος",  # Cyrillic o in openai_key
        ),
    )
    def test_homoglyph_label_confusable_value_detected(self, witness: str) -> None:
        assert contains_secret_material(witness)

    @pytest.mark.parametrize(
        "witness",
        (
            # A homoglyph label with a uniform-case LATIN value is still prose:
            # the label spelling must not manufacture a credential from prose.
            "sеcret: authentication",
            "sеcret: abcdefghijklmnop",
            "tоken: authentication",
            "σecret: compartmentalization",
        ),
    )
    def test_homoglyph_label_uniform_latin_value_stays_benign(self, witness: str) -> None:
        assert not contains_secret_material(witness)

    def test_homoglyph_label_detection_is_invariant(self) -> None:
        # Metamorphic: replacing any ASCII letter of a credential label with its
        # confusable homoglyph must not change the all-letter-value verdict for
        # ANY value class (non-Latin, confusable-only, mixed-case, uniform Latin).
        homoglyph_variants = {
            "secret": ("sеcret", "sεcret", "σecret", "ѕecret", "seсret", "secгet", "secreτ"),
            "token": ("tоken", "tοken", "tоκen"),
            "authorization": ("authorizatiоn",),
            "credential": ("credentіal",),
        }
        values = (
            "αεικινητος",  # confusable-only non-Latin
            "οοοοοοοο",  # confusable-only non-Latin (omicron)
            "αβγδεζηθικλμν",  # non-confusable non-Latin
            "AbCdEfGhIj",  # mixed-case Latin
            "abcdefghijklmnop",  # uniform Latin prose
        )
        for label, variants in homoglyph_variants.items():
            for value in values:
                expected = contains_secret_material(f"{label}: {value}")
                for variant in variants:
                    assert (
                        contains_secret_material(f"{variant}: {value}") == expected
                    ), f"{variant}: {value} diverged from {label}: {value}"
