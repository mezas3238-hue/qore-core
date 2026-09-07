"""Lane 6 integration/regression: reachable Trader Lab / CIBO boundaries and replay.

This is a REGRESSION/integration file, not a re-test of unit semantics. It proves
the new provider-neutral ``qore.infrastructure.traders`` package:

- does not break the existing Trader Lab imports and its DRAFT lifecycle surface;
- does not break the existing CIBO Trader Manager / Capability Profile imports and
  the fail-closed rule that ``CiboCertificationState`` can never be DEMO_ELIGIBLE;
- does not break the existing CIBO Trader Voice OPINION seam that the new
  cognitive wrapper complements;
- exposes every ``__all__`` public symbol through importlib resolution;
- keeps the five-cohort evaluator replay contract deterministic (stable config and
  methodology fingerprints); and
- preserves authority separation (no order/account/quantity/risk_approval/
  production field on the deterministic output or the cognitive opinion).
"""

from __future__ import annotations

import dataclasses
import importlib
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import qore.infrastructure.traders as traders
from qore.infrastructure.cibo.contracts import CiboFunctionalAuthority
from qore.infrastructure.cibo.trader_voice import CiboTraderVoice
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCertificationState,
    CiboEvidenceFreshness,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboSpecialtyCode,
    CiboTimeframeCode,
    CiboTradeableMarketRef,
    CiboTraderConfigFingerprint,
    build_cibo_trader_capability_profile,
)
from qore.infrastructure.cibo_trader_manager import CiboTraderManager
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.infrastructure.research_strategy_freeze import ResearchRunStrategyBinding
from qore.infrastructure.trader_lab import (
    TraderLabCandidateBinding,
    TraderLabCandidateId,
    TraderLabCandidateVersion,
    TraderLabLifecycle,
    TraderLabState,
    build_trader_lab_candidate_binding,
    start_trader_lab_lifecycle,
)
from qore.infrastructure.traders.cognitive import TraderCognitiveOpinion
from qore.infrastructure.traders.contracts import DemoTradingOutput
from qore.infrastructure.traders.evaluators import cohort_evaluators
from qore.kernel.result import Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)

_FORBIDDEN_AUTHORITY_FIELDS = frozenset(
    {"order", "account", "quantity", "risk_approval", "production"}
)


def _identity() -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily("virtual.trader.vt01"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


def _strategy_binding() -> ResearchRunStrategyBinding:
    """Build a minimal frozen strategy-binding double for the DRAFT lifecycle surface.

    ``build_trader_lab_candidate_binding`` and ``TraderLabLifecycle`` validation only
    read ``binding_fingerprint.value`` and ``manifest.content_digest.value`` to derive
    the candidate fingerprint, so a hollow frozen double (the same pattern the
    existing ``tests/infrastructure/trader_lab/conftest.py`` uses for evidence
    carriers) proves the surface without any external qualification evidence.
    """
    binding = object.__new__(ResearchRunStrategyBinding)
    object.__setattr__(binding, "binding_fingerprint", SimpleNamespace(value="a" * 64))
    object.__setattr__(
        binding,
        "manifest",
        SimpleNamespace(content_digest=SimpleNamespace(value="b" * 64)),
    )
    return binding


def _candidate_binding() -> TraderLabCandidateBinding:
    built = build_trader_lab_candidate_binding(
        candidate_id=TraderLabCandidateId(UUID("71000000-0000-0000-0000-000000000001")),
        version=TraderLabCandidateVersion("v1"),
        strategy_binding=_strategy_binding(),
    )
    assert isinstance(built, Success)
    return built.value


# --- Full changed-symbol recheck -------------------------------------------------


def test_public_symbols_resolve_via_importlib() -> None:
    module = importlib.import_module("qore.infrastructure.traders")
    assert module is traders
    assert traders.__all__ == module.__all__
    assert len(traders.__all__) > 0
    for name in traders.__all__:
        assert getattr(module, name) is not None
        assert getattr(traders, name) is not None


# --- Trader Lab compatibility ----------------------------------------------------


def test_trader_lab_draft_lifecycle_surface() -> None:
    candidate = _candidate_binding()
    assert isinstance(candidate, TraderLabCandidateBinding)
    lifecycle = start_trader_lab_lifecycle(candidate)
    assert isinstance(lifecycle, TraderLabLifecycle)
    assert lifecycle.state is TraderLabState.DRAFT
    assert lifecycle.completed_stages == ()


# --- CIBO Trader Manager compatibility -------------------------------------------


def test_cibo_certification_state_never_demo_eligible() -> None:
    assert not hasattr(CiboCertificationState, "DEMO_ELIGIBLE")
    member_names = {member.name for member in CiboCertificationState}
    member_values = {member.value for member in CiboCertificationState}
    assert "DEMO_ELIGIBLE" not in member_names
    assert "demo_eligible" not in member_values


def test_cibo_trader_manager_builds_unqualified_profile() -> None:
    profile_result = build_cibo_trader_capability_profile(
        trader_identity=_identity(),
        config_fingerprint=CiboTraderConfigFingerprint("0" * 64),
        specialty=CiboSpecialtyCode("trend-following"),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        certification_state=CiboCertificationState.UNQUALIFIED,
        freshness=CiboEvidenceFreshness(
            state=CiboEvidenceFreshnessState.CURRENT,
            as_of=_NOW,
        ),
    )
    assert isinstance(profile_result, Success)
    profile = profile_result.value
    assert profile.certification_state is CiboCertificationState.UNQUALIFIED
    assert CiboTraderManager() is not None


# --- CIBO Trader Voice compatibility ---------------------------------------------


def test_cibo_trader_voice_opinion_seam() -> None:
    voice = CiboTraderVoice(
        trader_identity=_identity(),
        observation_codes=("obs-trend",),
        reasoning_code="reasoning-trend-strength",
        opinion_code="opinion-favorable",
        evidence_refs=(CiboEvidenceRef("evidence:voice"),),
        voiced_at=_NOW,
        authority=CiboFunctionalAuthority.OPINION,
    )
    assert voice.authority is CiboFunctionalAuthority.OPINION


# --- Deterministic replay integration --------------------------------------------


def test_cohort_evaluators_deterministic_replay() -> None:
    evaluators = cohort_evaluators()
    assert len(evaluators) == 5
    methodology_fingerprints: set[str] = set()
    for evaluator in evaluators:
        config_a = evaluator.config_fingerprint()
        config_b = evaluator.config_fingerprint()
        assert config_a == config_b
        assert config_a.value == config_b.value

        methodology_a = evaluator.methodology()
        methodology_b = evaluator.methodology()
        assert isinstance(methodology_a, tuple)
        assert len(methodology_a) == 3
        assert methodology_a == methodology_b
        assert methodology_a[2] == methodology_b[2]
        assert methodology_a[2].value == methodology_b[2].value
        methodology_fingerprints.add(methodology_a[2].value)
    assert len(methodology_fingerprints) == 5


# --- Boundary integrity (authority separation) -----------------------------------


def test_output_and_opinion_authority_separation() -> None:
    for model in (DemoTradingOutput, TraderCognitiveOpinion):
        field_names = {field.name for field in dataclasses.fields(model)}
        assert not (_FORBIDDEN_AUTHORITY_FIELDS & field_names)
