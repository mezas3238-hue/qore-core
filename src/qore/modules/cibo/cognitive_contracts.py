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
from unicodedata import category as _unicodedata_category
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
#   - a bare value after ``:`` (colon) is tiered by label ambiguity:
#     * UNEQUIVOCAL labels (password, api_key, client_secret, private_key,
#       access/secret key, AWS labels) are technical identifiers, so
#       ``label: value`` is credential material for any non-empty bare or quoted
#       value (short/all-digit/all-letter/mixed), EXCEPT the closed English
#       auxiliary/modal/copula verb class — the value position of a verb phrase
#       is never a value ("password: must be rotated", "access key: is rotated"
#       stay prose). Ordinary pronouns/quantifiers such as one/them/some/another
#       ARE values and fail closed ("password: one" is a credential).
#     * AMBIGUOUS labels (secret, credential, and the compound token/key/id
#       labels below) are common English words/phrases, so a bare value is
#       credible only when digit-bearing or quoted ("access token: abc123" is a
#       credential, "access token: expires daily" is prose).
#     * WEAK labels (authorization, token) are prose-ambiguous, so a bare value
#       is credible only as an 8+ char token carrying BOTH a letter and a digit
#       ("authorization: delegated", "authorization: OAuth2", "token: 12 units"
#       stay admissible).
# Compound credential labels closed under snake/kebab/space/camel separators.
# ``[ _-]?`` matches zero (camelCase ``accessToken`` -> ``access`` + ``Token``)
# or one snake/kebab/space separator, and ``re.IGNORECASE`` folds the casing, so
# ``access_token`` / ``access-token`` / ``access token`` / ``accessToken`` are one
# equivalence class. These token/key/id phrases are prose-ambiguous, so they
# belong to the AMBIGUOUS tier: ``label: value`` is credential material only for
# a digit-bearing or quoted value, never by label alone.
_COMPOUND_CRED_LABEL = (
    r"access[ _-]?token|refresh[ _-]?token|bearer[ _-]?token|auth[ _-]?token|"
    r"id[ _-]?token|personal[ _-]?access[ _-]?token|oauth[ _-]?token|"
    r"slack[ _-]?token|github[ _-]?token|openai[ _-]?key|client[ _-]?id|"
    r"x[ _-]?auth[ _-]?token|api[ _-]?token|secret[ _-]?token|"
    r"session[ _-]?token|aws[ _-]?session[ _-]?token"
)
_UNEQUIVOCAL_CRED_LABEL = (
    r"password|passwd|api[ _-]?key|access[ _-]?key|secret[ _-]?key|"
    r"client[ _-]?secret|private[ _-]?key|access[ _-]?key[ _-]?id|"
    r"secret[ _-]?access[ _-]?key|aws[ _-]?secret[ _-]?access[ _-]?key|"
    r"aws[ _-]?access[ _-]?key[ _-]?id|awssecretaccesskey|awsaccesskeyid"
)
_AMBIGUOUS_CRED_LABEL = r"credential|" + _COMPOUND_CRED_LABEL + r"|secret"
_WEAK_CRED_LABEL = r"authorization|token"
_CRED_LABEL = (
    r"(?:" + _UNEQUIVOCAL_CRED_LABEL + r"|"
    + _AMBIGUOUS_CRED_LABEL + r"|" + _WEAK_CRED_LABEL + r")"
)
_QUOTED_VALUE = r"[\"'][^\"'\n]+[\"']"
_BARE_ANY_VALUE = r"[^\s\"']+"
# A bare (unquoted) colon value for an AMBIGUOUS label is credible when it
# carries a digit (any length): "secret: abc123" is a credential while
# "secret: the recipe" is prose. (This is the pre-regression digit-bearing
# shape, retained for the prose-ambiguous bare-word labels only.)
_BARE_DIGIT_VALUE = r"(?=[^\s\"']*\d)[^\s\"']+"
# A bare (unquoted) colon value for a WEAK label is credible only as an 8+ char
# mixed token carrying BOTH a letter and a digit. Short tokens like "OAuth2",
# "2FA", "12", or "2008" are ordinary prose/numbers and stay admissible.
_BARE_CREDIBLE_VALUE = r"(?=[^\s\"']*\d)(?=[^\s\"']*[A-Za-z])[^\s\"']{8,}"
# The English auxiliary/modal/copula verb CLOSED class. Only this class can
# never be a credential value, because it marks the START of a verb phrase
# (predicate), not a value assignment: "password: must be rotated" and
# "access key: is rotated" are prose about the credential, not a credential.
# Ordinary pronouns/quantifiers/determiners/prepositions/conjunctions are NOT
# verbs and therefore remain candidate values that must fail closed
# ("password: one", "password: them", "client_secret: some", "api key: another"
# are credentials). This is a principled structural discriminator (a fixed
# closed linguistic class), NOT an ever-growing stopword list.
_COLON_PREDICATE_VERBS = frozenset(
    {
        "am", "is", "are", "was", "were", "be", "been", "being",
        "has", "have", "had", "do", "does", "did",
        "must", "should", "shall", "will", "would", "can", "could", "may", "might",
    }
)
_COLON_PREDICATE_VERB_RE = (
    r"(?:" + "|".join(sorted(_COLON_PREDICATE_VERBS, key=len, reverse=True)) + r")\b"
)
_UNEQUIVOCAL_BARE_VALUE = rf"(?!{_COLON_PREDICATE_VERB_RE}){_BARE_ANY_VALUE}"

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
# used by credential labels, both cases: re.IGNORECASE does not fold across
# scripts, so uppercase homoglyphs must be folded explicitly). Detection-only:
# applied to a transient skeleton, never to persisted/user text.
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
        "\u0410": "a",  # CYRILLIC CAPITAL A
        "\u0412": "b",  # CYRILLIC CAPITAL VE
        "\u0421": "c",  # CYRILLIC CAPITAL ES
        "\u0415": "e",  # CYRILLIC CAPITAL IE
        "\u0405": "s",  # CYRILLIC CAPITAL DZE
        "\u0406": "i",  # CYRILLIC CAPITAL BYELORUSSIAN-UKRAINIAN I
        "\u0408": "j",  # CYRILLIC CAPITAL JE
        "\u041a": "k",  # CYRILLIC CAPITAL KA
        "\u041c": "m",  # CYRILLIC CAPITAL EM
        "\u041d": "n",  # CYRILLIC CAPITAL EN
        "\u041e": "o",  # CYRILLIC CAPITAL O
        "\u0420": "p",  # CYRILLIC CAPITAL ER
        "\u0422": "t",  # CYRILLIC CAPITAL TE
        "\u0423": "y",  # CYRILLIC CAPITAL U
        "\u0425": "x",  # CYRILLIC CAPITAL HA
        "\u0417": "z",  # CYRILLIC CAPITAL ZE
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
        "\u0391": "a",  # GREEK CAPITAL LETTER ALPHA
        "\u0392": "b",  # GREEK CAPITAL LETTER BETA
        "\u0395": "e",  # GREEK CAPITAL LETTER EPSILON
        "\u0399": "i",  # GREEK CAPITAL LETTER IOTA
        "\u039a": "k",  # GREEK CAPITAL LETTER KAPPA
        "\u039d": "n",  # GREEK CAPITAL LETTER NU
        "\u039f": "o",  # GREEK CAPITAL LETTER OMICRON
        "\u03a1": "p",  # GREEK CAPITAL LETTER RHO
        "\u03a3": "s",  # GREEK CAPITAL LETTER SIGMA
        "\u03a4": "t",  # GREEK CAPITAL LETTER TAU
        "\u03a5": "u",  # GREEK CAPITAL LETTER UPSILON
        "\u03a7": "x",  # GREEK CAPITAL LETTER CHI
        "\u03b6": "z",  # GREEK SMALL LETTER ZETA
        "\u03b7": "n",  # GREEK SMALL LETTER ETA
        "\u0396": "z",  # GREEK CAPITAL LETTER ZETA
        "\u0397": "h",  # GREEK CAPITAL LETTER ETA
    }
)

_SECRET_PATTERNS: tuple[Pattern[str], ...] = (
    compile(r"-----BEGIN [A-Z ]*(?:PRIVATE KEY|SECRET|ENCRYPTED PRIVATE KEY)-----"),
    # OpenAI secret keys: ``sk-`` and its delimiter-equivalent ``sk_``.
    compile(r"\bsk[-_][A-Za-z0-9_-]{8,}"),
    # AWS access key ids: permanent (AKIA) and temporary (ASIA) prefixes.
    compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    # Slack tokens: ``xox*`` prefix with hyphen or its delimiter-equivalent
    # underscore.
    compile(r"\bxox[baprsc][-_][A-Za-z0-9-]{10,}"),
    # Bearer tokens are high-entropy: require a digit inside an 8+ char token so
    # prose like "Bearer certificate"/"Bearer obligations" is not a false positive.
    # ``\s*`` (not ``\s+``) because the detection skeleton strips non-ASCII width
    # spaces that a caller may insert between the keyword and the token; after
    # stripping, keyword and token are re-joined and must still match.
    compile(
        r"\bBearer\s*(?=[A-Za-z0-9._~+/=-]{8,})"
        r"[A-Za-z0-9._~+/=-]*[0-9][A-Za-z0-9._~+/=-]*",
        IGNORECASE,
    ),
    # Bare HTTP Basic authorization: base64 material, discriminated structurally
    # rather than by requiring uppercase as a proxy for credential-ness. The
    # scheme keyword stays ``[Bb]asic`` (the original, prose-safe shape): the
    # all-caps "BASIC" keyword is far more often the BASIC programming language
    # or an acronym than a credential, so case-insensitive matching was dropped
    # to avoid new prose false positives ("BASIC Authentication", "BASIC HTML").
    # A Basic credential is detected when the token is (a) base64 with explicit
    # ``=`` padding, (b) unpadded 4+ base64 chars carrying an uppercase or
    # base64-special char at a NON-INITIAL position (a scattered/internal
    # uppercase is structural; a leading-capital English word is not), or
    # (c) unpadded 6+ mixed letter+digit token whose digit is INTERNAL (a digit
    # followed by a letter/+//), i.e. scattered base64, not a trailing-version
    # scheme name ("oauth2", "sha256", "kerberos5" keep their digit(s) at the
    # tail and stay admissible). A pure digit run ("2008"), a bare lowercase
    # word ("principles"), a leading-capital word ("Authentication"), and fiscal
    # labels ("2024q1") stay admissible.
    compile(
        r"\b[Bb]asic\s*"
        r"(?:"
        r"[A-Za-z0-9+/]{2,}={1,2}"
        r"|"
        r"(?=[A-Za-z0-9+/][A-Za-z0-9+/]*[A-Z+/])[A-Za-z0-9+/]{4,}"
        r"|"
        r"(?=[A-Za-z0-9+/]*[A-Za-z])(?=[A-Za-z0-9+/]*\d[A-Za-z+/])"
        r"(?!\d{2,4}[QqHh]\d)(?![QqHh]\d{1,4})"
        r"[A-Za-z0-9+/]{6,}"
        r")"
        r"(?![A-Za-z0-9+/=])"
    ),
    compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}"),
    compile(r"//[^/@\s:]+:[^/@\s]+@"),
    # Equals assignment: strong for every label. Any non-empty bare or quoted value.
    compile(
        rf"(?i)\b{_CRED_LABEL}\b[\"']?\s*=\s*(?:{_QUOTED_VALUE}|{_BARE_ANY_VALUE})"
    ),
    # Unequivocal-label colon assignment: credential for any non-stopword bare or
    # quoted value (short/all-digit/all-letter/mixed values alike).
    compile(
        rf"(?i)\b(?:{_UNEQUIVOCAL_CRED_LABEL})\b[\"']?\s*:\s*"
        rf"(?:{_QUOTED_VALUE}|{_UNEQUIVOCAL_BARE_VALUE})"
    ),
    # Ambiguous-label colon assignment: prose-ambiguous. Quoted or digit-bearing.
    compile(
        rf"(?i)\b(?:{_AMBIGUOUS_CRED_LABEL})\b[\"']?\s*:\s*"
        rf"(?:{_QUOTED_VALUE}|{_BARE_DIGIT_VALUE})"
    ),
    # Weak-label colon assignment: prose-ambiguous. Quoted or 8+ mixed only.
    compile(
        rf"(?i)\b(?:{_WEAK_CRED_LABEL})\b[\"']?\s*:\s*(?:{_QUOTED_VALUE}|{_BARE_CREDIBLE_VALUE})"
    ),
)

_CONTROL_CHARS = "\x00\n\r\t"


# Format/control/separator categories plus nonspacing marks (Mn) that can split
# credential labels, delimiters, or key ids and fail the detector open. Mn covers
# the combining grapheme joiner U+034F, invisible variation selectors
# (U+FE00-U+FE0F, U+E0100-U+E01EF), Mongolian free variation selectors
# (U+180B-U+180D), and combining diacritics (U+0300-U+036F). Combining marks are
# stripped from the RAW text BEFORE NFKC, because NFKC would compose a base
# letter + mark into a single precomposed letter (``o + U+0301 -> ó``) and
# thereby reshape the label ("passwórd") instead of re-joining it. Stripping
# these from the detection-only skeleton can only re-join split tokens (fail
# closed) — it never rewrites the caller's text.
_INVISIBLE_CATEGORIES = frozenset({"Cf", "Cc", "Cs", "Zl", "Zp", "Mn"})


def _is_detection_invisible(ch: str) -> bool:
    """Return whether ``ch`` is stripped from the detection-only skeleton.

    Strips the format/control/separator/line/paragraph and nonspacing-mark
    categories (as before) PLUS non-ASCII space separators (width spaces, NBSP,
    …). ASCII space U+0020 is deliberately preserved: it is the ordinary word
    separator, and collapsing it would break the whitespace semantics of the
    Bearer/Basic/label patterns and join unrelated prose words. A non-ASCII
    space is never natural prose punctuation, so stripping it can only re-join
    adversarially-split credential labels or token bodies (fail closed), and is
    never applied to persisted/caller text.
    """
    category = _unicodedata_category(ch)
    if category in _INVISIBLE_CATEGORIES:
        return True
    return category == "Zs" and ch != " "


def _secret_skeleton(text: str) -> str:
    """Return a detection-only normalized view of ``text``.

    Canonical decomposition (NFD) is applied FIRST so a precomposed accented
    letter (``ó``, category Ll) decomposes to ``o + U+0301`` (Mn): then the
    invisible-category strip removes the combining mark and re-joins the label,
    symmetric with the already-handled decomposed form. Next invisible
    format/control/separator characters and nonspacing marks (zero-width
    spaces, joiners, bidi marks, BOM, variation selectors, combining grapheme
    joiner, combining diacritics, …) are stripped: combining marks must be
    removed before NFKC, which would otherwise compose ``o + U+0301`` into a
    single ``ó`` and reshape the label. Then Unicode colon-confusables fold to a
    strong ``=`` (before NFKC, which would collapse them to a weak ``:``); NFKC
    folds remaining full-width delimiters/alphanumerics; the bounded confusable
    map folds common Cyrillic/Greek homoglyphs of credential-label letters;
    finally any residual invisible category is stripped again for safety. The
    original text is never rewritten: this view is used only to run the
    fail-closed detection patterns.
    """
    decomposed = _unicodedata_normalize("NFD", text)
    visible = "".join(ch for ch in decomposed if not _is_detection_invisible(ch))
    normalized = _unicodedata_normalize(
        "NFKC", visible.translate(_DELIMITER_CONFUSABLE_MAP)
    ).translate(_CONFUSABLE_MAP)
    return "".join(ch for ch in normalized if not _is_detection_invisible(ch))


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
ABSTENTION_UNCERTAINTY_KINDS = frozenset(
    {
        CiboUncertaintyKind.INSUFFICIENT_EVIDENCE,
        CiboUncertaintyKind.MORE_EVIDENCE_REQUESTED,
        CiboUncertaintyKind.ABSTAIN_DEFER,
    }
)

# Uncertainty kinds that must never be laundered into an actionable carrier
# (formal recommendation, brain RECOMMEND directive, council DECISION synthesis):
# the abstain/request/defer kinds plus UNRESOLVED_CONTRADICTION, an open
# epistemic contradiction that cannot be asserted as an advisory action.
# COMPETING_HYPOTHESES stays admissible because it is substantive,
# detail-carrying uncertainty rather than an abstention or an open contradiction.
NON_ACTIONABLE_UNCERTAINTY_KINDS = frozenset(ABSTENTION_UNCERTAINTY_KINDS) | {
    CiboUncertaintyKind.UNRESOLVED_CONTRADICTION,
}


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
        if self.uncertainty.kind in NON_ACTIONABLE_UNCERTAINTY_KINDS:
            raise CiboCognitiveValidationError(
                "a formal recommendation must not carry non-actionable uncertainty"
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
        if self.uncertainty.kind in NON_ACTIONABLE_UNCERTAINTY_KINDS:
            raise CiboCognitiveValidationError(
                "a formal recommendation must not carry non-actionable uncertainty"
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
