from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.research_strategy_freeze import (
    ResearchRunStrategyBinding,
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding
from qore.infrastructure.trader_lab.cohort import FirstCohortTraderLabEntry
from qore.infrastructure.trader_lab.first_cohort_failure_analysis import (
    FirstCohortFailureAnalysisError,
)
from qore.infrastructure.trader_lab.first_cohort_research_dossiers import (
    _CODES,
    _SYMBOLS,
    _lifecycle_stage_statuses,
    _write_reports,
    build_research_reports,
)
from qore.infrastructure.trader_lab.lifecycle import (
    MANDATORY_STAGES,
    TraderLabPromotionRequest,
    TraderLabState,
    apply_trader_lab_promotion,
    start_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabStage,
    TraderLabStageEvidenceRecord,
)
from qore.infrastructure.traders.contracts import DemoTradingTraderCode
from qore.kernel.result import Success

_SHA = "b" * 40
_ACCOUNT = "a" * 64


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _profile(code: str, *, symbol: str | None = None) -> dict[str, object]:
    setup = []
    if symbol is not None:
        setup = [
            {
                "exit_at": f"2026-01-{index + 1:02d}T00:00:00+00:00",
                "return_rate": "0.01" if index % 2 == 0 else "-0.005",
            }
            for index in range(6)
        ]
    return {
        "profile": "production-default",
        "selected_by_in_sample_only": False,
        "config_fingerprint": f"config-{code}",
        "parameters": {},
        "methodology_identity": {
            "trader_version": "1.0.0",
            "methodology_id": f"method-{code}",
            "methodology_version": "1.0.0",
            "methodology_fingerprint": f"methodology-{code}",
            "timeframe": "M5",
            "session": "all",
        },
        "setups": setup,
        "decision_funnel": {"setup": len(setup), "filled": len(setup)},
        "classification_labels": ["sparse_opportunity"],
    }


def _rows(*, symbol: str | None = None) -> list[dict[str, object]]:
    return [
        {
            "trader_code": code,
            "methodology_component_map": {"ordered_components": ["signal"]},
            "profiles": [_profile(code, symbol=symbol)],
        }
        for code in _CODES
    ]


def _build_fixture(root: Path) -> tuple[Path, Path]:
    evidence = root / "evidence"
    aggregate = root / "aggregate"
    for symbol in _SYMBOLS:
        directory = evidence / symbol
        common = {"software_sha": _SHA, "symbol": symbol}
        _write(
            directory / "market-evidence.json",
            {
                "software_sha": _SHA,
                "symbol": {"symbol_name": symbol},
                "environment": "demo",
                "read_only": True,
                "account_is_live": False,
                "trading_permission_verified": True,
                "account_fingerprint": _ACCOUNT,
                "coverage": {
                    period: {
                        "span_seconds": 730 * 24 * 60 * 60,
                        "bar_count": 2,
                        "first_opened_at": "2024-01-01T00:00:00+00:00",
                        "last_closed_at": "2025-12-31T00:00:00+00:00",
                    }
                    for period in ("M5", "M15", "H4")
                },
            },
        )
        _write(directory / "backtest.json", common)
        _write(directory / "walk-forward.json", common)
        _write(
            directory / "characterization.json",
            {
                **common,
                "account_fingerprint": _ACCOUNT,
                "results": _rows(symbol=symbol),
            },
        )
        _write(
            directory / "failure-analysis.json",
            {
                **common,
                "account_fingerprint": _ACCOUNT,
                "results": [
                    {"trader_code": code, "failure_stage": "in_sample"}
                    for code in _CODES
                ],
            },
        )

    aggregate_common = {"software_sha": _SHA, "account_fingerprint": _ACCOUNT}
    _write(
        aggregate / "multi-pair-walk-forward.json",
        {
            **aggregate_common,
            "results": [
                {
                    "trader_code": code,
                    "robust_pass": False,
                    "pooled_in_sample": {"sample_size": 36},
                    "pooled_oos": {"sample_size": 12},
                    "pooled_stressed_oos": {"sample_size": 12},
                }
                for code in _CODES
            ],
        },
    )
    _write(
        aggregate / "characterization-aggregate.json",
        {**aggregate_common, "results": _rows()},
    )
    _write(
        aggregate / "failure-analysis-aggregate.json",
        {
            **aggregate_common,
            "results": [
                {"trader_code": code, "classification_labels": ["sparse_opportunity"]}
                for code in _CODES
            ],
        },
    )
    _write(
        aggregate / "hypothesis-register.json",
        {
            **aggregate_common,
            "hypotheses": [
                {"trader": code, "hypothesis_id": f"HYP-{code.upper()}-001"}
                for code in _CODES
            ],
        },
    )
    return evidence, aggregate


def test_builds_five_complete_dossiers_and_governed_reports(tmp_path: Path) -> None:
    evidence, aggregate = _build_fixture(tmp_path)

    first = build_research_reports(evidence, aggregate, software_sha=_SHA)
    second = build_research_reports(evidence, aggregate, software_sha=_SHA)

    assert first == second
    assert tuple(first) == (
        *(f"{code}-deep-characterization-dossier.json" for code in _CODES),
        "first-cohort-comparative-deep-characterization-report.json",
        "holdout-register.json",
        "promotion-report.json",
    )
    for code in _CODES:
        dossier = first[f"{code}-deep-characterization-dossier.json"]
        provenance = cast(dict[str, object], dossier["data_provenance"])
        battery = cast(dict[str, object], dossier["evaluation_battery"])
        stages = cast(dict[str, object], dossier["lifecycle_stages"])
        research_vs = cast(dict[str, object], dossier["research_vs_lifecycle"])
        monte_carlo = cast(dict[str, object], dossier["monte_carlo"])
        promotion = cast(dict[str, object], dossier["promotion"])
        governance = cast(dict[str, object], dossier["holdout_governance"])
        assert dossier["software_sha"] == _SHA
        assert provenance["minimum_required_days"] == 730
        # The research battery is descriptive and must never claim the formal
        # lifecycle Replay gate or the governed authority stages.
        assert battery["descriptive_monte_carlo"] == "completed"
        assert battery["closed_bar_characterization"] == "completed"
        assert "replay" not in battery
        assert "risk_review" not in battery
        assert "cibo_review" not in battery
        assert "independent_validation" not in battery
        assert "economic_evidence" not in battery
        # Research-only dossier: all 10 governed lifecycle stages are not supplied.
        assert set(stages) == {
            "research",
            "replay",
            "fast_forward",
            "oos",
            "stress",
            "monte_carlo",
            "risk_review",
            "cibo_review",
            "independent_validation",
            "economic_evidence",
        }
        assert all(value == "not_supplied" for value in stages.values())
        assert research_vs["lifecycle_materialized"] is False
        assert research_vs["research_battery_completed"] is True
        assert monte_carlo["simulations"] == 1000
        assert promotion["demo_eligible"] is False
        assert promotion["state"] == "research_only"
        assert governance[
            "consumed_holdout_cannot_certify_modified_strategy"
        ] is True
    assert first["promotion-report.json"]["demo_eligible_count"] == 0
    assert first["first-cohort-comparative-deep-characterization-report.json"][
        "five_dossiers_complete"
    ] is True

    output = tmp_path / "output"
    _write_reports(output, first)
    assert sorted(path.name for path in output.iterdir()) == sorted(first)
    assert all(path.read_bytes().endswith(b"\n") for path in output.iterdir())


def test_rejects_less_than_730_effective_days(tmp_path: Path) -> None:
    evidence, aggregate = _build_fixture(tmp_path)
    path = evidence / _SYMBOLS[0] / "market-evidence.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    # 729d 23:59:59 actual span, with the declared span kept consistent so the
    # fail-closed "less than 730 effective days" branch is exercised (not the
    # declared-vs-actual mismatch branch).
    payload["coverage"]["M5"]["last_closed_at"] = "2025-12-30T23:59:59+00:00"
    payload["coverage"]["M5"]["span_seconds"] = 729 * 24 * 60 * 60 - 1
    _write(path, payload)

    with pytest.raises(FirstCohortFailureAnalysisError, match="less than 730"):
        build_research_reports(evidence, aggregate, software_sha=_SHA)


def test_rejects_declared_span_mismatch_and_mixed_account(tmp_path: Path) -> None:
    evidence, aggregate = _build_fixture(tmp_path)
    path = evidence / _SYMBOLS[0] / "market-evidence.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    # Actual span is 730 days but the declared span is off by one second.
    payload["coverage"]["M5"]["span_seconds"] -= 1
    _write(path, payload)
    with pytest.raises(FirstCohortFailureAnalysisError, match="span mismatch"):
        build_research_reports(evidence, aggregate, software_sha=_SHA)

    # A second DEMO account cannot be laundered into the cohort.
    evidence, aggregate = _build_fixture(tmp_path)
    path = evidence / _SYMBOLS[1] / "market-evidence.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["account_fingerprint"] = "f" * 64
    _write(path, payload)
    with pytest.raises(FirstCohortFailureAnalysisError, match="mixed DEMO accounts"):
        build_research_reports(evidence, aggregate, software_sha=_SHA)


def test_rejects_non_demo_or_live_market_evidence(tmp_path: Path) -> None:
    evidence, aggregate = _build_fixture(tmp_path)
    path = evidence / _SYMBOLS[0] / "market-evidence.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["environment"] = "live"
    _write(path, payload)
    with pytest.raises(FirstCohortFailureAnalysisError, match="must be DEMO"):
        build_research_reports(evidence, aggregate, software_sha=_SHA)

    evidence, aggregate = _build_fixture(tmp_path)
    path = evidence / _SYMBOLS[0] / "market-evidence.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["account_is_live"] = True
    _write(path, payload)
    with pytest.raises(FirstCohortFailureAnalysisError, match="LIVE account"):
        build_research_reports(evidence, aggregate, software_sha=_SHA)


def test_rejects_mixed_software_sha_and_incomplete_cohort(tmp_path: Path) -> None:
    evidence, aggregate = _build_fixture(tmp_path)
    path = aggregate / "hypothesis-register.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["software_sha"] = "c" * 40
    _write(path, payload)
    with pytest.raises(FirstCohortFailureAnalysisError, match="exact software SHA"):
        build_research_reports(evidence, aggregate, software_sha=_SHA)

    _build_fixture(tmp_path)
    path = aggregate / "characterization-aggregate.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["results"] = payload["results"][:-1]
    _write(path, payload)
    with pytest.raises(FirstCohortFailureAnalysisError, match="identity/order"):
        build_research_reports(evidence, aggregate, software_sha=_SHA)


def test_lifecycle_stage_statuses_none_is_all_not_supplied() -> None:
    statuses = _lifecycle_stage_statuses(None)
    assert set(statuses) == {
        "research",
        "replay",
        "fast_forward",
        "oos",
        "stress",
        "monte_carlo",
        "risk_review",
        "cibo_review",
        "independent_validation",
        "economic_evidence",
    }
    assert all(value == "not_supplied" for value in statuses.values())


def test_lifecycle_stage_statuses_research_only_lifecycle(
    candidate_factory: Callable[..., TraderLabCandidateBinding],
    stage_evidence_factory: Callable[..., TraderLabStageEvidenceRecord],
) -> None:
    # The mandatory chain is RESEARCH -> REPLAY -> ...; a lifecycle promoted only
    # through RESEARCH reports RESEARCH completed and every later stage not_started.
    candidate = candidate_factory(candidate_suffix=701)
    lifecycle = start_trader_lab_lifecycle(candidate)
    research_evidence = stage_evidence_factory(
        stage=TraderLabStage.RESEARCH,
        candidate=candidate,
        evidence_suffix=9_700,
    )
    promoted = apply_trader_lab_promotion(
        lifecycle,
        TraderLabPromotionRequest(stage=TraderLabStage.RESEARCH, evidence=research_evidence),
    )
    assert isinstance(promoted, Success)
    lifecycle = promoted.value

    statuses = _lifecycle_stage_statuses(lifecycle)
    assert statuses["research"] == "completed"
    assert statuses["replay"] == "not_started"
    assert statuses["fast_forward"] == "not_started"
    assert statuses["monte_carlo"] == "not_started"
    assert statuses["risk_review"] == "not_started"
    assert statuses["economic_evidence"] == "not_started"
    assert lifecycle.state is TraderLabState.RESEARCH_READY


def test_lifecycle_by_trader_validation_is_fail_closed(tmp_path: Path) -> None:
    evidence, aggregate = _build_fixture(tmp_path)

    with pytest.raises(FirstCohortFailureAnalysisError, match="first-cohort"):
        build_research_reports(
            evidence,
            aggregate,
            software_sha=_SHA,
            lifecycle_by_trader=cast(
                Mapping[str, FirstCohortTraderLabEntry], {"vt-99": object()}
            ),
        )
    with pytest.raises(FirstCohortFailureAnalysisError, match="FirstCohortTraderLabEntry"):
        build_research_reports(
            evidence,
            aggregate,
            software_sha=_SHA,
            lifecycle_by_trader=cast(
                Mapping[str, FirstCohortTraderLabEntry], {"vt-01": "not-an-entry"}
            ),
        )
    with pytest.raises(FirstCohortFailureAnalysisError, match="string-keyed"):
        build_research_reports(
            evidence,
            aggregate,
            software_sha=_SHA,
            lifecycle_by_trader=cast(
                Mapping[str, FirstCohortTraderLabEntry], {1: "vt-01"}
            ),
        )


def test_lifecycle_stage_statuses_monte_carlo_external_stages_blocked(
    candidate_factory: Callable[..., TraderLabCandidateBinding],
    stage_evidence_factory: Callable[..., TraderLabStageEvidenceRecord],
) -> None:
    """External-governed stages are 'blocked_external' once Monte Carlo is reached.

    Stress is completed before Monte Carlo; Risk/CIBO/independent validation
    follow Monte Carlo and require an owning authority, so a lifecycle at
    MONTE_CARLO_QUALIFIED reports them blocked_external, and economic evidence
    not_started. This mirrors evaluate_demo_eligibility's
    EXTERNAL_EVIDENCE_DEPENDENT branch without fabricating a completed stage.
    """
    candidate = candidate_factory(candidate_suffix=702)
    lifecycle = start_trader_lab_lifecycle(candidate)
    for offset, stage in enumerate(
        (
            TraderLabStage.RESEARCH,
            TraderLabStage.REPLAY,
            TraderLabStage.FAST_FORWARD,
            TraderLabStage.OOS,
            TraderLabStage.STRESS,
            TraderLabStage.MONTE_CARLO,
        )
    ):
        evidence = stage_evidence_factory(
            stage=stage,
            candidate=candidate,
            evidence_suffix=9_800 + offset,
        )
        promoted = apply_trader_lab_promotion(
            lifecycle,
            TraderLabPromotionRequest(stage=stage, evidence=evidence),
        )
        assert isinstance(promoted, Success)
        lifecycle = promoted.value
    assert lifecycle.state is TraderLabState.MONTE_CARLO_QUALIFIED

    statuses = _lifecycle_stage_statuses(lifecycle)
    for stage_name in ("research", "replay", "fast_forward", "oos", "stress", "monte_carlo"):
        assert statuses[stage_name] == "completed"
    for stage_name in ("risk_review", "cibo_review", "independent_validation"):
        assert statuses[stage_name] == "blocked_external"
    assert statuses["economic_evidence"] == "not_started"


def _first_cohort_binding(
    strategy_binding_factory: Callable[..., ResearchRunStrategyBinding],
    *,
    suffix: int,
    code: str,
) -> ResearchRunStrategyBinding:
    """Build a first-cohort strategy binding carrying the mandatory Trader params.

    The frozen manifest must include ``trader.code`` (plus the remaining five
    first-cohort Trader/instrument binding parameters) so the dossier builder can
    cross-check the entry label against the lifecycle's candidate binding.
    """
    base = strategy_binding_factory(configuration_id_suffix=suffix)
    manifest = build_research_strategy_configuration_manifest(
        configuration_id=base.run.strategy_configuration_id,
        schema_version=base.manifest.schema_version,
        parameters=(
            ResearchStrategyParameter("trader.code", code),
            ResearchStrategyParameter("trader.config_fingerprint", f"config-{code}"),
            ResearchStrategyParameter("trader.instrument", "EURUSD"),
            ResearchStrategyParameter(
                "trader.methodology_fingerprint", f"methodology-{code}"
            ),
            ResearchStrategyParameter("trader.methodology_id", f"method-{code}"),
            ResearchStrategyParameter("trader.methodology_version", "1.0.0"),
        ),
        frozen_at=base.manifest.frozen_at,
        evidence_ref=ResearchStrategyFreezeEvidenceReference(
            UUID(f"73000000-0000-0000-0000-{suffix:012d}")
        ),
    )
    assert isinstance(manifest, Success)
    built = build_research_run_strategy_binding(run=base.run, manifest=manifest.value)
    assert isinstance(built, Success)
    return built.value


def _hollow_entry(
    lifecycle: object,
    economic_evidence: object,
    *,
    trader_code: str = "vt-01",
) -> FirstCohortTraderLabEntry:
    """Build a minimal reflection shell reusing a fully validated lifecycle.

    The dossier reflection only reads ``trader_code``, ``lifecycle``, and
    ``economic_evidence``; the remaining fields are irrelevant to the wiring and
    are deliberately left unset (mirroring the conftest hollow-object pattern).
    """
    entry = object.__new__(FirstCohortTraderLabEntry)
    object.__setattr__(entry, "trader_code", DemoTradingTraderCode(trader_code))
    object.__setattr__(entry, "lifecycle", lifecycle)
    object.__setattr__(entry, "economic_evidence", economic_evidence)
    return entry


def test_lifecycle_reflection_reflects_demo_eligible_lifecycle(
    tmp_path: Path,
    strategy_binding_factory: Callable[..., ResearchRunStrategyBinding],
    candidate_factory: Callable[..., TraderLabCandidateBinding],
    stage_evidence_factory: Callable[..., TraderLabStageEvidenceRecord],
) -> None:
    """A supplied DEMO_ELIGIBLE lifecycle is reflected truthfully via the canonical gate.

    Only vt-01 is supplied; the other four codes fall back to the research-only
    scaffold. The promotion report counts exactly the one DEMO_ELIGIBLE Trader and
    the dossier never invents authority (it reuses evaluate_demo_eligibility).
    """
    binding = _first_cohort_binding(strategy_binding_factory, suffix=703, code="vt-01")
    candidate = candidate_factory(candidate_suffix=703, binding=binding)
    lifecycle = start_trader_lab_lifecycle(candidate)
    for offset, stage in enumerate(MANDATORY_STAGES):
        evidence = stage_evidence_factory(
            stage=stage,
            candidate=candidate,
            evidence_suffix=9_900 + offset,
        )
        promoted = apply_trader_lab_promotion(
            lifecycle,
            TraderLabPromotionRequest(stage=stage, evidence=evidence),
        )
        assert isinstance(promoted, Success)
        lifecycle = promoted.value
    assert lifecycle.state is TraderLabState.DEMO_ELIGIBLE
    economic_evidence = lifecycle.qualifications[-1].evidence.source_reference
    entry = _hollow_entry(lifecycle, economic_evidence)

    evidence_root, aggregate = _build_fixture(tmp_path)
    reports = build_research_reports(
        evidence_root, aggregate, software_sha=_SHA, lifecycle_by_trader={"vt-01": entry}
    )

    vt01 = reports["vt-01-deep-characterization-dossier.json"]
    vt01_stages = cast(dict[str, object], vt01["lifecycle_stages"])
    vt01_promotion = cast(dict[str, object], vt01["promotion"])
    assert all(value == "completed" for value in vt01_stages.values())
    assert vt01_promotion["demo_eligible"] is True
    assert vt01_promotion["state"] == "demo_eligible"
    assert vt01_promotion["promotion_status"] == "demo_eligible"
    assert vt01_promotion["blockers"] == ()
    assert cast(dict[str, object], vt01["research_vs_lifecycle"])[
        "lifecycle_materialized"
    ] is True

    for code in ("vt-08", "vt-09", "vt-17", "vt-31"):
        dossier = reports[f"{code}-deep-characterization-dossier.json"]
        stages = cast(dict[str, object], dossier["lifecycle_stages"])
        promotion = cast(dict[str, object], dossier["promotion"])
        assert all(value == "not_supplied" for value in stages.values())
        assert promotion["demo_eligible"] is False
        assert promotion["state"] == "research_only"

    assert reports["promotion-report.json"]["demo_eligible_count"] == 1


def test_lifecycle_reflection_blocks_incomplete_lifecycle_without_fake_pass(
    tmp_path: Path,
    strategy_binding_factory: Callable[..., ResearchRunStrategyBinding],
    candidate_factory: Callable[..., TraderLabCandidateBinding],
    stage_evidence_factory: Callable[..., TraderLabStageEvidenceRecord],
) -> None:
    """Benign control: an incomplete governed lifecycle never surfaces as eligible.

    A MONTE_CARLO_QUALIFIED lifecycle is missing Risk/CIBO/independent/economic
    authority evidence. The dossier must reflect it as blocked (demo_eligible
    False, promotion_status external_evidence_dependent) and must not fabricate a
    downstream PASS or a completed external authority stage.
    """
    binding = _first_cohort_binding(strategy_binding_factory, suffix=704, code="vt-01")
    candidate = candidate_factory(candidate_suffix=704, binding=binding)
    lifecycle = start_trader_lab_lifecycle(candidate)
    for offset, stage in enumerate(
        (
            TraderLabStage.RESEARCH,
            TraderLabStage.REPLAY,
            TraderLabStage.FAST_FORWARD,
            TraderLabStage.OOS,
            TraderLabStage.STRESS,
            TraderLabStage.MONTE_CARLO,
        )
    ):
        evidence = stage_evidence_factory(
            stage=stage,
            candidate=candidate,
            evidence_suffix=9_700 + offset,
        )
        promoted = apply_trader_lab_promotion(
            lifecycle,
            TraderLabPromotionRequest(stage=stage, evidence=evidence),
        )
        assert isinstance(promoted, Success)
        lifecycle = promoted.value
    assert lifecycle.state is TraderLabState.MONTE_CARLO_QUALIFIED
    economic_evidence = lifecycle.qualifications[-1].evidence.source_reference
    entry = _hollow_entry(lifecycle, economic_evidence)

    evidence_root, aggregate = _build_fixture(tmp_path)
    reports = build_research_reports(
        evidence_root, aggregate, software_sha=_SHA, lifecycle_by_trader={"vt-01": entry}
    )

    vt01 = reports["vt-01-deep-characterization-dossier.json"]
    stages = cast(dict[str, object], vt01["lifecycle_stages"])
    promotion = cast(dict[str, object], vt01["promotion"])
    assert promotion["demo_eligible"] is False
    assert promotion["promotion_status"] == "external_evidence_dependent"
    assert promotion["state"] == "monte_carlo_qualified"
    assert promotion["blockers"]
    for stage_name in ("risk_review", "cibo_review", "independent_validation"):
        assert stages[stage_name] == "blocked_external"
    assert stages["economic_evidence"] == "not_started"
    assert reports["promotion-report.json"]["demo_eligible_count"] == 0


def test_lifecycle_by_trader_rejects_mismatched_candidate_binding(
    tmp_path: Path,
    strategy_binding_factory: Callable[..., ResearchRunStrategyBinding],
    candidate_factory: Callable[..., TraderLabCandidateBinding],
) -> None:
    """A hollow entry whose lifecycle candidate binds a different Trader is rejected.

    The entry label says vt-01 but its lifecycle candidate froze trader.code=vt-08;
    the trust-boundary cross-check must fail closed rather than misattribute the
    lifecycle under the wrong dossier.
    """
    binding = _first_cohort_binding(strategy_binding_factory, suffix=705, code="vt-08")
    candidate = candidate_factory(candidate_suffix=705, binding=binding)
    lifecycle = start_trader_lab_lifecycle(candidate)
    entry = _hollow_entry(lifecycle, None, trader_code="vt-01")

    evidence_root, aggregate = _build_fixture(tmp_path)
    with pytest.raises(FirstCohortFailureAnalysisError, match="mismatched Trader code"):
        build_research_reports(
            evidence_root,
            aggregate,
            software_sha=_SHA,
            lifecycle_by_trader={"vt-01": entry},
        )
