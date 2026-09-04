"""Provider-neutral CIBO Cognitive Executive contracts.

This module defines the pure, deterministic semantic foundation for CIBO as a
Cognitive Executive Director. It is intentionally free of any concrete LLM,
model, provider, adapter, or execution authority: it only shapes reasoning
modes, epistemic states, uncertainty, deliberation roles, and formal
recommendations.

Canonical law enforced here:

- CIBO INTELLIGENCE != UNBOUNDED AUTHORITY
- CIBO RECOMMENDATION != RISK BYPASS
- CIBO REASONING != PROVIDER-NATIVE ORDER
- FORMAL_RECOMMENDATION != AUTHORIZED_ACTION

No value object in this module carries an order, intent, account, credential,
quantity, instrument, provider, or promotion field.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import IGNORECASE, Pattern, compile, fullmatch
from unicodedata import normalize as _unicodedata_normalize
from uuid import UUID

from qore.kernel.errors import DomainError
from qore.kernel.temporal import canonical_instant

_CODE_RE = r"[a-z][a-z0-9._-]*"
_OPAQUE_REF_RE = r"[a-z][a-z0-9._:/-]*"

# Structural, low-false-positive secret-material patterns. Detection-only:
# never rewrite text, only reject it (fail closed).
#
# Boundary semantics (law 20 + "no naive substring false positives"):
#   - provider tokens (sk-/AKIA/gh*_/xox/JWT) and URL userinfo are matched by
#     their own structural shape with word/length/character-class bounds;
#   - credential labels (client_secret, private_key, api_key, token, password,
#     authorization, ...) are matched ONLY in assignment form `label[=:] value`
#     (the key/value patterns below) — never as a bare field-name mention. A bare
#     identifier such as ``client_secret_demo`` or prose like "the client_secret
#     field must be configured" is not itself secret material and is accepted.
#   - private-key material is matched structurally via the PEM block marker.
#
# Assignment value credibility (law "no naive benign-prose false positives"):
#   - a quoted value (single or double, non-empty) is always credible, since an
#     explicit quote signals a deliberate value assignment;
#   - a bare value after ``=`` (equals) is credible for any non-empty token, as
#     ``=`` is essentially never natural-language prose punctuation;
#   - a bare value after ``:`` (colon) is credible only when it carries a digit,
#     because ``label:`` followed by a bare lowercase English word is ordinary
#     prose (e.g. "authorization: delegated", "password:less"). Callers carrying
#     a low-entropy colon-separated secret must quote it (``password: "secret"``).
_CRED_LABEL = (
    r"(?:password|passwd|api[_-]?key|access[_-]?key|secret[_-]?key|"
    r"client[_-]?secret|private[_-]?key|credential|authorization|token|secret)"
)
_QUOTED_VALUE = r"[\"'][^\"'\n]+[\"']"
_BARE_ANY_VALUE = r"[^\s\"']+"
_BARE_CREDIBLE_VALUE = r"(?=[^\s\"']*\d)[^\s\"']+"

# Unicode colon-confusables that fold to STRONG ``=`` before NFKC. NFKC itself
# collapses ``：`` (U+FF1A) to ASCII ``:`` and ``︰`` (U+FE30) to ``..``, which would
# lose the adversarial-delimiter signal; a full-width/confusable colon never
# appears in natural prose, so it is treated as an explicit value assignment.
# Detection-only: applied to a transient skeleton, never to persisted/user text.
_DELIMITER_CONFUSABLE_MAP = str.maketrans(
    {
        "\u02d0": "=",  # MODIFIER LETTER TRIANGULAR COLON
        "\u02f8": "=",  # MODIFIER LETTER RAISED COLON
        "\u0589": "=",  # ARMENIAN FULL STOP
        "\u05c3": "=",  # HEBREW PUNCTUATION SOF PASUQ
        "\u2236": "=",  # RATIO
        "\ua789": "=",  # MODIFIER LETTER COLON
        "\ufe13": "=",  # PRESENTATION FORM FOR VERTICAL COLON
        "\ufe30": "=",  # PRESENTATION FORM FOR VERTICAL TWO DOT LEADER
        "\ufe55": "=",  # SMALL COLON
        "\uff1a": "=",  # FULLWIDTH COLON
    }
)

# Confusable label characters (Cyrillic/Greek homoglyphs of the Latin letters
# used by credential labels). Detection-only: applied to a transient skeleton,
# never to persisted/user text.
_CONFUSABLE_MAP = str.maketrans(
    {
        "\u0430": "a",  # CYRILLIC SMALL A
        "\u0432": "b",  # CYRILLIC SMALL VE
        "\u0441": "c",  # CYRILLIC SMALL ES
        "\u0435": "e",  # CYRILLIC SMALL IE
        "\u0455": "s",  # CYRILLIC SMALL DZE
        "\u0456": "i",  # CYRILLIC SMALL BYELORUSSIAN-UKRAINIAN I
        "\u0458": "j",  # CYRILLIC SMALL JE
        "\u043a": "k",  # CYRILLIC SMALL KA
        "\u043c": "m",  # CYRILLIC SMALL EM
        "\u043d": "n",  # CYRILLIC SMALL EN
        "\u043e": "o",  # CYRILLIC SMALL O
        "\u0440": "p",  # CYRILLIC SMALL ER
        "\u0442": "t",  # CYRILLIC SMALL TE
        "\u0443": "y",  # CYRILLIC SMALL U
        "\u0445": "x",  # CYRILLIC SMALL HA
        "\u0437": "z",  # CYRILLIC SMALL ZE
        "\u03b1": "a",  # GREEK SMALL LETTER ALPHA
        "\u03b5": "e",  # GREEK SMALL LETTER EPSILON
        "\u03b9": "i",  # GREEK SMALL LETTER IOTA
        "\u03ba": "k",  # GREEK SMALL LETTER KAPPA
        "\u03bd": "n",  # GREEK SMALL LETTER NU
        "\u03bf": "o",  # GREEK SMALL LETTER OMICRON
        "\u03c1": "p",  # GREEK SMALL LETTER RHO
        "\u03c2": "s",  # GREEK SMALL LETTER FINAL SIGMA
        "\u03c3": "s",  # GREEK SMALL LETTER SIGMA
        "\u03c4": "t",  # GREEK SMALL LETTER TAU
        "\u03c5": "u",  # GREEK SMALL LETTER UPSILON
        "\u03c7": "x",  # GREEK SMALL LETTER CHI
    }
)

_SECRET_PATTERNS: tuple[Pattern[str], ...] = (
    compile(r"-----BEGIN [A-Z ]*(?:PRIVATE KEY|SECRET|ENCRYPTED PRIVATE KEY)-----"),
    compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    # AWS access key ids: permanent (AKIA) and temporary (ASIA) prefixes.
    compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    compile(r"\bxox[baprsc]-[A-Za-z0-9-]{10,}"),
    # Bearer tokens are high-entropy: require a digit inside an 8+ char token so
    # prose like "Bearer certificate"/"Bearer obligations" is not a false positive.
    compile(
        r"\bBearer\s+(?=[A-Za-z0-9._~+/=-]{8,})"
        r"[A-Za-z0-9._~+/=-]*[0-9][A-Za-z0-9._~+/=-]*",
        IGNORECASE,
    ),
    # Bare HTTP Basic authorization: base64 body carrying at least one
    # uppercase/digit/base64-special character. Case-sensitive on purpose: the
    # discriminator must not match all-lowercase prose like "Basic principles"
    # or "Basic authentication", while still matching real base64 credentials
    # (e.g. "Basic dXNlcjpwYXNz").
    compile(
        r"\b[Bb]asic\s+(?=[A-Za-z0-9+/]{4,}={0,2}\b)"
        r"(?=[A-Za-z0-9+/]*[A-Z0-9+/])[A-Za-z0-9+/]+={0,2}"
    ),
    compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}"),
    compile(r"//[^/@\s:]+:[^/@\s]+@"),
    # Equals assignment: strong. Any non-empty bare token or quoted value.
    compile(
        rf"(?i)\b{_CRED_LABEL}\b[\"']?\s*=\s*(?:{_QUOTED_VALUE}|{_BARE_ANY_VALUE})"
    ),
    # Colon assignment: weak (prose-ambiguous). Quoted or digit-bearing only.
    compile(
        rf"(?i)\b{_CRED_LABEL}\b[\"']?\s*:\s*(?:{_QUOTED_VALUE}|{_BARE_CREDIBLE_VALUE})"
    ),
)

_CONTROL_CHARS = "\x00\n\r\t"


def _secret_skeleton(text: str) -> str:
    """Return a detection-only normalized view of ``text``.

    Unicode colon-confusables fold to a strong ``=`` first (before NFKC, which
    would otherwise collapse them to a weak ``:``); NFKC then folds remaining
    full-width delimiters/alphanumerics; finally the bounded confusable map folds
    common Cyrillic/Greek homoglyphs of credential-label letters. The original
    text is never rewritten: this view is used only to run the fail-closed
    detection patterns.
    """
    return (
        _unicodedata_normalize("NFKC", text.translate(_DELIMITER_CONFUSABLE_MAP))
        .translate(_CONFUSABLE_MAP)
    )


class CiboCognitiveError(DomainError):
    """Base error for CIBO Cognitive Executive provider-neutral contracts."""

    __slots__ = ()


class CiboCognitiveValidationError(CiboCognitiveError):
    """A CIBO cognitive value violates a deterministic provider-neutral invariant."""

    __slots__ = ()


def contains_secret_material(text: str) -> bool:
    """Return whether ``text`` carries structural secret-bearing material.

    Requires an exact ``str`` (``str`` subclasses are rejected fail-closed).
    Detection-only: never rewrites the input; callers decide to reject.
    """
    if type(text) is not str:
        raise CiboCognitiveValidationError(
            f"secret detection input must be an exact str, not {type(text).__name__}"
        )
    skeleton = _secret_skeleton(text)
    return any(pattern.search(skeleton) is not None for pattern in _SECRET_PATTERNS)


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboCognitiveValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCognitiveValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if type(value) is not str or fullmatch(_CODE_RE, value) is None:
        raise CiboCognitiveValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )
    if contains_secret_material(value):
        raise CiboCognitiveValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_codes(
    values: tuple[str, ...],
    *,
    field_name: str,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    if type(values) is not tuple or any(type(v) is not str for v in values):
        raise CiboCognitiveValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(v, field_name=field_name) for v in values)
    if len(set(normalized)) != len(normalized):
        raise CiboCognitiveValidationError(f"{field_name} must not contain duplicates")
    if not allow_empty and not normalized:
        raise CiboCognitiveValidationError(f"{field_name} must be non-empty")
    return tuple(sorted(normalized))


def _validate_opaque_ref(value: str, *, field_name: str) -> str:
    if type(value) is not str or fullmatch(_OPAQUE_REF_RE, value) is None:
        raise CiboCognitiveValidationError(
            f"{field_name} must use canonical opaque-reference syntax"
        )
    if contains_secret_material(value):
        raise CiboCognitiveValidationError(f"{field_name} must not contain sensitive material")
    return value


def _validate_safe_text(value: str, *, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise CiboCognitiveValidationError(f"{field_name} must be non-empty text")
    if any(ch in value for ch in _CONTROL_CHARS):
        raise CiboCognitiveValidationError(f"{field_name} must not contain control characters")
    if contains_secret_material(value):
        raise CiboCognitiveValidationError(f"{field_name} must not contain sensitive material")
    return value


def _canonical_evidence_refs(
    values: tuple[CiboCognitiveEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboCognitiveEvidenceRef, ...]:
    if type(values) is not tuple or any(
        type(item) is not CiboCognitiveEvidenceRef for item in values
    ):
        raise CiboCognitiveValidationError(
            f"{field_name} must be an immutable tuple of CiboCognitiveEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboCognitiveValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


class CiboReasoningMode(StrEnum):
    """Reasoning-policy semantics, never a concrete model/token/API setting."""

    FAST = "fast"
    HIGH = "high"
    MAX = "max"
    COUNCIL_ADVERSARIAL = "council-adversarial"


class CiboEpistemicState(StrEnum):
    """Epistemic strength of a CIBO cognitive statement. None is an action."""

    OBSERVATION = "observation"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    OPINION = "opinion"
    FORMAL_RECOMMENDATION = "formal-recommendation"


class CiboUncertaintyKind(StrEnum):
    """Explicit uncertainty outcomes; bounded confidence is only one possibility."""

    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    UNRESOLVED_CONTRADICTION = "unresolved-contradiction"
    COMPETING_HYPOTHESES = "competing-hypotheses"
    MORE_EVIDENCE_REQUESTED = "more-evidence-requested"
    ABSTAIN_DEFER = "abstain-defer"
    BOUNDED_CONFIDENCE = "bounded-confidence"


class CiboConfidenceLevel(StrEnum):
    """Bounded confidence levels; never a raw float or bool."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Uncertainty kinds that semantically abstain/request more evidence rather than
# assert an actionable conclusion. An action/decision carrier (formal
# recommendation, recommend directive, decision synthesis) must never carry one
# of these, and an abstain/defer/non-decision carrier must never carry
# BOUNDED_CONFIDENCE.
_ABSTENTION_UNCERTAINTY_KINDS = frozenset(
    {
        CiboUncertaintyKind.INSUFFICIENT_EVIDENCE,
        CiboUncertaintyKind.MORE_EVIDENCE_REQUESTED,
        CiboUncertaintyKind.ABSTAIN_DEFER,
    }
)


@dataclass(frozen=True, slots=True)
class CiboCognitiveEvidenceRef:
    """Opaque sanitized reference to evidence stored outside the cognitive value."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_opaque_ref(self.value, field_name="CIBO cognitive evidence ref"),
        )

    def revalidate(self) -> None:
        _validate_opaque_ref(self.value, field_name="CIBO cognitive evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CiboDeliberationRole:
    """Canonical provider-neutral deliberation faculty/role identity.

    A role emits an evidence-bound argument, critique, or opinion; it carries no
    operational privilege and no execution/promotion authority.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_code(self.value, field_name="CIBO deliberation role"),
        )

    def revalidate(self) -> None:
        _validate_code(self.value, field_name="CIBO deliberation role")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CiboConfidence:
    """Bounded confidence that is always justified by explicit evidence."""

    level: CiboConfidenceLevel
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if type(self.level) is not CiboConfidenceLevel:
            raise CiboCognitiveValidationError(
                "CIBO confidence requires CiboConfidenceLevel"
            )
        refs = _canonical_evidence_refs(
            self.evidence_refs,
            field_name="CIBO confidence evidence",
        )
        if not refs:
            raise CiboCognitiveValidationError(
                "bounded confidence requires explicit backing evidence"
            )
        object.__setattr__(self, "evidence_refs", refs)
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.level) is not CiboConfidenceLevel:
            raise CiboCognitiveValidationError(
                "CIBO confidence requires CiboConfidenceLevel"
            )
        if not self.evidence_refs:
            raise CiboCognitiveValidationError(
                "bounded confidence requires explicit backing evidence"
            )
        if self.evidence_refs != _canonical_evidence_refs(
            self.evidence_refs,
            field_name="CIBO confidence evidence",
        ):
            raise CiboCognitiveValidationError(
                "CIBO confidence evidence failed canonical revalidation"
            )
        for ref in self.evidence_refs:
            ref.revalidate()

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.level.value,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class CiboUncertainty:
    """Explicit uncertainty carried by a cognitive statement.

    BOUNDED_CONFIDENCE requires a ``CiboConfidence``; COMPETING_HYPOTHESES and
    UNRESOLVED_CONTRADICTION require non-empty detail codes so uncertainty is
    never collapsed into fabricated certainty.
    """

    kind: CiboUncertaintyKind
    detail_codes: tuple[str, ...] = ()
    confidence: CiboConfidence | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not CiboUncertaintyKind:
            raise CiboCognitiveValidationError(
                "CIBO uncertainty requires CiboUncertaintyKind"
            )
        object.__setattr__(
            self,
            "detail_codes",
            _validate_codes(self.detail_codes, field_name="CIBO uncertainty detail"),
        )
        if self.kind is CiboUncertaintyKind.BOUNDED_CONFIDENCE:
            if type(self.confidence) is not CiboConfidence:
                raise CiboCognitiveValidationError(
                    "bounded confidence uncertainty requires CiboConfidence"
                )
            if self.detail_codes:
                raise CiboCognitiveValidationError(
                    "bounded confidence uncertainty must not carry detail codes"
                )
        else:
            if self.confidence is not None:
                raise CiboCognitiveValidationError(
                    "non-bounded uncertainty must not carry confidence"
                )
            if self.kind in (
                CiboUncertaintyKind.COMPETING_HYPOTHESES,
                CiboUncertaintyKind.UNRESOLVED_CONTRADICTION,
            ) and not self.detail_codes:
                raise CiboCognitiveValidationError(
                    f"{self.kind.value} uncertainty requires detail codes"
                )
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.kind) is not CiboUncertaintyKind:
            raise CiboCognitiveValidationError(
                "CIBO uncertainty requires CiboUncertaintyKind"
            )
        if self.detail_codes != _validate_codes(
            self.detail_codes,
            field_name="CIBO uncertainty detail",
        ):
            raise CiboCognitiveValidationError(
                "CIBO uncertainty detail failed canonical revalidation"
            )
        if self.kind is CiboUncertaintyKind.BOUNDED_CONFIDENCE:
            if type(self.confidence) is not CiboConfidence:
                raise CiboCognitiveValidationError(
                    "bounded confidence uncertainty requires CiboConfidence"
                )
            if self.detail_codes:
                raise CiboCognitiveValidationError(
                    "bounded confidence uncertainty must not carry detail codes"
                )
            self.confidence.revalidate()
        elif self.confidence is not None:
            raise CiboCognitiveValidationError(
                "non-bounded uncertainty must not carry confidence"
            )
        if self.kind in (
            CiboUncertaintyKind.COMPETING_HYPOTHESES,
            CiboUncertaintyKind.UNRESOLVED_CONTRADICTION,
        ) and not self.detail_codes:
            raise CiboCognitiveValidationError(
                f"{self.kind.value} uncertainty requires detail codes"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            self.detail_codes,
            None if self.confidence is None else self.confidence.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CiboEpistemicClaim:
    """One evidence-bound cognitive statement (observation/…/hypothesis/opinion)."""

    claim_id: UUID
    epistemic_state: CiboEpistemicState
    reasoning_mode: CiboReasoningMode
    content_code: str
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]
    uncertainty: CiboUncertainty
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.claim_id) is not UUID:
            raise CiboCognitiveValidationError("CIBO epistemic claim id must be UUID")
        if type(self.epistemic_state) is not CiboEpistemicState:
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires CiboEpistemicState"
            )
        if self.epistemic_state is CiboEpistemicState.FORMAL_RECOMMENDATION:
            raise CiboCognitiveValidationError(
                "formal recommendations must use CiboFormalRecommendation"
            )
        if type(self.reasoning_mode) is not CiboReasoningMode:
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires CiboReasoningMode"
            )
        object.__setattr__(
            self,
            "content_code",
            _validate_code(self.content_code, field_name="CIBO claim content code"),
        )
        refs = _canonical_evidence_refs(self.evidence_refs, field_name="CIBO claim evidence")
        if not refs:
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires explicit backing evidence"
            )
        object.__setattr__(self, "evidence_refs", refs)
        if type(self.uncertainty) is not CiboUncertainty:
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires CiboUncertainty"
            )
        object.__setattr__(
            self,
            "limitations",
            _validate_codes(self.limitations, field_name="CIBO claim limitations"),
        )
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.claim_id) is not UUID:
            raise CiboCognitiveValidationError("CIBO epistemic claim id must be UUID")
        if type(self.epistemic_state) is not CiboEpistemicState:
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires CiboEpistemicState"
            )
        if self.epistemic_state is CiboEpistemicState.FORMAL_RECOMMENDATION:
            raise CiboCognitiveValidationError(
                "formal recommendations must use CiboFormalRecommendation"
            )
        if type(self.reasoning_mode) is not CiboReasoningMode:
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires CiboReasoningMode"
            )
        _validate_code(self.content_code, field_name="CIBO claim content code")
        if not self.evidence_refs:
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires explicit backing evidence"
            )
        if self.evidence_refs != _canonical_evidence_refs(
            self.evidence_refs,
            field_name="CIBO claim evidence",
        ):
            raise CiboCognitiveValidationError(
                "CIBO claim evidence failed canonical revalidation"
            )
        for ref in self.evidence_refs:
            ref.revalidate()
        if type(self.uncertainty) is not CiboUncertainty:
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires CiboUncertainty"
            )
        self.uncertainty.revalidate()
        if self.limitations != _validate_codes(
            self.limitations,
            field_name="CIBO claim limitations",
        ):
            raise CiboCognitiveValidationError(
                "CIBO claim limitations failed canonical revalidation"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.claim_id),
            self.epistemic_state.value,
            self.reasoning_mode.value,
            self.content_code,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.uncertainty.logical_values(),
            self.limitations,
        )


@dataclass(frozen=True, slots=True)
class CiboFormalRecommendation:
    """A formal, evidence-bound recommendation. Advisory only: never an action.

    This value object deliberately exposes no order, intent, account, quantity,
    instrument, provider, promotion, or authorization field. Downstream
    operational authority can only be created by separate Policy/Risk/Execution
    contracts, never by this recommendation.
    """

    recommendation_id: UUID
    recommendation_code: str
    reasoning_mode: CiboReasoningMode
    summary: str
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]
    uncertainty: CiboUncertainty
    issued_at: datetime
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.recommendation_id) is not UUID:
            raise CiboCognitiveValidationError(
                "CIBO recommendation id must be UUID"
            )
        object.__setattr__(
            self,
            "recommendation_code",
            _validate_code(self.recommendation_code, field_name="CIBO recommendation code"),
        )
        if type(self.reasoning_mode) is not CiboReasoningMode:
            raise CiboCognitiveValidationError(
                "CIBO recommendation requires CiboReasoningMode"
            )
        object.__setattr__(
            self,
            "summary",
            _validate_safe_text(self.summary, field_name="CIBO recommendation summary"),
        )
        refs = _canonical_evidence_refs(
            self.evidence_refs,
            field_name="CIBO recommendation evidence",
        )
        if not refs:
            raise CiboCognitiveValidationError(
                "a formal recommendation requires explicit backing evidence"
            )
        object.__setattr__(self, "evidence_refs", refs)
        if type(self.uncertainty) is not CiboUncertainty:
            raise CiboCognitiveValidationError(
                "CIBO recommendation requires CiboUncertainty"
            )
        if self.uncertainty.kind in _ABSTENTION_UNCERTAINTY_KINDS:
            raise CiboCognitiveValidationError(
                "a formal recommendation must not carry abstention-kind uncertainty"
            )
        object.__setattr__(
            self,
            "limitations",
            _validate_codes(self.limitations, field_name="CIBO recommendation limitations"),
        )
        _validate_aware_datetime(self.issued_at, field_name="CIBO recommendation issued_at")
        self.revalidate()

    @property
    def epistemic_state(self) -> CiboEpistemicState:
        """A formal recommendation is FORMAL_RECOMMENDATION, never an action."""
        return CiboEpistemicState.FORMAL_RECOMMENDATION

    def revalidate(self) -> None:
        if type(self.recommendation_id) is not UUID:
            raise CiboCognitiveValidationError("CIBO recommendation id must be UUID")
        _validate_code(self.recommendation_code, field_name="CIBO recommendation code")
        if type(self.reasoning_mode) is not CiboReasoningMode:
            raise CiboCognitiveValidationError(
                "CIBO recommendation requires CiboReasoningMode"
            )
        _validate_safe_text(self.summary, field_name="CIBO recommendation summary")
        if not self.evidence_refs:
            raise CiboCognitiveValidationError(
                "a formal recommendation requires explicit backing evidence"
            )
        if self.evidence_refs != _canonical_evidence_refs(
            self.evidence_refs,
            field_name="CIBO recommendation evidence",
        ):
            raise CiboCognitiveValidationError(
                "CIBO recommendation evidence failed canonical revalidation"
            )
        for ref in self.evidence_refs:
            ref.revalidate()
        if type(self.uncertainty) is not CiboUncertainty:
            raise CiboCognitiveValidationError(
                "CIBO recommendation requires CiboUncertainty"
            )
        if self.uncertainty.kind in _ABSTENTION_UNCERTAINTY_KINDS:
            raise CiboCognitiveValidationError(
                "a formal recommendation must not carry abstention-kind uncertainty"
            )
        self.uncertainty.revalidate()
        if self.limitations != _validate_codes(
            self.limitations,
            field_name="CIBO recommendation limitations",
        ):
            raise CiboCognitiveValidationError(
                "CIBO recommendation limitations failed canonical revalidation"
            )
        _validate_aware_datetime(self.issued_at, field_name="CIBO recommendation issued_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.recommendation_id),
            self.recommendation_code,
            self.reasoning_mode.value,
            self.summary,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.uncertainty.logical_values(),
            self.limitations,
            canonical_instant(self.issued_at),
        )
